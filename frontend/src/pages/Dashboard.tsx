import clsx from 'clsx'
import { useState } from 'react'
import { ChartPanel } from '../components/chart/ChartPanel'
import { Panel } from '../components/common/ui'
import { LiveChange, LiveNum } from '../components/market/Quote'
import {
  CalendarList, HoldingsTable, MessagesList, NewsList, OpportunityCards, PortfolioCard, RiskAlertsInline,
} from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { hhmm, int, num } from '../game/format'
import { api } from '../services/api'

function ChartTitle({ symbol }: { symbol: string }) {
  const s = useGameState()
  const stock = s.stocks.find((x) => x.symbol === symbol)
  const idx = s.indices.find((x) => x.key === symbol)
  const val = stock?.price ?? idx?.value ?? 0
  const prev = stock?.prev_close ?? idx?.prev_close ?? val
  return (
    <div className="flex min-w-0 items-baseline gap-2 px-3 pt-2">
      <span className="truncate text-sm font-semibold">{stock ? stock.name : idx?.name}</span>
      <span className="text-2xs text-txt-mute">{stock ? stock.symbol : 'Index'}</span>
      <LiveNum symbol={symbol} value={val} decimals={symbol === 'USDINR' ? 4 : 2} className="text-sm font-semibold" />
      <LiveChange symbol={symbol} value={val} prevClose={prev} className="text-xs" />
    </div>
  )
}

function OpenOrdersMini() {
  const s = useGameState()
  const { run, setPage } = useGame()
  const open = s.orders.filter((o) => o.status === 'OPEN' || o.status === 'TRIGGERED')
  if (!open.length) {
    return <div className="flex h-full min-h-[60px] items-center justify-center px-4 text-center text-xs text-txt-mute">No working orders.</div>
  }
  return (
    <ul>
      {open.slice(0, 12).map((o) => (
        <li key={o.id} className="flex items-center gap-2 border-b border-line/60 px-3 py-1.5 text-xs">
          <span className={o.side === 'BUY' ? 'text-info' : 'text-down'}>{o.side === 'BUY' ? 'B' : 'S'}</span>
          <span className="w-12 font-medium">{o.symbol}</span>
          <span className="text-txt-mute">{o.tag ? o.tag.toLowerCase() : o.type}</span>
          <span className="num">{int(o.qty)}</span>
          <span className="num ml-auto">{o.price !== null ? num(o.price) : `trg ${num(o.trigger ?? 0)}`}</span>
          <button className="text-txt-mute hover:text-down" title="Cancel" onClick={() => run(() => api.cancelOrder(o.id))}>✕</button>
        </li>
      ))}
      {open.length > 12 && <li><button className="w-full py-1.5 text-xs text-info" onClick={() => setPage('orders')}>All {open.length} orders</button></li>}
    </ul>
  )
}

export default function Dashboard() {
  const s = useGameState()
  const { symbol, openSymbol } = useGame()
  const [lower, setLower] = useState<'positions' | 'orders'>('positions')
  const [side, setSide] = useState<'news' | 'calendar' | 'messages'>('news')
  const hasDeals = s.opportunities.some((o) => o.status === 'OPEN')
  const jobs = s.research_jobs
  const openCount = s.orders.filter((o) => o.status === 'OPEN' || o.status === 'TRIGGERED').length
  const unread = s.messages.filter((m) => !m.read).length

  return (
    <div className="h-full overflow-y-auto">
      <div className="grid min-h-full grid-cols-12 gap-2 p-2 xl:h-full xl:grid-rows-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Panel className="col-span-12 h-[440px] xl:col-span-8 xl:h-auto" bodyClass="flex flex-col">
          <ChartTitle symbol={symbol} />
          <div className="min-h-0 flex-1"><ChartPanel symbol={symbol} prefsKey="dash" defaultTf="5m" defaultStudies={['volume']} /></div>
        </Panel>

        <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto md:col-span-6 xl:col-span-4 [&>*:first-child]:shrink-0">
          <PortfolioCard />
          <Panel className="min-h-[150px] flex-1" bodyClass="overflow-y-auto"
            title={hasDeals ? 'Block deal on offer' : 'Coming up'}>
            <RiskAlertsInline />
            {jobs.map((j) => (
              <div key={j.id} className="mx-3 mt-2 rounded border border-line bg-ink-800 px-2.5 py-1.5 text-xs text-txt-dim">
                Research on <b className="font-medium text-txt">{j.symbol}</b> ({j.depth === 'DEEP' ? 'deep dive' : 'quick look'}) due at {hhmm(j.ready_at)}
              </div>
            ))}
            {hasDeals ? <div className="p-3"><OpportunityCards /></div> : <CalendarList items={s.calendar} limit={8} />}
          </Panel>
        </div>

        <Panel className="col-span-12 h-[300px] md:col-span-6 xl:col-span-7 xl:h-auto" bodyClass="overflow-y-auto"
          title={<span className="flex gap-3">
            <button className={lower === 'positions' ? 'text-txt' : 'hover:text-txt'} onClick={() => setLower('positions')}>Positions <span className="num text-txt-mute">{s.holdings.length}</span></button>
            <button className={lower === 'orders' ? 'text-txt' : 'hover:text-txt'} onClick={() => setLower('orders')}>Open orders <span className="num text-txt-mute">{openCount}</span></button>
          </span>}>
          {lower === 'positions' ? <HoldingsTable compact /> : <OpenOrdersMini />}
        </Panel>

        <Panel className="col-span-12 h-[300px] xl:col-span-5 xl:h-auto" bodyClass="overflow-y-auto"
          title={<span className="flex gap-3">
            {(['news', 'calendar', 'messages'] as const).map((t) => (
              <button key={t} className={clsx('capitalize', side === t ? 'text-txt' : 'hover:text-txt')} onClick={() => setSide(t)}>
                {t}{t === 'messages' && unread > 0 && <span className="num ml-1 text-info">{unread}</span>}
              </button>
            ))}
          </span>}>
          {side === 'news' && <NewsList items={s.news.slice(0, 30)} onPick={(n) => n.symbols.length === 1 && openSymbol(n.symbols[0])} />}
          {side === 'calendar' && <CalendarList items={s.calendar} limit={20} />}
          {side === 'messages' && <MessagesList />}
        </Panel>
      </div>
    </div>
  )
}
