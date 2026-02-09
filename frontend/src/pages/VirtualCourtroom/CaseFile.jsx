import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

function CaseFile() {
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [scenario, setScenario] = useState(null)

    const [objective, setObjective] = useState('compensation')
    const [sessionSettings, setSessionSettings] = useState({
        timeLimit: 10,
        objectionLimit: 3,
        pauseEnabled: true
    })

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

    const handleContinue = () => {
        const updatedSession = {
            ...session,
            objective,
            settings: sessionSettings
        }
        sessionStorage.setItem('courtroomSession', JSON.stringify(updatedSession))
        navigate('/courtroom/strategy')
    }

    if (!scenario) {
        return <div className="courtroom-page">Loading...</div>
    }

    return (
        <div className="courtroom-page case-file">
            <header className="page-header">
                <div className="breadcrumb">
                    <span onClick={() => navigate('/courtroom')}>Kịch bản</span>
                    <span> → Chi tiết → Coach → </span>
                    <span>Hồ sơ</span>
                </div>
                <h1>📁 Hồ Sơ Vụ Án</h1>
                <p>{scenario.name}</p>
            </header>

            <section className="facts-section">
                <h2>📋 Các Sự Kiện (Facts)</h2>
                <ul className="facts-list">
                    {scenario.facts?.map((fact, i) => (
                        <li key={i}>
                            <span className="fact-number">{i + 1}</span>
                            <span className="fact-text">{fact}</span>
                        </li>
                    ))}
                </ul>
            </section>

            <section className="objective-section">
                <h2>🎯 Mục Tiêu Của Bạn</h2>
                <div className="objective-options">
                    <label className={`objective-card ${objective === 'compensation' ? 'selected' : ''}`}>
                        <input
                            type="radio"
                            name="objective"
                            value="compensation"
                            checked={objective === 'compensation'}
                            onChange={(e) => setObjective(e.target.value)}
                        />
                        <div className="icon">💰</div>
                        <h3>Nhận bồi thường</h3>
                        <p>Yêu cầu bồi thường thiệt hại đầy đủ</p>
                    </label>

                    <label className={`objective-card ${objective === 'mediation' ? 'selected' : ''}`}>
                        <input
                            type="radio"
                            name="objective"
                            value="mediation"
                            checked={objective === 'mediation'}
                            onChange={(e) => setObjective(e.target.value)}
                        />
                        <div className="icon">🤝</div>
                        <h3>Hòa giải (Win-Win)</h3>
                        <p>Đạt thỏa thuận có lợi cho cả hai bên</p>
                    </label>
                </div>
            </section>

            <section className="settings-section">
                <h2>⚙️ Cài Đặt Phiên</h2>
                <div className="settings-grid">
                    <div className="setting-item">
                        <label>⏱️ Giới hạn thời gian</label>
                        <select
                            value={sessionSettings.timeLimit}
                            onChange={(e) => setSessionSettings(prev => ({
                                ...prev,
                                timeLimit: parseInt(e.target.value)
                            }))}
                        >
                            <option value={5}>5 phút</option>
                            <option value={10}>10 phút</option>
                            <option value={15}>15 phút</option>
                            <option value={20}>20 phút</option>
                        </select>
                    </div>

                    <div className="setting-item">
                        <label>✋ Giới hạn lượt phản đối</label>
                        <select
                            value={sessionSettings.objectionLimit}
                            onChange={(e) => setSessionSettings(prev => ({
                                ...prev,
                                objectionLimit: parseInt(e.target.value)
                            }))}
                        >
                            <option value={2}>2 lượt</option>
                            <option value={3}>3 lượt</option>
                            <option value={5}>5 lượt</option>
                        </select>
                    </div>

                    <div className="setting-item">
                        <label className="checkbox-label">
                            <input
                                type="checkbox"
                                checked={sessionSettings.pauseEnabled}
                                onChange={(e) => setSessionSettings(prev => ({
                                    ...prev,
                                    pauseEnabled: e.target.checked
                                }))}
                            />
                            <span>⏸️ Cho phép tạm dừng 10 giây</span>
                        </label>
                    </div>
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

export default CaseFile
