// Command nodesoftware-operator is the NodeSoftwareOperator controller. It watches
// RuntimeInstall CRs and reconciles them against target nodes using per-runtime handlers.
//
// On startup:
//  1. Parse flags (--metrics-addr, --health-addr, --leader-elect, --handler-image-source).
//  2. Resolve --handler-image-source to a real image reference (default reads the
//     `runsc-handler-mirror` initContainer image from this pod's spec, so Flux image
//     automation owns the tag and we never need to hard-code a SHA in source).
//  3. Build the controller-runtime manager.
//  4. Register the closed-set handlers in the registry (runsc shipped; kata, nvidia stubbed).
//  5. Wire the Reconciler.
//  6. Start the manager.
//
// The controller image runs in the operator's namespace. The handler pods it creates run in the
// same namespace and are hostPath-mounted to /host.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/kubernetes"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/manager"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/controller"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler/runsc"
)

const (
	// defaultHandlerImageSource is the initContainer whose image the controller
	// reads at startup to learn which runsc handler image to spawn. The
	// initContainer itself is a noop (its only job is to be a kustomize-managed
	// image: field that Flux image-automation can rewrite).
	defaultHandlerImageSource = "init:runsc-handler-mirror"
)

var scheme = runtime.NewScheme()

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(nodesoftwarev1alpha1.AddToScheme(scheme))
}

func main() {
	var (
		metricsAddr        string
		healthAddr         string
		leaderElect        bool
		handlerImage       string
		handlerImageSource string
		handlerNamespace   string
	)
	flag.StringVar(&metricsAddr, "metrics-addr", ":8080", "address for the metrics endpoint")
	flag.StringVar(&healthAddr, "health-addr", ":8081", "address for the health-probe endpoint")
	flag.BoolVar(&leaderElect, "leader-elect", true, "enable leader election for HA")
	flag.StringVar(&handlerImage, "handler-image", "", "literal handler image (empty => resolve from --handler-image-source). Used for unit tests and out-of-cluster dev.")
	flag.StringVar(&handlerImageSource, "handler-image-source", envOr("HANDLER_IMAGE_SOURCE", defaultHandlerImageSource), `source of the handler image. "init:<name>" reads the named initContainer's image from this pod (image-automation-owned). A literal image string pins it in source.`)
	flag.StringVar(&handlerNamespace, "handler-namespace", envOr("HANDLER_NAMESPACE", "nodesoftware-operator"), "namespace for handler pods")
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

	if handlerImage == "" {
		resolved, err := resolveHandlerImage(handlerImageSource)
		if err != nil {
			ctrl.Log.Error(err, "unable to resolve --handler-image from --handler-image-source",
				"source", handlerImageSource)
			os.Exit(1)
		}
		handlerImage = resolved
		ctrl.Log.Info("resolved handler image from source", "source", handlerImageSource, "image", handlerImage)
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), manager.Options{
		Scheme:                 scheme,
		HealthProbeBindAddress: healthAddr,
		Metrics:                metricsserver.Options{BindAddress: metricsAddr},
		LeaderElection:         leaderElect,
		LeaderElectionID:       "nodesoftware-operator.estate.io",
	})
	if err != nil {
		ctrl.Log.Error(err, "unable to start manager")
		os.Exit(1)
	}

	registry := handler.NewRegistry()
	runscHandler, err := runsc.New(handlerImage, "/host")
	if err != nil {
		ctrl.Log.Error(err, "unable to construct runsc handler", "handlerImage", handlerImage)
		os.Exit(1)
	}
	registry.Register(runscHandler)
	// kata + nvidia handlers register when their handlers land (NodeSoftwareOperator: kata-runtime-handler
	// and NodeSoftwareOperator: nvidia-runtime-handler).

	if err := (&controller.Reconciler{
		Client:           mgr.GetClient(),
		Scheme:           mgr.GetScheme(),
		Handlers:         registry,
		HandlerNamespace: handlerNamespace,
	}).SetupWithManager(mgr); err != nil {
		ctrl.Log.Error(err, "unable to create controller")
		os.Exit(1)
	}

	if err := mgr.AddHealthzCheck("ping", healthz.Ping); err != nil {
		ctrl.Log.Error(err, "unable to add healthz")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("ping", healthz.Ping); err != nil {
		ctrl.Log.Error(err, "unable to add readyz")
		os.Exit(1)
	}

	ctrl.Log.Info("starting manager", "runtimes", registry.Names())
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		ctrl.Log.Error(err, "manager exited non-zero")
		os.Exit(1)
	}
}

// resolveHandlerImage translates --handler-image-source into a concrete image string.
// The only scheme currently supported is "init:<containerName>", which reads the named
// initContainer's image from the controller's own pod. The pod identity comes from the
// downward-API env vars POD_NAME / POD_NAMESPACE (deployment.yaml). Out-of-cluster runs
// (unit tests, dev) set --handler-image directly and skip this code path.
//
// Why this exists: image-automation only rewrites PodSpec container `image:` fields; a
// CLI flag cannot carry a $imagepolicy marker, so wiring the runsc handler image through
// a flag would freeze its tag at apply time and break the estate's auto-bump flow.
// Reading from an initContainer puts the tag under kustomize's control while still
// giving the controller binary access to the live value at startup.
func resolveHandlerImage(source string) (string, error) {
	const initScheme = "init:"
	if len(source) <= len(initScheme) || source[:len(initScheme)] != initScheme {
		return "", fmt.Errorf("unsupported --handler-image-source %q (only %s<containerName> is implemented)", source, initScheme)
	}
	containerName := source[len(initScheme):]

	podName := os.Getenv("POD_NAME")
	podNamespace := os.Getenv("POD_NAMESPACE")
	if podName == "" || podNamespace == "" {
		return "", fmt.Errorf("in-cluster identity required: POD_NAME=%q POD_NAMESPACE=%q (deployment.yaml must downward-API both)", podName, podNamespace)
	}

	cfg, err := ctrl.GetConfig()
	if err != nil {
		return "", fmt.Errorf("kubeconfig: %w", err)
	}
	clientset, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		return "", fmt.Errorf("kube client: %w", err)
	}

	pod, err := clientset.CoreV1().Pods(podNamespace).Get(context.Background(), podName, metav1.GetOptions{})
	if err != nil {
		if apierrors.IsNotFound(err) {
			return "", fmt.Errorf("pod %s/%s not found (controller started before the pod was visible to its own service account?): %w", podNamespace, podName, err)
		}
		return "", fmt.Errorf("get pod %s/%s: %w", podNamespace, podName, err)
	}

	for _, c := range pod.Spec.InitContainers {
		if c.Name == containerName {
			if c.Image == "" {
				return "", fmt.Errorf("initContainer %q has empty image: field (kustomize images: marker missing?)", containerName)
			}
			return c.Image, nil
		}
	}
	return "", fmt.Errorf("initContainer %q not found on pod %s/%s (check deployment.yaml for the runsc-handler-mirror entry)", containerName, podNamespace, podName)
}

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}
