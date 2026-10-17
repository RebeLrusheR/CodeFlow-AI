# 🚀 CodeFlow-AI

[![CodeFlow-AI Pipeline](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml/badge.svg)](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml)

A highly integrated, multimodal local developer assistant and autonomous RAG agent designed to streamline coding workflows, manage workspace memory, and bridge local development with cloud intelligence via the Model Context Protocol (MCP). 

Now featuring a **3-way synced architecture** (Terminal, Web Dashboard, and Discord) and an autonomous **GitScout** agent that resolves GitHub issues and generates Pull Requests with a human-in-the-loop approval gate.

---

## 🛠️ Tech Stack & Architecture

- **Orchestration & UI:** FastAPI + WebSockets for the real-time Web Dashboard, orchestrated via `start.py`.
- **LLM Routing & Implementation:** Groq (`openai/gpt-oss-120b` for routing, `llama3-70b-8192` for multi-agent planning/coding).
- **Embeddings & Code Review:** Google Gemini (`text-embedding-004` & `gemini-3.8-flash`) via the updated `google-genai` SDK.
- **Vector Memory (RAG):** Pinecone (Serverless) for long-term workspace indexing and code chunk retrieval.
- **Dynamic Tooling:** Model Context Protocol (MCP) for asynchronous local tool discovery and execution.
- **Observability:** Langfuse for real-time production tracing of agent steps, latency, and token usage.
- **Integrations:** Two-way Discord Bot (`discord.py`) and GitHub API integration for issue scouting.
- **Web Scraping:** DuckDuckGo Search (`ddgs`) for real-time web lookups.

---

## ✨ Key Features

- **🚀 3-Way Control Architecture:** Operate Jarvis seamlessly from your IDE Terminal, a sleek local Web Dashboard, or remotely via Discord. All interfaces share state and sync in real-time.
- **🛰️ Autonomous GitScout & PR Generation:** Finds "good first issues", clones the target repository locally, and deploys the AI Task Force to fix the bug. **Zero Profile Spam:** It only forks the repository to your public GitHub profile and submits a PR *after* you explicitly approve the code.
- **🚦 Unified Human Approval Gate:** Before any PR is submitted, GitScout pauses and sends a detailed code diff and Gemini Security Audit to both Discord and the Web Dashboard. Reply `!approve` or click the web button to merge, or `!reject` to abort.
- **⚡ Fast Local Intent Router:** Instantly intercepts native OS commands (e.g., `play <song>`, system reboots, launching apps) to execute them locally, bypassing the heavy AI multi-agent pipelines to save tokens and latency.
- **🤖 Polyglot Multi-Agent Task Force:** Trigger complex tasks to launch an asynchronous workflow where a Groq Architect plans the architecture, a Groq Implementer writes the code, and a Gemini Senior Reviewer audits it for bugs.
- **🔌 Model Context Protocol (MCP):** Connects to a local FastMCP server to discover and execute local environment tools dynamically without hardcoding them into the router.
- **🧠 Workspace RAG Memory:** Automatically chunks, embeds, and indexes your local codebase into Pinecone so you can query your project architecture in plain English.
- **👀 Complete Observability:** Every API call, retrieval operation, and multi-agent workflow is fully traced and monitored on your Langfuse dashboard.

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/RebeLrusheR/CodeFlow-AI.git](https://github.com/RebeLrusheR/CodeFlow-AI.git)
cd CodeFlow-AI
  
  python -m venv .venv
  source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
  pip install -r requirements.txt
  
 # AI APIs
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# Databases & Observability
PINECONE_API_KEY=your_pinecone_api_key
LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public
LANGFUSE_HOST=[https://cloud.langfuse.com](https://cloud.langfuse.com)

# Integrations
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_WEBHOOK_URL=your_discord_webhook_url
GITHUB_TOKEN=your_github_token
  
  python main.py
