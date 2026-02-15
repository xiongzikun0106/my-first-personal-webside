#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
publish_gui.py — Obsidian → Valaxy 发布工具 (GUI 版本)

提供现代化的图形界面，用于将 Obsidian 笔记一键发布到 Valaxy 博客。
"""

import sys
import os

# ── Windows 编码修正 ──
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

# ── 依赖检查 ──
try:
    import customtkinter as ctk
except ImportError:
    import subprocess as _sp
    _sp.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

try:
    import yaml
except ImportError:
    import subprocess as _sp
    _sp.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml

import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

# ━━━━━━━━━━━━━━━━ 配置区域 ━━━━━━━━━━━━━━━━
VALAXY_ROOT = Path(r"D:\myWeb")
POSTS_DIR = VALAXY_ROOT / "pages" / "posts"
ASSETS_DIR = VALAXY_ROOT / "public" / "assets"
OBSIDIAN_ATTACHMENT_NAMES = ["attachments", "assets", "images", "附件", "Attachments"]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 样式常量 ──
FONT_FAMILY = "Microsoft YaHei"
COLOR_ACCENT = "#6366f1"       # 靛蓝色主色调
COLOR_ACCENT_HOVER = "#818cf8"
COLOR_SUCCESS = "#22c55e"
COLOR_ERROR = "#ef4444"
COLOR_WARNING = "#f59e0b"
COLOR_INFO = "#60a5fa"
COLOR_CARD = "#1e1e2e"         # 卡片背景
COLOR_TAG_BG = "#2d2d44"       # 标签未选中背景
COLOR_TAG_BORDER = "#4a4a6a"   # 标签边框
COLOR_MUTED = "#94a3b8"        # 次要文字


# ══════════════════════════════════════════
#  核心逻辑（复用自 publish.py）
# ══════════════════════════════════════════

def parse_front_matter(content: str):
    """解析 Front Matter，返回 (meta_dict | None, body_str)。"""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        try:
            meta = yaml.safe_load(match.group(1))
            if not isinstance(meta, dict):
                meta = {}
        except yaml.YAMLError:
            meta = {}
        return meta, content[match.end():]
    return None, content


def dump_front_matter(meta: dict, body: str) -> str:
    """合并 Front Matter 和正文。"""
    yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---\n{body}"


def find_image_file(image_ref: str, md_file_path: Path):
    """在 Obsidian 目录结构中搜索图片文件。"""
    md_dir = md_file_path.parent
    image_name = Path(image_ref).name

    # 直接相对路径
    c = md_dir / image_ref
    if c.is_file():
        return c
    # 同级目录
    c = md_dir / image_name
    if c.is_file():
        return c
    # 常见附件文件夹
    for folder in OBSIDIAN_ATTACHMENT_NAMES:
        c = md_dir / folder / image_name
        if c.is_file():
            return c
    # 父级附件文件夹
    for folder in OBSIDIAN_ATTACHMENT_NAMES:
        c = md_dir.parent / folder / image_name
        if c.is_file():
            return c
    # 向上搜索 3 层
    cur = md_dir
    for _ in range(3):
        cur = cur.parent
        for folder in OBSIDIAN_ATTACHMENT_NAMES:
            c = cur / folder / image_name
            if c.is_file():
                return c
    return None


def collect_existing_tags() -> list[str]:
    """收集博客已有标签，按使用频率降序。"""
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
                    s = str(t).strip()
                    if s:
                        tag_count[s] = tag_count.get(s, 0) + 1
            elif isinstance(tags, str) and tags.strip():
                tag_count[tags.strip()] = tag_count.get(tags.strip(), 0) + 1
    return [t for t, _ in sorted(tag_count.items(), key=lambda x: x[1], reverse=True)]


def collect_existing_categories() -> list[str]:
    """收集博客已有分类。"""
    cat_count: dict[str, int] = {}
    if not POSTS_DIR.exists():
        return []
    for md_file in POSTS_DIR.glob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, _ = parse_front_matter(text)
        if meta and "categories" in meta:
            cats = meta["categories"]
            if isinstance(cats, list):
                for c in cats:
                    s = str(c).strip()
                    if s:
                        cat_count[s] = cat_count.get(s, 0) + 1
            elif isinstance(cats, str) and cats.strip():
                cat_count[cats.strip()] = cat_count.get(cats.strip(), 0) + 1
    return [c for c, _ in sorted(cat_count.items(), key=lambda x: x[1], reverse=True)]


# ══════════════════════════════════════════
#  自定义组件
# ══════════════════════════════════════════

class TagChip(ctk.CTkButton):
    """可切换的标签药丸按钮。"""

    def __init__(self, master, tag_name: str, on_toggle=None, **kwargs):
        self.tag_name = tag_name
        self.is_selected = False
        self._on_toggle = on_toggle
        super().__init__(
            master,
            text=tag_name,
            command=self._toggle,
            width=0,
            height=30,
            corner_radius=15,
            font=(FONT_FAMILY, 12),
            fg_color=COLOR_TAG_BG,
            border_width=1,
            border_color=COLOR_TAG_BORDER,
            text_color=COLOR_MUTED,
            hover_color="#3d3d5c",
            **kwargs,
        )

    def _toggle(self):
        self.is_selected = not self.is_selected
        if self.is_selected:
            self.configure(
                fg_color=COLOR_ACCENT,
                border_color=COLOR_ACCENT,
                text_color="white",
            )
        else:
            self.configure(
                fg_color=COLOR_TAG_BG,
                border_color=COLOR_TAG_BORDER,
                text_color=COLOR_MUTED,
            )
        if self._on_toggle:
            self._on_toggle(self.tag_name, self.is_selected)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if self.is_selected:
            self.configure(
                fg_color=COLOR_ACCENT,
                border_color=COLOR_ACCENT,
                text_color="white",
            )
        else:
            self.configure(
                fg_color=COLOR_TAG_BG,
                border_color=COLOR_TAG_BORDER,
                text_color=COLOR_MUTED,
            )


class SectionHeader(ctk.CTkFrame):
    """带图标的区域标题。"""

    def __init__(self, master, icon: str, title: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self, text=f"{icon}  {title}",
            font=(FONT_FAMILY, 15, "bold"),
            text_color="#e2e8f0",
            anchor="w",
        ).pack(side="left")


# ══════════════════════════════════════════
#  主应用窗口
# ══════════════════════════════════════════

class PublishApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ── 窗口基本设置 ──
        self.title("Obsidian → Valaxy 发布工具")
        self.geometry("920x820")
        self.minsize(760, 680)
        ctk.set_appearance_mode("dark")

        self.selected_tags: set[str] = set()
        self.tag_chips: list[TagChip] = []
        self.source_path: Path | None = None
        self.file_content: str = ""
        self._publishing = False

        # ── 构建界面 ──
        self._build_ui()
        self._load_existing_tags()

    # ──────────────────────────────────────
    #  界面构建
    # ──────────────────────────────────────

    def _build_ui(self):
        # 最外层可滚动区域
        self.outer = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color="#333355",
            scrollbar_button_hover_color="#444466",
        )
        self.outer.pack(fill="both", expand=True, padx=16, pady=(10, 16))

        self._build_header()
        self._build_file_section()
        self._build_frontmatter_section()
        self._build_tags_section()
        self._build_log_section()
        self._build_footer()

    def _build_header(self):
        hdr = ctk.CTkFrame(self.outer, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            hdr, text="📖  Obsidian → Valaxy",
            font=(FONT_FAMILY, 24, "bold"),
            text_color="#e2e8f0",
        ).pack(side="left")

        ctk.CTkLabel(
            hdr, text="一键发布工具",
            font=(FONT_FAMILY, 13),
            text_color=COLOR_MUTED,
        ).pack(side="left", padx=(10, 0), pady=(8, 0))

    # ── 文件选择 ──

    def _build_file_section(self):
        card = ctk.CTkFrame(self.outer, fg_color=COLOR_CARD, corner_radius=12)
        card.pack(fill="x", pady=(6, 4))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        SectionHeader(inner, "📄", "选择 Markdown 文件").pack(fill="x")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))

        self.file_entry = ctk.CTkEntry(
            row,
            placeholder_text="点击右侧按钮选择 Obsidian 笔记文件...",
            font=(FONT_FAMILY, 13),
            height=38,
            corner_radius=8,
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            row, text="📁 浏览",
            width=90, height=38,
            corner_radius=8,
            font=(FONT_FAMILY, 13),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._browse_file,
        ).pack(side="right")

    # ── Front Matter 表单 ──

    def _build_frontmatter_section(self):
        card = ctk.CTkFrame(self.outer, fg_color=COLOR_CARD, corner_radius=12)
        card.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        SectionHeader(inner, "📝", "文章信息").pack(fill="x")

        form = ctk.CTkFrame(inner, fg_color="transparent")
        form.pack(fill="x", pady=(10, 0))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        lbl_opts = dict(font=(FONT_FAMILY, 13), text_color=COLOR_MUTED, anchor="e")
        ent_opts = dict(font=(FONT_FAMILY, 13), height=34, corner_radius=8)

        # 第一行：标题 + 日期
        ctk.CTkLabel(form, text="标题：", **lbl_opts).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=5)
        self.title_entry = ctk.CTkEntry(form, placeholder_text="文章标题", **ent_opts)
        self.title_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=5)

        ctk.CTkLabel(form, text="日期：", **lbl_opts).grid(row=0, column=2, sticky="e", padx=(0, 6), pady=5)
        self.date_entry = ctk.CTkEntry(form, **ent_opts)
        self.date_entry.grid(row=0, column=3, sticky="ew", pady=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 第二行：分类 + 摘要
        ctk.CTkLabel(form, text="分类：", **lbl_opts).grid(row=1, column=0, sticky="e", padx=(0, 6), pady=5)
        self.cat_entry = ctk.CTkEntry(form, placeholder_text="文章分类", **ent_opts)
        self.cat_entry.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=5)

        ctk.CTkLabel(form, text="摘要：", **lbl_opts).grid(row=1, column=2, sticky="e", padx=(0, 6), pady=5)
        self.excerpt_entry = ctk.CTkEntry(form, placeholder_text="一句话摘要（可选）", **ent_opts)
        self.excerpt_entry.grid(row=1, column=3, sticky="ew", pady=5)

    # ── 标签选择 ──

    def _build_tags_section(self):
        card = ctk.CTkFrame(self.outer, fg_color=COLOR_CARD, corner_radius=12)
        card.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        SectionHeader(inner, "🏷️", "标签（点击选择，支持多选）").pack(fill="x")

        # 标签容器
        self.tags_container = ctk.CTkFrame(inner, fg_color="transparent")
        self.tags_container.pack(fill="x", pady=(10, 8))

        self.no_tags_label = ctk.CTkLabel(
            self.tags_container,
            text="暂无已有标签",
            font=(FONT_FAMILY, 12),
            text_color=COLOR_MUTED,
        )

        # 新增标签行
        add_row = ctk.CTkFrame(inner, fg_color="transparent")
        add_row.pack(fill="x", pady=(4, 0))

        self.new_tag_entry = ctk.CTkEntry(
            add_row,
            placeholder_text="输入新标签，按回车或点击添加",
            font=(FONT_FAMILY, 12),
            height=34,
            corner_radius=8,
        )
        self.new_tag_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.new_tag_entry.bind("<Return>", lambda e: self._add_new_tag())

        ctk.CTkButton(
            add_row, text="＋ 添加",
            width=80, height=34,
            corner_radius=8,
            font=(FONT_FAMILY, 12),
            fg_color="#334155",
            hover_color="#475569",
            command=self._add_new_tag,
        ).pack(side="right")

        # 已选标签展示
        self.selected_label = ctk.CTkLabel(
            inner, text="",
            font=(FONT_FAMILY, 12),
            text_color=COLOR_SUCCESS,
            anchor="w",
        )
        self.selected_label.pack(fill="x", pady=(6, 0))

    # ── 日志区域 ──

    def _build_log_section(self):
        card = ctk.CTkFrame(self.outer, fg_color=COLOR_CARD, corner_radius=12)
        card.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        SectionHeader(inner, "📋", "发布日志").pack(fill="x")

        self.log_text = ctk.CTkTextbox(
            inner,
            height=180,
            font=("Consolas", 12),
            corner_radius=8,
            fg_color="#11111b",
            text_color="#cdd6f4",
            state="disabled",
            wrap="word",
        )
        self.log_text.pack(fill="x", pady=(10, 0))

        # 配置颜色标签
        self.log_text.tag_config("error", foreground=COLOR_ERROR)
        self.log_text.tag_config("success", foreground=COLOR_SUCCESS)
        self.log_text.tag_config("warning", foreground=COLOR_WARNING)
        self.log_text.tag_config("info", foreground=COLOR_INFO)
        self.log_text.tag_config("dim", foreground="#6c7086")

    # ── 底部操作栏 ──

    def _build_footer(self):
        footer = ctk.CTkFrame(self.outer, fg_color="transparent")
        footer.pack(fill="x", pady=(10, 4))

        self.publish_btn = ctk.CTkButton(
            footer,
            text="🚀  一键发布",
            height=46,
            corner_radius=10,
            font=(FONT_FAMILY, 16, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._on_publish_click,
        )
        self.publish_btn.pack(fill="x")

        # 底部提示
        ctk.CTkLabel(
            footer,
            text="发布流程：复制文件 → 迁移图片 → 补全 Front Matter → Git 提交并推送",
            font=(FONT_FAMILY, 11),
            text_color="#585b70",
        ).pack(pady=(8, 0))

    # ──────────────────────────────────────
    #  事件处理
    # ──────────────────────────────────────

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="选择 Obsidian Markdown 笔记",
            filetypes=[("Markdown", "*.md *.markdown"), ("所有文件", "*.*")],
        )
        if path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)
            self._on_file_selected(Path(path))

    def _on_file_selected(self, path: Path):
        """文件选中后：读取内容，自动填充表单。"""
        self.source_path = path.resolve()

        if not self.source_path.exists():
            self.log("❌ 文件不存在：" + str(self.source_path), "error")
            return

        # 读取文件
        try:
            self.file_content = self.source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                self.file_content = self.source_path.read_text(encoding="gbk")
            except Exception as e:
                self.log(f"❌ 无法读取文件：{e}", "error")
                return

        self.log(f"已加载文件：{self.source_path.name}", "info")

        # 解析 Front Matter
        meta, _ = parse_front_matter(self.file_content)

        # 填充标题
        self.title_entry.delete(0, "end")
        if meta and meta.get("title"):
            self.title_entry.insert(0, str(meta["title"]))
        else:
            self.title_entry.insert(0, self.source_path.stem)

        # 填充日期
        self.date_entry.delete(0, "end")
        if meta and meta.get("date"):
            self.date_entry.insert(0, str(meta["date"]))
        else:
            self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 填充分类
        self.cat_entry.delete(0, "end")
        if meta and meta.get("categories"):
            cats = meta["categories"]
            if isinstance(cats, list):
                self.cat_entry.insert(0, str(cats[0]) if cats else "")
            else:
                self.cat_entry.insert(0, str(cats))

        # 填充摘要
        self.excerpt_entry.delete(0, "end")
        if meta and meta.get("excerpt"):
            self.excerpt_entry.insert(0, str(meta["excerpt"]))

        # 填充已有标签
        self.selected_tags.clear()
        if meta and meta.get("tags"):
            tags = meta["tags"]
            if isinstance(tags, list):
                for t in tags:
                    self.selected_tags.add(str(t).strip())
            elif isinstance(tags, str):
                self.selected_tags.add(tags.strip())

        # 同步标签芯片状态
        for chip in self.tag_chips:
            chip.set_selected(chip.tag_name in self.selected_tags)

        # 添加文件中有但标签库里没有的标签
        known = {c.tag_name for c in self.tag_chips}
        for t in self.selected_tags:
            if t and t not in known:
                self._create_tag_chip(t, selected=True)

        self._update_selected_label()

    def _load_existing_tags(self):
        """加载博客已有标签，渲染为标签按钮。"""
        tags = collect_existing_tags()
        if not tags:
            self.no_tags_label.pack(pady=4)
            return

        self.no_tags_label.pack_forget()
        for tag in tags:
            self._create_tag_chip(tag)

    def _create_tag_chip(self, tag: str, selected: bool = False):
        chip = TagChip(self.tags_container, tag, on_toggle=self._on_tag_toggle)
        chip.pack(side="left", padx=(0, 6), pady=3)
        if selected:
            chip.set_selected(True)
        self.tag_chips.append(chip)

    def _on_tag_toggle(self, tag_name: str, is_selected: bool):
        if is_selected:
            self.selected_tags.add(tag_name)
        else:
            self.selected_tags.discard(tag_name)
        self._update_selected_label()

    def _add_new_tag(self):
        raw = self.new_tag_entry.get().strip()
        if not raw:
            return
        # 支持逗号分隔多个标签
        new_tags = [t.strip() for t in raw.split(",") if t.strip()]
        known = {c.tag_name for c in self.tag_chips}
        for tag in new_tags:
            if tag not in known:
                self.no_tags_label.pack_forget()
                self._create_tag_chip(tag, selected=True)
                self.selected_tags.add(tag)
                known.add(tag)
            else:
                # 如果已存在，设置为选中
                for c in self.tag_chips:
                    if c.tag_name == tag and not c.is_selected:
                        c.set_selected(True)
                        self.selected_tags.add(tag)
        self.new_tag_entry.delete(0, "end")
        self._update_selected_label()

    def _update_selected_label(self):
        if self.selected_tags:
            self.selected_label.configure(
                text="已选标签：" + "、".join(sorted(self.selected_tags))
            )
        else:
            self.selected_label.configure(text="")

    # ──────────────────────────────────────
    #  日志输出
    # ──────────────────────────────────────

    def log(self, message: str, tag: str = ""):
        """线程安全地向日志区域追加文本。"""
        def _append():
            self.log_text.configure(state="normal")
            if tag:
                self.log_text.insert("end", message + "\n", tag)
            else:
                self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.after(0, _append)

    def log_clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ──────────────────────────────────────
    #  发布流程
    # ──────────────────────────────────────

    def _on_publish_click(self):
        if self._publishing:
            return

        # 校验
        file_path = self.file_entry.get().strip()
        if not file_path:
            self.log("❌ 请先选择一个 Markdown 文件", "error")
            return
        src = Path(file_path).resolve()
        if not src.exists():
            self.log(f"❌ 文件不存在：{src}", "error")
            return
        if src.suffix.lower() not in (".md", ".markdown"):
            self.log("❌ 请选择 Markdown 文件（.md）", "error")
            return
        title = self.title_entry.get().strip()
        if not title:
            self.log("❌ 文章标题不能为空", "error")
            return

        # 读取文件（如果还没有加载过）
        if self.source_path != src or not self.file_content:
            self._on_file_selected(src)

        self._publishing = True
        self.publish_btn.configure(state="disabled", text="⏳ 发布中...")
        self.log_clear()

        thread = threading.Thread(target=self._do_publish, daemon=True)
        thread.start()

    def _do_publish(self):
        """在后台线程执行完整发布流程。"""
        try:
            source = self.source_path
            content = self.file_content

            self.log("══════════════════════════════════════", "dim")
            self.log("  开始发布流程", "info")
            self.log("══════════════════════════════════════", "dim")

            # ── 1. 迁移图片 ──
            self.log("\n▸ 正在处理图片...", "info")
            content = self._migrate_images(content, source)

            # ── 2. 构建 Front Matter ──
            self.log("\n▸ 正在处理 Front Matter...", "info")
            content = self._build_final_content(content)

            # ── 3. 写入目标文件 ──
            self.log("\n▸ 正在写入文件...", "info")
            POSTS_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = source.stem.replace(" ", "-") + ".md"
            dest = POSTS_DIR / safe_name

            dest.write_text(content, encoding="utf-8")
            self.log(f"  ✔ 文章已写入：{dest.relative_to(VALAXY_ROOT)}", "success")

            # ── 4. Git 操作 ──
            publish_title = self.title_entry.get().strip() or source.stem
            self.log("\n▸ 正在执行 Git 操作...", "info")
            self._git_publish(publish_title)

            self.log("\n══════════════════════════════════════", "dim")
            self.log(f"  🎉 发布成功！「{publish_title}」已推送到远程仓库", "success")
            self.log("══════════════════════════════════════", "dim")

        except Exception as e:
            self.log(f"\n❌ 发布过程中出错：{e}", "error")
        finally:
            self.after(0, self._publish_done)

    def _publish_done(self):
        self._publishing = False
        self.publish_btn.configure(state="normal", text="🚀  一键发布")

    # ── 图片迁移 ──

    def _migrate_images(self, content: str, md_path: Path) -> str:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        count = 0

        # 标准 Markdown 图片
        def _replace_md(m):
            nonlocal count
            alt, raw = m.group(1), m.group(2).strip()
            if raw.startswith(("/assets/", "/images/", "http://", "https://")):
                return m.group(0)
            img = find_image_file(raw, md_path)
            if img:
                dest = self._copy_image(img)
                count += 1
                self.log(f"  📷 {img.name} → public/assets/{dest.name}", "success")
                return f"![{alt}](/assets/{dest.name})"
            else:
                self.log(f"  ⚠ 未找到图片「{raw}」，保留原始引用", "warning")
                return m.group(0)

        content = re.sub(r"!\[([^\]]*)\]\((?!https?://)([^)]+)\)", _replace_md, content)

        # Obsidian Wiki 链接
        def _replace_wiki(m):
            nonlocal count
            ref = m.group(1).strip()
            alt_part = m.group(2)
            alt = alt_part[1:].strip() if alt_part else Path(ref).stem
            if Path(ref).suffix.lower() not in IMAGE_EXTENSIONS:
                return m.group(0)
            img = find_image_file(ref, md_path)
            if img:
                dest = self._copy_image(img)
                count += 1
                self.log(f"  📷 {img.name} → public/assets/{dest.name}", "success")
                return f"![{alt}](/assets/{dest.name})"
            else:
                self.log(f"  ⚠ 未找到图片「{ref}」，保留原始引用", "warning")
                return m.group(0)

        content = re.sub(r"!\[\[([^\]|]+?)(\|[^\]]*)?\]\]", _replace_wiki, content)

        if count == 0:
            self.log("  ℹ 未发现需要迁移的本地图片", "dim")
        else:
            self.log(f"  ✔ 共迁移 {count} 张图片", "success")
        return content

    @staticmethod
    def _copy_image(src: Path) -> Path:
        dest = ASSETS_DIR / src.name
        if dest.exists() and dest.stat().st_size != src.stat().st_size:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = ASSETS_DIR / f"{src.stem}_{ts}{src.suffix}"
        shutil.copy2(str(src), str(dest))
        return dest

    # ── 构建最终内容 ──

    def _build_final_content(self, content: str) -> str:
        meta, body = parse_front_matter(content)
        title = self.title_entry.get().strip()
        date = self.date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        category = self.cat_entry.get().strip()
        excerpt = self.excerpt_entry.get().strip()
        tags = sorted(self.selected_tags) if self.selected_tags else []

        if meta is None:
            meta = {}
            self.log("  ✔ 自动生成 Front Matter", "success")
        else:
            self.log("  ✔ 已有 Front Matter，进行补全", "success")

        if title:
            meta["title"] = title
        if date:
            meta["date"] = date
        if "updated" not in meta:
            meta["updated"] = date
        if category:
            meta["categories"] = [category]
        if tags:
            meta["tags"] = tags
        if excerpt:
            meta["excerpt"] = excerpt

        return dump_front_matter(meta, body)

    # ── Git 操作 ──

    def _run_git(self, args: list[str]) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["git"] + args,
                cwd=str(VALAXY_ROOT),
                capture_output=True, text=True, encoding="utf-8",
            )
            output = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
            return r.returncode == 0, output
        except FileNotFoundError:
            return False, "未找到 Git，请确保 Git 已安装并在 PATH 中"
        except Exception as e:
            return False, str(e)

    def _git_publish(self, title: str):
        # add
        self.log("  ▶ git add .", "dim")
        ok, out = self._run_git(["add", "."])
        if not ok:
            self.log(f"  ✘ git add 失败：{out}", "error")
            raise RuntimeError("git add 失败")
        self.log("    ✔ 暂存完成", "success")

        # commit
        msg = f"feat: publish {title}"
        self.log(f'  ▶ git commit -m "{msg}"', "dim")
        ok, out = self._run_git(["commit", "-m", msg])
        if not ok:
            if "nothing to commit" in out:
                self.log("    ℹ 没有新的更改需要提交", "warning")
            else:
                self.log(f"  ✘ git commit 失败：{out}", "error")
                raise RuntimeError("git commit 失败")
        else:
            self.log("    ✔ 提交完成", "success")

        # push
        self.log("  ▶ git push", "dim")
        ok, out = self._run_git(["push"])
        if not ok:
            self.log(f"  ✘ git push 失败：{out}", "error")
            self.log("    请检查网络连接或远程仓库配置", "warning")
            raise RuntimeError("git push 失败")
        self.log("    ✔ 推送完成", "success")


# ══════════════════════════════════════════
#  入口
# ══════════════════════════════════════════

if __name__ == "__main__":
    app = PublishApp()
    app.mainloop()
