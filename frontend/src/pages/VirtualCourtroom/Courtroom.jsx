import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios, getOpponentResponse } from '../../services/courtroomMockApi'

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
    }, [navigate])

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

    if (!scenario) {
        return <div className="courtroom-page">Loading...</div>
    }

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
    )
}

export default Courtroom
