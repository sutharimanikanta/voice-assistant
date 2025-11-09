# import os
# import tempfile
# import speech_recognition as sr
# import edge_tts
# from dotenv import load_dotenv
# from groq import Groq
# import gradio as gr

# load_dotenv()
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# recognizer = sr.Recognizer()
# chat_history = []
# voice = "en-US-JennyNeural"


# def transcribe(audio_file):
#     try:
#         with sr.AudioFile(audio_file) as source:
#             audio = recognizer.record(source)
#         return recognizer.recognize_google(audio)
#     except:
#         return ""


# async def text_to_speech(text):
#     tts = edge_tts.Communicate(text, voice, rate="+20%")
#     output_path = os.path.join(tempfile.gettempdir(), "reply.mp3")
#     await tts.save(output_path)
#     return output_path


# def chat_reply(user_text):
#     chat_history.append({"role": "user", "content": user_text})

#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {
#                 "role": "system",
#                 "content": "You are Priya. Be friendly, short and clear.",
#             }
#         ]
#         + chat_history[-8:],
#         max_tokens=150,
#         temperature=0.6,
#     )

#     reply = response.choices[0].message.content.strip()
#     chat_history.append({"role": "assistant", "content": reply})
#     return reply


# async def process(audio):
#     text = transcribe(audio)
#     if not text:
#         return "(Couldn't understand speech)", None

#     reply = chat_reply(text)
#     audio_reply = await text_to_speech(reply)
#     return reply, audio_reply


# ui = gr.Interface(
#     fn=process,
#     inputs=gr.Audio(sources=["microphone"], type="filepath", label="🎤 Speak"),
#     outputs=[gr.Textbox(label="Priya Says"), gr.Audio(label="🔊 Spoken Response")],
#     title="Priya - Voice Assistant",
#     description="Click and speak. Priya listens, responds, and speaks back.",
# )


# ui.launch()
