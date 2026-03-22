# advanced-ai-graphrag
Final Project for class Advanced AI - Class 35(2026)

## General Technical Introduction
To run this project, indexing must be done first, as that will create materials needed for retrieving steps. Indexing is the offline step, whereas retrieving is the online.
For this project, you can run these things:
- Run Indexing
- Run Indexing + Retrieving
- Run Retrieving
- Run Evaluate GraphRAG
- 
This document is the guideline to run 
## Setup Environments
**1. Install Dependencies**: Install the necessary requirements:
```bash
conda create -n graphrag python=3.10 -y
conda activate graphrag
```
```bash
pip install uv
uv pip install -r ./backend/requirement.txt
```
**2. Configuration**: Create a `.env` file with the required environment variables.
This is needed for step 

## Run Guide for Each Component
**Run Retrieving**: 
Since Indexing has already been done, you can start  
If you want to run test retrieve for a specific query, execute the command below using the following command:
```bash
python -m backend.src.chatbot
```
Please come to main() of file chatbot.py and input your question.
Also note that, currently 

### **Run Indexing**: Run the following command to create chunks, extract Entities & Relationships & Claims, create graph, perform community detection, and create community summaries:
Indexing has been done by default as we set up this project. You can check the outputs of the Indexing in folder artifacts. Folder artifacts is the default folder for storing Indexing outputs.

However, if you want to re-run indexing (e.g. you have changed Indexing flow, new config), follow the commands below under these scenarios:
1. If you want all of the new indexing's outputs to be replaced, run:
```bash
python -m backend.tools.graphrag --force-index-from-scratch
```
Without tag "--force-index-from-scratch", since folder artifacts has enough materials needed for retrieving steps then Indexing step will be skipped.

2. If you want the Indexing's output to be in a new folder aside from artifacts (e.g. artifacts_v2), run:
```bash
python -m backend.tools.graphrag --output-folder artifacts_v2
```
Note that if folder artifacts_v2 has already existed and has enough materials needed for retrieving steps then Indexing step will be skipped.
Which also means if folder artifacts_v2 has already existed and you want to replace its contents, use tag "--force-index-from-scratch"
```bash
python -m backend.tools.graphrag --output-folder artifacts_v2 --force-index-from-scratch
```

3. Note:
Currently, indexing is done mainly by using vllm of model Qwen/Qwen2.5-7B-Instruct. To change it, please go to config.py file.


## Run the whole application

### Run Example
2. **Indexing RAG**: Run the following command to create chunks, extract Entities & Relationships & Claims, create graph, perform community detection, and create community summaries:
```bash
python -m backend.tools.graphrag
```

4. **Run LangGraph Example**: Execute the chatbot flow using the following command:
```bash
python -m backend.src.chatbot
```
## Run 


### Run Backend

1. Follow the setup and indexing steps from the **Run Example** section above.
2. Start the backend server by running:
```bash
python -m backend.main
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
