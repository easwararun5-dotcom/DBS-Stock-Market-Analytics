import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockExplorer from './pages/StockExplorer'
import StockDetail from './pages/StockDetail'
import Sectors from './pages/Sectors'
import Portfolio from './pages/Portfolio'
import Watchlist from './pages/Watchlist'
import MLPredictions from './pages/MLPredictions'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/stocks" element={<StockExplorer />} />
        <Route path="/stocks/:ticker" element={<StockDetail />} />
        <Route path="/sectors" element={<Sectors />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/watchlist" element={<Watchlist />} />
        <Route path="/ml" element={<MLPredictions />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
