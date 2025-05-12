#!/usr/bin/env python3
import os
import sys
import platform
import random
import re
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

try:
    import yt_dlp as youtube_dl
    from tqdm import tqdm
    from rich.console import Console
    from rich.prompt import Prompt, IntPrompt
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import print
    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
    import ffmpeg
except ImportError as e:
    print(f"Error: Required module not found - {e}")
    print("Please install dependencies with: pip install yt-dlp tqdm rich ffmpeg-python")
    sys.exit(1)

class DownloadType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLES = "subtitles"

class SocialMediaGrabber:
    def __init__(self):
        self.console = Console()
        self.version = "1.1"
        self.author = "Anmol Khadka"
        self.github = "github.com/Anmol-Khadka/SocialMediaGrabber"
        self.download_dir = self.get_default_download_dir()
        self.supported_platforms = {
            'youtube': ['youtube.com', 'youtu.be'],
            'facebook': ['facebook.com', 'fb.watch'],
            'tiktok': ['tiktok.com'],
            'instagram': ['instagram.com'],
            'twitter': ['twitter.com', 'x.com'],
            'reddit': ['reddit.com'],
            'vimeo': ['vimeo.com'],
            'dailymotion': ['dailymotion.com', 'dai.ly'],
            'soundcloud': ['soundcloud.com']
        }
        self.check_termux_storage()
        self.ffmpeg_path = self.get_ffmpeg_path()

    def get_ffmpeg_path(self) -> str:
        """Get the path to ffmpeg executable"""
        try:
            # Try to find ffmpeg in PATH
            ffmpeg_path = 'ffmpeg'
            subprocess.run([ffmpeg_path, '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return ffmpeg_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If not found, try to use the one from ffmpeg-python
            try:
                import ffmpeg
                return ffmpeg.get_ffmpeg_path()
            except:
                return None

    def check_termux_storage(self):
        """Check and setup Termux storage with better detection"""
        if 'termux' in sys.executable.lower():
            # Check multiple possible download locations
            possible_dirs = [
                '/storage/emulated/0/Download',
                '/data/data/com.termux/files/home/storage/downloads',
                os.path.join(os.path.expanduser('~'), 'downloads')
            ]
            
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    self.download_dir = dir_path
                    return
            
            # If no download directory found, prompt for setup
            self.console.print("[yellow]📱 Termux Storage Not Configured[/yellow]")
            self.console.print("To access your device's Downloads folder, we need to setup storage permissions.")
            
            choice = Prompt.ask(
                "🛠️ Run 'termux-setup-storage' to enable downloads folder access?",
                choices=['y', 'n'],
                default='y'
            )
            
            if choice == 'y':
                try:
                    self.console.print("⏳ Setting up Termux storage...")
                    subprocess.run(['termux-setup-storage'], check=True)
                    
                    # Check again after setup
                    for dir_path in possible_dirs:
                        if os.path.exists(dir_path):
                            self.download_dir = dir_path
                            self.console.print(f"[green]✓ Storage setup complete! Downloads will save to: {self.download_dir}[/green]")
                            return
                    
                    self.console.print("[yellow]⚠️ Storage setup completed but couldn't find Downloads folder[/yellow]")
                except subprocess.CalledProcessError:
                    self.console.print("[red]❌ Failed to setup Termux storage![/red]")
                    self.console.print("Please run 'termux-setup-storage' manually.")
            
            # Fallback to current directory if setup fails
            self.download_dir = os.getcwd()
            self.console.print(f"[yellow]⚠️ Using current directory for downloads: {self.download_dir}[/yellow]")

    def get_default_download_dir(self) -> str:
        """Get the appropriate Downloads folder for the current OS with better detection"""
        system = platform.system()
        
        if system == "Windows":
            downloads = os.path.join(os.environ['USERPROFILE'], 'Downloads')
        elif system == "Linux" and 'ANDROID_ROOT' in os.environ:  # Android
            # Try multiple possible locations
            possible_dirs = [
                '/storage/emulated/0/Download',
                '/data/data/com.termux/files/home/storage/downloads',
                os.path.join(os.path.expanduser('~'), 'downloads')
            ]
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    return dir_path
            return os.getcwd()
        elif system in ["Linux", "Darwin"]:  # macOS is Darwin
            downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        else:
            downloads = os.getcwd()

        # Fallback to current directory if Downloads doesn't exist or isn't writable
        try:
            if not os.path.exists(downloads):
                os.makedirs(downloads, exist_ok=True)
            test_file = os.path.join(downloads, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return downloads
        except (OSError, IOError):
            return os.getcwd()

    def sanitize_filename(self, name: str) -> str:
        """Remove special characters from filename"""
        sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
        return sanitized.strip()

    def detect_platform(self, url: str) -> Optional[str]:
        """Detect which platform the URL belongs to"""
        for platform_name, domains in self.supported_platforms.items():
            if any(domain in url.lower() for domain in domains):
                return platform_name
        return None

    def get_random_filename(self, extension: str = "") -> str:
        """Generate a random filename with given extension"""
        random_num = random.randint(10000, 99999)
        if extension:
            return f"AnmolKhadkaSocialMediaGrabber_{random_num}.{extension}"
        return f"AnmolKhadkaSocialMediaGrabber_{random_num}"

    def get_available_qualities(self, url: str) -> List[Dict[str, Any]]:
        """Get available video qualities for a URL"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': True,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                if not info_dict:
                    return []

                formats = info_dict.get('formats', [])
                video_formats = [
                    f for f in formats 
                    if f.get('vcodec') != 'none' and f.get('height') is not None
                ]
                
                # Sort by resolution descending
                video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                
                # Remove duplicates and create simplified format list
                seen = set()
                unique_formats = []
                for f in video_formats:
                    height = f.get('height', 0)
                    if height not in seen:
                        seen.add(height)
                        unique_formats.append({
                            'height': height,
                            'ext': f.get('ext', 'mp4'),
                            'format_note': f.get('format_note', ''),
                            'format_id': f.get('format_id', '')
                        })
                
                return unique_formats
        except Exception:
            return []

    def show_quality_menu(self, url: str) -> str:
        """Show interactive quality selection menu"""
        qualities = self.get_available_qualities(url)
        
        if not qualities:
            self.console.print("[yellow]⚠️ Could not fetch available qualities. Using best available.[/yellow]")
            return 'best'
        
        table = Table(title="Available Qualities", show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan")
        table.add_column("Resolution", style="green")
        table.add_column("Format", style="yellow")
        
        table.add_row("1", "Best available", "Auto")
        
        for i, quality in enumerate(qualities[:4], 2):  # Show top 4 qualities + best option
            table.add_row(
                str(i),
                f"{quality['height']}p",
                f"{quality['ext']} ({quality['format_note']})"
            )
        
        table.add_row(str(len(qualities)+2), "Manual format selection", "Enter format ID")
        
        self.console.print(table)
        
        while True:
            choice = Prompt.ask(
                "🖥️ Select quality",
                choices=[str(i) for i in range(1, len(qualities)+3)],
                default="1"
            )
            
            if choice == "1":
                return 'best'
            elif choice == str(len(qualities)+2):
                manual_id = Prompt.ask("Enter format ID (use 'best' for best quality)")
                return manual_id
            elif 2 <= int(choice) <= len(qualities)+1:
                return qualities[int(choice)-2]['format_id']
            else:
                self.console.print("[red]❌ Invalid selection. Try again.[/red]")

    def download_media(self, url: str, download_type: DownloadType = DownloadType.VIDEO, quality: str = 'best') -> bool:
        """Download media from URL with specified type and quality"""
        platform_name = self.detect_platform(url)
        if not platform_name:
            self.console.print(f"[red]❌ Unsupported URL or platform: {url}[/red]")
            return False

        # Get output template based on platform
        if platform_name == 'youtube':
            out_template = os.path.join(self.download_dir, '%(title)s.%(ext)s')
        else:
            out_template = os.path.join(self.download_dir, self.get_random_filename('%(ext)s'))

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': out_template,
            'progress_hooks': [self.ytdl_progress_hook],
            'merge_output_format': 'mp4',  # Force mp4 output for videos
        }

        if download_type == DownloadType.AUDIO:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'writethumbnail': True,  # Download thumbnail
                'postprocessor_args': [
                    '-metadata', 'title=%(title)s',
                    '-metadata', 'artist=%(uploader)s',
                    '-metadata', 'album=%(title)s',
                ],
                'embedthumbnail': True,  # Embed thumbnail in audio file
            })
        elif download_type == DownloadType.VIDEO:
            if quality == 'best':
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                ydl_opts['format'] = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best'

        try:
            with Progress(
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                DownloadColumn(),
                TransferSpeedColumn(),
                transient=True,
            ) as progress:
                self.progress = progress
                self.task = progress.add_task("[cyan]Downloading...", total=100)
                
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info_dict)
                    
                    if download_type == DownloadType.AUDIO:
                        filename = os.path.splitext(filename)[0] + '.mp3'
                    
                    self.console.print(f"[green]✓ Download complete:[/green] {filename}")
                    return True
        except Exception as e:
            self.console.print(f"[red]❌ Download failed: {e}[/red]")
            return False
        finally:
            self.progress = None
            self.task = None

    def ytdl_progress_hook(self, d: Dict[str, Any]) -> None:
        """Progress hook for yt-dlp that updates the rich progress bar"""
        if self.progress and self.task:
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total_bytes:
                    downloaded = d['downloaded_bytes']
                    percent = min(100, downloaded / total_bytes * 100)
                    self.progress.update(self.task, completed=percent)

    def batch_download(self, urls: List[str], download_type: DownloadType = DownloadType.VIDEO, quality: str = 'best') -> None:
        """Process multiple URLs for batch download"""
        success_count = 0
        total = len(urls)
        
        with Progress(
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            transient=True,
        ) as progress:
            batch_task = progress.add_task("[cyan]Processing batch...", total=total)
            
            for i, url in enumerate(urls, 1):
                url = url.strip()
                if not url:
                    continue
                    
                progress.console.print(f"\n[bold]📥 Processing URL {i} of {total}:[/bold] {url}")
                if self.download_media(url, download_type, quality):
                    success_count += 1
                progress.update(batch_task, advance=1)
        
        self.console.print(f"\n[green]✓ Batch download complete! {success_count}/{total} succeeded.[/green]")

    def download_subtitles(self, url: str) -> bool:
        """Download subtitles for YouTube videos"""
        if 'youtube' not in self.detect_platform(url):
            self.console.print("[red]❌ Subtitles only supported for YouTube videos[/red]")
            return False

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'srt',
            'subtitleslangs': ['en'],
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'skip_download': True,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.console.print("[green]✓ Subtitles downloaded successfully![/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]❌ Failed to download subtitles: {e}[/red]")
            return False

    def set_download_directory(self) -> None:
        """Prompt user to set a new download directory with better UI"""
        current_dir_panel = Panel(
            f"[cyan]Current download directory:[/cyan]\n[yellow]{self.download_dir}[/yellow]",
            title="Current Directory",
            border_style="blue"
        )
        self.console.print(current_dir_panel)
        
        new_dir = Prompt.ask("📁 Enter new download directory path", default=self.download_dir)
        try:
            if not os.path.exists(new_dir):
                os.makedirs(new_dir, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(new_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            self.download_dir = new_dir
            self.console.print(Panel(
                f"[green]✓ Download directory updated to:[/green]\n[yellow]{new_dir}[/yellow]",
                title="Success",
                border_style="green"
            ))
        except (OSError, IOError) as e:
            self.console.print(Panel(
                f"[red]❌ Error: {e}[/red]\n"
                f"[yellow]⚠️ Using current directory instead: {self.download_dir}[/yellow]",
                title="Error",
                border_style="red"
            ))

    def show_about(self) -> None:
        """Display information about the tool with enhanced UI"""
        about_text = Text()
        about_text.append(f"SocialMediaGrabber v{self.version}\n", style="bold green")
        about_text.append(f"✨ Created by {self.author}\n", style="bold")
        about_text.append(f"🌍 GitHub: {self.github}\n\n")
        about_text.append("📱 A universal social media downloader that supports:\n")
        about_text.append("- YouTube, Facebook, TikTok, Instagram, Twitter/X\n")
        about_text.append("- Reddit, Vimeo, Dailymotion, SoundCloud\n\n")
        about_text.append("🚀 Features:\n")
        about_text.append("- Download HD/full-quality videos (MP4 format)\n")
        about_text.append("- Extract and save MP3 audio with metadata and thumbnails\n")
        about_text.append("- Batch downloads from multiple URLs\n")
        about_text.append("- YouTube subtitle downloads\n")
        about_text.append("- Cross-platform (Windows, macOS, Linux, Android Termux)\n")
        
        self.console.print(Panel(
            about_text,
            title="📝 About SocialMediaGrabber",
            border_style="blue",
            padding=(1, 2)
        ))

    def show_main_menu(self) -> None:
        """Display the enhanced main menu"""
        menu_panel = Panel(
            f"[bold green]🌟 Welcome to SocialMediaGrabber v{self.version}[/bold green]\n"
            f"❤️ Made by {self.author}\n"
            f"🌐 GitHub: {self.github}\n\n"
            f"📂 Current download directory: [yellow]{self.download_dir}[/yellow]",
            title="Main Menu",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(menu_panel)

        menu_table = Table(show_header=False, box=None)
        menu_table.add_column("Option", style="cyan")
        menu_table.add_column("Description", style="white")
        
        menu_table.add_row("1️⃣", "📥 Download Video (HD/full quality)")
        menu_table.add_row("2️⃣", "🎵 Download Audio (MP3 with metadata)")
        menu_table.add_row("3️⃣", "🔄 Batch Download (Multiple URLs)")
        menu_table.add_row("4️⃣", "📝 Download Subtitles (YouTube only)")
        menu_table.add_row("5️⃣", "📁 Set/Change Download Directory)")
        menu_table.add_row("6️⃣", "ℹ️ About This Tool)")
        menu_table.add_row("7️⃣", "🚪 Exit)")
        
        self.console.print(menu_table)

    def process_menu_choice(self) -> None:
        """Process user's menu choice with enhanced UI and error handling"""
        while True:
            try:
                choice = IntPrompt.ask(
                    "\n🔢 Enter your choice (1-7)",
                    choices=[str(i) for i in range(1, 8)],
                    show_choices=False
                )
                
                if choice == 1:  # Download Video
                    url = Prompt.ask("🌐 Enter video URL")
                    quality = self.show_quality_menu(url)
                    self.download_media(url, DownloadType.VIDEO, quality)
                
                elif choice == 2:  # Download Audio
                    url = Prompt.ask("🌐 Enter audio URL")
                    self.download_media(url, DownloadType.AUDIO)
                
                elif choice == 3:  # Batch Download
                    self.console.print(Panel(
                        "📋 Paste multiple URLs (one per line). Press Enter twice to start download.",
                        title="Batch Download",
                        border_style="cyan"
                    ))
                    urls = []
                    while True:
                        line = input()
                        if not line.strip():
                            if urls:
                                break
                            else:
                                continue
                        urls.append(line)
                    
                    download_type = Prompt.ask(
                        "🔘 Download as (1) Video or (2) Audio?",
                        choices=['1', '2'],
                        default='1'
                    )
                    
                    quality = 'best'
                    if download_type == '1':
                        quality = self.show_quality_menu(urls[0]) if urls else 'best'
                    
                    self.batch_download(
                        urls,
                        DownloadType.VIDEO if download_type == '1' else DownloadType.AUDIO,
                        quality
                    )
                
                elif choice == 4:  # Download Subtitles
                    url = Prompt.ask("🌐 Enter YouTube URL")
                    self.download_subtitles(url)
                
                elif choice == 5:  # Set Download Directory
                    self.set_download_directory()
                
                elif choice == 6:  # About
                    self.show_about()
                
                elif choice == 7:  # Exit
                    self.console.print(Panel(
                        "[bold green]👍 Thank you for using SocialMediaGrabber![/bold green]",
                        title="Goodbye",
                        border_style="green"
                    ))
                    sys.exit(0)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]⚠️ Operation cancelled by user.[/yellow]")
                continue
            except Exception as e:
                self.console.print(Panel(
                    f"[red]❌ Error: {str(e)}[/red]",
                    title="Error",
                    border_style="red"
                ))
                continue

    def run(self) -> None:
        """Main entry point for the application"""
        if len(sys.argv) > 1:
            self.handle_cli_args()
        else:
            self.show_main_menu()
            self.process_menu_choice()

    def handle_cli_args(self) -> None:
        """Handle command line arguments with better feedback"""
        if '--version' in sys.argv or '-v' in sys.argv:
            self.console.print(f"SocialMediaGrabber v{self.version}")
            sys.exit(0)
        
        if '--about' in sys.argv or '-a' in sys.argv:
            self.show_about()
            sys.exit(0)
        
        # Handle direct URL downloads from CLI
        if len(sys.argv) >= 3 and sys.argv[1] in ['-d', '--download']:
            url = sys.argv[2]
            download_type = DownloadType.VIDEO
            quality = 'best'
            
            if '-a' in sys.argv or '--audio' in sys.argv:
                download_type = DownloadType.AUDIO
            elif '-q' in sys.argv or '--quality' in sys.argv:
                try:
                    quality_idx = sys.argv.index('-q') if '-q' in sys.argv else sys.argv.index('--quality')
                    quality = sys.argv[quality_idx + 1]
                except IndexError:
                    quality = 'best'
            
            self.download_media(url, download_type, quality)
            sys.exit(0)
        
        self.console.print(Panel(
            "[red]❌ Invalid command line arguments[/red]",
            title="Error",
            border_style="red"
        ))
        self.console.print("Usage:")
        self.console.print("  python SocialMediaGrabber.py [options]")
        self.console.print("\nOptions:")
        usage_table = Table(show_header=False, box=None)
        usage_table.add_column("Option", style="cyan")
        usage_table.add_column("Description", style="white")
        usage_table.add_row("-v, --version", "Show version information")
        usage_table.add_row("-a, --about", "Show about information")
        usage_table.add_row("-d URL, --download URL", "Download from URL directly")
        usage_table.add_row("-a", "Download as audio (with -d)")
        usage_table.add_row("-q QUALITY, --quality QUALITY", "Set video quality (with -d)")
        self.console.print(usage_table)
        sys.exit(1)

if __name__ == "__main__":
    try:
        grabber = SocialMediaGrabber()
        grabber.run()
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
