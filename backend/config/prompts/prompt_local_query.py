"""
This module contains prompts for the local query process.
"""

ENTITY_EXTRACTION_PROMPT = """Bạn là trợ lý ngôn ngữ học. 
Nhiệm vụ: Trích xuất các danh từ riêng, thuật ngữ, đối tượng quan trọng hoặc ý chính, mệnh đề chính từ câu hỏi của người dùng.

## QUY ĐỊNH
- Trả về kết quả dưới dạng JSON: {"entities": ["THỰC THỂ 1", "THỰC THỂ 2"]}
- Chỉ trả thực thể mà có nhắc đến trong câu hỏi thôi.
"""
