import { BookOpen, Clock, Captions, Headphones, Play } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { PodcastSummary } from '../types'
import { formatDurationLong } from '../utils/text'

export default function PodcastCard({ podcast }: { podcast: PodcastSummary }) {
  return (
    <article className="card group flex flex-col overflow-hidden transition-shadow hover:shadow-md">
      <Link
        to={`/podcast/${podcast.id}`}
        className="relative block aspect-[16/9] overflow-hidden bg-slate-100"
        aria-label={`Open ${podcast.title}`}
      >
        {podcast.coverUrl ? (
          <img
            src={podcast.coverUrl}
            alt=""
            className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex size-full items-center justify-center bg-gradient-to-br from-brand-700 via-brand-600 to-slate-800">
            <Headphones className="size-10 text-white/80" aria-hidden />
          </div>
        )}
        <span className="absolute right-3 bottom-3 flex items-center gap-1.5 rounded-md bg-black/70 px-2 py-1 text-xs font-medium text-white">
          <Play className="size-3 fill-current" aria-hidden />
          Start Listening
        </span>
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <h2 className="line-clamp-2 text-[15px] leading-snug font-semibold text-slate-900">
          <Link to={`/podcast/${podcast.id}`} className="hover:text-brand-700">
            {podcast.title}
          </Link>
        </h2>
        {podcast.description && (
          <p className="mt-1.5 line-clamp-2 text-sm text-slate-500">{podcast.description}</p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <Clock className="size-3.5" aria-hidden />
            {formatDurationLong(podcast.duration)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BookOpen className="size-3.5" aria-hidden />
            {podcast.vocabCount} words
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Captions className="size-3.5" aria-hidden />
            {podcast.segmentCount} lines
          </span>
        </div>

        <div className="mt-4 flex-1" />
        <Link to={`/podcast/${podcast.id}`} className="btn-primary w-full">
          <Play className="size-4 fill-current" aria-hidden />
          Start Listening
        </Link>
      </div>
    </article>
  )
}
