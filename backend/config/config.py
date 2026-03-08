import os

from dotenv import load_dotenv

load_dotenv()

TEMPERATURE = os.getenv("TEMPERATURE", 0.7)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
