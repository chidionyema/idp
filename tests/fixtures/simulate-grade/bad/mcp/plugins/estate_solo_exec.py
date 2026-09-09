"""Bad fixture: a mutating MCP tool with no simulate twin (must be refused)."""

try:
    from datasette import hookimpl
except ImportError:

    def hookimpl(fn):
        return fn


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def execute_change(proposal_id: str) -> dict:
        """A tool that changes the world with no propose twin -- the breach."""
        return {"executed": True}
