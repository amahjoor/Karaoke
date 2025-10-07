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
from services.audio_separation_service import AudioSeparationService
from services.lyrics_alignment_service import LyricsAlignmentService

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
audio_separation_service = AudioSeparationService()
lyrics_alignment_service = LyricsAlignmentService(min_confidence=0.75)

# Track processing status for each video_id
# Status can be: "processing", "completed", "failed"
processing_status = {}

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

@app.get("/check/{video_id}")
async def check_video(video_id: str):
    """Pre-check if a video is available for processing"""
    try:
        availability = await youtube_service.check_video_availability(video_id)
        return availability
    except Exception as e:
        return {
            "available": False,
            "issues": ["check_failed"],
            "error": str(e)
        }

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
        
        # Check if already processing to avoid duplicate tasks
        if video_id in processing_status and processing_status[video_id]["status"] == "processing":
            print(f"Already processing video_id: {video_id}, skipping duplicate request")
            return {"status": "processing", "video_id": video_id}
        
        print(f"Starting background processing for video_id: {video_id}")
        
        # Mark as processing
        processing_status[video_id] = {"status": "processing"}
        
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
        # Check if completed (cached)
        cached_data = cache_service.get_cached_song(video_id)
        if cached_data:
            return {"status": "ready"}
        
        # Check if failed or processing
        if video_id in processing_status:
            status_info = processing_status[video_id]
            if status_info["status"] == "failed":
                return {
                    "status": "failed",
                    "error": status_info.get("error", "Unknown error occurred")
                }
            return {"status": "processing"}
        
        return {"status": "not_started"}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _process_song_async(video_id: str):
    """Background task to process a song"""
    try:
        # 1. Download original song from YouTube
        print(f"\n{'='*60}")
        print(f"🎵 [1/5] Downloading song from YouTube...")
        print(f"{'='*60}")
        original_path, metadata = await youtube_service.download_song(video_id)
        print(f"✅ Download complete!")
        
        # 2. Separate audio into vocals and instrumental
        print(f"\n{'='*60}")
        print(f"🎚️  [2/5] Separating vocals and instrumental...")
        print(f"    Using mdx_extra (fast model)")
        print(f"{'='*60}")
        vocals_path, instrumental_path = await audio_separation_service.separate_audio(original_path, video_id)
        print(f"✅ Separation complete!")
        
        # 3. Transcribe original audio with Whisper (faster & more accurate!)
        print(f"\n{'='*60}")
        print(f"🎤 [3/5] Transcribing audio with faster-whisper...")
        print(f"    Using base model with int8 quantization")
        print(f"{'='*60}")
        transcription = await whisper_service.transcribe_with_timestamps(original_path)
        
        # 4. Get lyrics from Genius for alignment
        print(f"\n{'='*60}")
        print(f"🎼 [4/5] Fetching lyrics from Genius...")
        print(f"{'='*60}")
        genius_lyrics = await genius_service.get_lyrics(metadata['title'], metadata['artist'])
        print(f"✅ Lyrics fetched!")
        
        # 5. Align and correct lyrics
        print(f"\n{'='*60}")
        print(f"🎯 [5/5] Aligning and correcting lyrics...")
        print(f"{'='*60}")
        aligned_data = await lyrics_alignment_service.align_and_correct(
            whisper_words=transcription,
            genius_lyrics=genius_lyrics
        )
        print(f"✅ Lyrics aligned!")
        
        print(f"✓ Alignment complete: {aligned_data['alignment_meta']['corrected_count']}/{aligned_data['alignment_meta']['total_words']} words corrected (avg confidence: {aligned_data['alignment_meta']['avg_confidence']:.2f})")
        
        # 6. Cache the results
        karaoke_data = {
            "audio_url": f"/cache/audio/{video_id}_instrumental.mp3",
            "lyrics": aligned_data["lyrics"],
            "lyric_lines": aligned_data["lyric_lines"],
            "alignment_meta": aligned_data["alignment_meta"],
            "title": metadata['title'],
            "artist": metadata['artist'],
            "genius_lyrics": genius_lyrics,
            "whisper_original": transcription  # Keep original for debugging
        }
        
        cache_service.cache_song(video_id, karaoke_data)
        
        # Mark as completed
        processing_status[video_id] = {"status": "completed"}
        
        print(f"\n{'='*60}")
        print(f"🎉 Processing complete for {video_id}!")
        print(f"✅ Song is ready to play!")
        print(f"{'='*60}\n")
        return karaoke_data
        
    except Exception as e:
        error_message = str(e)
        print(f"\n{'='*60}")
        print(f"❌ Error processing song {video_id}")
        print(f"   {error_message}")
        print(f"{'='*60}\n")
        
        # Mark as failed with error message
        processing_status[video_id] = {
            "status": "failed",
            "error": error_message
        }
        
        # Don't re-raise to prevent "Task exception was never retrieved"
        return None

# Serve cached audio files
app.mount("/cache", StaticFiles(directory="../cache"), name="cache")

if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Configure logging to hide repetitive status checks
    class StatusEndpointFilter(logging.Filter):
        def filter(self, record):
            # Hide GET /status/* requests from logs
            return "/status/" not in record.getMessage()
    
    # Apply filter to uvicorn access logs
    logging.getLogger("uvicorn.access").addFilter(StatusEndpointFilter())
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
