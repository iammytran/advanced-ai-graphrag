"""Example usage of the RAG Chatbot"""
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.chatbot import RAGChatbot
from src.vector_db import VectorDBManager
from langchain_core.documents import Document
from config.config import VECTOR_DB_PATH


def setup_sample_documents():
    """Setup sample documents in the vector store"""
    print("\n📖 Setting up sample documents...")

    # Create sample documents with doc_id
    sample_docs = [
        Document(
            page_content="Python is a high-level, interpreted programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            metadata={"doc_id": "python_001", "source": "python_guide", "type": "general"},
        ),
        Document(
            page_content="Machine Learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data and make predictions.",
            metadata={"doc_id": "ml_001", "source": "ml_guide", "type": "definition"},
        ),
        Document(
            page_content="LangChain is a framework for developing applications powered by language models. It provides tools and abstractions for working with LLMs, including prompt management, memory, and chains.",
            metadata={"doc_id": "langchain_001", "source": "langchain_docs", "type": "framework"},
        ),
        Document(
            page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs. It allows you to define complex workflows using a graph-based approach with nodes and edges.",
            metadata={"doc_id": "langgraph_001", "source": "langgraph_docs", "type": "framework"},
        ),
        Document(
            page_content="RAG (Retrieval-Augmented Generation) is a technique that combines information retrieval with generative models. It retrieves relevant documents first, then uses them as context for generating more accurate and informed responses.",
            metadata={"doc_id": "rag_001", "source": "rag_guide", "type": "technique"},
        ),
    ]

    # Add documents to vector store
    db = VectorDBManager()
    db.add_documents(sample_docs)

    print(f"✓ Loaded {len(sample_docs)} sample documents")
    print(f"   Vector Store Info: {db.get_store_info()}")

    return db


def main():
    """Main function to demonstrate the RAG Chatbot"""

    # Setup sample documents
    db = setup_sample_documents()

    # Initialize chatbot
    print("\n🤖 Initializing RAG Chatbot...")
    chatbot = RAGChatbot()

    # Example questions
    questions = [
        "What is Python and what are its main features?",
        "Explain machine learning and how it works",
        "What is the difference between LangChain and LangGraph?",
        "How does RAG work and what are its benefits?",
    ]

    # Run chatbot on questions
    results = []
    for question in questions:
        result = chatbot.run(question)
        results.append(result)

        # Print the result
        print(f"\n📊 RESULT:")
        print(f"Question: {result['question']}")
        print(f"Answer: {result['answer']}")
        print(f"Documents Used: {result['documents_used']}")
        if result.get("evaluation"):
            print(f"Quality Score: {result['evaluation'].get('overall_score', 'N/A'):.2f}")

    # Print summary
    print("\n" + "=" * 60)
    print("📈 SESSION SUMMARY")
    print("=" * 60)
    print(f"Total questions processed: {len(results)}")
    avg_quality = (
        sum(
            [
                r.get("evaluation", {}).get("overall_score", 0)
                for r in results
            ]
        )
        / len(results)
        if results
        else 0
    )
    print(f"Average quality score: {avg_quality:.2f}")

    # Display conversation history
    display_conversation_history(chatbot)

    # Save conversation
    print("\n💾 Saving conversation history...")
    json_file = chatbot.save_conversation("example_session")
    text_file = chatbot.save_conversation_text("example_session")
    print(f"✓ Saved conversation to:\n  - {json_file}\n  - {text_file}")

    return results


def display_conversation_history(chatbot):
    """Display conversation history and statistics"""
    print("\n" + "=" * 60)
    print("📜 CONVERSATION HISTORY")
    print("=" * 60)

    # Print conversation
    chatbot.print_conversation()

    # Print statistics
    stats = chatbot.get_conversation_statistics()
    print("\n" + "=" * 60)
    print("📊 CONVERSATION STATISTICS")
    print("=" * 60)
    print(f"Total Messages: {stats['total_messages']}")
    print(f"User Questions: {stats['user_messages']}")
    print(f"Assistant Answers: {stats['assistant_messages']}")
    print(f"Total Documents Used: {stats['total_documents_used']}")
    print(f"Avg Documents/Answer: {stats['average_documents_per_answer']:.2f}")
    print(f"High Quality Answers: {stats['high_quality_answers']}")
    print(f"Quality Rate: {stats['quality_rate']:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
