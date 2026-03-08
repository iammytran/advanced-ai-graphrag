import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, getOpponentResponse, getBotSuggestions } from '../../services/courtroomMockApi'

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
    const [totalRounds] = useState(4)
    const [messages, setMessages] = useState([])
    const [userInput, setUserInput] = useState('')
    const [isOpponentTurn, setIsOpponentTurn] = useState(false)
    const [objectionsUsed, setObjectionsUsed] = useState(0)

    // Left panel suggestions
    const [botSuggestions, setBotSuggestions] = useState([])

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

        // Set timer based on settings
        const timeInSeconds = (sess.settings?.timeLimit || 10) * 60
        setTimeRemaining(timeInSeconds)

        // Start with opening statement from plaintiff
        const openingMessage = {
            id: Date.now(),
            type: 'system',
            text: `📢 Phiên tòa bắt đầu!\n\nVụ án: ${sc?.name}\nVai trò của bạn: ${sess.role === 'defendant' ? 'Luật sư bào chữa' : 'Luật sư nguyên đơn'}\n\nHãy trình bày luận điểm mở đầu của bạn.`
        }
        setMessages([openingMessage])

        // Load initial bot suggestions
        const suggestions = getBotSuggestions(1, sess.coach?.type || 'normal', sess.coach?.options || {})
        setBotSuggestions(suggestions)
    }, [navigate])

    // Update suggestions when round changes
    useEffect(() => {
        if (!session) return
        const suggestions = getBotSuggestions(currentRound, session.coach?.type || 'normal', session.coach?.options || {})
        setBotSuggestions(suggestions)
    }, [currentRound, session])

    // Timer countdown
    useEffect(() => {
        if (timeRemaining <= 0 || isPaused) {
            return
        }

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
            text: '⏰ Hết thời gian! Phiên tòa kết thúc.'
        }])
        setTimeout(() => endSession(), 2000)
    }

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }

    const getTimeClass = () => {
        if (timeRemaining <= 60) return 'critical'
        if (timeRemaining <= 180) return 'warning'
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

        setTimeout(() => {
            setIsPaused(false)
        }, 10000)
    }

    const handleSendMessage = async () => {
        if (!userInput.trim() || isOpponentTurn) return

        // Add user message
        const userMessage = {
            id: Date.now(),
            type: 'user',
            text: userInput,
            round: currentRound
        }
        setMessages(prev => [...prev, userMessage])
        setUserInput('')
        setIsOpponentTurn(true)

        // Get opponent response
        try {
            const response = await getOpponentResponse(currentRound, userInput, scenario)

            const opponentMessage = {
                id: Date.now() + 1,
                type: 'opponent',
                text: response.text,
                round: currentRound
            }
            setMessages(prev => [...prev, opponentMessage])

            // Check if round complete
            if (currentRound >= totalRounds) {
                setMessages(prev => [...prev, {
                    id: Date.now() + 2,
                    type: 'system',
                    text: '📋 Đã hoàn thành 4 vòng tranh luận. Hãy đưa ra kết luận cuối cùng.'
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

    const handleObjection = () => {
        if (objectionsUsed >= (session?.settings?.objectionLimit || 3)) {
            alert('Đã hết lượt phản đối!')
            return
        }

        setObjectionsUsed(prev => prev + 1)
        setMessages(prev => [...prev, {
            id: Date.now(),
            type: 'objection',
            text: '✋ PHẢN ĐỐI! Lập luận không có căn cứ pháp lý.'
        }])
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

    // Click suggestion → fill input
    const handleSuggestionClick = (suggestionText) => {
        // Strip the icon prefix and quotes for cleaner input
        const cleaned = suggestionText.replace(/^[^\s]+\s*"?/, '').replace(/"$/, '')
        setUserInput(cleaned)
    }

    // Click argument card → paste argument + linked evidences into input
    const handleArgumentClick = (arg, linkedEvidences) => {
        let text = arg.text
        if (linkedEvidences.length > 0) {
            const evidenceList = linkedEvidences.map(ev => `"${ev.name}"`).join(', ')
            text += `\n\n📎 Chứng cứ đính kèm: ${evidenceList}`
        }
        setUserInput(text)
    }

    if (!scenario) {
        return <div className="courtroom-page">Loading...</div>
    }

    const strategy = session?.strategy
    const coach = session?.coach

    return (
        <div className="courtroom-page courtroom-session">
            {/* Timer Header */}
            <header className="courtroom-header">
                <div className="round-info">
                    <span className="round-label">Vòng {currentRound}/{totalRounds}</span>
                    <span className="scenario-name">{scenario.name}</span>
                </div>

                <div className={`timer ${getTimeClass()}`}>
                    <span className="timer-icon">⏱️</span>
                    <span className="timer-value">{formatTime(timeRemaining)}</span>
                    {isPaused && <span className="paused-label">TẠM DỪNG</span>}
                </div>

                <div className="timer-progress">
                    <div
                        className="progress-bar"
                        style={{
                            width: `${(timeRemaining / ((session?.settings?.timeLimit || 10) * 60)) * 100}%`
                        }}
                    />
                </div>
            </header>

            {/* Main Body - 30/70 Split */}
            <div className="courtroom-body">

                {/* LEFT PANEL — 30% */}
                <div className="session-left-panel">

                    {/* TOP: Scenario Info */}
                    <div className="session-scenario-info">
                        <div className="panel-title">
                            <span className="panel-title-icon">🏛️</span>
                            <div>
                                <h3>Tình huống</h3>
                                <p>{session?.role === 'defendant' ? 'Luật sư bào chữa' : 'Luật sư nguyên đơn'}</p>
                            </div>
                        </div>

                        <div className="scenario-detail-content">
                            <div className="scenario-detail-name">{scenario.name}</div>
                            <p className="scenario-detail-desc">{scenario.description}</p>

                            <div className="scenario-detail-section">
                                <div className="scenario-detail-label">📋 Tóm tắt vụ án</div>
                                <p className="scenario-detail-summary">{scenario.summary}</p>
                            </div>

                            {scenario.facts?.length > 0 && (
                                <div className="scenario-detail-section">
                                    <div className="scenario-detail-label">🔍 Sự kiện pháp lý</div>
                                    <ul className="scenario-facts-list">
                                        {scenario.facts.map((fact, i) => (
                                            <li key={i}>
                                                <span className="fact-dot">•</span>
                                                <span>{fact}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* BOTTOM: Strategy Info */}
                    <div className="session-strategy-info">
                        <div className="panel-title">
                            <span className="panel-title-icon">📋</span>
                            <div>
                                <h3>Chiến lược của bạn</h3>
                                <p>Đã xây dựng trước phiên tòa</p>
                            </div>
                        </div>

                        {!strategy ? (
                            <div className="strategy-empty">
                                <span>📝</span>
                                <p>Không có chiến lược được xây dựng trước</p>
                            </div>
                        ) : (
                            <div className="strategy-content-panel">
                                {/* Arguments */}
                                {/* Arguments — each clickable, with linked evidences shown inline */}
                                {strategy.arguments?.length > 0 && (
                                    <div className="strategy-block">
                                        <div className="strategy-block-title">💬 Luận điểm · click để dán vào chat</div>
                                        {strategy.arguments.map((arg, i) => {
                                            if (!arg.text) return null
                                            // Find evidences linked to this argument
                                            const linked = (strategy.evidences || []).filter(
                                                ev => ev.linkedArguments?.includes(arg.id)
                                            )
                                            return (
                                                <button
                                                    key={arg.id || i}
                                                    className={`strategy-arg-card ${linked.length > 0 ? 'has-evidence' : ''}`}
                                                    onClick={() => handleArgumentClick(arg, linked)}
                                                    title="Click để dán luận điểm + chứng cứ vào ô nhập liệu"
                                                >
                                                    <div className="strategy-arg-top">
                                                        <span className="strategy-num">{i + 1}</span>
                                                        <span className="strategy-arg-text">{arg.text}</span>
                                                    </div>
                                                    {linked.length > 0 && (
                                                        <div className="strategy-arg-evidences">
                                                            {linked.map(ev => (
                                                                <span key={ev.id} className="strategy-ev-tag" title={ev.name}>
                                                                    <span className="ev-icon">📄</span>
                                                                    <span className="ev-name">{ev.name}</span>
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}
                                                    <div className="strategy-arg-hint">↗ Dán vào chat</div>
                                                </button>
                                            )
                                        })}
                                    </div>
                                )}

                                {/* Standalone evidences (not linked to any argument) */}
                                {strategy.evidences?.some(ev => !ev.linkedArguments?.length) && (
                                    <div className="strategy-block">
                                        <div className="strategy-block-title">📎 Chứng cứ khác</div>
                                        {strategy.evidences.filter(ev => !ev.linkedArguments?.length).map((ev, i) => (
                                            <div key={ev.id || i} className="strategy-evidence-item">
                                                <span>📄</span>
                                                <span>{ev.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Requirements */}
                                {strategy.requirements && (
                                    <div className="strategy-block">
                                        <div className="strategy-block-title">🎯 Yêu cầu</div>
                                        <p className="strategy-requirements">{strategy.requirements}</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                </div>

                {/* RIGHT PANEL — 70% */}
                <div className="session-right-panel">
                    {/* Messages Area */}
                    <div className="courtroom-messages">
                        {messages.map(msg => (
                            <div key={msg.id} className={`courtroom-message ${msg.type}`}>
                                <div className="message-avatar">
                                    {msg.type === 'user' && '👤'}
                                    {msg.type === 'opponent' && '🤖'}
                                    {msg.type === 'system' && '⚖️'}
                                    {msg.type === 'objection' && '✋'}
                                </div>
                                <div className="message-content">
                                    {msg.type === 'user' && <span className="sender">Bạn</span>}
                                    {msg.type === 'opponent' && <span className="sender">Đối phương</span>}
                                    <p>{msg.text}</p>
                                </div>
                            </div>
                        ))}

                        {isOpponentTurn && (
                            <div className="courtroom-message opponent typing">
                                <div className="message-avatar">🤖</div>
                                <div className="message-content">
                                    <span className="typing-indicator">Đang phản hồi...</span>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Coach Suggestions — above input */}
                    {botSuggestions.length > 0 && (
                        <div className="session-coach-suggestions-bar">
                            <div className="coach-suggestions-header">
                                <span>{coach?.type === 'lawyer' ? '👨‍⚖️' : '😊'}</span>
                                <span>Gợi ý coach · Vòng {currentRound}</span>
                            </div>
                            <div className="coach-suggestions-chips">
                                {botSuggestions.map((sug, idx) => (
                                    <button
                                        key={idx}
                                        className={`coach-chip coach-chip-${sug.type}`}
                                        onClick={() => handleSuggestionClick(sug.text)}
                                        title={sug.text}
                                    >
                                        <span>{sug.icon}</span>
                                        <span className="coach-chip-text">{sug.text}</span>
                                    </button>
                                ))}
                            </div>
                            {coach?.options?.autoObjection && (
                                <div className="auto-objection-hint">✋ Tự động phản đối BẬT</div>
                            )}
                        </div>
                    )}

                    {/* Input Area */}
                    <div className="courtroom-input">
                        <div className="input-controls">
                            <button
                                className="control-btn pause-btn"
                                onClick={handlePause}
                                disabled={!session?.settings?.pauseEnabled || pausesUsed >= 3 || isPaused}
                            >
                                ⏸️ Tạm dừng ({3 - pausesUsed} lượt)
                            </button>

                            <button
                                className="control-btn objection-btn"
                                onClick={handleObjection}
                                disabled={objectionsUsed >= (session?.settings?.objectionLimit || 3)}
                            >
                                ✋ Phản đối ({(session?.settings?.objectionLimit || 3) - objectionsUsed} lượt)
                            </button>

                            <button
                                className="control-btn end-btn"
                                onClick={handleEndEarly}
                            >
                                ⏹️ Kết thúc
                            </button>
                        </div>

                        <div className="input-row">
                            <textarea
                                placeholder="Nhập lập luận của bạn... (hoặc click gợi ý Coach phía trên)"
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
                                className="send-btn"
                                onClick={handleSendMessage}
                                disabled={isOpponentTurn || !userInput.trim() || currentRound > totalRounds}
                            >
                                ➡️ Gửi
                            </button>
                        </div>

                        {currentRound > totalRounds && (
                            <button className="conclude-btn" onClick={endSession}>
                                📋 Đưa ra kết luận cuối cùng
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Courtroom
