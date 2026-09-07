#!/usr/bin/env bash
# Fixture: the same script written so a failed `cd` stops it.
set -euo pipefail
cd /var/tmp/does-not-exist || exit 1
ls
