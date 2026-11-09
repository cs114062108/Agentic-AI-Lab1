from __future__ import annotations

import argparse
import os
import sys

import json

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.utils import Logger

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "qwen2.5:3b"),
        help="API model name, such as qwen2.5:3b, qwen2.5:7b, or llama3.1:8b.",
    )
    args = parser.parse_args()
    
    instructions = "You are a helpful assistant."
    prompt = "Reply with exactly: API works"
    
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": prompt},
    ]
    
    Logger.info(f"Enage chat with model [{args.model}], prompt: {prompt}")
    
    messages_str = json.dumps(messages, indent=2, ensure_ascii=False)
    print(messages_str)

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
            messages=messages,
            temperature=0,
            max_tokens=32,
            stream=False,
        )
        
        response_message = response.choices[0].message
        messages.append(response_message.model_dump(exclude_none=True))
    except Exception as exc:
        Logger.warning(
            f"API call failed ({type(exc).__name__})."
        )
        Logger.warning(
            "Check that you have activated the course Python environment, "
            "selected an available model, and used the correct API base URL."
        )
        Logger.warning(
            "If the request timed out, wait briefly and try again."
        )
        return 1

    Logger.info(f"Model: {args.model}")
    Logger.info("Got response:")
    print(response.choices[0].message.content)
    
    messages_str = json.dumps(messages, indent=2, ensure_ascii=False)
    print(messages_str)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
