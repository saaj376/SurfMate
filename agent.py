import asyncio
import os
import argparse

from dotenv import load_dotenv
from browser_use import Agent, Browser
from browser_use.llm.litellm.chat import ChatLiteLLM

load_dotenv()

APP_URL = "http://127.0.0.1:5000"
GEMINI_MODEL = "gemini-2.5-flash"


def build_llm() -> ChatLiteLLM:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "Missing GOOGLE_API_KEY. Add it to the .env file:\n"
            "  GOOGLE_API_KEY=your_actual_key"
        )
    # litellm expects GEMINI_API_KEY internally for gemini models
    os.environ["GEMINI_API_KEY"] = api_key
    
    return ChatLiteLLM(
        model=f"gemini/{GEMINI_MODEL}",
        temperature=0.0,
    )


async def run_task(browser: Browser, llm: ChatLiteLLM, task: str):
    # use_vision=True explicitly forces the agent to extract visual elements 
    # instead of just relying on text attributes, fulfilling the VisionWebAnnotator requirement.
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
    )
    history = await agent.run()
    
    if history and history.history and history.history[-1].result:
        res = history.history[-1].result[-1].extracted_content
        print("\n=== Agent Result ===")
        print(res)
    return history


async def execute_task_persistent(browser: Browser, task_text: str) -> str:
    print("\n[agent] ----------------------------------------------------", flush=True)
    print(f"[agent] Received task from queue: '{task_text}'", flush=True)
    print("[agent] Connecting to LLM...", flush=True)
    llm = build_llm()
    try:
        print("[agent] Booting persistent sequence...", flush=True)
        
        full_task = (
            "You are an autonomous administrative agent.\n"
            f"If you are not currently on the dashboard, go to {APP_URL}/bypass to automatically access the dashboard.\n"
            "If you are already on the dashboard, DO NOT navigate or log in again. Just execute the task directly from where you are.\n"
            f"Execute the user's requested core task: '{task_text}'\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Use your vision capabilities to locate elements directly on the screen.\n"
            "- Find and click the necessary buttons.\n"
            "- Verify that the action was successful by watching for success messages before calling done.\n"
        )
        
        history = await run_task(browser, llm, full_task)
        if history and history.history and history.history[-1].result:
            return history.history[-1].result[-1].extracted_content or "Done."
        return "Task completed without return."
    except Exception as e:
        print(f"Error in execute_task_persistent: {e}")
        return f"Error: {e}"

async def execute_task(task_text: str) -> str:
    print("[agent] Connecting to LLM...", flush=True)
    llm = build_llm()
    print("[agent] Launching headless browser engine (this may take up to 10 seconds)...", flush=True)
    browser = Browser()
    print(f"[agent] Browser launched. Booting agent sequence with task: '{task_text}'", flush=True)

    try:
        
        full_task = (
            "You are an autonomous administrative agent.\n"
            f"Step 1: Go to {APP_URL}/bypass to automatically bypass login and access the dashboard.\n"
            "Step 2: Wait for the dashboard to load.\n"
            f"Step 3: Execute the user's requested core task: '{task_text}'\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Use your vision capabilities to locate elements directly on the screen.\n"
            "- Find and click the necessary buttons.\n"
            "- Verify that the action was successful by watching for success messages before calling done.\n"
        )
        
        history = await run_task(browser, llm, full_task)
        if history and history.history and history.history[-1].result:
            return history.history[-1].result[-1].extracted_content or "Done."
        return "Task completed without return."
    finally:
        await browser.stop()


async def main() -> None:
    parser = argparse.ArgumentParser(description="IT Task Agent using Browser-Use")
    parser.add_argument(
        "task",
        type=str,
        nargs="?",
        help="Natural language instruction for the agent."
    )
    args = parser.parse_args()
    if not args.task:
        print("Please provide a task. Example: python agent.py \"Create a user named Bob\"")
        return
    await execute_task(args.task)


if __name__ == "__main__":
    asyncio.run(main())
