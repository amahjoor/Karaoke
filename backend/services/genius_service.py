import lyricsgenius
import asyncio
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class GeniusService:
    def __init__(self):
        # Initialize Genius API (optional - will work without token but with rate limits)
        token = os.getenv("GENIUS_ACCESS_TOKEN")
        if token:
            self.genius = lyricsgenius.Genius(token)
            self.genius.verbose = False  # Turn off status messages
            self.genius.remove_section_headers = True  # Clean up lyrics
        else:
            self.genius = None
            print("Warning: No Genius API token found. Lyrics backup will be limited.")
    
    async def get_lyrics(self, title: str, artist: str) -> Optional[str]:
        """Get lyrics from Genius API as backup/verification"""
        
        if not self.genius:
            return None
        
        def _search_lyrics():
            try:
                # Search for the song
                song = self.genius.search_song(title, artist)
                
                if song:
                    return song.lyrics
                else:
                    # Try with just the title if artist search fails
                    song = self.genius.search_song(title)
                    return song.lyrics if song else None
                    
            except Exception as e:
                print(f"Genius API error: {str(e)}")
                return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _search_lyrics)
    
    def clean_lyrics(self, lyrics: str) -> str:
        """Clean up lyrics text"""
        if not lyrics:
            return ""
        
        # Remove common artifacts
        lines = lyrics.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and common artifacts
            if line and not line.startswith('[') and not line.endswith('Lyrics'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
