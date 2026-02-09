import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { scenarios } from '../../services/courtroomMockApi'

function ScenarioDetail() {
    const navigate = useNavigate()
    const { id } = useParams()
    const scenario = scenarios.find(s => s.id === parseInt(id))

    const [selectedRole, setSelectedRole] = useState(null)

    if (!scenario) {
        return (
            <div className="courtroom-page">
                <h1>Không tìm thấy kịch bản</h1>
                <button onClick={() => navigate('/courtroom')}>← Quay lại</button>
            </div>
        )
    }

    const handleContinue = () => {
        if (!selectedRole) {
            alert('Vui lòng chọn vai trò của bạn')
            return
        }
        // Store in session/state and navigate
        sessionStorage.setItem('courtroomSession', JSON.stringify({
            scenarioId: scenario.id,
            role: selectedRole
        }))
        navigate('/courtroom/coach')
    }

    return (
        <div className="courtroom-page scenario-detail">
            <header className="page-header">
                <div className="breadcrumb">
                    <span onClick={() => navigate('/courtroom')}>Kịch bản</span>
                    <span> → </span>
                    <span>Chi tiết</span>
                </div>
                <h1>{scenario.name}</h1>
                <div className="meta">
                    <span>{'⭐'.repeat(scenario.difficulty)} {scenario.difficultyLabel}</span>
                    <span>⏱️ {scenario.duration} phút</span>
                </div>
            </header>

            <section className="summary-section">
                <h2>📋 Tóm Tắt Kịch Bản</h2>
                <div className="summary-content">
                    {scenario.summary.split('\n').map((line, i) => (
                        <p key={i}>{line}</p>
                    ))}
                </div>
            </section>

            <section className="role-section">
                <h2>👤 Chọn Vai Trò Của Bạn</h2>
                <div className="role-options">
                    <div
                        className={`role-card ${selectedRole === 'defendant' ? 'selected' : ''}`}
                        onClick={() => setSelectedRole('defendant')}
                    >
                        <div className="role-icon">🛡️</div>
                        <h3>Luật sư Bào chữa</h3>
                        <p>Bảo vệ quyền lợi cho bị đơn/bị cáo</p>
                    </div>

                    <div
                        className={`role-card ${selectedRole === 'plaintiff' ? 'selected' : ''}`}
                        onClick={() => setSelectedRole('plaintiff')}
                    >
                        <div className="role-icon">⚔️</div>
                        <h3>Luật sư Nguyên đơn</h3>
                        <p>Bảo vệ quyền lợi cho người bị hại</p>
                    </div>
                </div>
            </section>

            <div className="navigation-buttons">
                <button className="btn-secondary" onClick={() => navigate('/courtroom')}>
                    ← Quay lại
                </button>
                <button className="btn-primary" onClick={handleContinue} disabled={!selectedRole}>
                    Tiếp tục →
                </button>
            </div>
        </div>
    )
}

export default ScenarioDetail
