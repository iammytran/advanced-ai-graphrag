"""Evaluation module for assessing answer quality"""

import json
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Dict, List

from config.config import LLM_MODEL, USE_GEMINI
from langchain_core.documents import Document

# Import LLM based on provider
if USE_GEMINI:
    from langchain_google_genai import ChatGoogleGenerativeAI
else:
    from langchain_openai import ChatOpenAI


class EvaluationManager:
    """Manages evaluation of answers using LangChain"""

    def __init__(self, request_delay: float = 1.0):
        """Initialize the Evaluation Manager

        Args:
            request_delay: Delay in seconds between API requests to avoid rate limiting
        """
        self.request_delay = request_delay
        self.last_request_time = 0

        if USE_GEMINI:
            from config.config import GOOGLE_API_KEY

            os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
            self.llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0.0)
        else:
            from config.config import OPENAI_API_KEY

            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            self.llm = ChatOpenAI(model_name=LLM_MODEL, temperature=0.0)

    def _apply_rate_limit(self):
        """Apply rate limiting delay between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            time.sleep(delay)
        self.last_request_time = time.time()

    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from LLM response, removing markdown code blocks"""
        # Remove markdown code blocks (```json ... ```)
        if "```" in content:
            parts = content.split("```")
            # If surrounded by backticks, take middle part
            if len(parts) >= 3:
                json_str = parts[1]
                # Remove 'json' prefix if present
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                return json_str.strip()
            # Try last part if format is different
            return parts[-1].strip()
        return content.strip()

    def evaluate_document(self, question: str, document: Document) -> Dict:
        """
        Evaluate if a single document is relevant to the question

        Args:
            question: User question
            document: Single document to evaluate

        Returns:
            Dictionary with document evaluation metrics
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Apply rate limiting
                self._apply_rate_limit()

                eval_prompt = ChatPromptTemplate.from_template(
                    """Evaluate if the following document is relevant to the question.

Question: {question}

Document Content:
{doc_content}

Provide evaluation in JSON format:
{{
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "key_info": "Key information in this document",
    "relevance_reason": "Why this document is or isn't relevant"
}}"""
                )

                chain = eval_prompt | self.llm
                response = chain.invoke(
                    {"question": question, "doc_content": document.page_content}
                )

                # Extract JSON content and clean markdown
                json_str = self._extract_json_from_response(response.content)
                result = json.loads(json_str)
                return result

            except Exception as e:
                retry_count += 1
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait_time = min(10 * (2**retry_count), 60)  # Exponential backoff
                    print(
                        f"⏳ Rate limited. Waiting {wait_time}s before retry {retry_count}/{max_retries}..."
                    )
                    time.sleep(wait_time)
                else:
                    print(f"Error parsing document evaluation: {e}")
                    return {
                        "is_relevant": True,
                        "relevance_score": 0.5,
                        "key_info": "Could not parse evaluation",
                        "relevance_reason": "Evaluation parsing failed",
                    }

        # If all retries failed
        return {
            "is_relevant": True,
            "relevance_score": 0.5,
            "key_info": "Could not evaluate",
            "relevance_reason": "Max retries exceeded",
        }

    def evaluate_retrieval(self, question: str, documents: List[Document]) -> Dict:
        """
        Evaluate if the retrieved documents are relevant to the question

        Args:
            question: User question
            documents: Retrieved documents

        Returns:
            Dictionary with retrieval evaluation metrics
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Apply rate limiting
                self._apply_rate_limit()

                doc_summary = "\n".join(
                    [
                        f"Doc {i+1}: {doc.page_content[:100]}..."
                        for i, doc in enumerate(documents[:5])
                    ]
                )

                eval_prompt = ChatPromptTemplate.from_template(
                    """Evaluate if the following retrieved documents are relevant to the question.

Question: {question}

Retrieved Documents:
{documents}

Provide evaluation in JSON format:
{{
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "coverage_score": 0.0-1.0,
    "missing_info": "What important information is missing if any",
    "recommendation": "Should we search for more documents?"
}}"""
                )

                chain = eval_prompt | self.llm
                response = chain.invoke(
                    {"question": question, "documents": doc_summary}
                )

                # Extract JSON content and clean markdown
                json_str = self._extract_json_from_response(response.content)
                result = json.loads(json_str)
                return result

            except Exception as e:
                retry_count += 1
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait_time = min(10 * (2**retry_count), 60)  # Exponential backoff
                    print(
                        f"⏳ Rate limited. Waiting {wait_time}s before retry {retry_count}/{max_retries}..."
                    )
                    time.sleep(wait_time)
                else:
                    print(f"Error parsing retrieval evaluation: {e}")
                    return {
                        "is_relevant": True,
                        "relevance_score": 0.5,
                        "coverage_score": 0.5,
                        "missing_info": "Could not parse evaluation",
                        "recommendation": "Manual review needed",
                    }

        # If all retries failed
        return {
            "is_relevant": True,
            "relevance_score": 0.5,
            "coverage_score": 0.5,
            "missing_info": "Max retries exceeded",
            "recommendation": "Manual review needed",
        }
