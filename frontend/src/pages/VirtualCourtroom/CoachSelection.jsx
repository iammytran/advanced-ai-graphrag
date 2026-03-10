import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function CoachSelection() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)

    const [coachType, setCoachType] = useState('lawyer')
    const [toneValue, setToneValue] = useState(50)
    const [options, setOptions] = useState({
        openingSuggestion: true,
        evidenceReminder: true,
        autoObjection: false,
        riskWarning: true
    })

    useEffect(() => {
        const stored = sessionStorage.getItem('courtroomSession')
        if (!stored) {
            navigate('/courtroom')
            return
        }
        setSession(JSON.parse(stored))
    }, [navigate])

    const handleOptionChange = (key) => {
        setOptions(prev => ({ ...prev, [key]: !prev[key] }))
    }

    const handleContinue = () => {
        const updatedSession = {
            ...session,
            coach: {
                type: coachType,
                tone: toneValue,
                options
            }
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/case')
    }

    const steps = [
        { label: 'Kịch bản', done: true },
        { label: 'Vai trò', done: true },
        { label: 'Huấn luyện viên', active: true },
        { label: 'Hồ sơ vụ án' },
        { label: 'Chiến lược' }
    ]

    const features = [
        { key: 'openingSuggestion', icon: '💡', label: 'Gợi ý câu mở đầu' },
        { key: 'evidenceReminder', icon: '📎', label: 'Nhắc chứng cứ phù hợp' },
        { key: 'autoObjection', icon: '✋', label: 'Tự động soạn phản đối' },
        { key: 'riskWarning', icon: '⚠️', label: 'Cảnh báo rủi ro pháp lý' }
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
                {/* Coach type selection */}
                <div className="vc-section">
                    <div className="vc-section-label">Chọn loại huấn luyện viên</div>
                    <div className="vc-coach-grid">
                        <div
                            className={`vc-coach-card${coachType === 'lawyer' ? ' selected' : ''}`}
                            onClick={() => setCoachType('lawyer')}
                            style={{ animationDelay: '0.05s' }}
                        >
                            <div className="vc-coach-avatar">👨‍⚖️</div>
                            <div className="vc-coach-text">
                                <h3>Luật sư cố vấn</h3>
                                <p>Phản hồi chuyên nghiệp, trích dẫn điều luật cụ thể, phân tích sắc bén</p>
                            </div>
                        </div>

                        <div
                            className={`vc-coach-card${coachType === 'normal' ? ' selected' : ''}`}
                            onClick={() => setCoachType('normal')}
                            style={{ animationDelay: '0.12s' }}
                        >
                            <div className="vc-coach-avatar">😊</div>
                            <div className="vc-coach-text">
                                <h3>Người bạn đồng hành</h3>
                                <p>Phản hồi thân thiện, dễ hiểu, chia sẻ từ kinh nghiệm thực tế</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Tone slider */}
                <div className="vc-section">
                    <div className="vc-section-label">Phong cách phản hồi</div>
                    <div className="vc-tone-box" style={{ animationDelay: '0.15s' }}>
                        <div className="vc-tone-labels">
                            <span className={`vc-tone-label${toneValue < 40 ? ' active' : ''}`}>
                                🗣️ Đời thường
                            </span>
                            <span className={`vc-tone-label${toneValue >= 40 && toneValue <= 60 ? ' active' : ''}`}>
                                Cân bằng
                            </span>
                            <span className={`vc-tone-label${toneValue > 60 ? ' active' : ''}`}>
                                ⚖️ Pháp lý
                            </span>
                        </div>
                        <input
                            type="range"
                            className="vc-tone-slider"
                            min="0"
                            max="100"
                            value={toneValue}
                            onChange={(e) => setToneValue(parseInt(e.target.value))}
                        />
                        <div className="vc-tone-value">
                            {toneValue < 30 ? 'Rất đời thường' :
                             toneValue < 50 ? 'Thiên đời thường' :
                             toneValue === 50 ? 'Cân bằng' :
                             toneValue < 70 ? 'Thiên pháp lý' :
                             'Rất chuyên nghiệp'} — {toneValue}%
                        </div>
                    </div>
                </div>

                {/* Feature toggles */}
                <div className="vc-section">
                    <div className="vc-section-label">Hỗ trợ trong phiên tòa</div>
                    <div className="vc-features-grid">
                        {features.map((f, i) => (
                            <label
                                key={f.key}
                                className={`vc-feature-card${options[f.key] ? ' active' : ''}`}
                                style={{ animationDelay: `${0.18 + i * 0.05}s` }}
                            >
                                <input
                                    type="checkbox"
                                    checked={options[f.key]}
                                    onChange={() => handleOptionChange(f.key)}
                                />
                                <span className="vc-feature-icon">{f.icon}</span>
                                <span className="vc-feature-label">{f.label}</span>
                                <span className="vc-feature-toggle" />
                            </label>
                        ))}
                    </div>
                </div>

                {/* Navigation */}
                <div className="vc-nav">
                    <button className="vc-btn-back" onClick={() => navigate(-1)}>
                        ← Quay lại
                    </button>
                    <button className="vc-btn-next" onClick={handleContinue}>
                        Tiếp tục → Hồ sơ vụ án
                    </button>
                </div>
            </div>
        </div>
    )
}

export default CoachSelection
