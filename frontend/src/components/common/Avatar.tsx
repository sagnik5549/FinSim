import { useId } from 'react'

/**
 * Illustrated vector character portraits. No photographs: every character is a
 * parametric flat illustration (skin, hair, outfit, accessories, accent colour).
 */
type Hair = 'short' | 'side' | 'bob' | 'bun' | 'long' | 'curly' | 'fade' | 'bald' | 'wavy' | 'crop'
interface Look {
  skin: string
  hair: Hair
  hairColor: string
  suit: string
  shirt: string
  tie?: string
  glasses?: boolean
  beard?: boolean
  mustache?: boolean
  necklace?: boolean
  headset?: boolean
  accent: string
}

const LOOKS: Record<string, Look> = {
  ceo: { skin: '#C68B59', hair: 'side', hairColor: '#3B3B40', suit: '#1B2A4A', shirt: '#E8EEF8', tie: '#B3263A', accent: '#E9B949' },
  cfo: { skin: '#D9A273', hair: 'bob', hairColor: '#1E1614', suit: '#2B2F3A', shirt: '#F1E9E2', necklace: true, accent: '#9B7BFF' },
  risk_manager: { skin: '#B97A4E', hair: 'short', hairColor: '#17110E', suit: '#3A4152', shirt: '#E4EAF5', tie: '#2A5DB0', glasses: true, beard: true, accent: '#F5A524' },
  research_director: { skin: '#C99066', hair: 'bun', hairColor: '#20150F', suit: '#1F5A63', shirt: '#EAF4F2', glasses: true, accent: '#4C8DFF' },
  senior_analyst: { skin: '#A86F47', hair: 'curly', hairColor: '#1A120C', suit: '#2C3E5C', shirt: '#DCE6F5', accent: '#38C6E8' },
  trader: { skin: '#8D5A3B', hair: 'fade', hairColor: '#0F0B09', suit: '#E4EAF5', shirt: '#E4EAF5', tie: '#12203A', headset: true, accent: '#26D07C' },
  economist: { skin: '#D6A07A', hair: 'crop', hairColor: '#9AA0AA', suit: '#5B2333', shirt: '#F3E7EA', glasses: true, necklace: true, accent: '#F2728A' },
  compliance: { skin: '#B07550', hair: 'bald', hairColor: '#2A221D', suit: '#232833', shirt: '#E8ECF2', tie: '#4A5568', mustache: true, accent: '#8FA3BF' },
  hr: { skin: '#E0AC7E', hair: 'wavy', hairColor: '#3A2418', suit: '#9A5B3C', shirt: '#FBEFE6', accent: '#FFB38A' },
  analyst: { skin: '#C08257', hair: 'crop', hairColor: '#1C1410', suit: '#2B3A55', shirt: '#E1E8F4', tie: '#355C9E', accent: '#4C8DFF' },
  risk: { skin: '#A56C45', hair: 'short', hairColor: '#120D0A', suit: '#39404E', shirt: '#E6EBF2', tie: '#8A6D1F', glasses: true, accent: '#F5A524' },
}

function hairPath(h: Hair): { back?: string; front: string } {
  switch (h) {
    case 'short':
      return { front: 'M38 50c0-17 10-26 22-26s22 9 22 26c-3-7-8-11-14-12-6 4-16 5-26 2-2 3-3 6-4 10z' }
    case 'side':
      return { front: 'M37 52c-1-18 9-28 23-28 13 0 23 8 23 25-2-6-5-9-9-10-9 1-20-1-28-6-4 4-7 11-9 19z' }
    case 'bob':
      return {
        back: 'M33 50c0-19 12-29 27-29s27 10 27 29v24c-6 4-10 4-12 2V52H45v24c-3 2-7 2-12-2z',
        front: 'M36 54c0-18 10-27 24-27s24 9 24 27c-10-2-20-8-26-16-5 8-12 13-22 16z',
      }
    case 'bun':
      return {
        back: 'M52 16a9 9 0 1 1 16 0 9 9 0 0 1-16 0z',
        front: 'M37 54c0-19 10-28 23-28s23 9 23 28c-2-9-6-15-12-17-8 3-18 3-27 0-4 4-6 10-7 17z',
      }
    case 'long':
      return {
        back: 'M32 54c0-21 12-31 28-31s28 10 28 31v34H32z',
        front: 'M37 55c0-19 10-28 23-28s23 9 23 28c-9-4-17-11-23-19-5 9-13 15-23 19z',
      }
    case 'curly':
      return {
        front:
          'M36 50c-3-6 1-13 6-14 1-7 9-12 16-10 5-5 15-4 18 2 7 0 11 7 9 13 4 4 3 10-1 12-2-6-5-10-9-11-7 3-19 3-27 0-4 3-8 5-12 8z',
      }
    case 'fade':
      return { front: 'M39 48c0-15 9-23 21-23s21 8 21 23c-4-5-10-8-21-8s-17 3-21 8z' }
    case 'bald':
      return { front: 'M37 60c-1-5-1-9 0-12 2 3 3 6 3 12zM83 60c1-5 1-9 0-12-2 3-3 6-3 12z' }
    case 'wavy':
      return {
        back: 'M31 56c0-22 13-33 29-33s29 11 29 33c2 10-2 18-6 24-3-8-5-14-5-22H43c0 8-2 14-5 22-5-6-8-14-7-24z',
        front: 'M36 55c1-18 11-27 24-27 14 0 23 9 24 26-8-2-15-8-19-15-7 8-17 13-29 16z',
      }
    case 'crop':
    default:
      return { front: 'M38 50c0-16 10-25 22-25s22 9 22 25c-5-6-12-9-22-9s-17 3-22 9z' }
  }
}

export function Avatar({ id, size = 64, ring = true, className = '' }: { id: string; size?: number; ring?: boolean; className?: string }) {
  const uid = useId().replace(/:/g, '')
  const look = LOOKS[id] ?? LOOKS.analyst
  const hair = hairPath(look.hair)
  const skinShade = shade(look.skin, -18)
  return (
    <svg viewBox="0 0 120 120" width={size} height={size} className={className} role="img" aria-label={`${id} portrait`}>
      <defs>
        <radialGradient id={`bg${uid}`} cx="50%" cy="35%" r="70%">
          <stop offset="0%" stopColor={look.accent} stopOpacity="0.35" />
          <stop offset="100%" stopColor="#0B111D" stopOpacity="1" />
        </radialGradient>
        <linearGradient id={`suit${uid}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={shade(look.suit, 12)} />
          <stop offset="100%" stopColor={shade(look.suit, -22)} />
        </linearGradient>
        <clipPath id={`clip${uid}`}>
          <circle cx="60" cy="60" r="58" />
        </clipPath>
      </defs>
      <circle cx="60" cy="60" r="58" fill={`url(#bg${uid})`} />
      <g clipPath={`url(#clip${uid})`}>
        {hair.back && <path d={hair.back} fill={look.hairColor} />}
        {/* shoulders / suit */}
        <path d="M14 122c2-22 16-34 34-38l12 10 12-10c18 4 32 16 34 38z" fill={`url(#suit${uid})`} />
        {/* shirt V */}
        <path d="M48 84l12 22 12-22-12 10z" fill={look.shirt} />
        {look.tie && <path d="M57 92h6l2 4-3 18h-4l-3-18z" fill={look.tie} />}
        {look.necklace && <path d="M49 88c5 7 17 7 22 0" stroke="#F4E9D8" strokeWidth="2" fill="none" strokeDasharray="0.1 3.2" strokeLinecap="round" />}
        {/* lapels */}
        <path d="M48 84l-7 6 11 20 8-6zM72 84l7 6-11 20-8-6z" fill={shade(look.suit, -30)} opacity="0.55" />
        {/* neck */}
        <path d="M52 70h16v14c-4 5-12 5-16 0z" fill={skinShade} />
        {/* head */}
        <ellipse cx="60" cy="54" rx="21" ry="24" fill={look.skin} />
        <ellipse cx="39.5" cy="56" rx="3.2" ry="5" fill={skinShade} />
        <ellipse cx="80.5" cy="56" rx="3.2" ry="5" fill={skinShade} />
        {look.beard && <path d="M40 58c2 16 10 22 20 22s18-6 20-22c-4 6-9 8-20 8s-16-2-20-8z" fill={look.hairColor} opacity="0.92" />}
        {/* eyes & brows */}
        <ellipse cx="52" cy="55" rx="2" ry="2.3" fill="#1A1412" />
        <ellipse cx="68" cy="55" rx="2" ry="2.3" fill="#1A1412" />
        <path d="M47 49.5q5-3 10 0M63 49.5q5-3 10 0" stroke={shade(look.hairColor, 10)} strokeWidth="1.8" fill="none" strokeLinecap="round" />
        {/* nose & mouth */}
        <path d="M60 57q-2 6 0 8" stroke={shade(look.skin, -35)} strokeWidth="1.3" fill="none" strokeLinecap="round" />
        {look.mustache ? (
          <path d="M53 68q7-4 14 0q-7 2-14 0z" fill={look.hairColor} />
        ) : (
          <path d="M54 69q6 3.5 12 0" stroke="#7A3A30" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        )}
        {look.glasses && (
          <g stroke="#0E1524" strokeWidth="1.6" fill="rgba(180,210,255,0.10)">
            <rect x="45" y="50" width="12" height="9" rx="3" />
            <rect x="63" y="50" width="12" height="9" rx="3" />
            <path d="M57 54h6" fill="none" />
          </g>
        )}
        <path d={hair.front} fill={look.hairColor} />
        {look.headset && (
          <g>
            <path d="M37 54c0-17 10-27 23-27s23 10 23 27" stroke="#0E1524" strokeWidth="3" fill="none" />
            <rect x="34" y="50" width="6" height="11" rx="2" fill="#0E1524" />
            <rect x="80" y="50" width="6" height="11" rx="2" fill="#0E1524" />
            <path d="M37 60c0 8 6 12 14 12" stroke="#0E1524" strokeWidth="2" fill="none" />
            <circle cx="51" cy="72" r="2" fill={look.accent} />
          </g>
        )}
        {/* rim light */}
        <path d="M78 40c4 5 5 10 4 15" stroke={look.accent} strokeWidth="1.5" opacity="0.5" fill="none" />
      </g>
      {ring && <circle cx="60" cy="60" r="57" fill="none" stroke={look.accent} strokeOpacity="0.55" strokeWidth="2" />}
    </svg>
  )
}

export function accentOf(id: string): string {
  return (LOOKS[id] ?? LOOKS.analyst).accent
}

function shade(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.min(255, Math.max(0, (n >> 16) + amt))
  const g = Math.min(255, Math.max(0, ((n >> 8) & 0xff) + amt))
  const b = Math.min(255, Math.max(0, (n & 0xff) + amt))
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
}
