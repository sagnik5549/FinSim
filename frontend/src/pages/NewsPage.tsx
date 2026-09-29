import clsx from 'clsx'
import { Activity, CalendarDays, Newspaper } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge, Empty, Panel } from '../components/common/ui'
import { CalendarList, NewsList } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { gameTime } from '../game/format'
import { api } from '../services/api'
import type { NewsItem } from '../types/game'

interface EventsPayload {
  active: { id: string; type: string; category: string; title: string; severity: number; narrative: string; started_at: string; symbols: string[]; sectors: string[]; remaining_hours: number }[]
}

export default function NewsPage() {
  const s = useGameState()
  const { openSymbol } = useGame()
  const [filter, setFilter] = useState<'ALL' | 'COMPANY' | 'MACRO' | 'MARKET' | 'HOLDINGS'>('ALL')
  const [archive, setArchive] = useState<NewsItem[]>([])
  const [events, setEvents] = useState<EventsPayload | null>(null)
  const [selected, setSelected] = useState<NewsItem | null>(null)
  useEffect(() => {
    api.get<NewsItem[]>('/news?limit=150').then(setArchive).catch(() => setArchive([]))
    api.get<EventsPayload>('/events').then(setEvents).catch(() => setEvents(null))
  }, [s.version])
  const held = new Set(s.holdings.map((h) => h.symbol))
  const items = (archive.length ? archive : s.news).filter((n) =>
    filter === 'ALL' ? true : filter === 'HOLDINGS' ? n.symbols.some((x) => held.has(x)) : n.category === filter)

  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-2.5 p-2.5">
      <Panel title="Newswire" icon={<Newspaper size={13} />} className="col-span-12 lg:col-span-6" bodyClass="overflow-y-auto"
        right={<div className="flex gap-1">{(['ALL', 'HOLDINGS', 'COMPANY', 'MACRO', 'MARKET'] as const).map((f) => (
          <button key={f} className={clsx('chip !h-5 !px-2', filter === f && 'chip-on')} onClick={() => setFilter(f)}>{f}</button>
        ))}</div>}>
        <NewsList items={items} onPick={setSelected} />
      </Panel>
      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 lg:col-span-6">
        {selected && (
          <div className="panel animate-fadeIn p-4">
            <div className="flex items-center gap-2"><Badge tone="info">{selected.category}</Badge><span className="num text-2xs text-txt-mute">{gameTime(selected.time)}</span></div>
            <div className="mt-2 font-display text-lg font-bold leading-snug">{selected.headline}</div>
            <p className="mt-2 text-sm leading-relaxed text-txt-dim">{selected.body}</p>
            <div className="mt-2 flex gap-1">{selected.symbols.map((x) => <button key={x} className="chip" onClick={() => openSymbol(x, 'stock')}>{x} →</button>)}</div>
          </div>
        )}
        <Panel title="Active market events" icon={<Activity size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto">
          {!events || events.active.length === 0 ? <Empty>No active events.</Empty> : (
            <ul>{events.active.map((e) => (
              <li key={e.id} className="border-b border-line/60 px-3 py-2 text-xs">
                <div className="flex items-center gap-2">
                  <Badge tone={e.category === 'macro' ? 'violet' : e.category === 'market' ? 'gold' : 'info'}>{e.category}</Badge>
                  <span className="font-semibold">{e.type.replace(/_/g, ' ')}</span>
                  <span className="ml-auto text-2xs text-txt-mute">{e.remaining_hours}h of impact left</span>
                </div>
                <div className="mt-0.5 text-txt-dim">{e.title}</div>
                {e.symbols.length > 0 && <div className="mt-1 flex gap-1">{e.symbols.map((x) => <button key={x} className="chip !h-5" onClick={() => openSymbol(x, 'stock')}>{x}</button>)}</div>}
              </li>
            ))}</ul>
          )}
        </Panel>
        <Panel title="Economic & earnings calendar" icon={<CalendarDays size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto">
          <CalendarList items={s.calendar} limit={30} />
        </Panel>
      </div>
    </div>
  )
}
