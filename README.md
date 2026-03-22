# Advanced AI: GraphRAG Legal Project
**Final Project | Class 35 (2026) - Advanced AI**

This project implements a **GraphRAG** (Graph Retrieval-Augmented Generation) system. The workflow is divided into two main phases: **Indexing** (offline knowledge graph construction) and **Retrieving** (online query processing).

---

## 🛠 1. Environment Setup

Ensure you have `conda` and `uv` installed for faster dependency management.

### Install Dependencies
```bash
# Create and activate environment
conda create -n graphrag python=3.10 -y
conda activate graphrag

# Install requirements using uv
pip install uv
uv pip install -r ./backend/requirement.txt
```
**2. Configuration**: 
1. Create a .env file in the root directory and add your required environment variables (API keys, endpoints, etc.).
2. Model Settings: By default, the system uses Qwen/Qwen2.5-7B-Instruct via vLLM. You can modify this in config.py.

## Execution Guide
**A. Run Retrieving**: 
If you already have indexing outputs in the artifacts folder, you can run the chatbot immediately:
1. Open backend/src/chatbot.py.
2. Locate the main() function and input your question.
3. Execute the following command:
```bash
python -m backend.src.chatbot
```

Also note that, currently we use the 

### **B. Run Indexing**: 
The indexing process creates chunks, extracts Entities, Relationships, and Claims, performs community detection, and generates community summaries.

By default, indexing outputs are stored in the artifacts/ folder. You can re-run the process using the following scenarios:
1. Force re-index from scratch (Overwrite default):
```bash
python -m backend.tools.graphrag --force-index-from-scratch
```

2. Index to a specific folder:
```bash
python -m backend.tools.graphrag --output-folder artifacts_v2
```
hoặc 
```bash
python -m backend.tools.graphrag -o artifacts_v2
```

3. Overwrite a specific folder:
```bash
python -m backend.tools.graphrag -o artifacts_v2 --force-index-from-scratch
```
Note: The system will skip the indexing step if the target folder already contains sufficient materials, unless the --force-index-from-scratch flag is used.

### **C. Run evaluator**: 
The project also includes a module for performance analysis, which assesses the quality and accuracy of the retrieved answers of GraphRAG on our own dataset.
To run the evaluation, execute the command below:
```bash
python -m evaluator_rag
```
## Run the whole application

### Run Backend
1. Follow the setup and indexing steps from the **Run Indexing** section above.
2. Start the backend server by running:
```bash
python -m backend.main
```

### Run Frontend
1. Go to folder frontend using:
```bash
cd frontend
```
2. Read file README in the folder and follow the guide there to run frontend.

### Access the System with API
If there is no frontend, you can test the backend directly by calling the API at `http://localhost:8000/chat` with the following JSON payload:


3. **Interact with the System**:
* **Frontend**: If the frontend is already running, you can interact with the chat normally.
* **API**: If there is no frontend, you can test the backend directly by calling the API at `http://localhost:8000/chat` with the following JSON payload:
```json
{
  "question": "đánh bài phạt bao nhiêu tiền?",
  
}
```
## 
