"""Pydantic validation for agent tool invocations before execution."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from backend.app.tools.knowledge_search import KnowledgeSearchInput
from backend.app.tools.mcp_tools import MCPQueryInput
from backend.app.tools.python_analysis import ALLOWED_OPERATIONS, PythonAnalysisInput


def validate_tool_call(tool_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate tool arguments with Pydantic schemas.

    Returns (ok, error_message).
    """
    try:
        if tool_name == "knowledge_search":
            KnowledgeSearchInput.model_validate(args)
        elif tool_name == "python_analysis":
            validated = PythonAnalysisInput.model_validate(args)
            if validated.operation not in ALLOWED_OPERATIONS:
                return False, f"Operation '{validated.operation}' is not permitted"
            if validated.records_json:
                records = json.loads(validated.records_json)
                if not isinstance(records, list):
                    return False, "records_json must decode to a JSON array"
                if len(records) > 100:
                    return False, "records_json exceeds maximum of 100 records"
        elif tool_name.startswith("lookup_"):
            MCPQueryInput.model_validate(args)
        else:
            return False, f"Unknown tool: {tool_name}"
    except PydanticValidationError as exc:
        return False, str(exc.errors()[0].get("msg", exc))
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON in tool args: {exc}"
    return True, None
