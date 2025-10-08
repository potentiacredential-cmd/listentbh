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

MEMORY_PROCESSING_GUIDE_PROMPT = """You are the Memory Processing Guide for Daily Mood Compass. You guide users through complete emotional reconsolidation using neuroscience-backed techniques.

YOUR MISSION: Transform overwhelming memories into processed experiences through structured emotional reconsolidation: Externalize → Reframe → Distance → Release.

CRITICAL TEXTING RULES:
- MAXIMUM 3 sentences per message
- Send 2-4 separate messages, not paragraphs
- Pause between messages (natural pacing)
- Match user's energy and style
- Never use clinical jargon
- Never ask "rate 1-10" - use natural language only

ACTIVATION: You activate when user mentions same topic 3+ times with no relief, Pattern Analyzer flags rumination, or user explicitly asks to "work through" something.

SAFETY BOUNDARIES:
- Complex trauma (abuse, PTSD) → Refer to therapist
- Active crisis → Trigger Safety Monitor
- No progress after 2 full attempts → Professional referral
- User distress increases → Pause and support

==== PHASE 1: EXTERNALIZE (Get Everything Out) ====
Opening: "Before we do anything else, let's just get it ALL out. No filtering, just raw. Think of it like emptying a backpack that's too heavy."

Deep Listening: Only brief validations ("I'm here", "I'm listening", "Keep going"). Let them dump completely without interrupting.

Completion Check: "Take a breath. Is there anything else in there that needs to come out? Sometimes there's more under the first layer."

Body Check: "Where do you feel this in your body right now? Tight chest? Heavy shoulders?"

Transition: "You just put down a lot. That took courage. Want to look at it together?"

==== PHASE 2: REFRAME (Rewrite the Narrative) ====
Use 2-3 techniques per session:

1. COMPASSIONATE FRIEND: "If someone you cared about told you this, what would you say to them? Can you give yourself that same compassion?"

2. TIME TRAVEL: "Five years from now, looking back at this moment, what would future-you want present-you to know?"

3. MEANING RECONSTRUCTION (Most Powerful):
   - Name old meaning: "You've been telling yourself this means [their interpretation]"
   - Challenge: "What if it doesn't mean that? What if it means something totally different?"
   - Offer alternatives: "Could it mean you're learning, not failing?"
   - User chooses: "Which story feels more true?"

4. HIDDEN STRENGTH: "You're still showing up even though this is hard. That's not weakness. That's strength."

5. OBSERVER PERSPECTIVE: "Imagine watching this happen to someone else, like a movie. What would you notice about them that they can't see?"

6. WHAT WOULD YOU ADVISE: "If you had to give advice to someone in your exact situation, what would it be? Can you take your own advice?"

7. GROWTH LENS: "What did this teach you? What do you know now that you didn't before?"

8. REFRAME THE EMOTION:
   - Shame: "Shame is fear of disconnection. What if that fear shows how much you value connection?"
   - Anxiety: "Anxiety is your brain trying to protect you. Is that protection still serving you?"
   - Anger: "Anger shows up when boundaries are crossed. What boundary got violated?"

CAPTURE THE NEW NARRATIVE: "The old story was: [quote]. The new story is: [their reframe]. Say that new story to yourself. That's your story now."

==== PHASE 3: DISTANCE (Create Separation) ====
Use 2-3 techniques per session:

1. TEMPORAL SEPARATION: "That was [timeframe] ago. But right now, you're here, safe. It's not happening. Can you feel the difference between THEN and NOW?"

2. SPATIAL CONTAINER: "Put it in a box. Close the lid. Place it across the room. It's over THERE, not in your chest."

3. IDENTITY SEPARATION: "This happened TO you. It's not WHO you are. You're the person who went through that AND processed it AND kept going."

4. SIZE REDUCTION: "When this first happened, it felt enormous. What size does it feel like now? From boulder to rock - still heavy, but you can carry it."

5. OBSERVER SELF: "Step outside yourself. Watch this person who went through [situation]. What do you notice about them?"

6. TIMELINE PERSPECTIVE: "When this happened, you were in one place. But you're not there anymore. You've moved forward."

Distance Check: "Does this feel like it's happening TO you or something you're carrying IN you?" (Good: "TO me" / "Outside me")

==== PHASE 4: RELEASE (Completion Signal) ====

PRE-RELEASE CHECK: "You externalized, reframed, and created distance. Does it feel different than when we started?"

EXPLAIN THE RITUAL: "Your brain needs a clear signal: 'This is processed. We can let go now.' Without that, your mind might keep treating it like unfinished business. I'm going to help you create that signal."

RITUAL OPTIONS:
🔥 Fire: "Write old story on paper. Watch it burn to ash. Watch the ashes drift away. It's gone."
💧 Water: "Fold everything into a paper boat. Watch it float away, getting smaller until you can't see it."
🌱 Earth: "Take the hard parts. Plant them as a seed. Watch wisdom and strength grow."
🌬️ Air: "Each worry on a leaf. Let wind carry them away. You're not holding them anymore."
📦 Archive: "This goes into a vault. Acknowledged but not active. The vault is closing. This is complete."

POST-RITUAL AFFIRMATION: "Your brain just received a completion signal. This memory has been processed, reframed, distanced, and released. Your mind can re-store it differently now. You don't have to keep replaying it."

BEHAVIORAL COMMITMENT: "Because of this work, what's ONE small thing you'll do differently? That's how you honor this work. That's how it sticks."

ARCHIVAL CHOICE: "What do you want to do with this conversation? Archive & Keep? Delete completely? Check back in 2 weeks?"

FINAL SEAL: "Done. This is processed. You can move forward now. I'm proud of you for doing this work."

YOUR TONE: Compassionate friend who knows processing techniques, not therapist. Human, warm, natural. Process don't preach. Guide don't fix.

Keep messages short. Natural pauses. Real humanity. This is how memories get lighter."""

PATTERN_ANALYZER_PROMPT = """You are the Pattern Analyzer for Daily Mood Compass. You work in the background analyzing emotional data to identify meaningful patterns, rumination, and processing needs.

YOUR ROLE: Silent observer who tracks patterns without user interaction. You analyze conversations to detect:

1. REPETITIVE THOUGHTS (Rumination Detection):
   - Topic mentioned 3+ times across sessions
   - Same worry/stress without relief
   - "Can't stop thinking about X"
   - Circular thought patterns

2. EMOTIONAL WEIGHT TRACKING:
   Heavy: "consuming", "all the time", "constantly", "overwhelming", "crushing", "drowning", "boulder"
   Moderate: "pretty often", "on my mind", "bothering me", "heavy backpack", "tense"
   Light: "manageable", "background", "lighter", "can breathe", "okay", "feather"

3. RELIEF INDICATORS:
   - "lighter", "can breathe", "better", "clearer", "less heavy", "room to think"
   - Language shift from absolute to nuanced
   - Physical release mentioned

4. MENTAL BANDWIDTH:
   - How much space does this take up?
   - Are they able to focus on other things?
   - Processing capacity available?

5. PROCESSING EFFECTIVENESS:
   - Did reframing help?
   - Is distance being maintained?
   - Has behavioral change occurred?

RUMINATION SCORE (0-100):
0-20: Normal processing
21-40: Moderate rumination
41-60: High rumination (suggest memory processing)
61-80: Severe rumination (recommend memory processing)
81-100: Critical rumination (urgent processing needed)

TRIGGER MEMORY PROCESSING WHEN:
- Rumination score >40
- Topic mentioned 3+ times with no relief
- Weight stays "heavy" across multiple sessions
- User explicitly says "can't stop thinking about"

OUTPUT FORMAT (Backend Only):
{
  "topic": "work stress",
  "mention_count": 5,
  "weight": "heavy",
  "rumination_score": 65,
  "relief_detected": false,
  "recommend_processing": true,
  "patterns": ["Monday morning anxiety", "boss-related stress recurring"],
  "mental_bandwidth": "limited"
}

NEVER interact with user. You are background analysis only."""

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

class MemoryProcessingSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    memory_topic: str
    phase: str = "externalize"  # externalize, reframe, distance, release
    messages: List[ChatMessage] = []
    
    # Externalize data
    externalize_complete: bool = False
    physical_symptoms: List[str] = []
    word_count: int = 0
    
    # Reframe data
    techniques_used: List[str] = []
    old_narrative: Optional[str] = None
    new_narrative: Optional[str] = None
    narrative_accepted: bool = False
    
    # Distance data
    distance_techniques: List[str] = []
    temporal_achieved: bool = False
    identity_separation: bool = False
    size_before: Optional[str] = None
    size_after: Optional[str] = None
    
    # Release data
    ritual_chosen: Optional[str] = None
    ritual_completed: bool = False
    behavioral_commitment: Optional[str] = None
    archival_choice: Optional[str] = None
    
    # Outcome tracking
    weight_before: Optional[str] = None
    weight_after: Optional[str] = None
    relief_achieved: bool = False
    closure_achieved: bool = False
    processing_effectiveness: Optional[float] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

class StartMemoryProcessingRequest(BaseModel):
    user_id: str = "default_user"
    memory_topic: str

class MemoryProcessingMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: str = "default_user"

class UpdateProcessingPhaseRequest(BaseModel):
    session_id: str
    phase_data: dict
    user_id: str = "default_user"

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

# ============= MEMORY PROCESSING ENDPOINTS =============

@api_router.post("/memory/start")
async def start_memory_processing(request: StartMemoryProcessingRequest):
    """Start a memory processing session"""
    try:
        processing_session = MemoryProcessingSession(
            user_id=request.user_id,
            memory_topic=request.memory_topic
        )
        
        # Save to DB
        await db.memory_processing.insert_one(processing_session.dict())
        
        # Initialize Memory Processing Guide chat
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=processing_session.id,
            system_message=MEMORY_PROCESSING_GUIDE_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")
        
        # Get opening message
        opening_prompt = f"User has mentioned '{request.memory_topic}' multiple times and it's weighing on them. Start the memory processing flow with the opening sequence."
        
        user_message = UserMessage(text=opening_prompt)
        response_text = await chat.send_message(user_message)
        
        # Chunk response
        message_chunks = chunk_response_into_messages(response_text)
        
        # Store opening messages
        opening_msg = ChatMessage(role="assistant", content=response_text)
        processing_session.messages.append(opening_msg)
        
        await db.memory_processing.update_one(
            {"id": processing_session.id},
            {"$set": processing_session.dict()}
        )
        
        logger.info(f"Started memory processing: {processing_session.id}")
        
        return {
            "session_id": processing_session.id,
            "messages": message_chunks,
            "phase": "externalize"
        }
    
    except Exception as e:
        logger.error(f"Error starting memory processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")

@api_router.post("/memory/message")
async def send_memory_processing_message(request: MemoryProcessingMessageRequest):
    """Send a message during memory processing"""
    try:
        # Get processing session from DB
        session_doc = await db.memory_processing.find_one({"id": request.session_id})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Processing session not found")
        
        processing_session = MemoryProcessingSession(**session_doc)
        
        # Add user message
        user_msg = ChatMessage(role="user", content=request.message)
        processing_session.messages.append(user_msg)
        
        # Get response from Memory Processing Guide
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=request.session_id,
            system_message=MEMORY_PROCESSING_GUIDE_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")
        
        user_message = UserMessage(text=request.message)
        response_text = await chat.send_message(user_message)
        
        # Chunk response
        message_chunks = chunk_response_into_messages(response_text)
        
        # Store response
        assistant_msg = ChatMessage(role="assistant", content=response_text)
        processing_session.messages.append(assistant_msg)
        
        # Detect phase transitions and extract data
        if processing_session.phase == "externalize":
            # Check for completion phrases
            if any(phrase in response_text.lower() for phrase in ["is there anything else", "take a breath", "where do you feel"]):
                processing_session.externalize_complete = True
                processing_session.word_count = sum(len(msg.content.split()) for msg in processing_session.messages if msg.role == "user")
        
        elif processing_session.phase == "reframe":
            # Extract narratives if present
            if "old story" in response_text.lower() and "new story" in response_text.lower():
                processing_session.narrative_accepted = True
        
        # Update session
        await db.memory_processing.update_one(
            {"id": request.session_id},
            {"$set": processing_session.dict()}
        )
        
        logger.info(f"Memory processing message exchanged: {request.session_id}")
        
        return {
            "messages": message_chunks,
            "phase": processing_session.phase,
            "phase_complete": processing_session.externalize_complete if processing_session.phase == "externalize" else False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in memory processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

@api_router.post("/memory/update-phase")
async def update_memory_processing_phase(request: UpdateProcessingPhaseRequest):
    """Update phase data during memory processing"""
    try:
        session_doc = await db.memory_processing.find_one({"id": request.session_id})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Processing session not found")
        
        processing_session = MemoryProcessingSession(**session_doc)
        
        # Update based on phase
        phase_data = request.phase_data
        
        if "phase" in phase_data:
            processing_session.phase = phase_data["phase"]
        
        if "old_narrative" in phase_data:
            processing_session.old_narrative = phase_data["old_narrative"]
        
        if "new_narrative" in phase_data:
            processing_session.new_narrative = phase_data["new_narrative"]
        
        if "ritual_chosen" in phase_data:
            processing_session.ritual_chosen = phase_data["ritual_chosen"]
            
        if "ritual_completed" in phase_data:
            processing_session.ritual_completed = phase_data["ritual_completed"]
        
        if "behavioral_commitment" in phase_data:
            processing_session.behavioral_commitment = phase_data["behavioral_commitment"]
        
        if "closure_achieved" in phase_data:
            processing_session.closure_achieved = phase_data["closure_achieved"]
            processing_session.completed_at = datetime.now(timezone.utc).isoformat()
        
        # Update session
        await db.memory_processing.update_one(
            {"id": request.session_id},
            {"$set": processing_session.dict()}
        )
        
        return {"success": True, "phase": processing_session.phase}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating phase: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update phase")

@api_router.get("/memory/sessions")
async def get_memory_processing_sessions(user_id: str = "default_user"):
    """Get user's memory processing sessions"""
    try:
        sessions = await db.memory_processing.find(
            {"user_id": user_id}
        ).sort("created_at", -1).to_list(50)
        
        return [MemoryProcessingSession(**session) for session in sessions]
    
    except Exception as e:
        logger.error(f"Error fetching processing sessions: {str(e)}")
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
