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

        // Calculate stats
        const totalEarned = badges.reduce((sum, b) => sum + b.count, 0)
        setStats({
            total: badges.length,
            sessions: totalEarned
        })
    }, [])

    const getBadgeStatus = (badgeId) => {
        const userBadge = userBadges.find(b => b.id === badgeId)
        return userBadge || null
    }

    const formatDate = (dateString) => {
        if (!dateString) return ''
        const date = new Date(dateString)
        return date.toLocaleDateString('vi-VN')
    }

    return (
        <div className="courtroom-page badge-collection">
            <header className="page-header">
                <h1>🏆 Bộ Sưu Tập Huy Hiệu</h1>
                <p>Xem tất cả huy hiệu bạn đã đạt được</p>
            </header>

            {/* Stats Overview */}
            <section className="stats-overview">
                <div className="stat-card">
                    <div className="stat-icon">🏅</div>
                    <div className="stat-info">
                        <span className="stat-value">{stats.total}/{allBadges.length}</span>
                        <span className="stat-label">Huy hiệu đã mở khóa</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon">⚖️</div>
                    <div className="stat-info">
                        <span className="stat-value">{stats.sessions}</span>
                        <span className="stat-label">Lần nhận huy hiệu</span>
                    </div>
                </div>
                <div className="stat-card progress">
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${(stats.total / allBadges.length) * 100}%` }}
                        />
                    </div>
                    <span className="progress-label">
                        {Math.round((stats.total / allBadges.length) * 100)}% hoàn thành
                    </span>
                </div>
            </section>

            {/* Badge Grid */}
            <section className="badges-grid-section">
                <h2>Tất Cả Huy Hiệu</h2>
                <div className="badges-grid">
                    {allBadges.map(badge => {
                        const status = getBadgeStatus(badge.id)
                        const isUnlocked = status !== null

                        return (
                            <div
                                key={badge.id}
                                className={`badge-card ${isUnlocked ? 'unlocked' : 'locked'}`}
                            >
                                <div className="badge-icon">
                                    {isUnlocked ? badge.icon : '🔒'}
                                </div>
                                <div className="badge-name">{badge.name}</div>
                                <div className="badge-description">{badge.description}</div>

                                {isUnlocked && (
                                    <div className="badge-stats">
                                        <span className="times-earned">
                                            ✅ Đạt {status.count} lần
                                        </span>
                                        <span className="last-earned">
                                            Gần nhất: {formatDate(status.lastEarned)}
                                        </span>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            </section>

            {/* Navigation */}
            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate('/')}>
                    💬 Về Chatbot
                </button>
                <button className="btn-primary" onClick={() => navigate('/courtroom')}>
                    🏛️ Phiên tòa mới
                </button>
            </div>
        </div>
    )
}

export default BadgeCollection
