import { GoogleGenerativeAI } from "@google/generative-ai";

// Lấy API key từ environment variables
const apiKey = import.meta.env.VITE_GEMINI_API_KEY;

// Kiểm tra xem API key có tồn tại không
if (!apiKey) {
    console.warn("⚠️ VITE_GEMINI_API_KEY không được tìm thấy. Sẽ sử dụng mock data fallback.");
}

const genAI = new GoogleGenerativeAI(apiKey || "dummy_key");

// Khởi tạo model (Sử dụng gemini-1.5-flash làm mặc định vì gemini-2.0-flash chưa được support native trên SDK cũ, hoặc dùng 1.5 flash an toàn hơn)
// Bạn có thể đổi sang 'gemini-2.0-flash' nếu SDK VITE đã update. Ở đây dùng gemini-1.5-flash vì nó free tier ổn định.
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

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
        const result = await model.generateContent(prompt);
        const response = await result.response;
        return response.text();
    } catch (error) {
        console.error("Lỗi khi gọi Gemini API:", error);
        
        // Check lỗi quota
        if (error.message?.includes('429') || error.message?.includes('EXHAUSTED')) {
           return "Tôi phản đối lập luận này. (Chú ý: Đã vượt quá giới hạn API miễn phí của Gemini).";
        }
        
        return fallback;
    }
}
