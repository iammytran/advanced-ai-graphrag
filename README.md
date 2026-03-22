# Advanced AI: GraphRAG Legal Project
**Final Project | Class 35 (2026) - Advanced AI**

This project implements a **GraphRAG** (Graph Retrieval-Augmented Generation) system. The workflow is divided into two main phases: **Indexing** (offline knowledge graph construction) and **Retrieving** (online query processing).

---

## 1. Environment Setup

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
1. Create a .env file in the **root directory** and add your required environment variables for backend. You can follow the format (HERE)[https://github.com/iammytran/advanced-ai-graphrag/blob/main/backend/.env.example] for .env file.
2. Create a .env file in the 'frontend' directory and add your required environment variables for frontend. You can follow the format (HERE)[https://github.com/iammytran/advanced-ai-graphrag/blob/main/frontend/.env.example] for .env file.
3. SPECIAL NOTE: Since the project uses vLLM for indexing, OpenAI for queries, and a custom embedding model for local search, please ensure that the VLLM_MODEL, OPENAI_API_KEY, and VN_EMBEDDING_MODEL fields are defined in your .env file. If these are not provided, the system will fallback to the default values in config.py.

## Execution Guide
**A. Run Retrieving**: 
If you already have indexing outputs in the artifacts folder, you can run the chatbot immediately:
1. Open backend/src/chatbot.py.
2. Locate the main() function and input your question.
3. Execute the following command:
```bash
python -m backend.src.chatbot
```

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
or 
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
## 2. Run Chatbot Application

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
### What is in folder artifacts?
After the indexing process, the artifacts folder is populated with the essential data structures required for the querying step. Key files include:
- entities.pkl: Contains a DataFrame of all entities extracted from the text chunks, including their types, descriptions, and chunks they are from.
- relationships.pkl: Stores the extracted connections between entities, representing the edges of your knowledge graph and the strength/description of those connections. You can use this file to visualize graph using library networkx.
- claims.pkl: Contains "covariates" or statements of fact (claims) extracted from the text, linked to specific entities and documented with source citations.
- entity_embeddings.npy: Stores the high-dimensional vector representations of all entity names. This is crucial for Local Search, allowing the system to perform similarity mapping between your query and the entities in the graph.
- communities.json: Contains the output of the Leiden community detection algorithm. It defines the hierarchical structure of the knowledge graph, grouping related entities into clusters.
- community_summaries.json: Holds the AI-generated summaries for each community at different levels of the hierarchy. This is the core resource for both Global and Local Search, enabling the model to answer questions by synthesizing these summaries.
