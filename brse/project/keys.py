"""Store an API key for brse-toolkit outside every project, typed hidden.

Usage (in your own terminal, not in the chat):  python3 brse.py set-key OPENAI_API_KEY
Writes ~/.config/brse-toolkit/secrets.env (permissions 600). The key is never
echoed and never stored in a workspace. Remove a key: run again and press Enter.
"""
import sys
import getpass
import os

from brse import config as brse_config


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].replace("_", "").isalnum():
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    name = sys.argv[1]
    value = getpass.getpass(f"{name} (input hidden, Enter to remove): ").strip()
    f = brse_config.secrets_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    lines = [l for l in (f.read_text(encoding="utf-8").splitlines() if f.is_file() else [])
             if l.partition("=")[0].strip() != name]
    if value:
        lines.append(f"{name}={value}")
    f.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    os.chmod(f, 0o600)
    print(f"{'saved' if value else 'removed'} {name} in {f}")

