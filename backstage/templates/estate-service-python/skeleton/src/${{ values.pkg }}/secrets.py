"""Secrets are files, never environment variables.

The cluster refuses envFrom and secretKeyRef (platform/edge/kyverno-secrets-policy.yaml); the
deployment mounts the vault entry at /var/run/secrets/${{ values.name }}/<key>. This reads one key.
"""
import os
import pathlib

SECRET_DIR = pathlib.Path(os.environ.get("SECRET_DIR", "/var/run/secrets/${{ values.name }}"))


def read(key: str) -> str | None:
    p = SECRET_DIR / key
    return p.read_text().strip() if p.is_file() else None
