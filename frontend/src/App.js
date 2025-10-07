import React, { useState } from 'react';
import './App.css';
import SearchComponent from './components/SearchComponent';
import KaraokePlayer from './components/KaraokePlayer';

function App() {
  const [selectedSong, setSelectedSong] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSongSelect = (song) => {
    setSelectedSong(song);
    setIsProcessing(true);
  };

  const handleBackToSearch = () => {
    setSelectedSong(null);
    setIsProcessing(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎤 Karaoke Platform</h1>
      </header>
      
      <main className="App-main">
        {!selectedSong ? (
          <SearchComponent onSongSelect={handleSongSelect} />
        ) : (
          <KaraokePlayer 
            song={selectedSong} 
            onBack={handleBackToSearch}
            isProcessing={isProcessing}
            setIsProcessing={setIsProcessing}
          />
        )}
      </main>
    </div>
  );
}

export default App;