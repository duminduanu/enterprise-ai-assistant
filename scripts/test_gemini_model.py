#!/usr/bin/env python3
"""Verify the configured Gemini chat model is reachable with the current API key."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# Fallbacks if the primary model is unavailable to new accounts (see Gemini deprecations).
FALLBACK_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
)


def test_model(api_key: str, model: str) -> tuple[int, str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = httpx.post(
        url,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": "Reply with exactly: OK"}]}]},
        timeout=60.0,
    )
    return response.status_code, response.text[:400]


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set in .env")
        sys.exit(1)

    configured = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
    models = [configured, *[m for m in FALLBACK_MODELS if m != configured]]

    print(f"Testing models with key ending ...{api_key[-4:]}")
    for model in models:
        status, body = test_model(api_key, model)
        print(f"\n{model}: HTTP {status}")
        if status == 200:
            print("SUCCESS — use this model in LLM_MODEL")
            if model != configured:
                print(f"Update .env: LLM_MODEL={model}")
            sys.exit(0)
        print(body)

    print("\nNo working chat model found. Check AI Studio rate limits for gemini-3.x models.")
    sys.exit(1)


if __name__ == "__main__":
    main()
