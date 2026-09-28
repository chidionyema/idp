"""sovereign/attach/ -- estate attach (cp21), owner: builder D.
See sovereign/attach/README.md.

Deliberately does not import sovereign.attach.core here: sovereign/config.py
merges ATTACH_KEYS via `from sovereign.attach.config_keys import
ATTACH_KEYS`, which runs this file first. core.py's own lazy
`from sovereign import config` (inside function bodies, not at module
level) is the second line of defense; this file not importing core.py at
all is the first.
"""
