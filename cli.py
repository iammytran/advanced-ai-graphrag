"""Interactive CLI for the RAG Chatbot"""
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.chatbot import RAGChatbot
from src.vector_db import VectorDBManager
from langchain_core.documents import Document


def load_initial_documents():
    """Load initial documents if vector store is empty"""
    db = VectorDBManager()
    store_info = db.get_store_info()

    if store_info.get("document_count", 0) == 0:
        print("\n⚠️  Vector store is empty. Loading sample documents...")

        sample_docs = [
            Document(
                page_content="Python is a high-level, interpreted programming language known for its simplicity and readability.",
                metadata={"doc_id": "python_001", "source": "python_guide"},
            ),
            Document(
                page_content="Machine Learning enables systems to learn from experience without explicit programming.",
                metadata={"doc_id": "ml_001", "source": "ml_guide"},
            ),
            Document(
                page_content="LangChain is a framework for developing applications powered by language models.",
                metadata={"doc_id": "langchain_001", "source": "langchain_docs"},
            ),
            Document(
                page_content="LangGraph allows building stateful applications with LLMs using a graph-based approach.",
                metadata={"doc_id": "langgraph_001", "source": "langgraph_docs"},
            ),
            Document(
                page_content="RAG combines information retrieval with generative models for better accuracy.",
                metadata={"doc_id": "rag_001", "source": "rag_guide"},
            ),
        ]

        db.add_documents(sample_docs)
        print(f"✓ Loaded {len(sample_docs)} documents")

    return db


def main():
    """Interactive CLI main function"""
    print("\n" + "=" * 60)
    print("🤖 RAG CHATBOT - INTERACTIVE CLI")
    print("=" * 60)

    # Load documents
    db = load_initial_documents()
    info = db.get_store_info()
    print(f"\n📚 Vector Store Status: {info['document_count']} documents loaded")

    # Initialize chatbot
    print("\n✅ Chatbot ready!")
    print("Type 'exit' or 'quit' to stop")
    print("Type 'help' for available commands")
    print("-" * 60)

    chatbot = RAGChatbot()

    while True:
        try:
            question = input("\n❓ Your question: ").strip()

            if not question:
                print("⚠️  Please enter a question")
                continue

            if question.lower() in ["exit", "quit"]:
                # Ask to save history
                save = input("\n💾 Save conversation history before exiting? (y/n): ").strip().lower()
                if save == 'y':
                    json_file = chatbot.save_conversation()
                    text_file = chatbot.save_conversation_text()
                    print(f"✓ Saved to:\n  - {json_file}\n  - {text_file}")
                print("\n👋 Goodbye!")
                break

            if question.lower() == "help":
                print("\n📖 AVAILABLE COMMANDS:")
                print("  exit/quit    - Exit and optionally save history")
                print("  help         - Show this help message")
                print("  history      - Show conversation history")
                print("  stats        - Show conversation statistics")
                print("  save         - Save conversation to file")
                print("  clear        - Clear conversation history")
                print("  Or just type your question")
                continue

            if question.lower() == "history":
                chatbot.print_conversation()
                continue

            if question.lower() == "stats":
                stats = chatbot.get_conversation_statistics()
                print("\n📊 CONVERSATION STATISTICS:")
                print(f"  Total Messages: {stats['total_messages']}")
                print(f"  User Questions: {stats['user_messages']}")
                print(f"  Assistant Answers: {stats['assistant_messages']}")
                print(f"  Total Documents Used: {stats['total_documents_used']}")
                print(f"  Avg Documents/Answer: {stats['average_documents_per_answer']:.2f}")
                print(f"  High Quality Answers: {stats['high_quality_answers']}")
                print(f"  Quality Rate: {stats['quality_rate']:.1f}%")
                continue

            if question.lower() == "save":
                json_file = chatbot.save_conversation()
                text_file = chatbot.save_conversation_text()
                print(f"✓ Saved to:\n  - {json_file}\n  - {text_file}")
                continue

            if question.lower() == "clear":
                confirm = input("⚠️  Are you sure you want to clear history? (y/n): ").strip().lower()
                if confirm == 'y':
                    chatbot.conversation_history.clear_history()
                continue

            # Run chatbot
            result = chatbot.run(question)

            # Display result
            print("\n" + "=" * 60)
            print("📋 ANSWER:")
            print(result["answer"])
            print("-" * 60)

            if result.get("evaluation"):
                eval_data = result["evaluation"]
                print(f"✅ Quality Assessment:")
                print(
                    f"   Relevance: {eval_data.get('relevance_score', 0):.2f}/1.0"
                )
                print(
                    f"   Accuracy: {eval_data.get('accuracy_score', 0):.2f}/1.0"
                )
                print(
                    f"   Completeness: {eval_data.get('completeness_score', 0):.2f}/1.0"
                )
                print(f"   Overall: {eval_data.get('overall_score', 0):.2f}/1.0")
                print(f"   Feedback: {eval_data.get('feedback', 'N/A')}")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again")


if __name__ == "__main__":
    main()
