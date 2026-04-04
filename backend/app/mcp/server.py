"""MCP server setup — mounts onto the existing FastAPI app."""

import logging

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

logger = logging.getLogger(__name__)


def create_and_mount_mcp(app: FastAPI) -> FastApiMCP:
    """Create an MCP server and mount it.

    Auto-discovers FastAPI endpoints tagged with "mcp" and exposes them
    as MCP tools. The MCP endpoint becomes available at ``/mcp`` for
    external clients (Claude Desktop, Cursor, etc.) via Streamable HTTP.
    """
    mcp_server = FastApiMCP(
        app,
        name="Turkcell AI-Gen MCP Server",
        description="Turkcell musteri oneri ve analiz araclari — kisisellestirilmis tarife/paket onerisi, churn riski, kullanim analizi, pazar karsilastirma",
        include_tags=["mcp"],
    )

    mcp_server.mount()

    logger.info("MCP server mounted at /mcp")
    return mcp_server
