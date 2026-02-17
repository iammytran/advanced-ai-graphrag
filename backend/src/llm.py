"""LLM and Generation modules"""

import os
import time
from typing import Dict, List

from config.config import LLM_MODEL, TEMPERATURE, USE_GEMINI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

# Import LLM based on provider
if USE_GEMINI:
    from langchain_google_genai import ChatGoogleGenerativeAI
else:
    from langchain_openai import ChatOpenAI


class LLMManager:
    """Manages LLM operations"""

    def __init__(self, request_delay: float = 1.0):
        """Initialize the LLM Manager

        Args:
            request_delay: Delay in seconds between API requests to avoid rate limiting
        """
        self.request_delay = request_delay
        self.last_request_time = 0

        if USE_GEMINI:
            from config.config import GOOGLE_API_KEY

            os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
            self.llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=TEMPERATURE)
        else:
            from config.config import OPENAI_API_KEY

            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            self.llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                model_name=LLM_MODEL,
                temperature=TEMPERATURE,
            )

    def _apply_rate_limit(self):
        """Apply rate limiting delay between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            time.sleep(delay)
        self.last_request_time = time.time()

    def generate_response(
        self,
        question: str,
        context_documents: List[Document],
        options: Dict[str, str] = None,
    ) -> str:
        """Generate response based on question and context documents"""
        max_retries = 3
        retry_count = 0
        options = options or {}

        while retry_count < max_retries:
            try:
                # Apply rate limiting
                self._apply_rate_limit()

                # Build system instruction based on options
                system_instruction = "You are a helpful AI assistant."
                if options.get("character"):
                    system_instruction = f"You are a {options['character']}."

                if options.get("toneValue"):
                    tone = options["toneValue"]
                    system_instruction += f" Speak with a tone level of {tone}/100 (where 0 is casual, 100 is formal)."

                prompt_template_str = (
                    system_instruction
                    + """ Use the provided context documents to answer the user's question. Answer in Vietnamese.

Context Documents:
{context}

User Question: {question}

Please provide a comprehensive and accurate answer based on the context. If the context doesn't contain relevant information, let the user know."""
                )

                context_text = "\n\n".join(
                    [
                        f"Document {i+1}:\n{doc.page_content}"
                        for i, doc in enumerate(context_documents)
                    ]
                )

                prompt_template = ChatPromptTemplate.from_template(prompt_template_str)

                chain = prompt_template | self.llm
                response = chain.invoke({"context": context_text, "question": question})

                return response.content

            except Exception as e:
                retry_count += 1
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait_time = min(10 * (2**retry_count), 60)  # Exponential backoff
                    print(
                        f"⏳ Rate limited. Waiting {wait_time}s before retry {retry_count}/{max_retries}..."
                    )
                    time.sleep(wait_time)
                else:
                    print(f"Error generating response: {e}")
                    return "I encountered an error while generating the response. Please try again."

        # If all retries failed
        return "Unable to generate response after multiple attempts. Please try again later."

    def evaluate_question(self, question: str) -> Dict[str, any]:
        """Evaluate if the question needs additional context or can be answered directly"""
        eval_prompt = ChatPromptTemplate.from_template(
            """Analyze the following question and determine if it requires external knowledge/documents to answer properly.

Question: {question}

Respond ONLY with a JSON object in this format:
{{
    "needs_context": true/false,
    "reason": "brief explanation",
    "confidence": 0.0-1.0
}}

needs_context: true if the question likely needs external documents/knowledge, false if it can be answered from general knowledge
confidence: how confident you are in this assessment"""
        )

        chain = eval_prompt | self.llm

        response = chain.invoke({"question": question})

        try:
            import json

            # Extract JSON content and clean markdown
            json_str = self._extract_json_from_response(response.content)
            result = json.loads(json_str)
            return result
        except Exception as e:
            print(f"Error parsing question evaluation: {e}")
            return {
                "needs_context": True,
                "reason": "Could not parse evaluation",
                "confidence": 0.5,
            }

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
