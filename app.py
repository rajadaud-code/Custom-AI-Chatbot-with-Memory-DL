"""
Web Server Backend - Custom AI Chatbot with Memory
===================================================
Author: Senior AI Architect (Decode Lab)

Provides REST API endpoints and serves the modern Responsive Web UI
for testing the Stateful Chatbot, Sliding Window Memory Engine, and System Audits.
"""

import os
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

from memory_manager import ValidationError
from chatbot import StatefulChatbot
from db_persistence import PostgresMemoryStore
from run_audit import (
    audit_validation_gate,
    audit_memory_exam,
    audit_sliding_window_truncation,
    audit_database_persistence
)

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebApp")

# Initialize global chatbot instance and session ID
SESSION_UUID = str(uuid.uuid4())
chatbot = StatefulChatbot(provider="auto", max_memory_messages=10)
db_store = PostgresMemoryStore()


@app.route("/")
def serve_index():
    """Serve main responsive Web UI."""
    return send_from_directory("static", "index.html")


@app.route("/api/session", methods=["GET"])
def get_session():
    """Get active session details and memory state."""
    return jsonify({
        "session_id": SESSION_UUID,
        "provider": chatbot.provider_type.upper(),
        "memory_summary": chatbot.memory.get_summary(),
        "history": chatbot.get_memory_snapshot()
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    CHAT API ENDPOINT
    -----------------
    Receives JSON payload: { "message": "user input string" }
    Runs payload through Structural Validation Gate -> Stateful Memory -> LLM Provider.
    Returns HTTP 400 JSON on validation intercept, or HTTP 200 on success.
    """
    data = request.get_json(force=True, silent=True) or {}
    user_input = data.get("message")

    try:
        # Process message through stateful pipeline
        model_response = chatbot.send_message(user_input)

        return jsonify({
            "success": True,
            "user_input": user_input,
            "response": model_response,
            "provider": chatbot.provider_type.upper(),
            "memory_summary": chatbot.memory.get_summary(),
            "history": chatbot.get_memory_snapshot()
        })

    except ValidationError as ve:
        # Intercepted by Structural Validation Gate
        logger.warning(f"Validation Gate Intercepted: {ve}")
        return jsonify({
            "success": False,
            "error_type": "ValidationError",
            "error": str(ve)
        }), 400

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({
            "success": False,
            "error_type": "ServerError",
            "error": str(e)
        }), 500


@app.route("/api/clear", methods=["POST"])
def clear_memory():
    """Clear in-memory conversation history."""
    chatbot.clear_memory()
    return jsonify({
        "success": True,
        "message": "Memory history cleared successfully.",
        "memory_summary": chatbot.memory.get_summary(),
        "history": []
    })


@app.route("/api/persist", methods=["POST"])
def persist_memory():
    """Persist RAM array to PostgreSQL JSONB under current session UUID."""
    history = chatbot.get_memory_snapshot()
    success = db_store.save_session_memory(session_id=SESSION_UUID, memory_history=history)
    return jsonify({
        "success": success,
        "session_id": SESSION_UUID,
        "persisted_message_count": len(history)
    })


@app.route("/api/audit", methods=["POST"])
def run_audit_api():
    """Trigger System Audit ('Memory Exam') suite and return JSON report."""
    v_gate = audit_validation_gate()
    m_exam = audit_memory_exam()
    s_win = audit_sliding_window_truncation()
    db_pers = audit_database_persistence()

    all_passed = v_gate and m_exam and s_win and db_pers

    return jsonify({
        "all_passed": all_passed,
        "audits": [
            {"id": 1, "name": "Structural Validation Gate Interceptor", "passed": v_gate},
            {"id": 2, "name": "System Memory Exam (Retention Test)", "passed": m_exam},
            {"id": 3, "name": "Sliding Window FIFO Dynamic Truncation", "passed": s_win},
            {"id": 4, "name": "Enterprise PostgreSQL JSONB Persistence", "passed": db_pers}
        ]
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n=================================================================")
    print(f"  CUSTOM AI CHATBOT WITH MEMORY - WEB UI SERVER")
    print(f"  Decode Lab | Running on http://127.0.0.1:{port}")
    print(f"=================================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
