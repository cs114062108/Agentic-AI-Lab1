from __future__ import annotations

import argparse
import os
import sys

from openai import OpenAI


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "qwen2.5:3b"),
        help="API model name, such as qwen2.5:3b, qwen2.5:7b, or llama3.1:8b.",
    )
    args = parser.parse_args()

    try:
        client = OpenAI(
            base_url=os.getenv(
                "LLM_BASE_URL", "http://127.0.0.1:8000/v1"
            ),
            api_key=os.getenv("LLM_API_KEY", "classroom-internal"),
            timeout=float(os.getenv("LLM_TIMEOUT", "120")),
            max_retries=0,
        )

        response = client.chat.completions.create(
            model=args.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: API works"},
            ],
            temperature=0,
            max_tokens=32,
            stream=False,
        )
    except Exception as exc:
        print(
            f"API call failed ({type(exc).__name__}).",
            file=sys.stderr,
        )
        print(
            "Check that you have activated the course Python environment, "
            "selected an available model, and used the correct API base URL.",
            file=sys.stderr,
        )
        print(
            "If the request timed out, wait briefly and try again.",
            file=sys.stderr,
        )
        return 1

    print(f"Model: {args.model}")
    print(response.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
