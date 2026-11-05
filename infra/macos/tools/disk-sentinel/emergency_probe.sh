#!/bin/bash
# Entirely read-only. Emits no files, does not invoke a package manager.
set -u
printf '\n=== Actual available storage on the home volume ===\n'
/bin/df -h "$HOME"
printf '\n=== High-probability storage consumers (sizes may overlap) ===\n'
for path in \
  "$HOME/.npm" \
  "$HOME/.nvm/.cache" \
  "$HOME/.cache" \
  "$HOME/.gradle" \
  "$HOME/.cargo" \
  "$HOME/Library/Caches" \
  "$HOME/Library/Developer" \
  "$HOME/Library/Containers/com.docker.docker/Data/vms" \
  "$HOME/Downloads"; do
  if [ -d "$path" ]; then
    /usr/bin/nice -n 18 /usr/bin/du -skx "$path" 2>/dev/null | /usr/bin/awk -v p="$path" 'NR==1 {printf "%8.2f GiB  %s\n",$1/1048576,p}'
  fi
done
printf '\n=== Important active tasks (read-only listing) ===\n'
/bin/ps -axo pid,etime,comm 2>/dev/null | /usr/bin/grep -E '(^ *PID|node|npm|npx|docker|xcode|swift|clang|rsync|backup|python)' | /usr/bin/head -n 35 || true
printf '\nNo files were deleted or modified. Do not infer safety from size alone.\n'
