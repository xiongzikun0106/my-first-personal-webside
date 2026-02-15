#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
publish.py — Obsidian 笔记一键发布到 Valaxy 博客

用法:
    python publish.py <Obsidian笔记的Markdown文件路径>

功能:
    1. 将 Markdown 文件复制到 Valaxy 的 pages/posts/ 目录
    2. 自动迁移本地图片到 public/assets/ 并更新引用路径
    3. 自动补全 Front Matter（title / date / tags 等）
    4. 执行 git add / commit / push 完成发布
"""

import sys
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ━━━━━━━ 修正 Windows 终端编码 ━━━━━━━
# Windows PowerShell 默认使用 GBK 编码，强制切换为 UTF-8
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

# ━━━━━━━━━━ 尝试导入 PyYAML ━━━━━━━━━━
try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 库，请先运行以下命令安装：")
    print("   pip install pyyaml")
    sys.exit(1)

# ━━━━━━━━━━━━━━━━ 配置区域 ━━━━━━━━━━━━━━━━
# Valaxy 博客项目根目录（请根据实际情况修改）
VALAXY_ROOT = Path(r"D:\myWeb")
# 文章存放目录
POSTS_DIR = VALAXY_ROOT / "pages" / "posts"
# 图片资源存放目录
ASSETS_DIR = VALAXY_ROOT / "public" / "assets"
# Obsidian 中常见的附件文件夹名称（脚本会依次搜索）
OBSIDIAN_ATTACHMENT_NAMES = ["attachments", "assets", "images", "附件", "Attachments"]
# 支持的图片扩展名
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ──────────────────────────────────────────
#  Front Matter 解析 / 序列化
# ──────────────────────────────────────────

def parse_front_matter(content: str):
    """
    解析 Markdown 文件内容，分离 Front Matter 和正文。
    返回 (meta_dict | None, body_str)
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(content)
    if match:
        raw_yaml = match.group(1)
        try:
            meta = yaml.safe_load(raw_yaml)
            if not isinstance(meta, dict):
                meta = {}
        except yaml.YAMLError:
            meta = {}
        body = content[match.end():]
        return meta, body
    return None, content


def dump_front_matter(meta: dict, body: str) -> str:
    """将 Front Matter 字典和正文合并为完整 Markdown 内容。"""
    # 使用 allow_unicode 以正确显示中文
    yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n{body}"


# ──────────────────────────────────────────
#  图片处理
# ──────────────────────────────────────────

def find_image_file(image_ref: str, md_file_path: Path) -> Path | None:
    """
    根据图片引用路径，在 Obsidian 笔记所在目录及其附件子目录中搜索图片文件。
    返回找到的图片 Path，找不到返回 None。
    """
    md_dir = md_file_path.parent
    image_name = Path(image_ref).name  # 取纯文件名

    # 搜索策略：
    # 1. 直接按引用路径解析（相对于 md 文件所在目录）
    candidate = md_dir / image_ref
    if candidate.is_file():
        return candidate

    # 2. 在 md 文件同级目录直接查找同名文件
    candidate = md_dir / image_name
    if candidate.is_file():
        return candidate

    # 3. 在 md 文件同级的常见附件文件夹中查找
    for folder_name in OBSIDIAN_ATTACHMENT_NAMES:
        candidate = md_dir / folder_name / image_name
        if candidate.is_file():
            return candidate

    # 4. 在 md 文件的父目录的常见附件文件夹中查找（笔记库根目录附件）
    parent_dir = md_dir.parent
    for folder_name in OBSIDIAN_ATTACHMENT_NAMES:
        candidate = parent_dir / folder_name / image_name
        if candidate.is_file():
            return candidate

    # 5. 递归向上查找最多 3 层
    current = md_dir
    for _ in range(3):
        current = current.parent
        for folder_name in OBSIDIAN_ATTACHMENT_NAMES:
            candidate = current / folder_name / image_name
            if candidate.is_file():
                return candidate

    return None


def migrate_images(content: str, md_file_path: Path) -> str:
    """
    识别 Markdown 中的本地图片链接，将图片复制到 Valaxy 的 assets 目录，
    并更新 Markdown 中的引用路径。支持：
      - 标准 Markdown: ![alt](path/to/image.png)
      - Obsidian Wiki:  ![[image.png]]  或  ![[image.png|alt]]
    """
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    migrated_count = 0

    # ── 处理标准 Markdown 图片 ──
    # 匹配 ![alt](path)，排除 http/https 开头的远程链接
    md_img_pattern = re.compile(r"!\[([^\]]*)\]\((?!https?://)([^)]+)\)")

    def replace_md_image(match):
        nonlocal migrated_count
        alt_text = match.group(1)
        img_path_raw = match.group(2).strip()

        # 跳过已经是 /assets/ 路径的图片（已迁移过）
        if img_path_raw.startswith("/assets/"):
            return match.group(0)

        # 跳过已经是 /images/ 路径的图片（博客原有图片）
        if img_path_raw.startswith("/images/"):
            return match.group(0)

        img_file = find_image_file(img_path_raw, md_file_path)
        if img_file:
            dest = ASSETS_DIR / img_file.name
            # 如果目标已存在同名文件，添加时间戳避免冲突
            if dest.exists() and dest.stat().st_size != img_file.stat().st_size:
                stem = img_file.stem
                suffix = img_file.suffix
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                dest = ASSETS_DIR / f"{stem}_{timestamp}{suffix}"
            shutil.copy2(str(img_file), str(dest))
            migrated_count += 1
            print(f"  📷 已迁移图片: {img_file.name} → public/assets/{dest.name}")
            return f"![{alt_text}](/assets/{dest.name})"
        else:
            print(f"  ⚠️  警告：未找到图片文件「{img_path_raw}」，保留原始引用")
            return match.group(0)

    content = md_img_pattern.sub(replace_md_image, content)

    # ── 处理 Obsidian Wiki 链接图片 ──
    # 匹配 ![[filename.png]] 或 ![[filename.png|alt text]]
    wiki_img_pattern = re.compile(r"!\[\[([^\]|]+?)(\|[^\]]*)?\]\]")

    def replace_wiki_image(match):
        nonlocal migrated_count
        img_ref = match.group(1).strip()
        alt_part = match.group(2)
        alt_text = alt_part[1:].strip() if alt_part else Path(img_ref).stem

        # 检查是否是图片文件
        ext = Path(img_ref).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            return match.group(0)  # 不是图片，保留原样

        img_file = find_image_file(img_ref, md_file_path)
        if img_file:
            dest = ASSETS_DIR / img_file.name
            if dest.exists() and dest.stat().st_size != img_file.stat().st_size:
                stem = img_file.stem
                suffix = img_file.suffix
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                dest = ASSETS_DIR / f"{stem}_{timestamp}{suffix}"
            shutil.copy2(str(img_file), str(dest))
            migrated_count += 1
            print(f"  📷 已迁移图片: {img_file.name} → public/assets/{dest.name}")
            return f"![{alt_text}](/assets/{dest.name})"
        else:
            print(f"  ⚠️  警告：未找到图片文件「{img_ref}」，保留原始引用")
            return match.group(0)

    content = wiki_img_pattern.sub(replace_wiki_image, content)

    if migrated_count == 0:
        print("  ℹ️  未发现需要迁移的本地图片")
    else:
        print(f"  ✅ 共迁移 {migrated_count} 张图片")

    return content


# ──────────────────────────────────────────
#  标签处理
# ──────────────────────────────────────────

def collect_existing_tags() -> list[str]:
    """扫描 pages/posts/ 目录下所有文章，收集已有标签并按出现频率排序。"""
    tag_count: dict[str, int] = {}
    if not POSTS_DIR.exists():
        return []

    for md_file in POSTS_DIR.glob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, _ = parse_front_matter(text)
        if meta and "tags" in meta:
            tags = meta["tags"]
            if isinstance(tags, list):
                for t in tags:
                    tag_str = str(t).strip()
                    if tag_str:
                        tag_count[tag_str] = tag_count.get(tag_str, 0) + 1
            elif isinstance(tags, str):
                tag_str = tags.strip()
                if tag_str:
                    tag_count[tag_str] = tag_count.get(tag_str, 0) + 1

    # 按频率降序排列
    sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_tags]


def interactive_tags() -> list[str]:
    """
    交互式标签选择：
      - 列出博客已有标签供用户选择（输入序号，逗号分隔）
      - 也可直接输入新标签
    """
    existing_tags = collect_existing_tags()

    print("\n🏷️  标签设置")
    print("─" * 40)

    if existing_tags:
        print("博客已有标签：")
        for i, tag in enumerate(existing_tags, 1):
            print(f"  [{i:2d}] {tag}")
        print()
        print("请输入标签序号（逗号分隔）或直接输入新标签名称（逗号分隔）")
        print("也可混合使用，例如: 1,3,新标签名")
        print("直接回车跳过标签设置")
    else:
        print("博客暂无已有标签，请输入新标签（逗号分隔）：")
        print("直接回车跳过标签设置")

    print("─" * 40)
    user_input = input("👉 标签: ").strip()

    if not user_input:
        return []

    selected_tags = []
    parts = [p.strip() for p in user_input.split(",") if p.strip()]

    for part in parts:
        # 尝试解析为数字序号
        try:
            idx = int(part)
            if 1 <= idx <= len(existing_tags):
                tag = existing_tags[idx - 1]
                if tag not in selected_tags:
                    selected_tags.append(tag)
            else:
                print(f"  ⚠️  序号 {idx} 超出范围，已忽略")
        except ValueError:
            # 不是数字，视为新标签
            if part not in selected_tags:
                selected_tags.append(part)

    if selected_tags:
        print(f"  ✅ 已选择标签: {', '.join(selected_tags)}")

    return selected_tags


# ──────────────────────────────────────────
#  Front Matter 补全
# ──────────────────────────────────────────

def ensure_front_matter(content: str, title: str) -> str:
    """
    检查并补全 Front Matter：
      - 没有 Front Matter → 自动生成（title, date, tags 交互选择）
      - 有 Front Matter 但缺少 tags → 交互补全
      - 有 Front Matter 且完整 → 保持不变
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta, body = parse_front_matter(content)

    if meta is None:
        # ── 完全没有 Front Matter，生成一个 ──
        print("\n📝 未检测到 Front Matter，正在自动生成...")
        tags = interactive_tags()
        meta = {
            "title": title,
            "date": now_str,
            "updated": now_str,
        }
        if tags:
            meta["tags"] = tags

        # 询问分类
        print("\n📂 请输入文章分类（直接回车跳过）：")
        category = input("👉 分类: ").strip()
        if category:
            meta["categories"] = [category]

        # 询问摘要
        print("\n📋 请输入文章摘要（直接回车跳过）：")
        excerpt = input("👉 摘要: ").strip()
        if excerpt:
            meta["excerpt"] = excerpt

        return dump_front_matter(meta, body)

    else:
        # ── 已有 Front Matter，检查缺失字段 ──
        changed = False

        if "title" not in meta or not meta["title"]:
            meta["title"] = title
            changed = True

        if "date" not in meta or not meta["date"]:
            meta["date"] = now_str
            changed = True

        if "updated" not in meta:
            meta["updated"] = now_str
            changed = True

        # 检查 tags
        if "tags" not in meta or not meta["tags"]:
            print(f"\n📝 文章已有 Front Matter，但缺少标签（tags）")
            tags = interactive_tags()
            if tags:
                meta["tags"] = tags
                changed = True

        if changed:
            return dump_front_matter(meta, body)
        else:
            print("  ✅ Front Matter 已完整，无需修改")
            return content


# ──────────────────────────────────────────
#  Git 操作
# ──────────────────────────────────────────

def run_git_command(args: list[str], error_msg: str) -> bool:
    """执行 Git 命令，返回是否成功。"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(VALAXY_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"❌ {error_msg}")
            print(f"   Git 输出: {result.stderr.strip() or result.stdout.strip()}")
            return False
        return True
    except FileNotFoundError:
        print("❌ 错误：未找到 Git 命令，请确保 Git 已安装并在 PATH 中")
        return False
    except Exception as e:
        print(f"❌ 执行 Git 命令时出错: {e}")
        return False


def git_publish(title: str) -> bool:
    """执行 git add / commit / push 三步发布。"""
    print("\n🚀 开始 Git 发布流程...")
    print("─" * 40)

    # git add .
    print("  ▶ git add .")
    if not run_git_command(["add", "."], "执行 git add 失败"):
        return False
    print("    ✅ 暂存完成")

    # git commit
    commit_msg = f"feat: publish {title}"
    print(f"  ▶ git commit -m \"{commit_msg}\"")
    if not run_git_command(["commit", "-m", commit_msg], "执行 git commit 失败（可能没有更改需要提交）"):
        return False
    print("    ✅ 提交完成")

    # git push
    print("  ▶ git push")
    if not run_git_command(["push"], "执行 git push 失败（请检查网络连接或远程仓库配置）"):
        return False
    print("    ✅ 推送完成")

    return True


# ──────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   📖 Obsidian → Valaxy 一键发布工具     ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # ── 1. 参数检查 ──
    if len(sys.argv) < 2:
        print("❌ 错误：请提供 Markdown 文件路径作为参数")
        print("   用法: python publish.py <Markdown文件路径>")
        print('   示例: python publish.py "D:\\Obsidian\\笔记\\我的文章.md"')
        sys.exit(1)

    source_path = Path(sys.argv[1]).resolve()

    # ── 2. 文件存在性检查 ──
    if not source_path.exists():
        print(f"❌ 错误：文件不存在 → {source_path}")
        sys.exit(1)

    if not source_path.is_file():
        print(f"❌ 错误：路径不是文件 → {source_path}")
        sys.exit(1)

    if source_path.suffix.lower() not in (".md", ".markdown"):
        print(f"❌ 错误：文件不是 Markdown 格式（{source_path.suffix}）")
        sys.exit(1)

    # 从文件名提取文章标题（去掉扩展名）
    title = source_path.stem
    print(f"📄 源文件: {source_path}")
    print(f"📌 文章标题: {title}")

    # ── 3. 确保目标目录存在 ──
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 4. 读取源文件 ──
    try:
        content = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = source_path.read_text(encoding="gbk")
        except Exception as e:
            print(f"❌ 错误：无法读取文件（编码问题）: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 错误：读取文件失败: {e}")
        sys.exit(1)

    # ── 5. 迁移图片 ──
    print("\n🖼️  正在处理图片...")
    print("─" * 40)
    content = migrate_images(content, source_path)

    # ── 6. 处理 Front Matter ──
    content = ensure_front_matter(content, title)

    # ── 7. 写入目标文件 ──
    # 文件名做简单处理：保留原名，但替换空格为短横线
    safe_filename = source_path.stem.replace(" ", "-") + ".md"
    dest_path = POSTS_DIR / safe_filename

    try:
        dest_path.write_text(content, encoding="utf-8")
        print(f"\n✅ 文章已写入: {dest_path}")
    except Exception as e:
        print(f"❌ 错误：写入目标文件失败: {e}")
        sys.exit(1)

    # ── 8. Git 发布 ──
    # 从最终的 front matter 中读取标题
    final_meta, _ = parse_front_matter(content)
    publish_title = title
    if final_meta and "title" in final_meta:
        publish_title = final_meta["title"]

    if git_publish(publish_title):
        print("\n" + "═" * 42)
        print(f"🎉 发布成功！文章「{publish_title}」已推送到远程仓库")
        print("═" * 42)
    else:
        print("\n⚠️  Git 操作未完全成功，请手动检查并完成发布")
        sys.exit(1)


if __name__ == "__main__":
    main()
