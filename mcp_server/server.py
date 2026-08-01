"""Commercial Bank enterprise MCP server (employee directory, service catalog, incidents)."""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from mcp_server.data_store import search_employees, search_incidents, search_services

mcp = MCPServer("commercial-bank-enterprise")


@mcp.tool(
    name="lookup_employee",
    description="Search the employee directory by name, email, department, or title.",
)
def lookup_employee(query: str) -> str:
    results = search_employees(query)
    return json.dumps({"query": query, "count": len(results), "employees": results}, indent=2)


@mcp.tool(
    name="lookup_service",
    description="Search the service catalog for ownership, on-call rotation, and dependencies.",
)
def lookup_service(query: str) -> str:
    results = search_services(query)
    return json.dumps({"query": query, "count": len(results), "services": results}, indent=2)


@mcp.tool(
    name="lookup_incident",
    description="Search operational incident records by ID, title, service, or status.",
)
def lookup_incident(query: str) -> str:
    results = search_incidents(query)
    return json.dumps({"query": query, "count": len(results), "incidents": results}, indent=2)


def create_server() -> MCPServer:
    """Return the configured MCP server instance."""
    return mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")
