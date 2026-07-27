#!/usr/bin/env python3
"""Size Compare - Web-based recursive directory/file size comparison tool."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

# Add bundled deps to PATH
_DEPS_DIR = Path(__file__).parent / "deps"
if _DEPS_DIR.is_dir():
    os.environ["PATH"] = str(_DEPS_DIR) + os.pathsep + os.environ.get("PATH", "")

import typer  # noqa: E402
from flask import Flask, jsonify, render_template, request  # noqa: E402
from flask_cors import CORS  # noqa: E402

app = Flask(__name__)
CORS(app)

PATH_A: str = ""
PATH_B: str = ""


def parse_size(size_str: str) -> int:
    """Convert dust size string (e.g. '7.9G', '330M') to bytes."""
    if not size_str:
        return 0
    units = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    size_str = size_str.strip()
    for suffix, multiplier in units.items():
        if size_str.upper().endswith(suffix):
            try:
                return int(float(size_str[:-1]) * multiplier)
            except ValueError:
                return 0
    try:
        return int(size_str)
    except ValueError:
        return 0


def format_size(size_bytes: int) -> str:
    """Format bytes as 'raw_bytes (friendly)' e.g. '93512 (91.3 K)'."""
    if size_bytes == 0:
        return "0"
    raw = int(size_bytes)
    val = abs(raw)
    for unit in ["B", "K", "M", "G", "T", "P"]:
        if val < 1024 or unit == "P":
            friendly = f"{val} B" if unit == "B" else f"{val:.1f} {unit}"
            return f"{raw} ({friendly})"
        val /= 1024
    return f"{raw} ({val:.1f} P)"


def run_dust(path: str) -> dict:
    """Run dust -j on a path and return parsed JSON."""
    try:
        result = subprocess.run(["dust", "-j", "-o", "b", path], capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        json_start = output.find("{")
        if json_start >= 0:
            return json.loads(output[json_start:])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"Warning: dust failed for {path}: {e}", file=sys.stderr)
    return {"size": "0B", "name": os.path.basename(path), "children": []}


def is_elf_file(path: str) -> bool:
    """Check if a file is an ELF binary."""
    try:
        result = subprocess.run(["file", path], capture_output=True, text=True, timeout=10)
        return "ELF" in result.stdout
    except Exception:
        return False


def is_binary_file(path: str) -> bool:
    """Check if a file is a binary (non-text) file using heuristics."""
    try:
        # Read first 8KB and check for null bytes (reliable binary indicator)
        with open(path, "rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return True
        # No null bytes found - treat as text file
        return False
    except Exception:
        return False


def get_elf_size_info(path: str) -> dict:
    """Get ELF section sizes using the size command."""
    try:
        result = subprocess.run(["size", path], capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                return {
                    "text": int(parts[0]),
                    "data": int(parts[1]),
                    "bss": int(parts[2]),
                    "total": int(parts[3]),
                }
    except Exception as e:
        print(f"Warning: size failed for {path}: {e}", file=sys.stderr)
    return {}


def get_binwalk_info(path: str) -> list:
    """Get binwalk analysis for a binary file (only for files < 10MB)."""
    if not shutil.which("binwalk"):
        return [{"offset": "0", "hex": "0x0", "description": "binwalk not installed"}]
    try:
        if os.path.getsize(path) > 10 * 1024 * 1024:
            return [{"offset": "0", "hex": "0x0", "description": "File too large for binwalk analysis (>10MB)"}]
        result = subprocess.run(["binwalk", path], capture_output=True, text=True, timeout=30)
        entries = []
        for line in result.stdout.strip().split("\n"):
            if line and not line.startswith("DECIMAL") and not line.startswith("---"):
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    entries.append({"offset": parts[0], "hex": parts[1], "description": parts[2]})
        return entries
    except Exception as e:
        print(f"Warning: binwalk failed for {path}: {e}", file=sys.stderr)
    return []


def get_file_detail(path: str) -> dict:
    """Get detailed file info based on file type."""
    # Symlink: don't resolve, just report link size
    if os.path.islink(path):
        return {"type": "symlink", "size": os.lstat(path).st_size}
    if not os.path.isfile(path):
        return {"type": "missing", "size": 0}

    file_size = os.path.getsize(path)
    info: dict = {"type": "file", "size": file_size}

    if is_elf_file(path):
        info["type"] = "elf"
        info["elf_sections"] = get_elf_size_info(path)
    elif is_binary_file(path):
        info["type"] = "binary"
        info["binwalk"] = get_binwalk_info(path)

    return info


def compare_directories(path_a: str, path_b: str, sub_path: str = "") -> dict:
    """Compare two directories and return comparison data."""
    full_a = os.path.join(path_a, sub_path) if sub_path else path_a
    full_b = os.path.join(path_b, sub_path) if sub_path else path_b

    entries_a = set()
    entries_b = set()

    if os.path.isdir(full_a):
        entries_a = set(os.listdir(full_a))
    if os.path.isdir(full_b):
        entries_b = set(os.listdir(full_b))

    all_entries = sorted(entries_a | entries_b)

    results = []
    for name in all_entries:
        entry_a = os.path.join(full_a, name)
        entry_b = os.path.join(full_b, name)
        rel_path = os.path.join(sub_path, name) if sub_path else name

        in_a = name in entries_a
        in_b = name in entries_b

        # Symlinks: detect before isdir (isdir follows links)
        is_link_a = os.path.islink(entry_a) if in_a else False
        is_link_b = os.path.islink(entry_b) if in_b else False
        is_dir_a = os.path.isdir(entry_a) if in_a else False
        is_dir_b = os.path.isdir(entry_b) if in_b else False
        is_dir = is_dir_a or is_dir_b

        size_a = 0
        size_b = 0

        if is_dir:
            # Symlink dirs: use lstat for link size, don't follow with dust
            if in_a and is_dir_a:
                if is_link_a:
                    size_a = os.lstat(entry_a).st_size
                else:
                    dust_a = run_dust(entry_a)
                    size_a = parse_size(dust_a.get("size", "0B"))
            if in_b and is_dir_b:
                if is_link_b:
                    size_b = os.lstat(entry_b).st_size
                else:
                    dust_b = run_dust(entry_b)
                    size_b = parse_size(dust_b.get("size", "0B"))
        else:
            # Only get file size for the list view; details loaded on demand
            # Symlinks: use lstat to get link size, not target
            if in_a and is_link_a:
                size_a = os.lstat(entry_a).st_size
            elif in_a and os.path.isfile(entry_a):
                size_a = os.path.getsize(entry_a)
            if in_b and is_link_b:
                size_b = os.lstat(entry_b).st_size
            elif in_b and os.path.isfile(entry_b):
                size_b = os.path.getsize(entry_b)

        diff = size_a - size_b
        results.append(
            {
                "name": name,
                "path": rel_path,
                "is_dir": is_dir,
                "in_a": in_a,
                "in_b": in_b,
                "size_a": size_a,
                "size_b": size_b,
                "size_a_fmt": format_size(size_a),
                "size_b_fmt": format_size(size_b),
                "diff": diff,
                "diff_fmt": format_size(abs(diff)),
            }
        )

    # Sort: directories first, then by diff magnitude descending
    results.sort(key=lambda x: (not x["is_dir"], -abs(x["diff"])))

    root_size_a = sum(e["size_a"] for e in results)
    root_size_b = sum(e["size_b"] for e in results)

    return {
        "path_a": path_a,
        "path_b": path_b,
        "sub_path": sub_path,
        "entries": results,
        "root_size_a": root_size_a,
        "root_size_b": root_size_b,
        "root_size_a_fmt": format_size(root_size_a),
        "root_size_b_fmt": format_size(root_size_b),
    }


@app.route("/")
def index():
    """Render the main comparison page."""
    return render_template("index.html", path_a=PATH_A, path_b=PATH_B)


@app.route("/api/compare")
def api_compare():
    """API endpoint for comparison data."""
    sub_path = request.args.get("path", "")
    data = compare_directories(PATH_A, PATH_B, sub_path)
    return jsonify(data)


@app.route("/api/file_detail")
def api_file_detail():
    """API endpoint for detailed file info."""
    side = request.args.get("side", "a")
    rel_path = request.args.get("path", "")
    base = PATH_A if side == "a" else PATH_B
    full_path = os.path.join(base, rel_path) if rel_path else base
    detail = get_file_detail(full_path)
    detail["path"] = full_path
    return jsonify(detail)


def collect_all_files(path_a: str, path_b: str, sub_path: str = "") -> list[dict]:
    """Recursively collect all files (not dirs) from both sides."""
    full_a = os.path.join(path_a, sub_path) if sub_path else path_a
    full_b = os.path.join(path_b, sub_path) if sub_path else path_b

    entries_a = set(os.listdir(full_a)) if os.path.isdir(full_a) else set()
    entries_b = set(os.listdir(full_b)) if os.path.isdir(full_b) else set()

    files = []
    for name in sorted(entries_a | entries_b):
        entry_a = os.path.join(full_a, name)
        entry_b = os.path.join(full_b, name)
        rel_path = os.path.join(sub_path, name) if sub_path else name

        in_a, in_b = name in entries_a, name in entries_b
        is_link_a = os.path.islink(entry_a) if in_a else False
        is_link_b = os.path.islink(entry_b) if in_b else False
        is_dir_a = os.path.isdir(entry_a) if in_a else False
        is_dir_b = os.path.isdir(entry_b) if in_b else False

        # Recurse into real directories (not symlinks)
        if (is_dir_a and not is_link_a) or (is_dir_b and not is_link_b):
            files.extend(collect_all_files(path_a, path_b, rel_path))
            continue

        # File or symlink: collect size
        size_a, size_b = 0, 0
        if in_a and is_link_a:
            size_a = os.lstat(entry_a).st_size
        elif in_a and os.path.isfile(entry_a):
            size_a = os.path.getsize(entry_a)
        if in_b and is_link_b:
            size_b = os.lstat(entry_b).st_size
        elif in_b and os.path.isfile(entry_b):
            size_b = os.path.getsize(entry_b)

        files.append(
            {
                "path": rel_path,
                "size_a": size_a,
                "size_b": size_b,
                "diff": size_a - size_b,
            }
        )

    return files


cli = typer.Typer(help="Compare sizes of two files/directories via web UI")


@cli.command()
def web(
    path_a: Annotated[str, typer.Argument(help="First file or directory path")],
    path_b: Annotated[str, typer.Argument(help="Second file or directory path")],
    port: Annotated[int, typer.Option("--port", "-p", help="Web server port")] = 5000,
    host: Annotated[str, typer.Option("--host", help="Host to bind to")] = "0.0.0.0",
):
    global PATH_A, PATH_B
    pa = Path(path_a).resolve()
    pb = Path(path_b).resolve()
    if not pa.exists():
        typer.echo(f"Error: {pa} does not exist", err=True)
        raise typer.Exit(1)
    if not pb.exists():
        typer.echo(f"Error: {pb} does not exist", err=True)
        raise typer.Exit(1)
    PATH_A = str(pa)
    PATH_B = str(pb)

    typer.echo(f"Comparing:\n  A: {PATH_A}\n  B: {PATH_B}")
    typer.echo(f"Starting web server at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


@cli.command()
def top(
    path_a: Annotated[str, typer.Argument(help="First directory path")],
    path_b: Annotated[str, typer.Argument(help="Second directory path")],
    n: Annotated[int, typer.Option("--top", "-n", help="Top N files by change ratio")] = 10,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
):
    """Show top N files with highest change ratio (|diff| / total_size)."""
    import json

    pa = Path(path_a).resolve()
    pb = Path(path_b).resolve()
    if not pa.exists():
        typer.echo(f"Error: {pa} does not exist", err=True)
        raise typer.Exit(1)
    if not pb.exists():
        typer.echo(f"Error: {pb} does not exist", err=True)
        raise typer.Exit(1)

    if not json_output:
        typer.echo(f"Scanning {pa} vs {pb} ...")
    files = collect_all_files(str(pa), str(pb))
    total_a = sum(f["size_a"] for f in files)
    total_b = sum(f["size_b"] for f in files)
    total = max(total_a, total_b, 1)

    # Sort by |diff| / total descending
    files.sort(key=lambda f: -abs(f["diff"]))
    top_files = files[:n]

    if json_output:
        result = {
            "path_a": str(pa),
            "path_b": str(pb),
            "total_a": total_a,
            "total_b": total_b,
            "total_a_fmt": format_size(total_a),
            "total_b_fmt": format_size(total_b),
            "diff": total_a - total_b,
            "diff_fmt": format_size(total_a - total_b),
            "top_n": [
                {
                    "rank": i,
                    "path": f["path"],
                    "size_a": f["size_a"],
                    "size_a_fmt": format_size(f["size_a"]),
                    "size_b": f["size_b"],
                    "size_b_fmt": format_size(f["size_b"]),
                    "diff": f["diff"],
                    "diff_fmt": format_size(f["diff"]),
                    "ratio": round(abs(f["diff"]) / total * 100, 2),
                }
                for i, f in enumerate(top_files, 1)
            ],
        }
        typer.echo(json.dumps(result, indent=2))
        return

    # Table format
    typer.echo(f"\nTotal: A={format_size(total_a)}  B={format_size(total_b)}  Diff={format_size(total_a - total_b)}")
    typer.echo(f"{'Rank':<5} {'Ratio':>8} {'Diff':>16} {'Size A':>16} {'Size B':>16}  Path")
    typer.echo("-" * 90)
    for i, f in enumerate(top_files, 1):
        ratio = abs(f["diff"]) / total * 100
        diff_sign = "+" if f["diff"] > 0 else ""
        typer.echo(
            f"{i:<5} {ratio:>7.2f}% {diff_sign}{format_size(f['diff']):>15} "
            f"{format_size(f['size_a']):>16} {format_size(f['size_b']):>16}  {f['path']}"
        )


if __name__ == "__main__":
    cli()
