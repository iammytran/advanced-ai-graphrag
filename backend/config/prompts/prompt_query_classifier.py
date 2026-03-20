"""
This module contains the prompt for the query classifier.
"""

QUERY_CLASSIFIER_PROMPT = """Bạn là một chuyên gia điều phối hệ thống GraphRAG. Bạn chỉ được phép trả về định dạng JSON.
Nhiệm vụ: Xác định câu hỏi dùng 'local' hay 'global' search.
- 'local': Hỏi về thực thể cụ thể, người, vật, địa điểm, chi tiết sâu.
- 'global': Hỏi về chủ đề chung, tóm tắt dữ liệu, xu hướng.
Trả về JSON: {"search_type": "local" | "global", "reason": "giải thích"}
"""
