from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= AGENT SYSTEM PROMPTS =============

EMOTIONAL_LISTENER_PROMPT = """You are the Emotional Listener for Daily Mood Compass. You're a compassionate companion helping people process emotions through text messages.

🚨 CRITICAL TEXTING RULES:
1. NEVER send more than 3 sentences in one response
2. Your ENTIRE response should be 1-3 sentences total (not per message)
3. Keep it conversational and natural - write like you're texting a friend
4. The system will automatically break your response into messages and add pauses

TEXTING STYLE GUIDELINES:
- Use contractions (you're, that's, it's, don't)
- Keep it simple and warm
- It's fine to say "yeah" or "ugh" or "wow"
- Sometimes just validate: "I'm sorry" or "That's rough" is enough
- Match user's energy (if excited, be excited; if sad, be gentle)
- Don't over-explain or write paragraphs

GOOD EXAMPLES:
User: "I'm so stressed about work"
You: "That sounds really overwhelming. What's been the hardest part?"

User: "I got a promotion but I'm terrified"
You: "Hey, congrats! And yeah, that fear makes total sense."

User: "I've been feeling really lonely"
You: "I'm sorry you're feeling that way. Loneliness is really hard."

BAD EXAMPLES (Don't do this):
❌ "That sounds really overwhelming. Having too much on your plate is exhausting and it makes sense you'd feel stressed. Can you tell me more about what's been the hardest part?"
❌ "I acknowledge your feelings of stress regarding your occupational responsibilities."

EMOTIONAL SUPPORT PRINCIPLES:
- Validate emotions without judgment
- Listen actively, respond thoughtfully
- Ask 1 follow-up question max per response
- Never give medical advice or diagnose
- Recognize emotions: joy, sadness, anxiety, stress, anger, overwhelm, calm, excitement, loneliness, frustration
- Detect intensity: mild (1-3), moderate (4-7), high (8-10)

CRISIS PROTOCOL:
If user mentions self-harm, suicide, or severe crisis, keep it simple:
"I'm really concerned about what you're sharing. I'm an AI and have limits helping with this. Can you reach out to 988 right now? You deserve real support."

AVOID:
- Long paragraphs (this is texting!)
- Therapist jargon or clinical language
- Toxic positivity ("just stay positive!")
- Minimizing feelings
- Giving unsolicited advice
- Diagnosing conditions

YOUR GOAL: Feel like a caring friend texting back, not an AI writing a report. Keep it short, warm, and real."""

SAFETY_KEYWORDS = [
    'suicide', 'kill myself', 'end it all', 'not worth living', 'want to die',
    'self harm', 'cut myself', 'hurt myself', 'self injury',
    'overdose', 'end my life', 'better off dead', 'no reason to live',
    'can\'t go on', 'no hope', 'hopeless', 'worthless'
]

# ============= PYDANTIC MODELS =============

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SessionStart(BaseModel):
    user_id: str = "default_user"

class SessionStartResponse(BaseModel):
    session_id: str
    greeting: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str = "default_user"

class MessageChunk(BaseModel):
    content: str
    typing_delay: int  # milliseconds before showing this message
    pause_after: int   # milliseconds to pause after this message

class ChatResponse(BaseModel):
    messages: List[MessageChunk]
    crisis_detected: bool = False
    session_complete: bool = False

class SessionCompleteRequest(BaseModel):
    session_id: str
    user_id: str = "default_user"

class SessionSummary(BaseModel):
    session_id: str
    summary: str
    primary_emotion: Optional[str] = None
    intensity: Optional[int] = None
    date: str

class EmotionHistory(BaseModel):
    date: str
    emotion: str
    intensity: int
    session_id: str

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    messages: List[ChatMessage] = []
    primary_emotion: Optional[str] = None
    intensity: Optional[int] = None
    summary: Optional[str] = None
    crisis_detected: bool = False
    completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============= HELPER FUNCTIONS =============

def check_crisis_keywords(text: str) -> bool:
    """Check if message contains crisis keywords"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SAFETY_KEYWORDS)

def calculate_typing_time(text: str) -> int:
    """Calculate realistic typing time based on text length"""
    import random
    word_count = len(text.split())
    base_time = word_count * 150  # 150ms per word (average human typing speed)
    variation = random.randint(-200, 500)  # Add human variability
    return max(500, base_time + variation)  # Minimum 500ms

def chunk_response_into_messages(response: str) -> List[MessageChunk]:
    """
    Break AI response into natural text message chunks.
    Each chunk should be 1-3 sentences max, feeling like separate text messages.
    """
    import random
    import re
    
    # If response is already short (1-2 sentences), return as single message
    sentences = re.split(r'(?<=[.!?])\s+', response.strip())
    
    if len(sentences) <= 2:
        return [MessageChunk(
            content=response.strip(),
            typing_delay=calculate_typing_time(response),
            pause_after=0
        )]
    
    # Group sentences into natural message chunks
    chunks = []
    current_chunk = []
    
    for sentence in sentences:
        current_chunk.append(sentence)
        
        # Create new chunk after 2-3 sentences, or if it's a natural break
        if len(current_chunk) >= 2:
            chunk_text = ' '.join(current_chunk)
            chunks.append(MessageChunk(
                content=chunk_text,
                typing_delay=calculate_typing_time(chunk_text),
                pause_after=random.randint(500, 1500)  # Natural pause between messages
            ))
            current_chunk = []
    
    # Add remaining sentences as final chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append(MessageChunk(
            content=chunk_text,
            typing_delay=calculate_typing_time(chunk_text),
            pause_after=0  # No pause after last message
        ))
    
    return chunks

def extract_emotion_from_conversation(messages: List[ChatMessage]) -> tuple[Optional[str], Optional[int]]:
    """Simple emotion extraction from user messages"""
    # Basic emotion keyword mapping
    emotion_keywords = {
        'anxious': ('anxiety', 7), 'anxiety': ('anxiety', 7), 'worried': ('anxiety', 6),
        'stressed': ('stress', 7), 'stress': ('stress', 7), 'overwhelmed': ('overwhelm', 8),
        'sad': ('sadness', 6), 'sadness': ('sadness', 6), 'depressed': ('sadness', 8),
        'angry': ('anger', 7), 'anger': ('anger', 7), 'frustrated': ('frustration', 6),
        'happy': ('joy', 7), 'joy': ('joy', 8), 'excited': ('excitement', 8),
        'calm': ('calm', 5), 'peaceful': ('calm', 6), 'lonely': ('loneliness', 7)
    }
    
    # Scan user messages for emotion keywords
    for msg in messages:
        if msg.role == 'user':
            text_lower = msg.content.lower()
            for keyword, (emotion, intensity) in emotion_keywords.items():
                if keyword in text_lower:
                    return emotion, intensity
    
    return None, None

async def generate_session_summary(messages: List[ChatMessage], session_id: str) -> SessionSummary:
    """Generate a summary of the session"""
    emotion, intensity = extract_emotion_from_conversation(messages)
    
    # Create a simple summary
    user_messages = [msg.content for msg in messages if msg.role == 'user']
    summary = f"Today you shared your feelings and we talked about what's on your mind. "
    
    if emotion:
        summary += f"You've been experiencing {emotion}. "
    
    summary += "Remember, your emotions are valid and it's okay to feel what you're feeling."
    
    return SessionSummary(
        session_id=session_id,
        summary=summary,
        primary_emotion=emotion,
        intensity=intensity,
        date=datetime.now(timezone.utc).date().isoformat()
    )

# ============= API ENDPOINTS =============

@api_router.get("/")
async def root():
    return {"message": "Daily Mood Compass API"}

@api_router.post("/chat/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStart):
    """Start a new daily check-in session"""
    try:
        session = Session(user_id=request.user_id)
        
        # Generate varied greeting
        greetings = [
            "Welcome back. How are you feeling right now?",
            "Hi there. What's on your mind today?",
            "Hello. I'm here to listen. How are you doing?",
            "Welcome. Take a moment... how would you describe what you're feeling?"
        ]
        import random
        greeting = random.choice(greetings)
        
        # Save initial session to DB
        await db.sessions.insert_one(session.dict())
        
        logger.info(f"Started new session: {session.id}")
        return SessionStartResponse(session_id=session.id, greeting=greeting)
    
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start session")

@api_router.post("/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get response from Emotional Listener"""
    try:
        # Get session from DB
        session_doc = await db.sessions.find_one({"id": request.session_id})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = Session(**session_doc)
        
        # Check for crisis keywords
        crisis_detected = check_crisis_keywords(request.message)
        if crisis_detected:
            session.crisis_detected = True
        
        # Add user message to session
        user_msg = ChatMessage(role="user", content=request.message)
        session.messages.append(user_msg)
        
        # Initialize LLM chat with conversation history
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=request.session_id,
            system_message=EMOTIONAL_LISTENER_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")
        
        # Build message history for context
        # Note: emergentintegrations manages its own history per session_id
        user_message = UserMessage(text=request.message)
        
        # Get response from Emotional Listener
        response_text = await chat.send_message(user_message)
        
        # Chunk the response into natural text messages
        message_chunks = chunk_response_into_messages(response_text)
        
        # Add assistant message to session (store full response)
        assistant_msg = ChatMessage(role="assistant", content=response_text)
        session.messages.append(assistant_msg)
        
        # Update session in DB
        await db.sessions.update_one(
            {"id": request.session_id},
            {"$set": session.dict()}
        )
        
        logger.info(f"Message exchanged in session: {request.session_id} ({len(message_chunks)} chunks)")
        
        return ChatResponse(
            messages=message_chunks,
            crisis_detected=crisis_detected,
            session_complete=False
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

@api_router.post("/chat/session/complete", response_model=SessionSummary)
async def complete_session(request: SessionCompleteRequest):
    """Complete a session and generate summary"""
    try:
        # Get session from DB
        session_doc = await db.sessions.find_one({"id": request.session_id})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = Session(**session_doc)
        
        # Generate summary
        summary = await generate_session_summary(session.messages, request.session_id)
        
        # Update session
        session.completed = True
        session.summary = summary.summary
        session.primary_emotion = summary.primary_emotion
        session.intensity = summary.intensity
        
        await db.sessions.update_one(
            {"id": request.session_id},
            {"$set": session.dict()}
        )
        
        # Log emotion to history
        if summary.primary_emotion:
            emotion_log = {
                "id": str(uuid.uuid4()),
                "user_id": request.user_id,
                "date": summary.date,
                "emotion": summary.primary_emotion,
                "intensity": summary.intensity or 5,
                "session_id": request.session_id
            }
            await db.emotion_history.insert_one(emotion_log)
        
        logger.info(f"Completed session: {request.session_id}")
        return summary
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete session")

@api_router.get("/emotions/history", response_model=List[EmotionHistory])
async def get_emotion_history(user_id: str = "default_user", days: int = 14):
    """Get emotion history for a user"""
    try:
        emotion_docs = await db.emotion_history.find(
            {"user_id": user_id}
        ).sort("date", -1).limit(days).to_list(days)
        
        return [EmotionHistory(**doc) for doc in emotion_docs]
    
    except Exception as e:
        logger.error(f"Error fetching emotion history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch emotion history")

@api_router.get("/sessions/recent", response_model=List[Session])
async def get_recent_sessions(user_id: str = "default_user", limit: int = 7):
    """Get recent sessions for a user"""
    try:
        session_docs = await db.sessions.find(
            {"user_id": user_id, "completed": True}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return [Session(**doc) for doc in session_docs]
    
    except Exception as e:
        logger.error(f"Error fetching recent sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
