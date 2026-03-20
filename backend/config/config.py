import os

from dotenv import load_dotenv

load_dotenv()

TEMPERATURE = os.getenv("TEMPERATURE", 0.7)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
HUGGINGFACE_MODEL = os.getenv(
    "HUGGINGFACE_MODEL", "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "keepitreal/vietnamese-sbert")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
ARTIFACT_FOLDER = os.getenv("ARTIFACT_FOLDER", "artifacts")
