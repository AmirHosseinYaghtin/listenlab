/** Small formatting + text-direction helpers. */

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

export function formatDurationLong(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '—'
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h} hr ${m} min`
  if (m > 0) return `${m} min ${s} sec`
  return `${s} sec`
}

const PERSIAN_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/

export function containsPersian(text: string): boolean {
  return PERSIAN_RE.test(text)
}

export function textDirection(text: string): 'rtl' | 'ltr' {
  return containsPersian(text) ? 'rtl' : 'ltr'
}

/** Best-effort direction for mixed field values. */
export function directionOf(...values: (string | null | undefined)[]): 'rtl' | 'ltr' {
  for (const v of values) {
    if (v && containsPersian(v)) return 'rtl'
  }
  return 'ltr'
}

export function guessMediaType(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    m4a: 'audio/mp4',
    ogg: 'audio/ogg',
    flac: 'audio/flac',
    srt: 'text/plain',
    vtt: 'text/vtt',
    txt: 'text/plain',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    pdf: 'application/pdf',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp',
    gif: 'image/gif',
  }
  return map[ext] ?? 'application/octet-stream'
}
