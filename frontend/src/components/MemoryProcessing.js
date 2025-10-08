import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RitualAnimation = ({ ritual, onComplete }) => {
  useEffect(() => {
    // Auto-complete animation after delay
    const timer = setTimeout(() => {
      onComplete();
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [onComplete]);
  
  if (ritual === "fire") {
    return (
      <div className="ritual-container" data-testid="ritual-fire">
        <div className="fire-animation">
          <div className="flame"></div>
          <div className="flame delay-1"></div>
          <div className="flame delay-2"></div>
          <div className="paper burning">
            <p className="old-story">Old Story</p>
          </div>
        </div>
        <p className="ritual-text">Watch it burn...</p>
      </div>
    );
  }
  
  if (ritual === "water") {
    return (
      <div className="ritual-container" data-testid="ritual-water">
        <div className="water-animation">
          <div className="river"></div>
          <div className="boat floating">
            <div className="boat-content">📜</div>
          </div>
          <div className="ripple"></div>
          <div className="ripple delay-1"></div>
        </div>
        <p className="ritual-text">Watch it float away...</p>
      </div>
    );
  }
  
  if (ritual === "earth") {
    return (
      <div className="ritual-container" data-testid="ritual-earth">
        <div className="earth-animation">
          <div className="soil"></div>
          <div className="seed planting"></div>
          <div className="sprout growing"></div>
        </div>
        <p className="ritual-text">Watch what grows...</p>
      </div>
    );
  }
  
  if (ritual === "air") {
    return (
      <div className="ritual-container" data-testid="ritual-air">
        <div className="air-animation">
          <div className="leaf drifting"></div>
          <div className="leaf drifting delay-1"></div>
          <div className="leaf drifting delay-2"></div>
          <div className="wind-lines"></div>
        </div>
        <p className="ritual-text">Watch them scatter...</p>
      </div>
    );
  }
  
  if (ritual === "archive") {
    return (
      <div className="ritual-container" data-testid="ritual-archive">
        <div className="archive-animation">
          <div className="vault">
            <div className="vault-door closing"></div>
            <div className="lock"></div>
          </div>
        </div>
        <p className="ritual-text">The vault is closing...</p>
      </div>
    );
  }
  
  return null;
};

const MemoryProcessingInterface = ({ topic, onClose }) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState("externalize");
  const [showRitual, setShowRitual] = useState(false);
  const [selectedRitual, setSelectedRitual] = useState(null);
  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    startProcessing();
  }, []);
  
  const startProcessing = async () => {
    try {
      const response = await axios.post(`${API}/memory/start`, {
        user_id: "default_user",
        memory_topic: topic
      });
      
      setSessionId(response.data.session_id);
      setPhase(response.data.phase);
      
      // Display messages sequentially
      const messageChunks = response.data.messages || [];
      for (let i = 0; i < messageChunks.length; i++) {
        const chunk = messageChunks[i];
        
        setLoading(true);
        await new Promise(resolve => setTimeout(resolve, chunk.typing_delay || 1000));
        
        const assistantMsg = {
          role: 'assistant',
          content: chunk.content,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMsg]);
        setLoading(false);
        
        if (i < messageChunks.length - 1 && chunk.pause_after) {
          await new Promise(resolve => setTimeout(resolve, chunk.pause_after));
        }
      }
    } catch (error) {
      console.error("Error starting memory processing:", error);
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
      const response = await axios.post(`${API}/memory/message`, {
        session_id: sessionId,
        message: inputMessage,
        user_id: "default_user"
      });
      
      // Handle chunked messages
      const messageChunks = response.data.messages || [];
      
      for (let i = 0; i < messageChunks.length; i++) {
        const chunk = messageChunks[i];
        
        setLoading(true);
        await new Promise(resolve => setTimeout(resolve, chunk.typing_delay || 1000));
        
        const assistantMsg = {
          role: 'assistant',
          content: chunk.content,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMsg]);
        setLoading(false);
        
        if (i < messageChunks.length - 1 && chunk.pause_after) {
          await new Promise(resolve => setTimeout(resolve, chunk.pause_after));
        }
      }
      
      // Update phase if changed
      if (response.data.phase !== phase) {
        setPhase(response.data.phase);
      }
      
      // Check for ritual trigger
      const lastMessage = messageChunks[messageChunks.length - 1];
      if (lastMessage && lastMessage.content.includes("🔥") || 
          lastMessage.content.includes("💧") ||
          lastMessage.content.includes("🌱") ||
          lastMessage.content.includes("🌬️") ||
          lastMessage.content.includes("📦")) {
        // Ritual selection message detected
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setLoading(false);
    }
  };
  
  const selectRitual = async (ritual) => {
    setSelectedRitual(ritual);
    setShowRitual(true);
    
    // Update backend
    await axios.post(`${API}/memory/update-phase`, {
      session_id: sessionId,
      user_id: "default_user",
      phase_data: {
        ritual_chosen: ritual
      }
    });
  };
  
  const completeRitual = async () => {
    setShowRitual(false);
    
    // Update backend
    await axios.post(`${API}/memory/update-phase`, {
      session_id: sessionId,
      user_id: "default_user",
      phase_data: {
        ritual_completed: true,
        closure_achieved: true
      }
    });
    
    // Show completion message
    const completionMsg = {
      role: 'assistant',
      content: "Your brain just received a completion signal. This memory has been processed.",
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, completionMsg]);
  };
  
  return (
    <div className="memory-processing-container">
      {showRitual ? (
        <div className="ritual-overlay">
          <RitualAnimation 
            ritual={selectedRitual} 
            onComplete={completeRitual}
          />
        </div>
      ) : (
        <>
          <div className="processing-header">
            <div className="phase-indicator">
              <span className={phase === "externalize" ? "active" : ""}>Externalize</span>
              <span className={phase === "reframe" ? "active" : ""}>Reframe</span>
              <span className={phase === "distance" ? "active" : ""}>Distance</span>
              <span className={phase === "release" ? "active" : ""}>Release</span>
            </div>
            <Button variant="ghost" onClick={onClose}>Exit</Button>
          </div>
          
          <div className="processing-messages" data-testid="processing-messages">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`message ${msg.role}`}
                data-testid={`processing-message-${msg.role}-${idx}`}
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
          
          {phase === "release" && !selectedRitual && (
            <div className="ritual-selector">
              <p>Choose your completion ritual:</p>
              <div className="ritual-options">
                <Button onClick={() => selectRitual("fire")} data-testid="ritual-fire-btn">
                  🔥 Fire
                </Button>
                <Button onClick={() => selectRitual("water")} data-testid="ritual-water-btn">
                  💧 Water
                </Button>
                <Button onClick={() => selectRitual("earth")} data-testid="ritual-earth-btn">
                  🌱 Earth
                </Button>
                <Button onClick={() => selectRitual("air")} data-testid="ritual-air-btn">
                  🌬️ Air
                </Button>
                <Button onClick={() => selectRitual("archive")} data-testid="ritual-archive-btn">
                  📦 Archive
                </Button>
              </div>
            </div>
          )}
          
          <div className="processing-input">
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
              data-testid="processing-input"
            />
            <Button 
              onClick={sendMessage} 
              disabled={!inputMessage.trim() || loading}
              data-testid="processing-send-button"
            >
              Send
            </Button>
          </div>
        </>
      )}
    </div>
  );
};

export default MemoryProcessingInterface;
