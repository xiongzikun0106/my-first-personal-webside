import json
import os
import hashlib
import time
from datetime import datetime

# --- 配置区 ---
DATA_DIR = "data"
ARTICLES_DIR = os.path.join(DATA_DIR, "articles")
IMAGES_DIR = "images"
POSTS_INDEX = os.path.join(DATA_DIR, "posts.json")

# 确保目录存在
os.makedirs(ARTICLES_DIR, exist_ok=True)

def load_json(path):
    if not os.path.exists(path): return []
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_new_post():
    print("\n=== 🧪 启动新文档收容程序 ===")
    title = input("请输入文章标题: ").strip()
    intro = input("请输入文章简介 (List预览): ").strip()
    
    # 1. 录入正文
    print("\n📝 请输入正文 (输入 'END' 结束，输入 'UNDO' 撤销上一行):")
    content_lines = []
    while True:
        line = input(f"[{len(content_lines)}] > ")
        if line.strip().upper() == 'END': break
        if line.strip().upper() == 'UNDO' and content_lines:
            content_lines.pop()
            continue
        content_lines.append(line)
    
    # 自动在最后添加时间戳
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_lines.append(f"--- 发布时间：{timestamp_str} ---")

    # 2. 插入图片（仅记录路径，不移动文件）
    images_list = []
    while True:
        print("\n" + "="*50)
        print("🔍 当前内容完整预览（用于定位图片插槽）:")
        print("[-1] -> (标题下方，正文之前)")
        for idx, line in enumerate(content_lines):
            print(f"[{idx}] {line}")
            # 显示该行已绑定的图
            for img in images_list:
                if img['insert_after'] == idx:
                    print(f"     └─🖼️  [图片已锚定]: {img['name']}")
        print("="*50)

        opt = input("\n是否要关联图片？(y/n): ").lower()
        if opt != 'y': break

        img_name = input("请输入 images/ 目录下的文件名 (如 test.jpg): ").strip()
        if not os.path.exists(os.path.join(IMAGES_DIR, img_name)):
            print(f"⚠️  警告：在 images/ 下没找到 {img_name}，请确保稍后手动上传。")

        try:
            pos = int(input(f"要把图片插在第几行后面? (-1 ~ {len(content_lines)-1}): "))
            if -1 <= pos < len(content_lines):
                # 幂等性检查：避免同一位置重复插同一张图
                if any(i['name'] == img_name and i['insert_after'] == pos for i in images_list):
                    print("🚫 发现重复锚定，已忽略。")
                else:
                    images_list.append({"name": img_name, "insert_after": pos})
                    print("✅ 锚定成功。")
            else:
                print("❌ 索引超出现实边界！")
        except ValueError:
            print("❌ 输入不是有效的数字。")

    # 3. 生成唯一 ID 并保存
    post_id = f"id_{hashlib.md5((title + str(time.time())).encode()).hexdigest()[:10]}"
    article_data = {
        "id": post_id,
        "title": title,
        "content_lines": content_lines,
        "images": images_list,
        "date": timestamp_str
    }

    # 幂等性保存：检查文件是否冲突（理论上由于时间戳不会冲突）
    article_path = os.path.join(ARTICLES_DIR, f"{post_id}.json")
    if os.path.exists(article_path):
        print("☢️  发生 ID 碰撞！收容中止。")
        return

    save_json(article_path, article_data)

    # 4. 更新索引
    posts = load_json(POSTS_INDEX)
    posts.insert(0, {"id": post_id, "title": title, "intro": intro})
    save_json(POSTS_INDEX, posts)
    print(f"\n🎉 文档 {post_id} 收容成功！")

def delete_post():
    print("\n=== 🗑️  收容失效/文档处决程序 ===")
    posts = load_json(POSTS_INDEX)
    if not posts:
        print("📂 当前收容室为空。"); return

    for i, p in enumerate(posts):
        print(f"[{i}] {p['title']} ({p['id']})")

    try:
        choice = int(input("\n请输入要处决的文档序号 (输入 -1 取消): "))
        if choice == -1: return
        target = posts.pop(choice)
        
        # 物理删除详情文件
        detail_path = os.path.join(ARTICLES_DIR, f"{target['id']}.json")
        if os.path.exists(detail_path):
            os.remove(detail_path)
            print(f"🔥 已粉碎物理文档: {detail_path}")
        
        save_json(POSTS_INDEX, posts)
        print(f"✅ 已从索引中抹除《{target['title']}》。")
    except Exception as e:
        print(f"❌ 处决失败: {e}")

def main():
    while True:
        print("\n--- 💻 SCP-Mikoto 终端系统 ---")
        print("1. 新建文档 (Add)")
        print("2. 处决文档 (Delete)")
        print("3. 退出系统 (Exit)")
        cmd = input("指令 > ").strip()
        if cmd == '1': add_new_post()
        elif cmd == '2': delete_post()
        elif cmd == '3': break

if __name__ == "__main__":
    main()