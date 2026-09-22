import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import PodcastCard from '../components/PodcastCard'
import { EmptyState, ErrorBanner, Spinner } from '../components/ui'
import type { PodcastSummary } from '../types'

type State =
  | { loading: true }
  | { loading: false; error: string }
  | { loading: false; podcasts: PodcastSummary[] }

export default function DashboardPage() {
  const [state, setState] = useState<State>({ loading: true })

  useEffect(() => {
    let cancelled = false
    api
      .listPodcasts()
      .then((podcasts) => {
        if (!cancelled) setState({ loading: false, podcasts })
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ loading: false, error: err.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Podcast Library
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Choose a podcast to listen, read the synchronized transcript, and explore
            highlighted vocabulary.
          </p>
        </div>
        <Link to="/podcast/new" className="btn-primary">
          Add Podcast
        </Link>
      </div>

      {state.loading && <Spinner label="Loading podcasts…" />}

      {!state.loading && 'error' in state && (
        <ErrorBanner message={state.error} />
      )}

      {!state.loading && 'podcasts' in state && state.podcasts.length === 0 && (
        <EmptyState
          title="No podcasts yet"
          description="Import your first podcast with its audio, subtitles, and vocabulary spreadsheet."
          action={
            <Link to="/podcast/new" className="btn-primary">
              Add your first podcast
            </Link>
          }
        />
      )}

      {!state.loading && 'podcasts' in state && state.podcasts.length > 0 && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {state.podcasts.map((p) => (
            <PodcastCard key={p.id} podcast={p} />
          ))}
        </div>
      )}
    </div>
  )
}
