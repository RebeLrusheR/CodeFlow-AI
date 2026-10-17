import subprocess
import sys
from main import multi_agent_task_force

print("==================================================")
print("CODEFLOW-AI KERNEL ONLINE")
print("==================================================")

processes = []

try:
    # 1. Boot up the Web Server
    print("Booting Web Server (api_server.py)...")
    web_proc = subprocess.Popen([sys.executable, "api_server.py"])
    processes.append(web_proc)

    # 2. Boot up the Discord GitScout Agent
    print("Booting GitScout (github_agent.py)...")
    agent_proc = subprocess.Popen([sys.executable, "github_agent.py"])
    processes.append(agent_proc)

    print("\n✅ All systems active. Web Dashboard: http://127.0.0.1:8000")
    print("✅ Discord Bot is listening for '!start'.")
    print("==================================================\n")

    # 3. Direct Terminal Pipe to main.py
    while True:
        try:
            user_input = input("\n[Terminal] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.lower() in ['exit', 'quit']:
            break

        print("Jarvis: Processing...")
        try:
            # Everything routes straight to your main agent engine
            response = multi_agent_task_force(user_input)

            if isinstance(response, dict):
                print(f"\nJarvis:\n{response.get('implementation') or response.get('review') or response}\n")
            else:
                print(f"\nJarvis: {response}\n")
        except Exception as e:
            print(f"Jarvis [Error]: {e}")

except KeyboardInterrupt:
    print("\nManual interrupt detected.")
finally:
    print("Shutting down all connected systems...")
    for p in processes:
        p.terminate()
    print("Shutdown complete. Goodbye!")