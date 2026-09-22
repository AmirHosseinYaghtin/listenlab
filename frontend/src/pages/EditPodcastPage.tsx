import { Loader2, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { ErrorBanner, Field, FileDropzone, Notice, Spinner } from '../components/ui'
import type {
  AudioUploadResult,
  PodcastDetail,
  SubtitleUploadResult,
  VocabularyPreview,
} from '../types'
import { formatDurationLong } from '../utils/text'

type Load =
  | { loading: true }
  | { loading: false; error: string }
  | { loading: false; podcast: PodcastDetail }

export default function EditPodcastPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [load, setLoad] = useState<Load>({ loading: true })
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [coverUrl, setCoverUrl] = useState<string | null>(null)

  const [newAudio, setNewAudio] = useState<AudioUploadResult | null>(null)
  const [audioBusy, setAudioBusy] = useState(false)
  const [newSubtitles, setNewSubtitles] = useState<SubtitleUploadResult | null>(null)
  const [subtitleBusy, setSubtitleBusy] = useState(false)
  const [newVocab, setNewVocab] = useState<VocabularyPreview | null>(null)
  const [vocabBusy, setVocabBusy] = useState(false)
  const [mapping, setMapping] = useState<Record<string, number | null> | undefined>()
  const [newCover, setNewCover] = useState<{ fileId: string; url: string; name: string } | null>(null)
  const [coverBusy, setCoverBusy] = useState(false)

  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .getPodcast(id)
      .then((podcast) => {
        if (cancelled) return
        setTitle(podcast.title)
        setDescription(podcast.description)
        setCoverUrl(podcast.coverUrl)
        setLoad({ loading: false, podcast })
      })
      .catch((err: Error) => {
        if (!cancelled) setLoad({ loading: false, error: err.message })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  const handleAudio = async (file: File) => {
    setAudioBusy(true)
    setError(null)
    try {
      setNewAudio(await api.uploadAudio(file))
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
      setNewSubtitles(await api.uploadSubtitles(file))
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
      setNewVocab(res)
      setMapping(res.mapping)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Vocabulary upload failed.')
    } finally {
      setVocabBusy(false)
    }
  }

  const handleCover = async (file: File) => {
    setCoverBusy(true)
    setError(null)
    try {
      const res = await api.uploadCover(file)
      setNewCover({ fileId: res.fileId, url: res.url, name: res.originalName })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Cover upload failed.')
    } finally {
      setCoverBusy(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await api.updatePodcast(id, {
        title: title.trim(),
        description: description.trim(),
        audioFileId: newAudio?.fileId,
        subtitleFileId: newSubtitles?.fileId,
        vocabularyFileId: newVocab?.fileId,
        coverFileId: newCover?.fileId,
        vocabularyMapping: newVocab ? mapping : undefined,
      })
      navigate(`/podcast/${id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save changes.')
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this podcast? The original source files are not affected.'))
      return
    setDeleting(true)
    setError(null)
    try {
      await api.deletePodcast(id)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete the podcast.')
      setDeleting(false)
    }
  }

  if (load.loading) return <Spinner label="Loading podcast…" />
  if ('error' in load) return <ErrorBanner message={load.error} />

  const podcast = load.podcast

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Edit Podcast</h1>
        <p className="mt-1 text-sm text-slate-500">
          Update metadata or replace any of the source files.
        </p>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      <div className="card flex flex-col gap-5 p-5 sm:p-6">
        <Field label="Title" htmlFor="edit-title" required>
          <input
            id="edit-title"
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>

        <Field label="Description" htmlFor="edit-desc">
          <textarea
            id="edit-desc"
            className="input min-h-24 resize-y"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>

        <div>
          <span className="label">Cover image</span>
          {newCover ? (
            <FileDropzone
              id="edit-cover"
              label=""
              busy={coverBusy}
              fileName={newCover.name}
              onFile={handleCover}
              onClear={() => setNewCover(null)}
            />
          ) : coverUrl ? (
            <div className="flex items-center gap-4">
              <img
                src={coverUrl}
                alt="Current cover"
                className="size-20 rounded-lg border border-slate-200 object-cover"
              />
              <FileDropzone
                id="edit-cover"
                label="Replace cover image"
                hint="PNG, JPG, WEBP"
                accept="image/png,image/jpeg,image/webp,image/gif"
                busy={coverBusy}
                onFile={handleCover}
              />
            </div>
          ) : (
            <FileDropzone
              id="edit-cover"
              label="Upload cover image"
              hint="Optional — PNG, JPG, WEBP"
              accept="image/png,image/jpeg,image/webp,image/gif"
              busy={coverBusy}
              onFile={handleCover}
            />
          )}
        </div>

        <div>
          <span className="label">Audio file</span>
          <p className="mb-2 text-xs text-slate-500">
            Current:{' '}
            <span className="text-slate-700">
              {podcast.audioName ?? '—'} ({formatDurationLong(podcast.duration)})
            </span>
          </p>
          <FileDropzone
            id="edit-audio"
            label="Replace audio"
            hint="MP3, WAV, M4A, OGG"
            accept=".mp3,.wav,.m4a,.ogg,.flac,audio/*"
            busy={audioBusy}
            fileName={newAudio?.originalName ?? null}
            fileMeta={
              newAudio
                ? `New duration: ${formatDurationLong(newAudio.duration)} — subtitles will be re-synced`
                : null
            }
            onFile={handleAudio}
            onClear={() => setNewAudio(null)}
          />
        </div>

        <div>
          <span className="label">Subtitles / transcript</span>
          <p className="mb-2 text-xs text-slate-500">
            Current: <span className="text-slate-700">{podcast.subtitleName ?? '—'}</span> (
            {podcast.subtitleFormat})
          </p>
          <FileDropzone
            id="edit-subs"
            label="Replace subtitles"
            hint=".srt · .vtt · .txt · .docx · .pdf"
            accept=".srt,.vtt,.txt,.docx,.pdf"
            busy={subtitleBusy}
            fileName={newSubtitles?.originalName ?? null}
            fileMeta={
              newSubtitles
                ? `${newSubtitles.segmentCount} segments detected`
                : null
            }
            onFile={handleSubtitles}
            onClear={() => setNewSubtitles(null)}
          />
        </div>

        <div>
          <span className="label">Vocabulary file</span>
          <p className="mb-2 text-xs text-slate-500">
            Current:{' '}
            <span className="text-slate-700">
              {podcast.vocabularyFileName ?? 'none'} ({podcast.vocabCount} entries)
            </span>
          </p>
          <FileDropzone
            id="edit-vocab"
            label="Replace vocabulary spreadsheet"
            hint=".xlsx — headers are auto-detected"
            accept=".xlsx"
            busy={vocabBusy}
            fileName={newVocab?.originalName ?? null}
            fileMeta={newVocab ? `${newVocab.entryCount} entries will replace the current list` : null}
            onFile={handleVocab}
            onClear={() => {
              setNewVocab(null)
              setMapping(undefined)
            }}
          />
          {newVocab && (
            <div className="mt-3">
              <Notice tone="success">
                {newVocab.entryCount} entries ready — {newVocab.report.duplicates.length}{' '}
                duplicate(s) will be skipped.
              </Notice>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
          <button
            type="button"
            className="btn-danger"
            onClick={handleDelete}
            disabled={deleting || saving}
          >
            {deleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Trash2 className="size-4" aria-hidden />
            )}
            Delete podcast
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate(`/podcast/${id}`)}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSave}
              disabled={saving || !title.trim()}
            >
              {saving ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  Saving…
                </>
              ) : (
                'Save changes'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
