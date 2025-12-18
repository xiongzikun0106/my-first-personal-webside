import hashlib
import html
import os
import shutil
from bs4 import BeautifulSoup

HTML_FILE = "final_page.html"
BACKUP_FILE = "final_page.html.bak"
MAX_CONTENT_CHARS = 200_000  # 防止把 HTML 写炸（可自行调整）

def generate_id(title: str) -> str:
    return "id_" + hashlib.md5(title.encode("utf-8")).hexdigest()[:10]

def multiline_input(prompt: str) -> str:
    print(prompt)
    print("（多行输入，单独一行输入 END 结束）")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)

def add_post():
    title = input("标题: ").strip()
    if not title:
        print("❌ 标题不能为空")
        return

    intro = input("简介: ").strip()
    content = multiline_input("正文:")
    img_name = input("图片文件名（images/ 下，可留空）: ").strip()

    if len(content) > MAX_CONTENT_CHARS:
        print(f"❌ 正文过长（{len(content)} 字符），已阻止写入，避免 HTML 失控。")
        return

    post_id = generate_id(title)

    if not os.path.exists(HTML_FILE):
        print(f"❌ 找不到 {HTML_FILE}")
        return

    # 备份
    shutil.copy2(HTML_FILE, BACKUP_FILE)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # 幂等性检查
    if soup.find(id=f"card_{post_id}") or soup.find(id=f"data-{post_id}"):
        print("⚠️ 文章已存在（基于标题哈希），未重复写入")
        return

    blog_list = soup.find(id="blog-list")
    blog_data = soup.find(id="blog-data")

    if not blog_list or not blog_data:
        print("❌ HTML 缺少 #blog-list 或 #blog-data")
        print("请确认你使用的是我给你的那份 HTML 结构")
        return

    esc_title = html.escape(title)
    esc_intro = html.escape(intro)
    esc_content = html.escape(content).replace("\n", "<br>")

    img_html = f'<img src="images/{img_name}" class="blog-img">' if img_name else ""

    card_html = f"""
    <div class="blog-card" id="card_{post_id}" onclick="openPost('{post_id}')">
        <span class="medium">{esc_title}</span><br>
        <span class="small">{esc_intro}</span>
    </div>
    """

    data_html = f"""
    <div id="data-{post_id}">
        <h3>{esc_title}</h3>
        {img_html}
        <p class="small">{esc_content}</p>
    </div>
    """

    blog_list.append(BeautifulSoup(card_html, "html.parser"))
    blog_data.append(BeautifulSoup(data_html, "html.parser"))

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"✅ 《{title}》已成功添加")
    print(f"🛟 原文件已备份为 {BACKUP_FILE}")

if __name__ == "__main__":
    add_post()
