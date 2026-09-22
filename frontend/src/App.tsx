import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import EditPodcastPage from './pages/EditPodcastPage'
import NewPodcastPage from './pages/NewPodcastPage'
import PlayerPage from './pages/PlayerPage'

/** Remount the player whenever the podcast id changes (fresh state). */
function PlayerRoute() {
  const { id } = useParams()
  return <PlayerPage key={id} />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/podcast/new" element={<NewPodcastPage />} />
          <Route path="/podcast/:id" element={<PlayerRoute />} />
          <Route path="/podcast/:id/edit" element={<EditPodcastPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
