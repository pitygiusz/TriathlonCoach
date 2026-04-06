# Triathlon Coach AI

In-depth details about the architecture and design choices.

## Telegram Bot

The **Telegram bot** delivers on-demant coaching with natural language understanding:
- **Natural language input** - Ask anything ("What should I do today?", "Analyze my swimming", "Delete yesterday's run") and the NLP router directs to the appropriate agent
- **Photo-based logging** - Send a screenshot of your training app (Strava, Garmin, etc.) and the bot extracts workout data automatically
- **Text-based logging** - Describe a workout naturally ("30 min easy run yesterday, RPE 5") and the bot parses, previews, and saves it with your confirmation

## Web Interface

The **Streamlit web app** provides user with easy access to all features in a web-friendly format:
- Interactive workout logging form with edit and delete capabilities
- Comprehensive dashboard with statistics and race countdowns
- AI-powered coaching tab to generate tailored weekly plans


## Agent-Powered Intelligence

The app's core strength is its **agent-based AI system** - specialized autonomous agents based on Google Gemini, optimized for specific coaching tasks:

- **Training Proposer** - Suggests optimal training plans based on your history and goals
- **History Analyzer** - Answers questions about your training and form
- **Workout Parser** - Converts natural language descriptions to structured data
- **Workout Image Parser** - Extracts data from training app screenshots
- **Delete Workout** - Intelligently removes workouts based on natural language descriptions

Rather than using a single monolithic AI prompt, each agent is context-aware and specialized for its task, ensuring better accuracy, faster responses, and more focused coaching.

By utilizing the newest `gemini-3.1-flash-lite-preview` model, the system can quickly and inexpensively handle multi-modal inputs (text + images) and generate structured outputs with JSON schemas, making it ideal for this coaching application. 

More complex questions that require deeper reasoning or expert knowledge are routed to the heavier `gemini-3-flash-preview` model.

## Interaction Pipeline 

1. **Ingestion:** User sends a message or image via Telegram.
2. **Context Retrieval:** The system fetches the last conversation state (`intent` and latest `response`) from the short-term memory buffer.
3. **Semantic Routing:** The lightweight LLM router classifies the intent into predefined categories (using strict JSON schemas) and checks for follow-up flags.
4. **Agent Execution:** The specific agent takes over, analyzes the context/database history, and generates a response or prepares a database transaction.
5. **Human-in-the-Loop (HITL):** For write/delete operations, the agent suspends execution and waits for user confirmation via the `register_next_step_handler`.
6. **Database Operation & State Update:** Upon confirmation, SQLite executes the transaction, and the conversation state is updated for future context.

## Pipeline diagram

[![](https://mermaid.ink/img/pako:eNp1U91u2jAUfhXLUieQyv8IIZo6AVHXqt3KoBVaAxdecgAPYke2Mxp-bvoW27PscrzX7CRknarlIvY55zvf-fUO-zwA7OCFINES3btThvR3doYmv39sj88JkooIxTeAKBI8VpQtMsiDBFHyzB9dsyhWszKqVC7QSGNA7MYQEqaon8uHzOcjhF5J_7hIUD-ez0GUZ6hSRQPOFDwpVC0IMnyRzJAHW0qOz4gRRFb-N8gsGdbE3Y-ABKiGBkui9qi3AKYm3g3jmzUEC9CGKyqVCZuaZq_cJ4IqA3NhDQpyhp43JMIU-NKpyOn406dw_LUi6C7wt4mKayO-DfkmyRBZDmlPLkH5S7fvldILcvunbMo5Zw5IwR-AjUB6-gBBdE5aiDiT8P_wjySiMtbzubq-v30RvJfyDQV8p7D5S-gSRU7anDSXUrwh2aVj1VOZUxHK9---itqF0edjNNe0a19A7pEpbPz51vTP7Z8qKiCf-B4NCPNh7WUHuotMHpSzfyrKqx_Hvg9SevmpN0ZKsnhV_CVlehsyMWtY1mitXnsPUWDqzPfsje5gtE6Q4unK5kwn_sIrU-cpVqonNT7XL4MG2FEihnMcggiJEfHOOEyxWkIIU-zoa0DEaoqn7KB9IsIeOQ9PbvrhLJbYmZO11FKc5udSot9cWGgFsADEgMdMYcdqWSkJdnb4CTvderVVt9vNVqfb7NQbHW1MsFNp21W73rG7nbrVblp2u3E4x9s0bKPaaFuWtllW0-40W423hz9HeT4x?type=png)](https://mermaid.live/edit#pako:eNp1U91u2jAUfhXLUieQyv8IIZo6AVHXqt3KoBVaAxdecgAPYke2Mxp-bvoW27PscrzX7CRknarlIvY55zvf-fUO-zwA7OCFINES3btThvR3doYmv39sj88JkooIxTeAKBI8VpQtMsiDBFHyzB9dsyhWszKqVC7QSGNA7MYQEqaon8uHzOcjhF5J_7hIUD-ez0GUZ6hSRQPOFDwpVC0IMnyRzJAHW0qOz4gRRFb-N8gsGdbE3Y-ABKiGBkui9qi3AKYm3g3jmzUEC9CGKyqVCZuaZq_cJ4IqA3NhDQpyhp43JMIU-NKpyOn406dw_LUi6C7wt4mKayO-DfkmyRBZDmlPLkH5S7fvldILcvunbMo5Zw5IwR-AjUB6-gBBdE5aiDiT8P_wjySiMtbzubq-v30RvJfyDQV8p7D5S-gSRU7anDSXUrwh2aVj1VOZUxHK9---itqF0edjNNe0a19A7pEpbPz51vTP7Z8qKiCf-B4NCPNh7WUHuotMHpSzfyrKqx_Hvg9SevmpN0ZKsnhV_CVlehsyMWtY1mitXnsPUWDqzPfsje5gtE6Q4unK5kwn_sIrU-cpVqonNT7XL4MG2FEihnMcggiJEfHOOEyxWkIIU-zoa0DEaoqn7KB9IsIeOQ9PbvrhLJbYmZO11FKc5udSot9cWGgFsADEgMdMYcdqWSkJdnb4CTvderVVt9vNVqfb7NQbHW1MsFNp21W73rG7nbrVblp2u3E4x9s0bKPaaFuWtllW0-40W423hz9HeT4x)