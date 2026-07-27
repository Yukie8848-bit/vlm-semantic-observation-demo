from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark one short text-only request through the OpenAI-compatible API."
    )
    parser.add_argument("--repeat", type=int, default=1, help="Number of sequential requests.")
    parser.add_argument("--timeout", type=int, default=None, help="Per-request timeout in seconds.")
    parser.add_argument("--model", default=None, help="Temporarily override MODEL_NAME from .env.")
    parser.add_argument("--stream", action="store_true", help="Measure time to the first streamed token.")
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("API_KEY", "")
    base_url = os.getenv("BASE_URL", "")
    model = args.model or os.getenv("MODEL_NAME", "")
    timeout = args.timeout or int(os.getenv("REQUEST_TIMEOUT", "300"))

    if not api_key:
        raise ValueError("API_KEY is required in .env")
    if not base_url:
        raise ValueError("BASE_URL is required in .env")
    if not model:
        raise ValueError("MODEL_NAME is required in .env")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
    )

    print(
        json.dumps(
            {
                "protocol": "openai-compatible",
                "base_host": urlparse(base_url).netloc,
                "model": model,
                "thinking": False,
                "max_tokens": 10,
                "timeout_seconds": timeout,
                "repeat": args.repeat,
                "stream": args.stream,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    elapsed_values: list[float] = []
    for run_index in range(1, args.repeat + 1):
        started = time.perf_counter()
        try:
            request_options = {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "temperature": 0,
                "max_tokens": 10,
                "extra_body": {"enable_thinking": False},
                "timeout": timeout,
            }
            if args.stream:
                stream = client.chat.completions.create(
                    **request_options,
                    stream=True,
                    stream_options={"include_usage": True},
                )
            else:
                response = client.chat.completions.create(**request_options)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(
                json.dumps(
                    {
                        "run": run_index,
                        "elapsed_seconds": round(elapsed, 2),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            sys.exit(1)

        if args.stream:
            first_token_seconds: float | None = None
            request_id: str | None = None
            content_parts: list[str] = []
            reasoning_content_chars = 0
            finish_reason: str | None = None
            usage = None

            try:
                for chunk in stream:
                    request_id = request_id or chunk.id
                    if chunk.usage:
                        usage = chunk.usage.model_dump(mode="json")
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                    delta = choice.delta
                    reasoning_content = getattr(delta, "reasoning_content", None)
                    reasoning_content_chars += len(reasoning_content or "")
                    if delta.content:
                        if first_token_seconds is None:
                            first_token_seconds = time.perf_counter() - started
                        content_parts.append(delta.content)
            except Exception as exc:
                elapsed = time.perf_counter() - started
                print(
                    json.dumps(
                        {
                            "run": run_index,
                            "elapsed_seconds": round(elapsed, 2),
                            "first_token_seconds": (
                                round(first_token_seconds, 2)
                                if first_token_seconds is not None
                                else None
                            ),
                            "request_id": request_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                sys.exit(1)

            elapsed = time.perf_counter() - started
            elapsed_values.append(elapsed)
            print(
                json.dumps(
                    {
                        "run": run_index,
                        "elapsed_seconds": round(elapsed, 2),
                        "first_token_seconds": (
                            round(first_token_seconds, 2)
                            if first_token_seconds is not None
                            else None
                        ),
                        "request_id": request_id,
                        "content": "".join(content_parts),
                        "finish_reason": finish_reason,
                        "usage": usage,
                        "reasoning_content_present": reasoning_content_chars > 0,
                        "reasoning_content_chars": reasoning_content_chars,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue

        elapsed = time.perf_counter() - started
        elapsed_values.append(elapsed)
        choice = response.choices[0]
        reasoning_content = getattr(choice.message, "reasoning_content", None)
        usage = response.usage.model_dump(mode="json") if response.usage else None

        print(
            json.dumps(
                {
                    "run": run_index,
                    "elapsed_seconds": round(elapsed, 2),
                    "content": choice.message.content,
                    "finish_reason": choice.finish_reason,
                    "usage": usage,
                    "reasoning_content_present": bool(reasoning_content),
                    "reasoning_content_chars": len(reasoning_content or ""),
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
