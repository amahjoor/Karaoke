from faster_whisper import WhisperModel
import asyncio
from typing import List, Dict
import os
from pathlib import Path

class WhisperService:
    def __init__(self):
        # Don't load model immediately - use lazy loading
        self.model = None
        self.model_loaded = False
    
    def _ensure_model_loaded(self):
        """Load Whisper model only when needed (lazy loading)"""
        if self.model_loaded:
            return
        
        # Use faster-whisper with optimized settings
        # Model sizes: tiny, base, small, medium, large-v2, large-v3
        # smaller models = faster but less accurate
        model_name = "base"  # Changed from medium to base for speed
        
        print(f"🔄 Loading faster-whisper '{model_name}' model...")
        
        try:
            # faster-whisper settings:
            # - device: "cpu" or "cuda"
            # - compute_type: "int8" (fastest), "float16" (GPU), "float32" (CPU)
            # - num_workers: parallel processing threads
            self.model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",  # int8 is much faster on CPU
                num_workers=4  # parallel processing
            )
            print(f"✅ faster-whisper '{model_name}' model loaded successfully")
            print(f"   Using: CPU with int8 quantization (optimized for speed)")
        except Exception as e:
            print(f"⚠️  Failed to load {model_name} model, trying tiny: {e}")
            try:
                self.model = WhisperModel("tiny", device="cpu", compute_type="int8", num_workers=4)
                print("✅ faster-whisper 'tiny' model loaded successfully")
            except Exception as e2:
                print(f"❌ Failed to load whisper models: {e2}")
                raise
        
        self.model_loaded = True
    
    async def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """Transcribe audio file and return words with timestamps"""
        
        # Load model only when actually needed
        self._ensure_model_loaded()
        
        def _transcribe():
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            try:
                # faster-whisper API: returns segments and info
                # word_timestamps=True enables word-level timing
                segments, info = self.model.transcribe(
                    audio_path,
                    language="en",
                    word_timestamps=True,
                    vad_filter=True,  # Voice activity detection for better accuracy
                    beam_size=5  # balance between speed and accuracy
                )
                
                # Extract word-level timestamps
                words_with_timestamps = []
                
                for segment in segments:
                    # faster-whisper provides words directly in segment.words
                    if hasattr(segment, 'words') and segment.words:
                        for word in segment.words:
                            words_with_timestamps.append({
                                "text": word.word.strip(),
                                "start": word.start,
                                "end": word.end
                            })
                    else:
                        # Fallback: split segment text into words
                        words = segment.text.strip().split()
                        segment_duration = segment.end - segment.start
                        word_duration = segment_duration / len(words) if words else 0
                        
                        for i, word in enumerate(words):
                            word_start = segment.start + (i * word_duration)
                            word_end = word_start + word_duration
                            
                            words_with_timestamps.append({
                                "text": word,
                                "start": word_start,
                                "end": word_end
                            })
                
                print(f"✅ Transcribed {len(words_with_timestamps)} words from {audio_path}")
                return words_with_timestamps
                
            except Exception as e:
                print(f"❌ Transcription error: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(None, _transcribe)
    
    async def transcribe_segments(self, audio_path: str) -> List[Dict]:
        """Transcribe audio and return sentence-level segments with timestamps"""
        
        # Load model only when actually needed
        self._ensure_model_loaded()
        
        def _transcribe_segments():
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # faster-whisper returns an iterator of segments
            segments_iter, info = self.model.transcribe(
                audio_path,
                language="en",
                beam_size=5
            )
            
            segments = []
            for segment in segments_iter:
                segments.append({
                    "text": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end
                })
            
            return segments
        
        return await asyncio.get_event_loop().run_in_executor(None, _transcribe_segments)
