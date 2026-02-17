"""Example usage of the RAG Chatbot"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.chatbot import RAGChatbot


def main():
    """Main function to demonstrate the RAG Chatbot"""

    # Setup sample documents
    # db = setup_sample_documents()

    # Initialize chatbot
    print("\n🤖 Initializing RAG Chatbot...")
    chatbot = RAGChatbot()

    # Example questions
    questions = [
        "Đánh bài bị phạt bao nhiêu tiền?",
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
        # print(f"Documents Used: {result.get('documents_used', 'N/A')}")
    # Display conversation history
    display_conversation_history(chatbot)

    # Save conversation
    # print("\n💾 Saving conversation history...")
    # json_file = chatbot.save_conversation("example_session")
    # text_file = chatbot.save_conversation_text("example_session")
    # print(f"✓ Saved conversation to:\n  - {json_file}\n  - {text_file}")

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
