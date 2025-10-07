import { useState, useEffect, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

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
  const navigate = useNavigate();
  
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
          className="cta-button" 
          onClick={() => navigate('/chat')}
          data-testid="start-checkin-button"
        >
          Start Today's Check-in
        </Button>
        
        <Button 
          variant="outline" 
          className="secondary-button" 
          onClick={() => navigate('/history')}
          data-testid="view-history-button"
        >
          View Your History
        </Button>
      </div>
    </div>
  );
};

const ChatInterface = () => {
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
      
      const assistantMsg = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, assistantMsg]);
      
      if (response.data.crisis_detected) {
        setShowCrisis(true);
      }
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
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
        <h2 data-testid="chat-title">Your Daily Check-in</h2>
        <Button 
          variant="outline" 
          onClick={endSession}
          data-testid="end-session-button"
        >
          End Session
        </Button>
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
  const location = window.location;
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

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/chat" element={<ChatInterface />} />
          <Route path="/summary" element={<SessionSummary />} />
          <Route path="/history" element={<EmotionHistory />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
