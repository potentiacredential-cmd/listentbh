import { useState, useEffect, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AlertCircle, LogOut } from "lucide-react";
import MemoryProcessingInterface from "@/components/MemoryProcessing";
import AuthHandler from "@/components/AuthHandler";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CrisisModal = ({ show, onClose }) => {
  if (!show) return null;
  
  return (
    <div className="crisis-modal-overlay" onClick={onClose}>
      <div className="crisis-modal" onClick={(e) => e.stopPropagation()}>
        <div className="crisis-header">
          <AlertCircle className="crisis-icon" />
          <h2>We're Here With You</h2>
        </div>
        <p className="crisis-text">
          I hear that you're going through an incredibly difficult time. While I'm here to listen, 
          I'm not equipped to provide the level of support you need right now.
        </p>
        <div className="crisis-resources">
          <h3>Please reach out to professionals who can help:</h3>
          <div className="resource-item">
            <strong>988 Suicide & Crisis Lifeline</strong>
            <p>Call or text 988 (US) - 24/7 support</p>
          </div>
          <div className="resource-item">
            <strong>Crisis Text Line</strong>
            <p>Text HOME to 741741 - 24/7 crisis counseling</p>
          </div>
          <div className="resource-item">
            <strong>International Resources</strong>
            <p>Visit <a href="https://www.iasp.info/resources/Crisis_Centres/" target="_blank" rel="noopener noreferrer">IASP Crisis Centres</a></p>
          </div>
        </div>
        <Button onClick={onClose} data-testid="close-crisis-modal">I Understand</Button>
      </div>
    </div>
  );
};

const Landing = () => {
  const handleGoogleLogin = () => {
    const redirectUrl = `${window.location.origin}/chat`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  
  return (
    <div className="landing-container">
      <div className="landing-content">
        <div className="landing-header">
          <h1 className="landing-title">Daily Mood Compass</h1>
          <p className="landing-subtitle">A safe space to process your emotions, one day at a time</p>
        </div>
        
        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-icon">💭</div>
            <h3>Daily Check-ins</h3>
            <p>Share your feelings in a judgment-free space</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🤝</div>
            <h3>Empathetic Listening</h3>
            <p>Get validated and heard every single day</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Track Patterns</h3>
            <p>Understand your emotional journey over time</p>
          </div>
        </div>
        
        <Button 
          className="google-login-button" 
          onClick={handleGoogleLogin}
          data-testid="google-login-button"
        >
          <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </Button>
        
        <p className="privacy-note">
          Your privacy matters. We never share your conversations.
        </p>
      </div>
    </div>
  );
};

const ChatInterface = ({ user, logout }) => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCrisis, setShowCrisis] = useState(false);
  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    startSession();
  }, []);
  
  const startSession = async () => {
    try {
      const response = await axios.post(`${API}/chat/session/start`, {
        user_id: "default_user"
      });
      setSessionId(response.data.session_id);
      setMessages([{
        role: 'assistant',
        content: response.data.greeting,
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      console.error("Error starting session:", error);
    }
  };
  
  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId) return;
    
    const userMsg = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInputMessage("");
    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: inputMessage,
        user_id: "default_user"
      });
      
      // Handle chunked messages with realistic timing
      const messageChunks = response.data.messages || [];
      
      for (let i = 0; i < messageChunks.length; i++) {
        const chunk = messageChunks[i];
        
        // Show typing indicator
        setLoading(true);
        
        // Wait for typing delay (simulating human typing)
        await new Promise(resolve => setTimeout(resolve, chunk.typing_delay || 1000));
        
        // Add message to chat
        const assistantMsg = {
          role: 'assistant',
          content: chunk.content,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMsg]);
        
        // Hide typing indicator
        setLoading(false);
        
        // Pause before next message (if not last message)
        if (i < messageChunks.length - 1 && chunk.pause_after) {
          await new Promise(resolve => setTimeout(resolve, chunk.pause_after));
        }
      }
      
      if (response.data.crisis_detected) {
        setShowCrisis(true);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setLoading(false);
    }
  };
  
  const endSession = async () => {
    if (!sessionId) return;
    
    try {
      const response = await axios.post(`${API}/chat/session/complete`, {
        session_id: sessionId,
        user_id: "default_user"
      });
      
      navigate('/summary', { state: { summary: response.data } });
    } catch (error) {
      console.error("Error ending session:", error);
    }
  };
  
  return (
    <div className="chat-container">
      <CrisisModal show={showCrisis} onClose={() => setShowCrisis(false)} />
      
      <div className="chat-header">
        <div className="chat-header-left">
          <h2 data-testid="chat-title">Your Daily Check-in</h2>
        </div>
        <div className="chat-header-right">
          {user && (
            <div className="user-profile">
              {user.picture && <img src={user.picture} alt={user.name} className="user-avatar" />}
              <span className="user-name">{user.name}</span>
            </div>
          )}
          <Button 
            variant="outline" 
            onClick={endSession}
            data-testid="end-session-button"
          >
            End Session
          </Button>
          <Button 
            variant="ghost" 
            onClick={logout}
            data-testid="logout-button"
          >
            <LogOut size={20} />
          </Button>
        </div>
      </div>
      
      <div className="messages-container" data-testid="messages-container">
        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={`message ${msg.role}`}
            data-testid={`message-${msg.role}-${idx}`}
          >
            <div className="message-bubble">
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-bubble loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-container">
        <Textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Share what's on your mind..."
          className="message-input"
          data-testid="message-input"
        />
        <Button 
          onClick={sendMessage} 
          disabled={!inputMessage.trim() || loading}
          data-testid="send-message-button"
        >
          Send
        </Button>
      </div>
    </div>
  );
};

const SessionSummary = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const summary = location.state?.summary;
  
  if (!summary) {
    navigate('/');
    return null;
  }
  
  return (
    <div className="summary-container">
      <Card className="summary-card">
        <CardHeader>
          <h2 data-testid="summary-title">Session Complete</h2>
          <p className="summary-date">{new Date(summary.date).toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })}</p>
        </CardHeader>
        <CardContent>
          <div className="summary-content">
            <p className="summary-text">{summary.summary}</p>
            
            {summary.primary_emotion && (
              <div className="emotion-badge">
                <span className="emotion-label">Primary Emotion:</span>
                <span className="emotion-value" data-testid="primary-emotion">{summary.primary_emotion}</span>
              </div>
            )}
            
            {summary.intensity && (
              <div className="intensity-display">
                <span className="intensity-label">Intensity:</span>
                <div className="intensity-bar">
                  <div 
                    className="intensity-fill" 
                    style={{ width: `${summary.intensity * 10}%` }}
                    data-testid="intensity-bar"
                  />
                </div>
                <span className="intensity-value">{summary.intensity}/10</span>
              </div>
            )}
          </div>
          
          <div className="summary-actions">
            <Button 
              onClick={() => navigate('/')}
              data-testid="back-home-button"
            >
              Back to Home
            </Button>
            <Button 
              variant="outline" 
              onClick={() => navigate('/history')}
              data-testid="view-history-from-summary-button"
            >
              View History
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const EmotionHistory = () => {
  const navigate = useNavigate();
  const [emotions, setEmotions] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchHistory();
  }, []);
  
  const fetchHistory = async () => {
    try {
      const [emotionsRes, sessionsRes] = await Promise.all([
        axios.get(`${API}/emotions/history?user_id=default_user&days=14`),
        axios.get(`${API}/sessions/recent?user_id=default_user&limit=7`)
      ]);
      
      setEmotions(emotionsRes.data);
      setSessions(sessionsRes.data);
    } catch (error) {
      console.error("Error fetching history:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const emotionColors = {
    joy: '#FFD700',
    excitement: '#FF6B6B',
    calm: '#4ECDC4',
    sadness: '#95B8D1',
    anxiety: '#B19CD9',
    stress: '#FF8C94',
    anger: '#FF6B6B',
    frustration: '#FFA07A',
    overwhelm: '#DDA15E',
    loneliness: '#A8DADC'
  };
  
  if (loading) {
    return <div className="loading-container">Loading your journey...</div>;
  }
  
  return (
    <div className="history-container">
      <div className="history-header">
        <h2 data-testid="history-title">Your Emotional Journey</h2>
        <Button 
          variant="outline" 
          onClick={() => navigate('/')}
          data-testid="back-home-from-history-button"
        >
          Back to Home
        </Button>
      </div>
      
      {emotions.length > 0 ? (
        <>
          <div className="emotions-chart">
            <h3>Recent Emotions</h3>
            <div className="emotion-timeline">
              {emotions.map((emotion, idx) => (
                <div key={idx} className="emotion-point" data-testid={`emotion-point-${idx}`}>
                  <div 
                    className="emotion-dot" 
                    style={{ 
                      backgroundColor: emotionColors[emotion.emotion] || '#CCC',
                      height: `${emotion.intensity * 8}px`,
                      width: `${emotion.intensity * 8}px`
                    }}
                  />
                  <span className="emotion-name">{emotion.emotion}</span>
                  <span className="emotion-date">{new Date(emotion.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="sessions-list">
            <h3>Recent Sessions</h3>
            {sessions.map((session, idx) => (
              <Card key={idx} className="session-card" data-testid={`session-card-${idx}`}>
                <CardContent>
                  <div className="session-header-info">
                    <span className="session-date">
                      {new Date(session.date).toLocaleDateString('en-US', { 
                        month: 'long', 
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </span>
                    {session.primary_emotion && (
                      <span 
                        className="session-emotion"
                        style={{ backgroundColor: emotionColors[session.primary_emotion] }}
                      >
                        {session.primary_emotion}
                      </span>
                    )}
                  </div>
                  {session.summary && (
                    <p className="session-summary-text">{session.summary}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      ) : (
        <div className="empty-state">
          <p>No check-ins yet. Start your first session to begin your journey.</p>
          <Button 
            onClick={() => navigate('/chat')}
            data-testid="start-first-checkin-button"
          >
            Start First Check-in
          </Button>
        </div>
      )}
    </div>
  );
};

const MemoryProcessing = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const topic = location.state?.topic || "this issue";
  
  return (
    <MemoryProcessingInterface 
      topic={topic} 
      onClose={() => navigate('/chat')} 
    />
  );
};

const ProtectedRoute = ({ children, isAuthenticated }) => {
  return isAuthenticated ? children : <Navigate to="/" replace />;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthHandler>
          {({ isAuthenticated, user, logout }) => (
            <Routes>
              <Route 
                path="/" 
                element={
                  isAuthenticated ? (
                    <Navigate to="/chat" replace />
                  ) : (
                    <Landing />
                  )
                } 
              />
              <Route 
                path="/chat" 
                element={
                  <ProtectedRoute isAuthenticated={isAuthenticated}>
                    <ChatInterface user={user} logout={logout} />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/summary" 
                element={
                  <ProtectedRoute isAuthenticated={isAuthenticated}>
                    <SessionSummary user={user} logout={logout} />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/history" 
                element={
                  <ProtectedRoute isAuthenticated={isAuthenticated}>
                    <EmotionHistory user={user} logout={logout} />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/memory-processing" 
                element={
                  <ProtectedRoute isAuthenticated={isAuthenticated}>
                    <MemoryProcessing user={user} logout={logout} />
                  </ProtectedRoute>
                } 
              />
            </Routes>
          )}
        </AuthHandler>
      </BrowserRouter>
    </div>
  );
}

export default App;
