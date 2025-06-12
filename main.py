#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any
import time
import threading
import requests
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    import yt_dlp
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install: pip install python-telegram-bot yt-dlp requests")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, base_download_path: str, x_cookies_path: str = None):
        self.base_download_path = Path(base_download_path)
        self.x_cookies_path = x_cookies_path
        
        # 从环境变量获取代理配置
        self.proxy_host = os.getenv('PROXY_HOST')
        if self.proxy_host:
            # 测试代理连接
            if self._test_proxy_connection():
                logger.info(f"代理服务器已配置并连接成功: {self.proxy_host}")
                logger.info(f"yt-dlp 使用代理: {self.proxy_host}")
                # 设置系统代理环境变量
                os.environ['HTTP_PROXY'] = self.proxy_host
                os.environ['HTTPS_PROXY'] = self.proxy_host
                os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
            else:
                logger.warning(f"代理服务器已配置但连接失败: {self.proxy_host}")
                logger.info("yt-dlp 直接连接")
                self.proxy_host = None  # 连接失败时禁用代理
                # 清除系统代理环境变量
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)
                os.environ.pop('NO_PROXY', None)
        else:
            logger.info("代理服务器未配置，将直接连接")
            logger.info("yt-dlp 直接连接")
            # 确保系统代理环境变量被清除
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('NO_PROXY', None)
        
        # 从环境变量获取是否转换格式的配置
        self.convert_to_mp4 = os.getenv('CONVERT_TO_MP4', 'true').lower() == 'true'
        logger.info(f"视频格式转换: {'开启' if self.convert_to_mp4 else '关闭'}")
        
        # 创建下载目录
        self.x_download_path = self.base_download_path / "x"
        self.youtube_download_path = self.base_download_path / "youtube"
        
        self.x_download_path.mkdir(parents=True, exist_ok=True)
        self.youtube_download_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"X 下载路径: {self.x_download_path}")
        logger.info(f"YouTube 下载路径: {self.youtube_download_path}")
        
    def _test_proxy_connection(self) -> bool:
        """测试代理服务器连接"""
        if not self.proxy_host:
            return False
            
        try:
            # 解析代理地址
            proxy_url = urlparse(self.proxy_host)
            proxies = {
                'http': self.proxy_host,
                'https': self.proxy_host
            }
            
            # 设置超时时间为5秒
            response = requests.get('http://www.google.com', 
                                 proxies=proxies, 
                                 timeout=5,
                                 verify=False)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"代理连接测试失败: {str(e)}")
            return False
    
    def is_x_url(self, url: str) -> bool:
        """检查是否为 X (Twitter) URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower() in ['twitter.com', 'x.com', 'www.twitter.com', 'www.x.com']
    
    def is_youtube_url(self, url: str) -> bool:
        """检查是否为 YouTube URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower() in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
    
    def get_download_path(self, url: str) -> Path:
        """根据 URL 确定下载路径"""
        if self.is_x_url(url):
            return self.x_download_path
        elif self.is_youtube_url(url):
            return self.youtube_download_path
        else:
            return self.youtube_download_path
    
    def get_platform_name(self, url: str) -> str:
        """获取平台名称"""
        if self.is_x_url(url):
            return "x"
        elif self.is_youtube_url(url):
            return "youtube"
        else:
            return "other"
    
    def check_ytdlp_version(self) -> Dict[str, Any]:
        """检查yt-dlp版本"""
        try:
            import yt_dlp
            version = yt_dlp.version.__version__
            
            return {
                'success': True,
                'version': version,
                'info': f'yt-dlp 版本: {version}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_video_formats(self, url: str) -> Dict[str, Any]:
        """检查视频的可用格式"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'listformats': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = info.get('formats', [])
                available_formats = []
                
                for fmt in formats[:10]:  # 只显示前10个格式
                    format_info = {
                        'id': fmt.get('format_id', 'unknown'),
                        'ext': fmt.get('ext', 'unknown'),
                        'quality': fmt.get('format_note', 'unknown'),
                        'filesize': fmt.get('filesize', 0)
                    }
                    available_formats.append(format_info)
                
                # 检查是否有高分辨率格式
                has_high_res = any(f.get('height', 0) >= 2160 for f in formats)
                if has_high_res:
                    logger.info("检测到4K分辨率可用")
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'formats': available_formats
                }
                
        except Exception as e:
            logger.error(f"格式检查失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_duplicates(self):
        """清理重复文件"""
        try:
            cleaned_count = 0
            for directory in [self.x_download_path, self.youtube_download_path]:
                if directory.exists():
                    for file in directory.glob("*"):
                        if file.is_file() and " #" in file.name:
                            # 检查是否是视频文件
                            if any(file.name.endswith(ext) for ext in ['.mp4', '.mkv', '.webm', '.mov', '.avi']):
                                try:
                                    file.unlink()
                                    logger.info(f"删除重复文件: {file.name}")
                                    cleaned_count += 1
                                except Exception as e:
                                    logger.error(f"删除文件失败: {e}")
            return cleaned_count
        except Exception as e:
            logger.error(f"清理重复文件失败: {e}")
            return 0
    
    def _generate_display_filename(self, original_filename, timestamp):
        """生成用户友好的显示文件名"""
        try:
            # 移除时间戳前缀
            if original_filename.startswith(f'{timestamp}_'):
                display_name = original_filename[len(f'{timestamp}_'):]
            else:
                display_name = original_filename
            
            # 如果文件名太长，截断它
            if len(display_name) > 35:
                name, ext = os.path.splitext(display_name)
                display_name = name[:30] + "..." + ext
            
            return display_name
        except:
            return original_filename
    
    async def download_video(self, url: str, message_updater=None) -> Dict[str, Any]:
        """下载视频 - 使用简化的进度更新方式"""
        download_path = self.get_download_path(url)
        platform = self.get_platform_name(url)
        
        # 生成唯一的文件名前缀，避免冲突
        import time
        timestamp = int(time.time())
        
        # 设置 yt-dlp 选项 - 根据平台优化格式选择
        if self.is_youtube_url(url):
            # 首先尝试获取视频信息
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    # 获取所有可用的格式
                    formats = info.get('formats', [])
                    logger.info("可用的视频格式:")
                    for f in formats:
                        if f.get('height'):
                            logger.info(f"格式: {f.get('format_id')} - {f.get('height')}p - {f.get('ext')}")
                    
                    # 选择最佳视频和音频流
                    video_streams = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('height')]
                    audio_streams = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                    
                    if video_streams and audio_streams:
                        best_video = max(video_streams, key=lambda f: f.get('height', 0))
                        best_audio = max(audio_streams, key=lambda f: f.get('abr', 0) if f.get('abr') else 0)
                        best_format = f"{best_video['format_id']}+{best_audio['format_id']}"
                        logger.info(f"自动选择最佳格式: {best_format} ({best_video.get('height')}p, {best_video.get('ext')})")
                    else:
                        best_format = 'best'
                        logger.info("使用默认最佳格式")
            except Exception as e:
                logger.error(f"获取视频信息失败: {e}")
                best_format = 'best'
            
            ydl_opts = {
                'outtmpl': str(download_path / f'{timestamp}_%(title)s.%(ext)s'),
                'format': best_format,
                'writeinfojson': False,
                'writedescription': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'nooverwrites': True,
                'restrictfilenames': True,
                'socket_timeout': 30,
                'retries': 10,
                'fragment_retries': 10,
                'extractor_retries': 10,
                'skip_unavailable_fragments': True,
                'nocheckcertificate': True,
                'prefer_insecure': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache',
                }
            }
            
            # 根据配置决定是否添加转换选项
            if self.convert_to_mp4:
                ydl_opts.update({
                    'merge_output_format': 'mp4',
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                })
                logger.info("已启用视频格式转换为 MP4")
            else:
                logger.info("保持原始视频格式")
        else:
            # X (Twitter) 和其他平台配置
            ydl_opts = {
                'outtmpl': str(download_path / f'{timestamp}_%(title)s.%(ext)s'),
                'format': 'best',  # 对X平台使用简单的格式选择
                'writeinfojson': False,
                'writedescription': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'nooverwrites': True,
                'restrictfilenames': True,
                'socket_timeout': 30,
                'retries': 10,
                'fragment_retries': 10,
                'extractor_retries': 10,
                'skip_unavailable_fragments': True,
                'nocheckcertificate': True,
                'prefer_insecure': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache',
                }
            }
        
        # 添加代理配置（如果设置了代理）
        if self.proxy_host:
            ydl_opts['proxy'] = self.proxy_host
            logger.info(f"使用代理服务器下载: {self.proxy_host}")
        else:
            logger.info("未使用代理服务器，直接连接下载")
        
        # 如果是 X URL 且有 cookies，添加 cookies 配置
        if self.is_x_url(url) and self.x_cookies_path and os.path.exists(self.x_cookies_path):
            ydl_opts['cookiefile'] = self.x_cookies_path
            logger.info(f"使用 X cookies: {self.x_cookies_path}")
        
        # 进度信息 - 使用线程安全的方式
        progress_data = {
            'filename': '',
            'total_bytes': 0,
            'downloaded_bytes': 0,
            'speed': 0,
            'status': 'downloading',
            'final_filename': '',
            'last_update': 0,
            'lock': threading.Lock()
        }
        
        def progress_hook(d):
            try:
                with progress_data['lock']:
                    current_time = time.time()
                    
                    if d['status'] == 'downloading':
                        raw_filename = d.get('filename', '')
                        display_filename = os.path.basename(raw_filename) if raw_filename else 'video.mp4'
                        
                        progress_data.update({
                            'filename': display_filename,
                            'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate', 0),
                            'downloaded_bytes': d.get('downloaded_bytes', 0),
                            'speed': d.get('speed', 0),
                            'status': 'downloading'
                        })
                        
                        # 每1秒更新一次进度
                        if current_time - progress_data['last_update'] > 1.0:
                            progress_data['last_update'] = current_time
                            
                            if message_updater:
                                # 直接在当前线程调用更新函数，避免事件循环问题
                                try:
                                    message_updater(progress_data.copy())
                                except Exception as e:
                                    logger.error(f"进度更新回调失败: {e}")
                        
                    elif d['status'] == 'finished':
                        final_filename = d.get('filename', '')
                        display_filename = os.path.basename(final_filename) if final_filename else 'video.mp4'
                        
                        progress_data.update({
                            'filename': display_filename,
                            'status': 'finished',
                            'final_filename': final_filename,
                            'progress': 100.0
                        })
                        
                        if message_updater:
                            try:
                                message_updater(progress_data.copy())
                            except Exception as e:
                                logger.error(f"完成更新回调失败: {e}")
                        
            except Exception as e:
                logger.error(f"进度钩子错误: {str(e)}")
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        def run_download():
            """下载视频"""
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        # 首先尝试获取视频信息
                        info = ydl.extract_info(url, download=False)
                        if not info:
                            raise Exception("无法获取视频信息")
                        
                        # 如果成功获取信息，开始下载
                        ydl.download([url])
                        logger.info("下载成功")
                        return True
                        
                    except Exception as e:
                        logger.error(f"下载失败: {str(e)}")
                        return False
                        
            except Exception as e:
                logger.error(f"下载器初始化失败: {str(e)}")
                return False
        
        try:
            # 运行下载
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, run_download)
            
            if not success:
                return {'success': False, 'error': '下载失败'}
            
            # 等待文件系统同步
            await asyncio.sleep(1)
            
            # 查找下载的文件
            final_file = progress_data.get('final_filename', '')
            downloaded_file = None
            file_size = 0
            original_filename = ""
            
            if final_file and os.path.exists(final_file):
                downloaded_file = final_file
                file_size = os.path.getsize(final_file)
                original_filename = os.path.basename(final_file)
            else:
                # 搜索带时间戳的最新文件
                try:
                    video_files = []
                    for ext in ['*.mp4', '*.mkv', '*.webm', '*.mov', '*.avi']:
                        video_files.extend(download_path.glob(f'{timestamp}_*{ext[1:]}'))
                    
                    if video_files:
                        latest_file = max(video_files, key=lambda f: f.stat().st_mtime)
                        downloaded_file = str(latest_file)
                        file_size = latest_file.stat().st_size
                        original_filename = latest_file.name
                except Exception as e:
                    logger.error(f"搜索下载文件失败: {str(e)}")
            
            if downloaded_file and os.path.exists(downloaded_file):
                file_size_mb = file_size / (1024 * 1024)
                display_filename = self._generate_display_filename(original_filename, timestamp)
                # 获取分辨率信息
                video_width = None
                video_height = None
                try:
                    import ffmpeg
                    probe = ffmpeg.probe(downloaded_file)
                    for stream in probe['streams']:
                        if stream['codec_type'] == 'video':
                            video_width = stream.get('width')
                            video_height = stream.get('height')
                            break
                except Exception as e:
                    logger.warning(f"获取分辨率失败: {e}")
                resolution = f"{video_width}x{video_height}" if video_width and video_height else "未知"
                return {
                    'success': True,
                    'filename': display_filename,
                    'full_path': downloaded_file,
                    'size_mb': round(file_size_mb, 2),
                    'platform': platform,
                    'download_path': str(download_path),
                    'original_filename': original_filename,
                    'resolution': resolution
                }
            else:
                return {'success': False, 'error': '无法找到下载的文件'}
                
        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            return {'success': False, 'error': str(e)}

class TelegramBot:
    def __init__(self, token: str, downloader: VideoDownloader):
        self.downloader = downloader
        # 配置 Telegram Bot 的代理
        if self.downloader.proxy_host:
            logger.info(f"Telegram Bot 使用代理: {self.downloader.proxy_host}")
            self.application = Application.builder().token(token).proxy(self.downloader.proxy_host).build()
        else:
            logger.info("Telegram Bot 直接连接")
            self.application = Application.builder().token(token).build()
        self.active_downloads = {}
        
    async def version_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /version 命令 - 显示版本信息"""
        try:
            version_info = self.downloader.check_ytdlp_version()
            
            if version_info['success']:
                version_text = f"""系统版本信息

yt-dlp: {version_info['version']}
Python: {sys.version.split()[0]}
机器人: v2.0 (YouTube修复版)

支持的功能:
✅ 多级格式尝试
✅ 自动格式回退
✅ 智能错误恢复
✅ 详细调试日志

如果下载仍有问题，请使用 /formats 命令检查视频格式"""
                
                await update.message.reply_text(version_text)
            else:
                await update.message.reply_text(f"无法获取版本信息: {version_info['error']}")
                
        except Exception as e:
            await update.message.reply_text(f"版本检查失败: {str(e)}")
    
    async def formats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /formats 命令 - 检查视频格式"""
        try:
            # 获取用户发送的URL
            if not context.args:
                await update.message.reply_text("""格式检查命令

使用方法：
/formats <视频链接>

示例：
/formats https://www.youtube.com/watch?v=xxx

此命令会显示视频的可用格式，帮助调试下载问题。""")
                return
            
            url = context.args[0]
            
            # 验证URL
            if not url.startswith(('http://', 'https://')):
                await update.message.reply_text("请提供有效的视频链接")
                return
            
            check_message = await update.message.reply_text("正在检查视频格式...")
            
            # 检查格式
            result = self.downloader.check_video_formats(url)
            
            if result['success']:
                formats_text = f"""视频格式信息

标题：{result['title']}

可用格式（前10个）：
"""
                for i, fmt in enumerate(result['formats'], 1):
                    size_info = ""
                    if fmt['filesize'] and fmt['filesize'] > 0:
                        size_mb = fmt['filesize'] / (1024 * 1024)
                        size_info = f" ({size_mb:.1f}MB)"
                    
                    formats_text += f"{i}. ID: {fmt['id']} | {fmt['ext']} | {fmt['quality']}{size_info}\n"
                
                formats_text += "\n如果下载失败，可以尝试其他视频或报告此信息。"
                
                await check_message.edit_text(formats_text)
            else:
                await check_message.edit_text(f"格式检查失败: {result['error']}")
                
        except Exception as e:
            await update.message.reply_text(f"格式检查出错: {str(e)}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_message = """视频下载机器人已启动！

支持的平台：
• X (Twitter)
• YouTube

使用方法：
直接发送视频链接即可开始下载

命令：
• /start - 显示此帮助信息
• /status - 查看下载统计
• /cleanup - 清理重复文件
• /formats <链接> - 检查视频格式

特性：
✅ 实时下载进度显示
✅ 智能格式选择和备用方案
✅ 自动格式转换 (YouTube webm → mp4)
✅ 按平台分类存储
✅ 支持 NSFW 内容下载
✅ 唯一文件名，避免覆盖

YouTube 下载优化：
• 自动选择最佳质量
• 格式不可用时自动使用备用格式
• 强制转换为 mp4 格式"""
        await update.message.reply_text(welcome_message)
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /cleanup 命令"""
        cleanup_message = await update.message.reply_text("开始清理重复文件...")
        
        try:
            cleaned_count = self.downloader.cleanup_duplicates()
            
            if cleaned_count > 0:
                completion_text = f"""清理完成!
删除了 {cleaned_count} 个重复文件
释放了存储空间"""
            else:
                completion_text = "清理完成! 未发现重复文件"
                
            await cleanup_message.edit_text(completion_text)
        except Exception as e:
            await cleanup_message.edit_text(f"清理失败: {str(e)}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令"""
        try:
            # 统计文件
            video_extensions = ['*.mp4', '*.mkv', '*.webm', '*.mov', '*.avi']
            
            x_files = []
            youtube_files = []
            
            for ext in video_extensions:
                x_files.extend(self.downloader.x_download_path.glob(ext))
                youtube_files.extend(self.downloader.youtube_download_path.glob(ext))
            
            total_size = 0
            for file_list in [x_files, youtube_files]:
                for file in file_list:
                    try:
                        total_size += file.stat().st_size
                    except:
                        pass
            
            total_size_mb = total_size / (1024 * 1024)
            
            status_text = f"""下载统计

X 视频: {len(x_files)} 个文件
YouTube 视频: {len(youtube_files)} 个文件
总计: {len(x_files) + len(youtube_files)} 个文件
总大小: {total_size_mb:.2f}MB

机器人状态: 正常运行
活跃下载: {len(self.active_downloads)} 个"""

            await update.message.reply_text(status_text)
        except Exception as e:
            await update.message.reply_text(f"获取状态失败: {str(e)}")
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 URL 消息"""
        url = update.message.text.strip()
        
        # 验证 URL 格式
        if not url.startswith(('http://', 'https://')):
            await update.message.reply_text("请发送有效的视频链接")
            return
        
        # 检查是否支持的平台
        if not (self.downloader.is_x_url(url) or self.downloader.is_youtube_url(url)):
            await update.message.reply_text("目前只支持 X (Twitter) 和 YouTube 链接")
            return
        
        chat_id = update.effective_chat.id
        
        # 检查是否有正在进行的下载
        if chat_id in self.active_downloads:
            await update.message.reply_text("有下载任务正在进行中，请等待完成后再试")
            return
        
        platform = "X" if self.downloader.is_x_url(url) else "YouTube"
        
        # 发送开始下载消息
        progress_message = await update.message.reply_text(f"开始下载 {platform} 视频...")
        
        # 获取当前事件循环引用
        current_loop = asyncio.get_running_loop()
        
        # 创建线程安全的进度更新器
        def update_progress(progress_info):
            """线程安全的进度更新函数"""
            try:
                filename = progress_info.get('filename', 'video.mp4')
                total_bytes = progress_info.get('total_bytes', 0)
                downloaded_bytes = progress_info.get('downloaded_bytes', 0)
                speed = progress_info.get('speed', 0)
                status = progress_info.get('status', 'downloading')
                
                # 生成用户友好的文件名显示
                display_filename = self._clean_filename_for_display(filename)
                
                if status == 'finished' or progress_info.get('progress') == 100.0:
                    progress = 100.0
                    progress_bar = self._create_progress_bar(progress)
                    size_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else downloaded_bytes / (1024 * 1024)
                    
                    progress_text = f"""📝 文件：{display_filename}
💾 大小：{size_mb:.2f}MB
⚡ 速度：完成
📊 进度：{progress_bar} ({progress:.1f}%)"""
                    
                    # 使用事件循环引用安全更新
                    asyncio.run_coroutine_threadsafe(
                        progress_message.edit_text(progress_text),
                        current_loop
                    )
                    return
                
                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                    progress_bar = self._create_progress_bar(progress)
                    
                    size_mb = total_bytes / (1024 * 1024)
                    speed_mb = (speed or 0) / (1024 * 1024)
                    
                    progress_text = f"""📝 文件：{display_filename}
💾 大小：{size_mb:.2f}MB
⚡ 速度：{speed_mb:.2f}MB/s
📊 进度：{progress_bar} ({progress:.1f}%)"""
                    
                    # 使用事件循环引用安全更新
                    asyncio.run_coroutine_threadsafe(
                        progress_message.edit_text(progress_text),
                        current_loop
                    )
                else:
                    # 没有总大小信息时的显示
                    downloaded_mb = downloaded_bytes / (1024 * 1024) if downloaded_bytes > 0 else 0
                    speed_mb = (speed or 0) / (1024 * 1024)
                    
                    progress_text = f"""📝 文件：{display_filename}
💾 大小：{downloaded_mb:.2f}MB
⚡ 速度：{speed_mb:.2f}MB/s
📊 进度：下载中..."""
                    
                    asyncio.run_coroutine_threadsafe(
                        progress_message.edit_text(progress_text),
                        current_loop
                    )
                    
            except Exception as e:
                logger.error(f"进度更新失败: {e}")
        
        # 标记下载开始
        self.active_downloads[chat_id] = True
        
        try:
            # 开始下载，传入进度更新函数
            result = await self.downloader.download_video(url, update_progress)
            
            if result['success']:
                # 生成用户友好的文件名显示
                display_filename = self._clean_filename_for_display(result['filename'])
                resolution = result.get('resolution', '未知')
                completion_text = f"""下载完成!
📝 文件名：{display_filename}
📂 保存位置：{result['platform']} 文件夹
💾 文件大小：{result['size_mb']}MB
🎥 分辨率：{resolution}
✅ 进度：████████████████████ (100%)"""
                
                await progress_message.edit_text(completion_text)
            else:
                await progress_message.edit_text(f"下载失败：{result['error']}")
                
        except Exception as e:
            logger.error(f"下载过程中发生错误: {str(e)}")
            await progress_message.edit_text(f"下载失败：{str(e)}")
        finally:
            # 清除下载标记
            self.active_downloads.pop(chat_id, None)
    
    def _clean_filename_for_display(self, filename):
        """清理文件名用于显示"""
        try:
            # 移除时间戳前缀如果存在
            import re
            if re.match(r'^\d{10}_', filename):
                display_name = filename[11:]
            else:
                display_name = filename
            
            # 如果文件名太长，进行智能截断
            if len(display_name) > 35:
                name, ext = os.path.splitext(display_name)
                display_name = name[:30] + "..." + ext
            
            return display_name
        except:
            return filename if len(filename) <= 35 else filename[:32] + "..."
    
    def _create_progress_bar(self, progress: float, length: int = 20) -> str:
        """创建进度条"""
        filled_length = int(length * progress / 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return bar
    
    def run(self):
        """启动机器人"""
        logger.info("Telegram 视频下载机器人启动中...")
        
        # 添加处理器
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("cleanup", self.cleanup_command))
        self.application.add_handler(CommandHandler("formats", self.formats_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        
        logger.info("程序已经正常启动")
        
        # 启动机器人
        self.application.run_polling()

def main():
    """主函数"""
    # 从环境变量获取配置
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    download_path = os.getenv('DOWNLOAD_PATH', '/downloads')
    x_cookies_path = os.getenv('X_COOKIES')
    
    if not bot_token:
        logger.error("请设置 TELEGRAM_BOT_TOKEN 环境变量")
        sys.exit(1)
    
    logger.info(f"下载路径: {download_path}")
    if x_cookies_path:
        logger.info(f"X Cookies 路径: {x_cookies_path}")
    
    # 创建下载器和机器人
    downloader = VideoDownloader(download_path, x_cookies_path)
    bot = TelegramBot(bot_token, downloader)
    
    # 启动机器人
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("机器人已停止")
    except Exception as e:
        logger.error(f"机器人运行出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
