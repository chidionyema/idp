// cmd/dros-daemon/main.go
// Layer 4: DROS eBPF Enforcement Engine (user-space control plane).
// Loads BPF bytecode, attaches LSM hook, exposes management Unix socket.
// Provides instantaneous in-kernel revocation: POST /revoke?pid=X
// immediately marks PID=2 in the BPF hash map → next syscall returns -EPERM.

package main

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
	"github.com/cilium/ebpf/rlimit"
)

const (
	statusUnknown  uint8 = 0
	statusActive   uint8 = 1
	statusRevoked  uint8 = 2
)

func main() {
	// Remove memlock limit required by eBPF subsystem.
	if err := rlimit.RemoveMemlock(); err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Removing memory locks: %v
", err)
		os.Exit(1)
	}

	bpfObjPath := os.Getenv("DROS_BPF_OBJECT")
	if bpfObjPath == "" {
		bpfObjPath = "/opt/dros/dros_enforce.bpf.o"
	}

	spec, err := ebpf.LoadCollectionSpec(bpfObjPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Failed reading BPF bytecode: %v
", err)
		os.Exit(1)
	}

	coll, err := ebpf.NewCollection(spec)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Loading BPF maps into kernel: %v
", err)
		os.Exit(1)
	}
	defer coll.Close()

	// Attach to Kernel LSM Hook (requires kernel CONFIG_BPF_LSM=y).
	l, err := link.AttachLSM(link.LSMOptions{
		Program: coll.Programs["dros_socket_connect"],
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Attaching to LSM hook (requires kernel CONFIG_BPF_LSM=y): %v
", err)
		os.Exit(1)
	}
	defer l.Close()

	agentMap := coll.Maps["agent_process_status"]
	if agentMap == nil {
		fmt.Fprintf(os.Stderr, "FATAL: BPF map 'agent_process_status' not found in object
")
		os.Exit(1)
	}

	// Expose Unix Domain Socket for instantaneous agent registration/revocation.
	socketPath := "/var/run/dros/control.sock"
	os.Remove(socketPath)

	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Opening management socket: %v
", err)
		os.Exit(1)
	}
	defer listener.Close()
	os.Chmod(socketPath, 0600)

	mux := http.NewServeMux()

	// POST /register?pid=<N> — Mark PID as active agent.
	mux.HandleFunc("/register", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		pidStr := r.URL.Query().Get("pid")
		pid, err := strconv.ParseUint(pidStr, 10, 32)
		if err != nil {
			http.Error(w, "invalid pid", http.StatusBadRequest)
			return
		}
		p := uint32(pid)
		status := statusActive
		if err := agentMap.Put(&p, &status); err != nil {
			http.Error(w, fmt.Sprintf("bpf map error: %v", err), http.StatusInternalServerError)
			return
		}
		fmt.Printf("DROS: Registered agent PID %d (ACTIVE)
", pid)
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("REGISTERED"))
	})

	// POST /revoke?pid=<N> — Revoke agent (kernel kills on next syscall).
	mux.HandleFunc("/revoke", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		pidStr := r.URL.Query().Get("pid")
		pid, err := strconv.ParseUint(pidStr, 10, 32)
		if err != nil {
			http.Error(w, "invalid pid", http.StatusBadRequest)
			return
		}
		p := uint32(pid)
		status := statusRevoked
		if err := agentMap.Put(&p, &status); err != nil {
			http.Error(w, fmt.Sprintf("bpf map error: %v", err), http.StatusInternalServerError)
			return
		}
		fmt.Printf("DROS: Revoked agent PID %d — next syscall returns -EPERM
", pid)
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("REVOKED"))
	})

	// GET /status?pid=<N> — Query agent process status.
	mux.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		pidStr := r.URL.Query().Get("pid")
		pid, err := strconv.ParseUint(pidStr, 10, 32)
		if err != nil {
			http.Error(w, "invalid pid", http.StatusBadRequest)
			return
		}
		p := uint32(pid)
		var status uint8
		if err := agentMap.Lookup(&p, &status); err != nil {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		labels := map[uint8]string{0: "UNKNOWN", 1: "ACTIVE", 2: "REVOKED"}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(fmt.Sprintf("pid=%d status=%s", pid, labels[status])))
	})

	server := &http.Server{Handler: mux}
	go func() {
		_ = server.Serve(listener)
	}()

	fmt.Println("DROS_ENFORCER_ACTIVE: Kernel hooks locked to socket_connect via BPF LSM")
	fmt.Printf("DROS: Management socket at %s
", socketPath)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	fmt.Println("DROS: Shutting down...")
	_ = server.Shutdown(context.Background())
}
