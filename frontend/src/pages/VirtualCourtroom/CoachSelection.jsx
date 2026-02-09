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
    const [recapStyle, setRecapStyle] = useState('detailed')

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
                options,
                recapStyle
            }
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/case')
    }

    return (
        <div className="courtroom-page coach-selection">
            <header className="page-header">
                <div className="breadcrumb">
                    <span onClick={() => navigate('/courtroom')}>Kịch bản</span>
                    <span> → Chi tiết → </span>
                    <span>Coach</span>
                </div>
                <h1>🧑‍🏫 Chọn Coach Hỗ Trợ</h1>
                <p>Coach sẽ đưa ra gợi ý và phản hồi trong suốt phiên tòa</p>
            </header>

            <section className="coach-type-section">
                <h2>Loại Coach</h2>
                <div className="coach-options">
                    <div
                        className={`coach-card ${coachType === 'lawyer' ? 'selected' : ''}`}
                        onClick={() => setCoachType('lawyer')}
                    >
                        <div className="coach-icon">👨‍⚖️</div>
                        <h3>Luật sư</h3>
                        <p>Phản hồi chuyên nghiệp, trích dẫn điều luật</p>
                    </div>

                    <div
                        className={`coach-card ${coachType === 'normal' ? 'selected' : ''}`}
                        onClick={() => setCoachType('normal')}
                    >
                        <div className="coach-icon">😊</div>
                        <h3>Người bình thường</h3>
                        <p>Phản hồi thân thiện, dễ hiểu</p>
                    </div>
                </div>
            </section>

            <section className="tone-section">
                <h2>Tone Phản Hồi</h2>
                <div className="tone-slider">
                    <span>🗣️ Đời thường</span>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={toneValue}
                        onChange={(e) => setToneValue(parseInt(e.target.value))}
                    />
                    <span>⚖️ Pháp lý</span>
                </div>
                <div className="tone-value">{toneValue}%</div>
            </section>

            <section className="options-section">
                <h2>Hỗ Trợ Trong Phiên</h2>
                <div className="options-grid">
                    <label className={`option-item ${options.openingSuggestion ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={options.openingSuggestion}
                            onChange={() => handleOptionChange('openingSuggestion')}
                        />
                        <span className="icon">💡</span>
                        <span>Gợi ý câu mở đầu</span>
                    </label>

                    <label className={`option-item ${options.evidenceReminder ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={options.evidenceReminder}
                            onChange={() => handleOptionChange('evidenceReminder')}
                        />
                        <span className="icon">📎</span>
                        <span>Nhắc chứng cứ phù hợp</span>
                    </label>

                    <label className={`option-item ${options.autoObjection ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={options.autoObjection}
                            onChange={() => handleOptionChange('autoObjection')}
                        />
                        <span className="icon">✋</span>
                        <span>Tự động soạn phản đối</span>
                    </label>

                    <label className={`option-item ${options.riskWarning ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={options.riskWarning}
                            onChange={() => handleOptionChange('riskWarning')}
                        />
                        <span className="icon">⚠️</span>
                        <span>Cảnh báo rủi ro pháp lý</span>
                    </label>
                </div>
            </section>

            <section className="recap-section">
                <h2>Phong Cách Recap</h2>
                <div className="recap-options">
                    <label className={recapStyle === 'detailed' ? 'selected' : ''}>
                        <input
                            type="radio"
                            name="recap"
                            value="detailed"
                            checked={recapStyle === 'detailed'}
                            onChange={(e) => setRecapStyle(e.target.value)}
                        />
                        <span>📝 Chi tiết</span>
                    </label>
                    <label className={recapStyle === 'summary' ? 'selected' : ''}>
                        <input
                            type="radio"
                            name="recap"
                            value="summary"
                            checked={recapStyle === 'summary'}
                            onChange={(e) => setRecapStyle(e.target.value)}
                        />
                        <span>📋 Tóm tắt</span>
                    </label>
                    <label className={recapStyle === 'visual' ? 'selected' : ''}>
                        <input
                            type="radio"
                            name="recap"
                            value="visual"
                            checked={recapStyle === 'visual'}
                            onChange={(e) => setRecapStyle(e.target.value)}
                        />
                        <span>🖼️ Hình ảnh</span>
                    </label>
                </div>
            </section>

            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate(-1)}>
                    ← Quay lại
                </button>
                <button className="btn-primary" onClick={handleContinue}>
                    Tiếp tục →
                </button>
            </div>
        </div>
    )
}

export default CoachSelection
