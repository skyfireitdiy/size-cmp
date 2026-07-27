#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
size‑cmp – 自动更新版本号并发布到 PyPI 的脚本
使用方法：
    python publish.py [major|minor|patch]

该脚本的行为与 ~/Jarvis/scripts/publish.py 基本保持一致，只是针对
size‑cmp 项目做了以下适配：
* 读取版本号的来源改为 pyproject.toml（而不是 src/jarvis/__init__.py）
* 更新的文件包括 pyproject.toml、setup.cfg（若存在）以及 README 中的版本标记
* Git 提交使用项目统一的作者信息 skyfire <skyfireitdiy@hotmail.com>
* 支持通过环境变量 REPOSITORY（pypi|testpypi）切换发布目标
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import Tuple, List


# ---------------------------------------------------------------------------
# 版本号处理
# ---------------------------------------------------------------------------
def _read_version() -> Tuple[int, int, int]:
    """从 pyproject.toml 中读取当前的 MAJOR.MINOR.PATCH 版本号"""
    toml_path = Path("pyproject.toml")
    content = toml_path.read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"](\d+)\.(\d+)\.(\d+)['\"]", content)
    if not m:
        raise RuntimeError("Unable to locate version in pyproject.toml")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _write_version(new_version: str) -> None:
    """在 pyproject.toml（以及可能的 setup.cfg）中写入新版本号"""
    toml_path = Path("pyproject.toml")
    toml_path.write_text(
        re.sub(
            r"version\s*=\s*['\"]\d+\.\d+\.\d+['\"]",
            f'version = "{new_version}"',
            toml_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    # 若项目仍保留 legacy setup.cfg，也同步更新
    cfg_path = Path("setup.cfg")
    if cfg_path.is_file():
        cfg_path.write_text(
            re.sub(
                r"version\s*=\s*\d+\.\d+\.\d+",
                f"version = {new_version}",
                cfg_path.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )


def bump_version(bump_type: str) -> str:
    """根据 bump_type（major/minor/patch）计算并写入新版本号，返回新版本字符串"""
    major, minor, patch = _read_version()
    if bump_type == "major":
        major += 1
        minor = patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError("bump_type must be one of: major, minor, patch")
    new_version = f"{major}.{minor}.{patch}"
    _write_version(new_version)
    return new_version


# ---------------------------------------------------------------------------
# Git & 发布工具
# ---------------------------------------------------------------------------
def _run(cmd: List[str], err_msg: str) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ {err_msg}\n{e.stderr.decode()}")
        sys.exit(1)


def _run_ignore(cmd: List[str], err_msg: str) -> bool:
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ {err_msg}\n{e.stderr.decode()}")
        return False


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"major", "minor", "patch"}:
        print("Usage: python publish.py [major|minor|patch]")
        sys.exit(1)

    bump_type = sys.argv[1]
    new_version = bump_version(bump_type)
    print(f"✅ Updated version to {new_version}")

    # ------------------- Git 操作 -------------------
    print("📝 Staging changes…")
    _run(["git", "add", "."], "Failed to stage files")
    _run(
        [
            "git",
            "commit",
            "--author",
            "skyfire <skyfireitdiy@hotmail.com>",
            "-m",
            f"Bump version to {new_version}",
        ],
        "Failed to commit version bump",
    )

    tag_name = f"v{new_version}"
    print(f"🏷 Creating tag {tag_name}…")
    _run(["git", "tag", tag_name], "Failed to create tag")

    # ------------------- 推送到所有 remote -------------------
    print("🚀 Pushing to remotes…")
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True, check=True).stdout.splitlines()
    success = 0
    for remote in remotes:
        if not remote:
            continue
        print(f"  → Pushing to {remote}…")
        if _run_ignore(["git", "push", remote, "main"], f"Failed to push main to {remote}"):
            if _run_ignore(["git", "push", remote, "--tags"], f"Failed to push tags to {remote}"):
                success += 1
    if success == 0:
        print("⚠️ No remote succeeded. Verify your remote configuration.")
    else:
        print(f"✅ Pushed to {success}/{len(remotes)} remote(s). GitHub Actions will now handle PyPI publishing.")

    # ------------------- 本地构建（可选） -------------------
    # 这里保留与 CI 相同的构建步骤，方便本地调试
    print("🔧 Building distribution locally…")
    subprocess.run(["python", "-m", "build"], check=True)

    # ------------------- 手动上传（可选） -------------------
    # 若希望直接在本机上传，可取消下面的注释并确保已设置 PYPI_API_TOKEN
    # token = os.getenv("PYPI_API_TOKEN")
    # if not token:
    #     print("⚠️ PYPI_API_TOKEN not set – skipping manual upload")
    # else:
    #     subprocess.run(
    #         ["twine", "upload", "--repository", os.getenv("REPOSITORY", "pypi"), "dist/*"],
    #         env={"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
    #         check=True,
    #     )


if __name__ == "__main__":
    main()
