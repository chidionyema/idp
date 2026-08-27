"""crew#503: bin/idp-oci-whoami read the session token's mtime with `stat -f %m`,
which is BSD/macOS only. On the Linux runner (vault-seed run 33089277235) GNU
`stat -f` printed filesystem status, `[ ... -gt ... ]` errored with "integer
expression expected" and no live session was ever detected. The helper must
return an integer mtime on whichever OS runs it. No socket."""
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oci-whoami"


def _mtime(path):
    src = SCRIPT.read_text()
    start = src.index("token_mtime() {")
    end = src.index("}", start) + 1
    return subprocess.run(
        ["bash", "-c", src[start:end] + f'\ntoken_mtime "{path}"'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_token_mtime_is_the_files_epoch_seconds(tmp_path):
    f = tmp_path / "token"
    f.write_text("x")
    want = 1_700_000_000
    os.utime(f, (want, want))
    assert _mtime(f) == str(want)


def test_missing_file_yields_zero_not_garbage(tmp_path):
    assert _mtime(tmp_path / "nope") == "0"


def test_script_no_longer_calls_bsd_stat_inline():
    body = SCRIPT.read_text()
    assert 'stat -f "%m" "$d/token"' not in body
