import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { sendMessage, getSuggestedQuestions } from './services/mockApi'

function App() {
    // State
    const [messages, setMessages] = useState([])
    const [inputValue, setInputValue] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [character, setCharacter] = useState('normal') // 'lawyer' or 'normal'
    const [toneValue, setToneValue] = useState(50)
    const [illustrationType, setIllustrationType] = useState('none')
    const [showScrollTop, setShowScrollTop] = useState(false)

    const messagesEndRef = useRef(null)
    const messagesTopRef = useRef(null)
    const messagesContainerRef = useRef(null)

    // Auto scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    // Hiện nút khi có tin nhắn từ bot
    useEffect(() => {
        const hasBotMessage = messages.some(m => m.type === 'bot')
        if (hasBotMessage) {
            // Delay để đảm bảo UI đã render
            setTimeout(() => setShowScrollTop(true), 500)
        }
    }, [messages])

    // Scroll to top
    const scrollToTop = () => {
        // Sử dụng scrollIntoView giống như scrollToBottom
        messagesTopRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    // Khi scroll bằng chuột - hiện lại nút nếu không ở đầu
    const handleContainerScroll = () => {
        const container = messagesContainerRef.current
        if (!container) return

        if (container.scrollTop < 10) {
            setShowScrollTop(false)
        } else if (messages.some(m => m.type === 'bot')) {
            setShowScrollTop(true)
        }
    }

    // Handle send message
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

            const botMessage = {
                id: Date.now() + 1,
                type: 'bot',
                text: response.text,
                character: response.character,
                illustration: response.illustration,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, botMessage])
        } catch (error) {
            console.error('Error:', error)
        } finally {
            setIsLoading(false)
        }
    }

    // Handle suggestion click
    const handleSuggestionClick = (question) => {
        setInputValue(question)
    }

    // Handle key press
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    // Format timestamp
    const formatTime = (date) => {
        return new Date(date).toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    // Get tone label
    const getToneLabel = () => {
        if (toneValue < 30) return 'Đời thường'
        if (toneValue > 70) return 'Pháp lý'
        return 'Cân bằng'
    }

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <div className="logo">⚖️</div>
                    <h1>Legal AI</h1>
                    <p>Hỗ trợ pháp luật thông minh</p>
                </div>

                {/* Navigation */}
                <nav className="sidebar-nav">
                    <Link to="/" className="nav-item active">
                        <span className="nav-icon">💬</span>
                        <span>Hỏi đáp AI</span>
                    </Link>
                    <Link to="/courtroom" className="nav-item">
                        <span className="nav-icon">🏛️</span>
                        <span>Phòng tòa ảo</span>
                    </Link>
                    <Link to="/courtroom/badges" className="nav-item">
                        <span className="nav-icon">🏆</span>
                        <span>Huy hiệu</span>
                    </Link>
                </nav>

                {/* Character Selection */}
                <div className="settings-section">
                    <div className="section-title">
                        <span>👤</span> Chọn nhân vật trả lời
                    </div>
                    <div className="character-options">
                        <div
                            className={`character-card lawyer ${character === 'lawyer' ? 'active' : ''}`}
                            onClick={() => setCharacter('lawyer')}
                        >
                            <div className="character-avatar lawyer">👨‍⚖️</div>
                            <div className="character-info">
                                <h3>Luật sư</h3>
                                <p>Nghiêm túc • Chuyên nghiệp • Chuẩn mực</p>
                            </div>
                        </div>
                        <div
                            className={`character-card normal ${character === 'normal' ? 'active' : ''}`}
                            onClick={() => setCharacter('normal')}
                        >
                            <div className="character-avatar normal">👤</div>
                            <div className="character-info">
                                <h3>Người bình thường</h3>
                                <p>Dễ hiểu • Gần gũi • Thân thiện</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Tone Slider */}
                <div className="settings-section">
                    <div className="section-title">
                        <span>🎚️</span> Tone phản hồi
                    </div>
                    <div className="tone-slider-container">
                        <div className="tone-labels">
                            <span className={`tone-label ${toneValue < 50 ? 'active' : ''}`}>
                                💬 Đời thường
                            </span>
                            <span className={`tone-label ${toneValue >= 50 ? 'active' : ''}`}>
                                ⚖️ Pháp lý
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={toneValue}
                            onChange={(e) => setToneValue(Number(e.target.value))}
                            className="tone-slider"
                        />
                        <div className="tone-value">
                            Mức độ: <span>{getToneLabel()}</span> ({toneValue}%)
                        </div>
                    </div>
                </div>

                {/* Illustration Options */}
                <div className="settings-section">
                    <div className="section-title">
                        <span>🖼️</span> Hình minh họa
                    </div>
                    <div className="illustration-options">
                        <div
                            className={`illustration-option ${illustrationType === 'none' ? 'active' : ''}`}
                            onClick={() => setIllustrationType('none')}
                        >
                            <div className="radio-circle">
                                <div className="radio-dot"></div>
                            </div>
                            <span className="illustration-icon">❌</span>
                            <div className="illustration-info">
                                <h4>Không có hình</h4>
                                <p>Chỉ hiển thị văn bản</p>
                            </div>
                        </div>
                        <div
                            className={`illustration-option ${illustrationType === 'comic' ? 'active' : ''}`}
                            onClick={() => setIllustrationType('comic')}
                        >
                            <div className="radio-circle">
                                <div className="radio-dot"></div>
                            </div>
                            <span className="illustration-icon">📖</span>
                            <div className="illustration-info">
                                <h4>Truyện tranh</h4>
                                <p>Dễ ghi nhớ, chia sẻ</p>
                            </div>
                        </div>
                        <div
                            className={`illustration-option ${illustrationType === 'poster' ? 'active' : ''}`}
                            onClick={() => setIllustrationType('poster')}
                        >
                            <div className="radio-circle">
                                <div className="radio-dot"></div>
                            </div>
                            <span className="illustration-icon">📢</span>
                            <div className="illustration-info">
                                <h4>Poster tuyên truyền</h4>
                                <p>Giáo dục, nâng cao nhận thức</p>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Chat Area */}
            <main className="main-chat">
                {/* Chat Header */}
                <header className="chat-header">
                    <div className="chat-title">
                        <h2>
                            {character === 'lawyer' ? '👨‍⚖️ Tư vấn cùng Luật sư' : '👤 Trò chuyện thân thiện'}
                        </h2>
                    </div>
                    <div className="chat-status">
                        <span className="status-dot"></span>
                        <span>Sẵn sàng hỗ trợ</span>
                    </div>
                </header>

                {/* Messages or Welcome Screen */}
                {messages.length === 0 ? (
                    <div className="welcome-screen">
                        <div className="welcome-icon">💬</div>
                        <h2>Chào mừng bạn đến với Legal AI!</h2>
                        <p>
                            Hãy đặt câu hỏi về pháp luật, tôi sẽ giải đáp theo phong cách bạn chọn.
                            Bạn có thể thử các câu hỏi gợi ý bên dưới.
                        </p>
                        <div className="suggestion-chips">
                            {getSuggestedQuestions().map((question, index) => (
                                <button
                                    key={index}
                                    className="suggestion-chip"
                                    onClick={() => handleSuggestionClick(question)}
                                >
                                    {question}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div
                        className="messages-container"
                        ref={messagesContainerRef}
                        onScroll={handleContainerScroll}
                    >
                        {/* Điểm đánh dấu đầu trang để scroll tới */}
                        <div ref={messagesTopRef} />

                        {messages.map((message) => (
                            <div key={message.id} className={`message ${message.type}`}>
                                <div className={`message-avatar ${message.type === 'bot' ? message.character : ''}`}>
                                    {message.type === 'user' ? '👤' : (message.character === 'lawyer' ? '👨‍⚖️' : '😊')}
                                </div>
                                <div className="message-content">
                                    <div className="message-bubble">
                                        {message.text.split('\n').map((line, i) => (
                                            <span key={i}>
                                                {line}
                                                {i < message.text.split('\n').length - 1 && <br />}
                                            </span>
                                        ))}
                                    </div>
                                    {message.illustration && (
                                        <div className="message-illustration">
                                            <img src={message.illustration.url} alt={message.illustration.caption} />
                                            <div className="illustration-caption">
                                                {message.illustration.caption}
                                            </div>
                                        </div>
                                    )}
                                    <span className="message-time">{formatTime(message.timestamp)}</span>
                                </div>
                            </div>
                        ))}

                        {/* Typing Indicator */}
                        {isLoading && (
                            <div className="message bot">
                                <div className={`message-avatar ${character}`}>
                                    {character === 'lawyer' ? '👨‍⚖️' : '😊'}
                                </div>
                                <div className="message-content">
                                    <div className="message-bubble">
                                        <div className="typing-indicator">
                                            <div className="typing-dot"></div>
                                            <div className="typing-dot"></div>
                                            <div className="typing-dot"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}

                {/* Chat Input */}
                <div className="chat-input-container">
                    <div className="chat-input-wrapper">
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Nhập câu hỏi của bạn về pháp luật..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={isLoading}
                        />
                        <button
                            className="send-button"
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isLoading}
                        >
                            ➤
                        </button>
                    </div>
                </div>

                {/* Nút Kéo Lên Đầu Trang - hiện khi có tin nhắn và đã cuộn xuống */}
                {messages.length > 0 && showScrollTop && (
                    <button
                        className="scroll-to-top-btn"
                        onClick={scrollToTop}
                        title="Kéo lên đầu trang"
                    >
                        ⬆
                    </button>
                )}
            </main>
        </div>
    )
}

export default App
