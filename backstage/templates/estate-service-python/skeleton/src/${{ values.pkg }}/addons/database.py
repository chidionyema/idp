{%- if 'database' in values.addons %}
"""Postgres on the cluster: a CloudNativePG Cluster named ${{ values.name }}-db, provisioned by
the infra pull request. CloudNativePG writes the connection string to the Secret
${{ values.name }}-db-app (key `uri`), which the deployment mounts as a file."""
import psycopg

from .. import secrets


def connect() -> psycopg.Connection:
    uri = secrets.read("uri")
    if not uri:
        raise RuntimeError("database secret not mounted: is the CloudNativePG Cluster ready?")
    return psycopg.connect(uri)
{%- else %}
"""Database not ticked at creation. Re-run the template with Database ticked to add it."""
{%- endif %}
