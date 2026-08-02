"""
Stateful Chatbot Module - Custom AI Chatbot with Memory
=========================================================
Author: Senior AI Architect (Techling Private Limited)

This module implements the core Stateful Chatbot engine with official Frontier LLM SDK integration
(Google GenAI / OpenAI) and fallback Mock LLM Provider capability.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from memory_manager import SlidingWindowMemory, validate_user_input, ValidationError

# Load environment variables
load_dotenv()

logger = logging.getLogger("StatefulChatbot")


class MockLLMProvider:
    """
    Mock/Simulated LLM Provider for local testing, system auditing, and zero-dependency execution.
    Maintains simulated memory recognition for state extraction tests (e.g., 'What is my name?').
    """

    def __init__(self):
        self.extracted_facts: Dict[str, str] = {}

    def generate_response(self, history: List[Dict[str, str]], system_instruction: Optional[str] = None) -> str:
        if not history:
            return "Hello! How can I assist you today?"

        latest_user_msg = history[-1]["content"]

        # Parse and extract facts from memory history
        for msg in history:
            if msg["role"] == "user":
                content = msg["content"]
                if "my name is" in content.lower():
                    name_part = content.lower().split("my name is")[-1].strip().split()[0].capitalize()
                    self.extracted_facts["name"] = name_part

        # Handle specific queries or distraction test prompts
        lower_input = latest_user_msg.lower()

        if "what is my name" in lower_input:
            if "name" in self.extracted_facts:
                return f"Your name is {self.extracted_facts['name']}."
            else:
                return "I'm sorry, I don't recall your name from our current conversation context."

        if "poem" in lower_input or "distraction" in lower_input:
            return (
                "Here is a poem about Artificial Intelligence:\n"
                "Silicon circuits, thoughts unfurled,\n"
                "A digital whisper across the world.\n"
                "Tokens stream through sliding space,\n"
                "Preserving facts in time and place."
            )

        return f"I have processed your message ('{latest_user_msg[:30]}...') within our active context window of {len(history)} messages."


class StatefulChatbot:
    """
    STATEFUL CHATBOT WITH SLIDING WINDOW MEMORY
    -------------------------------------------
    Orchestrates:
    - Input Validation Interceptor (Guard against HTTP 400 Bad Request)
    - Stateful Memory Append (User + Model turns)
    - Sliding Window FIFO Context Cap
    - Frontier LLM API Invocation (Gemini / OpenAI / Mock)
    """

    def __init__(
        self,
        provider: str = "auto",
        max_memory_messages: int = 10,
        system_instruction: str = "You are an intelligent, helpful AI assistant built by Techling Private Limited."
    ):
        """
        Initialize Stateful Chatbot instance.

        Args:
            provider (str): 'gemini', 'openai', 'mock', or 'auto' (detects API key from env).
            max_memory_messages (int): Max history array capacity (Sliding Window FIFO cap).
            system_instruction (str): System instruction prompt for context framing.
        """
        self.system_instruction = system_instruction
        self.memory = SlidingWindowMemory(max_messages=max_memory_messages, system_instruction=system_instruction)
        self.provider_type = self._resolve_provider(provider)
        self.client = self._init_client()

    def _resolve_provider(self, requested_provider: str) -> str:
        """Resolve LLM Provider based on requested value or environment availability."""
        req = requested_provider.lower()
        
        if req == "gemini":
            return "gemini"
        elif req == "openai":
            return "openai"
        elif req == "mock":
            return "mock"
        
        # Auto resolution
        if os.getenv("GEMINI_API_KEY"):
            return "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            return "openai"
        else:
            logger.info("No LLM API keys found in environment. Falling back to robust Mock LLM Provider.")
            return "mock"

    def _init_client(self) -> Any:
        """Initialize appropriate Frontier LLM SDK client or Mock Provider."""
        if self.provider_type == "gemini":
            try:
                from google import genai
                api_key = os.getenv("GEMINI_API_KEY")
                return genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Google GenAI SDK: {e}. Falling back to Mock Provider.")
                self.provider_type = "mock"
                return MockLLMProvider()

        elif self.provider_type == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                return OpenAI(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI SDK: {e}. Falling back to Mock Provider.")
                self.provider_type = "mock"
                return MockLLMProvider()

        return MockLLMProvider()

    def send_message(self, user_input: str) -> str:
        """
        STATEFUL CHATBOT EXECUTION PIPELINE
        -----------------------------------
        Phase 1: Structural Validation Interceptor (Guards against empty/whitespace strings)
        Phase 2: Append User Input (role: 'user')
        Phase 3: Invoke LLM with active Sliding Window Context History
        Phase 4: Append Model Response (role: 'model')
        Phase 5: Return final response payload

        Args:
            user_input (str): Raw input from user.

        Returns:
            str: Model response text.
        """
        # PHASE 1: STRUCTURAL VALIDATION GATE INTERCEPTOR
        validated_input = validate_user_input(user_input)

        # PHASE 2: APPEND USER INPUT TO STATEFUL MEMORY
        self.memory.add_message(role="user", content=validated_input)

        # PHASE 3: INVOKE FRONTIER LLM API WITH ACTIVE CONTEXT HISTORY
        active_history = self.memory.get_history()
        response_text = self._call_llm_api(active_history)

        # PHASE 4: APPEND MODEL RESPONSE TO STATEFUL MEMORY
        self.memory.add_message(role="model", content=response_text)

        # PHASE 5: RETURN MODEL RESPONSE
        return response_text

    def _call_llm_api(self, history: List[Dict[str, str]]) -> str:
        """Execute frontier LLM API call using active context history."""
        try:
            if self.provider_type == "gemini":
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                # Format contents for Google GenAI SDK
                formatted_contents = []
                for msg in history:
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=formatted_contents,
                    config={"system_instruction": self.system_instruction} if self.system_instruction else None
                )
                return response.text.strip()

            elif self.provider_type == "openai":
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                messages = []
                if self.system_instruction:
                    messages.append({"role": "system", "content": self.system_instruction})
                
                for msg in history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["content"]})

                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                return response.choices[0].message.content.strip()

            else:
                # Mock LLM Provider Execution
                return self.client.generate_response(history, self.system_instruction)

        except Exception as e:
            logger.error(f"LLM API Error during generation: {e}")
            raise RuntimeError(f"LLM Provider Generation Error ({self.provider_type}): {str(e)}")

    def get_memory_snapshot(self) -> List[Dict[str, str]]:
        """Return raw snapshot of current stateful memory array."""
        return self.memory.get_history()

    def clear_memory(self) -> None:
        """Reset stateful memory array."""
        self.memory.clear()
