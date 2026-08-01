"""LangChain tools backed by the enterprise MCP server."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.app.tools.mcp_client import call_mcp_tool


class MCPQueryInput(BaseModel):
    query: str = Field(..., description="Search query for the enterprise data source")


def create_mcp_tools() -> list[StructuredTool]:
    async def lookup_employee(query: str) -> str:
        return await call_mcp_tool("lookup_employee", {"query": query})

    async def lookup_service(query: str) -> str:
        return await call_mcp_tool("lookup_service", {"query": query})

    async def lookup_incident(query: str) -> str:
        return await call_mcp_tool("lookup_incident", {"query": query})

    return [
        StructuredTool.from_function(
            coroutine=lookup_employee,
            name="lookup_employee",
            description="MCP: search employee directory (name, email, department, title).",
            args_schema=MCPQueryInput,
        ),
        StructuredTool.from_function(
            coroutine=lookup_service,
            name="lookup_service",
            description="MCP: search service catalog for owners, on-call rotations, dependencies.",
            args_schema=MCPQueryInput,
        ),
        StructuredTool.from_function(
            coroutine=lookup_incident,
            name="lookup_incident",
            description="MCP: search incident records by ID, title, service, or status.",
            args_schema=MCPQueryInput,
        ),
    ]
