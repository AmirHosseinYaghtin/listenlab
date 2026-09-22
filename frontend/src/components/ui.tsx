import { Loader2, Upload, X } from 'lucide-react'
import { useRef, useState, type DragEvent, type ReactNode } from 'react'

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string
  onDismiss?: () => void
}) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      <p>{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded p-1 hover:bg-red-100"
          aria-label="Dismiss error"
        >
          <X className="size-4" />
        </button>
      )}
    </div>
  )
}

export function Notice({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'success' | 'warning'
  children: ReactNode
}) {
  const tones = {
    info: 'border-brand-200 bg-brand-50 text-brand-800',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    warning: 'border-amber-200 bg-amber-50 text-amber-800',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="card mx-auto max-w-md px-6 py-12 text-center">
      <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
        <Upload className="size-6" aria-hidden />
      </div>
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-1.5 text-sm text-slate-500">{description}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  )
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  required,
}: {
  label: string
  htmlFor: string
  hint?: string
  error?: string
  children: ReactNode
  required?: boolean
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="label">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

interface DropzoneProps {
  label: string
  hint?: string
  accept?: string
  busy?: boolean
  fileName?: string | null
  fileMeta?: string | null
  onFile: (file: File) => void
  onClear?: () => void
  id: string
}

export function FileDropzone({
  label,
  hint,
  accept,
  busy,
  fileName,
  fileMeta,
  onFile,
  onClear,
  id,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) onFile(file)
  }

  if (fileName) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-emerald-900">{fileName}</p>
          {fileMeta && <p className="text-xs text-emerald-700">{fileMeta}</p>}
        </div>
        {onClear && (
          <button type="button" onClick={onClear} className="btn-ghost shrink-0 text-emerald-700">
            Replace
          </button>
        )}
      </div>
    )
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        dragOver ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-white'
      }`}
    >
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <Upload className="size-5" aria-hidden />
      </div>
      <p className="text-sm font-medium text-slate-700">{label}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      <button
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="btn-secondary mt-4"
      >
        {busy ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden /> Uploading…
          </>
        ) : (
          'Choose file'
        )}
      </button>
      <p className="mt-2 text-xs text-slate-400">or drag &amp; drop here</p>
    </div>
  )
}
