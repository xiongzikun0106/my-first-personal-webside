# Valaxy 博客迁移指南

## 📁 项目结构

```
valaxy-blog/
├── pages/
│   ├── posts/           # 博客文章
│   │   ├── birthday-16.md
│   │   ├── wasted-evening-study.md
│   │   ├── projector-cliff.md
│   │   ├── instant-noodles.md
│   │   ├── 2025-annual-summary.md
│   │   ├── christmas-day.md
│   │   ├── christmas-eve.md
│   │   ├── nano-banana-shian.md
│   │   └── shian-poem.md
│   ├── about.md         # 关于页面
│   ├── links.md         # 友链页面
│   ├── archives.md      # 归档页面
│   ├── categories.md    # 分类页面
│   ├── tags.md          # 标签页面
│   └── index.md         # 首页
├── public/
│   └── images/          # 图片资源
├── styles/
│   └── index.scss       # 自定义样式
├── valaxy.config.ts     # Valaxy 配置
├── site.config.ts       # 站点配置
├── package.json
└── tsconfig.json
```

## 🚀 安装步骤

### 1. 安装 Node.js 和 pnpm

确保已安装 Node.js 18+ 和 pnpm：

```powershell
# 检查 Node.js 版本
node -v

# 安装 pnpm（如果未安装）
npm install -g pnpm
```

### 2. 进入项目目录

```powershell
cd D:\myWeb\valaxy-blog
```

### 3. 复制图片资源

将旧博客的图片复制到新项目：

```powershell
# 复制所有图片
Copy-Item -Path "D:\myWeb\images\*" -Destination "D:\myWeb\valaxy-blog\public\images\" -Recurse

# 将头像重命名
Copy-Item -Path "D:\myWeb\valaxy-blog\public\images\image01.jpg" -Destination "D:\myWeb\valaxy-blog\public\images\avatar.jpg"
```

### 4. 安装依赖

```powershell
pnpm install
```

### 5. 启动开发服务器

```powershell
pnpm dev
```

浏览器访问 `http://localhost:4859` 即可预览博客。

### 6. 构建生产版本

```powershell
pnpm build
```

构建产物在 `dist/` 目录。

### 7. 预览构建结果

```powershell
pnpm preview
```

## 📝 文章分类体系

根据你的内容，我重新规划了以下分类：

| 分类 | 说明 |
|------|------|
| 生活随笔 | 个人生活记录、心情 |
| 校园日常 | 学校生活、晚自习、活动 |
| 意识流 | 诗意、随想、意识流写作 |
| 年度总结 | 年度回顾与总结 |
| AI创作 | AI 生成的内容 |

## 🏷️ 标签体系

- **心情类**: 心情、成长、随笔、诗意
- **时间类**: 生日、节日、平安夜、圣诞节
- **内容类**: 诗岸、AI、创作、总结、回顾
- **日常类**: 晚自习、寝室、泡面、搞事、日常

## ⚙️ 配置说明

### 修改站点信息

编辑 `valaxy.config.ts` 中的 `siteConfig.author` 部分。

### 修改主题颜色

编辑 `valaxy.config.ts` 中的 `themeConfig.colors.primary`。

### 添加评论系统

在 `valaxy.config.ts` 中配置 `siteConfig.comment`，支持多种评论系统。

### 添加数学公式支持

已默认启用 KaTeX，在文章中使用：

```markdown
行内公式: $E = mc^2$

块级公式:
$$
\int_{a}^{b} f(x)dx = F(b) - F(a)
$$
```

## 🌐 部署

### GitHub Pages

1. 创建 GitHub 仓库
2. 添加 `.github/workflows/deploy.yml`
3. 推送代码即可自动部署

### Vercel / Netlify

直接连接 GitHub 仓库，配置构建命令 `pnpm build`，发布目录 `dist`。

## ❓ 常见问题

### 图片不显示

确保图片已复制到 `public/images/` 目录，并且路径以 `/images/` 开头。

### 样式问题

自定义样式在 `styles/index.scss` 中修改。

### 添加新文章

在 `pages/posts/` 目录下创建新的 `.md` 文件，格式：

```markdown
---
title: 文章标题
date: 2026-01-01 12:00:00
categories:
  - 分类名
tags:
  - 标签1
  - 标签2
excerpt: 文章摘要
cover: /images/cover.jpg  # 可选
---

正文内容...
```

---

**御坂鱼坂的电子牢房** - Powered by Valaxy & Yun Theme
