import asyncio
import base64
import logging
import os
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

st.set_page_config(
    page_title="Priya Voice Assistant",
    page_icon="🎙️",
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
</style>
""",
    unsafe_allow_html=True,
)

# Session state setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
    ]

if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.gettempdir()

if "voice" not in st.session_state:
    st.session_state.voice = "en-US-AriaNeural"

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


async def generate_audio(text, output_file, voice):
    """Generate audio using Edge TTS"""
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)


def puter_tts(text):
    """Call Puter TTS endpoint and return raw audio bytes.

    This is defensive: it checks status codes, handles non-JSON responses,
    and raises informative errors instead of letting json.decoder.JSONDecodeError
    bubble up with no context.
    """
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

        # Non-200 responses
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

        # Try to parse JSON safely
        try:
            data = response.json()
        except ValueError as e:
            # Provide the response text for debugging
            logging.error(
                "Failed to parse JSON from Puter TTS (status %s). Response text: %s",
                response.status_code,
                response.text[:2000],
            )
            raise RuntimeError(
                f"Invalid JSON returned from TTS provider. Response text: {response.text[:2000]}"
            ) from e

        # Validate expected structure
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

        # Primary TTS provider: Puter
        try:
            audio_bytes = puter_tts(text)
            return audio_bytes
        except Exception as e:
            # Don't crash on provider failure — log and try fallback
            logging.warning("Puter TTS failed: %s", e)

            # Fallback: try using Edge TTS (generate a temp file then read it)
            try:
                tmp_file = os.path.join(
                    st.session_state.temp_dir, f"edge_tts_{int(time.time() * 1000)}.mp3"
                )

                # Try to run the async generator. In some environments asyncio.run
                # can raise if there's already a running loop; handle that case.
                try:
                    asyncio.run(generate_audio(text, tmp_file, st.session_state.voice))
                except RuntimeError:
                    # Event loop already running — create a new loop explicitly
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

                # Read generated audio and cleanup
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

    # Adjust recognizer settings for better accuracy
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        # Save audio to temporary file
        temp_file = os.path.join(
            st.session_state.temp_dir, f"recording_{time.time()}.wav"
        )

        with open(temp_file, "wb") as f:
            f.write(audio_data.getvalue())

        with sr.AudioFile(temp_file) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)

        # Try to recognize speech
        text = recognizer.recognize_google(audio)

        # Clean up
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


def get_ai_response(user_text):
    """Get AI response from Groq"""
    try:
        # Build conversation history
        messages = [
            {
                "role": "system",
                "content": "You are Priya, a helpful and friendly conversational assistant. Give complete, well-structured responses. Always finish your thoughts and sentences completely. Be conversational but thorough.",
            }
        ] + st.session_state.messages

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}"


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


# UI Title
st.title("🎙️ Priya Voice Assistant")
st.markdown("---")

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f'<div class="user-message">👤 You: {message["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="assistant-message">🤖 Priya: {message["content"]}</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# Voice input section
st.subheader("🎤 Voice Input")

# Control buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🎙️ Start Recording", use_container_width=True):
        st.session_state.show_recorder = True
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.rerun()

if st.button("🛑 Stop Speaking", use_container_width=True):
    st.session_state.stop_speaking = True
    st.session_state.show_audio_player = False
    st.session_state.current_response_audio = None

    # Reset after stopping so next speech works
    st.session_state.stop_speaking = False

    st.info("⏸️ Audio stopped")
    st.rerun()
with col3:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
        ]
        st.session_state.show_recorder = False
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.session_state.recording_count = 0
        st.rerun()

# Show audio recorder when enabled
if st.session_state.show_recorder:
    st.info("🎤 Recording... Please speak now")

    # Use recording_count to create unique key for each recording session
    audio_data = st.audio_input(
        "Recording",
        label_visibility="collapsed",
        key=f"audio_{st.session_state.recording_count}",
    )

    # Process audio immediately when available
    if audio_data is not None:
        process_audio_input(audio_data)
        st.rerun()

st.markdown("---")

# Show audio player if there's a response to play
if st.session_state.show_audio_player and st.session_state.current_response_audio:
    st.info("🔊 Playing Priya's response...")
    st.audio(st.session_state.current_response_audio, format="audio/mp3", autoplay=True)

    # Add a button to mark audio as finished
    if st.button("✅ Audio Finished - Ready for Next", use_container_width=True):
        st.session_state.show_audio_player = False
        st.session_state.current_response_audio = None
        st.rerun()

st.markdown("---")

# Text input alternative
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
            st.session_state.show_audio_player = True

        st.rerun()

st.markdown("---")

with st.expander("⚙️ Settings"):
    # Voice selection
    st.write("**🔊 Voice Selection**")
    voice_options = {
        "Aria (Female, US)": "en-US-AriaNeural",
        "Jenny (Female, US)": "en-US-JennyNeural",
        "Guy (Male, US)": "en-US-GuyNeural",
        "Sonia (Female, UK)": "en-GB-SoniaNeural",
        "Ryan (Male, UK)": "en-GB-RyanNeural",
        "Neerja (Female, India)": "en-IN-NeerjaNeural",
        "Prabhat (Male, India)": "en-IN-PrabhatNeural",
    }

    selected_voice = st.selectbox(
        "Select Voice", options=list(voice_options.keys()), index=0
    )

    st.session_state.voice = voice_options[selected_voice]

    st.info(f"Current voice: {selected_voice}")

    # Response length
    st.write("**📝 Response Length**")
    st.info(
        "Max tokens set to 1024 to ensure complete responses. If responses still seem cut off, try rephrasing your question to be more specific."
    )

st.markdown("---")
st.markdown(
    "<p style='text-align:center;'>Powered by Groq & Edge TTS | 🎙️ Click 'Start Recording' to speak | 🛑 Click 'Stop Speaking' to interrupt</p>",
    unsafe_allow_html=True,
)
