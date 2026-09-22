/** Minimal typed API client with friendly error extraction. */

import type {
  AudioUploadResult,
  CoverUploadResult,
  PodcastDetail,
  PodcastSummary,
  SubtitleUploadResult,
  VocabularyEntry,
  VocabularyPreview,
} from '../types'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function extractError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((d: { msg?: string; loc?: unknown[] }) => d.msg ?? JSON.stringify(d))
        .join('; ')
    }
  } catch {
    /* not JSON */
  }
  return `Request failed (${res.status} ${res.statusText})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    throw new ApiError(await extractError(res), res.status)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(path, { method: 'POST', body: form })
  if (!res.ok) throw new ApiError(await extractError(res), res.status)
  return (await res.json()) as T
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),

  listPodcasts: () => request<PodcastSummary[]>('/api/podcasts'),

  getPodcast: (id: string) => request<PodcastDetail>(`/api/podcasts/${id}`),

  createPodcast: (payload: {
    title: string
    description?: string
    audioFileId: string
    subtitleFileId: string
    vocabularyFileId?: string | null
    coverFileId?: string | null
    vocabularyMapping?: Record<string, number | null>
  }) =>
    request<PodcastDetail>('/api/podcasts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  updatePodcast: (
    id: string,
    payload: {
      title?: string
      description?: string
      audioFileId?: string
      subtitleFileId?: string
      vocabularyFileId?: string
      coverFileId?: string
      vocabularyMapping?: Record<string, number | null>
    },
  ) =>
    request<PodcastDetail>(`/api/podcasts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  deletePodcast: (id: string) =>
    request<void>(`/api/podcasts/${id}`, { method: 'DELETE' }),

  vocabulary: (id: string) =>
    request<VocabularyEntry[]>(`/api/podcasts/${id}/vocabulary`),

  uploadAudio: (file: File) => upload<AudioUploadResult>('/api/uploads/audio', file),

  uploadSubtitles: (file: File) =>
    upload<SubtitleUploadResult>('/api/uploads/subtitles', file),

  uploadVocabulary: (file: File) =>
    upload<VocabularyPreview>('/api/uploads/vocabulary', file),

  uploadCover: (file: File) => upload<CoverUploadResult>('/api/uploads/cover', file),

  vocabularyPreview: (fileId: string, mapping?: Record<string, number | null>) =>
    request<VocabularyPreview>('/api/podcasts/vocabulary-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileId, mapping }),
    }),
}
