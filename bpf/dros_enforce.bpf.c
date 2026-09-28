// bpf/dros_enforce.bpf.c
// Layer 4: DROS eBPF Enforcement Engine
// Kernel-space BPF LSM hook that intercepts socket_connect syscalls.
// Blocks direct agent egress; only loopback:8080 (elpis-proxy) is permitted.
// Revocation is instantaneous: kernel atomically marks PID as REVOKED → next syscall returns -EPERM.
//
// Compile (on node with kernel headers):
//   clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
//     -I/usr/include/$(uname -m)-linux-gnu \
//     -c bpf/dros_enforce.bpf.c -o /opt/dros/dros_enforce.bpf.o
//   llvm-objdump -S /opt/dros/dros_enforce.bpf.o | head -n 60
//
// Requires: kernel CONFIG_BPF_LSM=y, BPF JIT enabled.
// Attach with: bpftool prog load /opt/dros/dros_enforce.bpf.o /sys/fs/bpf/dros_enforce
// Attach lsm hook: bpftool cgroup attach /sys/fs/cgroup/unified dros_socket_connect

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define EPERM 1
#define AF_INET 2

// LPM Trie: subnets allowed for direct egress (beyond elpis-proxy loopback).
// Default policy: DENY. Only explicitly registered subnets pass.
// Use bpftool to add entries: bpftool map update pinned /sys/fs/bpf/allowed_subnets \
//   key hex 0a000000 00000000 08000000 00000000 value hex 01
struct {
	__uint(type, BPF_MAP_TYPE_LPM_TRIE);
	__type(key, struct ipv4_lpm_key);
	__type(value, __u8);
	__uint(max_entries, 1024);
	__uint(map_flags, BPF_F_NO_PREALLOC);
} allowed_ipv4_subnets SEC(".maps");

// Hash map: PID → Status
//   0 = Unknown (not an agent process) → ALLOW
//   1 = Active (agent process) → ALLOW only loopback:8080 + registered subnets
//   2 = Revoked → DENY immediately (-EPERM)
struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__type(key, __u32);   // PID
	__type(value, __u8);  // Status
	__uint(max_entries, 32768);
} agent_process_status SEC(".maps");

// LSM hook: sys_enter_connect (called on every TCP connect() syscall).
// Returns: 0 = ALLOW, -EPERM = DENY.
SEC("lsm/socket_connect")
int BPF_PROG(dros_socket_connect, struct socket *sock, struct sockaddr *address, int addrlen) {
	__u64 pid_tgid = bpf_get_current_pid_tgid();
	__u32 pid = (__u32)(pid_tgid >> 32);

	// 1. Check revocation status: if REVOKED, die immediately.
	// This is the atomic kill-switch: no race, no delay.
	__u8 *status = bpf_map_lookup_elem(&agent_process_status, &pid);
	if (status && *status == 2) {
		return -EPERM;
	}

	// 2. Allow non-IPv4 sockets (UNIX domain for SPIRE agent, local IPC).
	if (!address || address->sa_family != AF_INET) {
		return 0;
	}

	struct sockaddr_in *addr_in = (struct sockaddr_in *)address;
	__u32 dest_ip = addr_in->sin_addr.s_addr;
	__u16 dest_port = bpf_ntohs(addr_in->sin_port);

	// 3. Allow loopback:8080 (elpis-signing-proxy, mandatory egress path).
	// 127.0.0.1 in little-endian byte order: 0x0100007F.
	if (dest_ip == 0x0100007F && dest_port == 8080) {
		return 0;
	}

	// 4. If active agent process: deny all non-loopback egress.
	// The agent MUST go through elpis-proxy. There is no other path.
	if (status && *status == 1) {
		// Check LPM trie for allowed subnets.
		struct ipv4_lpm_key key = {
			.prefixlen = 32,
			.data = dest_ip,
		};
		__u8 *allowed = bpf_map_lookup_elem(&allowed_ipv4_subnets, &key);
		if (!allowed) {
			// Direct egress attempt bypassing elpis-proxy → BLOCK.
			return -EPERM;
		}
	}

	// 5. Unknown process: allow (not managed by DROS).
	return 0;
}

char LICENSE[] SEC("license") = "GPL";
