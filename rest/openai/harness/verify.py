#!/usr/bin/env python3
"""Verify the Imposter OpenAI-compatible mock using the real OpenAI SDK.

This exercises the mock exactly as a downstream AI harness would: it points the
official `openai` client at the mock's base URL and checks that models, chat,
tool calling, streaming and embeddings all round-trip with the shapes the SDK
expects.

Usage:
    python verify.py                       # against http://localhost:8080/v1
    python verify.py --base-url http://localhost:3000/v1
    OPENAI_BASE_URL=... python verify.py

Exit code is 0 if every check passes, 1 otherwise, so it drops into CI.
"""
from __future__ import annotations

import argparse
import os
import sys

from openai import OpenAI

# The mock ignores the key, but the SDK insists on a non-empty one.
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-imposter-not-a-real-key")

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


class Checker:
    """Runs named checks, records outcomes and prints a running log."""

    def __init__(self) -> None:
        self.failures = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        marker = PASS if ok else FAIL
        line = f"  [{marker}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
        if not ok:
            self.failures += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", "http://localhost:8080/v1"),
        help="Base URL of the mock (default: http://localhost:8080/v1)",
    )
    args = parser.parse_args()

    print(f"Verifying OpenAI-compatible mock at {args.base_url}\n")
    client = OpenAI(base_url=args.base_url, api_key=API_KEY)
    c = Checker()

    # --- Models -----------------------------------------------------------
    print("models.list")
    model_ids = [m.id for m in client.models.list().data]
    c.check("returns a non-empty model list", bool(model_ids), ", ".join(model_ids))

    # --- Plain chat completion -------------------------------------------
    print("\nchat.completions.create")
    chat = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
    )
    choice = chat.choices[0]
    c.check("echoes the requested model", chat.model == "gpt-4o-mini", chat.model)
    c.check("finish_reason is 'stop'", choice.finish_reason == "stop")
    c.check("assistant returned content", bool(choice.message.content),
            (choice.message.content or "")[:60] + "…")

    # --- Tool calling -----------------------------------------------------
    print("\nchat.completions.create (tool calling)")
    tool_chat = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What's the weather in London?"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                },
            },
        }],
    )
    tchoice = tool_chat.choices[0]
    c.check("finish_reason is 'tool_calls'", tchoice.finish_reason == "tool_calls")
    tool_calls = tchoice.message.tool_calls or []
    c.check("assistant requested a tool call", len(tool_calls) == 1)
    if tool_calls:
        fn = tool_calls[0].function
        c.check("called get_weather with JSON arguments",
                fn.name == "get_weather" and fn.arguments.strip().startswith("{"),
                f"{fn.name}({fn.arguments})")

    # --- Streaming --------------------------------------------------------
    print("\nchat.completions.create (stream=True)")
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    )
    chunks = 0
    assembled = ""
    for chunk in stream:
        chunks += 1
        delta = chunk.choices[0].delta.content
        if delta:
            assembled += delta
    c.check("received multiple stream chunks", chunks > 1, f"{chunks} chunks")
    c.check("assembled a non-empty message", bool(assembled), repr(assembled))

    # --- Legacy completions ----------------------------------------------
    print("\ncompletions.create (legacy)")
    completion = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Once upon a time",
    )
    c.check("returned completion text", bool(completion.choices[0].text.strip()))

    # --- Embeddings -------------------------------------------------------
    print("\nembeddings.create")
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input="hello world",
    )
    vector = emb.data[0].embedding
    c.check("returned a numeric embedding vector",
            len(vector) > 0 and all(isinstance(x, float) for x in vector),
            f"{len(vector)} dimensions")

    # --- Summary ----------------------------------------------------------
    print()
    if c.failures:
        print(f"{FAIL}: {c.failures} check(s) failed")
        return 1
    print(f"{PASS}: all checks passed — the mock is OpenAI-compatible")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - surface any SDK/transport error clearly
        print(f"\n\033[31mERROR\033[0m: {exc}", file=sys.stderr)
        print("Is the mock running? Start it with `imposter up` in the parent "
              "directory, then re-run.", file=sys.stderr)
        sys.exit(2)
