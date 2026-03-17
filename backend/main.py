import os
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure backend directory is in path to import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.chatbot import Chatbot

app = FastAPI(title="RAG Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
chatbot = Chatbot(model_option=2, retrieval_mode="graphrag_only")

class Options(BaseModel):
    character: Optional[str] = None
    toneValue: Optional[int] = None
    illustrationType: Optional[str] = None
    output_folder: Optional[str] = None
    outputFolder: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    options: Optional[Options] = None


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Convert options to dict
        options_dict = request.options.model_dump() if request.options else {}

        # Run chatbot
        # Note: chatbot.chat returns a dict with 'answer', 'retrieved_documents', etc.
        try:
            rag_response = chatbot.chat(request.question, options_dict)
        except Exception as e:
            print(f"Error running chatbot: {e}")
            rag_response = {
                "answer": "This is a mock answer from backend.",
                "retrieved_documents": [],
            }    

        # Format response to match frontend expectation
        from datetime import datetime

        frontend_response = {
            "answer": rag_response.get("answer", ""),
            "character": options_dict.get("character", "normal"),
            "timestamp": datetime.now().isoformat(),
            "retrieved_documents": rag_response.get(
                "retrieved_documents", []
            ),  # useful extension
        }

        return frontend_response

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
