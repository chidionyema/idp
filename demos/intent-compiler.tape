# The estate compiler, recorded by the machines (crew#805 Demo Standard).
# CI replays this script against the real binary on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/intent-compiler.gif.
# Every run is pointed at a temporary --register: the compiler writes the root-trust row for a
# secret intent, and a demo that edits the repository leaves the render job with unstaged
# changes it cannot rebase past (run 34175974078: 'cannot pull with rebase: You have unstaged
# changes'). A demo replays the tool; it does not get to change the estate.
Output docs/demos/intent-compiler.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# An agent tries to speak a cloud provider and a zone — refused"
Enter
Type "python3 bin/intent-compile --intents tests/fixtures/intent/bad --out /tmp/demo-bad --register /tmp/demo-bad.md"
Enter
Sleep 3.5s
Type "# A valid capability request — compiled, twice, byte-identical"
Enter
Type "python3 bin/intent-compile --intents tests/fixtures/intent/good --out /tmp/demo-a --register /tmp/demo-a/register.md"
Enter
Sleep 2s
Type "python3 bin/intent-compile --intents tests/fixtures/intent/good --out /tmp/demo-b --register /tmp/demo-b/register.md"
Enter
Sleep 2s
Type "diff -r /tmp/demo-a /tmp/demo-b && echo deterministic"
Enter
Sleep 4s
