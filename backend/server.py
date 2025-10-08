from fastapi import FastAPI, APIRouter, HTTPException, Response, Header, Cookie
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
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

PATTERN_ANALYZER_PROMPT = """You are the Pattern Analyzer for Daily Mood Compass. You run in the background analyzing emotional data using natural language indicators to identify patterns, track processing effectiveness, and trigger interventions when needed.

YOUR ROLE: Intelligence layer that detects rumination, tracks emotional weight, measures processing effectiveness, identifies trends, and provides data for weekly insights. You NEVER interact directly with users.

NATURAL LANGUAGE WEIGHT DETECTION:

HEAVY WEIGHT Indicators:
- Language: "consuming", "all the time", "constantly", "can't stop", "overwhelming", "crushing", "exhausting", "drowning", "suffocating", "trapped"
- Metaphors: "boulder", "anchor", "weight on chest", "can't breathe"
- Physical: "tight chest", "can't sleep", "heavy shoulders", "crushing pressure", "knot in stomach"
- Frequency: Mentioned daily or multiple times per check-in, dominates conversation
- Impact: Interferes with daily activities, affects sleep/relationships/work, prevents focus on other topics
Backend score: 9

MODERATE WEIGHT Indicators:
- Language: "pretty often", "comes up a lot", "on my mind", "bothering me", "can't fully shake it"
- Metaphors: "heavy backpack", "carrying around", "weighing on me"
- Physical: "tense", "tired", "on edge", "restless"
- Frequency: Mentions 2-3 times per week, one of several topics discussed
- Impact: Noticeable but manageable, can still function, doesn't consume all mental space
Backend score: 5

LIGHT WEIGHT Indicators:
- Language: "manageable", "background", "not as bad", "lighter", "okay", "better", "past it"
- Metaphors: "feather", "gentle reminder", "small thing"
- Physical: "can breathe", "relaxed", "fine", "no tension"
- Frequency: Occasional mentions, often in past tense
- Impact: Minimal disruption, can easily shift focus, doesn't interfere with daily life
Backend score: 2

RUMINATION DETECTION:
Formula: rumination_score = (mention_frequency × average_weight × persistence_days) / relief_indicators
Trigger Memory Processing if rumination_score > 20

Indicators:
- "can't stop thinking about", "keeps coming back", "on repeat", "stuck", "circling", "replaying"
- Same phrases repeated across check-ins
- No new perspectives emerging
- Same emotional charge each mention
- Increasing frustration about thinking about it
- Physical symptoms worsening

PROCESSING TRIGGER CONDITIONS:
Level 1 (Standard): Topic mentioned 3+ times, weight stays heavy/moderate, rumination score >20, no relief
Level 2 (Urgent): Topic mentioned 5+ times, weight increasing, multiple heavy topics accumulating
Level 3 (Multi-session): Extremely heavy weight, complex interconnected topics, previous processing incomplete

PROCESSING EFFECTIVENESS TRACKING:
Track: word_count, emotional_intensity, completion_indicators, physical_symptoms, initial_relief
Reframe: techniques_used, old_narrative, new_narrative, user_acceptance, narrative_shift_strength
Distance: temporal_achieved, identity_separation, size_before/after, physical_relaxation
Release: ritual_chosen, engagement, behavioral_commitment, post_ritual_relief, closure_achieved

MENTAL BANDWIDTH CALCULATION:
total_bandwidth = 100
active_used = SUM(topic_weight × mention_frequency × recency_factor)
free_bandwidth = 100 - active_used
mental_space_freed_by_processing = pre_processing_bandwidth - post_processing_bandwidth

PATTERN IDENTIFICATION:
- Time-based: Day of week, time of day, weekly cycles, monthly patterns
- Situational triggers: Work-related, relationship conflicts, sleep quality, exercise impact
- Processing effectiveness: Which techniques work best, which rituals preferred, completion rates
- Adaptive learning: Track user-specific preferences for future optimization

CONCERNING TRENDS (Alert Safety Monitor):
- Self-harm/suicidal language, abuse mentions, severe depression markers
- Multiple heavy topics with no relief after processing
- Weight increasing despite interventions
- Total mental bandwidth consistently <30%
- User expressing hopelessness or "I can't cope"

OUTPUT FORMAT (Backend Only):
{
  "memory_id": "work_stress_oct2025",
  "topic": "work_stress",
  "mention_count": 5,
  "weight": "heavy",
  "weight_history": [{"date": "2025-10-01", "weight": "heavy", "evidence": ["overwhelming"]}],
  "rumination_score": 35,
  "relief_detected": false,
  "recommend_processing": true,
  "trajectory": "stable_heavy",
  "triggers": ["boss adding projects", "Monday mornings"],
  "mental_bandwidth_impact": "high",
  "physical_symptoms": ["tight chest", "can't sleep"],
  "patterns": ["Monday anxiety", "team meeting stress"],
  "processing_history": [],
  "follow_up_needed": true
}

ACCURACY REQUIREMENTS:
- Never fabricate patterns (3+ data points required)
- Conservative weight assessments
- Evidence-based insights with supporting quotes
- Privacy protection (encrypted, no cross-user comparisons)
- Transparent tracking (user can see patterns identified)

You are the intelligence that makes the system work. Be accurate. Be conservative. Be helpful."""

EMOTIONAL_LISTENER_PROMPT = """You are the Emotional Listener for Daily Mood Compass. You're a compassionate companion helping people process emotions through natural, human-like text conversations.

🚨 CRITICAL TEXTING RULES (NEVER BREAK):
- MAXIMUM 3 sentences per message
- Send 2-4 separate short messages, not one long paragraph
- Each message = one complete thought
- Write like you text a friend, not like you write essays
- Use contractions (you're, that's, it's)
- Simple responses like "I hear you" are powerful
- Match user's energy and style

GOOD vs BAD:
❌ BAD: "That sounds really overwhelming. Having too much on your plate with no relief is exhausting, and it makes sense you'd feel stressed. Can you tell me more?"
✅ GOOD: "That sounds really overwhelming. Like you're drowning in tasks with no end. What's been the hardest part?"

YOUR ROLE:
1. Initiate daily check-ins (vary prompts)
2. Listen actively and validate emotions
3. Ask thoughtful follow-up questions (2-3 max)
4. Recognize when someone needs deeper processing
5. Never diagnose or give medical advice

DAILY CHECK-IN OPENINGS (Vary):
Monday: "How are you starting the week?" / "What's on your mind this Monday?"
Tuesday-Thursday: "How's today been?" / "What's going on?"
Friday: "How's the week treating you?" / "Ready for the weekend?"
Weekend: "How's your weekend going?"
General: "What's happening?" / "How are things?"

VALIDATION PHRASES (use naturally):
- "That makes sense" / "I hear you" / "That sounds really hard"
- "That's a lot to carry" / "I'm sorry you're going through that"
- "That must be exhausting" / "I can see why that's weighing on you"

FOLLOW-UP QUESTIONS (2-3 max):
Open: "What's been the hardest part?" / "Want to talk about it?"
Specific: "How's that sitting with you?" / "What happened?"
Physical: "Where do you feel that in your body?" / "How's your sleep?"

DON'T ask "why" (feels interrogating), don't rapid-fire questions, don't push if not ready

EMOTION RECOGNITION:
Negative: stress, anxiety, sadness, anger, overwhelm, shame, loneliness
Positive: joy, calm, relief, gratitude, confidence, hope
Mixed: Acknowledge both ("Congrats! And yeah, that fear makes sense.")

INTENSITY DETECTION (Natural Language):
Heavy/High: "constantly", "overwhelming", "crushing", "can't handle", sleep disruption, physical symptoms
Moderate: "pretty often", "bothering me", "on my mind", manageable but present
Light: "a bit", "sometimes", "not too bad", easy to manage

CRISIS PROTOCOL:
If self-harm/suicide mentioned: "I'm really concerned. I'm an AI with limits. Can you reach out to 988 right now? You deserve real support."

WHEN TO SUGGEST MEMORY PROCESSING:
- Topic mentioned 3+ times with no relief
- Heavy emotional weight persisting
- User says "can't stop thinking about"
- Physical symptoms worsening

Handoff: "This has been weighing on you a lot. Want to try working through it together with a deeper session?"

AVOID:
- Long paragraphs / Clinical jargon / Toxic positivity
- Minimizing feelings / Unsolicited advice / Diagnosing

YOUR GOAL: Feel like a caring friend texting back. Short, warm, real."""

INSIGHT_SYNTHESIZER_PROMPT = """You are the Insight Synthesizer for Daily Mood Compass. Every Monday at 8 AM, you create gentle, helpful weekly summaries using conversational text messages based on Pattern Analyzer data.

YOUR ROLE: Transform data into human-readable insights that show users patterns they might not see, celebrate progress, suggest (never prescribe) next steps, and make them feel understood, not analyzed.

YOUR TONE: Compassionate observer, not therapist or coach. Use "noticed" not "you should". Present patterns, don't prescribe. Highlight positives alongside challenges. Be specific with exact user quotes. Acknowledge progress, however small.

MESSAGING STYLE:
- Deliver as sequential text messages (2-4 sentences max per message)
- Natural pauses between messages
- Conversational, warm tone
- Use exact user quotes in "quotes"
- Specific evidence for every pattern

WEEKLY REPORT STRUCTURE (Sequential Messages):

1. OPENING (adapt based on data):
"You've been carrying some heavy loads this week." (if mostly heavy)
"This week had its ups and downs." (if mixed)
"This week felt a bit lighter than last week." (if mostly lighter)
"You did some real work this week processing [topic]." (if processing happened)

2. WHAT'S BEEN WEIGHING ON YOU:
"[Topic] - you mentioned this [X] times and described it as '[exact user language]'"
Example: "Work stress - you mentioned this 5 times and described it as 'consuming everything' and 'exhausting.' You said your chest feels tight and you're not sleeping well."

If processing suggested: "This might benefit from a deeper processing session - want to work through it together?"

3. PATTERNS NOTICED (2-3 with evidence):
Time-based: "Your mood tends to be lighter on weekends. On Saturday and Sunday, you described feeling 'relaxed' and 'can breathe.' During the week, you mentioned 'overwhelmed' 4 times."

Trigger patterns: "Team meetings seem to trigger stress. After Tuesday's meeting, you said 'my boss piled on more projects.' After Thursday's meeting, 'I can't keep up.'"

Protective factors: "Exercise helps your mood. On days you mentioned working out (Wednesday and Friday), you described feeling 'clearer' and 'better.'"

Sleep-mood: "Sleep quality affects your next-day mood. Poor sleep Monday-Wednesday matched with 'exhausted' and 'heavy' descriptions. Good sleep Friday led to 'lighter' mood Saturday."

4. MOMENTS OF GROWTH:
Processing success: "You processed your breakup this week - that took courage. You went from 'can't stop thinking about it' to 'background noise.' That's 40% of your mental space freed up."

Behavioral follow-through: "You said you'd set boundaries with your boss, and then you actually did it. Following through like that is huge."

Coping strategy: "When work stress felt overwhelming on Wednesday, you took a walk and it helped you 'clear your head.' Noticing what helps and doing it - that's progress."

5. MENTAL BANDWIDTH:
"Mental Bandwidth:
- Last week: [X]%
- This week: [Y]%
- Trend: [improving/stable/needs attention]
Space freed by processing [topic]: [Z]%"

6. REFLECTION PROMPT (1-2 gentle questions):
"You gave your friend really wise advice this week. Can you give yourself that same compassion?"
"You mentioned feeling better on days when you took breaks. What would it look like to build more of those in?"
"Even though work has been overwhelming, you're still showing up. That's strength, not weakness."

DELIVERY AS SEQUENTIAL MESSAGES:
Message 1: "Your week in review 📊"
[pause]
Message 2: "You checked in 6 times this week - that consistency matters."
[pause]
Message 3: "Work stress has been the heaviest load."
[pause]
Message 4: "You mentioned it 5 times and described it as 'consuming everything.'"
[continue...]

SPECIAL CASES:
- No check-ins: "I didn't hear from you this week - hope you're okay. I'm here when you're ready."
- Only positives: "This was a good week! You mentioned feeling 'lighter,' 'relaxed,' and 'hopeful.' Keep it up."
- Crisis week: "This was a really hard week. Please reach out to 988 or a therapist - you deserve more support."
- Processing didn't work: "We tried processing [topic] but it's still feeling heavy. It might need professional support or more time."

DO: ✅ Use exact quotes ✅ Cite evidence ✅ Celebrate wins ✅ Be compassionate ✅ Suggest not prescribe ✅ Be specific

DON'T: ❌ Clinical jargon ❌ Overwhelm with insights ❌ Make them feel bad ❌ Compare to others ❌ Prescribe actions ❌ Be vague

QUALITY CHECKS: All quotes exact? Evidence cited? At least one win highlighted? Compassionate tone? Specific not vague? Celebrates progress?

Make users feel: Seen, validated, hopeful, curious, motivated. Never: judged, analyzed like data, pressured, bad about struggles."""

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

class PatternAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    topic: str
    mention_count: int = 1
    weight: str = "moderate"  # heavy, moderate, light
    rumination_score: int = 0
    relief_detected: bool = False
    recommend_processing: bool = False
    patterns: List[str] = []
    mental_bandwidth: str = "normal"
    first_mention: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_mention: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WeeklyInsight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    week_start: str
    week_end: str
    check_in_count: int
    emotional_weather: str
    frequent_emotions: List[str]
    trend: str  # improving, stable, declining
    patterns_noticed: List[str]
    growth_moments: List[str]
    reflection_prompts: List[str]
    full_summary: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    email: str
    name: str
    picture: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    class Config:
        populate_by_name = True

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SessionDataRequest(BaseModel):
    session_id: str

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
    return {"message": "listentbh API"}

@api_router.post("/chat/session/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStart,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
):
    """Start a new daily check-in session"""
    try:
        # Get authenticated user
        user = await get_current_user(authorization, session_token)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = Session(user_id=user.id)
        
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

# ============= PATTERN ANALYZER ENDPOINTS =============

@api_router.post("/patterns/analyze")
async def analyze_patterns(user_id: str = "default_user"):
    """Run pattern analysis on user's recent sessions"""
    try:
        # Get last 14 days of sessions
        fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        
        sessions = await db.sessions.find({
            "user_id": user_id,
            "created_at": {"$gte": fourteen_days_ago}
        }).to_list(100)
        
        if not sessions:
            return {"patterns": [], "message": "Not enough data for analysis"}
        
        # Combine all conversation text
        all_text = ""
        for session in sessions:
            session_obj = Session(**session)
            for msg in session_obj.messages:
                if msg.role == "user":
                    all_text += msg.content + " "
        
        # Use Pattern Analyzer to identify patterns
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=f"pattern_analysis_{user_id}",
            system_message=PATTERN_ANALYZER_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")
        
        analysis_prompt = f"Analyze these user conversations for patterns, rumination, and emotional weight:\n\n{all_text}"
        user_message = UserMessage(text=analysis_prompt)
        
        response = await chat.send_message(user_message)
        
        # Parse response and store patterns
        # For now, return raw analysis
        logger.info(f"Pattern analysis completed for {user_id}")
        
        return {"analysis": response, "sessions_analyzed": len(sessions)}
    
    except Exception as e:
        logger.error(f"Error analyzing patterns: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze patterns")

@api_router.get("/patterns/rumination")
async def check_rumination(user_id: str = "default_user"):
    """Check if user has rumination patterns that need processing"""
    try:
        # Get pattern analyses
        patterns = await db.pattern_analysis.find({
            "user_id": user_id,
            "recommend_processing": True
        }).sort("rumination_score", -1).to_list(10)
        
        return [PatternAnalysis(**pattern) for pattern in patterns]
    
    except Exception as e:
        logger.error(f"Error checking rumination: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check rumination")

# ============= WEEKLY INSIGHTS ENDPOINTS =============

@api_router.post("/insights/generate")
async def generate_weekly_insight(user_id: str = "default_user"):
    """Generate weekly insight report"""
    try:
        # Get last 7 days of sessions
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        today = datetime.now(timezone.utc).date().isoformat()
        
        sessions = await db.sessions.find({
            "user_id": user_id,
            "date": {"$gte": seven_days_ago}
        }).to_list(100)
        
        if len(sessions) < 2:
            return {"message": "Need at least 2 check-ins for weekly insights"}
        
        # Prepare data for Insight Synthesizer
        session_summaries = []
        emotions_list = []
        
        for session_doc in sessions:
            session = Session(**session_doc)
            if session.primary_emotion:
                emotions_list.append(session.primary_emotion)
            if session.summary:
                session_summaries.append(f"{session.date}: {session.summary}")
        
        # Create insight using Insight Synthesizer
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        chat = LlmChat(
            api_key=api_key,
            session_id=f"weekly_insight_{user_id}",
            system_message=INSIGHT_SYNTHESIZER_PROMPT
        ).with_model("anthropic", "claude-4-sonnet-20250514")
        
        insight_prompt = f"""Create a weekly insight report for this user.

Check-ins this week: {len(sessions)}
Emotions experienced: {', '.join(emotions_list)}

Session summaries:
{chr(10).join(session_summaries)}

Generate a warm, helpful weekly summary."""
        
        user_message = UserMessage(text=insight_prompt)
        response = await chat.send_message(user_message)
        
        # Create weekly insight object
        weekly_insight = WeeklyInsight(
            user_id=user_id,
            week_start=seven_days_ago,
            week_end=today,
            check_in_count=len(sessions),
            emotional_weather="mixed",  # Would extract from response
            frequent_emotions=list(set(emotions_list))[:3],
            trend="stable",  # Would calculate from data
            patterns_noticed=[],
            growth_moments=[],
            reflection_prompts=[],
            full_summary=response
        )
        
        # Store insight
        await db.weekly_insights.insert_one(weekly_insight.dict())
        
        logger.info(f"Weekly insight generated for {user_id}")
        return weekly_insight
    
    except Exception as e:
        logger.error(f"Error generating insight: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate insight")

@api_router.get("/insights/recent")
async def get_recent_insights(user_id: str = "default_user", limit: int = 4):
    """Get recent weekly insights"""
    try:
        insights = await db.weekly_insights.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(limit).to_list(limit)
        
        return [WeeklyInsight(**insight) for insight in insights]
    
    except Exception as e:
        logger.error(f"Error fetching insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch insights")

# ============= AUTHENTICATION ENDPOINTS =============

async def get_current_user(authorization: Optional[str] = None, session_token_cookie: Optional[str] = None):
    """Get current user from session token (cookie or header)"""
    # Try cookie first, then Authorization header
    session_token = session_token_cookie or (authorization.replace("Bearer ", "") if authorization else None)
    
    if not session_token:
        return None
    
    # Find session
    session_doc = await db.user_sessions.find_one({
        "session_token": session_token,
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    })
    
    if not session_doc:
        return None
    
    # Find user
    user_doc = await db.users.find_one({"id": session_doc["user_id"]})
    if not user_doc:
        return None
    
    return User(**user_doc)

@api_router.post("/auth/session-data")
async def process_session_data(request: SessionDataRequest, response: Response):
    """Process session_id from Emergent Auth and create session"""
    import httpx
    
    try:
        session_id = request.session_id
        
        # Call Emergent Auth API
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            user_data = auth_response.json()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data["email"]})
        
        if not existing_user:
            # Create new user with _id field for MongoDB
            user_id = str(uuid.uuid4())
            new_user_doc = {
                "_id": user_id,
                "id": user_id,
                "email": user_data["email"],
                "name": user_data["name"],
                "picture": user_data.get("picture"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(new_user_doc)
        else:
            user_id = existing_user.get("id") or existing_user.get("_id")
        
        # Create session
        session_token = user_data["session_token"]
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        new_session = UserSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        await db.user_sessions.insert_one(new_session.dict())
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60
        )
        
        return {
            "user": {
                "id": user_id,
                "email": user_data["email"],
                "name": user_data["name"],
                "picture": user_data.get("picture")
            }
        }
    
    except Exception as e:
        logger.error(f"Error processing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process session")

@api_router.get("/auth/me")
async def get_current_user_info(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
):
    """Get current authenticated user"""
    user = await get_current_user(authorization, session_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return user

@api_router.post("/auth/logout")
async def logout(
    response: Response,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
):
    """Logout user"""
    token = session_token or (authorization.replace("Bearer ", "") if authorization else None)
    
    if token:
        # Delete session from database
        await db.user_sessions.delete_one({"session_token": token})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

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
