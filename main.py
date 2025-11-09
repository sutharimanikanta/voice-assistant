# import os
# import time
# import tempfile
# import asyncio
# from dotenv import load_dotenv
# import speech_recognition as sr
# import edge_tts
# import pygame
# from groq import Groq
# import streamlit as st

# # Load API Key
# load_dotenv()
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# # Initialize pygame mixer for audio playback
# if not pygame.mixer.get_init():
#     pygame.mixer.init()

# # Page configuration
# st.set_page_config(
#     page_title="Priya Voice Assistant",
#     page_icon="🎙️",
#     layout="centered",
#     initial_sidebar_state="collapsed",
# )

# # Custom CSS for better styling
# st.markdown(
#     """
#     <style>
#     .main {
#         background-color: #2C3E50;
#     }
#     .stButton>button {
#         width: 100%;
#         height: 60px;
#         font-size: 16px;
#         font-weight: bold;
#         border-radius: 10px;
#     }
#     .user-message {
#         background-color: #3498DB;
#         color: white;
#         padding: 10px;
#         border-radius: 10px;
#         margin: 5px 0;
#     }
#     .assistant-message {
#         background-color: #2ECC71;
#         color: white;
#         padding: 10px;
#         border-radius: 10px;
#         margin: 5px 0;
#     }
#     .status-box {
#         padding: 10px;
#         border-radius: 5px;
#         text-align: center;
#         font-weight: bold;
#     }
#     </style>
# """,
#     unsafe_allow_html=True,
# )

# # Initialize session state
# if "messages" not in st.session_state:
#     st.session_state.messages = [
#         {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
#     ]
# if "is_speaking" not in st.session_state:
#     st.session_state.is_speaking = False
# if "temp_dir" not in st.session_state:
#     st.session_state.temp_dir = tempfile.gettempdir()
# if "voice" not in st.session_state:
#     st.session_state.voice = "en-US-AriaNeural"


# async def generate_audio(text, output_file, voice):
#     """Generate audio using edge-tts"""
#     communicate = edge_tts.Communicate(text, voice, rate="+10%")
#     await communicate.save(output_file)


# def speak(text):
#     """Convert text to speech using edge-tts"""
#     try:
#         st.session_state.is_speaking = True

#         # Generate audio file with edge-tts
#         audio_file = os.path.join(st.session_state.temp_dir, f"tts_{time.time()}.mp3")

#         # Run async TTS in sync context
#         asyncio.run(generate_audio(text, audio_file, st.session_state.voice))

#         # Play audio
#         pygame.mixer.music.load(audio_file)
#         pygame.mixer.music.play()

#         # Wait for audio to finish
#         while pygame.mixer.music.get_busy():
#             time.sleep(0.1)

#         # Clean up
#         time.sleep(0.1)
#         try:
#             os.remove(audio_file)
#         except:
#             pass

#     except Exception as e:
#         st.error(f"TTS Error: {e}")
#     finally:
#         st.session_state.is_speaking = False


# def stop_speaking():
#     """Stop the current speech"""
#     try:
#         pygame.mixer.music.stop()
#         st.session_state.is_speaking = False
#         st.success("Speech stopped")
#     except Exception as e:
#         st.error(f"Error stopping speech: {e}")


# def listen():
#     """Listen for speech input"""
#     recognizer = sr.Recognizer()
#     recognizer.energy_threshold = 4000
#     recognizer.dynamic_energy_threshold = True

#     try:
#         with sr.Microphone() as source:
#             status_placeholder.info("🎙️ Listening... Speak now!")
#             recognizer.adjust_for_ambient_noise(source, duration=0.2)
#             audio = recognizer.listen(source, timeout=4, phrase_time_limit=8)

#         status_placeholder.warning("Processing...")
#         text = recognizer.recognize_google(audio)
#         return text

#     except sr.WaitTimeoutError:
#         status_placeholder.error("No speech detected")
#         return ""
#     except sr.UnknownValueError:
#         status_placeholder.error("Could not understand audio")
#         return ""
#     except Exception as e:
#         status_placeholder.error(f"Error: {str(e)}")
#         return ""


# def get_ai_response(user_text):
#     """Get AI response from Groq"""
#     try:
#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are Priya, a helpful and concise voice assistant. Keep responses brief and conversational.",
#                 },
#                 {"role": "user", "content": user_text},
#             ],
#             max_tokens=150,
#             temperature=0.7,
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         return f"Error getting response: {str(e)}"


# # Main UI
# st.title("🎙️ Priya Voice Assistant")

# # Status placeholder
# status_placeholder = st.empty()
# status_placeholder.info("Ready")

# # Chat display
# chat_container = st.container()
# with chat_container:
#     for message in st.session_state.messages:
#         if message["role"] == "user":
#             st.markdown(
#                 f'<div class="user-message">👤 You: {message["content"]}</div>',
#                 unsafe_allow_html=True,
#             )
#         else:
#             st.markdown(
#                 f'<div class="assistant-message">🤖 Priya: {message["content"]}</div>',
#                 unsafe_allow_html=True,
#             )

# st.markdown("---")

# # Control buttons
# col1, col2, col3 = st.columns(3)

# with col1:
#     if st.button(
#         "🎤 Press to Talk", type="primary", disabled=st.session_state.is_speaking
#     ):
#         # Listen for input
#         user_text = listen()

#         if user_text:
#             # Add user message
#             st.session_state.messages.append({"role": "user", "content": user_text})

#             # Check for exit commands
#             if "stop" in user_text.lower() or "bye" in user_text.lower():
#                 response_text = "Goodbye! Have a great day!"
#                 st.session_state.messages.append(
#                     {"role": "assistant", "content": response_text}
#                 )
#                 speak(response_text)
#             else:
#                 # Get AI response
#                 status_placeholder.info("🤔 Thinking...")
#                 reply = get_ai_response(user_text)

#                 # Add AI response
#                 st.session_state.messages.append(
#                     {"role": "assistant", "content": reply}
#                 )

#                 # Speak the response
#                 status_placeholder.info("🔊 Speaking...")
#                 speak(reply)
#                 status_placeholder.success("Ready")

#             # Rerun to update chat display
#             st.rerun()

# with col2:
#     if st.button("⏹️ Stop Speaking", type="secondary"):
#         stop_speaking()

# with col3:
#     if st.button("🗑️ Clear Chat", type="secondary"):
#         st.session_state.messages = [
#             {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
#         ]
#         status_placeholder.info("Chat cleared")
#         st.rerun()

# # Footer
# st.markdown("---")
# st.markdown(
#     "<p style='text-align: center; color: #95A5A6;'>Powered by Groq & Edge TTS</p>",
#     unsafe_allow_html=True,
# )
import os
import time
import tempfile
import asyncio
from dotenv import load_dotenv
import speech_recognition as sr
import edge_tts
import pygame
from groq import Groq
import streamlit as st

# Load API Key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize pygame mixer for audio playback
if not pygame.mixer.get_init():
    pygame.mixer.init()

# Page configuration
st.set_page_config(
    page_title="Priya Voice Assistant",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown(
    """
    <style>
    .main { background-color: #2C3E50; }
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 10px;
    }
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
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
    ]
if "is_speaking" not in st.session_state:
    st.session_state.is_speaking = False
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.gettempdir()
if "voice" not in st.session_state:
    st.session_state.voice = "en-US-AriaNeural"


async def generate_audio(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)


def speak(text):
    try:
        st.session_state.is_speaking = True
        audio_file = os.path.join(st.session_state.temp_dir, f"tts_{time.time()}.mp3")
        asyncio.run(generate_audio(text, audio_file, st.session_state.voice))
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        try:
            os.remove(audio_file)
        except:
            pass
    except Exception as e:
        st.error(f"TTS Error: {e}")
    finally:
        st.session_state.is_speaking = False


# def stop_speaking():
# try:
# pygame.mixer.music.stop()
# st.session_state.is_speaking = False
# except Exception as e:
# st.error(f"Error stopping speech: {e}")
def stop_speaking():
    try:
        pygame.mixer.music.stop()
        st.session_state.is_speaking = False
        st.rerun()  # <---- forces UI refresh immediately
    except Exception as e:
        st.error(f"Error stopping speech: {e}")


def listen():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as source:
            status_placeholder.info("🎙️ Listening... Speak now!")
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio = recognizer.listen(source, timeout=4, phrase_time_limit=8)
        status_placeholder.warning("Processing...")
        return recognizer.recognize_google(audio)
    except:
        return ""


def get_ai_response(user_text):
    try:
        messages = (
            [
                {
                    "role": "system",
                    "content": "You are Priya, a helpful and concise voice assistant. Keep responses brief and conversational.",
                }
            ]
            + st.session_state.messages
            + [{"role": "user", "content": user_text}]
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error getting response: {str(e)}"


# UI Title
st.title("🎙️ Priya Voice Assistant")

status_placeholder = st.empty()
status_placeholder.info("Ready")

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

# Buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🎤 Press to Talk", disabled=st.session_state.is_speaking):
        user_text = listen()
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            if "stop" in user_text.lower() or "bye" in user_text.lower():
                reply = "Goodbye! Take care."
            else:
                status_placeholder.info("🤔 Thinking...")
                reply = get_ai_response(user_text)

            st.session_state.messages.append({"role": "assistant", "content": reply})
            status_placeholder.info("🔊 Speaking...")
            speak(reply)
            st.rerun()

with col2:
    if st.button("⏹️ Stop Speaking"):
        stop_speaking()

with col3:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello, I am Priya. How can I help you?"}
        ]
        st.rerun()

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #95A5A6;'>Powered by Groq & Edge TTS</p>",
    unsafe_allow_html=True,
)
