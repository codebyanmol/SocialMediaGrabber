#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import random
import time
from pathlib import Path
from urllib.parse import urlparse
from yt_dlp import YoutubeDL
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint
from rich.text import Text
from rich.box import ROUNDED

# Initialize rich console
console = Console()

# Constants
TOOL_NAME = "Anmol Khadka's SocialMediaGrabber"
VERSION = "2.0"
CREATOR = "Anmol Khadka"
GITHUB_URL = "https://github.com/codebyanmol"
EMAIL = "codebyanmol@gmail.com"
SUPPORTED_SITES = [
    "YouTube", "TikTok", "Facebook", "Instagram (reels/posts)", 
    "Twitter/X", "Reddit", "Vimeo", "Dailymotion", "SoundCloud"
]

class SocialMediaGrabber:
    def __init__(self):
        self.os_name = self.detect_os()
        self.download_dir = self.get_default_download_dir()
        self.ffmpeg_installed = False
        self.check_dependencies()
        
    def detect_os(self):
        """Detect the operating system and environment."""
        system = platform.system().lower()
        if 'termux' in os.environ.get('PREFIX', '').lower():
            return "Android (Termux)"
        elif system == 'linux':
            return "Linux"
        elif system == 'windows':
            return "Windows"
        elif system == 'darwin':
            return "macOS"
        else:
            return "Unknown OS"
    
    def get_default_download_dir(self):
        """Get the default download directory based on OS."""
        home = str(Path.home())
        
        if "Android" in self.os_name:
            return Path("/storage/emulated/0/Download")
        elif self.os_name == "Windows":
            return Path(home) / "Downloads"
        else:  # Linux, macOS
            return Path(home) / "Downloads"
    
    def check_dependencies(self):
        """Check and install required dependencies."""
        try:
            # Check if yt-dlp is available
            import yt_dlp
            
            # Check if ffmpeg is available
            try:
                subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                self.ffmpeg_installed = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                if "Android" in self.os_name:
                    self.install_android_dependencies()
                else:
                    console.print("[red]Warning: ffmpeg is not installed. Audio conversion may not work.[/red]")
        except ImportError:
            if "Android" in self.os_name:
                self.install_android_dependencies()
            else:
                console.print("[red]Error: Required packages not installed. Please install yt-dlp, ffmpeg, tqdm, and rich.[/red]")
                sys.exit(1)
    
    def install_android_dependencies(self):
        """Install dependencies for Termux."""
        console.print("[yellow]Installing required packages for Termux...[/yellow]")
        try:
            subprocess.run(["pkg", "install", "ffmpeg", "-y"], check=True)
            subprocess.run(["pip", "install", "yt-dlp", "tqdm", "rich", "ffmpeg-python"], check=True)
            self.ffmpeg_installed = True
            console.print("[green]Dependencies installed successfully![/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install dependencies: {e}[/red]")
            sys.exit(1)
    
    def generate_filename(self, url, ext="mp4"):
        """Generate a unique filename with prefix."""
        random_num = random.randint(100000, 999999)
        return f"AnmolKhadkaSocialMediaGrabber_{random_num}.{ext}"
    
    def get_video_info(self, url):
        """Fetch video metadata using yt-dlp."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Format the information for display
                title = info.get('title', 'N/A')
                uploader = info.get('uploader', 'N/A')
                upload_date = info.get('upload_date', 'N/A')
                if upload_date != 'N/A':
                    upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                likes = info.get('like_count', 'N/A')
                if likes != 'N/A':
                    likes = f"{int(likes):,}"
                duration = info.get('duration', 'N/A')
                if duration != 'N/A':
                    minutes, seconds = divmod(duration, 60)
                    duration = f"{minutes} minutes, {seconds} seconds"
                
                # Estimate size (approximate)
                formats = info.get('formats', [])
                if formats:
                    best_format = max(formats, key=lambda x: x.get('filesize', 0) if x.get('filesize') else 0)
                    size = best_format.get('filesize', 'N/A')
                    if size != 'N/A':
                        size_mb = size / (1024 * 1024)
                        size = f"~{size_mb:.1f} MB"
                else:
                    size = 'N/A'
                
                description = info.get('description', 'N/A')
                if description != 'N/A' and len(description) > 100:
                    description = description[:100] + "..."
                
                # Create info panel
                info_text = Text()
                info_text.append(f"✔️ Video found successfully!\n", style="bold green")
                info_text.append(f"📺 Title : {title}\n")
                info_text.append(f"🎬 Uploader : {uploader}\n")
                info_text.append(f"📅 Upload Date : {upload_date}\n")
                info_text.append(f"👍 Likes : {likes}\n")
                info_text.append(f"⏱ Duration : {duration}\n")
                info_text.append(f"🗂 Size : {size}\n")
                info_text.append(f"📝 Description : {description}")
                
                console.print(Panel(info_text, title="Video Information", border_style="blue", box=ROUNDED))
                return info
                
        except Exception as e:
            console.print(f"[red]Error fetching video info: {e}[/red]")
            return None
    
    def download_video(self, url, quality='best'):
        """Download video in specified quality."""
        filename = self.generate_filename(url)
        output_path = str(self.download_dir / filename)
        
        ydl_opts = {
            'format': quality,
            'outtmpl': output_path,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                console.print(f"[yellow]Downloading video...[/yellow]")
                ydl.download([url])
                console.print(f"[green]Video downloaded successfully to:[/green] {output_path}")
        except Exception as e:
            console.print(f"[red]Error downloading video: {e}[/red]")
    
    def download_audio(self, url):
        """Download audio as MP3."""
        filename = self.generate_filename(url, ext="mp3")
        output_path = str(self.download_dir / filename)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                console.print(f"[yellow]Downloading audio...[/yellow]")
                ydl.download([url])
                console.print(f"[green]Audio downloaded successfully to:[/green] {output_path}")
        except Exception as e:
            console.print(f"[red]Error downloading audio: {e}[/red]")
    
    def download_subtitles(self, url):
        """Download subtitles for YouTube videos."""
        filename = self.generate_filename(url, ext="vtt")
        output_path = str(self.download_dir / filename)
        
        ydl_opts = {
            'writesubtitles': True,
            'subtitlesformat': 'vtt',
            'subtitleslangs': ['en'],
            'outtmpl': output_path.replace('.vtt', ''),
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                console.print(f"[yellow]Downloading subtitles...[/yellow]")
                ydl.download([url])
                console.print(f"[green]Subtitles downloaded successfully to:[/green] {output_path}")
        except Exception as e:
            console.print(f"[red]Error downloading subtitles: {e}[/red]")
    
    def batch_download(self, urls, download_type='video'):
        """Download multiple URLs in batch."""
        for i, url in enumerate(urls, 1):
            console.print(f"\n[yellow]Processing URL {i} of {len(urls)}[/yellow]")
            if download_type == 'video':
                self.download_video(url)
            elif download_type == 'audio':
                self.download_audio(url)
            elif download_type == 'subtitles':
                self.download_subtitles(url)
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp to show download progress."""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes')
            speed = d.get('speed')
            eta = d.get('eta')
            
            if total_bytes and downloaded_bytes and speed and eta:
                progress = downloaded_bytes / total_bytes
                speed_mb = speed / (1024 * 1024)
                console.print(f"[cyan]Progress: {progress:.1%} | Speed: {speed_mb:.1f} MB/s | ETA: {eta}s[/cyan]", end="\r")
    
    def set_custom_download_dir(self):
        """Set a custom download directory."""
        console.print(f"\nCurrent download directory: [green]{self.download_dir}[/green]")
        new_dir = console.input("Enter new download directory path (or press Enter to keep current): ").strip()
        
        if new_dir:
            new_path = Path(new_dir)
            if new_path.is_dir():
                self.download_dir = new_path
                console.print(f"[green]Download directory changed to: {self.download_dir}[/green]")
            else:
                console.print("[red]Error: The specified directory does not exist.[/red]")
    
    def show_about(self):
        """Display information about the tool and creator."""
        about_text = Text()
        about_text.append(f"{TOOL_NAME} v{VERSION}\n", style="bold blue")
        about_text.append(f"Created by: {CREATOR}\n")
        about_text.append(f"GitHub: {GITHUB_URL}\n")
        about_text.append(f"Email: {EMAIL}\n\n")
        about_text.append("Features:\n", style="bold")
        about_text.append("- HD video and high-quality audio download\n")
        about_text.append("- Metadata preview for supported sites\n")
        about_text.append("- Batch download mode\n")
        about_text.append("- Subtitles download (YouTube)\n")
        about_text.append("- Works fully offline after installing requirements\n")
        about_text.append("- Auto install dependencies on Android/Termux\n\n")
        about_text.append("Supported Sites:\n", style="bold")
        about_text.append(", ".join(SUPPORTED_SITES))
        
        console.print(Panel(about_text, title="About", border_style="green", box=ROUNDED))
    
    def main_menu(self):
        """Display the main menu and handle user input."""
        while True:
            console.clear()
            
            # Create title panel
            title_text = Text()
            title_text.append(f"Welcome to {TOOL_NAME} v{VERSION}\n", style="bold blue")
            title_text.append(f"OS Detected: {self.os_name}")
            
            console.print(Panel(title_text, border_style="blue", box=ROUNDED))
            
            # Create menu table
            menu_table = Table(show_header=False, box=ROUNDED)
            menu_table.add_column("Option", style="cyan")
            menu_table.add_column("Description", style="white")
            
            menu_table.add_row("1️⃣", "Download Video (HD/full quality)")
            menu_table.add_row("2️⃣", "Download Audio (MP3)")
            menu_table.add_row("3️⃣", "Batch Download (Multiple URLs)")
            menu_table.add_row("4️⃣", "Download Subtitles (YouTube only)")
            menu_table.add_row("5️⃣", "Set Custom Download Directory")
            menu_table.add_row("6️⃣", "About This Tool")
            menu_table.add_row("7️⃣", "Exit")
            
            console.print(menu_table)
            
            choice = console.input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                self.handle_single_download('video')
            elif choice == '2':
                self.handle_single_download('audio')
            elif choice == '3':
                self.handle_batch_download()
            elif choice == '4':
                self.handle_subtitles_download()
            elif choice == '5':
                self.set_custom_download_dir()
            elif choice == '6':
                self.show_about()
                console.input("\nPress Enter to return to menu...")
            elif choice == '7':
                console.print("[yellow]Exiting... Thank you for using SocialMediaGrabber![/yellow]")
                sys.exit(0)
            else:
                console.print("[red]Invalid choice. Please enter a number between 1-7.[/red]")
                time.sleep(1)
    
    def handle_single_download(self, download_type):
        """Handle single video/audio download."""
        console.print(f"\nSupported sites: {', '.join(SUPPORTED_SITES)}")
        url = console.input("Enter video URL: ").strip()
        
        if not url:
            console.print("[red]Error: URL cannot be empty.[/red]")
            return
        
        # Show video info first
        self.get_video_info(url)
        
        if download_type == 'video':
            self.download_video(url)
        elif download_type == 'audio':
            self.download_audio(url)
        
        console.input("\nPress Enter to return to menu...")
    
    def handle_batch_download(self):
        """Handle batch download of multiple URLs."""
        console.print("\nEnter multiple URLs (one per line). Press Enter twice when done:")
        urls = []
        while True:
            url = console.input().strip()
            if not url and urls:  # Empty line after entering at least one URL
                break
            if url:
                urls.append(url)
        
        if not urls:
            console.print("[red]Error: No URLs provided.[/red]")
            return
        
        console.print("\nDownload as:")
        console.print("1. Videos")
        console.print("2. Audio (MP3)")
        choice = console.input("Enter your choice (1-2): ").strip()
        
        if choice == '1':
            self.batch_download(urls, 'video')
        elif choice == '2':
            self.batch_download(urls, 'audio')
        else:
            console.print("[red]Invalid choice.[/red]")
        
        console.input("\nPress Enter to return to menu...")
    
    def handle_subtitles_download(self):
        """Handle subtitles download."""
        console.print("\nNote: Subtitles download currently only works with YouTube videos.")
        url = console.input("Enter YouTube video URL: ").strip()
        
        if not url:
            console.print("[red]Error: URL cannot be empty.[/red]")
            return
        
        # Show video info first
        self.get_video_info(url)
        self.download_subtitles(url)
        
        console.input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    try:
        grabber = SocialMediaGrabber()
        grabber.main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting... Thank you for using SocialMediaGrabber![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        sys.exit(1)
