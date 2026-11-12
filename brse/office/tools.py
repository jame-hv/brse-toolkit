"""Find the office CLI the config lists, run tools, LibreOffice helpers."""
import shutil
import subprocess
import tempfile
from pathlib import Path


KIND = {".xlsx": "xlsx", ".xlsm": "xlsx", ".docx": "docx", ".pptx": "pptx",
        ".png": "image", ".jpg": "image", ".jpeg": "image"}


def kind_of(path: Path) -> str:
    k = KIND.get(path.suffix.lower())
    if not k:
        raise ValueError(f"unsupported file type: {path.suffix}")
    return k


def find_cli(kind: str, config: dict):
    """(cli name, path) of the first available office CLI for this kind, else (None, reason)."""
    tools = config.get("tools", {})
    tried = []
    for name in tools.get("office_order", {}).get(kind, []):
        if name == "python":
            break
        p = tools.get("paths", {}).get(name)
        p = p if p and Path(p).is_file() else shutil.which(name)
        if p:
            return name, p
        tried.append(name)
    return None, f"no office CLI found for .{kind} (tried: {', '.join(tried) or 'none configured'})"


def run(args, timeout=300) -> subprocess.CompletedProcess:
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-500:] or f"exit {r.returncode}")
    return r


def soffice():
    return shutil.which("soffice") or shutil.which("libreoffice")


def pdf_to_pngs(pdf: Path, out_dir: Path, stem: str) -> list:
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm not installed (poppler-utils)")
    run(["pdftoppm", "-png", "-r", "110", pdf, out_dir / stem])
    return sorted(str(p) for p in out_dir.glob(f"{stem}*.png"))


def render_with_libreoffice(path: Path, out_dir: Path) -> list:
    exe = soffice()
    if not exe:
        raise RuntimeError("LibreOffice not installed")
    if not shutil.which("pdftoppm"):  # no poppler: LibreOffice writes one PNG (the active sheet / first page)
        run([exe, "--headless", "--convert-to", "png", "--outdir", out_dir, path], timeout=240)
        return sorted(str(p) for p in Path(out_dir).glob(f"{path.stem}*.png"))
    with tempfile.TemporaryDirectory() as tmp:
        run([exe, "--headless", "--convert-to", "pdf", "--outdir", tmp, path], timeout=240)
        pdf = Path(tmp) / (path.stem + ".pdf")
        return pdf_to_pngs(pdf, out_dir, path.stem)


