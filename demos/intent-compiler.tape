# The estate compiler, recorded by the machines (crew#805 Demo Standard).
# CI replays this script against the real binary on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/intent-compiler.gif.
Output docs/demos/intent-compiler.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# An agent tries to speak a cloud provider and a zone — refused"
Enter
Type "python3 bin/intent-compile --intents tests/fixtures/intent/bad --out /tmp/demo-bad"
Enter
Sleep 3.5s
Type "# A valid capability request — compiled, twice, byte-identical"
Enter
Type "python3 bin/intent-compile --intents tests/fixtures/intent/good --out /tmp/demo-a"
Enter
Sleep 2s
Type "python3 bin/intent-compile --intents tests/fixtures/intent/good --out /tmp/demo-b"
Enter
Sleep 2s
Type "diff -r /tmp/demo-a /tmp/demo-b && echo deterministic"
Enter
Sleep 4s
