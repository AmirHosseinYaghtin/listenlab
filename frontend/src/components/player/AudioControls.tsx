import {
  Loader2,
  Pause,
  Play,
  RotateCcw,
  RotateCw,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from 'lucide-react'
import type { AudioEngineState } from '../../hooks/useAudioEngine'
import { formatTime } from '../../utils/text'

const RATES = [0.75, 1, 1.25, 1.5, 2]

interface Props {
  state: AudioEngineState
  onToggle: () => void
  onSeek: (t: number) => void
  onSkip: (delta: number) => void
  onRate: (rate: number) => void
  onVolume: (v: number) => void
  onToggleMute: () => void
  onPrevSegment: () => void
  onNextSegment: () => void
  hasSegments: boolean
}

export default function AudioControls({
  state,
  onToggle,
  onSeek,
  onSkip,
  onRate,
  onVolume,
  onToggleMute,
  onPrevSegment,
  onNextSegment,
  hasSegments,
}: Props) {
  const { playing, currentTime, duration, rate, volume, muted, loading } = state
  const scrubMax = duration > 0 ? duration : 0

  return (
    <div className="flex flex-col gap-2.5">
      {/* seek bar */}
      <div className="flex items-center gap-3">
        <span className="w-12 shrink-0 text-right font-mono text-xs tabular-nums text-slate-500">
          {formatTime(currentTime)}
        </span>
        <input
          type="range"
          min={0}
          max={scrubMax || 1}
          step={0.1}
          value={currentTime}
          disabled={duration <= 0}
          aria-label="Seek position"
          onChange={(e) => onSeek(Number(e.target.value))}
          className="flex-1"
          style={{
            background: `linear-gradient(to right, var(--color-brand-600) ${
              scrubMax ? (currentTime / scrubMax) * 100 : 0
            }%, var(--color-slate-200, #e2e8f0) 0%)`,
          }}
        />
        <span className="w-12 shrink-0 font-mono text-xs tabular-nums text-slate-400">
          {formatTime(duration)}
        </span>
      </div>

      {/* main controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onSkip(-5)}
            className="btn-ghost px-2.5"
            aria-label="Rewind 5 seconds"
            title="Rewind 5s (←)"
          >
            <RotateCcw className="size-4.5" />
            <span className="text-xs">5s</span>
          </button>

          <button
            type="button"
            onClick={onToggle}
            disabled={duration <= 0 && !playing}
            className="flex size-11 cursor-pointer items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label={playing ? 'Pause' : 'Play'}
            title="Play / Pause (Space)"
          >
            {loading && !playing ? (
              <Loader2 className="size-5 animate-spin" />
            ) : playing ? (
              <Pause className="size-5 fill-current" />
            ) : (
              <Play className="size-5 fill-current translate-x-0.5" />
            )}
          </button>

          <button
            type="button"
            onClick={() => onSkip(5)}
            className="btn-ghost px-2.5"
            aria-label="Forward 5 seconds"
            title="Forward 5s (→)"
          >
            <span className="text-xs">5s</span>
            <RotateCw className="size-4.5" />
          </button>

          <div className="mx-1.5 h-6 w-px bg-slate-200" aria-hidden />

          <button
            type="button"
            onClick={onPrevSegment}
            disabled={!hasSegments}
            className="btn-ghost px-2.5"
            aria-label="Previous transcript line"
            title="Previous line"
          >
            <SkipBack className="size-4" />
          </button>
          <button
            type="button"
            onClick={onNextSegment}
            disabled={!hasSegments}
            className="btn-ghost px-2.5"
            aria-label="Next transcript line"
            title="Next line"
          >
            <SkipForward className="size-4" />
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* speed */}
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="hidden sm:inline">Speed</span>
            <select
              value={rate}
              onChange={(e) => onRate(Number(e.target.value))}
              className="cursor-pointer rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs font-medium text-slate-700 focus:border-brand-500 focus:outline-none"
              aria-label="Playback speed"
            >
              {RATES.map((r) => (
                <option key={r} value={r}>
                  {r}x
                </option>
              ))}
            </select>
          </label>

          {/* volume */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onToggleMute}
              className="btn-ghost px-2"
              aria-label={muted ? 'Unmute' : 'Mute'}
              title={muted ? 'Unmute' : 'Mute'}
            >
              {muted || volume === 0 ? (
                <VolumeX className="size-4" />
              ) : (
                <Volume2 className="size-4" />
              )}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={muted ? 0 : volume}
              onChange={(e) => onVolume(Number(e.target.value))}
              className="w-20"
              aria-label="Volume"
              style={{
                background: `linear-gradient(to right, var(--color-brand-600) ${
                  (muted ? 0 : volume) * 100
                }%, var(--color-slate-200, #e2e8f0) 0%)`,
              }}
            />
          </div>
        </div>
      </div>

      {/* keyboard hints */}
      <p className="hidden text-[11px] text-slate-400 md:block">
        Shortcuts: <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono">Space</kbd> play/pause ·{' '}
        <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono">←</kbd>/
        <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono">→</kbd> ±5s ·{' '}
        <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono">↑</kbd>/
        <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono">↓</kbd> volume ·
        audio element keeps sync at every speed
      </p>
    </div>
  )
}
