"""
Enterprise Database Persistence Module - Custom AI Chatbot with Memory
======================================================================
Author: Senior AI Architect (Techling Private Limited)

BONUS / ENTERPRISE ARCHITECTURE
-------------------------------
Demonstrates enterprise-grade relational database persistence for scaling local RAM memory arrays
to distributed microservice clusters. Uses PostgreSQL with session_id (UUIDv4 Primary Key)
and message payloads stored in indexed JSONB columns.
"""

import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("DBPersistence")

# PostgreSQL Schema DDL Definition
CREATE_TABLES_SQL = """
-- PostgreSQL Enterprise Chatbot Memory Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: Chat Sessions Index
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Table 2: Stateful Conversation Memory Snapshots & Messages
CREATE TABLE IF NOT EXISTS chat_memory_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    messages JSONB NOT NULL, -- Full active sliding window history array stored as JSONB
    message_count INTEGER NOT NULL,
    persisted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for high-performance GIN query execution on JSONB content
CREATE INDEX IF NOT EXISTS idx_chat_memory_jsonb ON chat_memory_snapshots USING gin (messages);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
"""


class PostgresMemoryStore:
    """
    ENTERPRISE POSTGRESQL PERSISTENCE STORE
    ---------------------------------------
    Provides CRUD operations to persist in-memory Sliding Window RAM history
    to PostgreSQL using UUID session identifiers and JSONB payload storage.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database store.

        Args:
            connection_string (Optional[str]): PostgreSQL DSN (e.g. postgresql://user:pass@localhost:5432/dbname).
        """
        self.dsn = connection_string or os.getenv("POSTGRES_URI")
        self._is_connected = False
        self._mock_db_store: Dict[str, Dict[str, Any]] = {}

        if self.dsn:
            self._attempt_connection()

    def _attempt_connection(self):
        """Attempt to establish live connection to PostgreSQL instance."""
        try:
            import psycopg2
            self.conn = psycopg2.connect(self.dsn)
            self._is_connected = True
            logger.info("Successfully connected to enterprise PostgreSQL database.")
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Operating in Simulated DB Persistence Mode.")
            self._is_connected = False

    def init_schema(self) -> bool:
        """Initialize PostgreSQL table schemas and JSONB GIN indices."""
        if not self._is_connected:
            logger.info("[ENTERPRISE ARCHITECTURE DEMO] Mock Schema Initialized: chat_sessions & chat_memory_snapshots tables created.")
            return True

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(CREATE_TABLES_SQL)
                self.conn.commit()
            logger.info("PostgreSQL enterprise schema initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error initializing DB schema: {e}")
            return False

    def save_session_memory(self, session_id: str, memory_history: List[Dict[str, str]], user_id: str = "default_user") -> bool:
        """
        PERSIST IN-MEMORY RAM ARRAY TO POSTGRESQL (JSONB)
        -------------------------------------------------
        Serializes local sliding window history list into a JSONB column associated with a UUID session_id.

        Args:
            session_id (str): Valid UUID string representing unique user chat session.
            memory_history (List[Dict[str, str]]): In-memory conversation array from SlidingWindowMemory.
            user_id (str): Identifier of user owning the session.

        Returns:
            bool: True if persistence succeeded.
        """
        # Validate UUID format
        try:
            valid_uuid = str(uuid.UUID(session_id))
        except ValueError:
            raise ValueError(f"Invalid session_id format: '{session_id}'. Must be a valid UUIDv4 string.")

        jsonb_payload = json.dumps(memory_history)

        if not self._is_connected:
            # Simulated DB Persistence for testing/demonstration without active Postgres container
            self._mock_db_store[valid_uuid] = {
                "session_id": valid_uuid,
                "user_id": user_id,
                "messages_jsonb": jsonb_payload,
                "message_count": len(memory_history),
                "updated_at": datetime.utcnow().isoformat()
            }
            logger.info(
                f"[POSTGRES JSONB PERSISTENCE - MOCK MODE] Successfully persisted Session ID '{valid_uuid[:8]}...' "
                f"with {len(memory_history)} messages into JSONB column."
            )
            return True

        try:
            sql = """
            INSERT INTO chat_sessions (session_id, user_id, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP;

            INSERT INTO chat_memory_snapshots (session_id, messages, message_count)
            VALUES (%s, %s::jsonb, %s);
            """
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (valid_uuid, user_id, valid_uuid, jsonb_payload, len(memory_history)))
                self.conn.commit()

            logger.info(f"Persisted session memory to Postgres JSONB for Session ID: {valid_uuid}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist session memory to PostgreSQL: {e}")
            return False

    def load_session_memory(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """
        RESTORE MEMORY FROM POSTGRESQL JSONB TO RAM ARRAY
        -------------------------------------------------
        Queries the database for the latest JSONB memory payload for a given session UUID
        and deserializes it back into an active Python list for `SlidingWindowMemory`.

        Args:
            session_id (str): Session UUID string.

        Returns:
            Optional[List[Dict[str, str]]]: Deserialized memory history array or None.
        """
        try:
            valid_uuid = str(uuid.UUID(session_id))
        except ValueError:
            raise ValueError(f"Invalid session_id format: '{session_id}'. Must be valid UUIDv4.")

        if not self._is_connected:
            if valid_uuid in self._mock_db_store:
                record = self._mock_db_store[valid_uuid]
                deserialized = json.loads(record["messages_jsonb"])
                logger.info(
                    f"[POSTGRES JSONB LOAD - MOCK MODE] Retrieved Session ID '{valid_uuid[:8]}...' "
                    f"from DB with {len(deserialized)} messages."
                )
                return deserialized
            logger.warning(f"[POSTGRES MOCK DB] No session records found for UUID: {valid_uuid}")
            return None

        try:
            sql = """
            SELECT messages FROM chat_memory_snapshots
            WHERE session_id = %s
            ORDER BY persisted_at DESC LIMIT 1;
            """
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (valid_uuid,))
                row = cursor.fetchone()
                if row:
                    messages_jsonb = row[0]
                    return messages_jsonb if isinstance(messages_jsonb, list) else json.loads(messages_jsonb)
            return None
        except Exception as e:
            logger.error(f"Failed to load session memory from PostgreSQL: {e}")
            return None


def demonstrate_enterprise_persistence(session_id: Optional[str] = None, memory_snapshot: Optional[List[Dict[str, str]]] = None):
    """
    Standalone enterprise persistence demonstration helper.
    Shows complete workflow of generating UUID, saving RAM array to JSONB, and reloading.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    if memory_snapshot is None:
        memory_snapshot = [
            {"role": "user", "content": "My name is Vipin"},
            {"role": "model", "content": "Hello Vipin! Nice to meet you."},
            {"role": "user", "content": "I work at Techling Private Limited."},
            {"role": "model", "content": "Understood! Techling is an awesome tech company."}
        ]

    db_store = PostgresMemoryStore()
    db_store.init_schema()

    logger.info(f"\n--- Demonstrating Enterprise Database Persistence ---")
    logger.info(f"Target Session UUID: {session_id}")

    # 1. Persist RAM array to PostgreSQL JSONB
    success = db_store.save_session_memory(session_id=session_id, memory_history=memory_snapshot)

    # 2. Retrieve & restore session from DB back into RAM structure
    restored_memory = db_store.load_session_memory(session_id=session_id)

    logger.info(f"Restored Memory Match Verification: {restored_memory == memory_snapshot}")
    return {
        "session_id": session_id,
        "persisted": success,
        "restored_count": len(restored_memory) if restored_memory else 0,
        "restored_data": restored_memory
    }
