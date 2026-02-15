import { defineValaxyConfig } from 'valaxy'
import type { UserThemeConfig } from 'valaxy-theme-yun'

// 更多配置参考: https://valaxy.site/guide/config
export default defineValaxyConfig<UserThemeConfig>({
  // 站点配置
  siteConfig: {
    // 站点标题
    title: '御坂鱼坂的电子牢房',
    // 站点副标题
    subtitle: '诗起此方，终碎彼岸',
    // 站点描述
    description: '大概是一个很无聊的个人主页？！',
    // 作者信息
    author: {
      name: '御坂鱼坂',
      avatar: '/images/avatar.jpg',
      status: {
        emoji: '🐟',
        message: '这个人很懒，什么都没留下'
      }
    },
    // 站点URL
    url: 'https://mikotossd.net/',
    // 站点语言
    lang: 'zh-CN',
    // 站点favicon
    favicon: '/favicon.ico',
    // 搜索配置
    search: {
      enable: true,
      type: 'fuse'
    },
    // 文章加密 (可选)
    encrypt: {
      enable: false
    },
    // 评论系统 (可后续配置)
    comment: {
      enable: false
    },
    // 社交链接
    social: [
      {
        name: 'Twitter / X',
        link: 'https://x.com/mikotossd0106',
        icon: 'i-ri-twitter-x-fill',
        color: '#000'
      },
      {
        name: 'Bilibili',
        link: 'https://space.bilibili.com/514128180',
        icon: 'i-ri-bilibili-fill',
        color: '#FF8EB3'
      },
      {
        name: 'Telegram',
        link: 'https://t.me/+85vc8uK_ebUyM2E1',
        icon: 'i-ri-telegram-fill',
        color: '#0088CC'
      }
    ]
  },

  // Yun 主题配置
  theme: 'yun',
  themeConfig: {
    // 主题颜色
    colors: {
      primary: '#3498db'
    },

    // 横幅配置
    banner: {
      enable: true,
      title: '御坂鱼坂',
      cloud: {
        enable: true
      }
    },

    // 背景配置
    bg_image: {
      enable: true,
      url: '/images/bg.jpg',
      dark: '/images/bg-dark.jpg',
      opacity: 0.8
    },

    // 页脚配置
    footer: {
      since: 2025,
      beian: {
        enable: false
      },
      powered: true
    },

    // 侧边栏配置
    aside: {
      // 标签云
      tags: {
        enable: true
      },
      // 分类
      categories: {
        enable: true
      }
    },

    // 文章配置
    post: {
      // 字数统计
      wordCount: true,
      // 阅读时间
      readingTime: true
    },

    // 首页配置
    pages: [
      {
        name: '友链',
        url: '/links/',
        icon: 'i-ri-link',
        color: '#8e71c1'
      },
      {
        name: '归档',
        url: '/archives/',
        icon: 'i-ri-archive-line',
        color: '#e74c3c'
      },
      {
        name: '分类',
        url: '/categories/',
        icon: 'i-ri-folder-2-line',
        color: '#27ae60'
      },
      {
        name: '标签',
        url: '/tags/',
        icon: 'i-ri-price-tag-3-line',
        color: '#3498db'
      }
    ],

    // 打赏配置 (可选)
    sponsor: {
      enable: false
    },

    // 菜单配置
    menu: {
      custom: {
        title: '关于',
        url: '/about/',
        icon: 'i-ri-information-line'
      }
    }
  },

  // Markdown 配置
  markdown: {
    // KaTeX 数学公式支持
    katex: {
      enable: true,
      options: {}
    },
    // 代码高亮
    codeHighlight: {
      theme: 'one-dark-pro'
    }
  }
})
