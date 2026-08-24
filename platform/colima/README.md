# colima settings this estate depends on

`~/.colima/default/colima.yaml` is not in any repository, so the settings the
estate's guarantees rest on are recorded here. Each row says what the setting
must be, why, and the command that reads it back.

| setting | must be | why | read it back |
|---|---|---|---|
| `network.hostAddresses` | `true` | With `false`, lima cannot forward to a specific host IP, so `docker run -p 127.0.0.1:80:80` is honoured inside the VM as `0.0.0.0` and republished on the Mac as `*`. Every "loopback-only" container port is then on whatever network the laptop is joined to. Measured 2026-08-24: `catalog/ports.yaml` declared `bind: 127.0.0.1` for 80 and 443, `docker port k3d-estate-serverlb` agreed, and `lsof` showed `limactl *:80 (LISTEN)` and `limactl *:443 (LISTEN)`. | `grep -n 'hostAddresses' ~/.colima/default/colima.yaml` |

A change to this file takes effect at the next `colima start`. **Never restart
colima as a side effect of other work** — it restarts every container on the
machine, which is what caused the load-255 incident. The change is written now
and lands at the next restart the founder or a scheduled window performs.

Until it lands, `bin/bind-audit` FAILs on ports 80 and 443, and `bin/port-gate
--live` reports the same two ports from a second, independent source. Neither
gate has an allow-list row for them, on purpose: an exemption would record the
exposure as intended rather than as open.
