"""Good fixture: a mutating MCP tool ships with its simulate twin (must pass)."""

try:
    from datasette import hookimpl
except ImportError:

    def hookimpl(fn):
        return fn


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def simulate_change(source: str) -> dict:
        """Propose before execute."""
        return {"verdict": "UNKNOWN"}

    @mcp.tool()
    async def execute_change(proposal_id: str) -> dict:
        """Execute only what was simulated."""
        return {"executed": False}
