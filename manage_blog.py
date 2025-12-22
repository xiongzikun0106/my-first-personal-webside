import json
import os
import hashlib
import time

# --- 基础配置 ---
DATA_DIR = "data"
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")
IMAGES_DIR = "images"  # 你的图片仓库
POSTS_INDEX = os.path.join(DATA_DIR, "posts.json")

# 确保必要的目录存在
os.makedirs(ARTICLES_DIR, exist_ok=True)

def load_posts():
    """读取文章索引列表"""
    if not os.path.exists(POSTS_INDEX):
        return []
    try:
        with open(POSTS_INDEX, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_posts(posts):
    """保存文章索引列表"""
    with open(POSTS_INDEX, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)

def input_multiline():
    """输入正文逻辑"""
    print("\n📝 请输入正文内容 (输入单独一行的 'END' 结束，输入 'UNDO' 撤销上一行):")
    lines = []
    while True:
        line = input(f"[{len(lines)}] > ")
        if line.strip() == 'END':
            break
        elif line.strip().upper() == 'UNDO':
            if lines:
                removed = lines.pop()
                print(f"   已撤销: {removed[:10]}...")
            else:
                print("   没有可以撤销的行了。")
            continue
        lines.append(line)
    return lines

def add_new_post():
    print("\n=== 📄 新建收容文档 ===")
    title = input("请输入标题: ").strip()
    if not title:
        print("❌ 标题不能为空！")
        return

    intro = input("请输入简介 (用于列表显示): ").strip()
    
    # 1. 输入正文
    content_lines = input_multiline()
    if not content_lines:
        print("❌ 正文不能为空！")
        return

    # 2. 插入图片逻辑
    images_list = []
    
    while True:
        print("\n" + "="*40)
        print("👀 当前文档结构预览 (用于定位图片):")
        print(f"[-1] (⚠️ 标题正下方，正文之前)")
        for idx, line in enumerate(content_lines):
            # 这里按照要求，显示完整内容，不截断
            print(f"[{idx}] {line}")
            
            # 显示已绑定的图片
            current_imgs = [img['name'] for img in images_list if img['insert_after'] == idx]
            for img_name in current_imgs:
                print(f"     └── 🖼️  [图片] {img_name}")

        print("="*40)
        
        choice = input("\n需要插入图片吗？(y/n): ").lower()
        if choice != 'y':
            break

        # 图片检查逻辑
        img_name = input("请输入 images 文件夹内的图片文件名 (例如 cat.jpg): ").strip()
        full_img_path = os.path.join(IMAGES_DIR, img_name)
        
        if not os.path.exists(full_img_path):
            print(f"⚠️  警告: 在 {IMAGES_DIR} 下没找到 '{img_name}'。")
            confirm = input("   确定文件名没错且稍后会上传吗？(y/n): ").lower()
            if confirm != 'y':
                continue
        else:
            print("✅ 成功检测到本地图片资源。")

        # 位置选择
        try:
            pos_input = input(f"请输入要插在哪一行后面? (-1 ~ {len(content_lines)-1}): ")
            pos = int(pos_input)
            if pos < -1 or pos >= len(content_lines):
                raise ValueError
            
            # 幂等性/重复性检查：防止同一张图在同一位置重复插入
            is_duplicate = any(img['name'] == img_name and img['insert_after'] == pos for img in images_list)
            if is_duplicate:
                print("⚠️  这张图已经在这个位置了，无需重复添加。")
            else:
                images_list.append({
                    "name": img_name,
                    "insert_after": pos
                })
                print(f"📎 已将 {img_name} 锚定至索引 [{pos}]。")

        except ValueError:
            print("❌ 无效的索引位置！")

    # 3. 生成 ID 并保存
    # 使用 Hash 保证只要标题和时间不同，ID就唯一
    timestamp = str(time.time())
    post_id = f"id_{hashlib.md5((title + timestamp).encode()).hexdigest()[:10]}"
    
    article_data = {
        "id": post_id,
        "title": title,
        "content_lines": content_lines,
        "images": images_list,
        "date": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # 写入文章详情 JSON
    filepath = os.path.join(ARTICLES_DIR, f"{post_id}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=4)

    # 4. 更新索引 (posts.json)
    posts = load_posts()
    new_entry = {
        "id": post_id,
        "title": title,
        "intro": intro
    }
    # 插入到最前面
    posts.insert(0, new_entry)
    save_posts(posts)

    print(f"\n🎉 文档创建成功！ID: {post_id}")
    print(f"   记得 git add . 并提交哦！")

def delete_post():
    print("\n=== 🗑️  删除收容文档 ===")
    posts = load_posts()
    if not posts:
        print("❌ 当前没有任何文档。")
        return

    # 列出所有文章
    for i, post in enumerate(posts):
        print(f"[{i}] {post['title']} (ID: {post['id']})")

    try:
        idx = int(input("\n请输入要删除的序号 (输入 -1 取消): "))
        if idx == -1: return
        if 0 <= idx < len(posts):
            target = posts[idx]
            confirm = input(f"⚠️  确定要永久删除《{target['title']}》吗？(y/n): ").lower()
            if confirm == 'y':
                # 1. 删除详情文件
                file_path = os.path.join(ARTICLES_DIR, f"{target['id']}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"   - 已物理粉碎文档: {file_path}")
                else:
                    print(f"   - 警告: 找不到详情文件 {file_path}，可能已被手动删除。")

                # 2. 从索引移除
                del posts[idx]
                save_posts(posts)
                print("   - 已从索引中抹除记录。")
                print("✅ 删除完成。")
        else:
            print("❌ 无效的序号。")
    except ValueError:
        print("❌ 输入错误。")

def main():
    while True:
        print("\n--- blog manager ---")
        print("1. 新建文章 (New)")
        print("2. 删除文章 (Delete)")
        print("3. 退出 (Exit)")
        choice = input("请选择指令: ").strip()

        if choice == '1':
            add_new_post()
        elif choice == '2':
            delete_post()
        elif choice == '3':
            print("再见，现实扭曲者。")
            break
        else:
            print("无效指令。")

if __name__ == "__main__":
    main()