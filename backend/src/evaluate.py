import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

evaluate_router = APIRouter()


class ScenarioMsg(BaseModel):
    name: str = ""
    summary: str = ""
    facts: List[str] = []


class MessageItem(BaseModel):
    type: str
    text: str
    round: Optional[int] = None


class ArgumentItem(BaseModel):
    text: str


class EvidenceItem(BaseModel):
    text: str
    linkedArguments: Optional[List[int]] = None


class StrategyItem(BaseModel):
    arguments: List[ArgumentItem] = []
    evidences: List[EvidenceItem] = []


class EvaluateRequest(BaseModel):
    scenarioId: str
    role: str
    scenario: ScenarioMsg
    messages: List[MessageItem]
    strategy: StrategyItem
    roundsCompleted: int
    totalRounds: int
    timeRemaining: int
    totalTime: int


class CourtroomEvaluationResult(BaseModel):
    legalAccuracy: int = Field(
        description=(
            "Độ chính xác pháp lý (0-100). Tính như sau: "
            "Điểm gốc = 50. "
            "Cộng 0-20 theo tỷ lệ vòng hoàn thành (roundsCompleted / totalRounds * 20). "
            "Cộng 5/10/15 nếu độ dài trung bình tin nhắn người dùng >50 / >100 / >200 ký tự. "
            "Cộng 0-15 theo số luận điểm chuẩn bị (mỗi luận điểm +5, tối đa 15). Tổng tối đa 100."
        )
    )
    evidenceUse: int = Field(
        description=(
            "Sử dụng chứng cứ (0-100). Tính như sau: "
            "Điểm gốc = 40. "
            "Cộng 0-30 theo số chứng cứ chuẩn bị (mỗi chứng cứ +10, tối đa 30). "
            "Cộng 0-16 theo số chứng cứ liên kết với luận điểm (mỗi liên kết +8, tối đa 16). "
            "Cộng 0-14 nếu tin nhắn người dùng chứa từ khóa chứng cứ "
            "('chứng cứ', 'bằng chứng', 'tài liệu', 'chứng minh', 'căn cứ', 'minh chứng') — mỗi tin +5, tối đa 14. Tổng tối đa 100."
        )
    )
    persuasion: int = Field(
        description=(
            "Sức thuyết phục (0-100). Tính như sau: "
            "Điểm gốc = 45. "
            "Cộng 0-15 theo tỷ lệ vòng hoàn thành (roundsCompleted / totalRounds * 15). "
            "Cộng 0-16 theo số tin nhắn người dùng (mỗi tin +4, tối đa 16). "
            "Cộng 0-12 theo số luận điểm chuẩn bị (mỗi luận điểm +4, tối đa 12). "
            "Cộng 7/12 nếu độ dài trung bình tin nhắn >80 / >150 ký tự. Tổng tối đa 100."
        )
    )
    timeManagement: int = Field(
        description=(
            "Quản lý thời gian (0-100). Tính như sau: "
            "Điểm gốc = 40. "
            "Hoàn thành TẤT CẢ vòng VÀ còn thời gian: +30; thêm +10 nếu dùng 50-90% thời gian (pacing tốt), hoặc +20 nếu rất tốt. "
            "Kết thúc sớm nhưng còn thời gian: +15 + bonus theo vòng hoàn thành. "
            "Hết thời gian: +0-20 theo vòng hoàn thành. "
            "Cộng 0-10 theo tỷ lệ thời gian còn lại (timeRemaining / totalTime * 10). Tổng tối đa 100."
        )
    )
    etiquette: int = Field(
        description=(
            "Phong thái ứng xử (0-100). Tính như sau: "
            "Điểm gốc = 70. "
            "Cộng 0-25 nếu tin nhắn người dùng dùng từ lịch sự "
            "('thưa', 'kính', 'hội đồng', 'xét xử', 'tòa', 'đề nghị', 'xin phép', 'trân trọng') — mỗi tin +5, tối đa 25. "
            "Trừ 15 điểm mỗi lần có từ thô lỗ ('ngu', 'vớ vẩn', 'nhảm', 'láo', 'bậy'). "
            "Cộng +5 nếu hoàn thành tất cả vòng. Tối thiểu 0, tối đa 100."
        )
    )
    explanation: str = Field(
        description="Giải thích chi tiết (2-4 câu) lý do chấm các điểm số định tính trên."
    )
    strengths: str = Field(
        description="Liệt kê các điểm mạnh nổi bật của người chơi trong phiên tranh tụng này."
    )
    weaknesses: str = Field(
        description="Liệt kê các điểm thiếu sót hoặc cần cải thiện của người chơi trong phiên tranh tụng này."
    )


@evaluate_router.post("/courtroom/evaluate")
async def evaluate_endpoint(request_data: EvaluateRequest, request: Request):
    try:
        chatbot = request.app.state.chatbot

        # Compute derived statistics to help the LLM apply the rubric accurately
        user_messages = [m for m in request_data.messages if m.type == "user"]
        avg_msg_len = (
            sum(len(m.text) for m in user_messages) / len(user_messages)
            if user_messages
            else 0
        )
        evidence_keywords = {
            "chứng cứ",
            "bằng chứng",
            "tài liệu",
            "chứng minh",
            "căn cứ",
            "minh chứng",
        }
        msgs_with_evidence_kw = sum(
            1
            for m in user_messages
            if any(kw in m.text.lower() for kw in evidence_keywords)
        )
        polite_keywords = {
            "thưa",
            "kính",
            "hội đồng",
            "xét xử",
            "tòa",
            "đề nghị",
            "xin phép",
            "trân trọng",
        }
        msgs_with_polite_kw = sum(
            1
            for m in user_messages
            if any(kw in m.text.lower() for kw in polite_keywords)
        )
        rude_keywords = {"ngu", "vớ vẩn", "nhảm", "láo", "bậy"}
        rude_count = sum(
            1
            for m in user_messages
            if any(kw in m.text.lower() for kw in rude_keywords)
        )
        linked_evidences = sum(
            1 for ev in request_data.strategy.evidences if ev.linkedArguments
        )
        time_used_pct = (
            (request_data.totalTime - request_data.timeRemaining)
            / request_data.totalTime
            * 100
            if request_data.totalTime > 0
            else 0
        )

        prompt = f"""
        Bạn là giám khảo phiên tòa trực tuyến. Hãy tính điểm cho từng tiêu chí THEO ĐÚNG công thức được mô tả trong schema output.
        QUAN TRỌNG: Tất cả phần giải thích (explanation, strengths, weaknesses) phải được viết HOÀN TOÀN bằng tiếng Việt.
        Dưới đây là toàn bộ dữ liệu phiên tòa để bạn áp dụng công thức:

        === DỮ LIỆU PHIÊN TÒA ===
        - Vai trò người chơi: {request_data.role}
        - Kịch bản: {request_data.scenario.name}
        - Tóm tắt kịch bản: {request_data.scenario.summary}
        - Số vòng hoàn thành: {request_data.roundsCompleted} / {request_data.totalRounds}
        - Thời gian còn lại: {request_data.timeRemaining}s / {request_data.totalTime}s
        - Phần trăm thời gian đã dùng: {time_used_pct:.1f}%

        === LUẬN ĐIỂM & CHỨNG CỨ ===
        - Số luận điểm chuẩn bị: {len(request_data.strategy.arguments)}
        - Luận điểm: {[arg.text for arg in request_data.strategy.arguments]}
        - Số chứng cứ chuẩn bị: {len(request_data.strategy.evidences)}
        - Số chứng cứ liên kết luận điểm: {linked_evidences}
        - Chứng cứ: {[ev.text for ev in request_data.strategy.evidences]}

        === THỐNG KÊ TIN NHẮN NGƯỜI DÙNG ===
        - Số tin nhắn người dùng gửi: {len(user_messages)}
        - Độ dài trung bình tin nhắn: {avg_msg_len:.0f} ký tự
        - Số tin nhắn chứa từ khóa chứng cứ: {msgs_with_evidence_kw}
        - Số tin nhắn chứa từ lịch sự: {msgs_with_polite_kw}
        - Số lần dùng từ thô lỗ: {rude_count}

        === LỊCH SỬ TIN NHẮN ===
        """
        for msg in request_data.messages:
            prompt += f"- [{msg.type}] (Vòng {msg.round}): {msg.text}\n"

        from langchain.messages import HumanMessage

        messages = [HumanMessage(content=prompt)]

        # Use structured output for LLM model
        structured_llm = chatbot.llm.with_structured_output(CourtroomEvaluationResult)
        response = structured_llm.invoke(messages)

        # Return the parsed Pydantic model as dict
        return response.model_dump()

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
