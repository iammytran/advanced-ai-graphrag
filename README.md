# advanced-ai-graphrag
Final Project for class Advanced AI

## Setup and Run LangGraph

### Run Example
1. **Install Dependencies**: Install the necessary requirements:
```bash
pip install -r backend/requirements.txt
```

2. **Indexing RAG**: Run the following command to import chunks into the vector database:
```bash
python -m backend.tools.rag
```

3. **Configuration**: Create a `.env` file with the required environment variables.

4. **Run LangGraph Example**: Execute the chatbot flow using the following command:
```bash
python -m backend.src.chatbot
```



### Run Backend

1. Follow the setup and indexing steps from the **Run Example** section above.
2. Start the backend server by running:
```bash
python main.py
```


3. **Interact with the System**:
* **Frontend**: If the frontend is already running, you can interact with the chat normally.
* **API**: If there is no frontend, you can test the backend directly by calling the API at `http://localhost:8000/chat` with the following JSON payload:



```json
{
  "question": "đánh bài phạt bao nhiêu tiền?",
  "options": {
    "toneValue": 3
  }
}

```

```

Would you like me to help draft a template for your `.env` file to include alongside these setup instructions?

```