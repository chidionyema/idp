#!/usr/bin/env bash
# DISABLED 2026-11-11 by founder order -- see bin/idp-disk-watch's header.
#
# The 1303-line cleaner behind the resident guardian. Measured: 120 bounded steps freed
# 3 MB each while the volume fell 1526 MB -> 1012 MB and the machine sat at 26 MB free
# RAM with 80% swap. When the guardian was stopped the volume recovered on its own
# (1012 MB -> 2335 MB), which is the measurement that settles it: this cleaner was not
# what freed the disk, and running it forever cost more than it returned.
#
# Kept as a tombstone rather than deleted so any caller that still invokes it gets an
# honest, visible refusal instead of a silent no-op or a missing-file error.
echo "BLIND disk-cleanup disabled 2026-11-11 (founder order): it freed 3 MB/step while the volume fell. Do not reinstall." >&2
exit 1
