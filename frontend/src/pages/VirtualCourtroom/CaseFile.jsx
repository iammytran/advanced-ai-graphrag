import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

function CaseFile() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)

    const [objective, setObjective] = useState('compensation')
    const [sessionSettings, setSessionSettings] = useState({
        timeLimit: 10,
        roundLimit: 4,
        pauseEnabled: true
    })

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
    }, [navigate])

    const handleContinue = () => {
        const updatedSession = {
            ...session,
            objective,
            settings: sessionSettings
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/strategy')
    }

    if (!scenario) {
        return <div className="vc-page"><div className="vc-content">Đang tải...</div></div>
    }

    const steps = [
        { label: 'Kịch bản', done: true },
        { label: 'Vai trò', done: true },
        { label: 'Huấn luyện viên', done: true },
        { label: 'Hồ sơ vụ án', active: true },
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
                {/* Title */}
                <h1 className="vc-case-title">Hồ Sơ Vụ Án</h1>
                <p className="vc-case-scenario">{scenario.name}</p>

                {/* Facts */}
                <div className="vc-section">
                    <div className="vc-section-label">Các sự kiện pháp lý</div>
                    <div className="vc-facts-list">
                        {scenario.facts?.map((fact, i) => (
                            <div
                                key={i}
                                className="vc-fact-item"
                                style={{ animationDelay: `${0.05 + i * 0.06}s` }}
                            >
                                <span className="vc-fact-num">{i + 1}</span>
                                <span className="vc-fact-text">{fact}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Objective */}
                <div className="vc-section">
                    <div className="vc-section-label">Mục tiêu của bạn</div>
                    <div className="vc-objective-grid">
                        <label
                            className={`vc-objective-card${objective === 'compensation' ? ' selected' : ''}`}
                            style={{ animationDelay: '0.1s' }}
                        >
                            <input
                                type="radio"
                                name="objective"
                                value="compensation"
                                checked={objective === 'compensation'}
                                onChange={(e) => setObjective(e.target.value)}
                            />
                            <div className="vc-objective-icon">💰</div>
                            <div className="vc-objective-name">Nhận bồi thường</div>
                            <div className="vc-objective-desc">Yêu cầu bồi thường thiệt hại đầy đủ theo quy định pháp luật</div>
                        </label>

                        <label
                            className={`vc-objective-card${objective === 'mediation' ? ' selected' : ''}`}
                            style={{ animationDelay: '0.15s' }}
                        >
                            <input
                                type="radio"
                                name="objective"
                                value="mediation"
                                checked={objective === 'mediation'}
                                onChange={(e) => setObjective(e.target.value)}
                            />
                            <div className="vc-objective-icon">🤝</div>
                            <div className="vc-objective-name">Hòa giải (Win-Win)</div>
                            <div className="vc-objective-desc">Đạt thỏa thuận có lợi cho cả hai bên thông qua đàm phán</div>
                        </label>
                    </div>
                </div>

                {/* Settings */}
                <div className="vc-section">
                    <div className="vc-section-label">Cài đặt phiên tòa</div>
                    <div className="vc-settings-box" style={{ animationDelay: '0.2s' }}>
                        <div className="vc-setting-row">
                            <div className="vc-setting-label">
                                <span>⏱️</span>
                                <span>Giới hạn thời gian</span>
                            </div>
                            <select
                                className="vc-setting-select"
                                value={sessionSettings.timeLimit}
                                onChange={(e) => setSessionSettings(prev => ({
                                    ...prev,
                                    timeLimit: parseInt(e.target.value)
                                }))}
                            >
                                <option value={5}>5 phút</option>
                                <option value={10}>10 phút</option>
                                <option value={15}>15 phút</option>
                                <option value={20}>20 phút</option>
                            </select>
                        </div>

                        <div className="vc-setting-row">
                            <div className="vc-setting-label">
                                <span>🔄</span>
                                <span>Giới hạn lượt phản biện</span>
                            </div>
                            <select
                                className="vc-setting-select"
                                value={sessionSettings.roundLimit}
                                onChange={(e) => setSessionSettings(prev => ({
                                    ...prev,
                                    roundLimit: parseInt(e.target.value)
                                }))}
                            >
                                <option value={2}>2 lượt</option>
                                <option value={3}>3 lượt</option>
                                <option value={4}>4 lượt</option>
                                <option value={5}>5 lượt</option>
                                <option value={6}>6 lượt</option>
                            </select>
                        </div>

                        <div className="vc-setting-row">
                            <div className="vc-setting-label">
                                <span>⏸️</span>
                                <span>Cho phép tạm dừng 10 giây</span>
                            </div>
                            <div
                                className={`vc-toggle${sessionSettings.pauseEnabled ? ' on' : ''}`}
                                onClick={() => setSessionSettings(prev => ({
                                    ...prev,
                                    pauseEnabled: !prev.pauseEnabled
                                }))}
                            >
                                <input
                                    type="checkbox"
                                    checked={sessionSettings.pauseEnabled}
                                    readOnly
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <div className="vc-nav">
                    <button className="vc-btn-back" onClick={() => navigate(-1)}>
                        ← Quay lại
                    </button>
                    <button className="vc-btn-next" onClick={handleContinue}>
                        Tiếp tục → Xây dựng chiến lược
                    </button>
                </div>
            </div>
        </div>
    )
}

export default CaseFile
