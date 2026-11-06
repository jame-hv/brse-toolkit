#!/usr/bin/env python3
"""Machine-translate a text file as the base layer before Claude post-edits it.

Usage: mt.py <text_file> --to ja|vi|en [--from ja|vi|en] [project_dir]
Tries config.translation.engine_order:
  deepl  → DeepL API; key in the env var named by providers.deepl.api_key_env
           (keys ending in ":fx" use the free endpoint)
  openai → Chat Completions; needs providers.openai.model + its key env var
  claude → no machine engine: stop, provider "none" (Claude translates alone
           and must say so)
Prints {"engine", "translation", "tried": [...]}. Glossary terms are enforced
afterwards by the translate skill (check-glossary.py), not here.
"""
import sys

sys.dont_write_bytecode = True
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import brse_common

DEEPL_TARGET = {"ja": "JA", "vi": "VI", "en": "EN-US"}
DEEPL_SOURCE = {"ja": "JA", "vi": "VI", "en": "EN"}
LANG_NAME = {"ja": "Japanese", "vi": "Vietnamese", "en": "English"}
OPENAI_URL = os.environ.get("BRSE_OPENAI_URL", "https://api.openai.com/v1/chat/completions")


def post_json(url, payload, headers, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")


def deepl(text, src, dst, config):
    key = brse_common.secret(config.get("providers", {}).get("deepl", {}).get("api_key_env", "DEEPL_API_KEY"))
    if not key:
        raise LookupError("no DeepL key in the environment")
    url = os.environ.get("BRSE_DEEPL_URL") or (
        "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate")
    payload = {"text": [text], "target_lang": DEEPL_TARGET[dst]}
    if src:
        payload["source_lang"] = DEEPL_SOURCE[src]
    out = post_json(url, payload, {"Authorization": f"DeepL-Auth-Key {key}"})
    return out["translations"][0]["text"]


def openai(text, src, dst, config):
    p = config.get("providers", {}).get("openai", {})
    key, model = brse_common.secret(p.get("api_key_env", "OPENAI_API_KEY")), p.get("model")
    if not key or not model:
        raise LookupError(f"needs env var {p.get('api_key_env')} and providers.openai.model")
    instruction = (f"Translate the user's text {'from ' + LANG_NAME[src] + ' ' if src else ''}into "
                   f"{LANG_NAME[dst]}. Keep IDs, codes, numbers, names and line breaks unchanged. "
                   "Output only the translation.")
    out = post_json(OPENAI_URL, {"model": model, "messages": [
        {"role": "system", "content": instruction}, {"role": "user", "content": text}]},
        {"Authorization": f"Bearer {key}"})
    return out["choices"][0]["message"]["content"].strip()


def translate(text, src, dst, config) -> dict:
    tried = []
    for engine in config.get("translation", {}).get("engine_order", []):
        if engine == "claude":
            tried.append({"engine": engine, "skipped": "no machine engine — Claude translates alone"})
            break
        fn = {"deepl": deepl, "openai": openai}.get(engine)
        if fn is None:
            tried.append({"engine": engine, "skipped": "unknown engine"})
            continue
        try:
            return {"engine": engine, "translation": fn(text, src, dst, config), "tried": tried}
        except LookupError as e:
            tried.append({"engine": engine, "skipped": str(e)})
        except Exception as e:
            tried.append({"engine": engine, "error": f"{type(e).__name__}: {str(e)[:300]}"})
    return {"engine": "none", "translation": None, "tried": tried}


def main() -> None:
    args = sys.argv[1:]
    opts = {}
    for flag in ("--to", "--from"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if not args or opts.get("--to") not in DEEPL_TARGET or opts.get("--from", "ja") not in DEEPL_SOURCE:
        print("usage: mt.py <text_file> --to ja|vi|en [--from ja|vi|en] [project_dir]", file=sys.stderr)
        sys.exit(2)
    text = Path(args[0]).read_text(encoding="utf-8")
    _, config = brse_common.workspace(args[1] if len(args) > 1 else ".")
    print(json.dumps(translate(text, opts.get("--from"), opts["--to"], config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
