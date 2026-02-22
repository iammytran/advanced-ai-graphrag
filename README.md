# advanced-ai-graphrag
Final Project for class Advanced AI

## Setup and Run LangGraph

### Run Example
1. Run `python rag.py` to import chunks into the vector database (using LangChain's FAISS).
2. Change directory to the backend (`cd backend`) and install the necessary dependencies: `pip install -r requirements.txt`.
3. Create a `.env` file with the required environment variables.
4. Run `python example.py` to execute the example.

### Run Backend
1. Follow steps 1 to 3 from the **Run Example** section above.
2. Start the backend server by running `python main.py`.
3. If the frontend is already running, you can interact with the chat normally. If there is no frontend, you can test the backend directly by calling the API at `http://localhost:8000/chat` with the following JSON payload:

```json
{
  "question": "đánh bài phạt bao nhiêu tiền?",
  "options": {
    "toneValue": 3
  }
}
```
