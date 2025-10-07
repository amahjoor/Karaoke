import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const KaraokePlayer = ({ song, onBack, isProcessing, setIsProcessing }) => {
  const [karaokeData, setKaraokeData] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const [syncOffset, setSyncOffset] = useState(0.2  ); // Offset for perfect sync timing
  
  const audioRef = useRef(null);
  const intervalRef = useRef(null);
  const currentWordRef = useRef(null);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);

  useEffect(() => {
    processSong();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [song.id]);

  // Detect user scrolling - disable auto-scroll when user manually scrolls
  useEffect(() => {
    const handleScroll = () => {
      // User is manually scrolling, disable auto-scroll
      if (autoScrollEnabled) {
        console.log('Auto-scroll disabled - user is scrolling');
        setAutoScrollEnabled(false);
      }
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [autoScrollEnabled]);

  // Smart auto-scroll: only scroll if active lyric is in viewport
  useEffect(() => {
    if (!currentWordRef.current) return;
    
    // Check if current lyric is in viewport
    const rect = currentWordRef.current.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    const isInViewport = rect.top >= 0 && rect.bottom <= windowHeight;
    
    if (isInViewport) {
      // Active lyric is visible - re-enable auto-scroll and center it
      if (!autoScrollEnabled) {
        console.log('Auto-scroll re-enabled - active lyric in view');
      }
      setAutoScrollEnabled(true);
      currentWordRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest'
      });
    } else {
      // Active lyric not in viewport - keep auto-scroll disabled
      if (autoScrollEnabled) {
        console.log('Auto-scroll disabled - active lyric out of view');
        setAutoScrollEnabled(false);
      }
    }
    
  }, [currentWordIndex]);

  // Spacebar to play/pause
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.code === 'Space' && karaokeData && !isProcessing) {
        e.preventDefault();
        handlePlayPause();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [karaokeData, isProcessing, isPlaying]);

  const processSong = async () => {
    try {
      setError(null);
      
      // First, try to get cached data
      const cachedResponse = await axios.get(`${API_BASE_URL}/karaoke/${song.id}`);
      setKaraokeData(cachedResponse.data);
      setIsProcessing(false);
      return;
    } catch (err) {
      // If not cached, start processing
      if (err.response?.status === 404) {
        try {
          await axios.post(`${API_BASE_URL}/process/${song.id}`);
          
          // Poll for completion
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await axios.get(`${API_BASE_URL}/status/${song.id}`);
              
              if (statusResponse.data.status === 'ready') {
                clearInterval(pollInterval);
                const karaokeResponse = await axios.get(`${API_BASE_URL}/karaoke/${song.id}`);
                setKaraokeData(karaokeResponse.data);
                setIsProcessing(false);
              } else if (statusResponse.data.status === 'failed' || statusResponse.data.status === 'error') {
                clearInterval(pollInterval);
                const errorMsg = statusResponse.data.error || statusResponse.data.message || 'Processing failed';
                // Make error messages more user-friendly
                let userFriendlyError = errorMsg;
                if (errorMsg.includes('Downloaded file not found') || errorMsg.includes('downloaded file is empty')) {
                  userFriendlyError = '❌ This video cannot be downloaded. It may be restricted, age-gated, or unavailable in your region. Please try a different song.';
                } else if (errorMsg.includes('Failed to convert')) {
                  userFriendlyError = '❌ Failed to convert audio format. This video may be incompatible. Please try a different song.';
                } else if (errorMsg.includes('Separation') || errorMsg.includes('Demucs')) {
                  userFriendlyError = '❌ Failed to separate vocals and instrumental. Please try a different song.';
                }
                setError(userFriendlyError);
                setIsProcessing(false);
              }
            } catch (pollErr) {
              console.error('Polling error:', pollErr);
            }
          }, 2000);
          
          // Cleanup polling after 5 minutes
          setTimeout(() => {
            clearInterval(pollInterval);
            if (isProcessing) {
              setError('Processing timeout. Please try again.');
              setIsProcessing(false);
            }
          }, 300000);
          
        } catch (processErr) {
          setError(processErr.response?.data?.detail || 'Failed to start processing');
          setIsProcessing(false);
        }
      } else {
        setError(err.response?.data?.detail || 'Failed to load karaoke data');
        setIsProcessing(false);
      }
    }
  };

  const handlePlayPause = () => {
    if (!audioRef.current || !karaokeData) return;

    if (isPlaying) {
      audioRef.current.pause();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    } else {
      audioRef.current.play();
      intervalRef.current = setInterval(updateProgress, 100);
    }
    setIsPlaying(!isPlaying);
  };

  const updateProgress = () => {
    if (audioRef.current && karaokeData?.lyrics) {
      const actualTime = audioRef.current.currentTime;
      setCurrentTime(actualTime);
      
      // Apply sync offset to find current word
      const syncedTime = actualTime + syncOffset;
      
      // Find current word: highlight from word.start until next word.start
      let foundIndex = -1;
      
      for (let i = 0; i < karaokeData.lyrics.length; i++) {
        const currentWord = karaokeData.lyrics[i];
        const nextWord = karaokeData.lyrics[i + 1];
        
        // Highlight word from its start until next word starts
        if (syncedTime >= currentWord.start) {
          if (nextWord) {
            // Highlight current word until next word begins
            if (syncedTime < nextWord.start) {
              foundIndex = i;
              console.log(`Highlighting word ${i}: "${currentWord.text}" | Audio: ${actualTime.toFixed(2)}s | Word: ${currentWord.start.toFixed(2)}s - ${nextWord.start.toFixed(2)}s | Offset: ${syncOffset.toFixed(2)}s`);
              break;
            }
          } else {
            // Last word - highlight until the end
            foundIndex = i;
            break;
          }
        }
      }
      
      if (foundIndex !== -1 && foundIndex !== currentWordIndex) {
        setCurrentWordIndex(foundIndex);
      }
    }
  };

  const handleProgressClick = (e) => {
    if (!audioRef.current || !duration) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newTime = (clickX / rect.width) * duration;
    
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleLyricClick = (word, index) => {
    if (!audioRef.current) return;
    
    // Jump to the start time of the clicked word
    // Account for sync offset to land at the exact beginning
    const targetTime = word.start - syncOffset;
    audioRef.current.currentTime = targetTime;
    setCurrentTime(targetTime);
    setCurrentWordIndex(index);
    
    // Re-enable auto-scroll since user clicked to jump to this lyric
    console.log('Auto-scroll re-enabled - user clicked lyric');
    setAutoScrollEnabled(true);
    
    // Auto-play if not already playing
    if (!isPlaying) {
      audioRef.current.play();
      intervalRef.current = setInterval(updateProgress, 100);
      setIsPlaying(true);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Group words into lines based on timing gaps and punctuation
  const groupWordsIntoLines = () => {
    if (!karaokeData?.lyrics) return [];
    
    const lines = [];
    let currentLine = [];
    
    karaokeData.lyrics.forEach((word, index) => {
      currentLine.push({ ...word, index });
      
      // Start new line if:
      // 1. Word ends with punctuation (. ! ? , etc) OR
      // 2. Large gap to next word (>0.8s) OR
      // 3. Every ~10-12 words as fallback
      const nextWord = karaokeData.lyrics[index + 1];
      const endsWithPunctuation = /[.!?,;:]$/.test(word.text);
      const largeGap = nextWord && (nextWord.start - word.end) > 0.8;
      const lineTooLong = currentLine.length >= 12;
      
      if (endsWithPunctuation || largeGap || lineTooLong || !nextWord) {
        lines.push([...currentLine]);
        currentLine = [];
      }
    });
    
    return lines;
  };

  const renderLyrics = () => {
    if (!karaokeData?.lyrics) return null;
    
    const lines = groupWordsIntoLines();
    
    // Find which line contains the current word
    let currentLineIndex = -1;
    lines.forEach((line, lineIdx) => {
      line.forEach((word) => {
        if (word.index === currentWordIndex) {
          currentLineIndex = lineIdx;
        }
      });
    });

    return (
      <div className="lyrics-container-spotify">
        {lines.map((line, lineIdx) => {
          let lineClassName = 'lyric-line';
          
          if (lineIdx < currentLineIndex) {
            lineClassName = 'lyric-line past';
          } else if (lineIdx === currentLineIndex) {
            lineClassName = 'lyric-line current';
          } else {
            lineClassName = 'lyric-line future';
          }
          
          return (
            <div 
              key={lineIdx} 
              className={lineClassName}
              ref={lineIdx === currentLineIndex ? currentWordRef : null}
            >
              {line.map((word) => (
                <span 
                  key={word.index} 
                  className={`lyric-word-inline ${word.index === currentWordIndex ? 'active' : ''}`}
                  onClick={() => handleLyricClick(word, word.index)}
                >
                  {word.text}
                </span>
              ))}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="karaoke-container">
      <div className="karaoke-header">
        <button onClick={onBack} className="back-button">
          ← Back to Search
        </button>
        
        <div className="song-info">
          <h2>{song.title}</h2>
          <p>by {song.artist}</p>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <button onClick={processSong} className="search-button">
            Try Again
          </button>
        </div>
      )}

      {isProcessing && (
        <div className="processing-message">
          <div className="loading-spinner"></div>
          <h3>Processing Song...</h3>
          <p>This may take 3-5 minutes</p>
          <ul style={{ textAlign: 'left', maxWidth: '400px', margin: '0 auto' }}>
            <li>Downloading song from YouTube</li>
            <li>Separating vocals and instrumental with AI</li>
            <li>Transcribing vocals with Whisper</li>
            <li>Syncing lyrics with timestamps</li>
          </ul>
        </div>
      )}

      {karaokeData && !isProcessing && (
        <>
          <div className="karaoke-display">
            {renderLyrics()}
          </div>

          <audio
            ref={audioRef}
            src={`${API_BASE_URL}${karaokeData.audio_url}`}
            onLoadedMetadata={() => {
              if (audioRef.current) {
                setDuration(audioRef.current.duration);
              }
            }}
            onTimeUpdate={updateProgress}
            onEnded={() => {
              setIsPlaying(false);
              if (intervalRef.current) {
                clearInterval(intervalRef.current);
              }
            }}
          />
        </>
      )}

      {/* Sticky Audio Controls - Always visible at bottom */}
      {karaokeData && !isProcessing && (
        <div className="audio-controls-sticky">
          <div className="audio-controls">
            <button onClick={handlePlayPause} className="control-button">
              {isPlaying ? '⏸️' : '▶️'}
            </button>
            
            <div className="time-display">
              {formatTime(currentTime)}
            </div>
            
            <div className="progress-bar" onClick={handleProgressClick}>
              <div 
                className="progress-fill" 
                style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
              />
            </div>
            
            <div className="time-display">
              {formatTime(duration)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KaraokePlayer;
