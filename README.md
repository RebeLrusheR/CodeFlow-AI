# 🚀 CodeFlow-AI

[![CodeFlow-AI Pipeline](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml/badge.svg)](https://github.com/RebeLrusheR/CodeFlow-AI/actions/workflows/python-app.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/Protocol-MCP-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, multimodal developer copilot and autonomous coding agent designed to streamline engineering workflows, ground operations with Pinecone workspace memory, and bridge local tool execution with cloud models via the **Model Context Protocol (MCP)**.

Featuring a synchronized **3-Way Control Architecture** (Terminal, Web Dashboard, and Discord) and an autonomous **GitScout** agent that scouts issues, drafts solutions across an iterative self-correction loop, and submits Pull Requests with a strict **Human-in-the-Loop (HITL)** approval gate.

---

## 🛠️ Architecture Overview

```text
                              +-----------------------------+
                              |   Unified User Interfaces   |
                              |  Terminal | Web UI | Discord|
                              +--------------+--------------+
                                             |
                                             v
                                +------------------------+
                                | Fast Intent Router     |
                                | (Groq / Local Handlers)|
                                +-----------+------------+
                                            |
             +------------------------------+-------------------------------+
             |                                                              |
             v                                                              v
 [ Fast Local Actions / OS Tools ]                         [ Multi-Agent Task Force (Iterative) ]
 - Native App Launching & System Control                   1. Architect (Groq Llama 3)
 - Media Playback & DuckDuckGo Search                      2. Vector RAG Context (Pinecone)
 - MCP Subprocess Server Tools                             3. Implementer (Gemini 3.8 Flash)
                                                           4. Senior Reviewer Audit (Gemini 3.8 Flash)
                                                              (Auto-corrects up to 3 attempts)
                                                                            |
                                                                            v
                                                             [ Human-in-the-Loop Approval ]
                                                             - Web Deck / Discord (!approve / !reject)
                                                                            |
                                                                            v
                                                             [ Autonomous GitScout PR Submission ]

---

## ⚡ Tech Stack

- **Orchestration & Backend:** FastAPI, Uvicorn, Asynchronous I/O, `multiprocessing`/`subprocess` via `start.py`.
- **Primary Agent Routing:** Groq SDK (`llama3-70b-8192` / `openai/gpt-oss-120b`).
- **Heavy Implementation & Review:** Google GenAI SDK (`gemini-3.8-flash` with HTTP timeout handling).
- **Embeddings & Vector Store:** Google GenAI (`text-embedding-004`) + Pinecone Serverless Vector Database (`jarvis-workspace`).
- **Live Grounding & Web Search:** DuckDuckGo Search API (`ddgs`).
- **Local Extensibility:** Model Context Protocol (MCP) Client (`ClientSession`, `stdio_client`).
- **Traces & Observability:** Langfuse (`@observe()`) tracing token consumption, latency, and agent reasoning.
- **Frontend & Remote UI:** Tailwind CSS, Marked.js Markdown renderer, vanilla JavaScript event bus, Discord Gateway (`discord.py`).

---

## ✨ Key Features

- **🔄 Synchronized 3-Way Command Plane:** Drive the system through your local terminal CLI, the dark-themed web terminal dashboard (`http://localhost:8000`), or remotely through Discord.
- **🔁 Iterative Multi-Agent Self-Correction:**
  - **Architect:** Deconstructs prompts into executable technical steps.
  - **Implementer:** Synthesizes robust, non-truncated solutions informed by vector memory context.
  - **Senior Reviewer:** Scans for syntax errors, truncated blocks, or logic flaws. Automatically re-prompts the Implementer (up to 3 iterations) before asking for human intervention.
- **🛰️ Autonomous GitScout Issue Pipeline:** Scrapes GitHub for targeted documentation or code issues, automatically clones target repositories locally, and builds PR candidates.
- **🛡️ Zero-Spam Human Approval Gate (HITL):** GitScout never forks or pushes to public remotes automatically. It halts on completion, streaming the full unified diff and Gemini security audit to Discord and the Web Deck for an explicit `!approve` or `!reject`.
- **🧠 Workspace Vector Indexing (RAG):** Recursively inspects the `./workspace` directory, splits source files into 1,000-character overlapping chunks, embeds them via `text-embedding-004`, and updates Pinecone for semantic code queries.
- **💬 Conversational "Standard Chat" with Memory:** Direct chat mode preserving conversational context alongside live DuckDuckGo web snippets.
- **🔌 FastMCP Dynamic Tools:** Hooks into local `FastMCP` servers, exposing local workstation tools to the agent dynamically over standard I/O.

---

## 📁 Repository Structure
CodeFlow-AI/
├── api_server.py           # FastAPI backend handling dashboard endpoints and SSE/polling
├── github_agent.py         # GitScout engine: issue querying, cloning, branching, and PR creation
├── local_mcp_server.py     # Local FastMCP tool server
├── main.py                 # Core agent orchestration, RAG engine, and CLI loop
├── start.py                # Multi-service launcher (API Server + GitScout + CLI)
├── static/
│   └── index.html          # Cyberpunk/Terminal-aesthetic Tailwind Web Dashboard
├── workspace/              # Monitored directory for code ingestion and vector indexing
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment variable template
└── README.md

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python:** 3.11 or 3.12 installed
- **Git:** Installed and available in your global `PATH`
- **Pinecone Account:** An existing index named `jarvis-workspace` (dimension: `768`, metric: `cosine`)

### 2. Clone and Configure Virtual Environment

```bash
git clone [https://github.com/RebeLrusheR/CodeFlow-AI.git](https://github.com/RebeLrusheR/CodeFlow-AI.git)
cd CodeFlow-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

cp .env.example .env

Populate the .env file with your credentials:
# ==========================================
# Core AI Model Provider Keys
# ==========================================
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama3-70b-8192

# ==========================================
# Vector Database & Retrieval Memory
# ==========================================
PINECONE_API_KEY=your_pinecone_api_key_here

# ==========================================
# Observability & Production Tracing
# ==========================================
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=[https://cloud.langfuse.com](https://cloud.langfuse.com)

# ==========================================
# Remote Integrations & Autonomous Engine
# ==========================================
GITHUB_TOKEN=ghp_your_github_personal_access_token_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_WEBHOOK_URL=[https://discord.com/api/webhooks/](https://discord.com/api/webhooks/)...

Option A: Launch Full System (Recommended)
python start.py

Interactive CLI Only
python main.py
