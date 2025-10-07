import os
import asyncio
from typing import Tuple
import subprocess
import shutil

class AudioSeparationService:
    """
    Service for separating audio into vocals and instrumental using Demucs.
    Demucs is a state-of-the-art audio source separation library from Meta/Facebook Research.
    """
    
    def __init__(self):
        # Use absolute paths
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.cache_dir = os.path.join(project_root, 'cache')
        self.audio_dir = os.path.join(self.cache_dir, 'audio')
        self.temp_dir = os.path.join(self.cache_dir, 'temp_separation')
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def separate_audio(self, audio_path: str, video_id: str) -> Tuple[str, str]:
        """
        Separate audio into vocals and instrumental tracks.
        
        Args:
            audio_path: Path to the original audio file
            video_id: Video ID for naming output files
            
        Returns:
            Tuple of (vocals_path, instrumental_path)
        """
        
        def _separate():
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            try:
                # Run demucs separation
                # Using mdx_extra model (OPTIMIZED FOR SPEED)
                # Model comparison:
                # - htdemucs: High-quality but VERY SLOW (transformer-based)
                # - htdemucs_ft: Slightly faster, but still slow
                # - mdx_extra: 3-4x FASTER, good quality (recommended for speed)
                # - mdx_extra_q: Even faster with quantization
                
                print(f"Starting audio separation for {video_id} (using fast mdx_extra model)...")
                
                # Demucs command optimized for speed
                # -n: model name (mdx_extra for speed)
                # -o: output directory
                # --two-stems: only separate into vocals and accompaniment (faster)
                # --mp3: output format
                # --mp3-bitrate: bitrate for mp3
                # --int24: use int24 instead of float32 (faster processing)
                cmd = [
                    'python', '-m', 'demucs',
                    '--two-stems', 'vocals',  # Only separate vocals from the rest
                    '-o', self.temp_dir,
                    '--mp3',
                    '--mp3-bitrate', '192',
                    '-n', 'mdx_extra',  # FAST model (3-4x faster than htdemucs)
                    '--int24',  # Use int24 for faster processing
                    audio_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                print(f"Demucs output: {result.stdout}")
                
                # Demucs creates: temp_separation/mdx_extra/<filename>/vocals.mp3 and no_vocals.mp3
                audio_filename = os.path.splitext(os.path.basename(audio_path))[0]
                separation_dir = os.path.join(self.temp_dir, 'mdx_extra', audio_filename)
                
                vocals_src = os.path.join(separation_dir, 'vocals.mp3')
                instrumental_src = os.path.join(separation_dir, 'no_vocals.mp3')
                
                # Check if files were created
                if not os.path.exists(vocals_src):
                    raise FileNotFoundError(f"Vocals file not created: {vocals_src}")
                if not os.path.exists(instrumental_src):
                    raise FileNotFoundError(f"Instrumental file not created: {instrumental_src}")
                
                # Move to final locations with proper naming
                vocals_dest = os.path.join(self.audio_dir, f'{video_id}_vocals.mp3')
                instrumental_dest = os.path.join(self.audio_dir, f'{video_id}_instrumental.mp3')
                
                shutil.move(vocals_src, vocals_dest)
                shutil.move(instrumental_src, instrumental_dest)
                
                # Clean up temporary separation directory
                try:
                    shutil.rmtree(os.path.join(self.temp_dir, 'mdx_extra'))
                except Exception as e:
                    print(f"Warning: Failed to clean up temp directory: {e}")
                
                print(f"Separation complete for {video_id}")
                print(f"Vocals: {vocals_dest}")
                print(f"Instrumental: {instrumental_dest}")
                
                return vocals_dest, instrumental_dest
                
            except subprocess.CalledProcessError as e:
                error_msg = f"Demucs separation failed: {e.stderr}"
                print(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Audio separation error: {str(e)}"
                print(error_msg)
                raise Exception(error_msg)
        
        return await asyncio.get_event_loop().run_in_executor(None, _separate)
    
    def cleanup_temp_files(self):
        """Clean up temporary separation files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to clean up temp files: {e}")

