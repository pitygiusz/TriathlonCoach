# Triathlon Coach AI

A personal triathlon training assistant that helps athletes log workouts, track progress, and receive AI-generated coaching advice and personalized training plans.

## Goal
The goal of this project is to support triathlon preparation by elevating simple in-chat advice from AI into a more personalized and convenient experience. 

The system is designed in a way that feels like having a personal coach available 24/7, who knows your training history, tiredness, race goals and weather forecasts.

By combining a user-friendly web app for detailed logging and analysis with a Telegram bot for quick, on-the-go interactions that feels like talking to your coach, the system ensures that athletes can access coaching support whenever and wherever they need it.


## Key Features

- **Track workouts** - Log training sessions with discipline, duration, distance, RPE, and notes. 
- **Generate personalized plans** - Get AI-generated weekly training plans and one-off workout suggestions tailored to your recent performance and goals.
- **Provide coaching advice** - Receive detailed coaching feedback on your training history, form assessment, and targeted recommendations to improve performance.
- **Context-aware recommendations** - All suggestions take into account weather forecasts, upcoming races, training fatigue, recovery needs, and your current fitness level.

### Web Interface

The **Streamlit web app** provides user with easy access to all features in a web-friendly format:
- Interactive workout logging form with edit and delete capabilities
- Comprehensive dashboard with statistics and race countdowns
- AI-powered coaching tab to generate tailored weekly plans

### Telegram Bot

The **Telegram bot** delivers on-demant coaching with natural language understanding:
- **Natural language input** - Ask anything ("What should I do today?", "Analyze my swimming", "Delete yesterday's run") and the NLP router directs to the appropriate agent
- **Photo-based logging** - Send a screenshot of your training app (Strava, Garmin, etc.) and the bot extracts workout data automatically
- **Text-based logging** - Describe a workout naturally ("30 min easy run yesterday, RPE 5") and the bot parses, previews, and saves it with your confirmation

### Agent-Powered Intelligence

The app's core strength is its **agent-based AI system** - six specialized autonomous agents based on Google Gemini, optimized for specific coaching tasks:

- **One Training Proposer** - Suggests the optimal single workout for today
- **Weekly Plan Proposer** - Generates 7-day training schedules  
- **History Analyzer** - Answers questions about your training and form
- **Workout Parser** - Converts natural language descriptions to structured data
- **Workout Image Parser** - Extracts data from training app screenshots using vision AI
- **Delete Workout** - Intelligently removes workouts based on natural language descriptions

Rather than using a single monolithic AI prompt, each agent is context-aware and specialized for its task, ensuring better accuracy, faster responses, and more focused coaching.

By utilizing the newest `gemini-3.1-flash-lite-preview` model, the system can quickly and inexpensively handle multi-modal inputs (text + images) and generate structured outputs with JSON schemas, making it ideal for this coaching application.

The project is designed to be **self-hosted on Raspberry Pi** with secure remote access via Tailscale and Telegram.



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

- **Python** (Streamlit, Pandas, Pydantic)
- **Google Gemini API** (multi-modal AI, structured outputs with JSON schemas)
- **Telegram Bot API** (python-telebot)
- **SQLite** (local database)
- **Open-Meteo API** (weather forecasting)
- **PIL** (image processing for vision-based workout parsing)


## Screenshots and sample outputs

Streamlit app demo can be found [here](https://github.com/pitygiusz/TriathlonCoach/demo/app_demo.md).

Telegram bot demo can be found [here](). [WIP]

## Contributions
This project was completed individually. Some parts of the code were written/debugged with the help of AI.