from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANTHROPIC_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"


def extract_text(content: object) -> str:
    if not isinstance(content, list):
        return ""
    return "".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark one short text-only request through the Anthropic-compatible API."
    )
    parser.add_argument("--repeat", type=int, default=1, help="Number of sequential requests.")
    parser.add_argument("--timeout", type=int, default=None, help="Per-request timeout in seconds.")
    parser.add_argument("--model", default=None, help="Temporarily override MODEL_NAME from .env.")
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
    model = args.model or os.getenv("MODEL_NAME", "")
    timeout = args.timeout or int(os.getenv("REQUEST_TIMEOUT", "300"))

    if not api_key:
        raise ValueError("API_KEY is required in .env")
    if not model:
        raise ValueError("MODEL_NAME is required in .env")

    endpoint = f"{base_url}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model,
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly: OK",
            }
        ],
        "thinking": {"type": "disabled"},
    }

    print(
        json.dumps(
            {
                "protocol": "anthropic-compatible",
                "base_host": urlparse(base_url).netloc,
                "model": model,
                "thinking": False,
                "max_tokens": 10,
                "timeout_seconds": timeout,
                "repeat": args.repeat,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    elapsed_values: list[float] = []
    for run_index in range(1, args.repeat + 1):
        started = time.perf_counter()
        response: requests.Response | None = None
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            elapsed = time.perf_counter() - started
            error_body = response.text[:1000] if response is not None else ""
            print(
                json.dumps(
                    {
                        "run": run_index,
                        "elapsed_seconds": round(elapsed, 2),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "response_body": error_body,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            sys.exit(1)

        elapsed = time.perf_counter() - started
        elapsed_values.append(elapsed)
        content = data.get("content")
        has_thinking = any(
            isinstance(block, dict) and block.get("type") == "thinking"
            for block in content
        ) if isinstance(content, list) else False

        print(
            json.dumps(
                {
                    "run": run_index,
                    "elapsed_seconds": round(elapsed, 2),
                    "content": extract_text(content),
                    "stop_reason": data.get("stop_reason"),
                    "usage": data.get("usage"),
                    "thinking_content_present": has_thinking,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    if len(elapsed_values) > 1:
        print(
            json.dumps(
                {
                    "summary": {
                        "runs": len(elapsed_values),
                        "average_seconds": round(statistics.mean(elapsed_values), 2),
                        "min_seconds": round(min(elapsed_values), 2),
                        "max_seconds": round(max(elapsed_values), 2),
                    }
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
