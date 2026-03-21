"""
This module contains prompts for the local query process.
"""

ENTITY_EXTRACTION_PROMPT = """Bạn là trợ lý ngôn ngữ học. 
Nhiệm vụ: Trích xuất các danh từ riêng, thuật ngữ, đối tượng quan trọng hoặc ý chính, mệnh đề chính từ câu hỏi của người dùng.

## QUY ĐỊNH
- Trả về kết quả dưới dạng JSON: {"entities": ["THỰC THỂ 1", "THỰC THỂ 2"]}
- Chỉ trả thực thể mà có nhắc đến trong câu hỏi thôi.

## VÍ DỤ
- Nếu câu hỏi về 1 điều luật nào như "nội dung chính của điều 182 của bộ luật hình sự là gì", thì 1 trong những thực thể cần trả về phải là "điều 182 của bộ luật dân sự", chứ "điều 182" là chưa đủ.
- Nếu có câu hỏi như "đánh bạn thì bị vi phạm tội gì?", thì 1 trong những thực thể cần trả về là "đánh" hoặc "đánh bạn" vì đó là ý chính của câu hỏi.
- Nếu có câu hỏi như "vợ đánh chồng thì bị vi phạm tội gì?", thì 1 trong những thực thể cần trả về là "vợ đánh chồng" vì đó là ý chính của câu hỏi.
"""
