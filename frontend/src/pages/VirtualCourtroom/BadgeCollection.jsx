import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { allBadges, getUserBadges } from '../../services/courtroomMockApi'

function BadgeCollection() {
    const navigate = useNavigate()
    const [userBadges, setUserBadges] = useState([])
    const [stats, setStats] = useState({ total: 0, sessions: 0 })

    useEffect(() => {
        const badges = getUserBadges()
        setUserBadges(badges)
        const totalEarned = badges.reduce((sum, b) => sum + b.count, 0)
        setStats({ total: badges.length, sessions: totalEarned })
    }, [])

    const getBadgeStatus = (badgeId) => {
        return userBadges.find(b => b.id === badgeId) || null
    }

    const formatDate = (dateString) => {
        if (!dateString) return ''
        return new Date(dateString).toLocaleDateString('vi-VN')
    }

    const progressPct = Math.round((stats.total / allBadges.length) * 100)

    return (
        <div className="vc-page">
            {/* Header */}
            <header className="vc-landing-header">
                <div className="vc-landing-badge">Thành tích</div>
                <h1>Bộ Sưu Tập Huy Hiệu</h1>
                <p>Theo dõi hành trình rèn luyện kỹ năng tranh tụng của bạn</p>
            </header>

            <div className="vc-content">
                {/* Stats overview */}
                <div className="vc-section">
                    <div className="vc-badge-stats-row">
                        <div className="vc-badge-stat-card" style={{ animationDelay: '0.08s' }}>
                            <span className="vc-badge-stat-icon">🏅</span>
                            <span className="vc-badge-stat-num">{stats.total}/{allBadges.length}</span>
                            <span className="vc-badge-stat-label">Đã mở khóa</span>
                        </div>
                        <div className="vc-badge-stat-card" style={{ animationDelay: '0.14s' }}>
                            <span className="vc-badge-stat-icon">⚖️</span>
                            <span className="vc-badge-stat-num">{stats.sessions}</span>
                            <span className="vc-badge-stat-label">Lần nhận</span>
                        </div>
                        <div className="vc-badge-stat-card" style={{ animationDelay: '0.20s' }}>
                            <span className="vc-badge-stat-icon">📊</span>
                            <span className="vc-badge-stat-num">{progressPct}%</span>
                            <span className="vc-badge-stat-label">Hoàn thành</span>
                        </div>
                    </div>

                    {/* Progress bar */}
                    <div className="vc-badge-progress">
                        <div className="vc-badge-progress-bar">
                            <div
                                className="vc-badge-progress-fill"
                                style={{ width: `${progressPct}%` }}
                            />
                        </div>
                    </div>
                </div>

                {/* Badge grid */}
                <div className="vc-section">
                    <div className="vc-section-label">Tất cả huy hiệu</div>
                    <div className="vc-badge-grid">
                        {allBadges.map((badge, i) => {
                            const status = getBadgeStatus(badge.id)
                            const isUnlocked = status !== null

                            return (
                                <div
                                    key={badge.id}
                                    className={`vc-badge-card${isUnlocked ? ' unlocked' : ' locked'}`}
                                    style={{ animationDelay: `${0.05 + i * 0.04}s` }}
                                >
                                    <span className="vc-badge-card-icon">
                                        {isUnlocked ? badge.icon : '🔒'}
                                    </span>
                                    <span className="vc-badge-card-name">{badge.name}</span>
                                    <span className="vc-badge-card-desc">{badge.description}</span>

                                    {isUnlocked && (
                                        <div className="vc-badge-card-meta">
                                            <span>Đạt {status.count} lần</span>
                                            <span>Gần nhất: {formatDate(status.lastEarned)}</span>
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* Navigation */}
                <div className="vc-nav">
                    <button className="vc-btn-back" onClick={() => navigate('/courtroom')}>
                        ← Phiên tòa mới
                    </button>
                    <button className="vc-btn-next" onClick={() => navigate('/')}>
                        Về trang chính →
                    </button>
                </div>
            </div>
        </div>
    )
}

export default BadgeCollection
