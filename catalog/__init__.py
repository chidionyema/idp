"""The estate's catalog: one census, one record, one join table.

Phase 0 (the catalog proposal, D1): the record is Postgres in the estate's own
CloudNativePG cluster, and catalog/estate.db is a generated cache of it. This
package is the census that fills that record -- four collectors, one join, one
coverage table.
"""

from catalog.census.model import PLANES, STATE_MANAGED, STATE_UNCATALOGUED

__all__ = ["PLANES", "STATE_MANAGED", "STATE_UNCATALOGUED"]
