import os

from dotenv import load_dotenv

load_dotenv()

TEMPERATURE = os.getenv("TEMPERATURE", 0.7)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
HUGGINGFACE_MODEL = os.getenv(
    "HUGGINGFACE_MODEL", "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
)
VN_EMBEDDING_MODEL = os.getenv("VN_EMBEDDING_MODEL", "AITeamVN/Vietnamese_Embedding")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
ARTIFACT_FOLDER = os.getenv("ARTIFACT_FOLDER", "artifacts")
TOP_K_RETRIEVED = os.getenv("TOP_K", 3)

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vector_store")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

QUERY_CLASSIFIER_PROVIDER = os.getenv("QUERY_CLASSIFIER_PROVIDER", "openai")

# Global Query Config
GLOBAL_QUERY_PROVIDER = os.getenv("GLOBAL_QUERY_PROVIDER", "openai")
GLOBAL_QUERY_MAX_CONCURRENCY = int(os.getenv("GLOBAL_QUERY_MAX_CONCURRENCY", 8))
GLOBAL_QUERY_HF_BATCH_SIZE = int(os.getenv("GLOBAL_QUERY_HF_BATCH_SIZE", 8))

# Local Query Config
LOCAL_QUERY_PROVIDER = os.getenv("LOCAL_QUERY_PROVIDER", "openai")
LOCAL_QUERY_MAX_CONCURRENCY = int(os.getenv("LOCAL_QUERY_MAX_CONCURRENCY", 8))
LOCAL_QUERY_HF_BATCH_SIZE = int(os.getenv("LOCAL_QUERY_HF_BATCH_SIZE", 4))