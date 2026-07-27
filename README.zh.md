# size‑cmp

一个轻量级工具，用于比较两个目录或文件的大小。

---

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/youruser/size-cmp.git
cd size-cmp

# 安装依赖（ruff、typer、flask 等）
python -m pip install -r requirements.txt
```

> **注意**：仓库已包含 `deps/` 目录，内含 `dust`、`file`、`size` 等二进制文件。运行时会自动将该目录加入 `PATH`，无需在系统范围内额外安装这些工具。

---

## 🚀 快速开始（Web UI）

```bash
# 启动 Web 服务（默认绑定 0.0.0.0，端口 5002）
size-cmp web /path/to/dirA /path/to/dirB
```

在浏览器打开 `http://localhost:5002`，即可看到树形结构的对比页面，颜色标记差异，并支持按需加载文件详情。

### 参数说明

| 参数      | 说明                       |
| --------- | -------------------------- |
| `--host`  | 绑定地址（默认 `0.0.0.0`） |
| `--port`  | 端口号（默认 `5002`）      |
| `--debug` | 开启 Flask 调试模式        |

---

## 💻 CLI 使用（top 子命令）

`top` 子命令用于列出两个目录之间最大的差异。

```bash
# 显示前 10 条差异
size-cmp top /path/to/dirA /path/to/dirB -n 10

# 以 JSON 输出（便于脚本处理）
size-cmp top /path/to/dirA /path/to/dirB -n 10 --json
```

### 参数说明

| 参数                | 说明                                              |
| ------------------- | ------------------------------------------------- |
| `-n`, `--top`       | 要显示的条目数量（默认 10）                       |
| `--json`            | 输出机器可读的 JSON 对象                          |
| `--host` / `--port` | 同 Web 命令的参数，仅在需要同时启动 Web UI 时使用 |

---

## 🛠️ 高级配置

- **二进制依赖**：`deps/` 目录下的 `dust`、`file`、`size` 会在 `app.py` 启动时自动加入 `PATH`，因此在任何 Linux 主机上均可直接使用。
- **Git 元信息**：仓库的提交作者已统一为 `skyfire <skyfireitdiy@hotmail.com>`。

---

## 🌐 国际化说明

- **English README**: [`README.md`](README.md)
- **中文 README**: 本文件 (`README.zh.md`)

---

## 📚 许可证

MIT 许可证 – 详见 `LICENSE` 文件。
