// Command nodesoftware-operator is the NodeSoftwareOperator controller. It watches
// RuntimeInstall CRs and reconciles them against target nodes using per-runtime handlers.
//
// On startup:
//  1. Parse flags (--metrics-addr, --health-addr, --leader-elect).
//  2. Build the controller-runtime manager.
//  3. Register the closed-set handlers in the registry (runsc shipped; kata, nvidia stubbed).
//  4. Wire the Reconciler.
//  5. Start the manager.
//
// The controller image runs in the operator's namespace. The handler pods it creates run in the
// same namespace and are hostPath-mounted to /host.
package main

import (
	"flag"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
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

var scheme = runtime.NewScheme()

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(nodesoftwarev1alpha1.AddToScheme(scheme))
}

func main() {
	var (
		metricsAddr      string
		healthAddr       string
		leaderElect      bool
		handlerImage     string
		handlerNamespace string
	)
	flag.StringVar(&metricsAddr, "metrics-addr", ":8080", "address for the metrics endpoint")
	flag.StringVar(&healthAddr, "health-addr", ":8081", "address for the health-probe endpoint")
	flag.BoolVar(&leaderElect, "leader-elect", true, "enable leader election for HA")
	flag.StringVar(&handlerImage, "handler-image", envOr("HANDLER_IMAGE", "ghcr.io/chidionyema/nodesoftware-runsc-handler:IMAGE_TAG"), "runsc handler image")
	flag.StringVar(&handlerNamespace, "handler-namespace", envOr("HANDLER_NAMESPACE", "nodesoftware-operator-system"), "namespace for handler pods")
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

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
	registry.Register(runsc.New(handlerImage, "/host"))
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

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}
