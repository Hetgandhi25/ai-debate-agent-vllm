"""Quick check that vLLM is reachable and the model responds.

Run from the project folder (with venv activated):

    py test_vllm.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

def main() -> int:
    """Test connectivity to the vLLM API and return an exit code."""
    base_url = os.getenv("VLLM_BASE_URL", "").strip()
    api_key = os.getenv("VLLM_API_KEY", "EMPTY").strip()
    model = os.getenv("VLLM_MODEL", "").strip()

    if not base_url or "<MY-VLLM-IP>" in base_url:
        print("FAIL: Set a real VLLM_BASE_URL in .env (e.g. http://127.0.0.1:8000/v1).")
        return 1
    if not model or "<MY_MODEL_NAME>" in model:
        print("FAIL: Set a real VLLM_MODEL in .env.")
        return 1

    try:
        from openai import OpenAI, APIConnectionError, APITimeoutError
    except ImportError:
        print("FAIL: Install dependencies: pip install -r requirements.txt")
        return 1

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    print(f"Testing vLLM API at {base_url}\n")
    failures = 0

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=10,
            timeout=10,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        text = (response.choices[0].message.content or "").strip()
        print(f"OK   Model: {model}")
        print(f"     -> {text[:80]}\n")
    except APIConnectionError as exc:
        failures += 1
        print(f"FAIL Connection Error: Could not connect to {base_url}")
        print(f"     -> {exc}")
    except APITimeoutError as exc:
        failures += 1
        print(f"FAIL Timeout: Connection to {base_url} timed out")
        print(f"     -> {exc}")
    except Exception as exc:
        failures += 1
        detail = str(exc).strip() or type(exc).__name__
        if exc.__cause__ and str(exc.__cause__) not in detail:
            detail = f"{detail} - {exc.__cause__}"
        print(f"FAIL Model: {model}")
        print(f"     -> {type(exc).__name__}: {detail}\n")

    if failures:
        print(f"{failures} error(s) occurred. Check VLLM_BASE_URL, VLLM_API_KEY and VLLM_MODEL.")
        return 1

    print("The model responded. You can run: py app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
