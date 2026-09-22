import { useCallback, useEffect, useRef, useState } from 'react'

export interface AudioEngineState {
  playing: boolean
  currentTime: number
  duration: number
  rate: number
  volume: number
  muted: boolean
  loading: boolean
  error: string | null
  ended: boolean
}

/**
 * Wraps a native <audio> element: keeps state in sync and exposes
 * playback actions. Subtitle sync always reads `currentTime`, so it
 * stays accurate at every playback speed.
 */
export function useAudioEngine() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [state, setState] = useState<AudioEngineState>({
    playing: false,
    currentTime: 0,
    duration: 0,
    rate: 1,
    volume: 0.9,
    muted: false,
    loading: true,
    error: null,
    ended: false,
  })

  const patch = useCallback((partial: Partial<AudioEngineState>) => {
    setState((prev) => ({ ...prev, ...partial }))
  }, [])

  const toggle = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      void audio.play().catch(() => {
        patch({ error: 'Playback was blocked. Press play again.', playing: false })
      })
    } else {
      audio.pause()
    }
  }, [patch])

  const seek = useCallback((time: number) => {
    const audio = audioRef.current
    if (!audio) return
    const duration = audio.duration || Number.POSITIVE_INFINITY
    const clamped = Math.max(0, Math.min(time, duration))
    audio.currentTime = clamped
    patch({ currentTime: clamped, ended: false })
  }, [patch])

  const skip = useCallback(
    (delta: number) => {
      const audio = audioRef.current
      if (!audio) return
      seek(audio.currentTime + delta)
    },
    [seek],
  )

  const setRate = useCallback(
    (rate: number) => {
      const audio = audioRef.current
      if (audio) audio.playbackRate = rate
      patch({ rate })
    },
    [patch],
  )

  const setVolume = useCallback(
    (volume: number) => {
      const audio = audioRef.current
      const v = Math.max(0, Math.min(1, volume))
      if (audio) {
        audio.volume = v
        audio.muted = v === 0
      }
      patch({ volume: v, muted: v === 0 })
    },
    [patch],
  )

  const toggleMute = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    const next = !audio.muted
    audio.muted = next
    patch({ muted: next })
  }, [patch])

  const onLoadedMetadata = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    patch({ duration: audio.duration || 0, loading: false, error: null })
  }, [patch])

  const onTimeUpdate = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    patch({ currentTime: audio.currentTime })
  }, [patch])

  const onPlay = useCallback(() => patch({ playing: true, ended: false }), [patch])
  const onPause = useCallback(() => patch({ playing: false }), [patch])
  const onEnded = useCallback(() => patch({ playing: false, ended: true }), [patch])
  const onWaiting = useCallback(() => patch({ loading: true }), [patch])
  const onPlaying = useCallback(() => patch({ loading: false }), [patch])

  const onError = useCallback(() => {
    patch({
      loading: false,
      playing: false,
      error: 'The audio file could not be loaded. It may be corrupt or in an unsupported format.',
    })
  }, [patch])

  const onRateChange = useCallback(() => {
    const audio = audioRef.current
    if (audio) patch({ rate: audio.playbackRate })
  }, [patch])

  return {
    audioRef,
    state,
    actions: { toggle, seek, skip, setRate, setVolume, toggleMute, patch },
    listeners: {
      onLoadedMetadata,
      onTimeUpdate,
      onPlay,
      onPause,
      onEnded,
      onWaiting,
      onPlaying,
      onError,
      onRateChange,
    },
  }
}

/** Attach global keyboard shortcuts (Space / arrows), ignoring text inputs. */
export function usePlayerShortcuts(
  enabled: boolean,
  handlers: {
    toggle: () => void
    skip: (delta: number) => void
    volume: (delta: number) => void
  },
) {
  const ref = useRef(handlers)
  useEffect(() => {
    ref.current = handlers
  })

  useEffect(() => {
    if (!enabled) return
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return
      }
      const api = ref.current
      switch (e.key) {
        case ' ':
        case 'Spacebar':
          e.preventDefault()
          api.toggle()
          break
        case 'ArrowLeft':
          e.preventDefault()
          api.skip(-5)
          break
        case 'ArrowRight':
          e.preventDefault()
          api.skip(5)
          break
        case 'ArrowUp':
          e.preventDefault()
          api.volume(0.05)
          break
        case 'ArrowDown':
          e.preventDefault()
          api.volume(-0.05)
          break
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled])
}
