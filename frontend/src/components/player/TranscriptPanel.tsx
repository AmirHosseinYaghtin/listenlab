import { useEffect, useRef } from 'react'
import type { SubtitleSegment, VocabularyEntry } from '../../types'
import { formatTime } from '../../utils/text'

interface SegmentTextProps {
  segment: SubtitleSegment
  vocabById: Map<string, VocabularyEntry>
  activeEntryId: string | null
  onVocabPointerEnter: (entryId: string, el: HTMLElement) => void
  onVocabPointerLeave: (entryId: string, el: HTMLElement) => void
  onVocabClick: (entryId: string, el: HTMLElement) => void
}

function SegmentText({
  segment,
  vocabById,
  activeEntryId,
  onVocabPointerEnter,
  onVocabPointerLeave,
  onVocabClick,
}: SegmentTextProps) {
  return (
    <>
      {segment.parts.map((part, i) => {
        if (!part.v || !vocabById.has(part.v)) {
          return <span key={i}>{part.t}</span>
        }
        const entry = vocabById.get(part.v)!
        return (
          <span
            key={i}
            role="button"
            tabIndex={0}
            aria-label={`Vocabulary ${entry.word}`}
            data-active={activeEntryId === part.v ? 'true' : 'false'}
            className="vocab-term"
            onPointerEnter={(e) => onVocabPointerEnter(part.v!, e.currentTarget)}
            onPointerLeave={(e) => onVocabPointerLeave(part.v!, e.currentTarget)}
            onClick={(e) => {
              e.stopPropagation()
              onVocabClick(part.v!, e.currentTarget)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                e.stopPropagation()
                onVocabClick(part.v!, e.currentTarget)
              }
            }}
          >
            {part.t}
          </span>
        )
      })}
    </>
  )
}

interface TranscriptPanelProps {
  segments: SubtitleSegment[]
  activeIndex: number
  vocabById: Map<string, VocabularyEntry>
  activeEntryId: string | null
  onSeekSegment: (segment: SubtitleSegment) => void
  onVocabPointerEnter: (entryId: string, el: HTMLElement) => void
  onVocabPointerLeave: (entryId: string, el: HTMLElement) => void
  onVocabClick: (entryId: string, el: HTMLElement) => void
}

const USER_SCROLL_LOCK_MS = 3500

export default function TranscriptPanel({
  segments,
  activeIndex,
  vocabById,
  activeEntryId,
  onSeekSegment,
  onVocabPointerEnter,
  onVocabPointerLeave,
  onVocabClick,
}: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const itemRefs = useRef<(HTMLElement | null)[]>([])
  const lastUserScrollAt = useRef(0)

  // mark manual scrolling so we don't fight the reader
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const mark = () => {
      lastUserScrollAt.current = Date.now()
    }
    el.addEventListener('wheel', mark, { passive: true })
    el.addEventListener('touchstart', mark, { passive: true })
    return () => {
      el.removeEventListener('wheel', mark)
      el.removeEventListener('touchstart', mark)
    }
  }, [])

  // keep the refs array in sync with segment count (no render-time mutation)
  useEffect(() => {
    itemRefs.current.length = segments.length
  }, [segments.length])

  // keep the active sentence visible
  useEffect(() => {
    if (activeIndex < 0) return
    if (Date.now() - lastUserScrollAt.current < USER_SCROLL_LOCK_MS) return
    const container = scrollRef.current
    const item = itemRefs.current[activeIndex]
    if (!container || !item) return
    const target =
      item.offsetTop - container.clientHeight / 2 + item.clientHeight / 2
    container.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
  }, [activeIndex])

  const vocabHitCount = new Set(
    segments.flatMap((s) => s.parts.filter((p) => p.v).map((p) => p.v!)),
  ).size

  return (
    <section className="card flex min-h-0 flex-1 flex-col overflow-hidden" aria-label="Transcript">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-3.5">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Transcript</h2>
          <p className="text-xs text-slate-500">
            {segments.length} lines · {vocabHitCount} vocabulary terms highlighted · click a
            line to jump
          </p>
        </div>
        <span className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex">
          <span className="vocab-term pointer-events-none">word</span>
          = vocabulary
        </span>
      </header>

      <div
        ref={scrollRef}
        className="transcript-scroll min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5"
        style={{ scrollBehavior: 'smooth' }}
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-1.5" role="list">
          {segments.map((segment, i) => {
            const active = i === activeIndex
            const passed = i < activeIndex
            return (
              <div
                key={segment.id}
                ref={(el) => {
                  itemRefs.current[i] = el
                }}
                role="listitem"
                aria-current={active ? 'true' : undefined}
                onClick={() => onSeekSegment(segment)}
                className={`group w-full cursor-pointer rounded-lg border px-4 py-3 text-left transition-colors ${
                  active
                    ? 'border-brand-200 bg-brand-50/80 shadow-sm'
                    : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="mb-1 flex items-center gap-2 text-[11px] text-slate-400">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSeekSegment(segment)
                    }}
                    className="rounded font-mono tabular-nums hover:bg-slate-200 hover:text-slate-700"
                    aria-label={`Jump to ${formatTime(segment.startTime)}`}
                  >
                    {formatTime(segment.startTime)}
                  </button>
                  {segment.speaker && (
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-500 group-hover:bg-slate-200">
                      {segment.speaker}
                    </span>
                  )}
                  {active && (
                    <span className="ml-auto flex items-center gap-1 font-medium text-brand-600">
                      <span className="inline-block size-1.5 animate-pulse rounded-full bg-brand-500" />
                      now playing
                    </span>
                  )}
                </div>
                <p
                  className={`text-slate-700 ${
                    active
                      ? 'text-[17px] leading-8 font-medium text-slate-900'
                      : passed
                        ? 'text-[15px] leading-7 text-slate-600'
                        : 'text-[15px] leading-7'
                  }`}
                  lang="en"
                >
                  <SegmentText
                    segment={segment}
                    vocabById={vocabById}
                    activeEntryId={activeEntryId}
                    onVocabPointerEnter={onVocabPointerEnter}
                    onVocabPointerLeave={onVocabPointerLeave}
                    onVocabClick={onVocabClick}
                  />
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
