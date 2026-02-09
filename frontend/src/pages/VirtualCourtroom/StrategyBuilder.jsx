import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, getCoachFeedback } from '../../services/courtroomMockApi'

function StrategyBuilder() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)

    const [arguments_, setArguments] = useState([{ id: 1, text: '' }])
    const [evidences, setEvidences] = useState([])
    const [requirements, setRequirements] = useState('')
    const [coachFeedback, setCoachFeedback] = useState('')
    const [isLoadingFeedback, setIsLoadingFeedback] = useState(false)

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

    const addArgument = () => {
        setArguments(prev => [...prev, { id: Date.now(), text: '' }])
    }

    const updateArgument = (id, text) => {
        setArguments(prev => prev.map(arg =>
            arg.id === id ? { ...arg, text } : arg
        ))
    }

    const removeArgument = (id) => {
        if (arguments_.length > 1) {
            setArguments(prev => prev.filter(arg => arg.id !== id))
        }
    }

    const addEvidence = () => {
        const name = prompt('Nhập tên chứng cứ:')
        if (name) {
            setEvidences(prev => [...prev, {
                id: Date.now(),
                name,
                linkedArguments: []
            }])
        }
    }

    const toggleEvidenceLink = (evidenceId, argumentId) => {
        setEvidences(prev => prev.map(ev => {
            if (ev.id === evidenceId) {
                const linked = ev.linkedArguments.includes(argumentId)
                return {
                    ...ev,
                    linkedArguments: linked
                        ? ev.linkedArguments.filter(id => id !== argumentId)
                        : [...ev.linkedArguments, argumentId]
                }
            }
            return ev
        }))
    }

    const getCoachAdvice = async () => {
        if (!session?.coach) return

        setIsLoadingFeedback(true)
        const content = {
            arguments: arguments_,
            evidences,
            requirements
        }

        try {
            const feedback = await getCoachFeedback(
                JSON.stringify(content),
                session.coach.type,
                session.coach.tone
            )
            setCoachFeedback(feedback.text)
        } catch (error) {
            console.error(error)
        } finally {
            setIsLoadingFeedback(false)
        }
    }

    const handleContinue = () => {
        const updatedSession = {
            ...session,
            strategy: {
                arguments: arguments_,
                evidences,
                requirements
            }
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/session')
    }

    if (!scenario) {
        return <div className="courtroom-page">Loading...</div>
    }

    return (
        <div className="courtroom-page strategy-builder">
            <header className="page-header">
                <div className="breadcrumb">
                    <span onClick={() => navigate('/courtroom')}>Kịch bản</span>
                    <span> → ... → </span>
                    <span>Chiến lược</span>
                </div>
                <h1>📝 Xây Dựng Chiến Lược</h1>
                <p>Chuẩn bị luận điểm, chứng cứ và yêu cầu của bạn</p>
            </header>

            <div className="strategy-content">
                <div className="main-content">
                    <section className="arguments-section">
                        <h2>💬 Luận Điểm</h2>
                        {arguments_.map((arg, index) => (
                            <div key={arg.id} className="argument-item">
                                <span className="arg-number">{index + 1}</span>
                                <textarea
                                    placeholder="Nhập luận điểm của bạn..."
                                    value={arg.text}
                                    onChange={(e) => updateArgument(arg.id, e.target.value)}
                                />
                                <button
                                    className="remove-btn"
                                    onClick={() => removeArgument(arg.id)}
                                    disabled={arguments_.length === 1}
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                        <button className="add-btn" onClick={addArgument}>
                            + Thêm luận điểm
                        </button>
                    </section>

                    <section className="evidence-section">
                        <h2>📎 Bảng Chứng Cứ</h2>
                        <div className="evidence-list">
                            {evidences.map(ev => (
                                <div key={ev.id} className="evidence-item">
                                    <div className="evidence-name">📄 {ev.name}</div>
                                    <div className="evidence-links">
                                        <span className="link-label">Liên kết với:</span>
                                        {arguments_.map((arg, i) => (
                                            <label key={arg.id} className="link-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={ev.linkedArguments.includes(arg.id)}
                                                    onChange={() => toggleEvidenceLink(ev.id, arg.id)}
                                                />
                                                <span>Luận điểm {i + 1}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            {evidences.length === 0 && (
                                <p className="empty-state">Chưa có chứng cứ nào</p>
                            )}
                        </div>
                        <button className="add-btn" onClick={addEvidence}>
                            📤 Upload chứng cứ
                        </button>
                    </section>

                    <section className="requirements-section">
                        <h2>📋 Yêu Cầu Cụ Thể</h2>
                        <textarea
                            placeholder="Liệt kê các yêu cầu cụ thể của bạn (VD: Bồi thường 20 triệu đồng, xin lỗi công khai...)"
                            value={requirements}
                            onChange={(e) => setRequirements(e.target.value)}
                        />
                    </section>
                </div>

                <aside className="coach-panel">
                    <h2>🧑‍🏫 Coach Phản Hồi</h2>
                    <button
                        className="get-feedback-btn"
                        onClick={getCoachAdvice}
                        disabled={isLoadingFeedback}
                    >
                        {isLoadingFeedback ? 'Đang phân tích...' : '💡 Nhận phản hồi từ Coach'}
                    </button>

                    {coachFeedback && (
                        <div className="feedback-content">
                            <div className="coach-avatar">
                                {session?.coach?.type === 'lawyer' ? '👨‍⚖️' : '😊'}
                            </div>
                            <p>{coachFeedback}</p>
                        </div>
                    )}
                </aside>
            </div>

            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate(-1)}>
                    ← Quay lại
                </button>
                <button className="btn-primary" onClick={handleContinue}>
                    🏛️ Bắt đầu phiên tòa →
                </button>
            </div>
        </div>
    )
}

export default StrategyBuilder
