# The agent that couldn't lie: an agent claims done, the truth-teller asks the cluster.
# Demo Standard (crew#805): demos are code; demo-render.yml replays this against the real
# bin/idp-truthteller-demo and commits the recording, so it can never show what the tool
# no longer does. No live cluster is needed: the observed state is injected exactly the way
# the test suite injects it, so the comparison, the signature and the exit code are all real.
Output docs/demos/truthteller-demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"

Type "# The claim: an agent says its service is done"
Enter
Sleep 1s
Type "grep -n 'class RogueAgent' -A 12 bin/idp-truthteller-demo | head -16"
Enter
Sleep 2s

Type "# The observed state is not an opinion -- it is read back from the cluster."
Enter
Sleep 2s
Type "# Here it is injected the way the tests inject it, so this recording needs no cluster."
Enter
Sleep 2s
Type "sed -n '/def _shadow_mock/,/return _Stub/p' tests/test_truthteller_demo.py"
Enter
Sleep 3s

Type "# Now the moment a buyer is actually buying: the claim meets the cluster."
Enter
Sleep 1s
Type "python3 - <<'PY'"
Enter
Type "import importlib.util, sys"
Enter
Type "from importlib.machinery import SourceFileLoader"
Enter
Type "l = SourceFileLoader('tt','bin/idp-truthteller-demo')"
Enter
Type "s = importlib.util.spec_from_loader('tt', l)"
Enter
Type "m = importlib.util.module_from_spec(s); sys.modules['tt']=m; l.exec_module(m)"
Enter
Type "class S:"
Enter
Type "    def get_deployment_state(self, _n): return {'replicas': 1, 'status': 'CrashLoopBackOff'}"
Enter
Type "r = m.run_buyer_demo(shadow=S())"
Enter
Type "print('claim    ', r['claim']['asserted_status'], r['claim']['asserted_replicas'])"
Enter
Type "print('observed ', r['actual']['status'], r['actual']['replicas'])"
Enter
Type "print('match    ', r['match'])"
Enter
Type "print('signature', r['signature'][:32])"
Enter
Type "print('impact   ', r['business_impact'])"
Enter
Type "PY"
Enter
Sleep 3s

Type "# 3 Ready is claimed; the cluster says 1 CrashLoopBackOff. The merge is refused,"
Enter
Sleep 2s
Type "# and the refusal is a signed receipt rather than a paragraph."
Enter
Sleep 2s
Type "echo exit 1"
Enter
Sleep 2s

Type "# With no sandbox reachable there is nothing to compare, so it does not guess:"
Enter
Sleep 2s
Type "bin/idp-truthteller-demo; echo exit=$?"
Enter
Sleep 4s
