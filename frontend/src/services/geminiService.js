import { GoogleGenerativeAI } from "@google/generative-ai";

// Lấy API key từ environment variables
const apiKey = import.meta.env.VITE_GEMINI_API_KEY;

// Kiểm tra xem API key có tồn tại không
if (!apiKey) {
    console.warn("⚠️ VITE_GEMINI_API_KEY không được tìm thấy. Sẽ sử dụng mock data fallback.");
}

const genAI = new GoogleGenerativeAI(apiKey || "dummy_key");

const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

/**
 * Gọi Gemini API để sinh câu trả lời
 * @param {string} prompt Nội dung yêu cầu 
 * @param {string} fallback Phản hồi dự phòng nếu gọi API thất bại
 * @returns {Promise<string>} Câu trả lời từ AI
 */
export const generateGeminiResponse = async (prompt, fallback = "Lỗi kết nối AI. (Mock fallback)") => {
    if (!apiKey) {
        console.warn("Chưa cấu hình API Key, trả về fallback.");
        return fallback;
    }

    try {
        console.log('[Gemini] Request:', { model: 'gemini-2.5-flash', prompt });
        const startTime = Date.now();
        const result = await model.generateContent(prompt);
        const response = await result.response;
        const text = response.text();
        console.log('[Gemini] Response:', { text, duration: `${Date.now() - startTime}ms` });
        return text;
    } catch (error) {
        console.error("[Gemini] Error:", error);
        
        // Check lỗi quota
        if (error.message?.includes('429') || error.message?.includes('EXHAUSTED')) {
           return "Tôi phản đối lập luận này. (Chú ý: Đã vượt quá giới hạn API miễn phí của Gemini).";
        }
        
        return fallback;
    }
}
