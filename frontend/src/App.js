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
  const [editingIndex, setEditingIndex] = useState(null);
  const [editText, setEditText] = useState('');
  const [streamingIndex, setStreamingIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);


  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    // Use requestAnimationFrame for smoother scrolling during streaming
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
    });
  }, [messages]);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      textarea.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [input]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

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

    // Cancel any ongoing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    const userMessage = {
      role: 'user',
      content: input.trim() || (imageFile || imageUrl ? 'Analyze this image' : ''),
      image: imagePreview || imageUrl || null,
    };

    setMessages(prev => [...prev, userMessage]);
    const currentPrompt = input.trim() || (imageFile || imageUrl ? 'What is in this image? Describe it in detail.' : '');
    setInput('');
    setError(null);

    // Create assistant message placeholder for streaming
    const assistantMessageIndex = messages.length + 1;
    const assistantMessage = {
      role: 'assistant',
      content: '',
      streaming: true, // Mark as streaming
    };
    setMessages(prev => [...prev, assistantMessage]);
    setStreamingIndex(assistantMessageIndex);
    // Don't set loading=true since we're showing the message directly

    try {
      const formData = new FormData();
      formData.append('prompt', currentPrompt);

      if (imageFile) {
        formData.append('image', imageFile);
      } else if (imageUrl && imageUrl.trim()) {
        formData.append('image_url', imageUrl.trim());
      }

      // Use SSE streaming
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      const response = await fetch(`${API_URL}/stream-analyze`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        // Process complete SSE events (ending with \n\n)
        let eventEndIndex;
        while ((eventEndIndex = buffer.indexOf('\n\n')) !== -1) {
          const eventText = buffer.slice(0, eventEndIndex);
          buffer = buffer.slice(eventEndIndex + 2);
          
          // Parse SSE event
          const lines = eventText.split('\n');
          let eventType = 'message';
          let eventData = '';
          
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }
          
          // Handle done event
          if (eventType === 'done') {
            break;
          }
          
          // Parse data
          if (eventData) {
            try {
              const parsed = JSON.parse(eventData);
              
              if (parsed.error) {
                throw new Error(parsed.message || parsed.detail || 'Streaming error');
              }
              
              if (parsed.text) {
                accumulatedText += parsed.text;
                // Use functional update to ensure we have latest state
                setMessages(prev => {
                  const updated = [...prev];
                  if (updated[assistantMessageIndex]) {
                    updated[assistantMessageIndex] = {
                      ...updated[assistantMessageIndex],
                      content: accumulatedText,
                      streaming: true, // Keep streaming flag
                    };
                  }
                  return updated;
                });
                // Smooth scroll during streaming
                requestAnimationFrame(() => {
                  messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
                });
              }
            } catch (parseErr) {
              // If JSON parse fails, skip this chunk
              console.warn('Failed to parse SSE data:', eventData, parseErr);
            }
          }
        }
      }

      // Final update - remove streaming flag
      setMessages(prev => {
        const updated = [...prev];
        if (updated[assistantMessageIndex]) {
          updated[assistantMessageIndex] = {
            ...updated[assistantMessageIndex],
            content: accumulatedText,
            streaming: false, // Mark as done streaming
          };
        }
        return updated;
      });

    } catch (err) {
      if (err.name === 'AbortError') {
        // Stream was cancelled, remove the assistant message
        setMessages(prev => prev.slice(0, assistantMessageIndex));
      } else {
        console.error('Error:', err);
        setError(
          err.message ||
          'Failed to get response. Please make sure Ollama is running and try again.'
        );
        // Update the assistant message with error
        setMessages(prev => {
          const updated = [...prev];
          if (updated[assistantMessageIndex]) {
            updated[assistantMessageIndex] = {
              ...updated[assistantMessageIndex],
              content: `Error: ${err.message || 'Failed to get response'}`,
              streaming: false,
            };
          }
          return updated;
        });
      }
    } finally {
      setLoading(false);
      setStreamingIndex(null);
      abortControllerRef.current = null;
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
    // Cancel any ongoing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setMessages([]);
    setInput('');
    setImageFile(null);
    setImagePreview(null);
    setImageUrl('');
    setError(null);
    setStreamingIndex(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const handleEditMessage = (index) => {
    setEditingIndex(index);
    setEditText(messages[index].content);
  };

  const handleSaveEdit = (index) => {
    if (!editText.trim()) return;
    
    const updatedMessages = [...messages];
    updatedMessages[index] = {
      ...updatedMessages[index],
      content: editText.trim()
    };
    setMessages(updatedMessages);
    setEditingIndex(null);
    setEditText('');
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditText('');
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
          {messages.length === 0 && (
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
              {message.role === 'user' && (
                <div className="message-avatar user-avatar">
                  👤
                </div>
              )}
              <div className={`message-content-wrapper ${message.role}`}>
                <div className="message-content">
                  {message.image && (
                    <div className="message-image">
                      <img src={message.image} alt="Uploaded" />
                    </div>
                  )}
                  {message.role === 'user' ? (
                    editingIndex === index ? (
                      <div className="edit-container">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.ctrlKey) {
                              e.preventDefault();
                              handleSaveEdit(index);
                            } else if (e.key === 'Escape') {
                              handleCancelEdit();
                            }
                          }}
                          className="edit-textarea"
                          rows={3}
                          autoFocus
                        />
                        <div className="edit-actions">
                          <button
                            onClick={() => handleSaveEdit(index)}
                            className="edit-save-btn"
                            title="Save (Ctrl+Enter)"
                          >
                            ✓
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="edit-cancel-btn"
                            title="Cancel (Esc)"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="user-text-wrapper">
                        <div className="user-text">{message.content}</div>
                        <div className="message-actions">
                          <button
                            onClick={() => handleEditMessage(index)}
                            className="message-action-btn"
                            title="Edit message"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => copyToClipboard(message.content)}
                            className="message-action-btn"
                            title="Copy to clipboard"
                          >
                            📋
                          </button>
                        </div>
                      </div>
                    )
                  ) : (
                    <div className="assistant-text-wrapper">
                      <div className="assistant-text">
                        {message.content ? (
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
                        ) : (
                          <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        )}
                        {message.streaming && message.content && (
                          <span className="streaming-cursor">▊</span>
                        )}
                      </div>
                      {!message.streaming && message.content && (
                        <div className="message-actions">
                          <button
                            onClick={() => copyToClipboard(message.content)}
                            className="message-action-btn"
                            title="Copy to clipboard"
                          >
                            📋
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
              {message.role === 'assistant' && (
                <div className="message-avatar assistant-avatar">
                  🤖
                </div>
              )}
            </div>
          ))}

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
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  // Auto-resize
                  e.target.style.height = 'auto';
                  const scrollHeight = e.target.scrollHeight;
                  e.target.style.height = `${Math.min(scrollHeight, 200)}px`;
                }}
                onKeyPress={handleKeyPress}
                placeholder="Message Gemma3..."
                rows="1"
                className="message-input"
              />
              
              <button
                type="submit"
                disabled={streamingIndex !== null || (!input.trim() && !imageFile && !imageUrl)}
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
            
          
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
