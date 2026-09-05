# Demo: plist-gate

`bin/plist-gate` renders every `launchd/*.plist.tmpl` the way `bin/idp-install-launchd` does and parses the result. It exists because idp#49 merged a template in which a string replace had inserted a comment between every character; CI was green because nothing rendered it, and the installed plist came out at 671 KB. Run on this checkout:

```
$ python3 bin/plist-gate
ok   launchd/ai.estate.idp.plist.tmpl
ok   launchd/ai.estate.scheduler.plist.tmpl
$ python3 bin/plist-gate tests/fixtures/plist/bad.plist.tmpl
FAIL tests/fixtures/plist/bad.plist.tmpl: does not parse: InvalidFileException: Invalid file
```

The bad fixture is the first 4 KB of the merged template from idp#49, so the gate is proved against the real incident and not an invented one. `bin/idp-ci` runs both cases in one row named `plist`.
