/**
 * Mock API cho Virtual Courtroom
 * Cung cấp dữ liệu mẫu cho các kịch bản, coach, huy hiệu...
 */

// Danh sách kịch bản
export const scenarios = [
    {
        id: 1,
        name: 'Tranh chấp hợp đồng thuê nhà',
        difficulty: 1,
        difficultyLabel: 'Dễ',
        duration: 15,
        skills: ['Tranh luận cơ bản', 'Thu thập chứng cứ'],
        description: 'Người thuê nhà yêu cầu bồi thường do chủ nhà vi phạm hợp đồng.',
        summary: `Anh Minh thuê căn hộ của bà Hoa với thời hạn 1 năm. Sau 3 tháng, bà Hoa yêu cầu anh Minh dọn ra vì muốn bán căn hộ. Anh Minh đã đóng tiền đặt cọc 2 tháng và yêu cầu được bồi thường thiệt hại.

Các bên liên quan:
- Nguyên đơn: Anh Minh (người thuê)
- Bị đơn: Bà Hoa (chủ nhà)

Yêu cầu: Bồi thường tiền đặt cọc + thiệt hại do phải chuyển nhà đột xuất.`,
        facts: [
            'Hợp đồng thuê nhà ký ngày 01/01/2024, thời hạn 12 tháng',
            'Tiền đặt cọc: 20 triệu đồng',
            'Tiền thuê hàng tháng: 10 triệu đồng',
            'Bà Hoa thông báo yêu cầu dọn ra ngày 01/04/2024',
            'Anh Minh đã chi 5 triệu để tìm nhà mới và chuyển đồ'
        ]
    },
    {
        id: 2,
        name: 'Bồi thường tai nạn giao thông',
        difficulty: 2,
        difficultyLabel: 'Trung bình',
        duration: 25,
        skills: ['Phân tích chứng cứ', 'Tranh luận', 'Phản đối'],
        description: 'Nạn nhân yêu cầu bồi thường từ người gây tai nạn.',
        summary: `Anh Tuấn điều khiển xe máy va chạm với ô tô của chị Lan tại ngã tư. Anh Tuấn bị thương phải nhập viện 2 tuần. Camera giao thông ghi nhận sự việc.

Các bên liên quan:
- Nguyên đơn: Anh Tuấn (nạn nhân)
- Bị đơn: Chị Lan (người điều khiển ô tô)

Yêu cầu: Bồi thường chi phí y tế + tổn thất tinh thần + thu nhập bị mất.`,
        facts: [
            'Tai nạn xảy ra ngày 15/03/2024 lúc 8h sáng',
            'Anh Tuấn đi đúng làn đường, đèn xanh',
            'Chi phí y tế: 50 triệu đồng',
            'Thu nhập bị mất: 15 triệu đồng/tháng x 1 tháng',
            'Camera ghi nhận chị Lan vượt đèn đỏ'
        ]
    },
    {
        id: 3,
        name: 'Tranh chấp tài sản ly hôn',
        difficulty: 3,
        difficultyLabel: 'Khó',
        duration: 40,
        skills: ['Tranh luận nâng cao', 'Phản đối', 'Chiến lược', 'Đàm phán'],
        description: 'Phân chia tài sản chung sau khi ly hôn.',
        summary: `Anh Hùng và chị Mai kết hôn năm 2015, có 2 con. Năm 2024 họ đồng ý ly hôn nhưng tranh chấp về phân chia tài sản chung gồm căn nhà và tiền tiết kiệm.

Các bên liên quan:
- Nguyên đơn: Chị Mai
- Bị đơn: Anh Hùng

Yêu cầu: Phân chia công bằng tài sản chung + quyền nuôi con.`,
        facts: [
            'Kết hôn năm 2015, có 2 con (8 tuổi và 5 tuổi)',
            'Căn nhà trị giá 3 tỷ đồng, đứng tên chồng',
            'Tiền tiết kiệm: 500 triệu đồng',
            'Chị Mai là người chăm sóc con chính',
            'Anh Hùng có thu nhập 30 triệu/tháng, chị Mai 15 triệu/tháng'
        ]
    }
]

// Danh sách huy hiệu
export const allBadges = [
    { id: 'excellent', name: 'Luật sư xuất sắc', icon: '🥇', description: 'Tổng điểm > 400', threshold: 400 },
    { id: 'evidence', name: 'Bậc thầy chứng cứ', icon: '📊', description: 'Evidence Use > 90', threshold: 90 },
    { id: 'persuader', name: 'Nhà hùng biện', icon: '🎤', description: 'Persuasion > 90', threshold: 90 },
    { id: 'speed', name: 'Tốc độ ánh sáng', icon: '⚡', description: 'Hoàn thành trước thời gian', threshold: 0 },
    { id: 'accurate', name: 'Chính xác tuyệt đối', icon: '🎯', description: 'Legal Accuracy > 95', threshold: 95 },
    { id: 'polite', name: 'Lịch thiệp', icon: '🤝', description: 'Etiquette = 100', threshold: 100 },
    { id: 'first_win', name: 'Chiến thắng đầu tiên', icon: '🏆', description: 'Thắng phiên tòa đầu tiên', threshold: 0 },
    { id: 'streak_3', name: 'Chuỗi 3 trận', icon: '🔥', description: 'Thắng 3 phiên liên tiếp', threshold: 3 },
    { id: 'master', name: 'Bậc thầy tranh tụng', icon: '👑', description: 'Hoàn thành 10 phiên', threshold: 10 },
    { id: 'defender', name: 'Người bảo vệ', icon: '🛡️', description: 'Thắng với vai bào chữa', threshold: 0 },
    { id: 'prosecutor', name: 'Công tố viên', icon: '⚔️', description: 'Thắng với vai nguyên đơn', threshold: 0 },
    { id: 'comeback', name: 'Lội ngược dòng', icon: '🌊', description: 'Thắng khi bất lợi về điểm', threshold: 0 }
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

// Mock AI opponent responses
export const getOpponentResponse = (round, userArgument, scenario) => {
    const responses = [
        `Tôi phản đối lập luận này. Theo quy định pháp luật, bên nguyên đơn chưa cung cấp đủ bằng chứng để chứng minh thiệt hại thực tế.`,
        `Các chứng cứ được đưa ra không đủ tính thuyết phục. Tôi yêu cầu tòa xem xét lại các tình tiết của vụ án.`,
        `Quan điểm này mâu thuẫn với các tiền lệ pháp lý. Theo án lệ số 42/2023, tòa đã phán quyết ngược lại trong trường hợp tương tự.`,
        `Tôi đề nghị tòa bác bỏ yêu cầu bồi thường vì không có căn cứ pháp lý rõ ràng.`
    ]
    return new Promise(resolve => {
        setTimeout(() => {
            resolve({
                text: responses[round % responses.length],
                character: 'opponent'
            })
        }, 1500)
    })
}

// Mock Coach feedback
export const getCoachFeedback = (content, coachType, tone) => {
    const lawyerFeedback = [
        'Luận điểm này có căn cứ pháp lý vững chắc. Hãy bổ sung thêm điều luật cụ thể.',
        'Chứng cứ quan trọng. Cần liên kết với yêu cầu bồi thường rõ ràng hơn.',
        'Cần làm rõ mối quan hệ nhân quả giữa hành vi vi phạm và thiệt hại.'
    ]
    const normalFeedback = [
        'Ý tưởng hay đấy! Thử giải thích đơn giản hơn một chút nhé.',
        'Chứng cứ này sẽ thuyết phục hơn nếu có hình ảnh hoặc tài liệu đi kèm.',
        'Nghe có lý! Nhưng đối phương có thể phản bác điểm này.'
    ]

    return new Promise(resolve => {
        setTimeout(() => {
            const feedbacks = coachType === 'lawyer' ? lawyerFeedback : normalFeedback
            resolve({
                text: feedbacks[Math.floor(Math.random() * feedbacks.length)]
            })
        }, 800)
    })
}

// Calculate scores
export const calculateScores = (session) => {
    // Mock scoring based on session data
    const baseScores = {
        legalAccuracy: Math.floor(Math.random() * 30) + 60,
        evidenceUse: Math.floor(Math.random() * 30) + 60,
        persuasion: Math.floor(Math.random() * 30) + 60,
        timeManagement: session.timeRemaining > 0 ? 80 + Math.floor(session.timeRemaining / 10) : 50,
        etiquette: Math.floor(Math.random() * 20) + 75
    }

    // Add bonus for arguments made
    if (session.arguments?.length > 2) {
        baseScores.persuasion += 10
    }
    if (session.evidences?.length > 1) {
        baseScores.evidenceUse += 15
    }

    return baseScores
}

// Get earned badges from scores
export const getEarnedBadges = (scores) => {
    const earned = []
    const total = Object.values(scores).reduce((a, b) => a + b, 0)

    if (total > 400) earned.push('excellent')
    if (scores.evidenceUse > 90) earned.push('evidence')
    if (scores.persuasion > 90) earned.push('persuader')
    if (scores.legalAccuracy > 95) earned.push('accurate')
    if (scores.etiquette === 100) earned.push('polite')
    if (scores.timeManagement > 90) earned.push('speed')

    return earned
}
