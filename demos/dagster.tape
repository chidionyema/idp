# The estate scheduler: every clock is one generated table (crew#516, crew#727).
# CI replays this script against the real generator on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/dagster.gif.
Output docs/demos/dagster.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# Every scheduled job in the estate lives in one generated table"
Enter
Type "head -14 docs/scheduling/CLOCKS.md"
Enter
Sleep 3s
Type "# The table is generated, never hand-edited: --check fails when it is stale"
Enter
Type "python3 bin/estate-clocks --check && echo 'ok: the clocks page matches the sources'"
Enter
Sleep 5s
Type "# The scheduler itself is a declared row the cluster applies from git"
Enter
Type "grep -A8 'name: dagster' clusters/oke/platform.yaml | head -12"
Enter
Sleep 4s
