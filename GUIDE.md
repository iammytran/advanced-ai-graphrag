# RAG Chatbot with LangGraph

Một chatbot AI thông minh sử dụng **LangGraph** framework và **Retrieval-Augmented Generation (RAG)** để cung cấp các câu trả lời chính xác dựa trên tài liệu có liên quan.

## 🎯 Tính Năng

- **LangGraph Workflow**: Xây dựng quy trình phức tạp với các nodes và edges
- **Đánh Giá Câu Hỏi**: Tự động xác định xem câu hỏi có cần tài liệu tham khảo hay không
- **Vector Database**: Lưu trữ và tìm kiếm tài liệu sử dụng FAISS embeddings
- **Đánh Giá Kết Quả**: Đánh giá chất lượng câu trả lời sử dụng LangChain
- **Interactive CLI**: Giao diện dòng lệnh thân thiện cho người dùng

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
```bash
# Copy .env.example và chỉnh sửa
cp .env.example .env

# Thêm OpenAI API key của bạn
# Mở .env và cập nhật: OPENAI_API_KEY=your_key_here
```

## 📁 Cấu Trúc Dự Án

```
RAG_Chatbot/
├── src/
│   ├── vector_db.py        # Vector Database Manager
│   ├── llm.py              # LLM Manager (OpenAI)
│   ├── evaluation.py       # Evaluation Manager
│   └── chatbot.py          # LangGraph Workflow
├── config/
│   └── config.py           # Configuration
├── data/
│   └── vector_store/       # FAISS Vector Store
├── example.py              # Example Script
├── cli.py                  # Interactive CLI
├── requirements.txt        # Dependencies
├── .env.example            # Environment Template
└── README.md
```

## 💻 Sử Dụng

### 1. Chạy Example Script
```bash
python example.py
```

Điều này sẽ:
- Load các tài liệu mẫu
- Chạy chatbot trên 4 câu hỏi ví dụ
- Hiển thị đánh giá chất lượng

### 2. Sử Dụng Interactive CLI
```bash
python cli.py
```

Giao diện tương tác cho phép bạn:
- Hỏi câu hỏi bất kỳ lúc nào
- Nhận câu trả lời ngay lập tức
- Xem đánh giá chất lượng

### 3. Sử Dụng trong Code

```python
from src.chatbot import RAGChatbot
from src.vector_db import VectorDBManager
from langchain.schema import Document

# Setup documents
db = VectorDBManager()
docs = [Document(page_content="...")]
db.add_documents(docs)

# Create chatbot
chatbot = RAGChatbot()

# Ask question
result = chatbot.run("What is RAG?")
print(result)
```

## 🔧 Cấu Hình Tùy Chỉnh

Chỉnh sửa `config/config.py`:

```python
# LLM Configuration
LLM_MODEL = "gpt-3.5-turbo"  # hoặc "gpt-4"
TEMPERATURE = 0.7              # 0.0 = deterministic, 1.0 = creative

# Vector DB
TOP_K = 5                      # Số tài liệu truy xuất

# Evaluation
ENABLE_EVALUATION = True       # Bật/tắt đánh giá
EVALUATION_THRESHOLD = 0.6     # Ngưỡng chất lượng
```

## 📊 Output Example

```
============================================================
🚀 RAG CHATBOT WORKFLOW STARTED
============================================================

📝 INPUT: What is Machine Learning?

🔍 EVALUATING QUESTION...
   Needs Context: True (Confidence: 0.95)
   Reason: This requires domain-specific knowledge

📚 RETRIEVING DOCUMENTS...
   Found 2 relevant documents
   1. Score: 0.892 - Machine Learning is a subset...
   2. Score: 0.756 - ML algorithms analyze data...

🤖 GENERATING ANSWER...
   Answer: Machine Learning is a subset of artificial...

✅ EVALUATING ANSWER...
   Overall Score: 0.92
   Quality: ✓ High
   Feedback: Comprehensive and well-structured answer

🎯 FINAL OUTPUT
   Question: What is Machine Learning?
   Answer: [Full answer text]
   Documents Used: 2
   Quality Score: 0.92
============================================================
✅ WORKFLOW COMPLETED
============================================================
```

## 🤖 Module Details

### Vector DB Manager
- Lưu trữ tài liệu sử dụng FAISS
- Tìm kiếm ngữ nghĩa tương tự (semantic search)
- Trả về top-k tài liệu liên quan

### LLM Manager
- Đánh giá tự động xem câu hỏi có cần tài liệu
- Tạo câu trả lời sử dụng LangChain prompts
- Hỗ trợ gọi API OpenAI

### Evaluation Manager
- Đánh giá độ liên quan (relevance)
- Đánh giá độ chính xác (accuracy)
- Đánh giá độ hoàn chỉnh (completeness)
- Đánh giá độ rõ ràng (clarity)

### RAG Chatbot (LangGraph)
Workflow gồm các nodes:
1. **input**: Xử lý câu hỏi đầu vào
2. **evaluate_question**: Xác định cần retrieval hay không
3. **retrieve_documents**: Lấy tài liệu từ Vector DB
4. **generate_answer**: Tạo câu trả lời
5. **evaluate_answer**: Đánh giá chất lượng câu trả lời
6. **output**: Chuẩn bị kết quả cuối cùng

## 🔐 Bảo Mật

- Lưu OPENAI_API_KEY trong `.env` file (không commit lên git)
- `.gitignore` đã được cấu hình để bỏ qua `.env`

## 📚 Dependencies

- **langgraph**: Xây dựng workflow
- **langchain**: Framework LLM
- **langchain-openai**: OpenAI integration
- **faiss-cpu**: Vector database
- **python-dotenv**: Environment variables

## 🤝 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra API key OpenAI
2. Đảm bảo tất cả dependencies đã cài
3. Kiểm tra kết nối internet
4. Xem logs trong terminal

## 📝 Ghi Chú

- Lần đầu chạy sẽ tạo vector store
- Có thể mất thời gian để embedding tài liệu
- Chất lượng câu trả lời phụ thuộc vào chất lượng tài liệu

## 🎓 Dự Án Học Tập

Đây là project cuối cùng cho khóa học Advanced AI.

---

**Created**: February 2, 2026
