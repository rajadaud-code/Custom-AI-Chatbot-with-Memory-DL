"""
Main Interactive CLI Application - Custom AI Chatbot with Memory
=================================================================
Author: Senior AI Architect (Techling Private Limited)

Provides an interactive CLI interface to chat with the Stateful AI Chatbot,
inspect sliding window memory state, trigger live system audits, and test DB persistence.
"""

import sys
import uuid
import logging
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from memory_manager import ValidationError
from chatbot import StatefulChatbot
from db_persistence import PostgresMemoryStore
from run_audit import main as run_system_audit

# Load environment variables
load_dotenv()

# Silence verbose background logs for clean CLI interface
logging.getLogger("MemoryManager").setLevel(logging.WARNING)
logging.getLogger("StatefulChatbot").setLevel(logging.INFO)


def print_help():
    """Print available CLI slash commands."""
    print("\n--- Available Commands ---")
    print("  /help      - Display this help menu")
    print("  /audit     - Execute the automated 'System Audit & Memory Exam'")
    print("  /memory    - View the current in-memory sliding window history array")
    print("  /summary   - View memory statistics (size, capacity, dropped pairs)")
    print("  /persist   - Save current RAM memory state to PostgreSQL DB (UUID + JSONB)")
    print("  /clear     - Reset and clear current conversation memory")
    print("  /exit      - Exit the application")
    print("---------------------------\n")


def run_cli():
    """Run interactive terminal session with Stateful Chatbot."""
    print("\n" + "=" * 70)
    print("      PROJECT 1: CUSTOM AI CHATBOT WITH MEMORY (CLI INTERFACE)")
    print("      Developed for Techling Private Limited")
    print("=" * 70)

    # Initialize Chatbot
    session_uuid = str(uuid.uuid4())
    chatbot = StatefulChatbot(provider="auto", max_memory_messages=10)
    db_store = PostgresMemoryStore()

    print(f"\n[Session Initialized]")
    print(f"  • Session UUID : {session_uuid}")
    print(f"  • Provider     : {chatbot.provider_type.upper()}")
    print(f"  • Memory Cap   : {chatbot.memory.max_messages} messages (Sliding Window FIFO)")
    print("\nType your message below (or '/help' for commands, '/exit' to quit).\n")

    while True:
        try:
            user_input = input("User > ")
            trimmed = user_input.strip()

            # Handle commands
            if trimmed.lower() in ("/exit", "/quit"):
                print("\nGoodbye! Session ended.")
                break

            if trimmed.lower() == "/help":
                print_help()
                continue

            if trimmed.lower() == "/audit":
                run_system_audit()
                print("\n[Returned to interactive session]")
                continue

            if trimmed.lower() in ("/memory", "/history"):
                history = chatbot.get_memory_snapshot()
                print(f"\n--- In-Memory Sliding Window History ({len(history)} messages) ---")
                if not history:
                    print("  (Memory array is currently empty)")
                else:
                    for idx, msg in enumerate(history, 1):
                        print(f"  [{idx:02d}] {msg['role'].upper()}: {msg['content']}")
                print("-" * 65 + "\n")
                continue

            if trimmed.lower() == "/summary":
                summary = chatbot.memory.get_summary()
                print("\n--- Memory Manager State Summary ---")
                for key, value in summary.items():
                    print(f"  • {key:<25}: {value}")
                print("-" * 40 + "\n")
                continue

            if trimmed.lower() == "/clear":
                chatbot.clear_memory()
                print("[INFO] In-memory conversation history has been cleared.\n")
                continue

            if trimmed.lower() == "/persist":
                history = chatbot.get_memory_snapshot()
                success = db_store.save_session_memory(session_id=session_uuid, memory_history=history)
                if success:
                    print(f"[PASSED] Successfully persisted RAM array ({len(history)} msgs) to PostgreSQL JSONB under UUID: {session_uuid}\n")
                else:
                    print("[FAILED] Persistence failed.\n")
                continue

            # Process Chat Message through Stateful Pipeline
            try:
                model_response = chatbot.send_message(user_input)
                print(f"\nAI ({chatbot.provider_type.upper()}) > {model_response}\n")

            except ValidationError as ve:
                # Intercepted by Structural Validation Gate
                print(f"\n[Validation Gate Intercepted]: {ve}\n")

            except Exception as ex:
                print(f"\n[ERROR] Error generating response: {ex}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Exiting...")
            break


if __name__ == "__main__":
    run_cli()
