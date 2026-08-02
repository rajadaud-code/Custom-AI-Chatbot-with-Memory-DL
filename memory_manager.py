"""
Memory Manager Module - Custom AI Chatbot with Memory
======================================================
Author: Senior AI Architect (Decode Lab)

This module implements two core architectural components:
1. Structural Validation Gate: Intercepts user inputs before sending to the LLM
   to block empty or whitespace-only payloads (preventing 400 Bad Request errors).
2. Sliding Window Memory Engine: First-In-First-Out (FIFO) dynamic array management
   that caps context length to protect against token window exhaustion.
"""

from typing import List, Dict, Any, Optional
import logging

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MemoryManager")


class ValidationError(ValueError):
    """Custom exception raised when user input fails structural validation."""
    pass


def validate_user_input(user_input: Any) -> str:
    """
    STRUCTURAL VALIDATION GATE
    --------------------------
    Intercepts the user input prior to LLM API invocation.
    Guards against:
    - Non-string types
    - None / Null inputs
    - Empty strings ("")
    - Whitespace-only payloads ("   \n\t")

    Raises:
        ValidationError: If input is invalid or whitespace-only.

    Returns:
        str: Sanitized, trimmed string payload ready for processing.
    """
    if user_input is None:
        raise ValidationError("Validation Gate Error: Input payload cannot be None.")

    if not isinstance(user_input, str):
        raise ValidationError(f"Validation Gate Error: Input payload must be string, got {type(user_input).__name__}.")

    sanitized = user_input.strip()
    if not sanitized:
        raise ValidationError(
            "Validation Gate Error: Input payload is empty or contains only whitespace. "
            "Intercepted prior to API call to prevent HTTP 400 Bad Request."
        )

    return sanitized


class SlidingWindowMemory:
    """
    SLIDING WINDOW ALGORITHM (FIFO CONTEXT MANAGER)
    -----------------------------------------------
    Maintains an active in-memory list of conversation history entries.
    Enforces a strict First-In-First-Out (FIFO) dynamic truncation logic
    to preserve rolling window context while protecting against token limit breaches.
    """

    def __init__(self, max_messages: int = 10, system_instruction: Optional[str] = None):
        """
        Initialize the Sliding Window Memory structure.

        Args:
            max_messages (int): Maximum allowed conversation turn entries (default: 10 messages / 5 pairs).
            system_instruction (Optional[str]): Optional immutable system prompt preserved across sliding window drops.
        """
        if max_messages < 2:
            raise ValueError("max_messages capacity must be at least 2 (1 pair).")

        self.max_messages = max_messages
        self.system_instruction = system_instruction
        self._history: List[Dict[str, str]] = []
        self._dropped_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        """
        Append a validated message to the memory array and trigger FIFO sliding window check.

        Args:
            role (str): 'user', 'model', or 'assistant'
            content (str): Text message content
        """
        # Normalize role representations across SDK standards
        normalized_role = "model" if role in ("model", "assistant") else "user"
        
        message_entry = {"role": normalized_role, "content": content}
        self._history.append(message_entry)
        
        logger.debug(f"Added message: [{normalized_role}] {content[:40]}...")
        
        # Trigger dynamic FIFO truncation gate
        self._apply_sliding_window()

    def _apply_sliding_window(self) -> None:
        """
        DYNAMIC SLIDING WINDOW TRUNCATION ALGORITHM
        -------------------------------------------
        Monitors the array size. If history length exceeds `max_messages`,
        it dynamically drops the oldest message pairs (User + Model) to keep
        the conversation balanced and preserve complete turns.
        """
        while len(self._history) > self.max_messages:
            # Ensure we drop in pairs to keep User-Model conversational symmetry intact
            if len(self._history) >= 2 and self._history[0]["role"] == "user" and self._history[1]["role"] in ("model", "assistant"):
                dropped_user = self._history.pop(0)
                dropped_model = self._history.pop(0)
                self._dropped_count += 2
                logger.info(
                    f"[SLIDING WINDOW TRUNCATED] Dropped oldest pair: "
                    f"User('{dropped_user['content'][:25]}...') & Model('{dropped_model['content'][:25]}...'). "
                    f"Current Memory Size: {len(self._history)}/{self.max_messages}"
                )
            else:
                # Fallback single drop if history structure is non-paired
                dropped = self._history.pop(0)
                self._dropped_count += 1
                logger.info(f"[SLIDING WINDOW TRUNCATED] Dropped single message: [{dropped['role']}] '{dropped['content'][:25]}...'")

    def get_history(self) -> List[Dict[str, str]]:
        """Return a copy of the active in-memory rolling context window array."""
        return list(self._history)

    def clear(self) -> None:
        """Clear all active conversation history."""
        self._history.clear()
        self._dropped_count = 0
        logger.info("Memory history cleared.")

    @property
    def size(self) -> int:
        """Return current number of messages in memory."""
        return len(self._history)

    @property
    def dropped_count(self) -> int:
        """Return total number of message entries dropped by sliding window algorithm."""
        return self._dropped_count

    def get_summary(self) -> Dict[str, Any]:
        """Return state summary of the memory manager."""
        return {
            "current_message_count": len(self._history),
            "max_capacity": self.max_messages,
            "total_dropped_messages": self._dropped_count,
            "has_system_instruction": self.system_instruction is not None
        }
