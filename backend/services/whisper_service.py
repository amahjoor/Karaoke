import whisper
import asyncio
from typing import List, Dict
import os

class WhisperService:
    def __init__(self):
        # Load Whisper medium model for better accuracy
        # Note: First run will download ~1.5GB model
        try:
            print("Loading Whisper 'medium' model (this may take a moment on first run)...")
            self.model = whisper.load_model("medium")
            print("✓ Whisper 'medium' model loaded successfully")
        except Exception as e:
            print(f"Failed to load medium model, trying small: {e}")
            try:
                self.model = whisper.load_model("small")
            except Exception as e2:
                print(f"Failed to load small model, using base: {e2}")
                self.model = whisper.load_model("base")
    
    async def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """Transcribe audio file and return words with timestamps"""
        
        def _transcribe():
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            try:
                # Try with word-level timestamps first
                result = self.model.transcribe(
                    audio_path,
                    word_timestamps=True,
                    language="en"
                )
            except Exception as e:
                print(f"Word-level transcription failed: {e}")
                # Fallback to segment-level transcription
                result = self.model.transcribe(
                    audio_path,
                    language="en"
                )
            
            # Extract word-level timestamps
            words_with_timestamps = []
            
            for segment in result["segments"]:
                if "words" in segment:
                    for word_info in segment["words"]:
                        words_with_timestamps.append({
                            "text": word_info["word"].strip(),
                            "start": word_info["start"],
                            "end": word_info["end"]
                        })
                else:
                    # Fallback: if no word-level timestamps, use segment timestamps
                    # Split segment text into words and estimate timestamps
                    words = segment["text"].strip().split()
                    segment_duration = segment["end"] - segment["start"]
                    word_duration = segment_duration / len(words) if words else 0
                    
                    for i, word in enumerate(words):
                        word_start = segment["start"] + (i * word_duration)
                        word_end = word_start + word_duration
                        
                        words_with_timestamps.append({
                            "text": word,
                            "start": word_start,
                            "end": word_end
                        })
            
            return words_with_timestamps
        
        return await asyncio.get_event_loop().run_in_executor(None, _transcribe)
    
    async def transcribe_segments(self, audio_path: str) -> List[Dict]:
        """Transcribe audio and return sentence-level segments with timestamps"""
        
        def _transcribe_segments():
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            result = self.model.transcribe(audio_path, language="en")
            
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "text": segment["text"].strip(),
                    "start": segment["start"],
                    "end": segment["end"]
                })
            
            return segments
        
        return await asyncio.get_event_loop().run_in_executor(None, _transcribe_segments)
