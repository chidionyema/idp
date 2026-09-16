#!/usr/bin/env python3
"""idp-estate-gateway: MCP Server boundary for the idp estate.

All LLM commands must route through idp/bin/idp-exec.
This server enforces the token efficiency mandate at the MCP layer.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from mcp.server import InitializationOptions, Server, stdio_server
from mcp.types import TextContent, Tool, ToolResult

import mcp.types as types

server = Server("idp-estate-gateway")
IDP_EXEC = Path(__file__).parent.parent / "bin" / "idp-exec"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Expose the estate_exec tool."""
    return [
        Tool(
            name="estate_exec",
            description="Execute a shell command through the token-efficient idp-exec wrapper. Output is clamped to 50 lines; full output saved to ~/.pi/agent/state/last_exec.log",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute (e.g., 'ls -la', 'git status')",
                    }
                },
                "required": ["command"],
            },
        )
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.ToolResult]:
    """Route all tool calls through idp-exec."""
    if name != "estate_exec":
        return [
            ToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
        ]

    command = arguments.get("command", "")
    if not command:
        return [
            ToolResult(
                content=[
                    TextContent(
                        type="text", text="Error: 'command' argument is required"
                    )
                ],
                isError=True,
            )
        ]

    # Route through idp-exec (trusted wrapper)
    try:
        result = subprocess.run(  # noqa: S603
            [str(IDP_EXEC), command],
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )

        output = result.stdout
        if result.stderr:
            output += result.stderr

        return [
            ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Command: {command}\nExit Code: {result.returncode}\n\nOutput:\n{output}",
                    )
                ],
                isError=(result.returncode != 0),
            )
        ]

    except FileNotFoundError:
        return [
            ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: idp-exec not found at {IDP_EXEC}",
                    )
                ],
                isError=True,
            )
        ]
    except subprocess.TimeoutExpired:
        return [
            ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Error: Command timed out after 300 seconds",
                    )
                ],
                isError=True,
            )
        ]
    except Exception as e:
        return [
            ToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
        ]


async def main():
    """Start the MCP server on stdio."""
    async with stdio_server(server) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, InitializationOptions())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
