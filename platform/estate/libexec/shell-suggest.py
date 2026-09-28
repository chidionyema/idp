#!/usr/bin/env python3
"""Generate a unified diff patch for a specific line in a shell script."""

import sys, os

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <file> <line> <fixed_line_file>", file=sys.stderr)
    sys.exit(1)

file = sys.argv[1]
line_num = int(sys.argv[2])
fixed_file = sys.argv[3]

with open(file) as f:
    lines = f.readlines()
orig = lines[line_num - 1].rstrip("\n\r")

with open(fixed_file) as f:
    fixed_line = f.read().rstrip("\n\r")

# Use relative path from idp repo root so patch -p1 works
rel = os.path.relpath(file, os.path.expanduser("~/Documents/code/idp"))
if rel.startswith("../"):
    rel = os.path.basename(file)

sys.stdout.write(f"--- a/{rel}\n")
sys.stdout.write(f"+++ b/{rel}\n")
sys.stdout.write(f"@@ -{line_num},1 +{line_num},1 @@\n")
sys.stdout.write(f"-{orig}\n")
sys.stdout.write(f"+{fixed_line}\n")
sys.stdout.write("\n")
