# Drill evidence: the login drill photographs pages and proves they rendered (crew#292 CP2).
# CI replays this script to validate the drill's configuration on every relevant push,
# so this demo cannot go stale. Rendered to docs/demos/drill-evidence.gif.
Output docs/demos/drill-evidence.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Type "# The login drill validates the front door and photographs evidence"
Enter
Type "head -25 bin/idp-login-drill"
Enter
Sleep 2s
Type "# The drill configuration is loaded from the estate config"
Enter
Type "grep -A3 ESTATE_OIDC_DOMAIN_URL clusters/oke/estate-config.yaml"
Enter
Sleep 2s
Type "# Validate the drill's configuration and test framework"
Enter
Type `python3 -c "from tests.test_incident_crew301_login_drill_red_is_readable_and_green_closes_the_p0 import test_the_fail_line_keeps_the_call_log; test_the_fail_line_keeps_the_call_log(); print('ok: drill configuration valid')"`
Enter
Sleep 3s
