# SaveXTube - 智能视频下载机器人

SaveXTube 是一个基于 Telegram 的智能视频下载工具，支持 YouTube、X(Twitter) 等主流平台的视频下载，特别针对 NAS 环境进行了优化。

## 🚀 核心功能

### 📱 Telegram 机器人集成
- 简单易用：用户只需发送视频链接即可开始下载
- 支持多平台：YouTube、X(Twitter) 等主流视频平台
- 即时响应：机器人实时处理下载请求

### 📊 实时进度显示
- **文件信息**：显示视频标题、文件大小
- **下载进度**：实时更新的进度条
- **传输状态**：显示下载速度和剩余时间

### 🐳 Docker 容器化部署
- 完整容器化解决方案，轻松部署到 NAS
- 灵活的路径配置，适应不同存储需求
- 支持热重启，配置更新无需停机

### 📂 智能分类存储
- **自动分类**：根据视频来源自动分类存储
  - X 平台视频 → `/downloads/x/`
  - YouTube 视频 → `/downloads/youtube/`
- **路径自定义**：支持自定义下载目录结构

### 🔄 格式自动转换
- **智能转换**：YouTube webm 格式自动转换为通用的 mp4 格式
- **质量保证**：转换过程保持原视频质量
- **可配置**：支持开启/关闭自动转换功能

### 🔞 NSFW 内容支持
- 通过 Cookies 映射支持 X 平台的受限内容下载
- 安全的认证方式，保护用户隐私

## 🍪 X Platform Cookies 配置

### 步骤 1：登录 X 账户
在浏览器中登录您的 X (Twitter) 账户

### 步骤 2：导出 Cookies
1. 安装浏览器扩展 **Get cookies.txt LOCALLY**
2. 访问 X 平台并使用扩展导出 cookies
3. 将导出的 cookies 保存为 `x_cookies.txt`
4.导出后的内容如下：

#Netscape HTTP Cookie File
#http://curl.haxx.se/rfc/cookie_spec.html
#This is a generated file!  Do not edit.
.x.com	TRUE	/	TRUE	1780546503	XXX	XXXXXXXXXXXXXXXXXXXXXXXXXXXXX
。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。
### 步骤 3：配置 Cookies 路径
将 cookies 文件保存到指定路径：
```
/vol1/1000/docker/SaveXTube/x_cookies.txt
```

### 步骤 4：重启服务
重启 SaveXTube 容器以加载新的 cookies 配置

## 🤖 创建 Telegram 机器人

### 获取 Bot Token
1. 在 Telegram 中搜索 **@BotFather**
2. 发送 `/newbot` 命令创建新机器人
3. 按照提示设置机器人名称和用户名
4. 记录生成的 **Bot Token**，后续配置需要使用

## 🚀 Docker Compose 部署

```yaml
services:
  savextube:
    image: savextube/savextube:v0.1
    container_name: savextube
    restart: unless-stopped
    environment:
      # Telegram 机器人 Token（必填）
      TELEGRAM_BOT_TOKEN: "your_bot_token_here"
      
      # 自动转换设置（可选，默认开启）
      CONVERT_TO_MP4: true
      
      # X 平台 Cookies 路径（可选，仅下载 NSFW 内容时需要）
      X_COOKIES: /app/x/x_cookies.txt
      
      # 容器内下载路径（默认 /downloads）
      DOWNLOAD_PATH: /downloads
      
    volumes:
      # 下载文件存储路径映射
      - /vol1/1000/media/downloads/SaveXTube:/downloads
      
      # X 平台 Cookies 文件映射（可选）
      - /vol1/1000/docker/SaveXTube/x_cookies.txt:/app/x/x_cookies.txt
```

### 配置说明

| 环境变量 | 说明 | 是否必填 | 默认值 |
|---------|------|---------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token | ✅ 必填 | - |
| `CONVERT_TO_MP4` | 是否自动转换 webm 为 mp4 | ❌ 可选 | `true` |
| `X_COOKIES` | X 平台 cookies 文件路径 | ❌ 可选 | - |
| `DOWNLOAD_PATH` | 容器内下载路径 | ❌ 可选 | `/downloads` |

## 📖 使用方法

### 基本使用
1. 启动 SaveXTube 容器
2. 在 Telegram 中找到您创建的机器人
3. 向机器人发送视频链接
4. 机器人自动开始下载并显示进度
5. 下载完成后，文件保存到指定目录

### 支持的链接格式
- **YouTube**: `https://www.youtube.com/watch?v=...`
- **X (Twitter)**: `https://x.com/.../status/...`
- **其他平台**: 持续更新中...

### 文件存储结构
```
/downloads/
├── youtube/          # YouTube 视频
│   ├── video1.mp4
│   └── video2.mp4
└── x/               # X 平台视频
    ├── tweet1.mp4
    └── tweet2.mp4
```

## 🔧 故障排除

### 常见问题

**Q: 机器人无响应？**
- 检查 `TELEGRAM_BOT_TOKEN` 是否正确配置
- 确认容器是否正常运行：`docker logs savextube`

**Q: 无法下载 X 平台 NSFW 内容？**
- 确认已正确配置 `x_cookies.txt` 文件
- 检查 cookies 文件的映射路径是否正确
- 确保 cookies 未过期，必要时重新导出

**Q: 下载的文件找不到？**
- 检查卷映射路径是否正确
- 确认宿主机目录具有适当的读写权限

## 📝 更新日志

### v0.1
- 🎉 首次发布
- ✅ 支持 Telegram 机器人集成
- ✅ 支持 YouTube 和 X 平台视频下载
- ✅ 实现实时进度显示
- ✅ 添加格式自动转换功能
- ✅ 支持 NSFW 内容下载

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进 SaveXTube！

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
