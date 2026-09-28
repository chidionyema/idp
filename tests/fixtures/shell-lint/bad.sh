#!/usr/bin/env bash
# Fixture: shellcheck -S warning must refuse this file. `cd` with no guard (SC2164)
# carries on in the directory it was already in when the path does not exist, so
# every line after it runs somewhere else than the author meant.
cd /var/tmp/does-not-exist
ls
