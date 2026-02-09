// Mock API Service for Legal Chatbot
// Simulates server responses with lawyer and normal person styles

// Sample Q&A data with both styles
const mockResponses = {
    "thuê nhà": {
        lawyer: {
            text: `Theo quy định tại Điều 472 Bộ luật Dân sự 2015, hợp đồng thuê nhà ở là sự thỏa thuận giữa các bên, theo đó bên cho thuê giao nhà ở cho bên thuê sử dụng trong một thời hạn và bên thuê phải trả tiền thuê.

**Các điểm cần lưu ý:**

1. **Hình thức hợp đồng**: Hợp đồng thuê nhà có thời hạn từ 06 tháng trở lên phải được lập thành văn bản (Điều 121, 122 Luật Nhà ở 2014).

2. **Nội dung bắt buộc**: Hợp đồng phải có đầy đủ thông tin về bên cho thuê, bên thuê, đặc điểm nhà ở, giá thuê, thời hạn thuê, quyền và nghĩa vụ các bên.

3. **Đăng ký hợp đồng**: Trường hợp thuê nhà từ 06 tháng trở lên, các bên có nghĩa vụ đăng ký hợp đồng tại cơ quan có thẩm quyền.`,
            comic: "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=250&fit=crop"
        },
        normal: {
            text: `Khi thuê nhà, bạn cần chú ý mấy điều này nhé:

🏠 **Ký hợp đồng bằng văn bản** - Đừng chỉ nói miệng! Nếu thuê từ 6 tháng trở lên thì PHẢI có giấy trắng mực đen.

💰 **Ghi rõ tiền thuê** - Bao nhiêu tiền/tháng, trả ngày nào, có tăng giá không, đặt cọc bao nhiêu.

📝 **Kiểm tra kỹ nhà** - Chụp ảnh tình trạng nhà trước khi dọn vào. Nếu có hỏng hóc gì thì ghi vào biên bản, không là lúc trả nhà bị đổ thừa!

⚡ **Tiền điện nước** - Tính theo đồng hồ riêng hay chung? Giá bao nhiêu? Hỏi kỹ kẻo cuối tháng "méo mặt".

Đơn giản vậy thôi! Có gì không hiểu cứ hỏi tiếp nha! 😊`,
            comic: "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=250&fit=crop"
        }
    },
    "ly hôn": {
        lawyer: {
            text: `Căn cứ Luật Hôn nhân và Gia đình 2014, việc ly hôn được thực hiện theo hai phương thức:

**1. Ly hôn thuận tình (Điều 55)**
- Hai bên tự nguyện ly hôn
- Đã thỏa thuận được việc chia tài sản, nuôi con
- Tòa án công nhận thuận tình ly hôn

**2. Ly hôn theo yêu cầu một bên (Điều 56)**
- Một bên có yêu cầu ly hôn
- Được chấp nhận khi có căn cứ: bạo lực gia đình, vi phạm nghiêm trọng nghĩa vụ vợ chồng, đời sống chung không thể kéo dài

**Về tài sản chung**: Được chia theo thỏa thuận hoặc theo quyết định của Tòa án, căn cứ công sức đóng góp của mỗi bên (Điều 59).

**Về con chung**: Ưu tiên thỏa thuận. Nếu không thỏa thuận được, Tòa án quyết định dựa trên quyền lợi tốt nhất của con (Điều 81).`,
            comic: "https://images.unsplash.com/photo-1590012314607-cda9d9b699ae?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1589578527966-fdac0f44566c?w=400&h=250&fit=crop"
        },
        normal: {
            text: `Ly hôn thì có 2 cách:

💑 **Cách 1: Hai người đồng ý ly hôn**
- Cả hai bàn bạc xong xuôi chuyện chia tài sản, ai nuôi con
- Ra tòa nộp đơn chung
- Nhanh gọn, ít đau đầu hơn

😤 **Cách 2: Một người muốn ly hôn**
- Viết đơn gửi tòa, kể lý do (bị bạo lực, chồng/vợ không còn quan tâm, v.v.)
- Tòa sẽ hòa giải, nếu không được thì xử

**Chia tài sản thế nào?**
- Tốt nhất là tự thỏa thuận
- Không thỏa thuận được thì tòa chia, xem ai đóng góp nhiều hơn

**Con cái thì sao?**
- Ưu tiên để 2 người tự quyết định ai nuôi
- Tòa sẽ xem xét điều kiện ai tốt hơn cho con
- Con dưới 36 tháng thường theo mẹ

Đây là chuyện lớn, nên cân nhắc kỹ và có thể tìm luật sư tư vấn thêm nha! 🙏`,
            comic: "https://images.unsplash.com/photo-1590012314607-cda9d9b699ae?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1589578527966-fdac0f44566c?w=400&h=250&fit=crop"
        }
    },
    "tai nạn giao thông": {
        lawyer: {
            text: `Theo quy định của Bộ luật Hình sự 2015 (sửa đổi 2017) và Luật Giao thông đường bộ 2008:

**Trách nhiệm hình sự** (Điều 260 BLHS):
- Gây thiệt hại cho 01 người với tỷ lệ tổn thương cơ thể từ 61% trở lên
- Gây chết người
- Gây thiệt hại về tài sản từ 100 triệu đồng trở lên

**Nghĩa vụ khi xảy ra tai nạn** (Điều 38 Luật GTĐB):
1. Dừng xe ngay, giữ nguyên hiện trường
2. Cứu giúp người bị nạn
3. Báo cho cơ quan công an gần nhất
4. Có mặt khi cơ quan chức năng yêu cầu

**Quyền yêu cầu bồi thường**:
- Chi phí cứu chữa, phục hồi sức khỏe
- Thu nhập thực tế bị mất
- Tổn thất tinh thần (theo Điều 590-592 BLDS 2015)`,
            comic: "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=250&fit=crop"
        },
        normal: {
            text: `Bị tai nạn giao thông thì làm gì? Đây là các bước:

🚨 **Ngay lập tức:**
1. Dừng xe lại, ĐỪNG BỎ CHẠY (bỏ chạy là thêm tội!)
2. Gọi cấp cứu 115 nếu có người bị thương
3. Gọi công an 113

📸 **Bảo vệ chứng cứ:**
- Chụp ảnh hiện trường, vị trí xe
- Xin số điện thoại người làm chứng
- Giữ nguyên hiện trường, đừng di chuyển xe

💰 **Về bồi thường:**
Người gây tai nạn phải đền bù:
- Tiền viện phí, thuốc men
- Tiền lương bị mất (nếu phải nghỉ làm)
- Tiền sửa xe, đồ đạc hư hỏng

⚠️ **Lưu ý quan trọng:**
Nếu gây chết người hoặc bị thương nặng → có thể bị truy cứu hình sự!

Nên giữ bình tĩnh và hợp tác với công an nhé! 💪`,
            comic: "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=250&fit=crop"
        }
    },
    "di chúc": {
        lawyer: {
            text: `Theo Bộ luật Dân sự 2015, di chúc là sự thể hiện ý chí của cá nhân nhằm chuyển tài sản của mình cho người khác sau khi chết.

**Điều kiện hợp pháp của di chúc** (Điều 630):
1. Người lập di chúc phải minh mẫn, sáng suốt
2. Không bị lừa dối, đe dọa, cưỡng ép
3. Nội dung không trái pháp luật, đạo đức xã hội

**Hình thức di chúc** (Điều 628):
- Di chúc bằng văn bản (có công chứng hoặc không)
- Di chúc miệng (chỉ trong trường hợp tính mạng bị đe dọa)

**Lưu ý về người thừa kế không phụ thuộc vào nội dung di chúc** (Điều 644):
- Con chưa thành niên, cha/mẹ, vợ/chồng
- Con đã thành niên mà không có khả năng lao động
→ Được hưởng ít nhất 2/3 suất thừa kế theo pháp luật`,
            comic: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&h=250&fit=crop"
        },
        normal: {
            text: `Viết di chúc không khó đâu, nhưng cần lưu ý mấy điều:

📝 **Ai được viết di chúc?**
- Phải đủ 18 tuổi và tỉnh táo, minh mẫn
- Không ai ép buộc viết

✍️ **Viết di chúc như thế nào?**
- Tự tay viết hoặc đánh máy đều được
- Ghi rõ: ngày tháng, họ tên, ai được hưởng gì
- Ký tên cuối trang

🔒 **Muốn chắc ăn thì:**
- Ra phòng công chứng để công chứng di chúc
- Có 2 người làm chứng

⚠️ **Quan trọng:**
Dù bạn viết gì thì những người sau VẪN ĐƯỢC HƯỞNG ít nhất 2/3 phần:
- Vợ/chồng
- Cha mẹ già
- Con nhỏ hoặc con tàn tật

Ví dụ: Bạn có 900 triệu, có 1 vợ + 1 con. Dù bạn viết để hết cho người khác, vợ con vẫn được hưởng ít nhất khoảng 200 triệu mỗi người!`,
            comic: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&h=250&fit=crop"
        }
    },
    default: {
        lawyer: {
            text: `Cảm ơn bạn đã đặt câu hỏi. Để có thể tư vấn chính xác và đầy đủ nhất, tôi cần thêm thông tin chi tiết về vấn đề của bạn.

Tuy nhiên, dựa trên câu hỏi, tôi xin được lưu ý một số nguyên tắc pháp lý cơ bản:

1. **Nguyên tắc thượng tôn pháp luật**: Mọi hành vi đều phải tuân thủ quy định pháp luật hiện hành.

2. **Quyền và nghĩa vụ**: Khi tham gia bất kỳ quan hệ pháp luật nào, các bên đều có quyền và nghĩa vụ tương ứng.

3. **Tư vấn chuyên sâu**: Với các vấn đề phức tạp, tôi khuyến nghị bạn nên tham khảo ý kiến của luật sư có chuyên môn.

Bạn có thể cung cấp thêm chi tiết để tôi hỗ trợ tốt hơn không?`,
            comic: "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=400&h=250&fit=crop"
        },
        normal: {
            text: `Hmm, câu hỏi hay đấy! 🤔

Mình sẽ cố gắng giải thích đơn giản nhất có thể nhé.

Mỗi vấn đề pháp lý thường có nhiều khía cạnh khác nhau, tùy thuộc vào:
- Hoàn cảnh cụ thể của bạn
- Các bên liên quan
- Quy định pháp luật áp dụng

💡 **Mẹo nhỏ**: Khi gặp vấn đề pháp lý, hãy:
1. Ghi chép lại mọi thứ liên quan
2. Giữ các giấy tờ, tin nhắn, email làm bằng chứng
3. Tìm hiểu quy định trước khi hành động

Bạn có thể kể rõ hơn tình huống của mình được không? Mình sẽ giúp cụ thể hơn! 😊`,
            comic: "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400&h=250&fit=crop",
            poster: "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=400&h=250&fit=crop"
        }
    }
};

// Blend response based on tone slider (0 = casual, 100 = legal)
function blendResponse(lawyerText, normalText, toneValue) {
    // For simplicity, we'll return the appropriate text based on threshold
    // In a real implementation, this could use AI to blend the styles
    if (toneValue < 30) {
        return normalText;
    } else if (toneValue > 70) {
        return lawyerText;
    } else {
        // For middle values, add a note about the tone
        const prefix = toneValue < 50
            ? "Mình sẽ giải thích theo cách dễ hiểu nhưng vẫn đảm bảo đúng pháp luật nhé:\n\n"
            : "Tôi sẽ trình bày vấn đề một cách cân bằng giữa chuyên môn pháp lý và sự dễ hiểu:\n\n";

        return toneValue < 50
            ? prefix + normalText
            : prefix + lawyerText;
    }
}

// Find matching response based on keywords
function findResponse(question) {
    const questionLower = question.toLowerCase();

    for (const [keyword, responses] of Object.entries(mockResponses)) {
        if (keyword !== 'default' && questionLower.includes(keyword)) {
            return responses;
        }
    }

    return mockResponses.default;
}

// Main mock API function
export async function sendMessage(question, options = {}) {
    const {
        character = 'normal', // 'lawyer' or 'normal'
        toneValue = 50,       // 0-100
        illustrationType = 'none' // 'none', 'comic', or 'poster'
    } = options;

    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1500));

    const responses = findResponse(question);
    const characterResponse = responses[character];

    // Get blended text based on tone
    const responseText = character === 'lawyer'
        ? blendResponse(responses.lawyer.text, responses.normal.text, toneValue)
        : blendResponse(responses.lawyer.text, responses.normal.text, toneValue);

    // Build response object
    const response = {
        text: character === 'lawyer'
            ? (toneValue > 50 ? responses.lawyer.text : blendResponse(responses.lawyer.text, responses.normal.text, toneValue))
            : (toneValue < 50 ? responses.normal.text : blendResponse(responses.lawyer.text, responses.normal.text, toneValue)),
        character,
        timestamp: new Date().toISOString()
    };

    // Add illustration if requested
    if (illustrationType !== 'none' && characterResponse[illustrationType]) {
        response.illustration = {
            type: illustrationType,
            url: characterResponse[illustrationType],
            caption: illustrationType === 'comic'
                ? '📖 Minh họa truyện tranh - Dễ nhớ, dễ chia sẻ!'
                : '📢 Poster tuyên truyền - Nâng cao nhận thức pháp luật!'
        };
    }

    return response;
}

// Get suggested questions
export function getSuggestedQuestions() {
    return [
        "Thuê nhà cần lưu ý gì?",
        "Thủ tục ly hôn như thế nào?",
        "Bị tai nạn giao thông phải làm sao?",
        "Viết di chúc thế nào cho đúng?"
    ];
}
