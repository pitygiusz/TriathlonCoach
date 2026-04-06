# Triathlon Coach

An agent-based AI coaching system designed to assist you in training for traithlons.


## Goal
The goal of this project is to support triathlon preparation by elevating simple in-chat advice from AI into a more personalized and convenient experience. 

You can just text your coach 
>What should I do today?

>Analyze my latest swimming

>Add a 10km run yesterday, 55min, 155bpm

Available 24/7, the system considers training history, fatigue, race goals, and weather forecasts. It combines a **Streamlit web app** for detailed analytics with a **Telegram bot** for quick, on-the-go interactions that feel like talking to a real coach.

## Key Features
- **Multi-modal Logging:** Log workouts via natural language or by sending screenshots from Strava/Garmin app.
- **Personalized Coaching:** Generate training plans or daily suggestions tailored to recent performance and recovery needs.
- **Web Interface (Streamlit):** Interactive dashboard for workout logging, statistics, and race countdowns.
- **Telegram Bot:** On-demand NLP-powered interface for seamless, conversational coaching.

## System Architecture
Instead of relying on a single, unpredictable prompt, the bot implements a **Semantic Router** and **Specialized Sub-Agents**:
- **The Router:** Uses a fast and cheap model to intercept messages, enforce strict Pydantic JSON schemas, classify intent, and detect conversational follow-ups.
- **Specialized Sub-Agents:** Dedicated agents for Vision parsing, NLP parsing, and History analysis. Other questions are routed to a heavier model for expert knowledge.
- **Human-in-the-Loop:** Agents don't blindly hallucinate database changes. They generate parsed previews and require explicit user confirmation before executing SQLite operations.

More details about the architecture and design choices can be found [here](./architecture.md).

## Project Structure

```
TriathlonCoach/
├── app.py               # Streamlit UI 
├── bot.py              # Telegram bot 
├── agents.py           # Agent-based AI system 
├── coach.py            # AI logic 
├── database.py         # SQLite database layer 
├── tools.py            # External tools 
├── requirements.txt    # Python dependencies
└── triathlon_logs.db   # Auto-created SQLite database (not committed)
```

## Note
The project is currently hardcoded in Polish for my personal use, but the architecture allows for easy adaptation to other languages by modifying the prompts and NLP routing logic in the bot.

## How to Run

**1. Clone the repository**

```bash
git clone https://github.com/pitygiusz/TriathlonCoach
cd TriathlonCoach
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Set up your API keys**

The app uses the Google Gemini API and Telegram Bot API. Make sure your keys are available as environment variables:

```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
export TELEGRAM_TOKEN="your_telegram_bot_token_here"
export MY_CHAT_ID="your_telegram_chat_id_here"
```

**4a. Start the Streamlit web app**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

**4b. Start the Telegram bot** (in a separate terminal)

```bash
python bot.py
```

The bot will start polling for messages. Send `/start` to your bot on Telegram to begin and then simply write natural language requests.

## Technologies Used
- **AI & LLM:** Google Gemini API, Structured Outputs (JSON/Pydantic)
- **Backend:** Python, Pandas, Telebot (pyTelegramBotAPI), Open-Meteo API
- **Frontend:** Streamlit
- **Database:** SQLite (Local, lightweight, edge-ready)
- **Deployment:** Self-hosted on Raspberry Pi (Edge AI) with Tailscale for secure remote access.


## Screenshots and sample outputs

- [Streamlit app demo](./demo/app_demo.md)

- [Telegram bot demo](./demo/chat_demo.md)

## Contributions
This project was completed individually. Some parts of the code were written/debugged with the help of AI.

