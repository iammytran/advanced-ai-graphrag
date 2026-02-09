import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import VirtualCourtroomRoutes from './pages/VirtualCourtroom/index.jsx'
import './index.css'
import './styles/courtroom.css'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<App />} />
                <Route path="/courtroom/*" element={<VirtualCourtroomRoutes />} />
            </Routes>
        </BrowserRouter>
    </React.StrictMode>,
)
