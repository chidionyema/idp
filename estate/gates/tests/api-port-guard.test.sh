#!/bin/bash
G="$HOME/.estate/hooks/api-port-guard"
pass=0; fail=0
t(){ # expected_exit  label  command
  local exp=$1 label=$2 cmd=$3
  printf '{"tool_name":"Bash","tool_input":{"command":%s}}' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$cmd")" \
    | "$G" >/dev/null 2>/tmp/guard.err
  local got=$?
  if [ "$got" = "$exp" ]; then printf "  PASS  %-42s exit=%s\n" "$label" "$got"; pass=$((pass+1));
  else printf "  FAIL  %-42s expected=%s got=%s\n" "$label" "$exp" "$got"; fail=$((fail+1)); fi
}
DSH_PID=$(lsof -nP -ti tcp:3080 -sTCP:LISTEN | head -1)
t 2 "kill the PID on port 3080"          "kill -9 $DSH_PID"
t 2 "bootout the dsh-web label"          "launchctl bootout gui/501/ai.estate.dsh-web"
t 2 "pkill -f dsh-web"                   "pkill -f dsh-web"
t 2 "bootout pennyd (the 2026-11-27 bug)" "launchctl bootout com.estate.pennyd"
t 0 "plain listing"                      "ls -la ~/Documents/code"
t 0 "reading the port (not killing)"     "lsof -nP -iTCP:3080"
t 0 "kill an unrelated PID"              "kill -9 99999"
t 0 "echo to a file"                     "echo hi > /tmp/x"
t 0 "grep for pennyd in logs"            "grep -c pennyd /tmp/mlive.log"
echo ""; echo "guard falsifier: $pass passed, $fail failed"
[ "$fail" = 0 ] || exit 1
