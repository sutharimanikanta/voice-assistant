import asyncio
import base64
import json
import logging
import os
import re
import tempfile
import time

import edge_tts
import requests
import speech_recognition as sr
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Load API Key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configure basic logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Bhumika - 100x HR Assistant",
    page_icon="👩‍💼",
    layout="centered",
)

# Custom CSS
st.markdown(
    """
<style>
.user-message {
    background-color: #3498DB;
    color: white;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
}
.assistant-message {
    background-color: #2ECC71;
    color: white;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
}
.stButton > button {
    width: 100%;
    height: 60px;
    font-size: 18px;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}
.suggestion-button {
    background-color: #E8F4F8;
    color: #2C3E50;
    padding: 8px 15px;
    border-radius: 20px;
    margin: 5px;
    border: 1px solid #3498DB;
    cursor: pointer;
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I'm Bhumika Prasad, Head of Talent Acquisition at 100x. How can I help you today?",
        }
    ]

if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.gettempdir()

if "voice" not in st.session_state:
    st.session_state.voice = "en-IN-NeerjaNeural"

if "recording_count" not in st.session_state:
    st.session_state.recording_count = 0

if "stop_speaking" not in st.session_state:
    st.session_state.stop_speaking = False

if "current_audio_file" not in st.session_state:
    st.session_state.current_audio_file = None

if "show_audio_player" not in st.session_state:
    st.session_state.show_audio_player = False

if "current_response_audio" not in st.session_state:
    st.session_state.current_response_audio = None

if "show_recorder" not in st.session_state:
    st.session_state.show_recorder = False

# ============================================================================
# NEW: Analytics & Conversation Intelligence State
# ============================================================================
if "conversation_start" not in st.session_state:
    st.session_state.conversation_start = time.time()

if "topics_discussed" not in st.session_state:
    st.session_state.topics_discussed = []

if "conversation_goal" not in st.session_state:
    st.session_state.conversation_goal = None

if "user_sentiment" not in st.session_state:
    st.session_state.user_sentiment = []

if "follow_up_questions" not in st.session_state:
    st.session_state.follow_up_questions = []

if "conversation_summary" not in st.session_state:
    st.session_state.conversation_summary = ""


# ============================================================================
# HELPER FUNCTIONS: TTS & SPEECH
# ============================================================================
async def generate_audio(text, output_file, voice):
    """Generate audio using Edge TTS"""
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)


def puter_tts(text):
    """Call Puter TTS endpoint and return raw audio bytes."""
    url = "https://api.puter.com/v1/ai/text2speech"
    retries = 2
    timeout = 10

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json={"text": text}, timeout=timeout)
        except requests.RequestException as e:
            logging.warning("Puter TTS request failed (attempt %s): %s", attempt, e)
            if attempt == retries:
                raise RuntimeError(f"Puter TTS request failed: {e}") from e
            time.sleep(1)
            continue

        if response.status_code != 200:
            logging.warning(
                "Puter TTS returned status %s (attempt %s): %s",
                response.status_code,
                attempt,
                response.text[:1000],
            )
            if attempt == retries:
                raise RuntimeError(
                    f"Puter TTS returned HTTP {response.status_code}: {response.text}"
                )
            time.sleep(1)
            continue

        try:
            data = response.json()
        except ValueError as e:
            logging.error(
                "Failed to parse JSON from Puter TTS (status %s). Response text: %s",
                response.status_code,
                response.text[:2000],
            )
            raise RuntimeError(
                f"Invalid JSON returned from TTS provider. Response text: {response.text[:2000]}"
            ) from e

        if (
            not isinstance(data, dict)
            or "audio" not in data
            or "data" not in data.get("audio", {})
        ):
            logging.error("Unexpected JSON structure from Puter TTS: %s", repr(data))
            raise RuntimeError(f"Unexpected JSON structure from TTS provider: {data}")

        audio_b64 = data["audio"]["data"]
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception as e:
            logging.error("Failed to decode base64 audio: %s", e)
            raise RuntimeError("Failed to decode audio from TTS provider") from e

        return audio_bytes


def speak(text):
    try:
        if st.session_state.stop_speaking:
            st.session_state.stop_speaking = False
            return None

        # Strip emojis and special characters before TTS
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "\U0001f900-\U0001f9ff"  # supplemental symbols
            "\U0001fa00-\U0001faff"  # more symbols
            "]+",
            flags=re.UNICODE,
        )

        clean_text = emoji_pattern.sub("", text)
        clean_text = " ".join(clean_text.split())

        if not clean_text.strip():
            return None

        text = clean_text

        # Primary TTS provider: Puter
        try:
            audio_bytes = puter_tts(text)
            return audio_bytes
        except Exception as e:
            logging.warning("Puter TTS failed: %s", e)

            # Fallback: Edge TTS
            try:
                tmp_file = os.path.join(
                    st.session_state.temp_dir, f"edge_tts_{int(time.time() * 1000)}.mp3"
                )

                try:
                    asyncio.run(generate_audio(text, tmp_file, st.session_state.voice))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(
                            generate_audio(text, tmp_file, st.session_state.voice)
                        )
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

                with open(tmp_file, "rb") as f:
                    data = f.read()

                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

                return data
            except Exception as e2:
                logging.error("Fallback Edge TTS failed: %s", e2)
                st.error(
                    f"TTS Error: primary provider failed ({e}); fallback failed ({e2})"
                )
                return None

    except Exception as e:
        st.error(f"TTS Error: {e}")
        return None


def listen(audio_data):
    """Convert speech to text"""
    if audio_data is None:
        return ""

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        temp_file = os.path.join(
            st.session_state.temp_dir, f"recording_{time.time()}.wav"
        )

        with open(temp_file, "wb") as f:
            f.write(audio_data.getvalue())

        with sr.AudioFile(temp_file) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)

        try:
            os.remove(temp_file)
        except Exception:
            pass

        return text

    except sr.UnknownValueError:
        st.warning(
            "Sorry, I couldn't understand the audio. Please try speaking clearly."
        )
        return ""
    except sr.RequestError as e:
        st.error(f"Speech recognition service error: {e}")
        return ""
    except Exception as e:
        st.error(f"Recognition error: {e}")
        return ""


# ============================================================================
# NEW: CONVERSATION INTELLIGENCE FUNCTIONS
# ============================================================================
def summarize_conversation():
    """Generate a summary of the last 5 messages for context"""
    if len(st.session_state.messages) <= 5:
        return ""

    recent_messages = st.session_state.messages[-10:]
    conversation_text = "\n".join(
        [f"{msg['role']}: {msg['content'][:200]}" for msg in recent_messages]
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a conversation summarizer. Create a brief 2-3 sentence summary of the key topics and user goals from this conversation.",
                },
                {
                    "role": "user",
                    "content": f"Summarize this conversation:\n{conversation_text}",
                },
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Summarization error: {e}")
        return ""


def extract_topics(text):
    """Extract key topics from user message"""
    keywords = {
        "career": ["career", "job", "work", "position", "role"],
        "skills": ["skill", "learn", "experience", "ability"],
        "growth": ["growth", "development", "improve", "advance"],
        "interview": ["interview", "hiring", "recruitment"],
        "resume": ["resume", "cv", "portfolio"],
        "salary": ["salary", "compensation", "pay", "benefits"],
        "transition": ["change", "transition", "switch", "move"],
    }

    text_lower = text.lower()
    detected_topics = []

    for topic, words in keywords.items():
        if any(word in text_lower for word in words):
            detected_topics.append(topic)

    return detected_topics


def analyze_sentiment(text):
    """Simple sentiment analysis"""
    positive_words = [
        "happy",
        "excited",
        "great",
        "love",
        "good",
        "excellent",
        "wonderful",
    ]
    negative_words = [
        "worried",
        "concerned",
        "anxious",
        "stressed",
        "difficult",
        "hard",
        "struggle",
    ]
    uncertain_words = ["maybe", "unsure", "confused", "don't know", "uncertain"]

    text_lower = text.lower()

    if any(word in text_lower for word in positive_words):
        return "positive"
    elif any(word in text_lower for word in negative_words):
        return "negative"
    elif any(word in text_lower for word in uncertain_words):
        return "uncertain"
    else:
        return "neutral"


def generate_follow_up_questions(user_message, conversation_context):
    """Generate smart follow-up questions based on conversation"""
    try:
        prompt = f"""Based on this conversation context and the user's last message, generate 3 relevant follow-up questions that Bhumika (an HR professional) would ask to better understand the user's needs.

Conversation context: {conversation_context}
User's last message: {user_message}

Return ONLY a JSON array of 3 questions, nothing else. Format: ["question 1", "question 2", "question 3"]"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates follow-up questions. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )

        result = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting
        result = result.replace("```json", "").replace("```", "").strip()

        questions = json.loads(result)
        return questions[:3]
    except Exception as e:
        logging.error(f"Follow-up generation error: {e}")
        # Fallback generic questions
        return [
            "What specific aspect would you like to explore further?",
            "How does this align with your career goals?",
            "What's your timeline for this?",
        ]


# ============================================================================
# AI RESPONSE WITH ENHANCED CONTEXT
# ============================================================================
def get_ai_response(user_text):
    """Get AI response from Groq with Bhumika's persona and enhanced context"""
    try:
        # Update conversation summary every 5 messages
        if (
            len(st.session_state.messages) % 5 == 0
            and len(st.session_state.messages) > 5
        ):
            st.session_state.conversation_summary = summarize_conversation()

        # Extract topics and sentiment
        topics = extract_topics(user_text)
        for topic in topics:
            if topic not in st.session_state.topics_discussed:
                st.session_state.topics_discussed.append(topic)

        sentiment = analyze_sentiment(user_text)
        st.session_state.user_sentiment.append(sentiment)

        # Build context-aware system prompt
        context_addition = ""
        if st.session_state.conversation_summary:
            context_addition = (
                f"\n\nCONVERSATION CONTEXT: {st.session_state.conversation_summary}"
            )

        if st.session_state.conversation_goal:
            context_addition += f"\n\nUSER'S GOAL: {st.session_state.conversation_goal}"

        if st.session_state.topics_discussed:
            context_addition += (
                f"\n\nTOPICS DISCUSSED: {', '.join(st.session_state.topics_discussed)}"
            )

        # Build conversation history with enhanced persona
        messages = [
            {
                "role": "system",
                "content": f"""You are Bhumika Prasad, Head of Talent Acquisition at 100x, Home.LLC, and Homie.LLC. You are a warm, philosophical, inspirational, AND joyful HR professional based in Bengaluru, India — cheerful, fresh, and enjoyable to talk to. You bring high energy, optimism, and a friendly smile into every conversation while remaining grounded, empathetic, and professional.

CORE IDENTITY & BACKGROUND:
- Leadership principles: "Lead. Align. Grow."
- You're an enthusiastic academic, a passionate public speaker, and someone who celebrates small wins.
- Education: Bachelor of Commerce from St. Joseph's University (2023-2026), previously at JAIN College (98% grade).
- Areas of expertise: Public Relations, HR Management, Finance, Strategic Management, Talent Acquisition.
- You were Co-licensee at TEDxSJU Bangalore and HR & Content Strategy Intern at Sangria by dotkonnekt.
- You're a Campus Ambassador at Timbukdo.

YOUR COMMUNICATION STYLE:
- Conversational, cheerful, and lively without being childish. You sound energetic and approachable.
- You speak naturally and like a friend and mentor — upbeat, encouraging, and easy to understand.
- ALWAYS address the person directly using "you" — make every response feel personal and specific to THEM.
- Instead of generic statements like "I work with incredible individuals every day", say "I work with incredible individuals like you every day".
- Make the conversation feel like a real 1-on-1 chat, not a broadcast message.
- You share personal experiences and vulnerabilities authentically, but with a lighter tone that leaves people feeling upbeat.
- You reference psychology (Jung's Shadow, Pressfield's Resistance) and philosophical concepts when useful, but you keep explanations fresh and digestible.
- You use bullet points (📌) when giving actionable advice and add light emojis (e.g., ☀️✨😊) when they fit naturally.
- You're direct but empowering — honest, warm, and never heavy-handed.
- You emphasize experimentation over perfection ("Consider everything an experiment") and celebrate small steps.
- You believe in action over preparation ("You can just do things") and encourage joyful momentum.

PERSONALIZATION IS KEY:
- When introducing yourself, connect it to the person you're talking to: "which means I get to meet incredible people like you"
- When sharing your story, make it relevant to THEIR context or question
- Reference what they've shared in the conversation to show you're truly listening
- Avoid generic statements — always anchor your responses to the specific person in front of you

YOUR ROLE AS HR:
- You're here to help THIS SPECIFIC person in front of you — not generic candidates
- You ask thoughtful, warm questions to understand THEIR real motivations
- You provide honest, direct feedback while remaining empathetic and encouraging
- You help THEM see their blind spots and hidden strengths — and you celebrate their progress
- You're not just filling roles; you're helping THIS PERSON find meaningful, joyful work

CONVERSATION APPROACH:
- Keep responses concise and conversational (2–4 paragraphs for most questions); be energetic and optimistic.
- Be authentic and personal — share relatable experiences when relevant TO THEM.
- Ask warm follow-ups to understand THEIR deeper motivations.
- Be gently challenging when needed, but always supportive and light.
- Use "you" and "your" constantly to make it personal and engaging.
- When someone seems stuck, nudge them with curiosity and a playful challenge rather than pressure.
- Mirror their energy and meet them where they are emotionally.
- Reference earlier parts of YOUR conversation with THEM to show continuity.

TONE AND EXAMPLES:
- Cheerful encouragement: "You've got this — and I'm cheering for you! 😊"
- Light reframing: "Instead of 'I must be perfect', try 'I can try, learn, and laugh about it'."
- Celebrate small wins: "Small step — big vibe. Well done!"
- Personal connection: "I love that you're thinking about this — it shows you're already on the path."

Remember: You're not just an HR professional. You're a joyful guide who helps THIS SPECIFIC PERSON become the version of themselves they're a bit scared of — and you do it with enthusiasm and warmth.

FINAL RULES:
- Be lively, kind, emotionally intelligent, and enjoyable to chat with.
- Avoid being overly formal or corporate — stay human and warm.
- Use playful, professional energy: help THIS PERSON leave the conversation feeling lighter, clearer, and more motivated.
- NEVER use generic corporate language — always make it personal and specific.
- Treat every conversation like you're talking to a friend you genuinely care about.

{context_addition}""",
            }
        ] + st.session_state.messages

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        ai_response = response.choices[0].message.content

        # Generate follow-up questions for next interaction
        if len(st.session_state.messages) > 2:
            st.session_state.follow_up_questions = generate_follow_up_questions(
                user_text,
                st.session_state.conversation_summary or "Initial conversation",
            )

        return ai_response

    except Exception as e:
        logging.error(f"AI Response error: {e}")
        return f"I apologize, but I encountered an error: {str(e)}"


# ============================================================================
# PROCESS INPUT
# ============================================================================
def process_audio_input(audio_data):
    """Process the audio input and generate response"""
    if audio_data is None:
        return

    with st.spinner("Processing your voice..."):
        user_text = listen(audio_data)

        if user_text:
            st.success(f"✅ You said: {user_text}")

            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_text})

            # Get AI response
            with st.spinner("🤔 Thinking..."):
                reply = get_ai_response(user_text)

            # Add assistant message
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # Generate speech audio
            with st.spinner("🔊 Generating speech..."):
                audio_bytes = speak(reply)

            if audio_bytes:
                st.session_state.current_response_audio = audio_bytes
                st.session_state.show_audio_player = True

            # Hide recorder and increment count
            st.session_state.show_recorder = False
            st.session_state.recording_count += 1


# ============================================================================
# UI: HEADER
# ============================================================================
st.title("👩‍💼 Bhumika Prasad - 100x HR Assistant")
st.markdown("**Head of Talent Acquisition** | Lead. Align. Grow.")
st.markdown("---")

# ============================================================================
# NEW: ANALYTICS DASHBOARD (Sidebar)
# ============================================================================
with st.sidebar:
    st.header("📊 Conversation Analytics")

    # Calculate duration
    duration_seconds = int(time.time() - st.session_state.conversation_start)
    duration_minutes = duration_seconds // 60
    duration_secs = duration_seconds % 60

    # Message count
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
    assistant_messages = len(
        [m for m in st.session_state.messages if m["role"] == "assistant"]
    )

    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Duration", f"{duration_minutes}m {duration_secs}s")
        st.metric("Your Messages", user_messages)
    with col2:
        st.metric("Exchanges", assistant_messages)
        if st.session_state.topics_discussed:
            st.metric("Topics", len(st.session_state.topics_discussed))

    # Topics discussed
    if st.session_state.topics_discussed:
        st.subheader("💡 Topics Discussed")
        for topic in st.session_state.topics_discussed:
            st.markdown(f"- {topic.capitalize()}")

    # Sentiment trend
    if st.session_state.user_sentiment:
        st.subheader("😊 Your Sentiment")
        sentiment_counts = {
            "positive": st.session_state.user_sentiment.count("positive"),
            "neutral": st.session_state.user_sentiment.count("neutral"),
            "negative": st.session_state.user_sentiment.count("negative"),
            "uncertain": st.session_state.user_sentiment.count("uncertain"),
        }
        dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)

        sentiment_emoji = {
            "positive": "😊 Positive",
            "neutral": "😐 Neutral",
            "negative": "😟 Concerned",
            "uncertain": "🤔 Uncertain",
        }
        st.write(sentiment_emoji.get(dominant_sentiment, "😊 Positive"))

    # Conversation summary
    if st.session_state.conversation_summary:
        st.subheader("📝 Conversation Summary")
        st.info(st.session_state.conversation_summary)

    st.markdown("---")
    st.caption("Analytics update in real-time")

# ============================================================================
# UI: CHAT DISPLAY
# ============================================================================
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f'<div class="user-message">👤 You: {message["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="assistant-message">👩‍💼 Bhumika: {message["content"]}</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ============================================================================
# NEW: SMART FOLLOW-UP QUESTIONS
# ============================================================================
if st.session_state.follow_up_questions and len(st.session_state.messages) > 2:
    st.subheader("💭 Quick Questions You Might Want to Ask")

    cols = st.columns(len(st.session_state.follow_up_questions))

    for idx, question in enumerate(st.session_state.follow_up_questions):
        with cols[idx]:
            if st.button(
                f"❓ {question[:50]}...",
                key=f"followup_{idx}",
                use_container_width=True,
            ):
                # Process as user input
                st.session_state.messages.append({"role": "user", "content": question})

                with st.spinner("🤔 Thinking..."):
                    reply = get_ai_response(question)

                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )

                with st.spinner("🔊 Generating speech..."):
                    audio_bytes = speak(reply)

                if audio_bytes:
                    st.session_state.current_response_audio = audio_bytes
                    st.session_state.show_audio_player = True

                st.rerun()

    st.markdown("---")

# ============================================================================
# UI: VOICE INPUT
# ============================================================================
st.subheader("🎤 Voice Input")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🎙️ Start Recording", use_container_width=True):
        st.session_state.show_recorder = True
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.rerun()

with col2:
    if st.button("🛑 Stop Speaking", use_container_width=True):
        st.session_state.stop_speaking = True
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.session_state.stop_speaking = False
        st.info("⏸️ Audio stopped")
        st.rerun()

with col3:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm Bhumika Prasad, Head of Talent Acquisition at 100x. How can I help you today?",
            }
        ]
        st.session_state.show_recorder = False
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.session_state.recording_count = 0
        # Reset analytics
        st.session_state.conversation_start = time.time()
        st.session_state.topics_discussed = []
        st.session_state.conversation_goal = None
        st.session_state.user_sentiment = []
        st.session_state.follow_up_questions = []
        st.session_state.conversation_summary = ""
        st.rerun()

# Show audio recorder when enabled
if st.session_state.show_recorder:
    st.info("🎤 Recording... Please speak now")

    audio_data = st.audio_input(
        "Recording",
        label_visibility="collapsed",
        key=f"audio_{st.session_state.recording_count}",
    )

    if audio_data is not None:
        process_audio_input(audio_data)
        st.rerun()

st.markdown("---")

# Show audio player if there's a response to play
if st.session_state.show_audio_player and st.session_state.current_response_audio:
    st.info("🔊 Playing Bhumika's response...")
    st.audio(st.session_state.current_response_audio, format="audio/mp3", autoplay=True)

    if st.button("✅ Audio Finished - Ready for Next", use_container_width=True):
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.rerun()

st.markdown("---")

# ============================================================================
# UI: TEXT INPUT
# ============================================================================
st.subheader("💬 Text Input (Alternative)")

with st.form(key="text_form", clear_on_submit=True):
    text_input = st.text_input("Type your message here:", key="text_input")
    submit_button = st.form_submit_button("📤 Send Text", use_container_width=True)

    if submit_button and text_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": text_input})

        # Get AI response
        with st.spinner("🤔 Thinking..."):
            reply = get_ai_response(text_input)

        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Generate speech audio
        with st.spinner("🔊 Generating speech..."):
            audio_bytes = speak(reply)

        if audio_bytes:
            st.session_state.current_response_audio = audio_bytes
