import { Loader2, PanelLeftOpen } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ChartModal } from './components/chart/ChartModal'
import { AccountModal } from './components/modals/AccountModal'
import { PopupHost } from './components/modals/Popups'
import { LeaveModal, SavesModal, SettingsModal, ToastHost } from './components/modals/SystemModals'
import { ResearchModal } from './components/research/ResearchParts'
import { StatusBar, Watchlist } from './components/terminal/Chrome'
import { TopBar } from './components/terminal/TopBar'
import { OrderPad } from './components/trade/OrderPad'
import { useGame } from './game/GameContext'
import CareerPage from './pages/CareerPage'
import Dashboard from './pages/Dashboard'
import Markets from './pages/Markets'
import NewsPage from './pages/NewsPage'
import Onboarding from './pages/Onboarding'
import OrdersPage from './pages/OrdersPage'
import PerformancePage from './pages/PerformancePage'
import PortfolioPage from './pages/PortfolioPage'
import ResearchPage from './pages/ResearchPage'
import StockDetail from './pages/StockDetail'
import TeamPage from './pages/TeamPage'

const PAGES = {
  dashboard: Dashboard,
  markets: Markets,
  stock: StockDetail,
  portfolio: PortfolioPage,
  research: ResearchPage,
  trading: OrdersPage,
  orders: OrdersPage,
  news: NewsPage,
  team: TeamPage,
  career: CareerPage,
  performance: PerformancePage,
}

function ModalHost() {
  const { modal } = useGame()
  if (!modal) return null
  switch (modal.kind) {
    case 'research': return <ResearchModal symbol={modal.symbol} />
    case 'leave': return <LeaveModal />
    case 'saves': return <SavesModal />
    case 'settings': return <SettingsModal />
    case 'account': return <AccountModal />
    default: return null
  }
}

function useWide(min: number): boolean {
  const [wide, setWide] = useState(() => window.innerWidth >= min)
  useEffect(() => {
    const h = () => setWide(window.innerWidth >= min)
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [min])
  return wide
}

function Terminal() {
  const { page, ticket, chart } = useGame()
  const wide = useWide(1180)
  const [showList, setShowList] = useState(true)
  const Page = PAGES[page]
  const listVisible = wide ? showList : false
  const [overlayList, setOverlayList] = useState(false)
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <TopBar />
      <div className="relative flex min-h-0 flex-1">
        {listVisible && <Watchlist onClose={() => setShowList(false)} />}
        {!listVisible && (
          <button className="absolute bottom-3 left-3 z-10 flex h-8 items-center gap-1.5 rounded border border-line bg-ink-850 px-2.5 text-xs text-txt-dim shadow-pop hover:text-txt"
            onClick={() => (wide ? setShowList(true) : setOverlayList(true))}>
            <PanelLeftOpen size={14} /> Watchlist
          </button>
        )}
        {!wide && overlayList && (
          <div className="absolute inset-0 z-20 flex" onClick={() => setOverlayList(false)}>
            <div onClick={(e) => e.stopPropagation()} className="h-full shadow-pop"><Watchlist onClose={() => setOverlayList(false)} /></div>
            <div className="flex-1 bg-ink-950/50" />
          </div>
        )}
        <main className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
          <div key={page} className="h-full animate-fadeIn"><Page /></div>
        </main>
      </div>
      <StatusBar />
      {chart && <ChartModal symbol={chart} key={chart} />}
      {ticket && <OrderPad ticket={ticket} key={`${ticket.side}-${ticket.symbol}-${ticket.price}-${ticket.trigger}-${ticket.type}`} />}
      <ModalHost />
      <PopupHost />
    </div>
  )
}

export default function App() {
  const { state, booting } = useGame()
  return (
    <>
      {booting ? (
        <div className="flex h-full items-center justify-center text-txt-mute"><Loader2 className="animate-spin" /></div>
      ) : state ? <Terminal /> : <Onboarding />}
      <ToastHost />
    </>
  )
}
