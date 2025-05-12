#!/usr/bin/env python3
import os
import sys
import platform
import random
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import yt_dlp as youtube_dl
    from tqdm import tqdm
    from rich.console import Console
    from rich.prompt import Prompt, IntPrompt
    from rich.panel import Panel
    from rich.text import Text
    from rich import print
    import ffmpeg
except ImportError as e:
    print(f"Error: Required module not found - {e}")
    print("Please install dependencies with: pip install yt-dlp tqdm rich ffmpeg-python")
    sys.exit(1)

class SocialMediaGrabber:
    def __init__(self):
        self.console = Console()
        self.version = "1.0"
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

    def check_termux_storage(self):
        """Check and prompt for Termux storage setup if needed"""
        if 'termux' in sys.executable and not os.path.exists('/data/data/com.termux/files/home/storage'):
            self.console.print("[yellow]Termux storage not set up![/yellow]")
            choice = Prompt.ask("Run 'termux-setup-storage' to enable downloads folder access? (y/n)", choices=['y', 'n'], default='y')
            if choice == 'y':
                try:
                    subprocess.run(['termux-setup-storage'], check=True)
                    self.console.print("[green]Termux storage setup complete![/green]")
                except subprocess.CalledProcessError:
                    self.console.print("[red]Failed to setup Termux storage![/red]")
                    self.console.print("Please run 'termux-setup-storage' manually.")
                    self.download_dir = os.getcwd()

    def get_default_download_dir(self) -> str:
        """Get the appropriate Downloads folder for the current OS"""
        system = platform.system()
        
        if system == "Windows":
            downloads = os.path.join(os.environ['USERPROFILE'], 'Downloads')
        elif system == "Linux" and 'ANDROID_ROOT' in os.environ:  # Termux/Android
            downloads = '/data/data/com.termux/files/home/storage/downloads'
            if not os.path.exists(downloads):
                downloads = os.path.join(os.path.expanduser('~'), 'downloads')
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

    def get_random_filename(self, extension: str) -> str:
        """Generate a random filename with given extension"""
        random_num = random.randint(10000, 99999)
        return f"AnmolKhadkaSocialMediaGrabber_{random_num}.{extension}"

    def download_media(self, url: str, download_type: str = 'video', quality: str = 'best') -> bool:
        """Download media from URL with specified type and quality"""
        platform_name = self.detect_platform(url)
        if not platform_name:
            self.console.print(f"[red]Unsupported URL or platform: {url}[/red]")
            return False

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [self.progress_hook],
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s') if platform_name == 'youtube' 
                      else os.path.join(self.download_dir, self.get_random_filename('%(ext)s')),
            'format': self.get_best_format(platform_name, download_type, quality),
        }

        if download_type == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info_dict)
                
                if download_type == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
                
                self.console.print(f"[green]Download complete:[/green] {filename}")
                return True
        except Exception as e:
            self.console.print(f"[red]Download failed: {e}[/red]")
            return False

    def get_best_format(self, platform: str, download_type: str, quality: str) -> str:
        """Determine the best format for download"""
        if download_type == 'audio':
            return 'bestaudio/best'
        
        if quality == 'best':
            if platform == 'youtube':
                return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                return 'best'
        else:
            return f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'

    def progress_hook(self, d: Dict[str, Any]) -> None:
        """Progress hook for displaying download progress"""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = d['downloaded_bytes'] / total_bytes * 100
                self.console.print(f"Downloading: {percent:.1f}% complete", end='\r')

    def batch_download(self, urls: List[str], download_type: str = 'video', quality: str = 'best') -> None:
        """Process multiple URLs for batch download"""
        success_count = 0
        total = len(urls)
        
        for i, url in enumerate(urls, 1):
            url = url.strip()
            if not url:
                continue
                
            self.console.print(f"\n[bold]Processing URL {i} of {total}:[/bold] {url}")
            if self.download_media(url, download_type, quality):
                success_count += 1
        
        self.console.print(f"\n[green]Batch download complete! {success_count}/{total} succeeded.[/green]")

    def download_subtitles(self, url: str) -> bool:
        """Download subtitles for YouTube videos"""
        if 'youtube' not in self.detect_platform(url):
            self.console.print("[red]Subtitles only supported for YouTube videos[/red]")
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
            self.console.print("[green]Subtitles downloaded successfully![/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to download subtitles: {e}[/red]")
            return False

    def set_download_directory(self) -> None:
        """Prompt user to set a new download directory"""
        new_dir = Prompt.ask("Enter new download directory path", default=self.download_dir)
        try:
            if not os.path.exists(new_dir):
                os.makedirs(new_dir, exist_ok=True)
            
            test_file = os.path.join(new_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            self.download_dir = new_dir
            self.console.print(f"[green]Download directory set to: {new_dir}[/green]")
        except (OSError, IOError) as e:
            self.console.print(f"[red]Error: {e}[/red]")
            self.console.print("[yellow]Using current directory instead.[/yellow]")
            self.download_dir = os.getcwd()

    def show_about(self) -> None:
        """Display information about the tool"""
        about_text = Text()
        about_text.append(f"SocialMediaGrabber v{self.version}\n", style="bold green")
        about_text.append(f"Created by {self.author}\n")
        about_text.append(f"GitHub: {self.github}\n\n")
        about_text.append("A universal social media downloader that supports:\n")
        about_text.append("- YouTube, Facebook, TikTok, Instagram, Twitter/X\n")
        about_text.append("- Reddit, Vimeo, Dailymotion, SoundCloud\n\n")
        about_text.append("Features:\n")
        about_text.append("- Download HD/full-quality videos\n")
        about_text.append("- Extract and save MP3 audio\n")
        about_text.append("- Batch downloads from multiple URLs\n")
        about_text.append("- YouTube subtitle downloads\n")
        
        self.console.print(Panel(about_text, title="About SocialMediaGrabber", border_style="blue"))

    def show_menu(self) -> None:
        """Display the main menu"""
        self.console.print(Panel(
            f"[bold green]Welcome to SocialMediaGrabber v{self.version}[/bold green]\n"
            f"Made with ❤️ by {self.author}\n"
            f"GitHub: {self.github}\n\n"
            f"Current download directory: [yellow]{self.download_dir}[/yellow]",
            title="Main Menu",
            border_style="blue"
        ))

        self.console.print("\n[bold]Select an option:[/bold]")
        self.console.print("1️⃣ Download Video (HD/full quality)")
        self.console.print("2️⃣ Download Audio (MP3 only)")
        self.console.print("3️⃣ Batch Download (Paste multiple URLs)")
        self.console.print("4️⃣ Download Subtitles (YouTube only)")
        self.console.print("5️⃣ Set/Change Download Directory")
        self.console.print("6️⃣ About This Tool")
        self.console.print("7️⃣ Exit")

    def process_menu_choice(self) -> None:
        """Process user's menu choice"""
        while True:
            try:
                choice = IntPrompt.ask("\nEnter your choice (1-7)", choices=[str(i) for i in range(1, 8)])
                
                if choice == 1:  # Download Video
                    url = Prompt.ask("Enter video URL")
                    quality = Prompt.ask("Enter preferred resolution (e.g., 720, 1080) or 'best'", default="best")
                    self.download_media(url, 'video', quality)
                
                elif choice == 2:  # Download Audio
                    url = Prompt.ask("Enter audio URL")
                    self.download_media(url, 'audio')
                
                elif choice == 3:  # Batch Download
                    self.console.print("Paste multiple URLs (one per line). Press Enter twice to start download.")
                    urls = []
                    while True:
                        line = input()
                        if not line.strip():
                            if urls:
                                break
                            else:
                                continue
                        urls.append(line)
                    
                    download_type = Prompt.ask("Download as (1) Video or (2) Audio?", choices=['1', '2'], default='1')
                    quality = 'best'
                    if download_type == '1':
                        quality = Prompt.ask("Enter preferred resolution (e.g., 720, 1080) or 'best'", default="best")
                    
                    self.batch_download(urls, 'video' if download_type == '1' else 'audio', quality)
                
                elif choice == 4:  # Download Subtitles
                    url = Prompt.ask("Enter YouTube URL")
                    self.download_subtitles(url)
                
                elif choice == 5:  # Set Download Directory
                    self.set_download_directory()
                
                elif choice == 6:  # About
                    self.show_about()
                
                elif choice == 7:  # Exit
                    self.console.print("[bold green]Thank you for using SocialMediaGrabber![/bold green]")
                    sys.exit(0)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Operation cancelled by user.[/yellow]")
                continue
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                continue

    def run(self) -> None:
        """Main entry point for the application"""
        if len(sys.argv) > 1:
            self.handle_cli_args()
        else:
            self.show_menu()
            self.process_menu_choice()

    def handle_cli_args(self) -> None:
        """Handle command line arguments"""
        if '--version' in sys.argv or '-v' in sys.argv:
            self.console.print(f"SocialMediaGrabber v{self.version}")
            sys.exit(0)
        
        if '--about' in sys.argv or '-a' in sys.argv:
            self.show_about()
            sys.exit(0)
        
        # Handle direct URL downloads from CLI
        if len(sys.argv) >= 3 and sys.argv[1] in ['-d', '--download']:
            url = sys.argv[2]
            download_type = 'video'
            quality = 'best'
            
            if len(sys.argv) >= 4 and sys.argv[3] in ['-a', '--audio']:
                download_type = 'audio'
            elif len(sys.argv) >= 4 and sys.argv[3] in ['-q', '--quality']:
                quality = sys.argv[4] if len(sys.argv) >= 5 else 'best'
            
            self.download_media(url, download_type, quality)
            sys.exit(0)
        
        self.console.print("[red]Invalid command line arguments[/red]")
        self.console.print("Usage:")
        self.console.print("  python SocialMediaGrabber.py [options]")
        self.console.print("Options:")
        self.console.print("  -v, --version   Show version information")
        self.console.print("  -a, --about     Show about information")
        self.console.print("  -d URL, --download URL  Download from URL directly")
        self.console.print("  -a              Download as audio (with -d)")
        self.console.print("  -q QUALITY, --quality QUALITY  Set video quality (with -d)")
        sys.exit(1)

if __name__ == "__main__":
    try:
        grabber = SocialMediaGrabber()
        grabber.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)