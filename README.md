# size‑cmp

A lightweight tool to compare the size of two directories or files.

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/youruser/size-cmp.git
cd size-cmp

# Install dependencies (ruff, typer, flask, etc.)
python -m pip install -r requirements.txt
```

> **Note**: The repository already contains a `deps/` directory with bundled binaries (`dust`, `file`, `size`). The installer automatically adds this directory to `PATH` at runtime, so no extra system‑wide installation is required.

---

## 🚀 Quick start (Web UI)

```bash
# Run the web server (default host 0.0.0.0, port 5002)
size-cmp web /path/to/dirA /path/to/dirB
```

Open your browser and navigate to `http://localhost:5002`. The UI displays a tree view of the two directories, colour‑coded differences, and on‑demand file‑detail comparison.

### Options

| Option | Description |
|--------|-------------|
| `--host` | Bind address (default: `0.0.0.0`) |
| `--port` | Port number (default: `5002`) |
| `--debug` | Enable Flask debug mode |

---

## 💻 CLI usage (top command)

The tool provides a `top` sub‑command that lists the biggest differences between two directories.

```bash
# Show the top 10 biggest differences
size-cmp top /path/to/dirA /path/to/dirB -n 10

# Output as JSON (useful for scripts)
size-cmp top /path/to/dirA /path/to/dirB -n 10 --json
```

### Options

| Option | Description |
|--------|-------------|
| `-n`, `--top` | Number of entries to display (default: 10) |
| `--json` | Print a machine‑readable JSON object instead of a table |
| `--host` / `--port` | Same as the web command – only needed when you also want to start the web UI from the same invocation |

---

## 🛠️ Advanced configuration

- **Binary dependencies** – The `deps/` folder contains the required binaries (`dust`, `file`, `size`). They are automatically added to `PATH` when `app.py` starts, so the tool works on any Linux host without installing these utilities globally.
- **Git metadata** – The repository’s Git author/committer information has been normalised to `skyfire <skyfireitdiy@hotmail.com>`.

---

## 📚 License

MIT License – see the `LICENSE` file for details.
