#!/usr/bin/env python3
import os
import re
import json
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

# ===================== 配置区域=====================
# GitHub Pages 网页访问地址（仅打开页面用）
GH_PAGES_BASE = "https://l-yling.github.io/Thon-Market"
# RAW直链：固定读取main分支下的文件
RAW_BASE = "https://raw.githubusercontent.com/L-YLing/Thon-Market"

PACKAGES_DIR = Path("./packages")
OUT_INDEX = Path("./index.json")
OUT_HTML = Path("./index.html")
SCHEMA_VERSION = 1
DEFAULT_HOST_VERSION = ">=0.5.0"
REPO_ROOT = Path(__file__).resolve().parent
GH_BRANCH = "gh-pages"
MAIN_BRANCH = "main"
TMP_WT_NAME = "_gh_pages_tmp_wt"
WORKTREE_DIR = REPO_ROOT / TMP_WT_NAME
# ==============================================================

PKG_REGEX = re.compile(r"^(?P<id>.+)-(?P<ver>\d+\.\d+(?:\.\d+)*)\.zip$")

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thon Code 插件市场</title>
<style>
:root {
    --bg: #ffffff;
    --card-bg: #f8fafc;
    --text: #1e293b;
    --text-dim: #64748b;
    --border: #e2e8f0;
    --accent: #2563eb;
    --accent-light: #3b82f6;
    --shadow: 0 2px 12px rgba(0,0,0.06);
}
.dark {
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #f1f5f9;
    --text-dim: #94a3b8;
    --border: #334155;
    --accent: #3b82f6;
    --accent-light: #60a5fa;
    --shadow: 0 2px 12px rgba(0,0,0,0.25);
}
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: system-ui, -apple-system, sans-serif;
}
body {
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 2rem 1rem;
    transition: background 0.3s, color 0.3s;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
}
header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
}
h1 {
    font-size: 1.8rem;
    font-weight: 600;
}
.theme-btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    background: var(--card-bg);
    color: var(--text);
    border-radius: 8px;
    cursor: pointer;
    transition: 0.2s;
}
.theme-btn:hover {
    border-color: var(--accent);
}
.search-box {
    width: 100%;
    margin-bottom: 2rem;
}
#search {
    width: 100%;
    padding: 0.8rem 1rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--card-bg);
    color: var(--text);
    font-size: 1rem;
    outline: none;
    transition: border 0.2s;
}
#search:focus {
    border-color: var(--accent);
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.25rem;
}
.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow);
    transition: transform 0.2s, border-color 0.2s;
    padding: 1.25rem;
}
.card:hover {
    transform: translateY(-4px);
    border-color: var(--accent-light);
}
.card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.6rem;
}
.card-title {
    font-size: 1.15rem;
    font-weight: 600;
}
.version-tag {
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    border-radius: 6px;
    background: var(--border);
    color: var(--text-dim);
}
.desc {
    color: var(--text-dim);
    font-size: 0.9rem;
    margin: 0.8rem 0 1rem;
    line-height: 1.5;
}
.meta {
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-bottom: 1rem;
}
.download-btn {
    display: inline-block;
    text-decoration: none;
    padding: 0.6rem 1.2rem;
    background: var(--accent);
    color: white;
    border-radius: 8px;
    font-weight: 500;
    transition: opacity 0.2s;
}
.download-btn:hover {
    opacity: 0.85;
}
.empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 4rem 0;
    color: var(--text-dim);
    font-size: 1rem;
}
footer {
    margin-top: 4rem;
    text-align: center;
    color: var(--text-dim);
    font-size: 0.85rem;
}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Thon Code 插件市场</h1>
        <button class="theme-btn" id="toggleTheme">切换明暗模式</button>
    </header>
    <div class="search-box">
        <input id="search" placeholder="搜索插件名称、ID、描述..." type="text">
    </div>
    <div class="grid" id="pluginGrid"></div>
    <footer>
        <p>数据更新时间：<span id="updateTime"></span></p>
        <p>插件包存放于主分支 packages/ 目录，页面托管在 gh-pages</p>
    </footer>
</div>
<script>
// 明暗模式
const html = document.documentElement;
const toggleBtn = document.getElementById('toggleTheme');
function initTheme() {
    const saved = localStorage.getItem('market-theme');
    if (saved === 'dark') html.classList.add('dark');
}
toggleBtn.addEventListener('click', () => {
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    localStorage.setItem('market-theme', isDark ? 'dark' : 'light');
});
initTheme();
// HTML转义
function escapeHtml(s) {
    if (!s) return '';
    return String(s)
        .replaceAll('&','&amp;')
        .replaceAll('<','&lt;')
        .replaceAll('>','&gt;')
        .replaceAll('"','&quot;')
        .replaceAll("'",'&#39;');
}
// 渲染插件列表
let allPlugins = [];
const grid = document.getElementById('pluginGrid');
const searchInput = document.getElementById('search');
const timeSpan = document.getElementById('updateTime');
function render(list) {
    if (!list.length) {
        grid.innerHTML = '<div class="empty">未匹配到任何插件</div>';
        return;
    }
    grid.innerHTML = list.map(p => `
        <div class="card">
            <div class="card-head">
                <h3 class="card-title">${escapeHtml(p.name)}</h3>
                <span class="version-tag">v${escapeHtml(p.version)}</span>
            </div>
            <div class="meta">ID: ${escapeHtml(p.id)}</div>
            <p class="desc">${escapeHtml(p.description || '暂无描述')}</p>
            <a class="download-btn" href="${escapeHtml(p.package_url)}" target="_blank">下载 ZIP 包</a>
        </div>
    `).join('');
}
// 搜索过滤
function filterPlugins(keyword) {
    const kw = keyword.toLowerCase().trim();
    if (!kw) return allPlugins;
    return allPlugins.filter(p =>
        p.id.toLowerCase().includes(kw) ||
        p.name.toLowerCase().includes(kw) ||
        (p.description && p.description.toLowerCase().includes(kw))
    );
}
searchInput.addEventListener('input', e => {
    render(filterPlugins(e.target.value));
});
// 加载索引
fetch('index.json')
    .then(r => r.json())
    .then(data => {
        allPlugins = data.plugins || [];
        timeSpan.textContent = data.updated_at || '未知';
        render(allPlugins);
    })
    .catch(err => {
        grid.innerHTML = `<div class="empty">加载索引失败: ${escapeHtml(err.message)}</div>`;
    });
</script>
</body>
</html>
"""

def get_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_packages() -> List[Dict[str, Any]]:
    plugins = []
    if not PACKAGES_DIR.exists():
        print(f"[警告] 目录不存在: {PACKAGES_DIR}")
        return plugins
    files = sorted(os.listdir(PACKAGES_DIR))
    for fname in files:
        fpath = PACKAGES_DIR / fname
        if not fpath.is_file() or not fname.endswith(".zip"):
            continue
        match = PKG_REGEX.match(fname)
        if not match:
            print(f"[跳过] 文件名格式不匹配: {fname}")
            continue
        pid = match.group("id")
        pver = match.group("ver")
        zip_url = f"{RAW_BASE}/{MAIN_BRANCH}/packages/{fname}"
        sha256 = get_file_sha256(fpath)
        item = {
            "id": pid,
            "name": pid.replace("_", " ").title(),
            "version": pver,
            "author": "未知作者",
            "description": f"{pid} 插件，版本 {pver}",
            "package_url": zip_url,
            "package_sha256": sha256,
            "host_version": DEFAULT_HOST_VERSION,
            "requires": []
        }
        plugins.append(item)
        print(f"[识别] {pid} v{pver} | SHA256: {sha256[:12]}...")
    return plugins

def build_index(plugins: List[Dict[str, Any]]):
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index_data = {
        "version": SCHEMA_VERSION,
        "updated_at": now_utc,
        "plugins": plugins
    }
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(HTML_TPL)
    print(f"\n[完成] 生成索引: {OUT_INDEX}")
    print(f"[完成] 生成网页: {OUT_HTML}")
    print(f"[统计] 共 {len(plugins)} 个插件")
    return now_utc

def run_git(args: List[str], cwd: Optional[Path] = None, capture=False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LC_ALL"] = "en_US.UTF-8"
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = ["git"] + args
    run_kwargs = {"cwd": str(cwd) if cwd else REPO_ROOT, "env": env}
    if capture:
        run_kwargs["stdout"] = subprocess.PIPE
        run_kwargs["stderr"] = subprocess.PIPE
        proc = subprocess.run(cmd, **run_kwargs)
        out = proc.stdout.decode("utf-8", errors="replace")
        err = proc.stderr.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
    return subprocess.run(cmd, **run_kwargs)

def clean_old_worktree():
    wt_list = run_git(["worktree", "list"], capture=True)
    lines = wt_list.stdout.splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        wt_path = Path(parts[0])
        wt_branch = parts[1]
        if str(wt_path).endswith(TMP_WT_NAME):
            run_git(["worktree", "remove", "--force", str(wt_path)], capture=True)
            shutil.rmtree(wt_path, ignore_errors=True)
            run_git(["branch", "-D", wt_branch], capture=True)

def branch_exists(branch: str) -> bool:
    local = run_git(["rev-parse", "--verify", "--quiet", branch], capture=True)
    if local.returncode == 0:
        return True
    remote = run_git(["rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"], capture=True)
    return remote.returncode == 0

def push_main_branch(dry_run: bool, stamp: str):
    """自动提交并推送main分支"""
    print("\n==== 开始处理主分支main ====")
    # 检测变更
    status_res = run_git(["status", "--porcelain"], capture=True)
    changed = status_res.stdout.strip()
    if not changed:
        print("[main] 本地无文件变更，跳过提交推送")
        return True
    print(f"[main] 检测到变更文件，执行提交")
    # 添加全部变更
    run_git(["add", "."])
    commit_msg = f"市场更新 {stamp}\n自动生成index/index.html"
    commit = run_git(["commit", "-m", commit_msg], capture=True)
    if commit.returncode != 0:
        print(f"[main] 提交失败：{commit.stderr}")
        return False
    if dry_run:
        print("[main] 试运行模式，跳过推送origin/main")
        return True
    print(f"[main] 推送至 origin/{MAIN_BRANCH}")
    push = run_git(["push", "origin", MAIN_BRANCH], capture=True)
    if push.returncode != 0:
        print(f"[main] 推送失败：{push.stderr}")
        return False
    print("[main] 推送完成")
    return True

def deploy_gh_pages(dry_run: bool):
    clean_old_worktree()
    WORKTREE_DIR.mkdir(exist_ok=True, parents=True)
    has_branch = branch_exists(GH_BRANCH)

    if has_branch:
        print(f"\n[Git] 检出已有 {GH_BRANCH} 分支")
        run_git(["fetch", "origin", GH_BRANCH])
        run_git(["worktree", "add", str(WORKTREE_DIR), GH_BRANCH])
    else:
        print(f"\n[Git] 创建全新孤儿分支 {GH_BRANCH}")
        run_git(["worktree", "--orphan", "-b", GH_BRANCH, str(WORKTREE_DIR)])

    # 修复：变量名统一为 WORKTREE_DIR
    if WORKTREE_DIR.exists() and (WORKTREE_DIR / ".git").exists():
        run_git(["rm", "-rf", "--ignore-unmatch", "."], cwd=WORKTREE_DIR, capture=True)
        for entry in os.listdir(WORKTREE_DIR):
            ep = WORKTREE_DIR / entry
            if ep.name == ".git":
                continue
            if ep.is_dir():
                shutil.rmtree(ep)
            else:
                ep.unlink()
    else:
        print("[警告] worktree目录未正常生成，跳过清空")

    (WORKTREE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copy2(OUT_INDEX, WORKTREE_DIR / OUT_INDEX.name)
    shutil.copy2(OUT_HTML, WORKTREE_DIR / OUT_HTML.name)
    print("[Git] 仅复制 index.json / index.html 到gh-pages")

    run_git(["add", "-A"], cwd=WORKTREE_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit_msg = f"更新插件市场索引 {stamp}\n自动由 build_index.py 生成"
    commit = run_git(["commit", "-m", commit_msg], cwd=WORKTREE_DIR, capture=True)
    if commit.returncode == 0:
        print("[Git] gh-pages 生成提交记录")
    else:
        print("[Git] gh-pages 无变更，无需提交")

    if dry_run:
        print(f"\n[试运行] 临时目录：{WORKTREE_DIR}，不推送gh-pages")
        return True, stamp

    print(f"[Git] 推送 {GH_BRANCH} 至 origin")
    push = run_git(["push", "origin", GH_BRANCH], cwd=WORKTREE_DIR, capture=True)
    if push.returncode != 0:
        print(f"[Git] gh-pages 推送失败：{push.stderr}")
        return False, stamp
    print("[Git] gh-pages 推送完成")
    clean_old_worktree()
    return True, stamp

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Thon Code插件市场：自动构建+推送main+gh-pages")
    parser.add_argument("--dry-run", action="store_true", help="试运行：不推送远程两个分支")
    parser.add_argument("--skip-git", action="store_true", help="仅生成index/html，完全跳过Git所有操作")
    args = parser.parse_args()

    print("===== Thon Code Market Builder =====")
    plugins = scan_packages()
    stamp = build_index(plugins)

    if args.skip_git:
        print("\n[跳过Git] 仅生成文件，结束运行")
        exit(0)

    # 1 先处理 gh-pages
    gh_ok, time_stamp = deploy_gh_pages(dry_run=args.dry_run)
    if not gh_ok:
        print("[错误] gh-pages 流程失败，终止程序")
        exit(2)

    # 2 自动提交推送 main 主分支
    main_ok = push_main_branch(dry_run=args.dry_run, stamp=time_stamp)
    if not main_ok:
        print("[错误] main 分支推送失败")
        exit(3)

    print("\n==== 全部流程执行完成 ====")
    print(f"gh-pages、main 分支已处理完毕（试运行={args.dry_run}）")
    exit(0)

if __name__ == "__main__":
    main()