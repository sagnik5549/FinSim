import clsx from 'clsx'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Avatar } from '../components/common/Avatar'
import { Button } from '../components/common/ui'
import { useGame } from '../game/GameContext'

const CEO_LINES = [
  'Welcome to Apex Capital.',
  "We're giving you control of our investment portfolio.",
  'Your first assignment is simple.',
  'Beat the quarterly target.',
]

const MANDATE: [string, string, string?][] = [
  ['Role', 'Head of Investments'],
  ['Starting capital', '₹100 Cr'],
  ['Quarterly target', '₹112 Cr', 'text-gold'],
  ['Maximum drawdown', '10%', 'text-down'],
  ['Risk profile', 'MEDIUM', 'text-info'],
  ['Time', '90 DAYS'],
]

export default function Onboarding() {
  const { startNewGame, busy } = useGame()
  const [stage, setStage] = useState(0)
  const [lines, setLines] = useState(0)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    if (stage === 0) { const t = setTimeout(() => setStage(1), 2300); return () => clearTimeout(t) }
    if (stage === 1) { const t = setTimeout(() => setStage(2), 2600); return () => clearTimeout(t) }
    if (stage === 2 && lines < CEO_LINES.length) { const t = setTimeout(() => setLines((l) => l + 1), lines === 0 ? 500 : 1100); return () => clearTimeout(t) }
    if (stage === 2 && lines >= CEO_LINES.length) { const t = setTimeout(() => setStage(3), 1200); return () => clearTimeout(t) }
  }, [stage, lines])

  const start = async () => {
    setLeaving(true)
    await startNewGame()
    setLeaving(false)
  }

  return (
    <div className="relative flex h-full items-center justify-center overflow-hidden bg-ink-950">
      <Backdrop />
      {stage < 3 && (
        <button onClick={() => { setStage(3); setLines(CEO_LINES.length) }} className="absolute right-6 top-6 z-10 text-2xs font-bold uppercase tracking-[0.2em] text-txt-mute hover:text-txt">
          Skip intro →
        </button>
      )}

      {stage === 0 && (
        <div className="text-center animate-rise">
          <div className="mx-auto mb-5 h-px w-40 bg-gradient-to-r from-transparent via-gold to-transparent" />
          <h1 className="font-display text-5xl font-bold tracking-[0.35em] text-txt">APEX CAPITAL</h1>
          <div className="mt-3 text-sm uppercase tracking-[0.4em] text-txt-dim">Investment Management Division</div>
          <div className="mx-auto mt-5 h-px w-40 bg-gradient-to-r from-transparent via-gold to-transparent" />
        </div>
      )}

      {stage === 1 && (
        <div className="text-center animate-rise">
          <div className="font-display text-4xl font-semibold text-txt">Congratulations.</div>
          <div className="mt-4 text-lg text-txt-dim">You have been appointed</div>
          <div className="mt-1 font-display text-3xl font-bold tracking-wide text-gold drop-shadow-[0_0_24px_rgba(233,185,73,.35)]">Head of Investments.</div>
        </div>
      )}

      {stage === 2 && (
        <div className="flex max-w-3xl items-center gap-10 animate-fadeIn">
          <div className="relative">
            <div className="absolute inset-0 -z-10 rounded-full bg-gold/20 blur-3xl" />
            <Avatar id="ceo" size={240} />
            <div className="mt-3 text-center">
              <div className="font-display text-lg font-bold">Vikram Sethi</div>
              <div className="text-2xs uppercase tracking-[0.2em] text-txt-mute">Chief Executive Officer</div>
            </div>
          </div>
          <div className="min-w-[340px] space-y-3">
            {CEO_LINES.slice(0, lines).map((l, i) => (
              <div key={i} className={clsx('panel animate-fadeIn rounded-xl rounded-tl-none px-5 py-3 text-lg', i === CEO_LINES.length - 1 && 'border-gold/50 font-semibold text-gold')}>
                “{l}”
              </div>
            ))}
          </div>
        </div>
      )}

      {stage === 3 && (
        <div className={clsx('flex w-full max-w-4xl items-center gap-10 px-6 transition duration-500', leaving ? 'scale-105 opacity-0' : 'animate-fadeIn')}>
          <div className="hidden shrink-0 md:block">
            <Avatar id="ceo" size={180} />
          </div>
          <div className="panel flex-1 overflow-hidden">
            <div className="border-b border-line bg-gradient-to-r from-gold/15 via-transparent px-6 py-4">
              <div className="label tracking-[0.3em]">Apex Capital · Letter of appointment</div>
              <div className="mt-1 font-display text-2xl font-bold">Your mandate</div>
            </div>
            <div className="grid grid-cols-2 gap-px bg-line">
              {MANDATE.map(([k, v, tone]) => (
                <div key={k} className="bg-ink-850 px-6 py-4">
                  <div className="label">{k}</div>
                  <div className={clsx('num mt-1 text-2xl font-bold', tone ?? 'text-txt')}>{v}</div>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between gap-4 px-6 py-5">
              <p className="max-w-sm text-2xs leading-relaxed text-txt-mute">
                A simulation game. Every company, index, price and person is fictional. Not financial advice.
              </p>
              <Button variant="gold" size="lg" onClick={start} disabled={busy} className="min-w-[200px] tracking-[0.2em]">
                {busy ? <Loader2 className="animate-spin" size={18} /> : <>START CAREER <ArrowRight size={18} /></>}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Backdrop() {
  // Faint animated market lines behind the intro
  const paths = Array.from({ length: 6 }, (_, k) => {
    let y = 300 + k * 40
    const pts = Array.from({ length: 60 }, (_, i) => {
      y += Math.sin(i * 0.7 + k) * 9 + Math.cos(i * 0.23 * (k + 1)) * 6
      return `${i * 26},${y}`
    })
    return `M${pts.join(' L')}`
  })
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.12]" viewBox="0 0 1540 700" preserveAspectRatio="none">
      {paths.map((d, i) => (
        <path key={i} d={d} fill="none" stroke={i % 2 ? '#4C8DFF' : '#26D07C'} strokeWidth={1.2}>
          <animateTransform attributeName="transform" type="translate" values={`0 0; -26 ${i % 2 ? 6 : -6}; 0 0`} dur={`${8 + i}s`} repeatCount="indefinite" />
        </path>
      ))}
    </svg>
  )
}
