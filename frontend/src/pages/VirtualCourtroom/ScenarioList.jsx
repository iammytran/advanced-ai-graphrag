import { useNavigate } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

const difficultyMap = {
    1: { class: 'easy', label: 'Dễ' },
    2: { class: 'medium', label: 'Trung bình' },
    3: { class: 'hard', label: 'Khó' }
}

function ScenarioList() {
    const navigate = useNavigate()

    const handleSelect = (scenario) => {
        navigate(`/courtroom/scenario/${scenario.id}`)
    }

    return (
        <div className="vc-page">
            {/* Top nav bar */}
            <nav className="vc-topnav">
                <button className="vc-btn-back" onClick={() => navigate('/')}>
                    ← Quay lại Chatbot
                </button>
                <button className="vc-btn-back" onClick={() => navigate('/courtroom/badges')}>
                    🏅 Huy hiệu
                </button>
            </nav>

            {/* Landing header */}
            <header className="vc-landing-header">
                <div className="vc-landing-badge">Phòng tập luyện</div>
                <h1>Phiên Tòa Giả Định</h1>
                <p>Chọn một kịch bản để rèn luyện kỹ năng tranh tụng</p>
            </header>

            {/* Scenario grid */}
            <div className="vc-scenario-grid">
                {scenarios.map((scenario, idx) => {
                    const diff = difficultyMap[scenario.difficulty] || difficultyMap[1]
                    return (
                        <div
                            key={scenario.id}
                            className="vc-scenario-card"
                            style={{ animationDelay: `${0.08 + idx * 0.1}s` }}
                            onClick={() => handleSelect(scenario)}
                        >
                            <div className={`vc-sc-accent vc-sc-accent--${diff.class}`} />
                            <div className="vc-sc-body">
                                <div className="vc-sc-top">
                                    <span className={`vc-sc-difficulty vc-sc-difficulty--${diff.class}`}>
                                        {diff.label}
                                    </span>
                                    <span className="vc-sc-duration">⏱️ {scenario.duration} phút</span>
                                </div>

                                <div className="vc-sc-name">{scenario.name}</div>
                                <div className="vc-sc-desc">{scenario.description}</div>

                                <div className="vc-sc-skills">
                                    {scenario.skills.map((skill, i) => (
                                        <span key={i} className="vc-sc-skill">{skill}</span>
                                    ))}
                                </div>

                                <button className="vc-sc-action">
                                    Bắt đầu luyện tập →
                                </button>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default ScenarioList
