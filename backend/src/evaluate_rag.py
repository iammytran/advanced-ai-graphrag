"""
Evaluation script for RAG Chatbot using LangSmith.
Code adapted from LangChain LangSmith tutorials.
"""

import os
import sys
import json
from typing import TypedDict, Optional, List, Any
from typing_extensions import Annotated
from langsmith import Client, traceable
from langchain_core.documents import Document

# Import LLMs
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.chatbot import RAGChatbot
from config.config import LLM_MODEL, USE_GEMINI, GOOGLE_API_KEY, OPENAI_API_KEY

# Mute warnings
import warnings
warnings.filterwarnings("ignore")

# Initialize Chatbot
chatbot = RAGChatbot()

def get_judge_llm():
    """Get the LLM to use for evaluation (Judge)"""
    # Prefer OpenAI for evaluation if available, as it's the standard for 'LLM-as-a-Judge'
    if OPENAI_API_KEY:
        return ChatOpenAI(model="gpt-4-0125-preview", temperature=0)
    
    # Fallback to Gemini if configured
    if USE_GEMINI and GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
        
    raise ValueError("No API key found for evaluation. Please set OPENAI_API_KEY or GOOGLE_API_KEY.")

# --- Evaluator Definitions ---

# 1. Correctness Evaluator
class CorrectnessGrade(TypedDict):
    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    correct: Annotated[bool, ..., "True if the answer is correct, False otherwise."]

correctness_instructions = """You are a teacher grading a quiz. You will be given a QUESTION, the GROUND TRUTH (correct) ANSWER, and the STUDENT ANSWER. Here is the grade criteria to follow:
(1) Grade the student answers based ONLY on their factual accuracy relative to the ground truth answer. (2) Ensure that the student answer does not contain any conflicting statements.
(3) It is OK if the student answer contains more information than the ground truth answer, as long as it is factually accurate relative to the  ground truth answer.

Correctness:
A correctness value of True means that the student's answer meets all of the criteria.
A correctness value of False means that the student's answer does not meet all of the criteria.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""

def correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """An evaluator for RAG answer accuracy"""
    llm = get_judge_llm().with_structured_output(CorrectnessGrade, method="json_schema", strict=False) # strict=False for broader compatibility
    
    answers = f"""\
QUESTION: {inputs['question']}
GROUND TRUTH ANSWER: {reference_outputs['answer']}
STUDENT ANSWER: {outputs['answer']}"""
    
    grade = llm.invoke([
            {"role": "system", "content": correctness_instructions},
            {"role": "user", "content": answers},
        ]
    )
    return grade["correct"]

# 2. Relevance Evaluator
class RelevanceGrade(TypedDict):
    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    relevant: Annotated[
        bool, ..., "Provide the score on whether the answer addresses the question"
    ]

relevance_instructions = """You are a teacher grading a quiz. You will be given a QUESTION and a STUDENT ANSWER. Here is the grade criteria to follow:
(1) Ensure the STUDENT ANSWER is concise and relevant to the QUESTION
(2) Ensure the STUDENT ANSWER helps to answer the QUESTION

Relevance:
A relevance value of True means that the student's answer meets all of the criteria.
A relevance value of False means that the student's answer does not meet all of the criteria.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""

def relevance(inputs: dict, outputs: dict) -> bool:
    """A simple evaluator for RAG answer helpfulness."""
    llm = get_judge_llm().with_structured_output(RelevanceGrade, method="json_schema", strict=False)
    
    answer = f"QUESTION: {inputs['question']}\nSTUDENT ANSWER: {outputs['answer']}"
    grade = llm.invoke([
            {"role": "system", "content": relevance_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["relevant"]

# 3. Groundedness Evaluator
class GroundedGrade(TypedDict):
    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    grounded: Annotated[
        bool, ..., "Provide the score on if the answer hallucinates from the documents"
    ]

grounded_instructions = """You are a teacher grading a quiz. You will be given FACTS and a STUDENT ANSWER. Here is the grade criteria to follow:
(1) Ensure the STUDENT ANSWER is grounded in the FACTS. (2) Ensure the STUDENT ANSWER does not contain "hallucinated" information outside the scope of the FACTS.

Grounded:
A grounded value of True means that the student's answer meets all of the criteria.
A grounded value of False means that the student's answer does not meet all of the criteria.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""

def groundedness(inputs: dict, outputs: dict) -> bool:
    """A simple evaluator for RAG answer groundedness."""
    llm = get_judge_llm().with_structured_output(GroundedGrade, method="json_schema", strict=False)
    
    # Ensure documents are available and valid
    docs = outputs.get("documents", [])
    if not docs:
        return False # No documents -> Not grounded (or trivial)
        
    doc_string = "\n\n".join(doc.page_content for doc in docs)
    answer = f"FACTS: {doc_string}\nSTUDENT ANSWER: {outputs['answer']}"
    
    grade = llm.invoke([
            {"role": "system", "content": grounded_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["grounded"]

# 4. Retrieval Relevance Evaluator
class RetrievalRelevanceGrade(TypedDict):
    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    relevant: Annotated[
        bool,
        ...,
        "True if the retrieved documents are relevant to the question, False otherwise",
    ]

retrieval_relevance_instructions = """You are a teacher grading a quiz. You will be given a QUESTION and a set of FACTS provided by the student. Here is the grade criteria to follow:
(1) You goal is to identify FACTS that are completely unrelated to the QUESTION
(2) If the facts contain ANY keywords or semantic meaning related to the question, consider them relevant
(3) It is OK if the facts have SOME information that is unrelated to the question as long as (2) is met

Relevance:
A relevance value of True means that the FACTS contain ANY keywords or semantic meaning related to the QUESTION and are therefore relevant.
A relevance value of False means that the FACTS are completely unrelated to the QUESTION.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""

def retrieval_relevance(inputs: dict, outputs: dict) -> bool:
    """An evaluator for document relevance"""
    llm = get_judge_llm().with_structured_output(RetrievalRelevanceGrade, method="json_schema", strict=False)
    
    docs = outputs.get("documents", [])
    if not docs:
         return False

    doc_string = "\n\n".join(doc.page_content for doc in docs)
    answer = f"FACTS: {doc_string}\nQUESTION: {inputs['question']}"
    
    grade = llm.invoke([
            {"role": "system", "content": retrieval_relevance_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["relevant"]

# --- Target Function and Main Execution ---

@traceable()
def target(inputs: dict) -> dict:
    """Run the RAG Chatbot"""
    # The chatbot.run() method returns the final state dict
    result = chatbot.run(inputs["question"])
    return {
        "answer": result["answer"],
        # Ensure we pass the list of Document objects
        "documents": result["retrieved_documents"]
    }

def main():
    # Helper to load data
    dataset_path = os.path.join("data", "evaluation_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Initialize Client
    client = Client()
    dataset_name = "RAG_Eval_Dataset"

    # Create dataset if it doesn't exist
    if not client.has_dataset(dataset_name=dataset_name):
        print(f"Creating dataset '{dataset_name}'...")
        dataset = client.create_dataset(dataset_name=dataset_name)
        
        examples = []
        for item in raw_data:
            client.create_example(
                inputs={"question": item["question"]},
                outputs={"answer": item["expected_answer"]},
                dataset_id=dataset.id
            )
    else:
        print(f"Using existing dataset '{dataset_name}'")

    # Run Evaluation
    print(f"Starting evaluation with judges using {get_judge_llm().model_name}...")
    
    experiment_results = client.evaluate(
        target,
        data=dataset_name,
        evaluators=[correctness, groundedness, relevance, retrieval_relevance],
        experiment_prefix="rag-chatbot",
        metadata={
            "description": "RAG Chatbot Evaluation",
            "llm_model": LLM_MODEL,
        },
    )

    print("\nEvaluation Complete!")
    print(f"View results at: {experiment_results.url}")

if __name__ == "__main__":
    main()
