"""Configuration file for RAG Chatbot"""
import os
from dotenv import load_dotenv

load_dotenv()

# Provider Configuration (use_gemini or openai)
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true"

# LLM Configuration
if USE_GEMINI:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    # Available Gemini models: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
else:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

TEMPERATURE = 0.7

# Vector DB Configuration
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vector_store")
TOP_K = int(os.getenv("TOP_K", "5"))

# RAG Configuration
RETRIEVAL_THRESHOLD = 0.5
USE_RERANKING = False

# Evaluation Configuration
ENABLE_EVALUATION = True
EVALUATION_THRESHOLD = 0.6
