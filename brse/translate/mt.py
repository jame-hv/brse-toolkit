"""Machine-translate a text file as the base layer before Claude post-edits it.

Usage: brse.py mt <text_file> --to ja|vi|en [--from ja|vi|en] [project_dir]
Tries config.translation.engine_order:
  deepl  → DeepL API; key in the env var named by providers.deepl.api_key_env
           (keys ending in ":fx" use the free endpoint)
  openai → Chat Completions; needs providers.openai.model + its key env var
  claude → no machine engine: stop, provider "none" (Claude translates alone
           and must say so)
Prints {"engine", "translation", "tried": [...]}. Glossary terms are enforced
afterwards by the translate skill (brse.py check-glossary), not here.
"""
import sys
import json
import os
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.providers import openai_chat, post_json

DEEPL_TARGET = {"ja": "JA", "vi": "VI", "en": "EN-US"}
DEEPL_SOURCE = {"ja": "JA", "vi": "VI", "en": "EN"}
LANG_NAME = {"ja": "Japanese", "vi": "Vietnamese", "en": "English"}


def deepl(text, src, dst, config):
    key = brse_config.secret(config.get("providers", {}).get("deepl", {}).get("api_key_env", "DEEPL_API_KEY"))
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
    instruction = (f"Translate the user's text {'from ' + LANG_NAME[src] + ' ' if src else ''}into "
                   f"{LANG_NAME[dst]}. Keep IDs, codes, numbers, names and line breaks unchanged. "
                   "Output only the translation.")
    return openai_chat([{"role": "system", "content": instruction}, {"role": "user", "content": text}], config)


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
            opts[flag] = take(args, flag)
    if not args or opts.get("--to") not in DEEPL_TARGET or opts.get("--from", "ja") not in DEEPL_SOURCE:
        print("usage: brse.py mt <text_file> --to ja|vi|en [--from ja|vi|en] [project_dir]", file=sys.stderr)
        sys.exit(2)
    text = Path(args[0]).read_text(encoding="utf-8")
    _, config = brse_config.workspace(args[1] if len(args) > 1 else ".")
    print(json.dumps(translate(text, opts.get("--from"), opts["--to"], config), ensure_ascii=False, indent=2))

