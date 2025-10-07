import yt_dlp
import os
import asyncio
from typing import List, Dict, Tuple, Optional
import re

class YouTubeService:
    def __init__(self):
        # Use absolute paths to avoid cwd-related issues
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.cache_dir = os.path.join(project_root, 'cache')
        self.audio_dir = os.path.join(self.cache_dir, 'audio')
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # yt-dlp options for fast downloads
        self.ydl_opts_search = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        # Base download options (we override outtmpl per file to fixed names)
        self.ydl_opts_download = {
            # Explicitly avoid mhtml/dash formats, prefer direct audio streams
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/140/251/250/bestaudio/best',
            'format_sort': ['hasvid:false', 'br', 'res', 'fps'],  # Prefer audio-only
            'restrictfilenames': True,  # safe ascii filenames
            'overwrites': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,  # Show more info for debugging
            'no_warnings': False,
            'ignoreerrors': False,  # Fail fast on errors
            'nocheckcertificate': True,
            'prefer_free_formats': True,
            # Better browser emulation to avoid YouTube bot detection
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
        }

    async def check_video_availability(self, video_id: str) -> Dict:
        """Check if a video is available for download without actually downloading it"""
        def _check():
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                    info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                    
                    # Check for common issues
                    issues = []
                    
                    if info.get('age_limit', 0) > 0:
                        issues.append('age_restricted')
                    
                    if info.get('is_live'):
                        issues.append('live_stream')
                    
                    if not info.get('formats'):
                        issues.append('no_formats_available')
                    
                    availability = info.get('availability', 'unknown')
                    if availability not in ['public', 'unlisted']:
                        issues.append(f'not_available_{availability}')
                    
                    return {
                        'available': len(issues) == 0,
                        'issues': issues,
                        'title': info.get('title', ''),
                        'duration': info.get('duration', 0)
                    }
            except Exception as e:
                return {
                    'available': False,
                    'issues': ['check_failed'],
                    'error': str(e)
                }
        
        return await asyncio.get_event_loop().run_in_executor(None, _check)
    
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

    async def download_song(self, video_id: str) -> Tuple[str, Dict]:
        """Download original song from YouTube"""
        
        def _download():
            import glob
            
            # Fixed output template to avoid unicode/rename issues
            download_opts = self.ydl_opts_download.copy()
            download_opts['outtmpl'] = os.path.join(self.audio_dir, f'{video_id}_original.%(ext)s')

            with yt_dlp.YoutubeDL(download_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                title = info.get('title', '')
                artist, song_title = self._parse_title(title)
                
                # Download original
                try:
                    ydl.download([f"https://youtube.com/watch?v={video_id}"])
                except Exception as e:
                    # Some videos fail with postprocessor, but file might still be downloaded
                    print(f"Download warning: {e}")
                
                # Find downloaded file - check for .mp3 first, then any file with the video_id
                target_mp3 = os.path.join(self.audio_dir, f'{video_id}_original.mp3')
                if os.path.exists(target_mp3) and os.path.getsize(target_mp3) > 0:
                    return target_mp3, {
                        'title': song_title,
                        'artist': artist,
                        'full_title': title,
                        'video_id': video_id
                    }
                
                # Check for other extensions (webm, m4a, etc.) but REJECT mhtml
                pattern = os.path.join(self.audio_dir, f'{video_id}_original.*')
                matching_files = glob.glob(pattern)
                
                if matching_files:
                    downloaded_file = matching_files[0]
                    print(f"Found downloaded file: {downloaded_file}")
                    
                    # Reject .mhtml files entirely - they're corrupted
                    if downloaded_file.endswith('.mhtml'):
                        os.remove(downloaded_file)
                        raise Exception(
                            "Video is restricted or unavailable for download. "
                            "This video may be region-locked, age-restricted, or have DRM protection. "
                            "Please try a different song."
                        )
                    
                    # If not mp3, convert it manually with ffmpeg
                    if not downloaded_file.endswith('.mp3'):
                        import subprocess
                        output_mp3 = os.path.join(self.audio_dir, f'{video_id}_original.mp3')
                        try:
                            subprocess.run([
                                'ffmpeg', '-i', downloaded_file,
                                '-vn',  # No video
                                '-ar', '44100',  # Audio sample rate
                                '-ac', '2',  # Stereo
                                '-b:a', '192k',  # Bitrate
                                output_mp3
                            ], check=True, capture_output=True)
                            
                            # Remove original non-mp3 file
                            os.remove(downloaded_file)
                            print(f"Converted to MP3: {output_mp3}")
                            
                            return output_mp3, {
                                'title': song_title,
                                'artist': artist,
                                'full_title': title,
                                'video_id': video_id
                            }
                        except Exception as conv_error:
                            print(f"Conversion error: {conv_error}")
                            # Clean up failed file
                            if os.path.exists(downloaded_file):
                                os.remove(downloaded_file)
                            raise Exception(f"Failed to convert audio format. This video may be incompatible.")
                    
                    return downloaded_file, {
                        'title': song_title,
                        'artist': artist,
                        'full_title': title,
                        'video_id': video_id
                    }
                
                raise Exception(f"Download failed - no valid audio file was created for this video")
        
        return await asyncio.get_event_loop().run_in_executor(None, _download)

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
