import hashlib
import html
import os
import shutil
from bs4 import BeautifulSoup

HTML_FILE = "final_page.html"
BACKUP_FILE = "final_page.html.bak"
MAX_CONTENT_CHARS = 200_000 

def generate_id(title: str) -> str:
    return "id_" + hashlib.md5(title.encode("utf-8")).hexdigest()[:10]

def load_soup():
    if not os.path.exists(HTML_FILE):
        print(f"❌ 找不到 {HTML_FILE}")
        return None
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")

def save_soup(soup):
    # 保存前备份，以防万一
    shutil.copy2(HTML_FILE, BACKUP_FILE)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"✅ 操作成功，原文件已备份为 {BACKUP_FILE}")

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
    soup = load_soup()
    if not soup: return

    title = input("请输入文章标题: ").strip()
    if not title:
        print("❌ 标题不能为空")
        return

    post_id = generate_id(title)
    
    # --- 幂等性检查 ---
    # 同时检查卡片和数据区，确保不会重复写入导致 HTML 结构混乱
    if soup.find(id=f"card_{post_id}") or soup.find(id=f"data-{post_id}"):
        print(f"⚠️ 警告：标题为《{title}》的文章已存在，请勿重复添加！")
        return

    intro = input("请输入简介: ").strip()
    content = multiline_input("请输入正文:")
    img_name = input("图片文件名（images/ 路径下，无图请直接回车）: ").strip()

    if len(content) > MAX_CONTENT_CHARS:
        print(f"❌ 正文太长了，你是想写 SCP 文档集吗？(字符数: {len(content)})")
        return

    blog_list = soup.find(id="blog-list")
    blog_data = soup.find(id="blog-data")

    if not blog_list or not blog_data:
        print("❌ 结构错误：HTML 缺少 #blog-list 或 #blog-data 锚点")
        return

    esc_title = html.escape(title)
    esc_intro = html.escape(intro)
    esc_content = html.escape(content).replace("\n", "<br>")
    img_html = f'<img src="images/{img_name}" class="blog-img">' if img_name else ""

    # 构造卡片 HTML
    card_html = f"""
    <div class="blog-card" id="card_{post_id}" onclick="openPost('{post_id}')">
        <span class="medium">{esc_title}</span><br>
        <span class="small">{esc_intro}</span>
    </div>
    """
    # 构造内容数据 HTML
    data_html = f"""
    <div id="data-{post_id}">
        <h3>{esc_title}</h3>
        {img_html}
        <p class="small">{esc_content}</p>
    </div>
    """

    blog_list.append(BeautifulSoup(card_html, "html.parser"))
    blog_data.append(BeautifulSoup(data_html, "html.parser"))
    
    save_soup(soup)
    print(f"🎉 《{title}》已成功收容进你的博客！")

def delete_post():
    soup = load_soup()
    if not soup: return

    # 1. 自动寻找所有的博客卡片
    cards = soup.find(id="blog-list").find_all("div", class_="blog-card")
    
    if not cards:
        print("📭 博客列表空空如也，没什么好删的。")
        return

    print("\n--- 当前文章列表 ---")
    post_map = []
    for idx, card in enumerate(cards):
        # 提取标题
        title_span = card.find("span", class_="medium")
        title = title_span.get_text() if title_span else "无标题"
        # 提取 ID (去掉前缀 'card_')
        raw_id = card.get('id', '').replace('card_', '')
        post_map.append({"title": title, "id": raw_id})
        print(f"[{idx}] {title} (ID: {raw_id})")

    choice = input("\n请输入要删除的文章编号 (或输入 q 退出): ").strip()
    if choice.lower() == 'q': return

    try:
        target_idx = int(choice)
        target = post_map[target_idx]
    except (ValueError, IndexError):
        print("❌ 无效的选择。")
        return

    confirm = input(f"❗ 确定要抹除《{target['title']}》吗？(y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消。")
        return

    # 2. 执行精准删除
    # 删除卡片
    card_to_del = soup.find(id=f"card_{target['id']}")
    if card_to_del: card_to_del.decompose()

    # 删除对应的数据区
    data_to_del = soup.find(id=f"data-{target['id']}")
    if data_to_del: data_to_del.decompose()

    save_soup(soup)
    print(f"🚮 《{target['title']}》已被成功抹除。")

def main():
    while True:
        print("\n=== 御坂鱼坂的博客管理终端 ===")
        print("1. 添加新碎碎念")
        print("2. 抹除旧碎碎念")
        print("q. 退出")
        cmd = input("请选择操作: ").strip().lower()
        
        if cmd == '1':
            add_post()
        elif cmd == '2':
            delete_post()
        elif cmd == 'q':
            print("下次再见，现实扭曲者！")
            break
        else:
            print("❌ 指令错误，请重新输入。")

if __name__ == "__main__":
    main()