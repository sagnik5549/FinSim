import { Loader2 } from 'lucide-react'
import { ExecutedModal, TradeTicket } from './components/modals/TradeTicket'
import { PopupHost } from './components/modals/Popups'
import { LeaveModal, SavesModal, SettingsModal, ToastHost } from './components/modals/SystemModals'
import { ResearchModal } from './components/research/ResearchParts'
import { ActionBar, Sidebar, StatusMarquee, TickerStrip } from './components/terminal/Chrome'
import { TopBar } from './components/terminal/TopBar'
import { useGame } from './game/GameContext'
import CareerPage from './pages/CareerPage'
import Dashboard from './pages/Dashboard'
import Markets from './pages/Markets'
import NewsPage from './pages/NewsPage'
import Onboarding from './pages/Onboarding'
import PerformancePage from './pages/PerformancePage'
import PortfolioPage from './pages/PortfolioPage'
import ResearchPage from './pages/ResearchPage'
import StockDetail from './pages/StockDetail'
import TeamPage from './pages/TeamPage'
import TradingPage from './pages/TradingPage'

const PAGES = {
  dashboard: Dashboard,
  markets: Markets,
  stock: StockDetail,
  portfolio: PortfolioPage,
  research: ResearchPage,
  trading: TradingPage,
  news: NewsPage,
  team: TeamPage,
  career: CareerPage,
  performance: PerformancePage,
}

function ModalHost() {
  const { modal } = useGame()
  if (!modal) return null
  switch (modal.kind) {
    case 'trade': return <TradeTicket side={modal.side} symbol={modal.symbol} key={`${modal.side}-${modal.symbol}`} />
    case 'executed': return <ExecutedModal tx={modal.tx} />
    case 'research': return <ResearchModal symbol={modal.symbol} />
    case 'leave': return <LeaveModal />
    case 'saves': return <SavesModal />
    case 'settings': return <SettingsModal />
  }
}

function Terminal() {
  const { page, busy } = useGame()
  const Page = PAGES[page]
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <TopBar />
      <TickerStrip />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <main className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
          <div key={page} className="h-full animate-fadeIn"><Page /></div>
          {busy && (
            <div className="pointer-events-none absolute right-4 top-3 flex items-center gap-2 rounded-full border border-info/40 bg-ink-850/90 px-3 py-1 text-2xs font-semibold text-info">
              <Loader2 size={12} className="animate-spin" /> Simulating…
            </div>
          )}
        </main>
      </div>
      <ActionBar />
      <StatusMarquee />
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
