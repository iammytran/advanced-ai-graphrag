import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

const difficultyMap = {
    1: { class: 'easy' },
    2: { class: 'medium' },
    3: { class: 'hard' }
}

function ScenarioDetail() {
    const navigate = useNavigate()
    const { id } = useParams()
    const scenario = scenarios.find(s => s.id === parseInt(id))

    const [selectedRole, setSelectedRole] = useState(null)

    if (!scenario) {
        return (
            <div className="vc-page">
                <div className="vc-content">
                    <h1 className="vc-detail-title">Không tìm thấy kịch bản</h1>
                    <button className="vc-btn-back" onClick={() => navigate('/courtroom')}>
                        ← Quay lại
                    </button>
                </div>
            </div>
        )
    }

    const handleContinue = () => {
        if (!selectedRole) {
            alert('Vui lòng chọn vai trò của bạn')
            return
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify({
            scenarioId: scenario.id,
            role: selectedRole
        }))
        navigate('/courtroom/coach')
    }

    const diff = difficultyMap[scenario.difficulty] || difficultyMap[1]

    const steps = [
        { label: 'Kịch bản', done: true },
        { label: 'Vai trò', active: true },
        { label: 'Huấn luyện viên' },
        { label: 'Hồ sơ vụ án' },
        { label: 'Chiến lược' }
    ]

    return (
        <div className="vc-page">
            {/* Step indicator */}
            <nav className="vc-steps">
                {steps.map((step, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
                        {i > 0 && (
                            <div className={`vc-step-line${step.done || step.active ? ' done' : ''}`} />
                        )}
                        <div className={`vc-step${step.done ? ' done' : ''}${step.active ? ' active' : ''}`}>
                            <span className="vc-step-dot">
                                {step.done ? '✓' : i + 1}
                            </span>
                            <span>{step.label}</span>
                        </div>
                    </div>
                ))}
            </nav>

            <div className="vc-content">
                {/* Title & meta */}
                <h1 className="vc-detail-title">{scenario.name}</h1>
                <div className="vc-detail-meta">
                    <span className={`vc-detail-badge vc-sc-difficulty--${diff.class}`}>
                        {scenario.difficultyLabel}
                    </span>
                    <span className="vc-detail-duration">⏱️ {scenario.duration} phút</span>
                </div>

                {/* Summary */}
                <div className="vc-section">
                    <div className="vc-section-label">Tóm tắt kịch bản</div>
                    <div className="vc-summary-box">
                        {scenario.summary.split('\n').map((line, i) => (
                            <p key={i}>{line}</p>
                        ))}
                    </div>
                </div>

                {/* Role selection */}
                <div className="vc-section">
                    <div className="vc-section-label">Chọn vai trò của bạn</div>
                    <div className="vc-role-grid">
                        <div
                            className={`vc-role-card${selectedRole === 'defendant' ? ' selected' : ''}`}
                            onClick={() => setSelectedRole('defendant')}
                            style={{ animationDelay: '0.12s' }}
                        >
                            <div className="vc-role-icon">🛡️</div>
                            <div className="vc-role-name">Luật sư Bào chữa</div>
                            <div className="vc-role-desc">Bảo vệ quyền lợi cho bị đơn / bị cáo</div>
                            <div className="vc-role-check">
                                {selectedRole === 'defendant' && '✓'}
                            </div>
                        </div>

                        <div
                            className={`vc-role-card${selectedRole === 'plaintiff' ? ' selected' : ''}`}
                            onClick={() => setSelectedRole('plaintiff')}
                            style={{ animationDelay: '0.18s' }}
                        >
                            <div className="vc-role-icon">⚔️</div>
                            <div className="vc-role-name">Luật sư Nguyên đơn</div>
                            <div className="vc-role-desc">Bảo vệ quyền lợi cho người bị hại</div>
                            <div className="vc-role-check">
                                {selectedRole === 'plaintiff' && '✓'}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <div className="vc-nav">
                    <button className="vc-btn-back" onClick={() => navigate('/courtroom')}>
                        ← Quay lại danh sách
                    </button>
                    <button
                        className="vc-btn-next"
                        onClick={handleContinue}
                        disabled={!selectedRole}
                    >
                        Tiếp tục → Chọn huấn luyện viên
                    </button>
                </div>
            </div>
        </div>
    )
}

export default ScenarioDetail
