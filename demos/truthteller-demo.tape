# The agent that couldn't lie: an agent claims done, the truth-teller asks the cluster.
# Demo Standard (crew#805): demo-render.yml replays this against the real
# bin/idp-truthteller-demo and commits the recording, so it can never show what the tool
# no longer does. No live cluster is needed: the observed state is injected exactly the way
# the test suite injects it, so the comparison, the signature and the exit code are real.
Output docs/demos/truthteller-demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"

Type "# The claim: an agent says its service is Ready with 3 replicas."
Enter
Sleep 1s
Type "grep -n 'class RogueAgent' bin/idp-truthteller-demo"
Enter
Sleep 1s

Type "# The observed state is not an opinion. It is read back from the cluster,"
Enter
Sleep 1s
Type "# and here it is injected the way the tests inject it, so no cluster is needed."
Enter
Sleep 1s
Type "grep -n 'def _shadow_mock' tests/test_truthteller_demo.py"
Enter
Sleep 1s

Type "# The moment a buyer is buying: the claim meets the cluster."
Enter
Sleep 1s
Type `python3 -c "import importlib.util,sys; from importlib.machinery import SourceFileLoader; l=SourceFileLoader('tt','bin/idp-truthteller-demo'); s=importlib.util.spec_from_loader('tt',l); m=importlib.util.module_from_spec(s); sys.modules['tt']=m; l.exec_module(m); S=type('S',(),{'get_deployment_state':lambda self,n:{'replicas':1,'status':'CrashLoopBackOff'}}); r=m.run_buyer_demo(shadow=S()); print('claim    ', r['claim']['asserted_status'], r['claim']['asserted_replicas']); print('observed ', r['actual']['status'], r['actual']['replicas']); print('match    ', r['match']); print('signature', r['signature'][:32]); print('impact   ', r['business_impact'])"`
Enter
Sleep 4s

Type "# With no sandbox reachable it does not guess. BLIND is a fail-closed FAIL, never a pass."
Enter
Sleep 1s
Type "bin/idp-truthteller-demo; echo exit=$?"
Enter
Sleep 3s
