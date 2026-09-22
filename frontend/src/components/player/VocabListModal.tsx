import { BookOpen, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import type { VocabularyEntry } from '../../types'
import { containsPersian } from '../../utils/text'

export default function VocabListModal({
  vocabulary,
  onClose,
}: {
  vocabulary: VocabularyEntry[]
  onClose: () => void
}) {
  const [lang, setLang] = useState<'fa' | 'en'>(
    vocabulary.some((v) => v.persianMeaning) ? 'fa' : 'en',
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const sorted = [...vocabulary].sort((a, b) => a.word.localeCompare(b.word))

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Vocabulary list"
        className="animate-fade-in flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-vocab-100 text-vocab-700">
              <BookOpen className="size-4" aria-hidden />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Vocabulary list</h2>
              <p className="text-xs text-slate-500">{vocabulary.length} entries</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-lg bg-slate-100 p-0.5" role="group" aria-label="Language">
              <button
                type="button"
                onClick={() => setLang('fa')}
                aria-pressed={lang === 'fa'}
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${lang === 'fa' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
              >
                فارسی
              </button>
              <button
                type="button"
                onClick={() => setLang('en')}
                aria-pressed={lang === 'en'}
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${lang === 'en' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
              >
                English
              </button>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close vocabulary list"
              autoFocus
            >
              <X className="size-4.5" />
            </button>
          </div>
        </header>

        <ul className="transcript-scroll divide-y divide-slate-100 overflow-y-auto">
          {sorted.map((entry) => {
            const value =
              lang === 'fa' ? entry.persianMeaning : entry.englishMeaning
            const fa = lang === 'fa'
            return (
              <li key={entry.id} className="px-5 py-3">
                <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                  <span className="text-sm font-semibold text-slate-900 ltr-text">{entry.word}</span>
                  {entry.partOfSpeech && (
                    <span className="chip bg-slate-100 capitalize text-slate-500 ltr-text">
                      {entry.partOfSpeech}
                    </span>
                  )}
                </div>
                {value ? (
                  <p
                    lang={fa ? 'fa' : 'en'}
                    className={`mt-0.5 text-sm text-slate-600 ${fa && containsPersian(value) ? 'fa-text' : 'ltr-text'}`}
                  >
                    {value}
                  </p>
                ) : (
                  <p className="mt-0.5 text-sm text-slate-400 italic">Not available</p>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>,
    document.body,
  )
}
