import yt_dlp
import os
import asyncio
from typing import List, Dict, Tuple, Optional
import re

class YouTubeService:
    def __init__(self):
        self.cache_dir = "../cache"
        self.audio_dir = os.path.join(self.cache_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # yt-dlp options for fast downloads
        self.ydl_opts_search = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        self.ydl_opts_download = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.audio_dir, '%(id)s_%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }

    async def search_songs(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for songs on YouTube"""
        def _search():
            with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch{max_results}:{query}",
                    download=False
                )
                
                results = []
                for entry in search_results.get('entries', []):
                    # Parse title to extract artist and song
                    title = entry.get('title', '')
                    artist, song_title = self._parse_title(title)
                    
                    try:
                        duration = self._format_duration(entry.get('duration'))
                    except Exception:
                        duration = "Unknown"
                    
                    results.append({
                        'id': entry.get('id'),
                        'title': song_title,
                        'artist': artist,
                        'duration': duration,
                        'thumbnail': entry.get('thumbnail', ''),
                        'full_title': title
                    })
                
                return results
        
        return await asyncio.get_event_loop().run_in_executor(None, _search)

    async def download_song_and_instrumental(self, video_id: str) -> Tuple[str, str, Dict]:
        """Download original song and find/download instrumental version"""
        
        def _download_original():
            with yt_dlp.YoutubeDL(self.ydl_opts_download) as ydl:
                # Get video info first
                info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                title = info.get('title', '')
                artist, song_title = self._parse_title(title)
                
                # Download original
                ydl.download([f"https://youtube.com/watch?v={video_id}"])
                
                # Find downloaded file
                original_path = None
                for file in os.listdir(self.audio_dir):
                    if file.startswith(video_id) and file.endswith('.mp3'):
                        original_path = os.path.join(self.audio_dir, file)
                        break
                
                return original_path, {
                    'title': song_title,
                    'artist': artist,
                    'full_title': title,
                    'video_id': video_id
                }
        
        def _find_and_download_instrumental():
            # Search for instrumental version
            instrumental_query = f"{metadata['artist']} {metadata['title']} instrumental"
            
            with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch5:{instrumental_query}",
                    download=False
                )
                
                # Find best instrumental match
                for entry in search_results.get('entries', []):
                    entry_title = entry.get('title', '').lower()
                    if 'instrumental' in entry_title or 'karaoke' in entry_title:
                        # Download this instrumental
                        instrumental_id = entry.get('id')
                        
                        download_opts = self.ydl_opts_download.copy()
                        download_opts['outtmpl'] = os.path.join(
                            self.audio_dir, 
                            f'{video_id}_instrumental.%(ext)s'
                        )
                        
                        with yt_dlp.YoutubeDL(download_opts) as ydl_download:
                            ydl_download.download([f"https://youtube.com/watch?v={instrumental_id}"])
                        
                        instrumental_path = os.path.join(self.audio_dir, f'{video_id}_instrumental.mp3')
                        return instrumental_path
                
                raise Exception("No instrumental version found")
        
        # Download original first
        original_path, metadata = await asyncio.get_event_loop().run_in_executor(None, _download_original)
        
        if not original_path:
            raise Exception("Failed to download original song")
        
        # Then find and download instrumental
        try:
            instrumental_path = await asyncio.get_event_loop().run_in_executor(None, _find_and_download_instrumental)
        except Exception as e:
            raise Exception(f"Failed to find instrumental version: {str(e)}")
        
        return original_path, instrumental_path, metadata

    def _parse_title(self, title: str) -> Tuple[str, str]:
        """Parse YouTube title to extract artist and song name"""
        # Common patterns: "Artist - Song", "Artist: Song", "Song by Artist"
        patterns = [
            r'^(.+?)\s*-\s*(.+)$',  # Artist - Song
            r'^(.+?)\s*:\s*(.+)$',  # Artist: Song
            r'^(.+?)\s+by\s+(.+)$', # Song by Artist (reversed)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, title, re.IGNORECASE)
            if match:
                if 'by' in pattern:
                    return match.group(2).strip(), match.group(1).strip()  # Artist, Song
                else:
                    return match.group(1).strip(), match.group(2).strip()  # Artist, Song
        
        # If no pattern matches, return title as song with unknown artist
        return "Unknown Artist", title

    def _format_duration(self, duration: Optional[float]) -> str:
        """Format duration in seconds to MM:SS"""
        if not duration:
            return "Unknown"
        
        # Convert to int to handle float durations
        duration = int(duration)
        minutes = duration // 60
        seconds = duration % 60
        return f"{minutes}:{seconds:02d}"
