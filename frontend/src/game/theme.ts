// Light / dark theme. Colours live in CSS variables (src/index.css); charts read them here.

export type Theme = 'dark' | 'light'
const KEY = 'ibm.theme'
const listeners = new Set<() => void>()

export function getTheme(): Theme {
  try {
    return localStorage.getItem(KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function applyTheme(t: Theme = getTheme()): void {
  document.documentElement.dataset.theme = t
  const meta = document.querySelector('meta[name="theme-color"]')
  meta?.setAttribute('content', t === 'light' ? '#ffffff' : '#0d0f13')
}

export function setTheme(t: Theme): void {
  try {
    localStorage.setItem(KEY, t)
  } catch {
    /* storage unavailable */
  }
  applyTheme(t)
  listeners.forEach((fn) => fn())
}

export function onThemeChange(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

/** A theme colour as an rgba() string, e.g. color('up', 0.4). */
export function color(name: string, alpha = 1): string {
  if (typeof document === 'undefined') return `rgba(128,128,128,${alpha})`
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()
  const [r, g, b] = raw.split(/\s+/).map(Number)
  if ([r, g, b].some((x) => Number.isNaN(x))) return `rgba(128,128,128,${alpha})`
  return `rgba(${r},${g},${b},${alpha})`
}
