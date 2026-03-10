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
 * Evaluate courtroom session performance via backend AI
 * Sends full session data to server and receives scores for 5 categories
 *
 * @param {object} sessionData - The courtroom session data
 * @param {string} sessionData.scenarioId - ID of the scenario
 * @param {string} sessionData.role - 'defendant' or 'plaintiff'
 * @param {object} sessionData.scenario - Scenario info (name, summary, facts)
 * @param {object[]} sessionData.messages - Chat messages (type: user/opponent/system)
 * @param {object} sessionData.strategy - Prepared arguments and evidences
 * @param {number} sessionData.roundsCompleted - Number of rounds completed
 * @param {number} sessionData.totalRounds - Total rounds configured
 * @param {number} sessionData.timeRemaining - Seconds remaining
 * @param {number} sessionData.totalTime - Total seconds configured
 * @returns {Promise<object>} - Scores: { legalAccuracy, evidenceUse, persuasion, timeManagement, etiquette }
 */
export async function evaluateSession(sessionData) {
    try {
        const response = await fetch(`${API_Base_URL}/courtroom/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(sessionData)
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error calling evaluate API:", error);
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
