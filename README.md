# 👩‍💼 Bhumika – AI HR Assistant (Voice + Text)

Bhumika is an **AI-powered conversational HR assistant** built with **Streamlit + LLM (Groq) + Speech + Analytics**.
It simulates a real-world Talent Acquisition professional who can interact through **voice or text**, provide career guidance, and generate intelligent follow-ups while tracking conversation insights.

---

## 🚀 What This Project Does

This app creates a **human-like HR conversation experience** where users can:

* 🎤 Speak naturally → get AI responses (Speech-to-Text → LLM → Text-to-Speech)
* 💬 Chat via text as an alternative
* 🧠 Receive context-aware HR guidance (career, skills, interviews, growth)
* 📊 View real-time conversation analytics (topics, sentiment, duration)
* 🔁 Get smart follow-up questions generated dynamically
* 🔊 Hear responses spoken back using TTS
* 🧾 Maintain contextual memory using session state + summarization

---

## 🏗️ System Architecture

```
User (Voice/Text)
        ↓
Streamlit UI
        ↓
Speech Recognition (STT)
        ↓
Groq LLM (Conversation + Persona)
        ↓
Conversation Intelligence Layer
    • Topic Extraction
    • Sentiment Analysis
    • Context Summarization
    • Follow-up Generation
        ↓
Text-to-Speech (Puter / Edge TTS)
        ↓
Audio Response + UI Rendering
```

---

## 🔁 Application Pipeline

### 1️⃣ Input Layer

* User provides **voice or text input**
* Voice recorded using `st.audio_input()`

### 2️⃣ Speech-to-Text Processing

* `speech_recognition` converts audio → text
* Noise handling + transcription applied

### 3️⃣ Conversation Intelligence

System extracts:

* Topics discussed
* User sentiment
* Conversation goal/context
* Summary every few turns

### 4️⃣ LLM Response Generation

* Groq LLM generates response using:

  * Persona prompt (HR professional identity)
  * Conversation history
  * Extracted analytics context

### 5️⃣ Follow-Up Question Generation

* AI produces 3 smart HR-style follow-up questions

### 6️⃣ Text-to-Speech Response

* Primary: Puter TTS API
* Fallback: Microsoft Edge TTS
* Audio returned to Streamlit player

### 7️⃣ Analytics Update (Real-Time)

Sidebar updates:

* Duration
* Message count
* Topics discussed
* Sentiment trend
* Conversation summary

---

## 🧠 Key Features

✔ Voice-enabled conversational assistant
✔ Persona-driven HR advisory system
✔ Multi-provider TTS fallback system
✔ Lightweight sentiment + topic analysis
✔ Context summarization to control token growth
✔ Interactive follow-up suggestion engine
✔ Real-time conversation analytics dashboard
✔ Fully session-state driven (no external DB required)

---

## 🛠️ Tech Stack

| Layer              | Technology                               |
| ------------------ | ---------------------------------------- |
| Frontend           | Streamlit                                |
| LLM                | Groq (LLaMA 3.3)                         |
| Speech Recognition | Google Speech API (`speech_recognition`) |
| Text-to-Speech     | Puter API + Edge TTS                     |
| Async Audio        | `asyncio`                                |
| State Management   | Streamlit Session State                  |
| Analytics          | Custom NLP heuristics                    |
| Environment        | `python-dotenv`                          |

---

## 📦 Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/bhumika-hr-assistant.git
cd bhumika-hr-assistant
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Add Environment Variables

Create `.env` file:

```
GROQ_API_KEY=your_groq_api_key
```

---

## ▶️ Run the App

```bash
streamlit run app.py
```

---

## 📊 Example Use Cases

* AI-powered HR helpdesk
* Career counseling assistant
* Interview preparation bot
* Voice-enabled enterprise assistant
* Conversational onboarding guide
* AI coaching tool

---

## 🧩 Project Structure

```
app.py
.env
requirements.txt
README.md
```

---

## ⚙️ How It Manages Context Efficiently

Instead of sending full history every time:

* Summarizes conversation every few turns
* Tracks only key signals (topics, sentiment)
* Keeps token usage optimized
* Prevents LLM context overflow

---

## 🔐 Notes

* No data persistence — session-based conversation
* Designed for demonstration / conversational workflows
* Can be extended with Supabase / Redis for production memory

---

## 🔮 Possible Enhancements

* Persistent chat history (Supabase)
* Redis caching for conversation memory
* RAG integration for company policies
* Role-based enterprise deployment
* Real-time WebRTC audio streaming
* Vector search for resume matching

---

## 👩‍💼 Persona

Bhumika is designed as a **warm, conversational HR leader** who:

* Encourages reflection and growth
* Provides actionable career insights
* Maintains human-like tone and engagement

---

## 📜 License

MIT License — feel free to adapt and extend.

---

## ✨ Acknowledgment

Built to explore **voice-first AI interfaces combined with contextual LLM interaction** for human-centered enterprise tools.
