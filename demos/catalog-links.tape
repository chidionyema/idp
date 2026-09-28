# Catalogue links: every component has a URL the founder can open (crew#269, crew#297).
# CI replays this script against real inventory on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/catalog-links.gif.
Output docs/demos/catalog-links.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# Generate the catalogue from the estate's inventory"
Enter
Type "INV=tests/fixtures/inventory.json OUT=/tmp/demo-cat ESTATE_ENV=dev python3 bin/catalog-gen"
Enter
Sleep 6s
Type "# Verify every Component in the catalogue carries a URL"
Enter
Type "python3 bin/catalog-links-check /tmp/demo-cat/catalog-info.yaml"
Enter
Sleep 2s
Type "# Run again — the output is deterministic"
Enter
Type "INV=tests/fixtures/inventory.json OUT=/tmp/demo-cat2 ESTATE_ENV=dev python3 bin/catalog-gen"
Enter
Sleep 6s
Type "diff -q /tmp/demo-cat/catalog-info.yaml /tmp/demo-cat2/catalog-info.yaml"
Enter
Sleep 3s
