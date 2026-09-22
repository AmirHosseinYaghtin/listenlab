/** Shared API types mirroring the backend responses. */

export interface PodcastSummary {
  id: string
  sourceKey: string | null
  title: string
  description: string
  duration: number
  segmentCount: number
  vocabCount: number
  subtitleFormat: string
  hasVocabularyFile: boolean
  coverUrl: string | null
  audioName: string | null
  createdAt: string
  updatedAt: string
}

export interface VocabularyEntry {
  id: string
  word: string
  baseForm: string | null
  persianMeaning: string | null
  englishMeaning: string | null
  partOfSpeech: string | null
  notes: string | null
  example: string | null
  rowNumber: number | null
}

/** A piece of transcript text; `v` is the vocabulary entry id when highlighted. */
export interface SegmentPart {
  t: string
  v?: string
}

export interface SubtitleSegment {
  id: string
  index: number
  startTime: number
  endTime: number
  text: string
  speaker: string | null
  parts: SegmentPart[]
}

export interface PodcastDetail extends PodcastSummary {
  audioUrl: string
  subtitleName: string | null
  vocabularyFileName: string | null
  segments: SubtitleSegment[]
  vocabulary: VocabularyEntry[]
}

export interface AudioUploadResult {
  fileId: string
  originalName: string
  duration: number
  sizeBytes: number
}

export interface SubtitleUploadResult {
  fileId: string
  originalName: string
  format: string
  segmentCount: number
  firstSegments: Omit<SubtitleSegment, 'parts' | 'id'>[]
  lastSegments: Omit<SubtitleSegment, 'parts' | 'id'>[]
  issues: { line: number; message: string }[]
  issueCount: number
}

export interface VocabularyReport {
  totalRows: number
  imported: number
  skippedEmpty: number
  skippedMissingWord: number
  duplicates: { word: string; firstRow: number; duplicateRow: number }[]
  warnings: string[]
}

export type FieldName =
  | 'word'
  | 'baseForm'
  | 'persianMeaning'
  | 'englishMeaning'
  | 'partOfSpeech'
  | 'notes'
  | 'example'

export const VOCAB_FIELDS: { name: FieldName; label: string; required?: boolean }[] = [
  { name: 'word', label: 'Word / Phrase', required: true },
  { name: 'baseForm', label: 'Base Form' },
  { name: 'persianMeaning', label: 'Persian Meaning' },
  { name: 'englishMeaning', label: 'English Meaning' },
  { name: 'partOfSpeech', label: 'Part of Speech' },
  { name: 'notes', label: 'Notes / Explanation' },
  { name: 'example', label: 'Example' },
]

export interface VocabularyPreview {
  fileId: string
  originalName: string
  headers: string[]
  mapping: Record<string, number | null>
  sheetName: string
  previewEntries: Omit<VocabularyEntry, 'id' | 'rowNumber'>[] & { rowNumber?: number }[]
  entryCount: number
  report: VocabularyReport
}

export interface CoverUploadResult {
  fileId: string
  originalName: string
  url: string
}
