import os
import sys
import shutil
import asyncio
import requests
import discord
import subprocess
import time
from github import Github
from dotenv import load_dotenv
import logging
import urllib.parse
import urllib.request
import re
import webbrowser

# Mute noisy discord gateway debug/info logs in the terminal
logging.getLogger("discord").setLevel(logging.WARNING)

from main import multi_agent_task_force, embed_workspace

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
gh = Github(GITHUB_TOKEN)

WORKSPACE_DIR = os.path.join(os.getcwd(), "github_workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Global channel reference for the loop
command_channel = None
web_approval = None


def send_discord_webhook(message):
    """Sends a message to the Discord channel via Webhook."""
    if DISCORD_WEBHOOK_URL:
        chunks = [message[i:i + 1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk})
            time.sleep(1)


async def poll_web_commands():
    """Constantly watches the shared text file for commands from the Web Dashboard."""
    global web_approval
    while True:
        if os.path.exists("scout_command.txt"):
            try:
                with open("scout_command.txt", "r") as f:
                    command = f.read().strip().lower()

                if command:
                    # Delete the file immediately so it only triggers once
                    os.remove("scout_command.txt")

                    if command == "scout":
                        print("Jarvis: Web Dashboard triggered -> START SCOUTING")
                        await execute_scout_workflow(local_mode=False)
                    elif command == "local":
                        print("Jarvis: Web Dashboard triggered -> PROCESS LOCAL REPOS")
                        await execute_scout_workflow(local_mode=True)
                    elif command in ["approve", "reject"]:
                        web_approval = command
            except Exception:
                pass
        await asyncio.sleep(1)  # Check every 1 second


@client.event
async def on_ready():
    print(f"Jarvis Autonomous Scout logged in as {client.user}")
    print("Waiting for initial command via Discord (!start)...")
    client.loop.create_task(poll_web_commands())


@client.event
async def on_message(message):
    global command_channel
    if message.author == client.user:
        return

    # Set the channel so the loop knows where to send the menu
    command_channel = message.channel

    # ---------------------------------------------------------
    # Remote control: Play YouTube on host PC
    # ---------------------------------------------------------
    if message.content.lower().startswith("!play "):
        song_name = message.content[6:].strip()
        await message.channel.send(f"🎵 Opening YouTube on host PC to play: **{song_name}**")

        # Search YouTube and play the first result
        def play_on_pc():
            query_string = urllib.parse.urlencode({"search_query": song_name})
            html_content = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
            search_results = re.findall(r"watch\?v=(\S{11})", html_content.read().decode())
            if search_results:
                webbrowser.open("https://www.youtube.com/watch?v=" + search_results[0])

        # Run it in a background thread so it doesn't freeze the bot
        await asyncio.to_thread(play_on_pc)
        return

    # ---------------------------------------------------------
    # GitScout Commands
    # ---------------------------------------------------------
    if message.content.lower() == "!start":
        await present_action_menu()

    if message.content.startswith("!rollback"):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("⚠️ Please specify the repository. Example: `!rollback owner/repo_name`")
            return
        target_repo = parts[1]
        await message.channel.send(f"🔄 Attempting to roll back your open pull requests on `{target_repo}`...")
        try:
            def close_prs():
                repo = gh.get_repo(target_repo)
                me = gh.get_user()
                pulls = repo.get_pulls(state='open')
                closed_count = 0
                for pr in pulls:
                    if pr.user.login == me.login:
                        pr.edit(state='closed')
                        closed_count += 1
                return closed_count

            closed_count = await asyncio.to_thread(close_prs)
            if closed_count > 0:
                await message.channel.send(f"✅ Successfully closed {closed_count} pull request(s) on `{target_repo}`.")
            else:
                await message.channel.send(
                    f"ℹ️ Could not find any open pull requests created by you on `{target_repo}`.")
        except Exception as e:
            await message.channel.send(f"❌ Failed to rollback `{target_repo}`. Error: {str(e)}")


async def present_action_menu():
    """Presents the 3 options and routes the logic."""
    menu = (
        "🤖 **GitScout Awaiting Orders:**\n"
        "Reply with one of the following:\n"
        "👉 `scout` (Find a new issue on GitHub)\n"
        "👉 `local` (Work on an existing repo in github_workspace)\n"
        "👉 `exit` (Shut down the scout)"
    )
    send_discord_webhook(menu)

    def check(msg):
        return msg.author != client.user and msg.content.lower() in ['scout', 'local', 'exit']

    try:
        msg = await client.wait_for('message', check=check, timeout=86400)
        choice = msg.content.lower()

        if choice == 'exit':
            send_discord_webhook("👋 Shutting down GitScout. Goodbye!")
            await client.close()
            sys.exit(0)
        elif choice == 'scout':
            await execute_scout_workflow(local_mode=False)
        elif choice == 'local':
            await execute_scout_workflow(local_mode=True)

    except asyncio.TimeoutError:
        print("Menu timed out.")


def scout_and_prepare_issue():
    print("Jarvis: Scouting GitHub for 'good first issue' in Python...")
    query = 'label:"good first issue" language:python state:open no:assignee'
    issues = gh.search_issues(query, sort="created", order="desc")

    target_issue = None
    for issue in issues:
        if not issue.pull_request:
            target_issue = issue
            break

    if not target_issue:
        return None, None, None

    # Get the original repository, DO NOT fork yet
    original_repo = target_issue.repository
    repo_path = os.path.join(WORKSPACE_DIR, original_repo.name)

    if not os.path.exists(repo_path):
        # Clone original repo directly (read-only)
        subprocess.run(["git", "clone", original_repo.clone_url, repo_path], check=True)
    else:
        subprocess.run(["git", "pull"], cwd=repo_path, check=True)

    # Create a local branch for the fix
    branch_name = f"fix-issue-{target_issue.number}"
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=False)

    return target_issue, original_repo, repo_path

def get_local_repo():
    """Scans the workspace for existing downloaded repos."""
    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    if not folders:
        return None
    # For automation, we pick the first available local repo.
    target_folder = folders[0]
    repo_path = os.path.join(WORKSPACE_DIR, target_folder)
    return repo_path


async def human_approval_gate(issue_title, repo_name, proposed_patch_data):
    alert_msg = (
        f"🚨 **Proposed Fix Ready for Issue:** {issue_title}\n"
        f"**Repository:** {repo_name}\n\n"
        f"**Code Generated by Groq:**\n```python\n{proposed_patch_data['implementation']}\n```\n"
        f"**Gemini Audit:**\n{proposed_patch_data['review']}\n\n"
        f"**Reply with '!approve' to submit PR, or '!reject' to abort.**"
    )
    send_discord_webhook(alert_msg)

    # Write the alert to a shared state file for the web app to read
    with open("scout_alert.txt", "w", encoding="utf-8") as f:
        f.write(alert_msg)

    global web_approval
    web_approval = None  # Reset web state

    def check(msg):
        return msg.author != client.user and msg.content.lower() in ['!approve', '!reject']

    print(f"Jarvis: Sent alert for '{issue_title}'. Awaiting Discord OR Web response...")

    # Create a task for Discord's wait_for
    discord_task = asyncio.create_task(client.wait_for('message', check=check, timeout=86400))

    try:
        # Loop every second to see if the Web button was clicked OR if Discord got a reply
        while not discord_task.done():
            if web_approval == "approve":
                print("Jarvis: Approval received from Web Dashboard!")
                discord_task.cancel()
                if os.path.exists("scout_alert.txt"): os.remove("scout_alert.txt")
                return True
            elif web_approval == "reject":
                print("Jarvis: Fix rejected from Web Dashboard.")
                discord_task.cancel()
                if os.path.exists("scout_alert.txt"): os.remove("scout_alert.txt")
                return False

            await asyncio.sleep(1)

        # If Discord task finishes first, process its result
        msg = await discord_task

        if os.path.exists("scout_alert.txt"): os.remove("scout_alert.txt")

        if msg.content.lower() == '!approve':
            print("Jarvis: Approval received from Discord!")
            await msg.add_reaction("✅")
            return True
        else:
            print("Jarvis: Fix rejected by human via Discord.")
            await msg.add_reaction("❌")
            return False

    except asyncio.TimeoutError:
        if os.path.exists("scout_alert.txt"): os.remove("scout_alert.txt")
        print("Jarvis: Approval request timed out after 24 hours.")
        return False


async def execute_scout_workflow(local_mode=False):
    """The unified workflow for both scout and local execution."""

    issue_title = "Local Enhancements"
    issue_body = "General code review and optimization."
    repo_name = "Local Workspace"
    fork = None

    if not local_mode:
        issue, fork, repo_path = await asyncio.to_thread(scout_and_prepare_issue)
        if not issue:
            send_discord_webhook("⚠️ No suitable issues found on GitHub right now.")
            await present_action_menu()
            return
        issue_title = issue.title
        issue_body = issue.body
        repo_name = fork.full_name
    else:
        repo_path = get_local_repo()
        if not repo_path:
            send_discord_webhook("⚠️ No local repositories found in `github_workspace`. Please `scout` first.")
            await present_action_menu()
            return
        repo_name = os.path.basename(repo_path)

    print(f"Jarvis: Indexing {repo_name} into Vector Database...")
    try:
        # Assuming embed_workspace can target a specific directory
        await asyncio.to_thread(embed_workspace)
    except Exception as e:
        print(f"Embed warning: {e}")

    directive = (
        f"We are working on the repository located at '{repo_path}'. "
        f"Task Context: '{issue_title}'. Description: '{issue_body}'. "
        f"Analyze the codebase, implement necessary fixes, and specify which files are updated."
    )

    ai_result = await asyncio.to_thread(multi_agent_task_force, directive)
    is_approved = await human_approval_gate(issue_title, repo_name, ai_result)

    if is_approved:
        if not local_mode and fork:
            try:
                subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
                subprocess.run(["git", "commit", "-m", f"Fix: {issue_title}"], cwd=repo_path, check=True)
                default_branch = fork.default_branch
                subprocess.run(["git", "push", "origin", default_branch], cwd=repo_path, check=True)

                original_repo = gh.get_repo(fork.parent.full_name) if fork.parent else fork
                pr = original_repo.create_pull(
                    title=f"Fix: {issue_title}",
                    body="Automated fix generated by CodeFlow-AI.",
                    head=f"{gh.get_user().login}:{default_branch}",
                    base=original_repo.default_branch
                )
                send_discord_webhook(f"✅ **Pull Request Submitted!**\n🔗 {pr.html_url}")
            except Exception as e:
                send_discord_webhook(f"❌ **PR Submission Failed.**\nError: {e}")

        # Cleanup logic: Delete the folder on approval
        print(f"Jarvis: Cleaning up local workspace {repo_path}...")
        shutil.rmtree(repo_path, ignore_errors=True)
        send_discord_webhook(f"🗑️ Cleaned up local repository: `{repo_name}`")
    else:
        # Retain logic: Leave folder intact on rejection
        send_discord_webhook(
            f"🛑 PR Aborted. The local repository `{repo_name}` has been retained in `github_workspace` for manual review.")

    # Loop back to menu
    await present_action_menu()


# Comment this out if running exclusively via start.py to avoid port conflicts,
# or leave it if you run github_agent.py directly.
if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)