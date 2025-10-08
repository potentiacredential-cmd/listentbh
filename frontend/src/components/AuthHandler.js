import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthHandler = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    handleAuthentication();
  }, []);

  const handleAuthentication = async () => {
    // Check if there's a session_id in URL fragment
    const hash = window.location.hash;
    const sessionIdMatch = hash.match(/session_id=([^&]+)/);

    if (sessionIdMatch) {
      const sessionId = sessionIdMatch[1];
      
      // Clean URL
      window.history.replaceState(null, "", window.location.pathname);
      
      try {
        // Process session with backend
        const response = await axios.post(`${API}/auth/session-data?session_id=${sessionId}`);
        
        setUser(response.data.user);
        setIsAuthenticated(true);
        setLoading(false);
        
        // Redirect to main app
        navigate('/chat');
      } catch (error) {
        console.error("Authentication error:", error);
        setIsAuthenticated(false);
        setLoading(false);
        navigate('/');
      }
    } else {
      // Check existing session
      checkExistingSession();
    }
  };

  const checkExistingSession = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        withCredentials: true
      });
      
      setIsAuthenticated(false);
      setUser(null);
      navigate('/');
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return children({ isAuthenticated, user, logout });
};

export default AuthHandler;
