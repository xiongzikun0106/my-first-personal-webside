import hashlib
import html
import json
import os
import sys

# === 配置区 ===
DATA_DIR = "data"
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")
INDEX_FILE = os.path.join(DATA_DIR, "posts.json")
MAX_CONTENT_CHARS = 200_000

def ensure_structure():
    """确保收容设施（文件夹结构）完整"""
    if not os.path.exists(ARTICLES_DIR):
        os.makedirs(ARTICLES_DIR)
        print(f"🛠️ 已建立收容区: {ARTICLES_DIR}")
    
    if not os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("📄 已初始化空白索引文件。")

def load_index():
    """读取现有的收容目录"""
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ 索引文件损坏，已重置为空列表。")
        return []

def save_index(posts):
    """保存目录"""
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

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
    ensure_structure()
    posts = load_index()

    print("\n--- 📝 编写新碎碎念 ---")
    title = input("请输入文章标题: ").strip()
    if not title:
        print("❌ 标题不能为空，无名之物无法被收容。")
        return

    # === 幂等性与重复检查 ===
    if any(p['title'] == title for p in posts):
        print(f"⚠️ 警告：标题为《{title}》的文章已存在！")
        print("为了防止时空悖论（等幂性），操作已终止。如需修改请先删除旧文。")
        return

    intro = input("请输入简介: ").strip()
    content_raw = multiline_input("请输入正文:")
    img_name = input("图片文件名（images/ 路径下，无图请直接回车）: ").strip()

    if len(content_raw) > MAX_CONTENT_CHARS:
        print(f"❌ 内容溢出！你是想把整个 Wiki 塞进去吗？")
        return

    post_id = generate_id(title)

    # 处理内容：转义 HTML 以防注入，但保留换行符转换
    # 这样 JS 里的 innerHTML 既安全又能显示换行
    esc_title = html.escape(title)
    esc_intro = html.escape(intro)
    esc_content = html.escape(content_raw).replace("\n", "<br>")

    # 1. 创建单篇文章的数据文件
    article_data = {
        "id": post_id,
        "title": esc_title,
        "content": esc_content,
        "image": img_name
    }
    
    article_path = os.path.join(ARTICLES_DIR, f"{post_id}.json")
    with open(article_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=2)

    # 2. 更新索引列表（只存元数据，不存全文，保持加载速度）
    new_entry = {
        "id": post_id,
        "title": esc_title,
        "intro": esc_intro
    }
    posts.insert(0, new_entry) # 新文章放最前面
    save_index(posts)

    print(f"🎉 《{title}》收容成功！ID: {post_id}")
    print(f"💾 数据已存入: {article_path}")

def delete_post():
    ensure_structure()
    posts = load_index()

    if not posts:
        print("📭 收容区空空如也。")
        return

    print("\n--- 🗑️ 删除碎碎念 ---")
    for idx, post in enumerate(posts):
        print(f"[{idx}] {post['title']} (ID: {post['id']})")

    choice = input("\n请输入要删除的编号 (q 退出): ").strip()
    if choice.lower() == 'q': return

    try:
        target_idx = int(choice)
        target = posts[target_idx]
    except (ValueError, IndexError):
        print("❌ 目标锁定失败。")
        return

    confirm = input(f"❗ 确定要抹除《{target['title']}》吗？(y/n): ").strip().lower()
    if confirm != 'y': return

    # 1. 删除文件
    file_path = os.path.join(ARTICLES_DIR, f"{target['id']}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"🔥 物理文档已销毁: {file_path}")
    else:
        print("⚠️ 物理文档已丢失（可能已被删除），正在清理索引...")

    # 2. 更新索引
    posts.pop(target_idx)
    save_index(posts)
    print("✅ 索引记录已清除。")

def main():
    while True:
        print("\n=== 御坂鱼坂的博客收容终端 v2.0 ===")
        print("1. 收容新项目 (Add)")
        print("2. 处决旧项目 (Delete)")
        print("q. 退出连接")
        cmd = input("指令: ").strip().lower()
        
        if cmd == '1':
            add_post()
        elif cmd == '2':
            delete_post()
        elif cmd == 'q':
            print("再见，Reality Bender。")
            break
        else:
            print("❌ 未知指令。")

if __name__ == "__main__":
    main()