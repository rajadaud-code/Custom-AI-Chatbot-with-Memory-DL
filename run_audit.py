"""
System Audit Runner - Custom AI Chatbot with Memory
====================================================
Author: Senior AI Architect (Decode Lab)

SYSTEM AUDIT FUNCTIONALITY & MEMORY EXAM
-----------------------------------------
Executes automated diagnostic tests verifying:
1. Structural Validation Gate (interception of empty/whitespace payloads).
2. 'Memory Exam' (Fact Injection -> Context Distraction -> State Extraction).
3. Sliding Window FIFO dynamic truncation behavior under capacity pressure.
4. Enterprise Database Persistence (UUID session + JSONB storing).
"""

import sys
import os
import uuid
import logging

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from memory_manager import validate_user_input, ValidationError, SlidingWindowMemory
from chatbot import StatefulChatbot
from db_persistence import demonstrate_enterprise_persistence

# Configure clean audit logger output
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("SystemAudit")


def print_banner(title: str):
    """Print visually clean section banner for audit logs."""
    print("\n" + "=" * 75)
    print(f"  {title.upper()}")
    print("=" * 75)


def audit_validation_gate() -> bool:
    """Test 1: Verify Structural Validation Gate blocks empty/whitespace payloads."""
    print_banner("Audit 1: Structural Validation Gate Test")
    
    test_cases = [
        ("", "Empty String"),
        ("   ", "Spaces Only"),
        ("\t\n  \r", "Newlines & Tabs Only"),
        (None, "None Type")
    ]
    
    blocked_count = 0
    for payload, description in test_cases:
        try:
            print(f"Testing invalid input [{description}]: '{payload}'")
            validate_user_input(payload)
            print(f"  [FAIL] Validation Gate failed to intercept [{description}].")
            return False
        except ValidationError as ve:
            blocked_count += 1
            print(f"  [PASSED INTERCEPTION]: {ve}")

    print(f"\n[SUCCESS] Structural Validation Gate PASSED ({blocked_count}/{len(test_cases)} invalid payloads blocked before API call).")
    return True


def audit_memory_exam() -> bool:
    """
    Test 2: Predefined 'Memory Exam' Audit
    --------------------------------------
    Step 1: Fact Injection -> 'My name is Vipin'
    Step 2: Context Distraction -> 'Write a long poem about artificial intelligence'
    Step 3: State Extraction Test -> 'What is my name?'
    """
    print_banner("Audit 2: System Memory Exam (Fact -> Distraction -> Extraction)")

    # Initialize chatbot with max capacity of 10 messages (5 pairs) to easily hold context
    bot = StatefulChatbot(provider="auto", max_memory_messages=10)
    print(f"Chatbot initialized using provider: '{bot.provider_type.upper()}' (Capacity: {bot.memory.max_messages} messages)")

    # STEP 1: FACT INJECTION
    prompt_1 = "My name is Vipin"
    print(f"\n[Turn 1 - Fact Injection] User: '{prompt_1}'")
    resp_1 = bot.send_message(prompt_1)
    print(f"  Model Response: {resp_1}")

    # STEP 2: CONTEXT DISTRACTION
    prompt_2 = "Write a long poem about artificial intelligence"
    print(f"\n[Turn 2 - Context Distraction] User: '{prompt_2}'")
    resp_2 = bot.send_message(prompt_2)
    print(f"  Model Response:\n{resp_2}")

    # STEP 3: STATE EXTRACTION TEST
    prompt_3 = "What is my name?"
    print(f"\n[Turn 3 - State Extraction Test] User: '{prompt_3}'")
    resp_3 = bot.send_message(prompt_3)
    print(f"  Model Response: {resp_3}")

    # VERIFICATION
    is_retained = "Vipin" in resp_3 or "vipin" in resp_3.lower()
    if is_retained:
        print("\n[SUCCESS] MEMORY EXAM PASSED: The bot successfully retained the fact ('Vipin') across distraction turns!")
    else:
        print("\n[FAIL] MEMORY EXAM FAILED: Fact 'Vipin' was not found in response.")

    print(f"Current Memory Array Size: {bot.memory.size} messages")
    return is_retained


def audit_sliding_window_truncation() -> bool:
    """Test 3: Sliding Window FIFO Algorithm Truncation under capacity overflow."""
    print_banner("Audit 3: Sliding Window FIFO Truncation Test")

    # Set tight capacity limit of 4 messages (2 pairs)
    small_memory = SlidingWindowMemory(max_messages=4)
    
    print(f"Initialized Sliding Window with Max Capacity = {small_memory.max_messages} messages (2 turns)")

    # Add 3 conversation turns (6 messages) to trigger FIFO truncation twice
    turns = [
        ("user", "Pair 1 User: Fact A"),
        ("model", "Pair 1 Model: Ack A"),
        ("user", "Pair 2 User: Fact B"),
        ("model", "Pair 2 Model: Ack B"),
        ("user", "Pair 3 User: Fact C"),
        ("model", "Pair 3 Model: Ack C")
    ]

    for role, content in turns:
        small_memory.add_message(role, content)

    active_history = small_memory.get_history()
    dropped_count = small_memory.dropped_count

    print(f"\nFinal Memory Array Count: {small_memory.size}/{small_memory.max_messages}")
    print(f"Total Messages Dropped by FIFO: {dropped_count}")

    # Oldest pair (Pair 1) should have been truncated. Active history must contain Pair 2 & Pair 3.
    retained_contents = [m["content"] for m in active_history]
    has_pair_1 = any("Pair 1" in c for c in retained_contents)
    has_pair_3 = any("Pair 3" in c for c in retained_contents)

    if not has_pair_1 and has_pair_3 and len(active_history) == 4:
        print("\n[SUCCESS] SLIDING WINDOW TRUNCATION PASSED: Oldest message pair (Pair 1) was correctly dropped (FIFO).")
        return True
    else:
        print("\n[FAIL] SLIDING WINDOW TRUNCATION FAILED: History array state inconsistent.")
        return False


def audit_database_persistence() -> bool:
    """Test 4: Enterprise Database Persistence (UUID Session + JSONB Session)."""
    print_banner("Audit 4: Enterprise PostgreSQL Persistence Test")

    session_uuid = str(uuid.uuid4())
    result = demonstrate_enterprise_persistence(session_id=session_uuid)

    if result["persisted"] and result["restored_count"] == 4:
        print("\n[SUCCESS] ENTERPRISE PERSISTENCE PASSED: Memory snapshot serialized to JSONB & deserialized back seamlessly.")
        return True
    else:
        print("\n[FAIL] ENTERPRISE PERSISTENCE FAILED.")
        return False


def main():
    """Run all System Audits."""
    print("\n" + "#" * 75)
    print("      PROJECT 1: CUSTOM AI CHATBOT WITH MEMORY - SYSTEM AUDIT SUITE")
    print("      Decode Lab | Senior AI Architecture Verification")
    print("#" * 75)

    v_gate = audit_validation_gate()
    m_exam = audit_memory_exam()
    s_win = audit_sliding_window_truncation()
    db_pers = audit_database_persistence()

    print_banner("System Audit Final Summary")
    results = [
        ("1. Structural Validation Gate Interceptor", v_gate),
        ("2. System Memory Exam (Retention Test)", m_exam),
        ("3. Sliding Window FIFO Dynamic Truncation", s_win),
        ("4. Enterprise PostgreSQL JSONB Persistence", db_pers)
    ]

    all_passed = True
    for name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"  - {name:<48}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 75)
    if all_passed:
        print("  [SUCCESS] ALL SYSTEM AUDITS PASSED SUCCESSFULLY! ARCHITECTURE IS CERTIFIED.")
        sys.exit(0)
    else:
        print("  [WARNING] SOME AUDIT CHECKS FAILED. PLEASE REVIEW LOGS ABOVE.")
        sys.exit(1)


if __name__ == "__main__":
    main()
