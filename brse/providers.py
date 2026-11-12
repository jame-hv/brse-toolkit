"""HTTP calls to model providers (OpenAI chat completions), shared by review and translation."""
import json
import os
import urllib.error
import urllib.request

from brse import config as brse_config

OPENAI_URL = os.environ.get("BRSE_OPENAI_URL", "https://api.openai.com/v1/chat/completions")


def post_json(url: str, payload: dict, headers: dict, timeout=120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")


def openai_chat(messages: list, config: dict, timeout=120) -> str:
    """LookupError when the key or providers.openai.model is not set."""
    p = config.get("providers", {}).get("openai", {})
    key, model = brse_config.secret(p.get("api_key_env", "OPENAI_API_KEY")), p.get("model")
    if not key or not model:
        raise LookupError(f"needs env var {p.get('api_key_env')} and providers.openai.model")
    out = post_json(OPENAI_URL, {"model": model, "messages": messages}, {"Authorization": f"Bearer {key}"}, timeout)
    return out["choices"][0]["message"]["content"].strip()
