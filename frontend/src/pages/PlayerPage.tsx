import { BookOpen, Captions, Clock, ListChecks, Pencil } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAudioEngine, usePlayerShortcuts } from '../hooks/useAudioEngine'
import AudioControls from '../components/player/AudioControls'
import TranscriptPanel from '../components/player/TranscriptPanel'
import VocabListModal from '../components/player/VocabListModal'
import VocabPopover, { type PopoverState } from '../components/player/VocabPopover'
import { ErrorBanner, Spinner } from '../components/ui'
import type { PodcastDetail, SubtitleSegment, VocabularyEntry } from '../types'
import { formatDurationLong } from '../utils/text'

type LoadState =
  | { loading: true }
  | { loading: false; error: string }
  | { loading: false; podcast: PodcastDetail }

/** Index of the last segment that has started at time `t` (-1 before the first). */
function findActiveIndex(segments: SubtitleSegment[], t: number): number {
  let lo = 0
  let hi = segments.length - 1
  let ans = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (segments[mid].startTime <= t) {
      ans = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return ans
}

const HOVER_OPEN_MS = 140
const HOVER_CLOSE_MS = 280

export default function PlayerPage() {
  const { id = '' } = useParams()
  const [load, setLoad] = useState<LoadState>({ loading: true })
  const [popover, setPopover] = useState<PopoverState | null>(null)
  const [showList, setShowList] = useState(false)
  const hoverTimer = useRef<number | null>(null)
  const leaveTimer = useRef<number | null>(null)
  const pointerOverCard = useRef(false)

  const { audioRef, state, actions, listeners } = useAudioEngine()

  useEffect(() => {
    let cancelled = false
    api
      .getPodcast(id)
      .then((podcast) => {
        if (!cancelled) setLoad({ loading: false, podcast })
      })
      .catch((err: Error) => {
        if (!cancelled) setLoad({ loading: false, error: err.message })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  const podcast = !load.loading && 'podcast' in load ? load.podcast : null
  const segments = useMemo(() => podcast?.segments ?? [], [podcast])

  const vocabById = useMemo(() => {
    const map = new Map<string, VocabularyEntry>()
    podcast?.vocabulary.forEach((v) => map.set(v.id, v))
    return map
  }, [podcast])

  const activeIndex = useMemo(
    () => findActiveIndex(segments, state.currentTime),
    [segments, state.currentTime],
  )

  const activeSegment = activeIndex >= 0 ? segments[activeIndex] : null

  const seekToSegment = useCallback(
    (segment: SubtitleSegment) => {
      actions.seek(segment.startTime)
    },
    [actions],
  )

  const prevSegment = useCallback(() => {
    if (activeIndex <= 0) return
    const current = segments[activeIndex]
    // classic player UX: restart current line if we are well into it
    if (current && state.currentTime - current.startTime > 1.5) {
      actions.seek(current.startTime)
    } else {
      actions.seek(segments[activeIndex - 1].startTime)
    }
  }, [activeIndex, segments, state.currentTime, actions])

  const nextSegment = useCallback(() => {
    if (activeIndex < 0) return
    const next = segments[activeIndex + 1]
    if (next) actions.seek(next.startTime)
    else actions.seek(state.duration)
  }, [activeIndex, segments, state.duration, actions])

  usePlayerShortcuts(Boolean(podcast), {
    toggle: actions.toggle,
    skip: actions.skip,
    volume: (d) => actions.setVolume(state.volume + d),
  })

  useEffect(() => {
    const audio = audioRef.current
    if (audio && Number.isFinite(state.volume)) {
      audio.volume = state.volume
      audio.playbackRate = state.rate
    }
  }, [audioRef, state.volume, state.rate, podcast])

  // ----- vocabulary hover / click interaction -----
  const clearHoverTimer = () => {
    if (hoverTimer.current) window.clearTimeout(hoverTimer.current)
    hoverTimer.current = null
  }

  const scheduleClose = useCallback(() => {
    if (leaveTimer.current) window.clearTimeout(leaveTimer.current)
    leaveTimer.current = window.setTimeout(() => {
      if (pointerOverCard.current) return
      setPopover((prev) => (prev && !prev.pinned ? null : prev))
    }, HOVER_CLOSE_MS)
  }, [])

  const cancelClose = useCallback(() => {
    if (leaveTimer.current) {
      window.clearTimeout(leaveTimer.current)
      leaveTimer.current = null
    }
  }, [])

  const openPopover = useCallback(
    (entryId: string, el: HTMLElement, pinned: boolean) => {
      clearHoverTimer()
      cancelClose()
      setPopover({ entryId, anchor: el, pinned })
    },
    [cancelClose],
  )

  const onVocabPointerEnter = useCallback(
    (entryId: string, el: HTMLElement) => {
      clearHoverTimer()
      cancelClose()
      if (window.matchMedia('(hover: none)').matches) return
      hoverTimer.current = window.setTimeout(() => {
        setPopover((prev) => {
          if (prev?.pinned && prev.entryId !== entryId) return prev // pinned card wins
          if (prev?.entryId === entryId) return { ...prev, anchor: el }
          return { entryId, anchor: el, pinned: false }
        })
      }, HOVER_OPEN_MS)
    },
    [cancelClose],
  )

  const onVocabPointerLeave = useCallback(() => {
    clearHoverTimer()
    scheduleClose()
  }, [scheduleClose])

  const onVocabClick = useCallback(
    (entryId: string, el: HTMLElement) => {
      openPopover(entryId, el, true)
    },
    [openPopover],
  )

  const closePopover = useCallback(() => {
    clearHoverTimer()
    cancelClose()
    pointerOverCard.current = false
    setPopover(null)
  }, [cancelClose])

  const onPopoverHover = useCallback(
    (inside: boolean) => {
      pointerOverCard.current = inside
      if (inside) cancelClose()
      else scheduleClose()
    },
    [cancelClose, scheduleClose],
  )

  useEffect(
    () => () => {
      clearHoverTimer()
      if (leaveTimer.current) window.clearTimeout(leaveTimer.current)
    },
    [],
  )

  if (load.loading) return <Spinner label="Loading podcast…" />
  if ('error' in load) return <ErrorBanner message={load.error} />
  if (!podcast) return null

  const popoverEntry = popover ? vocabById.get(popover.entryId) : null

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col gap-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Link to="/" className="hover:text-brand-600">
              Library
            </Link>
            <span aria-hidden>/</span>
            <span className="truncate">{podcast.title}</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
            {podcast.title}
          </h1>
          {podcast.description && (
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              {podcast.description}
            </p>
          )}
          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3.5" aria-hidden />
              {formatDurationLong(podcast.duration)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Captions className="size-3.5" aria-hidden />
              {podcast.segmentCount} lines
            </span>
            <span className="inline-flex items-center gap-1.5">
              <BookOpen className="size-3.5" aria-hidden />
              {podcast.vocabCount} vocabulary items
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button type="button" className="btn-secondary" onClick={() => setShowList(true)}>
            <ListChecks className="size-4" aria-hidden />
            Vocabulary
          </button>
          <Link to={`/podcast/${podcast.id}/edit`} className="btn-ghost">
            <Pencil className="size-4" aria-hidden />
            Edit
          </Link>
        </div>
      </div>

      {state.error && (
        <ErrorBanner message={state.error} onDismiss={() => actions.patch({ error: null })} />
      )}

      {/* player card */}
      <section className="card p-4 sm:p-5" aria-label="Podcast player">
        <div className="flex min-w-0 items-center gap-4">
          <div className="hidden size-20 shrink-0 overflow-hidden rounded-lg bg-slate-100 sm:block">
            {podcast.coverUrl ? (
              <img src={podcast.coverUrl} alt="" className="size-full object-cover" />
            ) : (
              <div className="flex size-full items-center justify-center bg-gradient-to-br from-brand-700 to-slate-800 text-lg font-bold text-white/90">
                {podcast.title.charAt(0)}
              </div>
            )}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-800">{podcast.title}</p>
            <p className="mt-0.5 truncate text-xs text-slate-500">
              {activeSegment ? `Line ${activeIndex + 1} of ${segments.length}` : 'Press play to start'}
            </p>
            {activeSegment && (
              <p className="mt-1.5 line-clamp-2 text-sm leading-6 text-slate-600" lang="en">
                {activeSegment.text}
              </p>
            )}
          </div>
        </div>

        <div className="mt-4">
          <AudioControls
            state={state}
            onToggle={actions.toggle}
            onSeek={actions.seek}
            onSkip={actions.skip}
            onRate={actions.setRate}
            onVolume={actions.setVolume}
            onToggleMute={actions.toggleMute}
            onPrevSegment={prevSegment}
            onNextSegment={nextSegment}
            hasSegments={segments.length > 0}
          />
        </div>

        {/* native audio element — sync source of truth */}
        <audio
          ref={audioRef}
          src={podcast.audioUrl ?? undefined}
          preload="metadata"
          className="hidden"
          {...listeners}
        />
      </section>

      {/* transcript */}
      <div className="flex min-h-[55vh] flex-1 flex-col lg:min-h-[60vh]">
        <TranscriptPanel
          segments={segments}
          activeIndex={activeIndex}
          vocabById={vocabById}
          activeEntryId={popover?.entryId ?? null}
          onSeekSegment={seekToSegment}
          onVocabPointerEnter={onVocabPointerEnter}
          onVocabPointerLeave={onVocabPointerLeave}
          onVocabClick={onVocabClick}
        />
      </div>

      {popoverEntry && popover && (
        <VocabPopover
          key={popover.entryId}
          entry={popoverEntry}
          state={popover}
          onClose={closePopover}
          onHoverChange={onPopoverHover}
        />
      )}

      {showList && (
        <VocabListModal vocabulary={podcast.vocabulary} onClose={() => setShowList(false)} />
      )}
    </div>
  )
}
