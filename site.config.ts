import { defineSiteConfig } from 'valaxy'

export default defineSiteConfig({
  // 站点语言
  lang: 'zh-CN',
  // 站点标题
  title: '御坂鱼坂的电子牢房',
  // 站点副标题  
  subtitle: '诗起此方，终碎彼岸',
  // 站点描述
  description: '大概是一个很无聊的个人主页？！',
  // 作者
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
  ],
  // 搜索配置
  search: {
    enable: true,
    type: 'fuse'
  },
  // 版权声明
  license: {
    enabled: true,
    language: 'zh-CN',
    type: 'CC BY-NC-SA 4.0'
  }
})
