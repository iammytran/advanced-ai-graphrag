import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, allBadges, calculateScores, getEarnedBadges, addUserBadge, addSessionResult } from '../../services/courtroomMockApi'

function Results() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)
    const [scores, setScores] = useState(null)
    const [earnedBadges, setEarnedBadges] = useState([])
    const [showBadgeAnimation, setShowBadgeAnimation] = useState(false)
    const [animateScores, setAnimateScores] = useState(false)

    useEffect(() => {
        const stored = sessionStorage.getItem('courtroomSession')
        if (!stored) {
            navigate('/courtroom')
            return
        }
        const sess = JSON.parse(stored)
        setSession(sess)
        const sc = scenarios.find(s => s.id === sess.scenarioId)
        setScenario(sc)

        const loadScores = async () => {
            const calculatedScores = await calculateScores(sess)
            setScores(calculatedScores)

            // Save session to history before checking badges
            addSessionResult(sess, calculatedScores)

            const badges = getEarnedBadges(calculatedScores, sess)
            setEarnedBadges(badges)
            badges.forEach(badgeId => addUserBadge(badgeId))

            // Stagger animations
            setTimeout(() => setAnimateScores(true), 300)
            if (badges.length > 0) {
                setTimeout(() => setShowBadgeAnimation(true), 1000)
            }
        }
        loadScores()
    }, [navigate])

    const getTotalScore = () => {
        if (!scores) return 0
        return Object.values(scores).reduce((a, b) => a + b, 0)
    }

    const getScoreGrade = (total) => {
        if (total >= 450) return { grade: 'S', label: 'Xuất sắc!', color: '#f59e0b' }
        if (total >= 400) return { grade: 'A', label: 'Rất tốt!', color: '#22c55e' }
        if (total >= 350) return { grade: 'B', label: 'Tốt', color: '#3b82f6' }
        if (total >= 300) return { grade: 'C', label: 'Khá', color: '#8b5cf6' }
        return { grade: 'D', label: 'Cần cải thiện', color: '#ef4444' }
    }

    const getBadgeInfo = (badgeId) => allBadges.find(b => b.id === badgeId)

    if (!scores || !scenario) {
        return <div className="vc-page"><div className="vc-content">Đang tính điểm...</div></div>
    }

    const total = getTotalScore()
    const { grade, label, color } = getScoreGrade(total)

    const scoreItems = [
        { key: 'legalAccuracy', icon: '📚', label: 'Độ chính xác pháp lý', value: scores.legalAccuracy },
        { key: 'evidenceUse', icon: '📋', label: 'Sử dụng chứng cứ', value: scores.evidenceUse },
        { key: 'persuasion', icon: '🎯', label: 'Sức thuyết phục', value: scores.persuasion },
        { key: 'timeManagement', icon: '⏱️', label: 'Quản lý thời gian', value: scores.timeManagement },
        { key: 'etiquette', icon: '🤝', label: 'Phong thái ứng xử', value: scores.etiquette }
    ]

    return (
        <div className="vc-page">
            <div className="vc-content" style={{ maxWidth: 720 }}>
                {/* Grade hero */}
                <div className="vc-result-hero">
                    <div className="vc-result-grade" style={{ '--grade-color': color }}>
                        <span className="vc-result-grade-letter">{grade}</span>
                    </div>
                    <div className="vc-result-grade-label" style={{ color }}>{label}</div>
                    <div className="vc-result-total">Tổng điểm: <strong>{total}</strong> / 500</div>
                    <div className="vc-result-scenario">{scenario.name}</div>
                </div>

                {/* Score breakdown */}
                <div className="vc-section">
                    <div className="vc-section-label">Chi tiết điểm số</div>
                    <div className="vc-result-scores">
                        {scoreItems.map((item, i) => (
                            <div
                                key={item.key}
                                className="vc-result-score-row"
                                style={{ animationDelay: `${0.1 + i * 0.08}s` }}
                            >
                                <span className="vc-result-score-icon">{item.icon}</span>
                                <span className="vc-result-score-label">{item.label}</span>
                                <div className="vc-result-bar">
                                    <div
                                        className="vc-result-bar-fill"
                                        style={{
                                            width: animateScores ? `${item.value}%` : '0%',
                                            background: item.value >= 90 ? 'linear-gradient(90deg, #22c55e, #4ade80)' :
                                                         item.value >= 70 ? 'var(--accent-gradient)' :
                                                         'linear-gradient(90deg, #ef4444, #f87171)'
                                        }}
                                    />
                                </div>
                                <span className="vc-result-score-num">{item.value}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Badges earned */}
                {earnedBadges.length > 0 && (
                    <div className="vc-section">
                        <div className="vc-section-label">Huy hiệu đạt được</div>
                        <div className={`vc-result-badges${showBadgeAnimation ? ' animate' : ''}`}>
                            {earnedBadges.map((badgeId, i) => {
                                const badge = getBadgeInfo(badgeId)
                                if (!badge) return null
                                return (
                                    <div
                                        key={badgeId}
                                        className="vc-result-badge-card"
                                        style={{ animationDelay: `${i * 0.15}s` }}
                                    >
                                        <span className="vc-result-badge-icon">{badge.icon}</span>
                                        <span className="vc-result-badge-name">{badge.name}</span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}

                {/* Session stats */}
                <div className="vc-section">
                    <div className="vc-section-label">Thống kê phiên tòa</div>
                    <div className="vc-result-stats">
                        <div className="vc-result-stat">
                            <span className="vc-result-stat-value">
                                {session?.roundsCompleted || 0}/{session?.settings?.roundLimit || 4}
                            </span>
                            <span className="vc-result-stat-label">Vòng hoàn thành</span>
                        </div>
                        <div className="vc-result-stat">
                            <span className="vc-result-stat-value">
                                {Math.floor((session?.timeRemaining || 0) / 60)}:{String((session?.timeRemaining || 0) % 60).padStart(2, '0')}
                            </span>
                            <span className="vc-result-stat-label">Thời gian còn lại</span>
                        </div>
                        <div className="vc-result-stat">
                            <span className="vc-result-stat-value">
                                {session?.role === 'defendant' ? '🛡️' : '⚔️'}
                            </span>
                            <span className="vc-result-stat-label">
                                {session?.role === 'defendant' ? 'Bào chữa' : 'Nguyên đơn'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <div className="vc-nav">
                    <button className="vc-btn-back" onClick={() => navigate('/courtroom')}>
                        ← Chọn kịch bản khác
                    </button>
                    <button className="vc-btn-next" onClick={() => navigate('/courtroom/badges')}>
                        Bộ sưu tập huy hiệu →
                    </button>
                </div>
            </div>
        </div>
    )
}

export default Results
