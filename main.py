import os
import webbrowser
import time
import threading
import pyautogui
import subprocess
import requests
import re
import warnings
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from github import Github, Auth
import discord
from discord.ext import commands

import google.generativeai as genai
from groq import Groq
from pinecone import Pinecone

# Suppress the package rename warning from your terminal
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", category=FutureWarning)
from duckduckgo_search import DDGS

load_dotenv()

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")

# --- CONFIGURE AI APIs ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize Pinecone
pinecone_api_key = os.getenv("PINECONE_API_KEY")
if pinecone_api_key:
    pc = Pinecone(api_key=pinecone_api_key)
    pinecone_index = pc.Index("jarvis-workspace")
else:
    print("Warning: PINECONE_API_KEY missing from .env. Workspace memory disabled.")
    pinecone_index = None


# --- DESKTOP & WEB CONTROL FUNCTIONS ---
def open_url(url: str):
    webbrowser.open(url)
    print(f"Successfully opened {url} in the browser.")


def play_youtube(query: str):
    print(f"\n[Jarvis Media] Finding and playing top result for: '{query}'...")
    search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            webbrowser.open(search_url)
            return
        video_ids = re.findall(r"watch\?v=(\S{11})", response.text)
        if video_ids:
            top_video_id = video_ids[0]
            direct_url = f"https://www.youtube.com/watch?v={top_video_id}"
            webbrowser.open(direct_url)
            print(f"Jarvis: Now playing -> {direct_url}")
        else:
            webbrowser.open(search_url)
    except Exception as e:
        webbrowser.open(search_url)
        print(f"Error fetching direct video: {e}")


def search_web(query: str):
    print(f"\n[Jarvis Web Scraper] Searching web for: '{query}'...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            print("Jarvis: No results found.")
            return
        print("\n🔍 **Top Web Search Results:**")
        for res in results:
            print(f"   • [{res.get('title', 'No Title')}]({res.get('href', '#')})\n     {res.get('body', '')}\n")
    except Exception as e:
        print(f"Jarvis: Scraping error: {e}")


def launch_app(app_name: str):
    os.system(f"start {app_name}")
    print(f"Command issued to launch {app_name}.")


def type_text(text: str):
    time.sleep(1)
    pyautogui.write(text, interval=0.05)
    print(f"Successfully typed: '{text}'")


# --- LOCAL IDE INSPECTION & PURE PYTHON TEST RUNNER ---
def read_local_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Jarvis: Error - File '{file_path}' does not exist.")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"\n📁 **Inspecting Code: {file_path}**\n")
    print(content)
    print("-" * 50)


def test_local_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Jarvis: Error - File '{file_path}' does not exist.")
        return
    print(f"\n[Jarvis Test Runner] Running '{file_path}' locally...")
    try:
        result = subprocess.run(["python", file_path], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Success! '{file_path}' executed cleanly with zero errors.")
            if result.stdout.strip():
                print(f"Output:\n{result.stdout}")
        else:
            print(f"❌ Execution failed. Error Traceback captured:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("Jarvis: Execution timed out (possible infinite loop).")
    except Exception as e:
        print(f"Jarvis: Failed to run file: {e}")


# --- DISCORD NOTIFICATION & REMINDER SYSTEM ---
def send_discord_alert(message: str):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Jarvis: Error - DISCORD_WEBHOOK_URL is missing in your .env file.")
        return
    payload = {"content": f"🤖 **Jarvis Alert:** {message}"}
    try:
        requests.post(webhook_url, json=payload, timeout=5)
        print("📤 Jarvis: Alert successfully dispatched to Discord!")
    except Exception as e:
        print(f"Jarvis: Error sending Discord webhook: {e}")


def schedule_target_time_reminder(target_time_str: str, message: str):
    try:
        now = datetime.now()
        target_hour, target_minute = map(int, target_time_str.split(":"))
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target_time <= now:
            target_time += timedelta(days=1)
        delay_seconds = int((target_time - now).total_seconds())

        def target():
            time.sleep(delay_seconds)
            send_discord_alert(message)

        threading.Thread(target=target, daemon=True).start()
        print(
            f"⏱️ Jarvis: Reminder set for {target_time_str}! I will ping Discord in {delay_seconds // 60} minutes for: '{message}'")
    except Exception as e:
        print(f"Jarvis: Failed to set time-based reminder.")


# --- ADVANCED GITHUB SCOUT ---
def scout_issues_with_filters(command_input: str):
    target_difficulty = None
    if "--difficulty" in command_input.lower():
        parts = command_input.lower().split("--difficulty")
        query_part = parts[0].strip()
        target_difficulty = parts[1].strip().split()[0].lower()
    else:
        query_part = command_input.strip()

    auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
    g = Github(auth=auth)
    print(f"\n[Jarvis Scout] Scouting GitHub for: '{query_part}'...\n")

    try:
        if "/" in query_part and " " not in query_part:
            issues = g.get_repo(query_part).get_issues(state="open", sort="created", direction="desc")
        else:
            issues = g.search_issues(query=query_part)

        count = 0
        for issue in issues:
            if count >= 5: break
            if issue.pull_request: continue
            print(f"📌 Issue #{issue.number}: {issue.title}\n   • URL: {issue.html_url}\n")
            count += 1
    except Exception as e:
        print(f"Error fetching issues: {e}")


# --- PINECONE RAG MEMORY ---
def embed_workspace():
    """Scans the workspace, chunks code files, and uploads them to Pinecone."""
    if not pinecone_index:
        return "Pinecone API key missing."
    print("🧠 Indexing workspace into Pinecone memory...")

    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)  # Create it if it doesn't exist
        print(f"Created empty workspace folder at {WORKSPACE_DIR}")
        return "Workspace folder was missing, created a new empty one."

    vectors = []
    for root, _, files in os.walk(WORKSPACE_DIR):
        for file in files:
            if not file.endswith((".py", ".txt", ".md", ".json", ".html", ".js", ".css")):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Chunk large files every ~1000 characters
                chunks = [content[i:i + 1000] for i in range(0, len(content), 1000)]

                for i, chunk in enumerate(chunks):
                    # Fixed: using the new model and specifying 768 dimensions
                    embedding = genai.embed_content(
                        model="models/gemini-embedding-001",
                        content=chunk,
                        task_type="retrieval_document",
                        output_dimensionality=768
                    )["embedding"]

                    vectors.append({
                        "id": f"{file}-chunk-{i}",
                        "values": embedding,
                        "metadata": {"file": file, "text": chunk}
                    })
            except Exception as e:
                print(f"Failed to read {file}: {e}")

    if vectors:
        for i in range(0, len(vectors), 100):
            pinecone_index.upsert(vectors=vectors[i:i + 100])
        print(f"✅ Successfully memorized {len(vectors)} code chunks!")
        return f"Successfully embedded {len(vectors)} chunks of code."
    return "No compatible files found in workspace to embed."


def query_rag_memory(question: str):
    """Searches Pinecone for the answer and uses Gemini to explain it."""
    if not pinecone_index:
        return "Pinecone API key missing."
    print(f"🧠 Searching memory for: '{question}'...")

    try:
        # Fixed: using the new model and specifying 768 dimensions
        query_embedding = genai.embed_content(
            model="models/gemini-embedding-001",
            content=question,
            task_type="retrieval_query",
            output_dimensionality=768
        )["embedding"]

        results = pinecone_index.query(vector=query_embedding, top_k=3, include_metadata=True)

        if not results['matches']:
            return "I couldn't find anything relevant in your workspace."

        context = "\n\n".join([match['metadata']['text'] for match in results['matches']])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Answer the following question based ONLY on this retrieved code context from my workspace:\n\nContext:\n{context}\n\nQuestion: {question}"

        return model.generate_content(prompt).text
    except Exception as e:
        return f"Failed to query memory: {e}"


# --- AI BRAINS (GROQ ROUTER & GEMINI ANALYZER) ---
def parse_intent_with_groq(user_message: str):
    system_prompt = """
    You are Jarvis. Map the user's message to the available system functions.
    Output ONLY a valid JSON array of objects in execution order. Do not output conversational text outside the JSON.

    Available functions:
    - {"action": "play_youtube", "query": "<search term>"}
    - {"action": "search_web", "query": "<search term>"}
    - {"action": "launch_app", "app_name": "<name>"}
    - {"action": "open_url", "url": "<url>"}
    - {"action": "schedule_reminder", "time_str": "<HH:MM>", "message": "<msg>"}
    - {"action": "analyze_code", "file_path": "<path>"}
    - {"action": "scout", "query": "<topic> [--difficulty easy/medium/hard]"}
    - {"action": "embed_workspace"}
    - {"action": "query_workspace", "question": "<question about my code>"}
    - {"action": "chat", "response": "<conversational reply>"}
    """
    try:
        completion = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1
        )
        response_text = completion.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`").replace("json\n", "", 1)
        return json.loads(response_text)
    except Exception as e:
        print(f"Groq Routing Error: {e}")
        return [{"action": "chat", "response": "Sir, I encountered an API routing error."}]


def analyze_large_file_with_gemini(file_path: str):
    if not os.path.exists(file_path):
        return f"File '{file_path}' not found."
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyze this code file and provide a brief summary of its purpose and any potential bugs:\n\n{content}"
        print(f"🧠 Passing {file_path} to Gemini API for deep analysis...")
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Gemini Analysis Error: {e}"


# --- TWO-WAY DISCORD BOT INTEGRATION ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"\n🤖 Jarvis Discord Bot online as {bot.user}!")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.lower().startswith("jarvis"):
        clean_msg = re.sub(r'<@!?\d+>', '', message.content).strip()
        if clean_msg.lower().startswith("jarvis"):
            clean_msg = clean_msg[6:].strip()

        await message.channel.send("🧠 Thinking...")
        actions = parse_intent_with_groq(clean_msg)

        for task in actions:
            action = task.get("action")
            if action == "play_youtube":
                play_youtube(task.get("query"))
                await message.channel.send(f"🎵 Playing: `{task.get('query')}`")
            elif action == "launch_app":
                launch_app(task.get("app_name"))
                await message.channel.send(f"💻 Launching app: `{task.get('app_name')}`")
            elif action == "search_web":
                search_web(task.get("query"))
                await message.channel.send(f"🔍 Searching web for: `{task.get('query')}` (Check terminal for results)")
            elif action == "open_url":
                open_url(task.get("url"))
                await message.channel.send(f"🌐 Opening URL: `{task.get('url')}`")
            elif action == "schedule_reminder":
                schedule_target_time_reminder(task.get("time_str"), task.get("message"))
                await message.channel.send(f"⏱️ Reminder set for {task.get('time_str')}")
            elif action == "analyze_code":
                analysis = analyze_large_file_with_gemini(task.get("file_path"))
                await message.channel.send(f"**Gemini Analysis:**\n{analysis[:1900]}")
            elif action == "scout":
                scout_issues_with_filters(task.get("query"))
                await message.channel.send(
                    f"🛰️ Scouting GitHub for: `{task.get('query')}` (Check terminal for results)")
            elif action == "embed_workspace":
                await message.channel.send("🧠 Indexing workspace into Pinecone memory...")
                status = embed_workspace()
                await message.channel.send(f"✅ {status}")
            elif action == "query_workspace":
                answer = query_rag_memory(task.get("question"))
                await message.channel.send(f"🧠 **Workspace Memory:**\n{answer[:1900]}")
            elif action == "chat":
                await message.channel.send(task.get("response"))

    await bot.process_commands(message)


def run_discord_bot():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Jarvis: Warning - DISCORD_BOT_TOKEN missing. Two-way Discord bot disabled.")


discord_thread = threading.Thread(target=run_discord_bot, daemon=True)
discord_thread.start()

# --- INTERACTIVE TERMINAL LOOP ---
print("\n" + "=" * 65)
print(" Jarvis High-Speed Scout & AI Automation Online.")
print(" Type natural language commands or use strict shortcuts.")
print(" Type 'exit' to quit.")
print("=" * 65 + "\n")

while True:
    user_command = input("Aditya: ").strip()

    if not user_command:
        continue
    if user_command.lower() in ['exit', 'quit']:
        print("Jarvis: Shutting down systems. Goodbye!")
        break

    # Strict Shortcuts for Speed
    if user_command.lower().startswith("scout "):
        scout_issues_with_filters(user_command[6:].strip())
    elif user_command.lower().startswith("read "):
        read_local_file(user_command[5:].strip())
    elif user_command.lower().startswith("test "):
        test_local_file(user_command[5:].strip())

    # Groq AI Natural Language Fallback
    else:
        print("Jarvis: Thinking...")
        actions = parse_intent_with_groq(user_command)

        for task in actions:
            action = task.get("action")
            if action == "play_youtube":
                play_youtube(task.get("query"))
            elif action == "launch_app":
                launch_app(task.get("app_name"))
            elif action == "search_web":
                search_web(task.get("query"))
            elif action == "open_url":
                open_url(task.get("url"))
            elif action == "schedule_reminder":
                schedule_target_time_reminder(task.get("time_str"), task.get("message"))
            elif action == "analyze_code":
                print(analyze_large_file_with_gemini(task.get("file_path")))
            elif action == "scout":
                scout_issues_with_filters(task.get("query"))
            elif action == "embed_workspace":
                print(embed_workspace())
            elif action == "query_workspace":
                print(f"\n🧠 **Workspace Memory:**\n{query_rag_memory(task.get('question'))}")
            elif action == "chat":
                print(f"Jarvis: {task.get('response')}")