export async function generateImageFromGemini(character, toneValue, illustrationType, text) {
    const apiKey = import.meta.env.VITE_GEMINI_IMAGE_API_KEY;
    if (!apiKey) {
        console.warn('VITE_GEMINI_IMAGE_API_KEY is not set. Falling back to mock image.');
        return null;
    }

    const shortPhrase = text;

    const style = illustrationType === 'comic' ? 'truyện tranh pháp luật Việt Nam' : 'poster tuyên truyền pháp luật Việt Nam';
    const charDesc = character === 'lawyer' ? 'một luật sư chuyên nghiệp trong phòng xử án' : 'một người bình thường đang giải thích vui vẻ';

    // Map toneValue (0-100) to descriptive style
    let toneDesc;
    if (toneValue < 30) {
        toneDesc = 'phong cách vui tươi, gần gũi, màu sắc rực rỡ, ngôn ngữ đơn giản dễ hiểu';
    } else if (toneValue > 70) {
        toneDesc = 'phong cách trang trọng, chuyên nghiệp, màu sắc lịch sự (xanh navy, trắng, vàng đồng), ngôn ngữ pháp lý chuẩn mực';
    } else {
        toneDesc = 'phong cách cân bằng, vừa thân thiện vừa chuyên nghiệp, màu sắc hiện đại';
    }

    // Two separate prompts based on illustration type
    let prompt;
    if (illustrationType === 'comic') {
        // 9-panel comic strip prompt — Studio Ghibli style
        prompt = `Xây dựng 1 trang truyện tranh gồm 9 khung hình bố cục rõ ràng. 6 khung đầu xây dựng tình huống thực tế dựa trên nội dung pháp luật sau: "${text}". 3 khung cuối thể hiện kết quả, bài học hoặc hậu quả pháp lý. Nhân vật chính: ${charDesc}. ${toneDesc}. Phong cách nghệ thuật: Studio Ghibli, thẩm mỹ màu nước mềm mại, nhân vật biểu cảm phong phú, ánh sáng ấm áp ở khung cuối. Có chú thích tiếng Việt trong từng khung, chữ rõ ràng, dễ đọc.`;
    } else {
        // Propaganda poster prompt — bold, impactful Vietnamese style
        prompt = `Thiết kế một poster tuyên truyền pháp luật Việt Nam chuyên nghiệp, khổ dọc. Nhân vật chính: ${charDesc}. ${toneDesc}. Nội dung poster phải truyền tải thông điệp pháp lý sau: "${text}". Yêu cầu: Tiêu đề lớn in đậm bằng tiếng Việt ở trên cùng, hình minh họa trung tâm nổi bật, slogan ngắn gọn súc tích ở dưới, logo nhà nước hoặc biểu tượng pháp lý góc dưới. Màu sắc: đỏ-vàng truyền thống Việt Nam hoặc xanh navy trang trọng. Phong cách: hiện đại, sắc nét, in ấn được, cảm hứng từ poster tuyên truyền Việt Nam.`;
    }
     // Use gemini-2.5-flash-image (stable) which supports generateContent with image output
    const model = 'gemini-3.1-flash-image-preview';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    const requestBody = {
        contents: [
            {
                parts: [{ text: prompt }]
            }
        ],
        generationConfig: {
            responseModalities: ['TEXT', 'IMAGE']
        }
    };

    console.log('[Gemini Image] Model:', model);
    console.log('[Gemini Image] Request URL:', url.replace(apiKey, '***'));
    console.log('[Gemini Image] Request Body:', JSON.stringify(requestBody, null, 2));

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        console.log('[Gemini Image] HTTP Status:', response.status, response.statusText);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Gemini Image] Error Response:', errorText);
            return null;
        }

        const data = await response.json();

        // Log response, truncating base64 for readability
        const loggableData = {
            ...data,
            candidates: data.candidates?.map(c => ({
                ...c,
                content: {
                    ...c.content,
                    parts: c.content?.parts?.map(p => ({
                        ...p,
                        inlineData: p.inlineData
                            ? { mimeType: p.inlineData.mimeType, data: `[BASE64 image, length: ${p.inlineData.data?.length}]` }
                            : undefined
                    }))
                }
            }))
        };
        console.log('[Gemini Image] Response Data:', JSON.stringify(loggableData, null, 2));

        // Extract image from the response parts
        const parts = data.candidates?.[0]?.content?.parts;
        if (parts) {
            for (const part of parts) {
                if (part.inlineData?.data) {
                    const mimeType = part.inlineData.mimeType || 'image/png';
                    return `data:${mimeType};base64,${part.inlineData.data}`;
                }
            }
        }

        console.warn('[Gemini Image] No image found in response parts.');
    } catch (error) {
        console.error('[Gemini Image] Error generating image:', error);
    }

    return null;
}
