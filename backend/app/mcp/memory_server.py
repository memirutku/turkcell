"""Separate MCP server for customer interaction memory.

Mounted at /mcp/memory — independent from the personalization MCP at /mcp.
"""

import logging

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

logger = logging.getLogger(__name__)


def create_and_mount_memory_mcp(app: FastAPI) -> FastApiMCP:
    """Create the memory MCP server and mount at /mcp/memory.

    Auto-discovers FastAPI endpoints tagged with "mcp-memory" and exposes
    them as MCP tools.
    """
    mcp_server = FastApiMCP(
        app,
        name="Turkcell Customer Memory MCP Server",
        description=(
            "Musteri etkilesim hafizasi — onceki konusmalari, tercihleri "
            "ve cozulmemis sorunlari takip eder"
        ),
        include_tags=["mcp-memory"],
    )

    mcp_server.mount(mount_path="/mcp/memory")

    logger.info("Customer Memory MCP server mounted at /mcp/memory")
    return mcp_server
