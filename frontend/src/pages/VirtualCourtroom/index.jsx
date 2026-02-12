import { Routes, Route } from 'react-router-dom'
import ScenarioList from './ScenarioList'
import ScenarioDetail from './ScenarioDetail'
import CoachSelection from './CoachSelection'
import CaseFile from './CaseFile'
import StrategyBuilder from './StrategyBuilder'
import Courtroom from './Courtroom'
import Results from './Results'
import BadgeCollection from './BadgeCollection'

function VirtualCourtroomRoutes() {
    return (
        <Routes>
            <Route index element={<ScenarioList />} />
            <Route path="scenario/:id" element={<ScenarioDetail />} />
            <Route path="coach" element={<CoachSelection />} />
            <Route path="case" element={<CaseFile />} />
            <Route path="strategy" element={<StrategyBuilder />} />
            <Route path="session" element={<Courtroom />} />
            <Route path="results" element={<Results />} />
            <Route path="badges" element={<BadgeCollection />} />
        </Routes>
    )
}

export default VirtualCourtroomRoutes
