import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, allBadges, calculateScores, getEarnedBadges, addUserBadge } from '../../services/courtroomMockApi'

function Results() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)
    const [scores, setScores] = useState(null)
    const [earnedBadges, setEarnedBadges] = useState([])
    const [showBadgeAnimation, setShowBadgeAnimation] = useState(false)

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

        // Calculate scores
        const calculatedScores = calculateScores(sess)
        setScores(calculatedScores)

        // Get earned badges
        const badges = getEarnedBadges(calculatedScores)
        setEarnedBadges(badges)

        // Save badges to storage
        badges.forEach(badgeId => addUserBadge(badgeId))

        // Show badge animation
        if (badges.length > 0) {
            setTimeout(() => setShowBadgeAnimation(true), 1000)
        }
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

    const getBadgeInfo = (badgeId) => {
        return allBadges.find(b => b.id === badgeId)
    }

    if (!scores || !scenario) {
        return <div className="courtroom-page">Đang tính điểm...</div>
    }

    const { grade, label, color } = getScoreGrade(getTotalScore())

    return (
        <div className="courtroom-page results-page">
            <header className="page-header">
                <h1>🏆 Kết Quả Phiên Tòa</h1>
                <p>{scenario.name}</p>
            </header>

            {/* Grade Display */}
            <div className="grade-display" style={{ borderColor: color }}>
                <div className="grade-letter" style={{ color }}>{grade}</div>
                <div className="grade-label">{label}</div>
                <div className="total-score">Tổng điểm: {getTotalScore()}/500</div>
            </div>

            {/* Score Breakdown */}
            <section className="scores-section">
                <h2>📊 Chi Tiết Điểm Số</h2>
                <div className="score-grid">
                    <div className="score-item">
                        <div className="score-icon">📚</div>
                        <div className="score-label">Legal Accuracy</div>
                        <div className="score-bar">
                            <div className="bar-fill" style={{ width: `${scores.legalAccuracy}%` }} />
                        </div>
                        <div className="score-value">{scores.legalAccuracy}/100</div>
                    </div>

                    <div className="score-item">
                        <div className="score-icon">📋</div>
                        <div className="score-label">Evidence Use</div>
                        <div className="score-bar">
                            <div className="bar-fill" style={{ width: `${scores.evidenceUse}%` }} />
                        </div>
                        <div className="score-value">{scores.evidenceUse}/100</div>
                    </div>

                    <div className="score-item">
                        <div className="score-icon">🎯</div>
                        <div className="score-label">Persuasion</div>
                        <div className="score-bar">
                            <div className="bar-fill" style={{ width: `${scores.persuasion}%` }} />
                        </div>
                        <div className="score-value">{scores.persuasion}/100</div>
                    </div>

                    <div className="score-item">
                        <div className="score-icon">⏱️</div>
                        <div className="score-label">Time Management</div>
                        <div className="score-bar">
                            <div className="bar-fill" style={{ width: `${scores.timeManagement}%` }} />
                        </div>
                        <div className="score-value">{scores.timeManagement}/100</div>
                    </div>

                    <div className="score-item">
                        <div className="score-icon">🤝</div>
                        <div className="score-label">Etiquette</div>
                        <div className="score-bar">
                            <div className="bar-fill" style={{ width: `${scores.etiquette}%` }} />
                        </div>
                        <div className="score-value">{scores.etiquette}/100</div>
                    </div>
                </div>
            </section>

            {/* Badges Earned */}
            {earnedBadges.length > 0 && (
                <section className={`badges-section ${showBadgeAnimation ? 'animate' : ''}`}>
                    <h2>🏅 Huy Hiệu Đạt Được</h2>
                    <div className="badges-grid">
                        {earnedBadges.map(badgeId => {
                            const badge = getBadgeInfo(badgeId)
                            return badge ? (
                                <div key={badgeId} className="badge-card earned">
                                    <div className="badge-icon">{badge.icon}</div>
                                    <div className="badge-name">{badge.name}</div>
                                    <div className="badge-desc">{badge.description}</div>
                                </div>
                            ) : null
                        })}
                    </div>
                </section>
            )}

            {/* Session Stats */}
            <section className="stats-section">
                <h2>📈 Thống Kê Phiên</h2>
                <div className="stats-grid">
                    <div className="stat-item">
                        <span className="stat-label">Vòng hoàn thành</span>
                        <span className="stat-value">{session?.roundsCompleted || 0}/4</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Thời gian còn lại</span>
                        <span className="stat-value">{Math.floor((session?.timeRemaining || 0) / 60)}:{String((session?.timeRemaining || 0) % 60).padStart(2, '0')}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Vai trò</span>
                        <span className="stat-value">{session?.role === 'defendant' ? '🛡️ Bào chữa' : '⚔️ Nguyên đơn'}</span>
                    </div>
                </div>
            </section>

            {/* Navigation */}
            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate('/courtroom')}>
                    🏛️ Chọn kịch bản khác
                </button>
                <button className="btn-primary" onClick={() => navigate('/courtroom/badges')}>
                    🏆 Xem bộ sưu tập huy hiệu
                </button>
            </div>
        </div>
    )
}

export default Results
