# 🚀 CodeFlow-AI

[![CodeFlow-AI Pipeline](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml/badge.svg)](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml)

A high-speed, multimodal local developer assistant and autonomous RAG agent designed to streamline coding workflows, manage workspace memory, and bridge local development with cloud intelligence.

---

## 🛠️ Tech Stack & Architecture

- **LLM Routing:** Groq (`openai/gpt-oss-120b`) for ultra-fast natural language intent parsing.
- **Embeddings & Analysis:** Google Gemini (`gemini-embedding-001` & `gemini-1.5-flash`) for vector embeddings and deep code analysis.
- **Vector Memory (RAG):** Pinecone (Serverless) for long-term workspace indexing and code chunk retrieval.
- **Integrations:** Two-way Discord Bot (`discord.py`) and GitHub API integration for issue scouting.
- **Web Scraping:** DuckDuckGo Search (`ddgs`) for real-time web lookups.

---

## ✨ Key Features

- **🧠 Workspace RAG Memory:** Automatically chunks, embeds, and indexes your local codebase into Pinecone so you can query your project architecture in plain English.
- **💬 Two-Way Discord Integration:** Interact with your assistant via Discord webhooks and mentions (`@Jarvis`) with automatic message sanitization.
- **🛰️ GitHub Issue Scout:** Fetch and filter open GitHub issues by keywords and target difficulty (`easy`, `medium`, `hard`).
- **⚙️ Natural Language Automation:** Seamlessly maps conversational prompts to desktop actions, web searches, media playback, and code execution.

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/RebeLrusheR/CodeFlow-AI.git](https://github.com/RebeLrusheR/CodeFlow-AI.git)
cd CodeFlow-AI

python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt

GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_WEBHOOK_URL=your_discord_webhook_url
GITHUB_TOKEN=your_github_token

python main.py
