# Demo: Cursor is Otto's WORK worker

Otto's WORK lane runs Cursor on the Mac through `cursor-agent`, which only starts
when the vault holds `CURSOR_API_KEY`. Architect stays on the model router. A
person Cursor login is not this key.

The live dispatch file names the runtime and the wrapper, and never puts a key
on the command line:

```
$ python3 -c "import yaml; from pathlib import Path
p=Path('platform/hermes-agent/estate.yaml')
doc=yaml.safe_load(yaml.safe_load(p.read_text())['data']['estate.yaml'])
print(doc['dispatch']['runtime'])
print(doc['dispatch']['runtimes']['cursor'])"
cursor
['cursor-agent', '-p', '--force', '--model', 'composer-2.5', '{prompt}']
```

The control that refuses a Mac login without the vault key, and that Cursor is
a catalogue vendor the founder card opens:

```
$ .venv/bin/pytest -o addopts= -q tests/test_incident_crew751_cursor_is_the_hermes_worker.py
.......
7 passed, 49 warnings in 213.24s (0:03:33)
```

`bin/catalog-gen` against the fixture inventory emits `vendor-cursor` among the
registry vendors (captured 2026-09-02 on this branch):

```
catalog-gen: 142 entities, 3 dependsOn edges -> .../catalog-info.yaml
  vendors        12  (anthropic, apprise_telegram, cursor, deepseek, exa, gemini, google_oauth, kimi, minimax, openrouter, stripe, telegram)
```

The key is minted once in the Cursor dashboard and stored as the GitHub secret
`SEED_CURSOR_API_KEY`. Apply proves it and writes the vault. Until that secret
exists the wrapper prints `cursor-agent: no CURSOR_API_KEY in the vault; refusing the Mac login` and exits 2.

Tracked on [this ticket](https://github.com/chidionyema/crew/issues/751).
