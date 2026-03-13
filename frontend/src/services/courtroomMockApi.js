/**
 * Mock API cho Virtual Courtroom
 * Cung cấp dữ liệu mẫu cho các kịch bản, coach, huy hiệu...
 */

// Danh sách kịch bản
export const scenarios = [
    {
        id: 4,
        name: 'Cố ý gây thương tích có tính chất côn đồ',
        difficulty: 2,
        difficultyLabel: 'Trung bình',
        duration: 20,
        skills: ['Phân tích chứng cứ', 'Tranh luận', 'Viện dẫn điều luật'],
        description: 'Bị cáo tấn công người khác vì khó chịu với tiếng nẹt pô xe, gây thương tích nặng.',
        summary: `Anh Thắng đang đi bộ trên đường thì khó chịu với tiếng nẹt pô xe máy của anh Đức. Anh Thắng đã lao ra tấn công anh Đức, gây thương tích với tỷ lệ tổn thương cơ thể là 60%. Viện kiểm sát truy tố anh Thắng về tội cố ý gây thương tích với tình tiết tăng nặng "phạm tội có tính chất côn đồ".

Các bên liên quan:
- Bên buộc tội: Viện kiểm sát (đại diện cho anh Đức — bị hại)
- Bên bào chữa: Luật sư của anh Thắng (bị cáo)

Yêu cầu: Xác định anh Thắng có phạm tội với tính chất côn đồ hay không.`,
        facts: [
            'Sự việc xảy ra ngày 10/02/2025 trên đường Nguyễn Trãi, quận 5',
            'Anh Đức nẹt pô xe khi đi qua, không có va chạm trước đó',
            'Anh Thắng lao ra tấn công anh Đức bằng tay không',
            'Tỷ lệ tổn thương cơ thể của anh Đức: 60%',
            'Hai bên không quen biết, không có mâu thuẫn từ trước',
            'Theo Nghị quyết 04/2025/NQ-HĐTP: phạm tội côn đồ là coi thường pháp luật, sẵn sàng dùng vũ lực vì lý do nhỏ nhặt'
        ]
    },
    {
        id: 5,
        name: 'Chuẩn bị hung khí đi đánh nhau',
        difficulty: 1,
        difficultyLabel: 'Dễ',
        duration: 15,
        skills: ['Tranh luận cơ bản', 'Viện dẫn điều luật'],
        description: 'Nhóm thanh niên chuẩn bị hung khí để gây thương tích nhưng bị phát hiện trước khi hành động.',
        summary: `Do mâu thuẫn từ trước, nhóm 4 thanh niên gồm Tùng, Hải, Nam và Phong đã bàn bạc và chuẩn bị các loại hung khí (búa đinh, dao phay, kiếm, tuýt sắt) nhằm tấn công anh Quang. Khi đang trên đường đến nhà anh Quang thì bị công an phát hiện và bắt giữ.

Các bên liên quan:
- Bên buộc tội: Viện kiểm sát
- Bên bào chữa: Luật sư của nhóm bị cáo (Tùng, Hải, Nam, Phong)

Yêu cầu: Xác định nhóm bị cáo có đủ yếu tố cấu thành tội cố ý gây thương tích ở giai đoạn chuẩn bị phạm tội hay không.`,
        facts: [
            'Nhóm 4 người có mâu thuẫn với anh Quang từ 2 tuần trước',
            'Hung khí thu giữ: 1 búa đinh, 2 dao phay, 1 kiếm, 2 tuýt sắt dài',
            'Nhóm bị bắt cách nhà anh Quang khoảng 500m',
            'Có tin nhắn nhóm chat bàn bạc kế hoạch tấn công',
            'Chưa có hành vi gây thương tích thực tế nào xảy ra',
            'Khoản 6, Điều 134 BLHS 2015 quy định về chuẩn bị phạm tội cố ý gây thương tích'
        ]
    },
    {
        id: 6,
        name: 'Cho vay nặng lãi trong giao dịch dân sự',
        difficulty: 2,
        difficultyLabel: 'Trung bình',
        duration: 25,
        skills: ['Phân tích chứng cứ', 'Tranh luận', 'Tính toán pháp lý'],
        description: 'Bị cáo bị truy tố về tội cho vay nặng lãi với lãi suất 5%/tháng.',
        summary: `Ông Phú cho nhiều người vay tiền với lãi suất 5%/tháng (tương đương 60%/năm). Tổng số tiền cho vay khoảng 2 tỷ đồng, thu lợi bất chính ước tính 150 triệu đồng trong 1 năm. Viện kiểm sát truy tố ông Phú về tội cho vay lãi nặng trong giao dịch dân sự.

Các bên liên quan:
- Bên buộc tội: Viện kiểm sát (đại diện cho các bị hại)
- Bên bào chữa: Luật sư của ông Phú (bị cáo)

Yêu cầu: Xác định hành vi cho vay với lãi suất 5%/tháng có đủ yếu tố cấu thành tội cho vay nặng lãi hay không.`,
        facts: [
            'Lãi suất cho vay: 5%/tháng, tương đương 60%/năm',
            'Lãi suất tối đa theo Điều 468 BLDS 2015: 20%/năm',
            'Tội cho vay nặng lãi (Điều 201 BLHS 2015): lãi suất gấp 5 lần mức tối đa (tức >= 100%/năm)',
            'Lãi suất 60%/năm = gấp 3 lần mức tối đa, chưa đạt ngưỡng gấp 5 lần',
            'Ông Phú thu lợi bất chính khoảng 150 triệu đồng trong 1 năm',
            'Ông Phú chưa từng bị xử phạt hành chính về hành vi cho vay nặng lãi trước đó'
        ]
    },
    {
        id: 7,
        name: 'Sa thải lao động nữ mang thai trái pháp luật',
        difficulty: 2,
        difficultyLabel: 'Trung bình',
        duration: 25,
        skills: ['Tranh luận', 'Viện dẫn điều luật', 'Phản đối'],
        description: 'Công ty sa thải nhân viên nữ đang mang thai, bị kiện về tội sa thải trái pháp luật.',
        summary: `Chị Hương làm việc tại Công ty TNHH Thành Phát từ năm 2018 theo hợp đồng không xác định thời hạn. Ngày 04/08/2024, công ty sa thải chị với lý do vắng mặt liên tục 5 ngày không lý do chính đáng. Tại thời điểm bị sa thải, chị Hương đang mang thai tháng thứ 4. Chị Hương khởi kiện công ty.

Các bên liên quan:
- Nguyên đơn: Chị Hương (người lao động)
- Bị đơn: Công ty TNHH Thành Phát (người sử dụng lao động)

Yêu cầu: Xác định việc sa thải có trái pháp luật không và yêu cầu bồi thường.`,
        facts: [
            'Hợp đồng lao động không xác định thời hạn, ký từ năm 2018',
            'Chị Hương đang mang thai tháng thứ 4 tại thời điểm bị sa thải',
            'Lý do sa thải: vắng mặt liên tục 5 ngày không lý do chính đáng',
            'Điểm d Khoản 4 Điều 122 BLLĐ 2019: không được kỷ luật lao động với người mang thai',
            'Điều 162 BLHS 2015: tội sa thải người lao động trái pháp luật nếu vì vụ lợi hoặc động cơ cá nhân',
            'Công ty có email nội bộ thể hiện ý định thay thế chị Hương bằng nhân sự mới với mức lương thấp hơn'
        ]
    },
    {
        id: 8,
        name: 'Làm giả chứng thư bảo lãnh ngân hàng',
        difficulty: 3,
        difficultyLabel: 'Khó',
        duration: 35,
        skills: ['Tranh luận nâng cao', 'Phân tích chứng cứ', 'Chiến lược', 'Viện dẫn điều luật'],
        description: 'Chủ doanh nghiệp làm giả chứng thư bảo lãnh ngân hàng để ký hợp đồng mua bán.',
        summary: `Ông Dũng — chủ Doanh nghiệp tư nhân Minh Quang — trúng thầu dự án xây dựng khu nhà tập thể. Để Công ty Hòa Phát tin tưởng ký hợp đồng cung cấp vật liệu xây dựng trị giá 5 tỷ đồng, ông Dũng đã làm giả chứng thư bảo lãnh của Ngân hàng Á Châu. Công ty Hòa Phát phát hiện và trình báo công an.

Các bên liên quan:
- Bên buộc tội: Viện kiểm sát (đại diện cho Công ty Hòa Phát và Ngân hàng Á Châu)
- Bên bào chữa: Luật sư của ông Dũng (bị cáo)

Yêu cầu: Xác định ông Dũng phạm tội lừa đảo chiếm đoạt tài sản hay tội làm giả tài liệu.`,
        facts: [
            'Ông Dũng trúng thầu dự án xây dựng hợp pháp',
            'Chứng thư bảo lãnh giả mạo Ngân hàng Á Châu, giá trị 5 tỷ đồng',
            'Công ty Hòa Phát đã giao vật liệu đợt 1 trị giá 1,2 tỷ đồng trước khi phát hiện',
            'Ông Dũng khai nhận chỉ muốn tạo lòng tin, dự định thanh toán đầy đủ sau khi nhận tiền dự án',
            'Điều 174 BLHS 2015: tội lừa đảo chiếm đoạt tài sản (nếu có ý đồ chiếm đoạt)',
            'Điều 341 BLHS 2015: tội làm giả tài liệu của cơ quan, tổ chức (nếu không có ý đồ chiếm đoạt)',
            'Tài khoản doanh nghiệp còn 800 triệu đồng tại thời điểm bị phát hiện'
        ]
    },
    {
        id: 9,
        name: 'Vô ý gây thương tích nghiêm trọng',
        difficulty: 1,
        difficultyLabel: 'Dễ',
        duration: 15,
        skills: ['Tranh luận cơ bản', 'Thu thập chứng cứ'],
        description: 'Vô tình gây mù mắt bạn trong bữa tiệc sinh nhật do tăm cố định bánh kem.',
        summary: `Trong bữa tiệc sinh nhật, Minh Khôi (22 tuổi) đùa giỡn và ấn đầu bạn mình — Thanh Tùng — vào bánh kem. Tăm cố định bánh kem vô tình đâm vào mắt trái Thanh Tùng, gây mù vĩnh viễn một bên mắt. Gia đình Thanh Tùng yêu cầu truy cứu trách nhiệm hình sự.

Các bên liên quan:
- Bên buộc tội: Viện kiểm sát (đại diện cho Thanh Tùng — bị hại)
- Bên bào chữa: Luật sư của Minh Khôi (bị cáo)

Yêu cầu: Xác định Minh Khôi có phạm tội vô ý gây thương tích hay không và mức hình phạt.`,
        facts: [
            'Sự việc xảy ra tại bữa tiệc sinh nhật ngày 20/01/2025',
            'Minh Khôi ấn đầu Thanh Tùng vào bánh kem với mục đích đùa vui',
            'Tăm tre cố định tầng bánh kem đâm vào mắt trái Thanh Tùng',
            'Kết quả giám định: mù vĩnh viễn mắt trái, tỷ lệ tổn thương cơ thể 45%',
            'Điều 138 BLHS 2015: tội vô ý gây thương tích (tỷ lệ >= 31%)',
            'Minh Khôi không hề biết có tăm cố định trong bánh kem'
        ]
    }
]

// Danh sách huy hiệu
export const allBadges = [
    { id: 'excellent', name: 'Luật sư xuất sắc', icon: '🥇', description: 'Đạt tổng điểm ≥ 450/500' },
    { id: 'evidence', name: 'Bậc thầy chứng cứ', icon: '📊', description: 'Điểm sử dụng chứng cứ ≥ 90' },
    { id: 'persuader', name: 'Nhà hùng biện', icon: '🎤', description: 'Điểm thuyết phục ≥ 90' },
    { id: 'speed', name: 'Tốc độ ánh sáng', icon: '⚡', description: 'Hoàn thành tất cả vòng, còn ≥ 40% thời gian' },
    { id: 'accurate', name: 'Chính xác tuyệt đối', icon: '🎯', description: 'Điểm pháp lý ≥ 95' },
    { id: 'polite', name: 'Lịch thiệp', icon: '🤝', description: 'Điểm phong thái ≥ 95' },
    { id: 'first_win', name: 'Chiến thắng đầu tiên', icon: '🏆', description: 'Thắng phiên tòa đầu tiên (≥ 350 điểm)' },
    { id: 'streak_3', name: 'Chuỗi 3 trận', icon: '🔥', description: 'Thắng 3 phiên liên tiếp' },
    { id: 'master', name: 'Bậc thầy tranh tụng', icon: '👑', description: 'Hoàn thành 10 phiên tòa' },
    { id: 'defender', name: 'Người bảo vệ', icon: '🛡️', description: 'Thắng với vai trò bào chữa' },
    { id: 'prosecutor', name: 'Công tố viên', icon: '⚔️', description: 'Thắng với vai trò nguyên đơn' },
    { id: 'comeback', name: 'Lội ngược dòng', icon: '🌊', description: 'Thắng dù có ≥ 2 hạng mục điểm thấp' }
]

// Mock user badges (localStorage in real app)
export const getUserBadges = () => {
    const stored = localStorage.getItem('userBadges')
    return stored ? JSON.parse(stored) : []
}

export const addUserBadge = (badgeId) => {
    const badges = getUserBadges()
    const existing = badges.find(b => b.id === badgeId)
    if (existing) {
        existing.count++
        existing.lastEarned = new Date().toISOString()
    } else {
        badges.push({ id: badgeId, count: 1, lastEarned: new Date().toISOString() })
    }
    localStorage.setItem('userBadges', JSON.stringify(badges))
    return badges
}

import { evaluateSession } from './backendApi'
// Cập nhật: Gọi Gemini API thực tế thay vì mock cứng
import { generateGeminiResponse } from './geminiService'

export const getOpponentResponse = async (round, userArgument, scenario, userRole = 'defendant', messages = []) => {
    // Dự phòng fallback
    const fallbackResponses = [
        `Tôi phản đối lập luận này. Theo quy định pháp luật, bên nguyên đơn chưa cung cấp đủ bằng chứng.`,
        `Các chứng cứ được đưa ra không đủ tính thuyết phục. Tôi yêu cầu tòa xem xét lại.`,
        `Quan điểm này mâu thuẫn với các tiền lệ pháp lý đã có.`,
        `Tôi đề nghị tòa bác bỏ yêu cầu của đối phương vì không có căn cứ pháp lý rõ ràng.`
    ];
    const fallback = fallbackResponses[round % fallbackResponses.length];

    // Xác định vai trò đối phương (ngược lại với người dùng)
    const isDefendant = userRole === 'defendant'
    const opponentRole = isDefendant
        ? 'Luật sư Nguyên đơn (bảo vệ quyền lợi cho người bị hại/nguyên đơn)'
        : 'Luật sư Bào chữa (bảo vệ quyền lợi cho bị đơn/bị cáo)'
    const userRoleLabel = isDefendant
        ? 'Luật sư Bào chữa'
        : 'Luật sư Nguyên đơn'

    // Lịch sử trò chuyện gần nhất (tối đa 4 tin nhắn)
    const recentMessages = messages
        .filter(m => m.type === 'user' || m.type === 'opponent')
        .slice(-4)
    const conversationLog = recentMessages.length > 0
        ? recentMessages.map(m =>
            m.type === 'user' ? `  [${userRoleLabel}]: ${m.text}` : `  [${opponentRole.split(' (')[0]}]: ${m.text}`
        ).join('\n')
        : ''
    const conversationContext = conversationLog
        ? `\nDIỄN BIẾN PHIÊN TÒA TRƯỚC ĐÓ:\n${conversationLog}\n`
        : ''

    const prompt = `Bạn là ${opponentRole} trong một phiên tòa giả định tại Việt Nam. Bạn sừng sỏ, sắc sảo, và luôn tìm cách bảo vệ thân chủ của mình.

THÔNG TIN VỤ ÁN:
- Tên vụ án: ${scenario.name}
- Tóm tắt: ${scenario.summary}
- Sự kiện pháp lý:
${(scenario.facts || []).map(f => `  • ${f}`).join('\n')}
${conversationContext}
VÒNG TRANH LUẬN: ${round}/4

${userRoleLabel} (đối phương của bạn) vừa lập luận:
"${userArgument}"

NHIỆM VỤ:
Với vai trò ${opponentRole}, hãy phản biện lại lập luận trên:
1. Dựa trên SỰ KIỆN PHÁP LÝ cụ thể của vụ án để phản bác — chỉ ra mâu thuẫn, thiếu sót, hoặc cách diễn giải khác có lợi cho thân chủ bạn.
2. ${isDefendant
        ? 'Nhấn mạnh quyền lợi hợp pháp của nguyên đơn, chứng minh thiệt hại thực tế, và yêu cầu bồi thường xứng đáng.'
        : 'Bảo vệ thân chủ bằng cách chỉ ra đối phương chưa đủ căn cứ, hoặc tình tiết giảm nhẹ.'}
3. Có thể trích dẫn điều luật cụ thể (Bộ luật Dân sự 2015, Bộ luật Hình sự 2015, Luật Hôn nhân Gia đình...) nếu phù hợp.
4. Xưng hô "Tôi" hoặc "Thưa Hội đồng xét xử, tôi...".

Độ dài: Ngắn gọn, súc tích (3-5 câu). Đi thẳng vào phản bác, KHÔNG giải thích dài dòng. KHÔNG nhắc lại prompt.`

    console.log('[Opponent] Calling Gemini API:', {
        round,
        userRole,
        opponentRole: opponentRole.split(' (')[0],
        scenario: scenario?.name,
        userArgument: userArgument?.substring(0, 100) + (userArgument?.length > 100 ? '...' : ''),
        recentMessagesCount: recentMessages.length,
        promptLength: prompt.length
    })

    const replyText = await generateGeminiResponse(prompt, fallback);

    console.log('[Opponent] Response received:', {
        responseLength: replyText?.length,
        responsePreview: replyText?.substring(0, 150) + (replyText?.length > 150 ? '...' : '')
    })

    return {
        text: replyText,
        character: 'opponent'
    };
};

// Coach feedback sử dụng Gemini 2.5 Flash
export const getCoachFeedback = async (content, coachType, tone, scenario, userRole, feedbackType, messages = []) => {
    const fallbackFeedback = coachType === 'lawyer'
        ? 'Luận điểm này có căn cứ pháp lý vững chắc. Hãy bổ sung thêm điều luật cụ thể.'
        : 'Ý tưởng hay đấy! Thử giải thích đơn giản hơn một chút nhé.'

    // Parse content từ StrategyBuilder
    let strategy
    try {
        strategy = JSON.parse(content)
    } catch {
        strategy = { arguments: [], evidences: [] }
    }

    const argumentsList = (strategy.arguments || [])
        .filter(a => a.text)
        .map((a, i) => `  ${i + 1}. ${a.text}`)
        .join('\n') || '  (Chưa có luận điểm)'

    const evidencesList = (strategy.evidences || [])
        .map(e => {
            const linkedArgs = (e.linkedArguments || [])
                .map(argId => {
                    const idx = (strategy.arguments || []).findIndex(a => a.id === argId)
                    return idx >= 0 ? `Luận điểm ${idx + 1}` : null
                })
                .filter(Boolean)
            const linkInfo = linkedArgs.length > 0 ? ` (liên kết: ${linkedArgs.join(', ')})` : ''
            return `  - ${e.name}${linkInfo}`
        })
        .join('\n') || '  (Chưa có chứng cứ)'

    // Xác định vai trò người dùng
    const isDefendant = userRole === 'defendant'
    const userRoleLabel = isDefendant ? 'Luật sư Bào chữa (bảo vệ bị đơn/bị cáo)' : 'Luật sư Nguyên đơn (bảo vệ người bị hại)'
    const oppositeRoleLabel = isDefendant ? 'phía nguyên đơn' : 'phía bị đơn'

    // Xác định phong cách dựa trên tone (0 = đời thường, 100 = pháp lý)
    let toneInstruction
    if (tone < 30) {
        toneInstruction = `PHONG CÁCH GIAO TIẾP:
Nói chuyện thật tự nhiên, như đang ngồi cà phê tư vấn cho bạn bè vậy. Dùng từ ngữ bình dân, ví dụ thực tế từ cuộc sống hàng ngày. Tránh dùng thuật ngữ pháp lý, nếu buộc phải nhắc thì giải thích bằng ngôn ngữ đời thường. Có thể dùng các cách nói như "nói thật nhé", "theo mình thấy", "cái này quan trọng nè". Mục tiêu là người không biết gì về luật cũng hiểu được ngay.`
    } else if (tone < 70) {
        toneInstruction = `PHONG CÁCH GIAO TIẾP:
Sử dụng ngôn ngữ cân bằng giữa chuyên nghiệp và dễ hiểu. Có thể dùng thuật ngữ pháp lý nhưng kèm giải thích ngắn gọn trong ngoặc. Giọng văn thân thiện nhưng vẫn đáng tin cậy.`
    } else {
        toneInstruction = `PHONG CÁCH GIAO TIẾP:
Sử dụng ngôn ngữ pháp lý chuyên nghiệp, chính xác. Trích dẫn điều luật, tiền lệ pháp lý cụ thể nếu có thể (ví dụ: Điều X Bộ luật Dân sự 2015, Điều Y Bộ luật Hình sự 2015). Phong cách trang trọng, nghiêm túc như đang trao đổi giữa các luật sư.`
    }

    // Xác định vai trò coach dựa trên loại coach VÀ vai trò người dùng
    let coachRole
    if (coachType === 'lawyer') {
        coachRole = `Bạn là một Luật sư cố vấn giàu kinh nghiệm tại Việt Nam, chuyên tư vấn chiến lược tranh tụng.
Người bạn đang hỗ trợ là ${userRoleLabel}. Nhiệm vụ của bạn là giúp họ xây dựng chiến lược tốt nhất để ${isDefendant ? 'bào chữa, bảo vệ quyền lợi cho thân chủ (bị đơn/bị cáo)' : 'buộc tội, bảo vệ quyền lợi cho thân chủ (nguyên đơn/người bị hại)'}.
Bạn đứng về phía họ, phân tích điểm mạnh/yếu và gợi ý cách ${isDefendant ? 'phản bác lập luận của nguyên đơn' : 'củng cố chứng cứ buộc tội và phản bác lập luận bào chữa'}.`
    } else {
        coachRole = `Bạn là một người bạn tốt bụng, nhiệt tình, đã từng trải qua vài vụ kiện nên có chút kinh nghiệm thực tế (không phải luật sư chuyên nghiệp).
Bạn bè của bạn đang đóng vai ${userRoleLabel} trong một phiên tòa. Bạn muốn giúp họ hết sức mình bằng cách chia sẻ góc nhìn thực tế, kinh nghiệm đời thường.
Nói chuyện thoải mái, chân thành, đôi khi hài hước. Dùng ví dụ từ cuộc sống để giải thích. Thay vì trích dẫn điều luật, hãy nói kiểu "theo mình biết thì...", "hồi trước mình thấy người ta hay làm thế này...".
Mục tiêu là giúp bạn bè tự tin hơn và chuẩn bị tốt hơn cho phiên tòa.`
    }

    // Thông tin kịch bản
    let scenarioContext = ''
    if (scenario) {
        scenarioContext = `
THÔNG TIN VỤ ÁN:
- Tên vụ án: ${scenario.name}
- Tóm tắt: ${scenario.summary}
- Sự kiện pháp lý:
${(scenario.facts || []).map(f => `  • ${f}`).join('\n')}
`
    }

    // Trích xuất lịch sử cuộc trò chuyện (nếu có)
    const recentMessages = messages
        .filter(m => m.type === 'user' || m.type === 'opponent')
        .slice(-6)
    const conversationLog = recentMessages.length > 0
        ? recentMessages.map(m =>
            m.type === 'user' ? `  [Bạn]: ${m.text}` : `  [Đối phương]: ${m.text}`
        ).join('\n')
        : ''

    // Tìm lập luận gần nhất của đối phương
    const lastOpponentMsg = [...messages].reverse().find(m => m.type === 'opponent')

    // Xây dựng prompt theo từng loại feedback
    let taskSection = ''

    if (feedbackType === 'openingSuggestion') {
        taskSection = `Dựa trên TÓM TẮT VỤ ÁN và SỰ KIỆN PHÁP LÝ ở trên, với tư cách là người hỗ trợ cho ${userRoleLabel}, hãy gợi ý 2-3 câu mở đầu ấn tượng mà luật sư có thể sử dụng khi trình bày trước tòa.

Yêu cầu cho mỗi câu mở đầu:
- Phù hợp với vai trò ${isDefendant ? 'bào chữa (bảo vệ quyền lợi bị đơn)' : 'nguyên đơn (đòi quyền lợi cho thân chủ)'}.
- Tham chiếu trực tiếp đến sự kiện pháp lý cụ thể trong vụ án (ngày tháng, số tiền, hành vi vi phạm...).
- Tạo ấn tượng mạnh với Hội đồng xét xử ngay từ đầu.
- Dẫn dắt tự nhiên vào luận điểm chính mà luật sư đã chuẩn bị.

Đưa ra mỗi câu mở đầu dưới dạng trích dẫn trực tiếp (trong ngoặc kép), kèm giải thích ngắn tại sao câu đó hiệu quả.`
    } else if (feedbackType === 'evidenceReminder') {
        taskSection = `Dựa trên LUẬN ĐIỂM và CHỨNG CỨ đã chuẩn bị, với tư cách là người hỗ trợ cho ${userRoleLabel}, hãy phân tích và nhắc nhở:

1. CHỨNG CỨ ĐÃ CÓ — chứng cứ nào nên được nhấn mạnh nhất khi trình bày trước tòa? Tại sao nó có sức thuyết phục?
2. CHỨNG CỨ CÒN THIẾU — để ${isDefendant ? 'bào chữa vững chắc hơn' : 'buộc tội thuyết phục hơn'}, cần bổ sung chứng cứ gì? (ví dụ: văn bản, nhân chứng, giám định, hình ảnh...)
3. CÁCH SỬ DỤNG — gợi ý cách trình bày chứng cứ sao cho liên kết chặt chẽ với từng luận điểm, tạo logic thuyết phục cho Hội đồng xét xử.
4. THỨ TỰ TRÌNH BÀY — nên đưa ra chứng cứ nào trước, chứng cứ nào sau để tạo hiệu ứng tốt nhất.`
    } else if (feedbackType === 'autoObjection') {
        const opponentContext = lastOpponentMsg
            ? `\nLẬP LUẬN GẦN NHẤT CỦA ĐỐI PHƯƠNG:\n"${lastOpponentMsg.text}"\n`
            : ''
        const conversationContext = conversationLog
            ? `\nDIỄN BIẾN PHIÊN TÒA GẦN ĐÂY:\n${conversationLog}\n`
            : ''

        taskSection = `${conversationContext}${opponentContext}
Với tư cách là người hỗ trợ cho ${userRoleLabel}, hãy soạn sẵn câu trả lời/phản đối dựa trên lập luận gần nhất của đối phương.

Yêu cầu:
1. ${lastOpponentMsg ? 'Phân tích điểm yếu trong lập luận gần nhất của đối phương.' : 'Dự đoán các lập luận mà đối phương có thể đưa ra dựa trên sự kiện vụ án.'}
2. Soạn 2-3 câu phản đối/trả lời đanh thép dưới dạng trích dẫn trực tiếp (trong ngoặc kép) mà luật sư có thể nói ngay.
3. Mỗi câu phản đối phải nêu rõ: lý do phản đối + căn cứ pháp lý hoặc sự kiện thực tế.
4. Câu trả lời phải ${isDefendant ? 'bảo vệ thân chủ và phản bác lập luận buộc tội' : 'củng cố yêu cầu khởi kiện và bác bỏ lý lẽ bào chữa'}.`
    } else if (feedbackType === 'riskWarning') {
        const conversationContext = conversationLog
            ? `\nDIỄN BIẾN PHIÊN TÒA GẦN ĐÂY:\n${conversationLog}\n`
            : ''

        taskSection = `${conversationContext}
Dựa trên diễn biến phiên tòa và chiến lược hiện tại, với tư cách là người hỗ trợ cho ${userRoleLabel}, hãy phân tích RỦI RO:

1. ĐIỂM YẾU BỊ LỘ — qua các lập luận đã đưa ra, ${oppositeRoleLabel} có thể nhận ra và khai thác điểm yếu nào?
2. BẪY CỦA ĐỐI PHƯƠNG — ${oppositeRoleLabel} có thể đang dẫn dắt cuộc tranh luận theo hướng nào bất lợi?
3. SAI LẦM CẦN TRÁNH — những sai lầm phổ biến trong tình huống này mà luật sư cần cảnh giác.
4. CÁCH PHÒNG THỦ — gợi ý cụ thể cách xử lý nếu gặp tình huống bất lợi, cách xoay chuyển tình thế.`
    } else {
        taskSection = `Với tư cách là người hỗ trợ cho ${userRoleLabel}, hãy GỢI Ý giúp người dùng xây dựng luận điểm cho vụ án này:

1. GỢI Ý LUẬN ĐIỂM — Dựa trên sự kiện vụ án và vai trò ${isDefendant ? 'bào chữa' : 'nguyên đơn'}, gợi ý 2-3 luận điểm mạnh mà người dùng nên sử dụng. Mỗi luận điểm cần nêu rõ ý chính và căn cứ.
2. HƯỚNG LẬP LUẬN — Gợi ý cách triển khai từng luận điểm: nên nhấn mạnh điều gì, dẫn chứng gì, trình bày theo logic nào để ${isDefendant ? 'bảo vệ thân chủ hiệu quả nhất' : 'thuyết phục Hội đồng xét xử nhất'}.
3. CHỨNG CỨ NÊN CHUẨN BỊ — Gợi ý những loại chứng cứ cần thu thập để hỗ trợ cho các luận điểm trên (văn bản, nhân chứng, giám định, hình ảnh...).
4. LƯU Ý QUAN TRỌNG — Những điểm cần tránh hoặc cẩn thận khi xây dựng luận điểm cho vụ án này.`
    }

    const prompt = `${coachRole}

${toneInstruction}

${scenarioContext}
VAI TRÒ CỦA NGƯỜI DÙNG: ${userRoleLabel}
ĐỐI PHƯƠNG: ${oppositeRoleLabel}

CHIẾN LƯỢC HIỆN TẠI:

Luận điểm:
${argumentsList}

Chứng cứ đã chuẩn bị:
${evidencesList}

NHIỆM VỤ:
${taskSection}

Trả lời bằng tiếng Việt, có cấu trúc rõ ràng (khoảng 6-10 câu). KHÔNG lặp lại nội dung chiến lược. Đi thẳng vào phân tích và gợi ý cụ thể.`

    console.log('[Coach] Calling Gemini API:', {
        feedbackType,
        coachType,
        tone,
        userRole,
        scenario: scenario?.name,
        argumentsCount: (strategy.arguments || []).filter(a => a.text).length,
        evidencesCount: (strategy.evidences || []).length,
        messagesCount: messages.length,
        lastOpponentMsg: lastOpponentMsg?.text?.substring(0, 100) || '(none)',
        promptLength: prompt.length
    })

    const replyText = await generateGeminiResponse(prompt, fallbackFeedback)

    console.log('[Coach] Response received:', {
        feedbackType,
        responseLength: replyText?.length,
        responsePreview: replyText?.substring(0, 150) + (replyText?.length > 150 ? '...' : '')
    })

    return { text: replyText }
}

// Calculate scores: call backend API, fallback to local heuristic
export const calculateScores = async (session) => {
    const scenario = scenarios.find(s => s.id === session.scenarioId)
    try {
        const result = await evaluateSession({
            scenarioId: session.scenarioId,
            role: session.role,
            scenario: scenario ? { name: scenario.name, summary: scenario.summary, facts: scenario.facts } : null,
            messages: (session.messages || []).map(m => ({ type: m.type, text: m.text, round: m.round })),
            strategy: session.strategy || { arguments: [], evidences: [] },
            roundsCompleted: session.roundsCompleted || 0,
            totalRounds: session.settings?.roundLimit || 4,
            timeRemaining: session.timeRemaining || 0,
            totalTime: (session.settings?.timeLimit || 10) * 60
        })
        // Validate response shape
        const { legalAccuracy, evidenceUse, persuasion, timeManagement, etiquette } = result
        if ([legalAccuracy, evidenceUse, persuasion, timeManagement, etiquette].every(v => typeof v === 'number')) {
            console.log('[Scores] Backend API returned:', result)
            return { legalAccuracy, evidenceUse, persuasion, timeManagement, etiquette }
        }
        throw new Error('Invalid score format from backend')
    } catch (error) {
        console.warn('[Scores] Backend unavailable, using local fallback:', error.message)
        return calculateScoresLocal(session)
    }
}

// Local fallback: heuristic scoring based on session data
const calculateScoresLocal = (session) => {
    const messages = session.messages || []
    const strategy = session.strategy || { arguments: [], evidences: [] }
    const settings = session.settings || {}
    const totalTimeSeconds = (settings.timeLimit || 10) * 60
    const timeRemaining = session.timeRemaining || 0
    const roundsCompleted = session.roundsCompleted || 0
    const totalRounds = settings.roundLimit || 4

    const userMessages = messages.filter(m => m.type === 'user')
    const preparedArgs = (strategy.arguments || []).filter(a => a.text?.trim())
    const preparedEvs = strategy.evidences || []

    // --- Legal Accuracy (0-100) ---
    // Based on: message length/quality, citing evidence, number of rounds completed
    let legalAccuracy = 50
    // Completing all rounds shows thorough legal argumentation
    legalAccuracy += Math.round((roundsCompleted / totalRounds) * 20)
    // Longer, more detailed messages indicate better legal reasoning
    const avgUserMsgLength = userMessages.length > 0
        ? userMessages.reduce((sum, m) => sum + m.text.length, 0) / userMessages.length
        : 0
    if (avgUserMsgLength > 200) legalAccuracy += 15
    else if (avgUserMsgLength > 100) legalAccuracy += 10
    else if (avgUserMsgLength > 50) legalAccuracy += 5
    // Having prepared arguments shows legal preparation
    legalAccuracy += Math.min(preparedArgs.length * 5, 15)
    legalAccuracy = Math.min(legalAccuracy, 100)

    // --- Evidence Use (0-100) ---
    // Based on: prepared evidence count, linking evidence to arguments, mentioning evidence in messages
    let evidenceUse = 40
    // Prepared evidence
    evidenceUse += Math.min(preparedEvs.length * 10, 30)
    // Evidence linked to arguments
    const linkedEvs = preparedEvs.filter(e => (e.linkedArguments || []).length > 0)
    evidenceUse += Math.min(linkedEvs.length * 8, 16)
    // Mentioning "chứng cứ", "bằng chứng", "tài liệu", "chứng minh" in messages
    const evidenceKeywords = ['chứng cứ', 'bằng chứng', 'tài liệu', 'chứng minh', 'căn cứ', 'minh chứng']
    const msgsWithEvidence = userMessages.filter(m =>
        evidenceKeywords.some(kw => m.text.toLowerCase().includes(kw))
    )
    evidenceUse += Math.min(msgsWithEvidence.length * 5, 14)
    evidenceUse = Math.min(evidenceUse, 100)

    // --- Persuasion (0-100) ---
    // Based on: rounds completed, message engagement, argument preparation, response to opponent
    let persuasion = 45
    // Completing all rounds = persistent argumentation
    persuasion += Math.round((roundsCompleted / totalRounds) * 15)
    // Number of user messages (engagement)
    persuasion += Math.min(userMessages.length * 4, 16)
    // Prepared arguments used
    persuasion += Math.min(preparedArgs.length * 4, 12)
    // Longer messages = more persuasive effort
    if (avgUserMsgLength > 150) persuasion += 12
    else if (avgUserMsgLength > 80) persuasion += 7
    persuasion = Math.min(persuasion, 100)

    // --- Time Management (0-100) ---
    // Based on: time remaining, completing all rounds, pacing
    let timeManagement = 40
    const timeUsedRatio = (totalTimeSeconds - timeRemaining) / totalTimeSeconds
    // Completed all rounds within time
    if (roundsCompleted >= totalRounds && timeRemaining > 0) {
        timeManagement += 30
        // Bonus for good pacing (used 50-90% of time = not too fast, not too slow)
        if (timeUsedRatio >= 0.5 && timeUsedRatio <= 0.9) timeManagement += 20
        else if (timeUsedRatio >= 0.3) timeManagement += 10
    } else if (timeRemaining > 0) {
        // Ended early but still had time
        timeManagement += 15
        timeManagement += Math.round((roundsCompleted / totalRounds) * 15)
    } else {
        // Ran out of time
        timeManagement += Math.round((roundsCompleted / totalRounds) * 20)
    }
    // Having time left is generally good
    const timeLeftPct = timeRemaining / totalTimeSeconds
    timeManagement += Math.round(timeLeftPct * 10)
    timeManagement = Math.min(timeManagement, 100)

    // --- Etiquette (0-100) ---
    // Based on: polite language, no offensive words, proper form
    let etiquette = 70
    const politeKeywords = ['thưa', 'kính', 'hội đồng', 'xét xử', 'tòa', 'đề nghị', 'xin phép', 'trân trọng']
    const rudePhrases = ['ngu', 'đồ', 'vớ vẩn', 'nhảm', 'láo', 'bậy']
    const politeCount = userMessages.filter(m =>
        politeKeywords.some(kw => m.text.toLowerCase().includes(kw))
    ).length
    const rudeCount = userMessages.filter(m =>
        rudePhrases.some(kw => m.text.toLowerCase().includes(kw))
    ).length
    etiquette += Math.min(politeCount * 5, 25)
    etiquette -= rudeCount * 15
    // Completing all rounds without quitting early shows good conduct
    if (roundsCompleted >= totalRounds) etiquette += 5
    etiquette = Math.max(0, Math.min(etiquette, 100))

    return { legalAccuracy, evidenceUse, persuasion, timeManagement, etiquette }
}

// --- Session history for cumulative badges ---
export const getSessionHistory = () => {
    const stored = localStorage.getItem('courtroomSessionHistory')
    return stored ? JSON.parse(stored) : []
}

export const addSessionResult = (session, scores) => {
    const history = getSessionHistory()
    const total = Object.values(scores).reduce((a, b) => a + b, 0)
    history.push({
        scenarioId: session.scenarioId,
        role: session.role,
        total,
        scores,
        roundsCompleted: session.roundsCompleted || 0,
        totalRounds: session.settings?.roundLimit || 4,
        timeRemaining: session.timeRemaining || 0,
        totalTime: (session.settings?.timeLimit || 10) * 60,
        date: new Date().toISOString()
    })
    localStorage.setItem('courtroomSessionHistory', JSON.stringify(history))
    return history
}

// Determine if this session is a "win" (total >= 350)
const isWin = (total) => total >= 350

// Get earned badges from scores + session data + history
export const getEarnedBadges = (scores, session) => {
    const earned = []
    const total = Object.values(scores).reduce((a, b) => a + b, 0)
    const history = getSessionHistory()
    const roundsCompleted = session?.roundsCompleted || 0
    const totalRounds = session?.settings?.roundLimit || 4
    const timeRemaining = session?.timeRemaining || 0
    const totalTime = (session?.settings?.timeLimit || 10) * 60
    const role = session?.role

    // 1. Luật sư xuất sắc — Tổng điểm >= 450
    if (total >= 450) earned.push('excellent')

    // 2. Bậc thầy chứng cứ — Điểm sử dụng chứng cứ >= 90
    if (scores.evidenceUse >= 90) earned.push('evidence')

    // 3. Nhà hùng biện — Điểm thuyết phục >= 90
    if (scores.persuasion >= 90) earned.push('persuader')

    // 4. Tốc độ ánh sáng — Hoàn thành tất cả vòng & còn >= 40% thời gian
    if (roundsCompleted >= totalRounds && timeRemaining >= totalTime * 0.4) {
        earned.push('speed')
    }

    // 5. Chính xác tuyệt đối — Điểm pháp lý >= 95
    if (scores.legalAccuracy >= 95) earned.push('accurate')

    // 6. Lịch thiệp — Điểm phong thái >= 95
    if (scores.etiquette >= 95) earned.push('polite')

    // 7. Chiến thắng đầu tiên — Lần đầu đạt tổng điểm "win" & chưa có lịch sử win trước đó
    const previousWins = history.filter(h => isWin(h.total))
    if (isWin(total) && previousWins.length === 0) {
        earned.push('first_win')
    }

    // 8. Chuỗi 3 trận — 2 phiên gần nhất đều win + phiên hiện tại win
    if (isWin(total) && history.length >= 2) {
        const lastTwo = history.slice(-2)
        if (lastTwo.every(h => isWin(h.total))) {
            earned.push('streak_3')
        }
    }

    // 9. Bậc thầy tranh tụng — Tổng số phiên hoàn thành (bao gồm hiện tại) >= 10
    if (history.length + 1 >= 10) earned.push('master')

    // 10. Người bảo vệ — Win với vai trò bào chữa (defendant)
    if (isWin(total) && role === 'defendant') earned.push('defender')

    // 11. Công tố viên — Win với vai trò nguyên đơn (plaintiff)
    if (isWin(total) && role === 'plaintiff') earned.push('prosecutor')

    // 12. Lội ngược dòng — Win dù có điểm thấp ở ít nhất 2 hạng mục (< 60)
    if (isWin(total)) {
        const lowScoreCount = Object.values(scores).filter(s => s < 60).length
        if (lowScoreCount >= 2) earned.push('comeback')
    }

    return earned
}

// Bot suggestions based on coach options and round
export const getBotSuggestions = (round, coachType, coachOptions = {}) => {
    const lawyerSuggestions = {
        1: [
            '💡 "Theo Điều 492 BLDS 2015, hợp đồng này có hiệu lực pháp lý đầy đủ..."',
            '⚖️ "Căn cứ Nghị quyết 02/2004/NQ-HĐTP, thiệt hại thực tế phải được chứng minh rõ ràng..."',
            '📋 "Tôi đề nghị Hội đồng xét xử xem xét các chứng cứ sau đây..."'
        ],
        2: [
            '🔍 "Phân tích kỹ tình tiết này: đối phương chưa cung cấp căn cứ pháp lý..."',
            '⚖️ "Theo án lệ số 04/2016/AL, trong trường hợp tương tự, tòa đã phán quyết..."',
            '📎 "Tôi phản đối vì lập luận này mâu thuẫn với Điều 360 BLDS 2015..."'
        ],
        3: [
            '🎯 "Tổng kết lại, 3 luận điểm cốt lõi của chúng tôi là: Một, ...; Hai, ...; Ba, ..."',
            '⚡ "Đây là thời điểm đưa ra bằng chứng mang tính quyết định..."',
            '🛡️ "Yêu cầu tòa bác bỏ lập luận của đối phương vì thiếu căn cứ..."'
        ],
        4: [
            '📝 "Kết luận: Đề nghị Hội đồng xét xử chấp thuận toàn bộ yêu cầu khởi kiện..."',
            '🏁 "Dựa trên các chứng cứ đã trình bày, phán quyết có lợi cho thân chủ là hợp lý..."',
            '⚖️ "Tôi cam kết mọi lập luận đều có căn cứ pháp lý vững chắc..."'
        ]
    }

    const normalSuggestions = {
        1: [
            '💬 "Sự việc diễn ra như thế này, tôi có bằng chứng để chứng minh..."',
            '🙋 "Tôi muốn giải thích rõ hơn về thiệt hại mà tôi đã chịu..."',
            '📸 "Đây là tài liệu, hình ảnh chứng minh cho lời tôi nói..."'
        ],
        2: [
            '❓ "Điều đó không đúng vì sự thật là..."',
            '🤔 "Tôi không đồng ý với điểm vừa nêu, vì thực tế..."',
            '📋 "Tôi có thêm chứng cứ để bác bỏ lập luận kia..."'
        ],
        3: [
            '💪 "Tôi muốn nhấn mạnh lại rằng tôi đã bị thiệt hại nghiêm trọng..."',
            '🎯 "Điểm quan trọng nhất trong vụ việc này là..."',
            '⚡ "Phía bên kia vẫn chưa trả lời được câu hỏi chính..."'
        ],
        4: [
            '🙏 "Tôi hi vọng tòa sẽ xem xét đầy đủ các bằng chứng và ra phán quyết công bằng..."',
            '✅ "Tóm lại, tôi yêu cầu được bồi thường xứng đáng cho những thiệt hại..."',
            '📢 "Đây là quyết tâm bảo vệ quyền lợi hợp pháp của tôi..."'
        ]
    }

    const suggestions = coachType === 'lawyer' ? lawyerSuggestions : normalSuggestions
    const roundSuggestions = suggestions[Math.min(round, 4)] || suggestions[4]

    // Filter based on coach options
    const result = []

    if (coachOptions.openingSuggestion && round === 1) {
        result.push({ type: 'opening', icon: '💡', text: roundSuggestions[0] })
    }

    if (coachOptions.evidenceReminder) {
        result.push({ type: 'evidence', icon: '📎', text: 'Nhớ đề cập đến chứng cứ bạn đã chuẩn bị!' })
    }

    if (coachOptions.riskWarning && round >= 3) {
        result.push({ type: 'warning', icon: '⚠️', text: 'Cẩn thận! Đối phương có thể phản bác luận điểm này.' })
    }

    // Always show round-based suggestions
    roundSuggestions.forEach((s, i) => {
        if (!result.find(r => r.text === s)) {
            result.push({ type: 'suggestion', icon: i === 0 ? '💡' : i === 1 ? '⚖️' : '🎯', text: s })
        }
    })

    return result
}