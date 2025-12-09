import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Check Ollama connectivity on mount
  useEffect(() => {
    const checkOllamaStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/health`);
        setOllamaStatus(response.data);
      } catch (err) {
        setOllamaStatus({
          ollama_status: 'error',
          ollama_error: 'Failed to connect to backend API'
        });
      }
    };
    checkOllamaStatus();
    // Check every 30 seconds
    const interval = setInterval(checkOllamaStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please upload an image file');
        return;
      }
      
      if (file.size > 10 * 1024 * 1024) {
        setError('Image size should be less than 10MB');
        return;
      }

      setImageFile(file);
      setImageUrl('');
      setError(null);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveImage = () => {
    setImageFile(null);
    setImagePreview(null);
    setImageUrl('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    
    if (!input.trim() && !imageFile && !imageUrl) {
      return;
    }

    const userMessage = {
      role: 'user',
      content: input.trim() || (imageFile || imageUrl ? 'Analyze this image' : ''),
      image: imagePreview || imageUrl || null,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    const currentPrompt = input.trim() || (imageFile || imageUrl ? 'What is in this image? Describe it in detail.' : '');

    try {
      const formData = new FormData();
      formData.append('prompt', currentPrompt);

      if (imageFile) {
        formData.append('image', imageFile);
      } else if (imageUrl && imageUrl.trim()) {
        formData.append('image_url', imageUrl.trim());
      }

      const response = await axios.post(
        `${API_URL}/analyze`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 180000,
        }
      );

      if (response.data.success) {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response,
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        setError(response.data.message || 'Failed to get response');
      }
    } catch (err) {
      console.error('Error:', err);
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to get response. Please make sure Ollama is running and try again.'
      );
    } finally {
      setLoading(false);
      handleRemoveImage();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
    setImageFile(null);
    setImagePreview(null);
    setImageUrl('');
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  return (
    <div className="App">
      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <h1>Gemma3 Vision</h1>
          {messages.length > 0 && (
            <button onClick={handleClear} className="clear-chat-btn">
              Clear Chat
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="messages-container">
          {messages.length === 0 && !loading && (
            <div className="welcome-message">
              <div className="welcome-icon">🔍</div>
              <h2>Welcome to Gemma3 Vision</h2>
              <p>Ask me anything or upload an image to analyze!</p>
              <div className="welcome-examples">
                <div className="example-item">
                  <span className="example-icon">💬</span>
                  <span>Ask questions</span>
                </div>
                <div className="example-item">
                  <span className="example-icon">🖼️</span>
                  <span>Upload images</span>
                </div>
                <div className="example-item">
                  <span className="example-icon">🔗</span>
                  <span>Use image URLs</span>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                {message.image && (
                  <div className="message-image">
                    <img src={message.image} alt="Uploaded" />
                  </div>
                )}
                {message.role === 'user' ? (
                  <div className="user-text">{message.content}</div>
                ) : (
                  <div className="assistant-text">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        },
                        table({ children }) {
                          return (
                            <div className="table-wrapper">
                              <table>{children}</table>
                            </div>
                          );
                        },
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                    <button
                      onClick={() => copyToClipboard(message.content)}
                      className="copy-message-btn"
                      title="Copy to clipboard"
                    >
                      📋
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          {ollamaStatus && ollamaStatus.ollama_status !== 'connected' && (
            <div className="error-banner ollama-warning">
              ⚠️ Ollama Connection Issue: {ollamaStatus.ollama_error || 'Ollama is not connected'}
              {ollamaStatus.ollama_url && (
                <span className="ollama-url"> ({ollamaStatus.ollama_url})</span>
              )}
              <button onClick={() => setOllamaStatus(null)} className="error-close">×</button>
            </div>
          )}

          {error && (
            <div className="error-banner">
              ⚠️ {error}
              <button onClick={() => setError(null)} className="error-close">×</button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="input-container">
          {(imagePreview || imageUrl) && (
            <div className="image-attachment">
              <img src={imagePreview || imageUrl} alt="Preview" />
              <button onClick={handleRemoveImage} className="remove-attachment">×</button>
            </div>
          )}
          
          <form onSubmit={handleSend} className="input-form">
            <div className="input-wrapper">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="attach-btn"
                title="Attach image"
              >
                📎
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                style={{ display: 'none' }}
              />
              
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Message Gemma3..."
                rows="1"
                className="message-input"
              />
              
              <button
                type="submit"
                disabled={loading || (!input.trim() && !imageFile && !imageUrl)}
                className="send-btn"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path
                    d="M18 2L9 11M18 2L12 18L9 11M18 2L2 8L9 11"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
            
            <div className="input-footer">
              <button
                type="button"
                onClick={() => {
                  const url = prompt('Enter image URL:');
                  if (url) {
                    setImageUrl(url);
                    setImageFile(null);
                    setImagePreview(null);
                  }
                }}
                className="url-btn"
              >
                🔗 Image URL
              </button>
              <span className="input-hint">Press Enter to send, Shift+Enter for new line</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
