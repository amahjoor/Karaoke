import json
import os
from typing import Optional, Dict
import hashlib

class CacheService:
    def __init__(self):
        self.cache_dir = "../cache"
        self.metadata_dir = os.path.join(self.cache_dir, "metadata")
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def get_cached_song(self, video_id: str) -> Optional[Dict]:
        """Get cached karaoke data for a song"""
        cache_file = os.path.join(self.metadata_dir, f"{video_id}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache file {cache_file}: {str(e)}")
                return None
        
        return None
    
    def cache_song(self, video_id: str, karaoke_data: Dict) -> bool:
        """Cache karaoke data for a song"""
        cache_file = os.path.join(self.metadata_dir, f"{video_id}.json")
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(karaoke_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error caching song data: {str(e)}")
            return False
    
    def is_song_cached(self, video_id: str) -> bool:
        """Check if a song is already cached"""
        cache_file = os.path.join(self.metadata_dir, f"{video_id}.json")
        return os.path.exists(cache_file)
    
    def clear_cache(self) -> bool:
        """Clear all cached data"""
        try:
            # Clear metadata files
            for file in os.listdir(self.metadata_dir):
                if file.endswith('.json'):
                    os.remove(os.path.join(self.metadata_dir, file))
            
            # Clear audio files
            audio_dir = os.path.join(self.cache_dir, "audio")
            if os.path.exists(audio_dir):
                for file in os.listdir(audio_dir):
                    if file.endswith('.mp3'):
                        os.remove(os.path.join(audio_dir, file))
            
            return True
        except Exception as e:
            print(f"Error clearing cache: {str(e)}")
            return False
    
    def get_cache_size(self) -> Dict[str, int]:
        """Get cache statistics"""
        metadata_count = 0
        audio_count = 0
        
        # Count metadata files
        if os.path.exists(self.metadata_dir):
            metadata_count = len([f for f in os.listdir(self.metadata_dir) if f.endswith('.json')])
        
        # Count audio files
        audio_dir = os.path.join(self.cache_dir, "audio")
        if os.path.exists(audio_dir):
            audio_count = len([f for f in os.listdir(audio_dir) if f.endswith('.mp3')])
        
        return {
            "cached_songs": metadata_count,
            "audio_files": audio_count
        }
