"""Security package (auth, RBAC, guardrails)."""

from backend.app.security.guardrails import validate_answer_guardrails
from backend.app.security.models import CurrentUser
from backend.app.security.prompt_injection import check_user_input, wrap_untrusted_document
from backend.app.security.rbac import ROLE_PERMISSIONS, can_use_tool, normalize_role
from backend.app.security.rate_limit import TokenBucketRateLimiter
from backend.app.security.tool_validation import validate_tool_call

__all__ = [
    "CurrentUser",
    "ROLE_PERMISSIONS",
    "TokenBucketRateLimiter",
    "can_use_tool",
    "check_user_input",
    "normalize_role",
    "validate_answer_guardrails",
    "validate_tool_call",
    "wrap_untrusted_document",
]
