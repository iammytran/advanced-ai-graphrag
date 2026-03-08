// Service to interact with the backend RAG Chatbot API

const API_Base_URL = "http://localhost:8000";

/**
 * Send a message to the backend RAG system
 * @param {string} question - The user's question
 * @param {object} options - Configuration options (character, toneValue, illustrationType)
 * @returns {Promise<object>} - The backend response
 */
export async function sendMessage(question, options = {}) {
    try {
        const response = await fetch(`${API_Base_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question,
                options
            })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error calling backend API:", error);
        throw error;
    }
}

/**
 * Get example/suggested questions
 * @returns {string[]}
 */
export function getSuggestedQuestions() {
    return [
        "Thuê nhà cần lưu ý gì?",
        "Thủ tục ly hôn như thế nào?",
        "Bị tai nạn giao thông phải làm sao?",
        "Viết di chúc thế nào cho đúng?",
        "Thủ tục đăng ký kết hôn cần giấy tờ gì?",
        "Quyền lợi của người lao động khi bị sa thải trái luật?"
    ];
}
