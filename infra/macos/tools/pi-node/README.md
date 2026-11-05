# pi-node - restore the Node runtime Pi needs, without nvm or sudo

Pi's launcher runs `node` from `~/.local/bin`. When that symlink points at a Node the machine
can no longer run - a removed nvm version, a runtime built for another macOS - Pi fails to
start and the failure looks like Pi's, not Node's. This script repairs exactly that.

```bash
bash repair_pi_node_macos.sh
```

What it does, in order, and why each step is required:

1. **Picks the runtime the OS can actually run.** macOS 13.5+ gets Node 24; macOS 11-13.4 gets
   Node 22; anything older refuses before touching the disk, because the official binary will
   not execute there.
2. **Verifies the download against Node's own `SHASUMS256.txt`** and refuses on a mismatch. It
   installs to `~/.local/opt/pinned-node/<version>`, not over the system or nvm.
3. **Backs up, never overwrites.** Existing `node`/`npm`/`npx` files or symlinks (including
   broken ones) move to `~/.local/share/pi-node-repair/<timestamp>-<pid>/` first.
4. **Adds one idempotent PATH line** - `export PATH="$HOME/.local/bin:$PATH" # pinned-node-for-pi`
   - to `.bash_profile`, `.bashrc`, `.zprofile` and `.zshrc`, only if it is not already there.
5. **Proves it in fresh shells**, not in the calling one: `/bin/bash -lic` and `/bin/zsh -lic`
   must each resolve the pinned Node and run `pi --version`. A repair that only works in the
   terminal that ran it is the bug it was written to fix.

It does not reinstall Pi itself: if `pi` is missing from PATH after Node is repaired, it says so
and stops. That is a different failure with a different fix.

## Maintaining it

Re-running is safe and idempotent: a present-and-current runtime is a no-op, and the backup
directory is only written when something is replaced. The version map is pinned deliberately -
Node's release line moves, and a Mac whose only Node is whatever nvm last left behind will drift
back into this failure. Bump the two versions here in one change, with the upstream release they
come from, and re-run the script on the Mac.
