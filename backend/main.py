from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio
from typing import List, Optional
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.youtube_service import YouTubeService
from services.whisper_service import WhisperService
from services.genius_service import GeniusService
from services.cache_service import CacheService

app = FastAPI(title="Karaoke Platform API")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
youtube_service = YouTubeService()
whisper_service = WhisperService()
genius_service = GeniusService()
cache_service = CacheService()

class SearchRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    id: str
    title: str
    artist: str
    duration: str
    thumbnail: str

class KaraokeData(BaseModel):
    audio_url: str
    lyrics: List[dict]  # [{text: str, start: float, end: float}]
    title: str
    artist: str

@app.get("/")
async def root():
    return {"message": "Karaoke Platform API"}

@app.post("/search", response_model=List[SearchResult])
async def search_songs(request: SearchRequest):
    """Search for songs on YouTube"""
    try:
        results = await youtube_service.search_songs(request.query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/process/{video_id}")
async def process_song(video_id: str):
    """Process a song for karaoke (download, transcribe, cache)"""
    try:
        print(f"Processing request for video_id: {video_id}")
        
        # Check cache first
        cached_data = cache_service.get_cached_song(video_id)
        if cached_data:
            print(f"Found cached data for video_id: {video_id}")
            return {"status": "ready", "data": cached_data}
        
        print(f"Starting background processing for video_id: {video_id}")
        
        # Start processing
        processing_task = asyncio.create_task(
            _process_song_async(video_id)
        )
        
        return {"status": "processing", "video_id": video_id}
    
    except Exception as e:
        print(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/karaoke/{video_id}")
async def get_karaoke_data(video_id: str):
    """Get karaoke data for a processed song"""
    try:
        print(f"Getting karaoke data for video_id: {video_id}")
        cached_data = cache_service.get_cached_song(video_id)
        if not cached_data:
            print(f"No cached data found for video_id: {video_id}")
            raise HTTPException(status_code=404, detail="Song not processed yet")
        
        print(f"Found cached data for video_id: {video_id}")
        return cached_data
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting karaoke data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get karaoke data: {str(e)}")

@app.get("/status/{video_id}")
async def get_processing_status(video_id: str):
    """Check processing status of a song"""
    try:
        cached_data = cache_service.get_cached_song(video_id)
        if cached_data:
            return {"status": "ready"}
        
        # Check if currently processing (you'd implement this tracking)
        return {"status": "processing"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def _process_song_async(video_id: str):
    """Background task to process a song"""
    try:
        # 1. Download original and instrumental
        original_path, instrumental_path, metadata = await youtube_service.download_song_and_instrumental(video_id)
        
        # 2. Transcribe original with Whisper
        transcription = await whisper_service.transcribe_with_timestamps(original_path)
        
        # 3. Get lyrics from Genius as backup
        genius_lyrics = await genius_service.get_lyrics(metadata['title'], metadata['artist'])
        
        # 4. Cache the results
        karaoke_data = {
            "audio_url": f"/cache/audio/{video_id}_instrumental.mp3",
            "lyrics": transcription,
            "title": metadata['title'],
            "artist": metadata['artist'],
            "genius_lyrics": genius_lyrics
        }
        
        cache_service.cache_song(video_id, karaoke_data)
        
        return karaoke_data
        
    except Exception as e:
        print(f"Error processing song {video_id}: {str(e)}")
        raise

# Serve cached audio files
app.mount("/cache", StaticFiles(directory="../cache"), name="cache")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
