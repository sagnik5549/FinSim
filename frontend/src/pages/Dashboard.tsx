import clsx from 'clsx'
import { Activity, CalendarDays, Inbox, LineChart, Newspaper, Wallet } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Change, LivePrice, Panel, Segmented } from '../components/common/ui'
import { PriceChart, type Overlay } from '../components/market/PriceChart'
import {
  CalendarList, HoldingsTable, MessagesList, NewsList, OpportunityCards, PortfolioCard, RiskAlertsInline, TimeHint,
} from '../components/terminal/widgets'
import { useGame, useGameState, useLiveValue } from '../game/GameContext'
import { num } from '../game/format'

function ChartHeader({ symbol }: { symbol: string }) {
  const s = useGameState()
  const stock = s.stocks.find((x) => x.symbol === symbol)
  const idx = s.indices.find((x) => x.key === symbol)
  const val = stock?.price ?? idx?.value ?? 0
  const prev = stock?.prev_close ?? idx?.prev_close ?? val
  const live = useLiveValue(symbol, val)
  return (
    <div className="flex items-baseline gap-3">
      <span className="font-display text-base font-bold">{stock ? stock.name : idx?.name}</span>
      <span className="text-2xs text-txt-mute">{stock ? `${stock.symbol} · ${stock.sector}` : 'Simulated index'}</span>
      {stock ? <LivePrice symbol={symbol} value={val} className="text-lg font-bold" /> : <span className="num text-lg font-bold">{num(live, symbol === 'USDINR' ? 4 : 2)}</span>}
      <Change value={prev ? live / prev - 1 : 0} className="text-sm font-semibold" />
    </div>
  )
}

export default function Dashboard() {
  const s = useGameState()
  const { symbol, openSymbol } = useGame()
  const [tf, setTf] = useState<'1h' | '1d'>('1h')
  const [overlays, setOverlays] = useState<Overlay[]>(['sma20'])
  const [newsTab, setNewsTab] = useState<'news' | 'calendar'>('news')
  const tabs = useMemo(() => {
    const base = ['BH50', 'DL30', 'BKX']
    const held = s.holdings.map((h) => h.symbol)
    const all = [...base, ...held]
    if (!all.includes(symbol)) all.push(symbol)
    return all.slice(0, 10)
  }, [s.holdings, symbol])
  const toggle = (o: Overlay) => setOverlays((xs) => (xs.includes(o) ? xs.filter((x) => x !== o) : [...xs, o]))
  const hasDeals = s.opportunities.some((o) => o.status === 'OPEN')

  return (
    <div className="grid h-full min-h-0 grid-cols-12 grid-rows-[minmax(0,1.25fr)_minmax(0,1fr)] gap-2.5 p-2.5">
      <Panel className="col-span-12 xl:col-span-8" icon={<LineChart size={13} />}
        title={<span className="flex items-center gap-1">{tabs.map((t) => (
          <button key={t} onClick={() => openSymbol(t)}
            className={clsx('rounded px-2 py-0.5 text-2xs font-bold tracking-wider transition',
              t === symbol ? 'bg-info-soft text-info' : 'text-txt-mute hover:text-txt')}>{t}</button>
        ))}</span>}
        right={<>
          <TimeHint />
          <div className="hidden gap-1 lg:flex">
            {(['sma20', 'sma50', 'ema20', 'bb'] as Overlay[]).map((o) => (
              <button key={o} onClick={() => toggle(o)} className={clsx('chip !h-5 !px-2 uppercase', overlays.includes(o) && 'chip-on')}>{o}</button>
            ))}
          </div>
          <Segmented value={tf} onChange={setTf} options={[{ value: '1h', label: '1H' }, { value: '1d', label: '1D' }]} />
        </>}
        bodyClass="flex flex-col">
        <div className="px-3 pt-2"><ChartHeader symbol={symbol} /></div>
        <div className="min-h-0 flex-1 px-1 pb-1">
          <PriceChart symbol={symbol} tf={tf} overlays={overlays} limit={tf === '1h' ? 200 : 120} />
        </div>
      </Panel>

      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 xl:col-span-4">
        <PortfolioCard />
        <Panel title={hasDeals ? 'Opportunities' : 'Upcoming'} icon={hasDeals ? <Activity size={13} /> : <CalendarDays size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto">
          <RiskAlertsInline />
          {hasDeals ? <div className="p-3 pt-1"><OpportunityCards /></div> : <CalendarList items={s.calendar} limit={8} />}
        </Panel>
      </div>

      <Panel title="Holdings" icon={<Wallet size={13} />} className="col-span-12 lg:col-span-5" bodyClass="overflow-y-auto"
        right={<span className="num text-2xs text-txt-mute">{s.holdings.length} positions</span>}>
        <HoldingsTable compact />
      </Panel>
      <Panel className="col-span-12 md:col-span-6 lg:col-span-4" bodyClass="overflow-y-auto" icon={<Newspaper size={13} />}
        title={<span className="flex gap-2">
          <button onClick={() => setNewsTab('news')} className={newsTab === 'news' ? 'text-txt' : ''}>News & events</button>
          <span className="text-line">|</span>
          <button onClick={() => setNewsTab('calendar')} className={newsTab === 'calendar' ? 'text-txt' : ''}>Calendar</button>
        </span>}>
        {newsTab === 'news'
          ? <NewsList items={s.news.slice(0, 25)} onPick={(n) => n.symbols[0] && n.symbols.length === 1 && openSymbol(n.symbols[0])} />
          : <CalendarList items={s.calendar} limit={20} />}
      </Panel>
      <Panel title="Messages" icon={<Inbox size={13} />} className="col-span-12 md:col-span-6 lg:col-span-3" bodyClass="overflow-y-auto"
        right={<span className="num text-2xs text-txt-mute">{s.messages.filter((m) => !m.read).length} unread</span>}>
        <MessagesList />
      </Panel>
    </div>
  )
}
