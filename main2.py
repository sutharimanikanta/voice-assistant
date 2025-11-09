import os
import time
import tempfile
import asyncio
from dotenv import load_dotenv
import gradio as gr
import speech_recognition as sr
import edge_tts
from groq import Groq

# Load API Key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration
TEMP_DIR = tempfile.gettempdir()
VOICE = "en-US-AriaNeural"

# Chat history
chat_history = []


async def generate_audio(text, output_file, voice):
    """Generate audio using edge-tts"""
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)


def text_to_speech(text, voice=VOICE):
    """Convert text to speech and return audio file path"""
    try:
        audio_file = os.path.join(TEMP_DIR, f"tts_{time.time()}.mp3")
        asyncio.run(generate_audio(text, audio_file, voice))
        return audio_file
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


def transcribe_audio(audio_path):
    """Transcribe audio file to text using Google Speech Recognition"""
    if audio_path is None:
        return None

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        return text

    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None


def get_ai_response(user_text):
    """Get AI response from Groq"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are Priya, a helpful and concise voice assistant. Keep responses brief and conversational.",
                },
                {"role": "user", "content": user_text},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


def process_audio(audio, voice_choice, history):
    """Process audio input and return response"""
    if audio is None:
        return history, None, "Please record some audio first."

    # Transcribe audio
    status = "🎙️ Transcribing your voice..."
    user_text = transcribe_audio(audio)

    if not user_text:
        return history, None, "❌ Could not understand the audio. Please try again."

    # Add user message to history
    history.append({"role": "user", "content": f"👤 You: {user_text}"})

    # Check for exit commands
    if "stop" in user_text.lower() or "bye" in user_text.lower():
        response_text = "Goodbye! Have a great day!"
    else:
        # Get AI response
        status = "🤔 Thinking..."
        response_text = get_ai_response(user_text)

    # Add AI response to history
    history.append({"role": "assistant", "content": f"🤖 Priya: {response_text}"})

    # Generate speech
    status = "🔊 Generating speech..."
    audio_response = text_to_speech(response_text, voice_choice)

    return history, audio_response, "✅ Response ready! Playing audio..."


def process_text(text, voice_choice, history):
    """Process text input and return response"""
    if not text or text.strip() == "":
        return history, None, "Please enter some text first."

    # Add user message to history
    history.append({"role": "user", "content": f"👤 You: {text}"})

    # Check for exit commands
    if "stop" in text.lower() or "bye" in text.lower():
        response_text = "Goodbye! Have a great day!"
    else:
        # Get AI response
        response_text = get_ai_response(text)

    # Add AI response to history
    history.append({"role": "assistant", "content": f"🤖 Priya: {response_text}"})

    # Generate speech
    audio_response = text_to_speech(response_text, voice_choice)

    return history, audio_response, "✅ Response ready!"


def clear_chat():
    """Clear chat history"""
    return [], None, "Chat cleared!"


def format_chat_history(history):
    """Format chat history for display"""
    formatted = ""
    for speaker, message in history:
        formatted += f"**{speaker}:**\n{message}\n\n"
    return formatted


# Custom CSS
custom_css = """
.gradio-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.chat-message {
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
}
"""

# Create Gradio Interface
with gr.Blocks(
    css=custom_css, theme=gr.themes.Soft(), title="Priya Voice Assistant"
) as demo:
    gr.Markdown(
        """
        # 🎙️ Priya - Voice Assistant
        ### Speak or type to interact with your AI assistant
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            # Chat display
            chatbot = gr.Chatbot(
                label="💬 Conversation",
                height=400,
                show_label=True,
                value=[("🤖 Priya", "Hello, I am Priya. How can I help you?")],
            )

            # Status message
            status = gr.Textbox(
                label="Status",
                value="Ready to assist you!",
                interactive=False,
                show_label=False,
            )

        with gr.Column(scale=1):
            # Voice settings
            voice_choice = gr.Dropdown(
                choices=[
                    "en-US-AriaNeural",
                    "en-US-JennyNeural",
                    "en-US-GuyNeural",
                    "en-GB-SoniaNeural",
                    "en-GB-RyanNeural",
                ],
                value="en-US-AriaNeural",
                label="🔊 Select Voice",
                interactive=True,
            )

            # Audio output
            audio_output = gr.Audio(
                label="🔊 AI Response Audio", type="filepath", autoplay=True
            )

            # Statistics
            gr.Markdown("### 📊 Quick Stats")
            gr.Markdown("View your conversation statistics above in the chat!")

    gr.Markdown("---")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🎤 Voice Input")
            audio_input = gr.Audio(
                label="Record your voice", type="filepath", sources=["microphone"]
            )
            voice_btn = gr.Button("🎤 Send Voice Message", variant="primary", size="lg")

        with gr.Column():
            gr.Markdown("### ⌨️ Text Input")
            text_input = gr.Textbox(
                label="Type your message",
                placeholder="Type here or use voice...",
                lines=3,
            )
            text_btn = gr.Button("📤 Send Text Message", variant="primary", size="lg")

    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

    # Event handlers
    voice_btn.click(
        fn=process_audio,
        inputs=[audio_input, voice_choice, chatbot],
        outputs=[chatbot, audio_output, status],
    )

    text_btn.click(
        fn=process_text,
        inputs=[text_input, voice_choice, chatbot],
        outputs=[chatbot, audio_output, status],
    ).then(fn=lambda: "", outputs=[text_input])

    text_input.submit(
        fn=process_text,
        inputs=[text_input, voice_choice, chatbot],
        outputs=[chatbot, audio_output, status],
    ).then(fn=lambda: "", outputs=[text_input])

    clear_btn.click(fn=clear_chat, outputs=[chatbot, audio_output, status])

    gr.Markdown(
        """
        ---
        ### ℹ️ Instructions
        1. **Voice Mode:** Click the microphone to record, then click "Send Voice Message"
        2. **Text Mode:** Type your message and press Enter or click "Send Text Message"
        3. **Voice Settings:** Choose your preferred voice from the dropdown
        4. The AI will respond with both text and voice

        💡 **Tip:** Allow microphone access when prompted by your browser!

        ---
        <p style='text-align: center; color: #666;'>Powered by Groq API & Edge TTS | Built with Gradio</p>
        """
    )

# Launch the app
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
