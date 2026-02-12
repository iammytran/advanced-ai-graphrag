# RAG Chatbot với LangGraph

Một chatbot AI thông minh sử dụng **LangGraph** framework và **Retrieval-Augmented Generation (RAG)** để cung cấp các câu trả lời chính xác dựa trên tài liệu có liên quan.

## 🎯 Tính Năng

- **LangGraph Workflow**: Xây dựng quy trình phức tạp với các nodes và edges
- **Đánh Giá Câu Hỏi**: Tự động xác định xem câu hỏi có cần tài liệu tham khảo hay không
- **Vector Database**: Lưu trữ và tìm kiếm tài liệu sử dụng FAISS embeddings
- **Document ID Management**: Mỗi document có ID duy nhất, thay thế nếu trùng ID
- **Conversation History**: Lưu lại toàn bộ lịch sử cuộc trò chuyện
- **Đánh Giá Kết Quả**: Đánh giá chất lượng câu trả lời sử dụng LangChain
- **Interactive CLI**: Giao diện dòng lệnh thân thiện cho người dùng
- **Dual Provider Support**: Hỗ trợ cả Gemini API và OpenAI

## 📋 Workflow

```
START
  ↓
INPUT (Nhận câu hỏi)
  ↓
EVALUATE QUESTION (Đánh giá câu hỏi)
  ↓
  ├─ Nếu cần context → RETRIEVE DOCUMENTS
  │                      ↓
  │                  GENERATE ANSWER
  │
  └─ Nếu không cần context → GENERATE ANSWER
                              ↓
                          EVALUATE ANSWER (Optional)
                              ↓
OUTPUT (Trả về kết quả)
  ↓
END
```

## 🚀 Cài Đặt

### 1. Clone Repository
```bash
cd c:\DaiHoc\SDH\ML\RAG_Chatbot
```

### 2. Tạo Virtual Environment (tuỳ chọn)
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu Hình Environment

#### Sử dụng Gemini API (Khuyến nghị)
```bash
copy .env.example .env
```

Mở file `.env` và thêm:
```
USE_GEMINI=true
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini-1.5-pro
```

Lấy API key: https://makersuite.google.com/app/apikey

#### Hoặc sử dụng OpenAI API
```
USE_GEMINI=false
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo
```

Lấy API key: https://platform.openai.com/account/api-keys

## 📁 Cấu Trúc Dự Án

```
RAG_Chatbot/
├── src/
│   ├── vector_db.py           # Vector Database Manager
│   ├── llm.py                 # LLM Manager
│   ├── evaluation.py          # Evaluation Manager
│   ├── chatbot.py             # LangGraph Workflow
│   └── conversation_history.py # History Management
├── config/
│   └── config.py              # Configuration
├── data/
│   ├── vector_store/          # FAISS Vector Store
│   └── conversation_history/  # Saved conversations
├── example.py                 # Example Script
├── cli.py                     # Interactive CLI
├── requirements.txt           # Dependencies
├── .env.example               # Environment Template
└── README.md
```

## 💻 Sử Dụng

### 1. Chạy Example Script
```bash
python example.py
```

Điều này sẽ:
- Load các tài liệu mẫu với document IDs
- Chạy chatbot trên 4 câu hỏi ví dụ
- Hiển thị đánh giá chất lượng
- Lưu lịch sử cuộc trò chuyện

### 2. Sử Dụng Interactive CLI
```bash
python cli.py
```

Lệnh khả dụng:
```
history  - Xem lịch sử trò chuyện
stats    - Xem thống kê
save     - Lưu history ra file (JSON + TXT)
clear    - Xóa history
help     - Hiển thị trợ giúp
exit     - Thoát (và lưu history)
```

Hoặc chỉ cần nhập câu hỏi!

### 3. Sử Dụng trong Code

```python
from src.chatbot import RAGChatbot
from src.vector_db import VectorDBManager
from langchain_core.documents import Document

# Setup documents
db = VectorDBManager()
docs = [
    Document(
        page_content="...",
        metadata={"doc_id": "unique_id", "source": "..."}
    )
]
db.add_documents(docs)

# Create chatbot
chatbot = RAGChatbot()

# Ask question
result = chatbot.run("What is RAG?")
print(result)

# Save conversation
chatbot.save_conversation("my_session")
```

## 🔧 Cấu Hình Tùy Chỉnh

### Chỉnh sửa `config/config.py`:

```python
# LLM Configuration
TEMPERATURE = 0.7              # 0.0 = deterministic, 1.0 = creative

# Vector DB
TOP_K = 5                      # Số tài liệu truy xuất

# Evaluation
ENABLE_EVALUATION = True       # Bật/tắt đánh giá
EVALUATION_THRESHOLD = 0.6     # Ngưỡng chất lượng
```

### Gemini Models Khả Dụng:
- `gemini-1.5-pro` - Model mạnh nhất, chi phí cao hơn (Khuyến nghị)
- `gemini-1.5-flash` - Model nhanh, chi phí thấp
- `gemini-pro` - Model cũ, ổn định

### OpenAI Models:
- `gpt-4` - Model mạnh nhất
- `gpt-3.5-turbo` - Model nhanh, chi phí thấp

## 📊 Document ID Management

Mỗi document phải có `doc_id` trong metadata:

```python
Document(
    page_content="...",
    metadata={"doc_id": "unique_id_123", "source": "..."}
)
```

**Tính năng:**
- ✅ Nếu `doc_id` đã tồn tại → **Replace** (xóa cũ, thêm mới)
- ✅ Metadata được lưu trong `document_metadata.json`
- ✅ Support delete: `db.delete_document("doc_id")`
- ✅ Get info: `db.get_document_by_id("doc_id")`

## 📜 Conversation History

Mỗi cuộc trò chuyện được lưu tự động:

```
data/conversation_history/
├── conversation_20260202_120530.json  # Dữ liệu chi tiết
└── conversation_20260202_120530.txt   # Dạng đọc được
```

**File JSON chứa:**
```json
{
  "created_at": "2026-02-02T12:05:30",
  "message_count": 8,
  "messages": [
    {
      "timestamp": "...",
      "role": "user",
      "content": "...",
      "metadata": {...}
    }
  ]
}
```

## 📊 Output Example

```
============================================================
🚀 RAG CHATBOT WORKFLOW STARTED
============================================================

📝 INPUT: What is Machine Learning?

🔍 EVALUATING QUESTION...
   Needs Context: True (Confidence: 0.95)

📚 RETRIEVING DOCUMENTS...
   Found 2 relevant documents
   1. Score: 0.892 - Machine Learning is...
   
🤖 GENERATING ANSWER...
   Answer: Machine Learning is a subset...

✅ EVALUATING ANSWER...
   Overall Score: 0.92
   Quality: ✓ High

🎯 FINAL OUTPUT
============================================================
```

## 🤖 Module Details

### Vector DB Manager
- FAISS vector store cho semantic search
- Document ID tracking
- Auto-replace với trùng ID
- Metadata persistence

### LLM Manager
- Đánh giá tự động câu hỏi
- Hỗ trợ Gemini + OpenAI
- Chainable prompts

### Evaluation Manager
- Đánh giá relevance, accuracy, completeness
- Scoring từ 0.0-1.0
- Feedback tự động

### RAG Chatbot (LangGraph)
- 6 nodes: input, evaluate, retrieve, generate, evaluate, output
- Conditional routing
- State management

### Conversation History
- Auto-save mỗi message
- JSON + TXT export
- Statistics tracking
- Full history retrieval

## 🔐 Bảo Mật

- `.env` file không commit lên git
- API keys an toàn
- FAISS deserialization safe

## 🚀 Performance Tips

1. **Gemini 1.5-Flash**: Nhanh, chi phí thấp, tốt cho production
2. **TOP_K=3**: Đủ cho hầu hết queries
3. **TEMPERATURE=0.5**: Balanced creative + deterministic

## 🤝 Troubleshooting

**Model không tìm thấy:**
- Cập nhật `LLM_MODEL` trong .env
- Kiểm tra danh sách model khả dụng ở trên

**API Key issues:**
- Xác nhận file `.env` được copy từ `.env.example`
- Kiểm tra key không bị cắt xén

**Vector store errors:**
- Xóa thư mục `data/vector_store/` để reset
- Cài lại requirements: `pip install -r requirements.txt`

## 📝 Ghi Chú

- Lần đầu chạy sẽ tạo vector store
- Embedding tài liệu mất vài giây
- Gemini API miễn phí lên tới 60 request/phút

## 🎓 Project Info

- **Type**: Final Project for Advanced AI class
- **Framework**: LangGraph + LangChain
- **Provider**: Google Gemini / OpenAI
- **Created**: February 2, 2026

---

**Happy coding! 🚀**
