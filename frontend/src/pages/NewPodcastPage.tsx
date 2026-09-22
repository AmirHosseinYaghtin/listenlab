import {
  Check,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  Headphones,
  Loader2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { ErrorBanner, Field, FileDropzone, Notice } from '../components/ui'
import type { AudioUploadResult, SubtitleUploadResult, VocabularyPreview } from '../types'
import { VOCAB_FIELDS } from '../types'
import { formatDurationLong, formatTime } from '../utils/text'

const STEPS = ['Info', 'Audio', 'Subtitles', 'Vocabulary', 'Review'] as const

interface CoverState {
  fileId: string
  url: string
  name: string
}

export default function NewPodcastPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // step 0 — info
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [cover, setCover] = useState<CoverState | null>(null)
  const [coverBusy, setCoverBusy] = useState(false)

  // step 1 — audio
  const [audio, setAudio] = useState<AudioUploadResult | null>(null)
  const [audioBusy, setAudioBusy] = useState(false)

  // step 2 — subtitles
  const [subtitles, setSubtitles] = useState<SubtitleUploadResult | null>(null)
  const [subtitleBusy, setSubtitleBusy] = useState(false)

  // step 3 — vocabulary
  const [vocab, setVocab] = useState<VocabularyPreview | null>(null)
  const [vocabBusy, setVocabBusy] = useState(false)
  const [mapping, setMapping] = useState<Record<string, number | null> | null>(null)

  // step 4 — save
  const [saving, setSaving] = useState(false)

  const canNext = useMemo(() => {
    switch (step) {
      case 0:
        return title.trim().length > 0
      case 1:
        return audio !== null
      case 2:
        return subtitles !== null
      case 3:
        return true // vocabulary optional
      default:
        return !saving
    }
  }, [step, title, audio, subtitles, saving])

  const handleCover = async (file: File) => {
    setCoverBusy(true)
    setError(null)
    try {
      const res = await api.uploadCover(file)
      setCover({ fileId: res.fileId, url: res.url, name: res.originalName })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Cover upload failed.')
    } finally {
      setCoverBusy(false)
    }
  }

  const handleAudio = async (file: File) => {
    setAudioBusy(true)
    setError(null)
    try {
      const res = await api.uploadAudio(file)
      setAudio(res)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Audio upload failed.')
    } finally {
      setAudioBusy(false)
    }
  }

  const handleSubtitles = async (file: File) => {
    setSubtitleBusy(true)
    setError(null)
    try {
      const res = await api.uploadSubtitles(file)
      setSubtitles(res)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Subtitle upload failed.')
    } finally {
      setSubtitleBusy(false)
    }
  }

  const handleVocab = async (file: File) => {
    setVocabBusy(true)
    setError(null)
    try {
      const res = await api.uploadVocabulary(file)
      setVocab(res)
      setMapping(res.mapping)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Vocabulary upload failed.')
    } finally {
      setVocabBusy(false)
    }
  }

  const remap = async (field: string, col: number | null) => {
    if (!vocab) return
    const next = { ...(mapping ?? vocab.mapping), [field]: col }
    setMapping(next)
    setVocabBusy(true)
    setError(null)
    try {
      const res = await api.vocabularyPreview(vocab.fileId, next)
      setVocab(res)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not re-import with this mapping.')
    } finally {
      setVocabBusy(false)
    }
  }

  const handleSave = async () => {
    if (!audio || !subtitles) return
    setSaving(true)
    setError(null)
    try {
      const podcast = await api.createPodcast({
        title: title.trim(),
        description: description.trim(),
        audioFileId: audio.fileId,
        subtitleFileId: subtitles.fileId,
        vocabularyFileId: vocab?.fileId ?? null,
        coverFileId: cover?.fileId ?? null,
        vocabularyMapping: mapping ?? undefined,
      })
      navigate(`/podcast/${podcast.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the podcast.')
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Add Podcast</h1>
        <p className="mt-1 text-sm text-slate-500">
          Import audio, a transcript/subtitles, and an Excel vocabulary file — no technical
          knowledge needed.
        </p>
      </div>

      {/* stepper */}
      <ol className="mb-6 flex items-center gap-1 sm:gap-2" aria-label="Progress">
        {STEPS.map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-1 sm:gap-2">
            <button
              type="button"
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              className={`flex min-w-0 items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors sm:px-2.5 ${
                i === step
                  ? 'bg-brand-600 text-white'
                  : i < step
                    ? 'bg-brand-50 text-brand-700 hover:bg-brand-100'
                    : 'bg-slate-100 text-slate-400'
              }`}
              aria-current={i === step ? 'step' : undefined}
            >
              {i < step ? <Check className="size-3.5 shrink-0" aria-hidden /> : <span>{i + 1}</span>}
              <span className="hidden truncate sm:inline">{label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <span className="h-px w-3 flex-1 bg-slate-200 sm:w-5" aria-hidden />
            )}
          </li>
        ))}
      </ol>

      {error && <div className="mb-4">{<ErrorBanner message={error} onDismiss={() => setError(null)} />}</div>}

      <div className="card p-5 sm:p-6">
        {/* ---------------- STEP 0: INFO ---------------- */}
        {step === 0 && (
          <div className="flex flex-col gap-5">
            <Field label="Title" htmlFor="title" required hint="Shown on the library card.">
              <input
                id="title"
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. How Large Language Models Work"
                autoFocus
              />
            </Field>
            <Field
              label="Description"
              htmlFor="description"
              hint="Optional short summary for students."
            >
              <textarea
                id="description"
                className="input min-h-24 resize-y"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this episode about?"
              />
            </Field>
            <div>
              <span className="label">Cover image</span>
              <FileDropzone
                id="cover"
                label="Upload a cover image"
                hint="PNG, JPG, WEBP or GIF — optional"
                accept="image/png,image/jpeg,image/webp,image/gif"
                busy={coverBusy}
                fileName={cover?.name ?? null}
                onFile={handleCover}
                onClear={() => setCover(null)}
              />
            </div>
          </div>
        )}

        {/* ---------------- STEP 1: AUDIO ---------------- */}
        {step === 1 && (
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Audio file</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                The podcast recording. Duration is detected automatically.
              </p>
            </div>
            <FileDropzone
              id="audio"
              label="Upload the podcast audio"
              hint="MP3, WAV, M4A, OGG or FLAC"
              accept=".mp3,.wav,.m4a,.ogg,.flac,audio/*"
              busy={audioBusy}
              fileName={audio?.originalName ?? null}
              fileMeta={audio ? `Duration: ${formatDurationLong(audio.duration)} (${formatTime(audio.duration)})` : null}
              onFile={handleAudio}
              onClear={() => setAudio(null)}
            />
          </div>
        )}

        {/* ---------------- STEP 2: SUBTITLES ---------------- */}
        {step === 2 && (
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Subtitles / transcript</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                SRT or VTT subtitles, or a DOCX/PDF/TXT transcript with timestamps like{' '}
                <code className="rounded bg-slate-100 px-1">0:08</code>.
              </p>
            </div>
            <FileDropzone
              id="subtitles"
              label="Upload subtitles or transcript"
              hint=".srt · .vtt · .txt · .docx · .pdf"
              accept=".srt,.vtt,.txt,.docx,.pdf"
              busy={subtitleBusy}
              fileName={subtitles?.originalName ?? null}
              fileMeta={
                subtitles
                  ? `${subtitles.segmentCount} segments detected (${subtitles.format})`
                  : null
              }
              onFile={handleSubtitles}
              onClear={() => setSubtitles(null)}
            />

            {subtitles && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="mb-2 text-xs font-medium text-slate-600">Preview</p>
                <ul className="space-y-1.5">
                  {subtitles.firstSegments.slice(0, 4).map((s, i) => (
                    <li key={i} className="flex gap-3 text-xs" lang="en">
                      <span className="font-mono text-slate-400">{formatTime(s.startTime)}</span>
                      <span className="text-slate-600">{s.text}</span>
                    </li>
                  ))}
                </ul>
                {subtitles.issueCount > 0 && (
                  <div className="mt-3">
                    <Notice tone="warning">
                      {subtitles.issueCount} line(s) needed adjustment while parsing — the rest
                      imported fine.
                      {subtitles.issues.length > 0 && (
                        <ul className="mt-1 list-inside list-disc space-y-0.5 opacity-80">
                          {subtitles.issues.slice(0, 3).map((issue, i) => (
                            <li key={i}>{issue.message}</li>
                          ))}
                        </ul>
                      )}
                    </Notice>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ---------------- STEP 3: VOCABULARY ---------------- */}
        {step === 3 && (
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Vocabulary spreadsheet</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                An Excel (.xlsx) file with words/phrases and meanings. Column names are
                detected automatically — adjust the mapping if needed. You can skip this step.
              </p>
            </div>
            <FileDropzone
              id="vocab"
              label="Upload the vocabulary Excel file"
              hint=".xlsx — headers are auto-detected"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              busy={vocabBusy}
              fileName={vocab?.originalName ?? null}
              fileMeta={vocab ? `${vocab.entryCount} entries ready to import` : null}
              onFile={handleVocab}
              onClear={() => {
                setVocab(null)
                setMapping(null)
              }}
            />

            {vocab && (
              <>
                {/* column mapping */}
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="mb-3 text-xs font-medium text-slate-600">
                    Column mapping — detected from headers
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {VOCAB_FIELDS.map((field) => (
                      <label key={field.name} className="block">
                        <span className="mb-1 block text-xs text-slate-500">
                          {field.label}
                          {field.required && <span className="text-red-500"> *</span>}
                        </span>
                        <select
                          className="input py-1.5 text-xs"
                          value={mapping?.[field.name] ?? ''}
                          onChange={(e) =>
                            remap(field.name, e.target.value === '' ? null : Number(e.target.value))
                          }
                          aria-label={`Column for ${field.label}`}
                        >
                          <option value="">— not mapped —</option>
                          {vocab.headers.map((h, i) => (
                            <option key={i} value={i}>
                              {h || `Column ${i + 1}`}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                </div>

                {/* report */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Stat label="Rows" value={vocab.report.totalRows} />
                  <Stat label="To import" value={vocab.report.imported} tone="success" />
                  <Stat label="Duplicates" value={vocab.report.duplicates.length} />
                  <Stat label="Skipped" value={vocab.report.skippedEmpty + vocab.report.skippedMissingWord} />
                </div>
                {vocab.report.warnings.length > 0 && (
                  <Notice tone="warning">
                    <ul className="list-inside list-disc space-y-0.5">
                      {vocab.report.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </Notice>
                )}

                {/* preview table */}
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500">
                      <tr>
                        <th className="px-3 py-2 font-medium">Word</th>
                        <th className="px-3 py-2 font-medium">POS</th>
                        <th className="px-3 py-2 font-medium">Persian</th>
                        <th className="px-3 py-2 font-medium">English</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {vocab.previewEntries.slice(0, 8).map((e, i) => (
                        <tr key={i}>
                          <td className="px-3 py-2 font-medium text-slate-800 ltr-text">{e.word}</td>
                          <td className="px-3 py-2 text-slate-500 ltr-text">{e.partOfSpeech ?? '—'}</td>
                          <td className="px-3 py-2 text-slate-600 fa-text">{e.persianMeaning ?? '—'}</td>
                          <td className="px-3 py-2 text-slate-600 ltr-text">{e.englishMeaning ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {/* ---------------- STEP 4: REVIEW ---------------- */}
        {step === 4 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-slate-900">Review &amp; save</h2>
            <dl className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              <ReviewRow icon={<Headphones className="size-4" />} label="Title" value={title} />
              <ReviewRow
                icon={<FileText className="size-4" />}
                label="Subtitles"
                value={
                  subtitles
                    ? `${subtitles.originalName} — ${subtitles.segmentCount} segments`
                    : '—'
                }
              />
              <ReviewRow
                icon={<Headphones className="size-4" />}
                label="Audio"
                value={
                  audio
                    ? `${audio.originalName} — ${formatDurationLong(audio.duration)}`
                    : '—'
                }
              />
              <ReviewRow
                icon={<FileSpreadsheet className="size-4" />}
                label="Vocabulary"
                value={vocab ? `${vocab.originalName} — ${vocab.entryCount} entries` : 'None (skipped)'}
              />
              <ReviewRow
                icon={<Check className="size-4" />}
                label="Cover"
                value={cover?.name ?? 'None'}
              />
            </dl>
            {description && (
              <p className="text-sm leading-6 text-slate-600">{description}</p>
            )}
            <Notice tone="info">
              Saving parses the files, matches vocabulary inside the transcript, and adds the
              podcast to your library.
            </Notice>
          </div>
        )}
      </div>

      {/* nav */}
      <div className="mt-5 flex items-center justify-between">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0 || saving}
        >
          <ChevronLeft className="size-4" aria-hidden />
          Back
        </button>

        {step < STEPS.length - 1 ? (
          <button
            type="button"
            className="btn-primary"
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext}
          >
            Next
            <ChevronRight className="size-4" aria-hidden />
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary"
            onClick={handleSave}
            disabled={saving || !audio || !subtitles || !title.trim()}
          >
            {saving ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden />
                Saving…
              </>
            ) : (
              'Save podcast'
            )}
          </button>
        )}
      </div>

      {step > 0 && step < STEPS.length - 1 && (
        <p className="mt-3 text-center text-xs text-slate-400">
          Vocabulary is optional — click Next to skip this step.
        </p>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone?: 'success'
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p
        className={`text-lg font-semibold ${tone === 'success' ? 'text-emerald-600' : 'text-slate-800'}`}
      >
        {value}
      </p>
    </div>
  )
}

function ReviewRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <span className="text-slate-400" aria-hidden>
        {icon}
      </span>
      <dt className="w-24 shrink-0 text-xs font-medium text-slate-500">{label}</dt>
      <dd className="min-w-0 flex-1 truncate text-sm text-slate-800">{value}</dd>
    </div>
  )
}
