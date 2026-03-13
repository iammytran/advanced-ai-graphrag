import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSuggestedQuestions, sendMessage } from './services/backendApi'
import { generateImageFromGemini } from './services/geminiApi'

function App() {
    const [messages, setMessages] = useState([])
    const [inputValue, setInputValue] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [character, setCharacter] = useState('normal')
    const [toneValue, setToneValue] = useState(50)
    const [illustrationType, setIllustrationType] = useState('none')
    const [showScrollTop, setShowScrollTop] = useState(false)

    const messagesEndRef = useRef(null)
    const messagesTopRef = useRef(null)
    const messagesContainerRef = useRef(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        const hasBotMessage = messages.some(m => m.type === 'bot')
        if (hasBotMessage) {
            setTimeout(() => setShowScrollTop(true), 500)
        }
    }, [messages])

    const scrollToTop = () => {
        messagesTopRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    const handleContainerScroll = () => {
        const container = messagesContainerRef.current
        if (!container) return
        if (container.scrollTop < 10) {
            setShowScrollTop(false)
        } else if (messages.some(m => m.type === 'bot')) {
            setShowScrollTop(true)
        }
    }

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return

        const userMessage = {
            id: Date.now(),
            type: 'user',
            text: inputValue,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInputValue('')
        setIsLoading(true)

        try {
            const response = await sendMessage(inputValue, {
                character,
                toneValue,
                illustrationType
            })

            const botMessageId = Date.now() + 1
            const botMessage = {
                id: botMessageId,
                type: 'bot',
                text: response.text,
                character: response.character,
                illustration: response.illustration ? { ...response.illustration, isLoadingImage: true } : null,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, botMessage])

            if (response.illustration) {
                generateImageFromGemini(response.character, toneValue, illustrationType, response.text)
                    .then(imageUrl => {
                        setMessages(prev => prev.map(msg => {
                            if (msg.id === botMessageId) {
                                return {
                                    ...msg,
                                    illustration: {
                                        ...msg.illustration,
                                        url: imageUrl || msg.illustration.url,
                                        isLoadingImage: false
                                    }
                                }
                            }
                            return msg
                        }))
                    })
            }
        } catch (error) {
            console.error('Error:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleSuggestionClick = (question) => {
        setInputValue(question)
    }

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const formatTime = (date) => {
        return new Date(date).toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const getToneLabel = () => {
        if (toneValue < 30) return 'Đời thường'
        if (toneValue > 70) return 'Pháp lý'
        return 'Cân bằng'
    }

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="app-sidebar">
                <div className="app-sidebar-header">
                    <div className="app-logo">
                        <span className="app-logo-icon">⚖️</span>
                        <div>
                            <h1 className="app-logo-title">Legal AI</h1>
                            <p className="app-logo-sub">Hỗ trợ pháp luật thông minh</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="app-nav">
                    <Link to="/" className="app-nav-item active">
                        <span className="app-nav-icon">💬</span>
                        <span className="app-nav-label">Hỏi đáp AI</span>
                    </Link>
                    <Link to="/courtroom" className="app-nav-item">
                        <span className="app-nav-icon">🏛️</span>
                        <span className="app-nav-label">Phòng tòa ảo</span>
                    </Link>
                    <Link to="/courtroom/badges" className="app-nav-item">
                        <span className="app-nav-icon">🏆</span>
                        <span className="app-nav-label">Huy hiệu</span>
                    </Link>
                </nav>

                {/* Character Selection */}
                <div className="app-settings-section">
                    <div className="app-section-label">Chọn nhân vật trả lời</div>
                    <div className="app-character-options">
                        <div
                            className={`app-character-card ${character === 'lawyer' ? 'selected' : ''}`}
                            onClick={() => setCharacter('lawyer')}
                        >
                            <div className="app-character-avatar app-character-avatar--lawyer">👨‍⚖️</div>
                            <div className="app-character-info">
                                <div className="app-character-name">Luật sư</div>
                                <div className="app-character-desc">Nghiêm túc · Chuyên nghiệp</div>
                            </div>
                            <div className="app-character-check">
                                {character === 'lawyer' && '✓'}
                            </div>
                        </div>
                        <div
                            className={`app-character-card ${character === 'normal' ? 'selected' : ''}`}
                            onClick={() => setCharacter('normal')}
                        >
                            <div className="app-character-avatar app-character-avatar--normal">👤</div>
                            <div className="app-character-info">
                                <div className="app-character-name">Người bình thường</div>
                                <div className="app-character-desc">Dễ hiểu · Thân thiện</div>
                            </div>
                            <div className="app-character-check">
                                {character === 'normal' && '✓'}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Tone Slider */}
                <div className="app-settings-section">
                    <div className="app-section-label">Tone phản hồi</div>
                    <div className="app-tone-box">
                        <div className="app-tone-labels">
                            <span className={`app-tone-label ${toneValue < 50 ? 'active' : ''}`}>
                                💬 Đời thường
                            </span>
                            <span className={`app-tone-label ${toneValue >= 50 ? 'active' : ''}`}>
                                ⚖️ Pháp lý
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={toneValue}
                            onChange={(e) => setToneValue(Number(e.target.value))}
                            className="app-tone-slider"
                        />
                        <div className="app-tone-value">
                            {getToneLabel()} ({toneValue}%)
                        </div>
                    </div>
                </div>

                {/* Illustration Options */}
                <div className="app-settings-section">
                    <div className="app-section-label">Hình minh họa</div>
                    <div className="app-illust-options">
                        {[
                            { key: 'none', icon: '❌', label: 'Không có hình', desc: 'Chỉ hiển thị văn bản' },
                            { key: 'comic', icon: '📖', label: 'Truyện tranh', desc: 'Dễ ghi nhớ, chia sẻ' },
                            { key: 'poster', icon: '📢', label: 'Poster tuyên truyền', desc: 'Giáo dục, nâng cao nhận thức' }
                        ].map(opt => (
                            <div
                                key={opt.key}
                                className={`app-illust-option ${illustrationType === opt.key ? 'selected' : ''}`}
                                onClick={() => setIllustrationType(opt.key)}
                            >
                                <div className="app-illust-radio">
                                    <div className="app-illust-radio-dot" />
                                </div>
                                <span className="app-illust-icon">{opt.icon}</span>
                                <div className="app-illust-text">
                                    <div className="app-illust-label">{opt.label}</div>
                                    <div className="app-illust-desc">{opt.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Chat */}
            <main className="app-main">
                {/* Chat Header */}
                <header className="app-chat-header">
                    <div className="app-chat-title">
                        <span className="app-chat-title-icon">
                            {character === 'lawyer' ? '👨‍⚖️' : '👤'}
                        </span>
                        <h2>
                            {character === 'lawyer' ? 'Tư vấn cùng Luật sư' : 'Trò chuyện thân thiện'}
                        </h2>
                    </div>
                    <div className="app-chat-status">
                        <span className="app-status-dot" />
                        <span>Sẵn sàng hỗ trợ</span>
                    </div>
                </header>

                {/* Messages or Welcome */}
                {messages.length === 0 ? (
                    <div className="app-welcome">
                        <div className="app-welcome-icon">💬</div>
                        <h2 className="app-welcome-title">Chào mừng bạn đến với Legal AI!</h2>
                        <p className="app-welcome-desc">
                            Hãy đặt câu hỏi về pháp luật, tôi sẽ giải đáp theo phong cách bạn chọn.
                            Bạn có thể thử các câu hỏi gợi ý bên dưới.
                        </p>
                        <div className="app-suggestions">
                            {getSuggestedQuestions().map((question, index) => (
                                <button
                                    key={index}
                                    className="app-suggestion-chip"
                                    onClick={() => handleSuggestionClick(question)}
                                >
                                    {question}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div
                        className="app-messages"
                        ref={messagesContainerRef}
                        onScroll={handleContainerScroll}
                    >
                        <div ref={messagesTopRef} />

                        {messages.map((message) => (
                            <div key={message.id} className={`app-msg app-msg--${message.type}`}>
                                <div className={`app-msg-avatar ${message.type === 'bot' ? `app-msg-avatar--${message.character}` : ''}`}>
                                    {message.type === 'user' ? '👤' : (message.character === 'lawyer' ? '👨‍⚖️' : '😊')}
                                </div>
                                <div className="app-msg-content">
                                    <div className="app-msg-bubble">
                                        {message.text.split('\n').map((line, i) => (
                                            <span key={i}>
                                                {line}
                                                {i < message.text.split('\n').length - 1 && <br />}
                                            </span>
                                        ))}
                                    </div>
                                    {message.illustration && (
                                        <div className="app-msg-illust">
                                            {message.illustration.isLoadingImage ? (
                                                <div className="app-msg-illust-loading">
                                                    <span>🖼️ Đang vẽ hình minh họa...</span>
                                                </div>
                                            ) : (
                                                <img src={message.illustration.url} alt={message.illustration.caption} />
                                            )}
                                            <div className="app-msg-illust-caption">
                                                {message.illustration.caption}
                                            </div>
                                        </div>
                                    )}
                                    <span className="app-msg-time">{formatTime(message.timestamp)}</span>
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="app-msg app-msg--bot">
                                <div className={`app-msg-avatar app-msg-avatar--${character}`}>
                                    {character === 'lawyer' ? '👨‍⚖️' : '😊'}
                                </div>
                                <div className="app-msg-content">
                                    <div className="app-msg-bubble">
                                        <div className="app-msg-typing">
                                            <span /><span /><span />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}

                {/* Chat Input */}
                <div className="app-input-area">
                    <div className="app-input-wrapper">
                        <input
                            type="text"
                            className="app-input"
                            placeholder="Nhập câu hỏi của bạn về pháp luật..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={isLoading}
                        />
                        <button
                            className="app-send-btn"
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isLoading}
                        >
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M4 10L16 10M16 10L10 4M16 10L10 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </button>
                    </div>
                    <p className="app-input-disclaimer">AI có thể mắc lỗi. Hãy kiểm tra lại những thông tin quan trọng.</p>
                </div>

                {/* Scroll to top */}
                {messages.length > 0 && showScrollTop && (
                    <button className="app-scroll-top" onClick={scrollToTop} title="Kéo lên đầu trang">
                        ⬆
                    </button>
                )}
            </main>
        </div>
    )
}

export default App