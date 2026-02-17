"""Conversation History Manager"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langchain.messages import AIMessage, HumanMessage, SystemMessage


class ConversationHistoryManager:
    """Manages conversation history storage and retrieval"""

    def __init__(self, history_dir: str = "./data/conversation_history"):
        """Initialize the history manager

        Args:
            history_dir: Directory to store conversation history files
        """
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        self.conversation_history: List[Dict[str, Any]] = []

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ):
        """Add a message to the conversation history

        Args:
            role: Role of the sender (user, assistant, system)
            content: Content of the message
            metadata: Additional metadata about the message
        """
        # Create LangChain message objects
        if role.lower() == "user":
            message_obj = HumanMessage(content=content)
        elif role.lower() == "assistant":
            message_obj = AIMessage(content=content)
        elif role.lower() == "system":
            message_obj = SystemMessage(content=content)
        else:
            message_obj = HumanMessage(content=content)

        # Store as dictionary with LangChain message and metadata
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "message_obj": message_obj,
            "metadata": metadata or {},
        }
        self.conversation_history.append(message)

    def add_turn(
        self,
        question: str,
        answer: str,
        documents_used: int = 0,
        evaluation: Dict[str, Any] = None,
    ):
        """Add a complete turn (question + answer) to history

        Args:
            question: User's question
            answer: Assistant's answer
            documents_used: Number of documents used for retrieval
            evaluation: Evaluation metrics for the answer
        """
        self.add_message(
            role="user",
            content=question,
            metadata={"type": "question"},
        )

        self.add_message(
            role="assistant",
            content=answer,
            metadata={
                "type": "answer",
                "documents_used": documents_used,
                "evaluation": evaluation,
            },
        )

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the entire conversation history

        Returns:
            List of message dictionaries
        """
        return self.conversation_history

    def get_langchain_messages(self) -> List:
        """Get conversation history as LangChain message objects

        Returns:
            List of LangChain message objects (HumanMessage, AIMessage, SystemMessage)
        """
        return [
            msg.get("message_obj")
            for msg in self.conversation_history
            if "message_obj" in msg
        ]

    def get_context(self, max_messages: int = 10) -> str:
        """Get conversation context as a formatted string

        Args:
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted conversation context
        """
        recent_messages = self.conversation_history[-max_messages:]
        context_lines = []

        for msg in recent_messages:
            role = msg["role"].upper()
            content = msg["content"][:100]  # Truncate long content
            context_lines.append(f"{role}: {content}")

        return "\n".join(context_lines)

    def save_to_file(self, filename: str = None) -> str:
        """Save conversation history to a JSON file

        Args:
            filename: Name of the file (without extension)
                     If None, uses timestamp

        Returns:
            Path to the saved file
        """
        if filename is None:
            filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        filepath = os.path.join(self.history_dir, f"{filename}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "created_at": datetime.now().isoformat(),
                    "message_count": len(self.conversation_history),
                    "messages": self.conversation_history,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✓ Conversation saved to {filepath}")
        return filepath

    def save_to_text(self, filename: str = None) -> str:
        """Save conversation history as a readable text file

        Args:
            filename: Name of the file (without extension)

        Returns:
            Path to the saved file
        """
        if filename is None:
            filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        filepath = os.path.join(self.history_dir, f"{filename}.txt")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"CONVERSATION HISTORY\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Messages: {len(self.conversation_history)}\n")
            f.write("=" * 70 + "\n\n")

            for i, msg in enumerate(self.conversation_history, 1):
                timestamp = msg.get("timestamp", "N/A")
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                metadata = msg.get("metadata", {})

                f.write(f"[{i}] {role} (at {timestamp})\n")
                f.write(f"{content}\n")

                if metadata:
                    f.write(f"Metadata: {json.dumps(metadata, ensure_ascii=False)}\n")

                f.write("-" * 70 + "\n\n")

        print(f"✓ Conversation saved to {filepath}")
        return filepath

    def load_from_file(self, filepath: str) -> bool:
        """Load conversation history from a JSON file

        Args:
            filepath: Path to the JSON file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.conversation_history = data.get("messages", [])
                print(
                    f"✓ Loaded {len(self.conversation_history)} messages from {filepath}"
                )
                return True
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            return False

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        print("✓ Conversation history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the conversation

        Returns:
            Dictionary with conversation statistics
        """
        user_messages = [m for m in self.conversation_history if m["role"] == "user"]
        assistant_messages = [
            m for m in self.conversation_history if m["role"] == "assistant"
        ]

        total_docs_used = 0
        high_quality_answers = 0

        for msg in assistant_messages:
            metadata = msg.get("metadata", {})
            total_docs_used += metadata.get("documents_used", 0)
            if metadata.get("evaluation"):
                if metadata["evaluation"].get("is_high_quality", False):
                    high_quality_answers += 1

        avg_doc_per_answer = (
            total_docs_used / len(assistant_messages) if assistant_messages else 0
        )

        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_documents_used": total_docs_used,
            "average_documents_per_answer": avg_doc_per_answer,
            "high_quality_answers": high_quality_answers,
            "quality_rate": (
                (high_quality_answers / len(assistant_messages) * 100)
                if assistant_messages
                else 0
            ),
        }

    def print_history(self, max_messages: int = None):
        """Print the conversation history in a readable format

        Args:
            max_messages: Maximum number of messages to print
        """
        messages = (
            self.conversation_history[-max_messages:]
            if max_messages
            else self.conversation_history
        )

        print("\n" + "=" * 70)
        print("CONVERSATION HISTORY")
        print("=" * 70)

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "N/A")

            print(f"\n[{i}] {role} ({timestamp})")
            print(f"{content}")

            metadata = msg.get("metadata", {})
            # if metadata and "documents_used" in metadata:
            #     print(f"Documents used: {metadata['documents_used']}")

            # if metadata and metadata.get("evaluation"):
            #     eval_data = metadata["evaluation"]
            #     print(
            #         f"Quality Score: {eval_data.get('overall_score', 'N/A'):.2f}"
            #     )

        print("\n" + "=" * 70)
