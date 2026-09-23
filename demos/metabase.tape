# Boardroom dashboards: the metabase layer is declared in git, end to end (crew#539).
# CI replays this script against the real manifests on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/metabase.gif.
Output docs/demos/metabase.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# The dashboard layer is five declared files, no console steps"
Enter
Type "ls platform/observability/ | grep metabase"
Enter
Sleep 3s
Type "# Its public door rides the shared edge, behind the one estate login"
Enter
Type "grep -B1 -A2 'hostnames:' platform/observability/metabase-httproute.yaml"
Enter
Sleep 3s
Type "# A founder-facing surface survives losing one node, by declaration"
Enter
Type "head -12 platform/observability/metabase-availability.yaml"
Enter
Sleep 3s
Type `python3 -c "import yaml,glob; files=sorted(glob.glob('platform/observability/metabase-*.yaml')); [list(yaml.safe_load_all(open(f))) for f in files]; print('ok:', len(files), 'metabase manifests parse clean')"`
Enter
Sleep 3s
