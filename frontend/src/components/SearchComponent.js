import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const SearchComponent = ({ onSongSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const response = await axios.post(`${API_BASE_URL}/search`, {
        query: query.trim()
      });
      
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSongClick = (song) => {
    onSongSelect(song);
  };

  return (
    <div className="search-container">
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a song... (e.g., 'Bohemian Rhapsody Queen')"
          className="search-input"
        />
        <button 
          type="submit" 
          disabled={loading || !query.trim()}
          className="search-button"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <h3>Search Error</h3>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="processing-message">
          <div className="loading-spinner"></div>
          <p>Searching YouTube...</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          <h3>Search Results</h3>
          {results.map((song) => (
            <div 
              key={song.id} 
              className="song-item"
              onClick={() => handleSongClick(song)}
            >
              <div className="song-title">{song.title}</div>
              <div className="song-artist">{song.artist}</div>
              <div className="song-duration">{song.duration}</div>
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="search-results">
          <p>No results found. Try a different search term.</p>
        </div>
      )}
    </div>
  );
};

export default SearchComponent;
