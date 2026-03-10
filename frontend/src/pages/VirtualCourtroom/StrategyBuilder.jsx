import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, getCoachFeedback } from '../../services/courtroomMockApi'

function StrategyBuilder() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)

    const [arguments_, setArguments] = useState([{ id: 1, text: '' }])
    const [evidences, setEvidences] = useState([])
    const [coachFeedback, setCoachFeedback] = useState('')
    const [isLoadingFeedback, setIsLoadingFeedback] = useState(false)

    // Inline evidence input
    const [newEvidenceName, setNewEvidenceName] = useState('')
    const [showEvidenceInput, setShowEvidenceInput] = useState(false)
    const evidenceInputRef = useRef(null)

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

    useEffect(() => {
        if (showEvidenceInput && evidenceInputRef.current) {
            evidenceInputRef.current.focus()
        }
    }, [showEvidenceInput])

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
        if (newEvidenceName.trim()) {
            setEvidences(prev => [...prev, {
                id: Date.now(),
                name: newEvidenceName.trim(),
                linkedArguments: []
            }])
            setNewEvidenceName('')
            setShowEvidenceInput(false)
        }
    }

    const removeEvidence = (id) => {
        setEvidences(prev => prev.filter(ev => ev.id !== id))
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
            evidences
        }

        try {
            const feedback = await getCoachFeedback(
                JSON.stringify(content),
                session.coach.type,
                session.coach.tone,
                scenario,
                session.role,
                'general'
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
                evidences
            }
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/session')
    }

    const filledArguments = arguments_.filter(a => a.text.trim()).length
    const linkedEvidences = evidences.filter(e => e.linkedArguments.length > 0).length

    if (!scenario) {
        return <div className="courtroom-page">Loading...</div>
    }

    return (
        <div className="courtroom-page strategy-builder">
            {/* Compact header */}
            <header className="sb-header">
                <div className="sb-header-left">
                    <button className="sb-back-btn" onClick={() => navigate(-1)}>
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </button>
                    <div className="sb-header-info">
                        <h1>Xây Dựng Chiến Lược</h1>
                        <div className="sb-case-tag">
                            <span className="sb-case-icon">&#9878;</span>
                            <span>{scenario.name}</span>
                            <span className="sb-role-badge">
                                {session?.role === 'defendant' ? 'Bào chữa' : 'Nguyên đơn'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Progress indicators */}
                <div className="sb-progress">
                    <div className={`sb-progress-item ${filledArguments > 0 ? 'done' : ''}`}>
                        <span className="sb-progress-num">{filledArguments}</span>
                        <span className="sb-progress-label">Luận điểm</span>
                    </div>
                    <div className="sb-progress-divider" />
                    <div className={`sb-progress-item ${evidences.length > 0 ? 'done' : ''}`}>
                        <span className="sb-progress-num">{evidences.length}</span>
                        <span className="sb-progress-label">Chứng cứ</span>
                    </div>
                    <div className="sb-progress-divider" />
                    <div className={`sb-progress-item ${linkedEvidences > 0 ? 'done' : ''}`}>
                        <span className="sb-progress-num">{linkedEvidences}</span>
                        <span className="sb-progress-label">Liên kết</span>
                    </div>
                </div>

                <button
                    className="sb-start-btn"
                    onClick={handleContinue}
                    disabled={filledArguments === 0}
                >
                    Bắt đầu phiên tòa
                    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                        <path d="M7.5 5L12.5 10L7.5 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                </button>
            </header>

            {/* Two-column layout */}
            <div className="sb-body">

                {/* LEFT: Arguments + Evidence */}
                <div className="sb-col-left">

                    {/* Arguments */}
                    <div className="sb-section">
                        <div className="sb-section-header">
                            <div className="sb-section-title">
                                <span className="sb-section-icon sb-section-icon--args">&#128172;</span>
                                <div>
                                    <h2>Luận Điểm</h2>
                                    <p>Trình bày các luận điểm chính của bạn</p>
                                </div>
                            </div>
                            <button className="sb-add-btn" onClick={addArgument}>
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                </svg>
                                Thêm
                            </button>
                        </div>

                        <div className="sb-arguments-list">
                            {arguments_.map((arg, index) => (
                                <div
                                    key={arg.id}
                                    className={`sb-arg-card ${arg.text.trim() ? 'has-content' : ''}`}
                                    style={{ animationDelay: `${index * 0.05}s` }}
                                >
                                    <div className="sb-arg-index">
                                        <span>{index + 1}</span>
                                    </div>
                                    <div className="sb-arg-body">
                                        <textarea
                                            placeholder={`Luận điểm ${index + 1}: Nhập nội dung...`}
                                            value={arg.text}
                                            onChange={(e) => updateArgument(arg.id, e.target.value)}
                                            rows={2}
                                        />
                                        {/* Show linked evidence tags */}
                                        {evidences.filter(ev => ev.linkedArguments.includes(arg.id)).length > 0 && (
                                            <div className="sb-arg-evidence-tags">
                                                {evidences.filter(ev => ev.linkedArguments.includes(arg.id)).map(ev => (
                                                    <span key={ev.id} className="sb-arg-ev-tag">
                                                        &#128196; {ev.name}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <button
                                        className="sb-arg-remove"
                                        onClick={() => removeArgument(arg.id)}
                                        disabled={arguments_.length === 1}
                                        title="Xóa luận điểm"
                                    >
                                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                            <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                                        </svg>
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Evidence */}
                    <div className="sb-section">
                        <div className="sb-section-header">
                            <div className="sb-section-title">
                                <span className="sb-section-icon sb-section-icon--ev">&#128206;</span>
                                <div>
                                    <h2>Chứng Cứ</h2>
                                    <p>Thêm chứng cứ và liên kết với luận điểm</p>
                                </div>
                            </div>
                            <button
                                className="sb-add-btn"
                                onClick={() => setShowEvidenceInput(true)}
                            >
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                </svg>
                                Thêm
                            </button>
                        </div>

                        {/* Inline add evidence */}
                        {showEvidenceInput && (
                            <div className="sb-evidence-input-row">
                                <input
                                    ref={evidenceInputRef}
                                    type="text"
                                    placeholder="Tên chứng cứ (vd: Hợp đồng thuê nhà, Biên lai...)"
                                    value={newEvidenceName}
                                    onChange={(e) => setNewEvidenceName(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') addEvidence()
                                        if (e.key === 'Escape') {
                                            setShowEvidenceInput(false)
                                            setNewEvidenceName('')
                                        }
                                    }}
                                />
                                <button className="sb-ev-confirm" onClick={addEvidence} disabled={!newEvidenceName.trim()}>
                                    Thêm
                                </button>
                                <button className="sb-ev-cancel" onClick={() => { setShowEvidenceInput(false); setNewEvidenceName('') }}>
                                    Hủy
                                </button>
                            </div>
                        )}

                        <div className="sb-evidence-list">
                            {evidences.length === 0 && !showEvidenceInput && (
                                <div className="sb-empty">
                                    <span className="sb-empty-icon">&#128451;</span>
                                    <p>Chưa có chứng cứ nào</p>
                                    <span className="sb-empty-hint">Nhấn "Thêm" để bắt đầu</span>
                                </div>
                            )}

                            {evidences.map(ev => (
                                <div key={ev.id} className="sb-ev-card">
                                    <div className="sb-ev-top">
                                        <span className="sb-ev-icon">&#128196;</span>
                                        <span className="sb-ev-name">{ev.name}</span>
                                        <button
                                            className="sb-ev-remove"
                                            onClick={() => removeEvidence(ev.id)}
                                            title="Xóa chứng cứ"
                                        >
                                            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                                                <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                                            </svg>
                                        </button>
                                    </div>
                                    <div className="sb-ev-links">
                                        {arguments_.map((arg, i) => (
                                            <button
                                                key={arg.id}
                                                className={`sb-ev-link-chip ${ev.linkedArguments.includes(arg.id) ? 'active' : ''}`}
                                                onClick={() => toggleEvidenceLink(ev.id, arg.id)}
                                            >
                                                <span className="sb-ev-link-num">{i + 1}</span>
                                                {ev.linkedArguments.includes(arg.id) && (
                                                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                                                        <path d="M2 5L4 7L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                                    </svg>
                                                )}
                                            </button>
                                        ))}
                                        <span className="sb-ev-link-hint">Liên kết luận điểm</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* RIGHT: Coach */}
                <div className="sb-col-right">
                    <div className="sb-coach-panel">
                        <div className="sb-coach-header">
                            <div className="sb-coach-avatar">
                                {session?.coach?.type === 'lawyer' ? '\u{1F468}\u200D\u2696\uFE0F' : '\u{1F60A}'}
                            </div>
                            <div className="sb-coach-info">
                                <h3>{session?.coach?.type === 'lawyer' ? 'Luật sư cố vấn' : 'Người bình thường'}</h3>
                                <span className="sb-coach-tone">
                                    {session?.coach?.tone < 30 ? 'Đời thường' : session?.coach?.tone < 70 ? 'Cân bằng' : 'Pháp lý'}
                                </span>
                            </div>
                        </div>

                        <div className="sb-coach-body">
                            {!coachFeedback && !isLoadingFeedback && (
                                <div className="sb-coach-empty">
                                    <span className="sb-coach-empty-icon">&#128161;</span>
                                    <p>Nhấn nút bên dưới để nhận gợi ý xây dựng luận điểm từ {session?.coach?.type === 'lawyer' ? 'Luật sư cố vấn' : 'Coach'}.</p>
                                    <span className="sb-coach-empty-hint">Coach sẽ gợi ý luận điểm, hướng lập luận và chứng cứ nên chuẩn bị dựa trên vụ án.</span>
                                </div>
                            )}

                            {isLoadingFeedback && (
                                <div className="sb-coach-loading">
                                    <div className="sb-coach-loading-dots">
                                        <span /><span /><span />
                                    </div>
                                    <p>Đang chuẩn bị gợi ý...</p>
                                </div>
                            )}

                            {coachFeedback && !isLoadingFeedback && (
                                <div className="sb-coach-feedback">
                                    <p>{coachFeedback}</p>
                                </div>
                            )}
                        </div>

                        <button
                            className="sb-coach-btn"
                            onClick={getCoachAdvice}
                            disabled={isLoadingFeedback}
                        >
                            {isLoadingFeedback ? (
                                <><span className="loading-spinner-small" /> Đang chuẩn bị gợi ý...</>
                            ) : (
                                <>
                                    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                                        <path d="M10 3a4.5 4.5 0 0 0-1.5 8.74V14a1.5 1.5 0 0 0 3 0v-2.26A4.5 4.5 0 0 0 10 3zm0 1.5a3 3 0 0 1 1.04 5.81l-.54.2V14a.5.5 0 0 1-1 0v-3.49l-.54-.2A3 3 0 0 1 10 4.5z" fill="currentColor"/>
                                        <path d="M8.5 16h3M9 17.5h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                                    </svg>
                                    {coachFeedback ? 'Xin gợi ý mới' : 'Xin gợi ý luận điểm'}
                                </>
                            )}
                        </button>

                        {/* Case summary */}
                        <div className="sb-coach-case">
                            <div className="sb-coach-case-title">Thông tin vụ án</div>
                            <p className="sb-coach-case-summary">{scenario.description}</p>
                            {scenario.facts?.length > 0 && (
                                <ul className="sb-coach-facts">
                                    {scenario.facts.map((f, i) => (
                                        <li key={i}>{f}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default StrategyBuilder
