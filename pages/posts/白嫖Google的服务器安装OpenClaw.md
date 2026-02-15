---
title: 白嫖Google的服务器安装OpenClaw
date: '2026-02-15 20:22:57'
updated: '2026-02-15 20:22:57'
categories:
- 技术
tags:
- LLM
- 技术
- 指南
---
>前情提要：要实现此项目的效果你需要一张可以使用外区支付的银行卡，比如Master Card且在Google Cloud中绑定了此银行卡获得了Google送你的300美刀的现金

# Step0: 准备好你的LLM API和聊天平台bot
>这里就不再赘述LLM API的获取方法了，聊天平台的bot以 Telegram为例

- 在Telegram中搜索```@BotFather```
- 开始聊天，发送命令``` /newbot```
- 按照提示，输入你的bot名称
>注：你的bot名称必须是全英文并且以`bot`结尾的

- 创建成功后，BotFather 会给你一个 HTTP API Token（看起来像```123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11```）
- 复制并保存这个 Token，它非常重要，不要分享给他人（这是你的 Bot 认证密钥）
>注：你最好把这个token和你的LLM API都一起复制在你的剪切板上，因为Google Cloud的远程` SSH-in-browser`在你没有操作过后的大概30秒就会断开连接，你在后续配置OpenClaw的过程中是来不及去切换窗口复制的
  
# Step1:选择服务器
- 进入Google Cloud Dashboard 页面，选择Computer Engine选项
>我这里选择了4核CPU和16GB内存的虚拟机，你要是觉得太大了可以调小，毕竟单论OpenClaw不是什么很吃性能的东西

- 转到概览页面，在**新建的资源和后续操作**中选择虚拟机栏目右侧的**SSH**按钮，滞后会单出一个新的名称为**SSH-in-browser**浏览器页面，此页面就是虚拟机的终端了
>注意！服务器默认的系统为Debian

# Step2:配置服务器环境
>注意！OpenClaw在安装过程中我实测唯一需要手动安装的依赖是Node.js （版本≥22）
- 首先安装Node.js

```bash 

sudo apt update
sudo apt upgrade
sudo apt install curl
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```
- 验证安装
```bash
node -v  # 应该输出 v22.x.x
npm -v   # 应该输出 npm 版本
```

# Step3:下载OpenClaw安装包
- 运行命令
```shell
curl -fsSL https://openclaw.ai/install.sh | bash
```

>剩下的？全自动！

- 当然，要是不行的话，你也可以试试从npm安装
```bash
sudo apt update && sudo apt install -y npm #如果没有安装npm的话
npm install -g clawdbot@latest #通过npm安装
```
- 安装完成后，启动配置向导
```bash
openclaw onboard --install-daemon
```
>这里整个安装过程就结束了，很简单对吧，剩下的就按照引导来了哦


最后送上一张诗岸美图
>毕竟我的OpenClaw的人格就是诗岸
![诗岸_五维介质](/assets/shian.png)