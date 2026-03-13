import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCoachFeedback, getOpponentResponse, scenarios } from '../../services/courtroomMockApi'

function Courtroom() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)

    // Timer state
    const [timeRemaining, setTimeRemaining] = useState(0)
    const [isPaused, setIsPaused] = useState(false)
    const [pausesUsed, setPausesUsed] = useState(0)
    const timerRef = useRef(null)

    // Round state
    const [currentRound, setCurrentRound] = useState(1)
    const [totalRounds, setTotalRounds] = useState(4)
    const [messages, setMessages] = useState([])
    const [userInput, setUserInput] = useState('')
    const [isOpponentTurn, setIsOpponentTurn] = useState(false)

    // Coach feedback in session
    const [sessionLoadingKey, setSessionLoadingKey] = useState(null)
    const [coachModal, setCoachModal] = useState(null)
    const [usedCoachKeys, setUsedCoachKeys] = useState(new Set())

    const sessionCoachButtons = [
        { key: 'openingSuggestion', icon: '💡', label: 'Gợi ý câu mở đầu' },
        { key: 'evidenceReminder', icon: '📎', label: 'Nhắc chứng cứ' },
        { key: 'autoObjection', icon: '✋', label: 'Soạn phản đối' },
        { key: 'riskWarning', icon: '⚠️', label: 'Cảnh báo rủi ro' }
    ]

    const messagesEndRef = useRef(null)

    // Initialize session
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

        const timeInSeconds = (sess.settings?.timeLimit || 10) * 60
        setTimeRemaining(timeInSeconds)
        setTotalRounds(sess.settings?.roundLimit || 4)

        const openingMessage = {
            id: Date.now(),
            type: 'system',
            text: `Phiên tòa bắt đầu!\n\nVụ án: ${sc?.name}\nVai trò của bạn: ${sess.role === 'defendant' ? 'Luật sư bào chữa' : 'Luật sư nguyên đơn'}\n\nHãy trình bày luận điểm mở đầu của bạn.`
        }
        setMessages([openingMessage])
    }, [navigate])

    // Timer countdown
    useEffect(() => {
        if (timeRemaining <= 0 || isPaused) return

        timerRef.current = setInterval(() => {
            setTimeRemaining(prev => {
                if (prev <= 1) {
                    clearInterval(timerRef.current)
                    handleTimeUp()
                    return 0
                }
                return prev - 1
            })
        }, 1000)

        return () => clearInterval(timerRef.current)
    }, [isPaused, timeRemaining])

    // Auto scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const handleTimeUp = () => {
        setMessages(prev => [...prev, {
            id: Date.now(),
            type: 'system',
            text: 'Hết thời gian! Phiên tòa kết thúc.'
        }])
        setTimeout(() => endSession(), 2000)
    }

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }

    const getTimeClass = () => {
        if (timeRemaining <= 60) return 'vc-timer--critical'
        if (timeRemaining <= 180) return 'vc-timer--warning'
        return ''
    }

    const handlePause = () => {
        if (!session?.settings?.pauseEnabled) return
        if (pausesUsed >= 3) {
            alert('Bạn đã sử dụng hết lượt tạm dừng!')
            return
        }
        setIsPaused(true)
        setPausesUsed(prev => prev + 1)
        setTimeout(() => setIsPaused(false), 10000)
    }

    const handleSendMessage = async () => {
        if (!userInput.trim() || isOpponentTurn) return

        const userMessage = {
            id: Date.now(),
            type: 'user',
            text: userInput,
            round: currentRound
        }
        setMessages(prev => [...prev, userMessage])
        setUserInput('')
        setIsOpponentTurn(true)

        try {
            const response = await getOpponentResponse(currentRound, userInput, scenario, session.role, messages)
            const opponentMessage = {
                id: Date.now() + 1,
                type: 'opponent',
                text: response.text,
                round: currentRound
            }
            setMessages(prev => [...prev, opponentMessage])

            if (currentRound >= totalRounds) {
                setMessages(prev => [...prev, {
                    id: Date.now() + 2,
                    type: 'system',
                    text: `Đã hoàn thành ${totalRounds} vòng tranh luận. Hãy đưa ra kết luận cuối cùng.`
                }])
            } else {
                setCurrentRound(prev => prev + 1)
            }
        } catch (error) {
            console.error(error)
        } finally {
            setIsOpponentTurn(false)
        }
    }

    const endSession = useCallback(() => {
        const updatedSession = {
            ...session,
            completed: true,
            timeRemaining,
            roundsCompleted: currentRound,
            messages
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/results')
    }, [session, timeRemaining, currentRound, messages, navigate])

    const handleEndEarly = () => {
        if (window.confirm('Bạn có chắc muốn kết thúc phiên tòa sớm?')) {
            endSession()
        }
    }

    const handleArgumentClick = (arg, linkedEvidences) => {
        let text = arg.text
        if (linkedEvidences.length > 0) {
            const evidenceList = linkedEvidences.map(ev => `"${ev.name}"`).join(', ')
            text += `\n\nChứng cứ đính kèm: ${evidenceList}`
        }
        setUserInput(text)
    }

    const getSessionCoachAdvice = async (key) => {
        if (!session?.coach) return
        setSessionLoadingKey(key)
        const content = JSON.stringify({
            arguments: session?.strategy?.arguments || [],
            evidences: session?.strategy?.evidences || []
        })
        try {
            const feedback = await getCoachFeedback(
                content,
                session.coach.type,
                session.coach.tone,
                scenario,
                session.role,
                key,
                messages
            )
            setUsedCoachKeys(prev => new Set([...prev, key]))
            const btn = sessionCoachButtons.find(b => b.key === key)
            setCoachModal({ key, icon: btn?.icon, label: btn?.label, text: feedback.text })
        } catch (error) {
            console.error(error)
        } finally {
            setSessionLoadingKey(null)
        }
    }

    if (!scenario) {
        return (
            <div className="vc-page">
                <div className="vc-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
                    <div className="vc-session-loading">
                        <div className="sb-coach-loading-dots"><span /><span /><span /></div>
                        <p style={{ marginTop: 12, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Đang tải phiên tòa...</p>
                    </div>
                </div>
            </div>
        )
    }

    const strategy = session?.strategy
    const coach = session?.coach
    const timeProgress = (timeRemaining / ((session?.settings?.timeLimit || 10) * 60)) * 100

    return (
        <div className="vc-page vc-session">
            {/* Session Header */}
            <header className="vc-session-header">
                <div className="vc-session-header-left">
                    <div className="vc-session-round-badge">
                        Vòng {currentRound}/{totalRounds}
                    </div>
                    <div className="vc-session-case-info">
                        <span className="vc-session-case-name">{scenario.name}</span>
                        <span className="vc-session-role-tag">
                            {session?.role === 'defendant' ? '🛡️ Bào chữa' : '⚔️ Nguyên đơn'}
                        </span>
                    </div>
                </div>

                <div className="vc-session-header-center">
                    <div className={`vc-timer ${getTimeClass()}`}>
                        <span className="vc-timer-value">{formatTime(timeRemaining)}</span>
                        {isPaused && <span className="vc-timer-paused">TẠM DỪNG</span>}
                    </div>
                    <div className="vc-timer-bar">
                        <div className="vc-timer-bar-fill" style={{ width: `${timeProgress}%` }} />
                    </div>
                </div>

                <div className="vc-session-header-right">
                    <div className="vc-session-meta">
                        <span className="vc-session-meta-item">🔄 {totalRounds} vòng</span>
                        <span className="vc-session-meta-item">⏱️ {session?.settings?.timeLimit || 10}p</span>
                        {session?.settings?.pauseEnabled && (
                            <span className="vc-session-meta-item">⏸️ {3 - pausesUsed} lượt</span>
                        )}
                    </div>
                    <button className="vc-session-end-btn" onClick={handleEndEarly}>
                        Kết thúc
                    </button>
                </div>
            </header>

            {/* Main Body */}
            <div className="vc-session-body">

                {/* LEFT PANEL */}
                <div className="vc-session-sidebar">

                    {/* Scenario Info */}
                    <div className="vc-session-panel">
                        <div className="vc-session-panel-header">
                            <span className="vc-session-panel-icon">🏛️</span>
                            <div>
                                <div className="vc-session-panel-title">Tình huống</div>
                                <div className="vc-session-panel-sub">
                                    {session?.role === 'defendant' ? 'Luật sư bào chữa' : 'Luật sư nguyên đơn'}
                                </div>
                            </div>
                        </div>

                        <div className="vc-session-panel-body">
                            <div className="vc-session-case-title">{scenario.name}</div>
                            <p className="vc-session-case-desc">{scenario.description}</p>

                            <div className="vc-session-info-block">
                                <div className="vc-session-info-label">Tóm tắt vụ án</div>
                                <p className="vc-session-info-text">{scenario.summary}</p>
                            </div>

                            {scenario.facts?.length > 0 && (
                                <div className="vc-session-info-block">
                                    <div className="vc-session-info-label">Sự kiện pháp lý</div>
                                    <ul className="vc-session-facts">
                                        {scenario.facts.map((fact, i) => (
                                            <li key={i}>{fact}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Strategy Info */}
                    <div className="vc-session-panel">
                        <div className="vc-session-panel-header">
                            <span className="vc-session-panel-icon">📋</span>
                            <div>
                                <div className="vc-session-panel-title">Chiến lược</div>
                                <div className="vc-session-panel-sub">Đã xây dựng trước phiên tòa</div>
                            </div>
                        </div>

                        {!strategy ? (
                            <div className="vc-session-empty">
                                <span>📝</span>
                                <p>Không có chiến lược</p>
                            </div>
                        ) : (
                            <div className="vc-session-panel-body">
                                {strategy.arguments?.length > 0 && (
                                    <div className="vc-session-info-block">
                                        <div className="vc-session-info-label">Luận điểm · click để dán</div>
                                        {strategy.arguments.map((arg, i) => {
                                            if (!arg.text) return null
                                            const linked = (strategy.evidences || []).filter(
                                                ev => ev.linkedArguments?.includes(arg.id)
                                            )
                                            return (
                                                <button
                                                    key={arg.id || i}
                                                    className={`vc-session-arg-card ${linked.length > 0 ? 'has-evidence' : ''}`}
                                                    onClick={() => handleArgumentClick(arg, linked)}
                                                    title="Click để dán vào ô nhập liệu"
                                                >
                                                    <div className="vc-session-arg-top">
                                                        <span className="vc-session-arg-num">{i + 1}</span>
                                                        <span className="vc-session-arg-text">{arg.text}</span>
                                                    </div>
                                                    {linked.length > 0 && (
                                                        <div className="vc-session-arg-evs">
                                                            {linked.map(ev => (
                                                                <span key={ev.id} className="vc-session-ev-tag" title={ev.name}>
                                                                    📄 {ev.name}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </button>
                                            )
                                        })}
                                    </div>
                                )}

                                {strategy.evidences?.some(ev => !ev.linkedArguments?.length) && (
                                    <div className="vc-session-info-block">
                                        <div className="vc-session-info-label">Chứng cứ khác</div>
                                        {strategy.evidences.filter(ev => !ev.linkedArguments?.length).map((ev, i) => (
                                            <div key={ev.id || i} className="vc-session-ev-item">
                                                <span>📄</span> {ev.name}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {strategy.requirements && (
                                    <div className="vc-session-info-block">
                                        <div className="vc-session-info-label">Yêu cầu</div>
                                        <p className="vc-session-info-text">{strategy.requirements}</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* RIGHT PANEL — Chat */}
                <div className="vc-session-main">
                    {/* Messages */}
                    <div className="vc-session-messages">
                        {messages.map(msg => (
                            <div key={msg.id} className={`vc-msg vc-msg--${msg.type}`}>
                                {msg.type !== 'system' && (
                                    <div className="vc-msg-avatar">
                                        {msg.type === 'user' && '👤'}
                                        {msg.type === 'opponent' && '🤖'}
                                        {msg.type === 'objection' && '✋'}
                                    </div>
                                )}
                                <div className="vc-msg-body">
                                    {msg.type === 'user' && <span className="vc-msg-sender">Bạn</span>}
                                    {msg.type === 'opponent' && <span className="vc-msg-sender">Đối phương</span>}
                                    {msg.type === 'system' && <span className="vc-msg-sender vc-msg-sender--system">⚖️ Hệ thống</span>}
                                    <div className="vc-msg-text">{msg.text}</div>
                                </div>
                            </div>
                        ))}

                        {isOpponentTurn && (
                            <div className="vc-msg vc-msg--opponent">
                                <div className="vc-msg-avatar">🤖</div>
                                <div className="vc-msg-body">
                                    <span className="vc-msg-sender">Đối phương</span>
                                    <div className="vc-msg-typing">
                                        <span /><span /><span />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Coach Bar */}
                    {coach && (
                        <div className="vc-session-coach-bar">
                            <div className="vc-session-coach-info">
                                <span className="vc-session-coach-icon">
                                    {coach.type === 'lawyer' ? '👨‍⚖️' : '😊'}
                                </span>
                                <span className="vc-session-coach-name">
                                    {coach.type === 'lawyer' ? 'Luật sư cố vấn' : 'Coach'}
                                </span>
                            </div>
                            <div className="vc-session-coach-actions">
                                {sessionCoachButtons
                                    .filter(btn => coach.options?.[btn.key])
                                    .map(btn => (
                                        <button
                                            key={btn.key}
                                            className={`vc-session-coach-btn ${usedCoachKeys.has(btn.key) ? 'used' : ''}`}
                                            onClick={() => getSessionCoachAdvice(btn.key)}
                                            disabled={sessionLoadingKey !== null || usedCoachKeys.has(btn.key)}
                                            title={usedCoachKeys.has(btn.key) ? 'Đã sử dụng' : btn.label}
                                        >
                                            {sessionLoadingKey === btn.key ? (
                                                <><span className="loading-spinner-small" /> Đang xử lý</>
                                            ) : (
                                                <>{btn.icon} {btn.label}</>
                                            )}
                                        </button>
                                    ))}
                            </div>
                        </div>
                    )}

                    {/* Input */}
                    <div className="vc-session-input">
                        <div className="vc-session-input-controls">
                            {session?.settings?.pauseEnabled && (
                                <button
                                    className={`vc-session-ctrl-btn vc-session-ctrl-btn--pause ${isPaused ? 'active' : ''}`}
                                    onClick={handlePause}
                                    disabled={isPaused || pausesUsed >= 3}
                                >
                                    {isPaused ? `⏸️ Đang tạm dừng...` : `⏸️ Tạm dừng (${3 - pausesUsed})`}
                                </button>
                            )}
                        </div>

                        <div className="vc-session-input-row">
                            <textarea
                                className="vc-session-textarea"
                                placeholder="Nhập lập luận của bạn..."
                                value={userInput}
                                onChange={(e) => setUserInput(e.target.value)}
                                disabled={isOpponentTurn || currentRound > totalRounds}
                                onKeyPress={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault()
                                        handleSendMessage()
                                    }
                                }}
                            />
                            <button
                                className="vc-session-send-btn"
                                onClick={handleSendMessage}
                                disabled={isOpponentTurn || !userInput.trim() || currentRound > totalRounds}
                            >
                                Gửi
                                <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                                    <path d="M4 10L16 10M16 10L10 4M16 10L10 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                            </button>
                        </div>

                        {currentRound > totalRounds && (
                            <button className="vc-session-conclude-btn" onClick={endSession}>
                                📋 Đưa ra kết luận cuối cùng
                            </button>
                        )}
                        <p className="vc-session-disclaimer">AI có thể mắc lỗi. Hãy kiểm tra lại những thông tin quan trọng.</p>
                    </div>
                </div>
            </div>

            {/* Coach Modal */}
            {coachModal && (
                <div className="vc-modal-overlay" onClick={() => setCoachModal(null)}>
                    <div className="vc-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="vc-modal-header">
                            <span className="vc-modal-icon">{coachModal.icon}</span>
                            <h3>{coachModal.label}</h3>
                            <button className="vc-modal-close" onClick={() => setCoachModal(null)}>
                                <svg width="16" height="16" viewBox="0 0 14 14" fill="none">
                                    <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                                </svg>
                            </button>
                        </div>
                        <div className="vc-modal-body">
                            <div className="vc-modal-sender">
                                <span>{coach?.type === 'lawyer' ? '👨‍⚖️' : '😊'}</span>
                                <span>{coach?.type === 'lawyer' ? 'Luật sư cố vấn' : 'Coach'}</span>
                            </div>
                            <p className="vc-modal-text">{coachModal.text}</p>
                        </div>
                        <div className="vc-modal-footer">
                            <button className="vc-btn-next" onClick={() => setCoachModal(null)}>
                                Đã hiểu
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Courtroom