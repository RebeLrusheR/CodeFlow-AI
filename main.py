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
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime, timedelta
from dotenv import load_dotenv
from github import Github, Auth

# --- LANGFUSE INTEGRATION ---
from langfuse import observe

from google import genai
from google.genai import types
from groq import Groq
from pinecone import Pinecone

# Suppress the package rename warning from your terminal
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", category=FutureWarning)
from ddgs import DDGS

load_dotenv()

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")

# --- CONFIGURE AI APIs ---
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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


def play_youtube(query: str):
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
        else:
            webbrowser.open(search_url)
    except Exception as e:
        webbrowser.open(search_url)


def search_web(query: str):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return
        for res in results:
            print(f"   • [{res.get('title', 'No Title')}]({res.get('href', '#')})\n     {res.get('body', '')}\n")
    except Exception as e:
        pass


def launch_app(app_name: str):
    os.system(f"start {app_name}")


def type_text(text: str):
    time.sleep(1)
    pyautogui.write(text, interval=0.05)


# --- LOCAL IDE INSPECTION & PURE PYTHON TEST RUNNER ---
def read_local_file(file_path: str):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    print(content)


def test_local_file(file_path: str):
    if not os.path.exists(file_path):
        return
    try:
        result = subprocess.run(["python", file_path], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            if result.stdout.strip():
                print(f"Output:\n{result.stdout}")
        else:
            pass
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        pass


# --- DISCORD NOTIFICATION & REMINDER SYSTEM ---
def send_discord_alert(message: str):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    payload = {"content": f"🤖 **Jarvis Alert:** {message}"}
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        pass

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
    except Exception as e:
        pass


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

    try:
        if "/" in query_part and " " not in query_part:
            issues = g.get_repo(query_part).get_issues(state="open", sort="created", direction="desc")
        else:
            issues = g.search_issues(query=query_part)

        count = 0
        for issue in issues:
            if count >= 5: break
            if issue.pull_request: continue
            count += 1
    except Exception as e:
        pass


# --- PINECONE RAG MEMORY ---
def embed_workspace():
    """Scans the workspace, chunks code files, and uploads them to Pinecone."""
    if not pinecone_index:
        return "Pinecone API key missing."

    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
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

                chunks = [content[i:i + 1000] for i in range(0, len(content), 1000)]

                for i, chunk in enumerate(chunks):
                    response = gemini_client.models.embed_content(
                        model="text-embedding-004",
                        contents=chunk,
                        config=types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=768
                        )
                    )
                    embedding = response.embeddings[0].values

                    vectors.append({
                        "id": f"{file}-chunk-{i}",
                        "values": embedding,
                        "metadata": {"file": file, "text": chunk}
                    })
            except Exception as e:
                pass

    if vectors:
        for i in range(0, len(vectors), 100):
            pinecone_index.upsert(vectors=vectors[i:i + 100])
        return f"Successfully embedded {len(vectors)} chunks of code."
    return "No compatible files found in workspace to embed."


@observe()
def query_rag_memory(question: str):
    """Searches Pinecone for the answer and uses Gemini to explain it."""
    if not pinecone_index:
        return "Pinecone API key missing."

    try:
        response = gemini_client.models.embed_content(
            model="text-embedding-004",
            contents=question,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768
            )
        )
        query_embedding = response.embeddings[0].values

        results = pinecone_index.query(vector=query_embedding, top_k=3, include_metadata=True)

        if not results['matches']:
            return "I couldn't find anything relevant in your workspace."

        context = "\n\n".join([match['metadata']['text'] for match in results['matches']])
        prompt = f"Answer the following question based ONLY on this retrieved code context from my workspace:\n\nContext:\n{context}\n\nQuestion: {question}"

        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        return f"Failed to query memory: {e}"


# --- AI BRAINS (GROQ ROUTER & GEMINI ANALYZER) ---
@observe()
def parse_intent_with_groq(user_message: str, mcp_tools: list = None):
    mcp_tools_str = ""
    if mcp_tools:
        mcp_tools_str = "\n    " + "\n    ".join(
            [f'- {{"action": "mcp_tool", "tool_name": "{t.name}"}}' for t in mcp_tools])

    system_prompt = f"""
    You are Jarvis. Map the user's message to the available system functions.
    Output ONLY a valid JSON array of objects in execution order. Do not output conversational text outside the JSON.

    Available functions:
- {{"action": "play_youtube", "query": "<search term>"}}
- {{"action": "search_web", "query": "<search term>"}}
- {{"action": "launch_app", "app_name": "<name>"}}
- {{"action": "open_url", "url": "<url>"}}
- {{"action": "schedule_reminder", "time_str": "<HH:MM>", "message": "<msg>"}}
- {{"action": "analyze_code", "file_path": "<path>"}}
- {{"action": "scout", "query": "<topic> [--difficulty easy/medium/hard]"}}
- {{"action": "embed_workspace"}}
- {{"action": "query_workspace", "question": "<question about my code>"}}
- {{"action": "chat", "response": "<conversational reply>"}}{mcp_tools_str}
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
        return [{"action": "chat", "response": "Sir, I encountered an API routing error."}]


@observe()
def analyze_large_file_with_gemini(file_path: str):
    if not os.path.exists(file_path):
        return f"File '{file_path}' not found."
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        prompt = f"Analyze this code file and provide a brief summary of its purpose and any potential bugs:\n\n{content}"

        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        return f"Gemini Analysis Error: {e}"


@observe()
def multi_agent_task_force(task_description: str):
    command = task_description.strip().lower()

    # ==========================================
    # 1. INTENT ROUTER: FAST LOCAL COMMANDS
    # ==========================================
    if command.startswith("play "):
        song_name = task_description[5:].strip()
        try:
            play_youtube(song_name)
            return {
                "implementation": f"✅ Executed local command: Playing '{song_name}' on YouTube.",
                "review": "N/A - Direct OS Command Executed."
            }
        except Exception as e:
            return {
                "implementation": f"❌ Failed to play song: {e}",
                "review": "Error"
            }

    if command in ["reboot", "restart pc"]:
        time.sleep(5)
        os.system("shutdown /r /t 0")
        return {
            "implementation": "✅ Executed local command: Initiated System Reboot.",
            "review": "N/A - Direct OS Command Executed."
        }

    # ==========================================
    # 2. HEAVY AI PIPELINE (Iterative & Context-Aware)
    # ==========================================
    print("\n🤖 [Multi-Agent Task Force] Assembling team...")

    # FIX 3: ZERO-SHOT BLINDSPOT - Inject Pinecone memory
    print("🧠 Fetching workspace context from Vector Memory...")
    try:
        rag_context = query_rag_memory(task_description)
    except Exception as e:
        rag_context = "No relevant workspace context found."

    print("📐 Architect: Drafting execution plan...")
    architect_prompt = f"""
    You are the Architect AI. Break down this task into 2-4 concrete execution steps. 
    Output ONLY a valid JSON array of strings representing the steps. Do not add markdown formatting or conversational text.
    Task: {task_description}
    Workspace Context: {rag_context}
    """
    try:
        architect_res = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
            messages=[{"role": "system", "content": architect_prompt}],
            temperature=0.1
        ).choices[0].message.content.strip()

        if architect_res.startswith("```"):
            architect_res = architect_res.strip("`").replace("json\n", "", 1)
        plan = json.loads(architect_res)
    except Exception as e:
        plan = ["Execute the requested task directly."]

    # FIX 1 & 2: THE ITERATIVE LOOP & GEMINI UPGRADE
    max_retries = 3
    attempt = 1
    implementer_res = ""
    reviewer_res = "❌ REVISION NEEDED"
    feedback = ""

    while attempt <= max_retries and "❌ REVISION NEEDED" in reviewer_res:
        print(f"🛠️ Implementer: Executing plan (Attempt {attempt}/{max_retries})...")

        implementer_prompt = f"""
        You are the Implementer AI. Execute the following plan for the user's task.
        User Task: '{task_description}'
        Execution Plan: {plan}
        Workspace Context: {rag_context}
        {feedback}

        Provide the complete, working solution or code. Do not truncate the output.
        """
        try:
            implementer_res = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=implementer_prompt,
                config=types.GenerateContentConfig(temperature=0.2)
            ).text
        except Exception as e:
            implementer_res = f"Implementation Error: {e}"

        print(f"🧐 Reviewer: Analyzing implementation (Attempt {attempt}/{max_retries})...")
        reviewer_prompt = f"""
        You are the Senior Reviewer AI. Review this implementation for the task '{task_description}'.
        If it is flawless, start your response with '✅ APPROVED' and briefly state why. 
        If there are bugs, syntax errors, missing files, or truncation, start with '❌ REVISION NEEDED' and explain the exact fixes required.

        Implementation to review:
        {implementer_res}
        """
        try:
            reviewer_res = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=reviewer_prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            ).text
        except Exception as e:
            print(f"Reviewer API call error: {e}")
            reviewer_res = f"Reviewer Error: {e}"
            break

        if "❌ REVISION NEEDED" in reviewer_res:
            print("⚠️ Reviewer flagged issues. Sending feedback back to Implementer...")
            feedback = f"\n\n[Previous Reviewer Feedback - You MUST fix these issues]:\n{reviewer_res}"
            attempt += 1

    return {
        "implementation": implementer_res,
        "review": reviewer_res
    }


@observe()
def standard_chat(history: list):
    """Conversational chat with real-time web search grounding and memory."""
    # Get the latest user message for searching current events
    latest_message = history[-1]['content'] if history else ""

    # 1. Fetch live search context using DDGS
    search_context = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(latest_message, max_results=4))
        if results:
            snippets = [
                f"- {item.get('title', '')}: {item.get('body', '')} ({item.get('href', '')})"
                for item in results
            ]
            search_context = "\n".join(snippets)
    except Exception as e:
        search_context = ""

    # 2. Build system instructions with live search results
    system_prompt = (
        "You are Jarvis, an authentic and knowledgeable AI peer. "
        "Answer questions directly, accurately, and conversationally. "
        "You have full access to the conversation history to understand context. "
    )
    if search_context:
        system_prompt += f"\n\n[Live Web Search Context for the current query]:\n{search_context}"

    # 3. Compile full message payload
    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        completion = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
            messages=messages,
            temperature=0.4
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Chat Error: {e}"


# --- INTERACTIVE TERMINAL LOOP (ASYNC) ---
async def interactive_loop():
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["local_mcp_server.py"]
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                available_tools = tools_response.tools
                tool_names = [tool.name for tool in available_tools]

                while True:
                    user_command = await asyncio.to_thread(input, "Aditya: ")
                    user_command = user_command.strip()

                    if not user_command:
                        continue
                    if user_command.lower() in ['exit', 'quit']:
                        break

                    elif user_command.lower() == 'restart':
                        os.execv(sys.executable, ['python'] + sys.argv)

                    elif user_command.lower().startswith("scout "):
                        await asyncio.to_thread(scout_issues_with_filters, user_command[6:].strip())
                    elif user_command.lower().startswith("read "):
                        await asyncio.to_thread(read_local_file, user_command[5:].strip())
                    elif user_command.lower().startswith("test "):
                        await asyncio.to_thread(test_local_file, user_command[5:].strip())
                    elif user_command.lower().startswith("build "):
                        try:
                            result = await asyncio.to_thread(multi_agent_task_force, user_command[6:].strip())
                            print("\n" + "=" * 40 + " IMPLEMENTATION " + "=" * 40)
                            print(result["implementation"])
                            print("\n" + "=" * 40 + " CODE REVIEW " + "=" * 40)
                            print(result["review"])
                        except Exception as e:
                            pass
                    else:
                        actions = await asyncio.to_thread(parse_intent_with_groq, user_command, available_tools)

                        for task in actions:
                            action = task.get("action")
                            if action == "play_youtube":
                                await asyncio.to_thread(play_youtube, task.get("query"))
                            elif action == "launch_app":
                                await asyncio.to_thread(launch_app, task.get("app_name"))
                            elif action == "search_web":
                                await asyncio.to_thread(search_web, task.get("query"))
                            elif action == "open_url":
                                await asyncio.to_thread(open_url, task.get("url"))
                            elif action == "schedule_reminder":
                                await asyncio.to_thread(schedule_target_time_reminder, task.get("time_str"),
                                                        task.get("message"))
                            elif action == "analyze_code":
                                print(await asyncio.to_thread(analyze_large_file_with_gemini, task.get("file_path")))
                            elif action == "scout":
                                await asyncio.to_thread(scout_issues_with_filters, task.get("query"))
                            elif action == "embed_workspace":
                                print(await asyncio.to_thread(embed_workspace))
                            elif action == "query_workspace":
                                answer = await asyncio.to_thread(query_rag_memory, task.get("question"))
                                print(f"\n🧠 **Workspace Memory:**\n{answer}")
                            elif action == "mcp_tool":
                                tool_name = task.get("tool_name")
                                result = await session.call_tool(tool_name, arguments={})
                                print(f"Jarvis: {result.content[0].text}")
                            elif action == "chat":
                                print(f"Jarvis: {task.get('response')}")

    except Exception as e:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        pass
