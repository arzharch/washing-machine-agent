# Washing-Machine-Customer-Agent-Bot: AI-Powered Support Assistant

This project is a sophisticated Discord bot designed to act as a first-line of support for washing machine-related issues. It leverages a local Large Language Model (LLM) through Ollama to understand user queries, provide troubleshooting steps, and manage support tickets by integrating with a MantisHub issue tracker.

## Key Features

- **Natural Language Understanding (NLU)**: Uses the Mistral LLM to interpret user messages and determine their intent (e.g., asking for help, describing a problem, requesting a ticket status).
- **Stateful Conversation Management**: Maintains a unique session for each user to track the conversation's context, remember the problem being discussed, and provide coherent, multi-turn support.
- **Automated Troubleshooting**: Provides clear, step-by-step troubleshooting advice for common washing machine problems based on the user's description.
- **Full Ticket Lifecycle Management**: Seamlessly creates, updates, checks the status of, closes, and deletes tickets in MantisHub.
- **Dynamic MantisHub Integration**: Fetches project and category lists directly from MantisHub to ensure tickets are created with valid and relevant information.
- **Secure and Configurable**: Manages sensitive credentials like API tokens using a `.env` file.

## How It Works

The bot's architecture is designed to be modular and efficient:

1.  **Discord Interface (`main.py`)**: The main entry point that connects to Discord and listens for user messages.
2.  **Intent Routing (`bot/llm_ticket.py`)**: When a message is received, it is sent to the LLM, which acts as a "router." The LLM analyzes the message along with the current session context and determines the appropriate action (e.g., `kb_answer`, `create_ticket`, `greeting`).
3.  **Session & Context Management (`bot/session.py`)**: This is the core of the bot's "memory." It creates and maintains a JSON-based session file for each user. This session stores the conversation history, the current problem, and the overall state. This context is passed to the LLM with every request, enabling it to have context-aware conversations.
4.  **MantisHub Client (`mantishub/client.py`)**: A dedicated client for all interactions with the MantisHub REST API. It handles the details of making authenticated requests to create tickets, fetch details, add notes, and more.
5.  **Ticket-User Mapping (`bot/user_tickets.py`)**: A simple database that links a user's Discord ID to the MantisHub ticket IDs they have created, allowing them to easily manage their open tickets.

## Setup and Installation

Follow these steps to get the bot running locally.

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running.
- The `mistral` model pulled from Ollama:
  ```sh
  ollama pull mistral
  ```

### Installation Steps

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/arzharch/washing-machine-agent.git
    cd washing-machine-agent
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    # For Windows
    python -m venv .venv
    .venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a file named `.env` in the project root and add the following, replacing the placeholder values with your actual credentials:
    ```env
    # Your Discord bot's token
    DISCORD_BOT_TOKEN="your_discord_bot_token"

    # The base URL for your MantisHub instance's REST API
    MANTIS_API_BASE="https://your_mantishub_url/api/rest"

    # Your MantisHub API token
    MANTIS_API_TOKEN="your_mantishub_api_token"
    ```

## Usage

Once the setup is complete, run the bot with the following command:

```sh
python main.py
```

The bot should come online in your Discord server, and you can start interacting with it in any channel it has access to.

## Project Structure

```
arzharch-bot/
├── .env                # Holds secret keys and configuration (you must create this)
├── main.py             # Main entry point for the Discord bot
├── requirements.txt    # Project dependencies
├── bot/                # Core application logic
│   ├── llm_ticket.py   # Handles all interactions with the LLM for routing and generation
│   ├── session.py      # Manages user sessions and conversation context
│   ├── user_tickets.py # Maps Discord users to their MantisHub tickets
│   └── ...
├── config/             # Application configuration
│   └── settings.py     # Loads settings from the .env file
├── mantishub/          # MantisHub integration
│   └── client.py       # A client for interacting with the MantisHub REST API
└── ...
```
