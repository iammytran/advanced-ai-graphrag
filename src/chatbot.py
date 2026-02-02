"""RAG Chatbot using LangGraph"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.documents import Document
import json

from src.vector_db import VectorDBManager
from src.llm import LLMManager
from src.evaluation import EvaluationManager
from src.conversation_history import ConversationHistoryManager
from config.config import EVALUATION_THRESHOLD, ENABLE_EVALUATION


class ChatbotState(TypedDict):
    """State for the chatbot graph"""

    question: str
    evaluation_result: Dict[str, Any]
    retrieved_documents: List[Document]
    generated_answer: str
    evaluation_metrics: Dict[str, Any]
    final_output: Dict[str, Any]
    conversation_history: 'ConversationHistoryManager'


class RAGChatbot:
    """RAG Chatbot using LangGraph"""

    def __init__(self):
        """Initialize the RAG Chatbot"""
        self.vector_db = VectorDBManager()
        self.llm_manager = LLMManager()
        self.evaluator = EvaluationManager()
        self.conversation_history = ConversationHistoryManager()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(ChatbotState)

        # Add nodes
        workflow.add_node("input", self._input_node)
        workflow.add_node("evaluate_question", self._evaluate_question_node)
        workflow.add_node("retrieve_documents", self._retrieve_documents_node)
        workflow.add_node("generate_answer", self._generate_answer_node)
        workflow.add_node("evaluate_answer", self._evaluate_answer_node)
        workflow.add_node("output", self._output_node)

        # Add edges
        workflow.add_edge(START, "input")
        workflow.add_edge("input", "evaluate_question")
        # After evaluating retrieved documents, branch to generate or output
        workflow.add_conditional_edges(
            "evaluate_question",
            self._should_retrieve_documents,
            {
                "relevant": "generate_answer",
                "not_relevant": "output",
            },
        )

        if ENABLE_EVALUATION:
            workflow.add_edge("generate_answer", "evaluate_answer")
            workflow.add_edge("evaluate_answer", "output")
        else:
            workflow.add_edge("generate_answer", "output")

        workflow.add_edge("output", END)

        return workflow.compile()

    def _input_node(self, state: ChatbotState) -> ChatbotState:
        """Input node - process the question"""
        print(f"\n📝 INPUT: {state['question']}")
        state['conversation_history'].add_message(
            role="user",
            content=state['question'],
            metadata={"type": "question"}
        )
        return state

    def _evaluate_question_node(self, state: ChatbotState) -> ChatbotState:
        """Retrieve top-k documents then evaluate each document's relevance individually"""
        print("\n🔍 RETRIEVING TOP-K DOCUMENTS FOR EVALUATION...")

        # Retrieve documents first
        documents = self.vector_db.retrieve_documents(state["question"])
        all_docs = []
        relevant_docs = []
        eval_results = []

        if documents:
            all_docs = [doc for doc, score in documents]
            print(f"   Retrieved {len(documents)} documents")

            # Evaluate each document individually
            print("\n   Evaluating each document for relevance...")
            for i, doc in enumerate(all_docs, 1):
                doc_eval = self.evaluator.evaluate_document(state["question"], doc)
                eval_results.append({
                    "document": doc,
                    "evaluation": doc_eval
                })

                is_relevant = doc_eval.get("is_relevant", False)
                relevance_score = doc_eval.get("relevance_score", 0.0)

                status = "✓" if is_relevant else "✗"
                print(f"   {status} Doc {i}: {relevance_score:.2f} - {doc.page_content[:60]}...")
                if is_relevant:
                    relevant_docs.append(doc)

            # Store all evaluation results
            state["evaluation_result"] = {
                "total_retrieved": len(all_docs),
                "total_relevant": len(relevant_docs),
                "document_evaluations": eval_results,
                "is_relevant": len(relevant_docs) > 0
            }
            state["retrieved_documents"] = relevant_docs

            print(f"\n   Summary: {len(relevant_docs)}/{len(all_docs)} documents are relevant")
        else:
            state["retrieved_documents"] = []
            state["evaluation_result"] = {
                "total_retrieved": 0,
                "total_relevant": 0,
                "document_evaluations": [],
                "is_relevant": False
            }
            print("   No documents retrieved")

        return state

    def _should_retrieve_documents(self, state: ChatbotState) -> str:
        """Determine whether we have relevant documents to generate answer from"""
        is_relevant = state["evaluation_result"].get("is_relevant", False)
        total_relevant = state["evaluation_result"].get("total_relevant", 0)
        return "relevant" if is_relevant and total_relevant > 0 else "not_relevant"

    def _retrieve_documents_node(self, state: ChatbotState) -> ChatbotState:
        """Retrieve documents from vector DB"""
        print("\n📚 RETRIEVING DOCUMENTS...")
        documents = self.vector_db.retrieve_documents(state["question"])

        if documents:
            state["retrieved_documents"] = [doc for doc, score in documents]
            print(f"   Found {len(documents)} relevant documents")
            for i, (doc, score) in enumerate(documents, 1):
                print(
                    f"   {i}. Score: {score:.3f} - {doc.page_content[:80]}..."
                )
        else:
            state["retrieved_documents"] = []
            print("   No documents found")

        return state

    def _generate_answer_node(self, state: ChatbotState) -> ChatbotState:
        """Generate answer using LLM"""
        print("\n🤖 GENERATING ANSWER...")

        documents = state.get("retrieved_documents", [])
        if documents:
            answer = self.llm_manager.generate_response(
                state["question"], documents
            )
        else:
            # Generate answer without context
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_template(
                "Answer this question: {question}"
            )
            chain = prompt | self.llm_manager.llm
            response = chain.invoke({"question": state["question"]})
            answer = response.content

        state["generated_answer"] = answer
        print(f"   Answer: {answer[:200]}...")

        return state

    def _evaluate_answer_node(self, state: ChatbotState) -> ChatbotState:
        """Evaluate the generated answer"""
        print("\n✅ EVALUATING ANSWER...")

        evaluation = self.evaluator.evaluate_answer(
            state["question"],
            state["generated_answer"],
            state.get("retrieved_documents", []),
        )

        state["evaluation_metrics"] = evaluation

        overall_score = evaluation.get("overall_score", 0.5)
        is_high_quality = evaluation.get("is_high_quality", False)

        print(f"   Overall Score: {overall_score:.2f}")
        print(f"   Quality: {'✓ High' if is_high_quality else '✗ Needs Improvement'}")
        print(f"   Feedback: {evaluation.get('feedback', 'N/A')}")

        return state

    def _output_node(self, state: ChatbotState) -> ChatbotState:
        """Output node - prepare final response"""
        print("\n🎯 FINAL OUTPUT")
        # If there is no generated answer (e.g., retrieval was not relevant),
        # return a safe default and include retrieval evaluation
        answer = state.get("generated_answer") or "I don't know based on available documents."

        # Prefer evaluation_metrics (from answer eval) otherwise include retrieval evaluation
        evaluation = state.get("evaluation_metrics") or state.get("evaluation_result")

        state["final_output"] = {
            "question": state["question"],
            "answer": answer,
            "documents_used": len(state.get("retrieved_documents", [])),
            "evaluation": evaluation,
        }

        # Save to conversation history
        state['conversation_history'].add_message(
            role="assistant",
            content=answer,
            metadata={
                "type": "answer",
                "documents_used": len(state.get("retrieved_documents", [])),
                "evaluation": evaluation,
            }
        )

        return state

    def run(self, question: str) -> Dict[str, Any]:
        """Run the chatbot on a question"""
        print("\n" + "=" * 60)
        print("🚀 RAG CHATBOT WORKFLOW STARTED")
        print("=" * 60)

        initial_state: ChatbotState = {
            "question": question,
            "evaluation_result": {},
            "retrieved_documents": [],
            "generated_answer": "",
            "evaluation_metrics": {},
            "final_output": {},
            "conversation_history": self.conversation_history,
        }

        result = self.workflow.invoke(initial_state)

        print("\n" + "=" * 60)
        print("✅ WORKFLOW COMPLETED")
        print("=" * 60)

        return result["final_output"]

    def save_conversation(self, filename: str = None) -> str:
        """Save conversation history to file
        
        Args:
            filename: Optional filename (without extension)
            
        Returns:
            Path to saved file
        """
        return self.conversation_history.save_to_file(filename)

    def save_conversation_text(self, filename: str = None) -> str:
        """Save conversation history as readable text
        
        Args:
            filename: Optional filename (without extension)
            
        Returns:
            Path to saved file
        """
        return self.conversation_history.save_to_text(filename)

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history
        
        Returns:
            List of messages
        """
        return self.conversation_history.get_history()

    def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get statistics about the conversation
        
        Returns:
            Dictionary with statistics
        """
        return self.conversation_history.get_statistics()

    def print_conversation(self, max_messages: int = None):
        """Print the conversation history
        
        Args:
            max_messages: Maximum number of messages to print
        """
        self.conversation_history.print_history(max_messages)
