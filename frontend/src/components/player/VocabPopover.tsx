import { X } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { VocabularyEntry } from '../../types'
import { containsPersian } from '../../utils/text'

export interface PopoverState {
  entryId: string
  anchor: HTMLElement
  pinned: boolean
}

const POPOVER_WIDTH = 340
const MARGIN = 12
const ESTIMATED_HEIGHT = 260

function computePosition(anchor: HTMLElement, height: number) {
  const rect = anchor.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  const width = Math.min(POPOVER_WIDTH, vw - MARGIN * 2)

  let top = rect.top - height - 10 // prefer above the term
  if (top < MARGIN) top = rect.bottom + 10
  if (top + height > vh - MARGIN) {
    top = Math.max(MARGIN, vh - height - MARGIN)
  }

  let left = rect.left + rect.width / 2 - width / 2
  left = Math.max(MARGIN, Math.min(left, vw - width - MARGIN))

  return { top, left, width }
}

interface Props {
  entry: VocabularyEntry
  state: PopoverState
  onClose: () => void
  /** true while the pointer is over the card (keeps hover previews alive) */
  onHoverChange: (inside: boolean) => void
}

export default function VocabPopover({ entry, state, onClose, onHoverChange }: Props) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [lang, setLang] = useState<'fa' | 'en'>(entry.persianMeaning ? 'fa' : 'en')
  const [pos, setPos] = useState(() => computePosition(state.anchor, ESTIMATED_HEIGHT))

  const usesTouch =
    typeof window !== 'undefined' && window.matchMedia('(hover: none)').matches

  // re-measure once rendered, and whenever the anchor scrolls/resizes
  useLayoutEffect(() => {
    const update = () => {
      const h = cardRef.current?.offsetHeight ?? ESTIMATED_HEIGHT
      setPos(computePosition(state.anchor, h))
    }
    update()
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
    }
  }, [state.anchor, entry.id])

  // Escape + click-outside close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node
      if (cardRef.current?.contains(target)) return
      if (state.anchor.contains(target)) return
      onClose()
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointerDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointerDown)
    }
  }, [onClose, state.anchor])

  const translation = lang === 'fa' ? entry.persianMeaning : entry.englishMeaning
  const faAvailable = Boolean(entry.persianMeaning)
  const enAvailable = Boolean(entry.englishMeaning)

  const handleEnter = useCallback(() => onHoverChange(true), [onHoverChange])
  const handleLeave = useCallback(() => onHoverChange(false), [onHoverChange])

  const card = (
    <div
      ref={cardRef}
      role="dialog"
      aria-label={`Vocabulary: ${entry.word}`}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      style={
        usesTouch
          ? undefined
          : { top: pos.top, left: pos.left, width: pos.width, position: 'fixed' }
      }
      className={
        usesTouch
          ? 'fixed inset-x-3 bottom-3 z-50 animate-fade-in rounded-xl border border-slate-200 bg-white p-4 shadow-xl sm:inset-x-auto'
          : 'z-50 animate-fade-in rounded-xl border border-slate-200 bg-white p-4 shadow-xl'
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg leading-tight font-bold break-words text-slate-900 ltr-text">
            {entry.word}
          </h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {entry.baseForm &&
              entry.baseForm.toLowerCase() !== entry.word.toLowerCase() && (
                <span className="chip bg-slate-100 text-slate-600 ltr-text">
                  base: {entry.baseForm}
                </span>
              )}
            {entry.partOfSpeech && (
              <span className="chip bg-brand-50 capitalize text-brand-700 ltr-text">
                {entry.partOfSpeech}
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="-mt-1 -mr-1 shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label="Close vocabulary card"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* translation toggle */}
      <div className="mt-3 border-t border-slate-100 pt-3">
        <div
          className="inline-flex rounded-lg bg-slate-100 p-0.5"
          role="group"
          aria-label="Translation language"
        >
          <button
            type="button"
            onClick={() => setLang('fa')}
            disabled={!faAvailable}
            aria-pressed={lang === 'fa'}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
              lang === 'fa' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
            }`}
          >
            فارسی
          </button>
          <button
            type="button"
            onClick={() => setLang('en')}
            disabled={!enAvailable}
            aria-pressed={lang === 'en'}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
              lang === 'en' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
            }`}
          >
            English
          </button>
        </div>

        <div className="mt-2.5">
          <p className="text-[11px] tracking-wide text-slate-400 uppercase">Translation</p>
          {!translation ? (
            <p className="mt-1 text-sm text-slate-400 italic">Not available</p>
          ) : (
            <p
              lang={lang === 'fa' ? 'fa' : 'en'}
              className={`mt-1 text-[15px] leading-7 font-medium text-slate-800 ${
                lang === 'fa' ? 'fa-text' : 'ltr-text'
              }`}
            >
              {translation}
            </p>
          )}
        </div>
      </div>

      {entry.notes && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-[11px] tracking-wide text-slate-400 uppercase">
            Explanation / Notes
          </p>
          <p
            lang={containsPersian(entry.notes) ? 'fa' : 'en'}
            className={`mt-1 text-sm leading-6 text-slate-600 ${
              containsPersian(entry.notes) ? 'fa-text' : 'ltr-text'
            }`}
          >
            {entry.notes}
          </p>
        </div>
      )}

      {entry.example && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-[11px] tracking-wide text-slate-400 uppercase">Example</p>
          <p
            lang={containsPersian(entry.example) ? 'fa' : 'en'}
            className={`mt-1 text-sm leading-6 text-slate-600 italic ${
              containsPersian(entry.example)
                ? 'fa-text border-r-2 border-l-0 pr-3 pl-0'
                : 'ltr-text border-l-2 border-brand-200 pl-3'
            }`}
          >
            {entry.example}
          </p>
        </div>
      )}

      <p className="mt-2.5 text-[11px] text-slate-400">
        {state.pinned
          ? 'Pinned — press Esc or × to close'
          : 'Click the word to pin this card'}
      </p>
    </div>
  )

  return createPortal(card, document.body)
}
