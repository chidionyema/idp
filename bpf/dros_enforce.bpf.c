// bpf/dros_enforce.bpf.c
// Layer 4: DROS eBPF Enforcement Engine
// Kernel-space BPF LSM hook that intercepts socket_connect syscalls.
// Blocks direct agent egress; only loopback:8080 (elpis-proxy) is permitted.
// Revocation is instantaneous: kernel atomically marks PID as REVOKED -> next syscall returns -EPERM.
//
// Compile on a node with kernel headers:
//   clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
//     -I/usr/include/x86_64-linux-gnu \
//     -I/usr/include/linux \
//     -I/usr/include/asm-generic \
//     -c bpf/dros_enforce.bpf.c -o /opt/dros/dros_enforce.bpf.o
//
// Requires: kernel CONFIG_BPF_LSM=y, BPF JIT enabled.

#include <uapi/linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
#include <linux/socket.h>
#include <linux/in.h>
#include <linux/uio.h>

#define EPERM 1
#define AF_INET 2

// Minimal struct socket definition (compatible with kernel's net/sock.h).
// We only declare what we need to satisfy the compiler.
// The kernel BPF verifier handles the actual type checking.
struct socket {
    int type;
    unsigned long flags;
};

// LPM Trie: subnets allowed for direct egress (beyond elpis-proxy loopback).
struct ipv4_lpm_key {
    __u32 prefixlen;
    __u32 data;
};

struct {
    __uint(type, BPF_MAP_TYPE_LPM_TRIE);
    __type(key, struct ipv4_lpm_key);
    __type(value, __u8);
    __uint(max_entries, 1024);
    __uint(map_flags, BPF_F_NO_PREALLOC);
} allowed_ipv4_subnets SEC(".maps");

// Hash map: PID -> Status
//   0 = Unknown (not an agent process) -> ALLOW
//   1 = Active (agent process) -> ALLOW only loopback:8080 + registered subnets
//   2 = Revoked -> DENY immediately (-EPERM)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, __u32);
    __type(value, __u8);
    __uint(max_entries, 32768);
} agent_process_status SEC(".maps");

// LSM hook: security_socket_connect
// Returns: 0 = ALLOW, -EPERM = DENY.
SEC("lsm/socket_connect")
int BPF_PROG(dros_socket_connect,
              struct socket *sock,
              struct sockaddr *address,
              int addrlen) {
    __u64 pid_tgid = bpf_get_current_pid_tgid();
    __u32 pid = (__u32)(pid_tgid >> 32);

    // 1. Check revocation status: if REVOKED, die immediately.
    __u8 *status = bpf_map_lookup_elem(&agent_process_status, &pid);
    if (status && *status == 2) {
        return -EPERM;
    }

    // 2. Allow non-IPv4 sockets (UNIX domain for SPIRE agent, local IPC).
    if (!address || address->sa_family != AF_INET) {
        return 0;
    }

    // 3. Get IPv4 destination from sockaddr_in.
    struct sockaddr_in *addr_in = (struct sockaddr_in *)address;
    __u32 dest_ip = addr_in->sin_addr.s_addr;
    __u16 dest_port = __builtin_bswap16(addr_in->sin_port);

    // 4. Allow loopback:8080 (elpis-signing-proxy, mandatory egress path).
    // 127.0.0.1 in little-endian: 0x0100007F.
    if (dest_ip == 0x0100007F && dest_port == 8080) {
        return 0;
    }

    // 5. If active agent process: deny all non-loopback egress.
    // The agent MUST go through elpis-proxy. There is no other path.
    if (status && *status == 1) {
        struct ipv4_lpm_key key = {
            .prefixlen = 32,
            .data = dest_ip,
        };
        __u8 *allowed = bpf_map_lookup_elem(&allowed_ipv4_subnets, &key);
        if (!allowed) {
            return -EPERM;
        }
    }

    // 6. Unknown process: allow (not managed by DROS).
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
