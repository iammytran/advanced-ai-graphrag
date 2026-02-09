import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

function ScenarioList() {
    const navigate = useNavigate()
    const [selectedId, setSelectedId] = useState(null)

    const getDifficultyStars = (level) => {
        return '⭐'.repeat(level)
    }

    const handleSelect = (scenario) => {
        setSelectedId(scenario.id)
        // Navigate to detail page
        navigate(`/courtroom/scenario/${scenario.id}`)
    }

    return (
        <div className="courtroom-page scenario-list">
            <header className="page-header">
                <h1>🏛️ Chọn Kịch Bản Phiên Tòa</h1>
                <p>Chọn một kịch bản để bắt đầu luyện tập</p>
            </header>

            <div className="scenario-grid">
                {scenarios.map(scenario => (
                    <div
                        key={scenario.id}
                        className={`scenario-card ${selectedId === scenario.id ? 'selected' : ''}`}
                        onClick={() => handleSelect(scenario)}
                    >
                        <div className="scenario-difficulty">
                            <span className="stars">{getDifficultyStars(scenario.difficulty)}</span>
                            <span className="label">{scenario.difficultyLabel}</span>
                        </div>

                        <h3 className="scenario-name">{scenario.name}</h3>

                        <p className="scenario-description">{scenario.description}</p>

                        <div className="scenario-meta">
                            <span className="duration">⏱️ {scenario.duration} phút</span>
                        </div>

                        <div className="scenario-skills">
                            {scenario.skills.map((skill, i) => (
                                <span key={i} className="skill-tag">{skill}</span>
                            ))}
                        </div>

                        <button className="select-btn">Chọn kịch bản này →</button>
                    </div>
                ))}
            </div>

            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate('/')}>
                    ← Quay lại Chatbot
                </button>
            </div>
        </div>
    )
}

export default ScenarioList
