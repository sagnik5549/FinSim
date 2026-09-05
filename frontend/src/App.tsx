import React, { useState, useEffect, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Briefcase,
  Clock,
  FastForward,
  ShieldAlert,
  Newspaper,
  Award,
  BarChart2,
  Search,
  RefreshCw,
  User,
  CheckCircle2,
  AlertTriangle,
  X,
  Layers,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import type {
  GameState,
  ActiveScreen,
  StockInfo,
  HoldingInfo,
  QuarterlyReview as IQuarterlyReview,
} from './types/game';
import { gameApi } from './services/api';
import { useGameState } from './hooks/useGameState';

export default function App() {
  const [gameId, setGameId] = useState<string | null>(() => {
    return localStorage.getItem('finsim_game_id');
  });
  const [playerNameInput, setPlayerNameInput] = useState('Player');
  const [activeScreen, setActiveScreen] = useState<ActiveScreen>('dashboard');
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null);
  const [tradeModalStock, setTradeModalStock] = useState<StockInfo | null>(null);
  const [tradeAction, setTradeAction] = useState<'BUY' | 'SELL'>('BUY');
  const [tradeQuantity, setTradeQuantity] = useState<number>(100);
  const [tradeFeedback, setTradeFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isTrading, setIsTrading] = useState(false);
  const [reviewData, setReviewData] = useState<IQuarterlyReview | null>(null);
  const [loadingReview, setLoadingReview] = useState(false);
  const [savedGames, setSavedGames] = useState<Array<{ id: string; player_name: string; status: string; career_day: number; created_at: string }>>([]);
  const [loadingGames, setLoadingGames] = useState(false);
  const [startingNewGame, setStartingNewGame] = useState(false);

  const {
    state,
    setState,
    loading,
    error: stateError,
    advancing,
    refresh,
    advanceHour,
    advanceHours,
    advanceToClose,
    advanceToNextDay,
    skipWeekend,
  } = useGameState(gameId);

  // Load existing games on mount
  useEffect(() => {
    if (!gameId) {
      loadSavedGames();
    }
  }, [gameId]);

  // Initial fetch when gameId changes
  useEffect(() => {
    if (gameId) {
      refresh();
    }
  }, [gameId, refresh]);

  const loadSavedGames = async () => {
    try {
      setLoadingGames(true);
      const list = await gameApi.listGames();
      setSavedGames(list);
    } catch {
      // ignore
    } finally {
      setLoadingGames(false);
    }
  };

  const handleStartGame = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setStartingNewGame(true);
      const name = playerNameInput.trim() || 'Player';
      const res = await gameApi.newGame(name);
      localStorage.setItem('finsim_game_id', res.game_id);
      setGameId(res.game_id);
      setActiveScreen('dashboard');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to start game');
    } finally {
      setStartingNewGame(false);
    }
  };

  const handleResumeGame = (id: string) => {
    localStorage.setItem('finsim_game_id', id);
    setGameId(id);
    setActiveScreen('dashboard');
  };

  const handleQuitGame = () => {
    if (window.confirm('Return to Apex Capital lobby? Current game progress is saved.')) {
      localStorage.removeItem('finsim_game_id');
      setGameId(null);
      loadSavedGames();
    }
  };

  const handleOpenTrade = (stock: StockInfo, action: 'BUY' | 'SELL') => {
    setTradeModalStock(stock);
    setTradeAction(action);
    setTradeFeedback(null);
    if (action === 'BUY') {
      const maxShares = state ? Math.floor((state.financials.cash * 0.95) / stock.current_price) : 100;
      setTradeQuantity(Math.max(1, Math.min(100, maxShares)));
    } else {
      const holding = state?.holdings.find((h) => h.symbol === stock.symbol);
      setTradeQuantity(holding ? holding.quantity : 0);
    }
  };

  const handleExecuteTrade = async () => {
    if (!gameId || !tradeModalStock || tradeQuantity <= 0) return;
    try {
      setIsTrading(true);
      setTradeFeedback(null);
      const res = tradeAction === 'BUY'
        ? await gameApi.buy(gameId, tradeModalStock.symbol, tradeQuantity)
        : await gameApi.sell(gameId, tradeModalStock.symbol, tradeQuantity);

      if (res.success) {
        setTradeFeedback({
          type: 'success',
          text: `Executed ${tradeAction} ${res.quantity} shares of ${res.symbol} @ ₹${res.price.toFixed(2)}. Fee: ₹${res.fee.toFixed(2)}`,
        });
        await refresh();
      } else {
        setTradeFeedback({ type: 'error', text: res.message || 'Trade execution failed' });
      }
    } catch (err: unknown) {
      setTradeFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Trade execution failed',
      });
    } finally {
      setIsTrading(false);
    }
  };

  const handleTriggerReview = async () => {
    if (!gameId) return;
    try {
      setLoadingReview(true);
      const res = await gameApi.quarterlyReview(gameId);
      setReviewData(res);
      await refresh();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to fetch quarterly review');
    } finally {
      setLoadingReview(false);
    }
  };

  // If no gameId, render Onboarding Lobby
  if (!gameId || !state) {
    return (
      <div className="h-screen w-screen flex flex-col bg-[#080b10] text-[#c9d1d9] overflow-y-auto">
        {/* Terminal Header */}
        <header className="h-14 border-b border-[#21262d] bg-[#0d1117] px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-[#00d4ff] shadow-[0_0_8px_#00d4ff]" />
            <span className="font-mono text-base font-bold tracking-wider text-white">APEX CAPITAL</span>
            <span className="text-xs px-2 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff] font-mono border border-[#00d4ff]/30">
              IB MODE // SIMULATION
            </span>
          </div>
          <div className="font-mono text-xs text-[#8b949e]">
            SYSTEM READY · PORTFOLIO MANDATE: ₹100 CR → ₹112 CR
          </div>
        </header>

        {/* Lobby Content */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-3xl w-full grid grid-cols-1 md:grid-cols-5 gap-6">
            {/* Left Hero Brief */}
            <div className="md:col-span-3 panel p-8 rounded-lg flex flex-col justify-between relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#00d4ff]/5 rounded-full blur-3xl pointer-events-none" />
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-[#00d4ff]" />
                  <span className="section-label text-[#00d4ff]">INVESTMENT BANKING DIVISION</span>
                </div>
                <h1 className="text-2xl font-bold text-white mb-4 tracking-tight">
                  Welcome to Apex Capital, Head of Investments.
                </h1>
                <p className="text-sm text-[#8b949e] leading-relaxed mb-4">
                  You have been entrusted with institutional capital of <strong className="text-white font-mono">₹100 Crore</strong>.
                  Your performance evaluation takes place at the end of Quarter 1 (90 simulated career days).
                </p>
                <div className="p-4 rounded bg-[#161b22] border border-[#21262d] mb-6 space-y-2">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8b949e]">Initial Allocation:</span>
                    <span className="text-white font-semibold">₹100.00 Cr (₹1,000,000,000)</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8b949e]">Quarterly Hurdle Target:</span>
                    <span className="text-[#3fb950] font-semibold">₹112.00 Cr (+12.0% return)</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8b949e]">Evaluation Window:</span>
                    <span className="text-[#00d4ff] font-semibold">90 Days (Q1 Review)</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8b949e]">Market Universe:</span>
                    <span className="text-white">20 Equities + 8 Benchmarks</span>
                  </div>
                </div>
              </div>

              {/* Start Game Form */}
              <form onSubmit={handleStartGame} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#8b949e] mb-1.5">
                    Player Name / Alias
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={playerNameInput}
                      onChange={(e) => setPlayerNameInput(e.target.value)}
                      placeholder="e.g. Vikram Sharma"
                      className="input-field pl-9"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={startingNewGame}
                  className="btn btn-primary w-full justify-center py-3 text-sm font-bold tracking-wider"
                >
                  {startingNewGame ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      INITIALIZING APEX TERMINAL...
                    </>
                  ) : (
                    <>
                      TAKE THE DESK <ArrowRight className="w-4 h-4 ml-1" />
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Right Saved Games List */}
            <div className="md:col-span-2 panel p-6 rounded-lg flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <span className="section-label">SAVED CAREERS</span>
                <button
                  onClick={loadSavedGames}
                  disabled={loadingGames}
                  className="btn btn-ghost text-xs p-1"
                  title="Refresh saved careers"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingGames ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {loadingGames ? (
                <div className="flex-1 flex items-center justify-center text-xs text-[#8b949e] font-mono">
                  Loading careers...
                </div>
              ) : savedGames.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4 border border-dashed border-[#21262d] rounded">
                  <Briefcase className="w-8 h-8 text-[#484f58] mb-2" />
                  <p className="text-xs text-[#8b949e]">No saved careers found.</p>
                  <p className="text-[11px] text-[#484f58] mt-1">Start a new career on the left.</p>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                  {savedGames.map((g) => (
                    <div
                      key={g.id}
                      onClick={() => handleResumeGame(g.id)}
                      className="p-3 rounded bg-[#161b22] border border-[#21262d] hover:border-[#00d4ff]/40 cursor-pointer transition-all flex flex-col gap-1 group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-white group-hover:text-[#00d4ff]">
                          {g.player_name || 'Player'}
                        </span>
                        <span className="badge badge-neutral text-[10px]">
                          DAY {g.career_day}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] font-mono text-[#8b949e]">
                        <span>Status: {g.status}</span>
                        <span className="text-[#00d4ff] group-hover:translate-x-0.5 transition-transform">
                          RESUME →
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Active Terminal View
  const { time, financials, career, market, holdings, risk, recent_news } = state;

  return (
    <div className="h-screen w-screen flex flex-col bg-[#080b10] text-[#c9d1d9] overflow-hidden select-none">
      {/* ─── TOP BAR ──────────────────────────────────────────────────────── */}
      <header className="h-12 border-b border-[#21262d] bg-[#0d1117] px-4 flex items-center justify-between shrink-0 z-10">
        {/* Brand & Career */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-[#00d4ff] shadow-[0_0_6px_#00d4ff]" />
            <span className="font-mono text-sm font-bold tracking-wider text-white">APEX CAPITAL</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff] font-mono border border-[#00d4ff]/30">
              IB MODE
            </span>
          </div>

          <div className="h-4 w-px bg-[#21262d]" />

          {/* Player & Level */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-white font-semibold">{state.player_name}</span>
            <span className="text-[#8b949e]">·</span>
            <span className="text-[#00d4ff] font-semibold">{career.role} (LVL {career.level})</span>
            <span className="text-[#8b949e]">·</span>
            <span className="text-xs text-[#8b949e]">REP:</span>
            <span className="text-white font-bold">{career.reputation.toFixed(0)}%</span>
          </div>
        </div>

        {/* Financial Metrics Strip */}
        <div className="hidden lg:flex items-center gap-6 font-mono text-xs">
          <div>
            <span className="text-[#8b949e] text-[10px] block">TOTAL PORTFOLIO</span>
            <span className="stat-value text-white">₹{financials.total_value_cr.toFixed(2)} Cr</span>
          </div>
          <div>
            <span className="text-[#8b949e] text-[10px] block">UNINVESTED CASH</span>
            <span className="stat-value text-[#00d4ff]">₹{financials.cash_cr.toFixed(2)} Cr</span>
          </div>
          <div>
            <span className="text-[#8b949e] text-[10px] block">TOTAL RETURN</span>
            <span
              className={`stat-value ${
                financials.total_return_pct >= 0 ? 'text-gain' : 'text-loss'
              }`}
            >
              {financials.total_return_pct >= 0 ? '+' : ''}
              {financials.total_return_pct.toFixed(2)}%
            </span>
          </div>
          <div>
            <span className="text-[#8b949e] text-[10px] block">TARGET PROGRESS</span>
            <span className="stat-value text-[#d29922]">
              {financials.target_progress.toFixed(1)}% / ₹112 Cr
            </span>
          </div>
        </div>

        {/* Clock & Status & Actions */}
        <div className="flex items-center gap-3">
          <div className="text-right font-mono text-xs">
            <div className="flex items-center gap-1.5 justify-end">
              <span className="text-white font-semibold">DAY {time.career_day}</span>
              <span className="text-[#8b949e]">({time.day_of_week.slice(0, 3)})</span>
              <span className="text-white font-mono">{String(time.game_hour).padStart(2, '0')}:00</span>
              <span
                className={`badge ${
                  time.market_status === 'OPEN'
                    ? 'badge-gain'
                    : time.market_status === 'PRE_MARKET'
                    ? 'badge-warn'
                    : 'badge-loss'
                }`}
              >
                {time.market_status}
              </span>
            </div>
          </div>

          <button
            onClick={handleQuitGame}
            className="btn btn-ghost text-xs px-2.5 py-1"
            title="Lobby / Save & Exit"
          >
            LOBBY
          </button>
        </div>
      </header>

      {/* ─── TICKER TAPE (Indices) ────────────────────────────────────────── */}
      <div className="h-7 border-b border-[#21262d] bg-[#161b22] px-4 flex items-center overflow-x-auto whitespace-nowrap scrollbar-none shrink-0">
        <div className="flex items-center gap-5 text-[11px] font-mono">
          <span className="section-label text-[#8b949e] flex items-center gap-1">
            <Activity className="w-3 h-3 text-[#00d4ff]" /> MARKETS:
          </span>
          {market.indices.map((idx) => (
            <div key={idx.symbol} className="inline-flex items-center gap-1.5">
              <span className="text-[#8b949e] font-semibold">{idx.name}</span>
              <span className="text-white font-mono">{idx.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
              <span
                className={`text-[10px] font-bold ${
                  idx.change_pct >= 0 ? 'text-gain' : 'text-loss'
                }`}
              >
                {idx.change_pct >= 0 ? '+' : ''}
                {idx.change_pct.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ─── MAIN BODY (Sidebar + Screen Content) ─────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Nav Sidebar */}
        <aside className="w-48 border-r border-[#21262d] bg-[#0d1117] p-3 flex flex-col justify-between shrink-0">
          <div className="space-y-1">
            <div className="px-2 py-1 text-[10px] font-mono uppercase text-[#484f58] tracking-wider">
              TERMINAL VIEWS
            </div>
            {[
              { id: 'dashboard', label: 'Dashboard', icon: Layers },
              { id: 'markets', label: 'Market Universe', icon: BarChart2 },
              { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
              { id: 'trading', label: 'Order Desk', icon: TrendingUp },
              { id: 'news', label: 'News & Wire', icon: Newspaper },
              { id: 'career', label: 'Apex Career', icon: Award },
              { id: 'performance', label: 'Risk & Analytics', icon: ShieldAlert },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeScreen === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveScreen(tab.id as ActiveScreen)}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Quick Info & Review button */}
          <div className="space-y-3 pt-3 border-t border-[#21262d]">
            <div className="p-2.5 rounded bg-[#161b22] border border-[#21262d] space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-[#8b949e]">Target:</span>
                <span className="text-[#3fb950] font-bold">₹112.00 Cr</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill gain"
                  style={{ width: `${Math.min(100, financials.target_progress)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-[#8b949e]">
                <span>Progress: {financials.target_progress.toFixed(1)}%</span>
                <span>{90 - time.career_day}d left</span>
              </div>
            </div>

            <button
              onClick={handleTriggerReview}
              disabled={loadingReview}
              className="btn btn-ghost w-full justify-center text-[11px] py-2 border-[#d29922]/30 text-[#d29922] hover:bg-[#d29922]/10"
            >
              {loadingReview ? 'Evaluating...' : 'CEO QUARTERLY REVIEW'}
            </button>
          </div>
        </aside>

        {/* Central Workspace Area */}
        <main className="flex-1 flex flex-col overflow-hidden bg-[#080b10]">
          {/* Top Simulation Time Controls */}
          <div className="h-11 border-b border-[#21262d] bg-[#0d1117] px-4 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-[#00d4ff]" />
              <span className="text-xs font-mono text-[#8b949e] uppercase">ADVANCE TIME:</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={advanceHour}
                disabled={advancing}
                className="btn btn-time"
                title="Work 1 simulation hour"
              >
                +1 HOUR
              </button>
              <button
                onClick={() => advanceHours(2)}
                disabled={advancing}
                className="btn btn-time"
                title="Advance 2 hours"
              >
                +2 HOURS
              </button>
              <button
                onClick={() => advanceHours(4)}
                disabled={advancing}
                className="btn btn-time"
                title="Advance 4 hours"
              >
                +4 HOURS
              </button>
              <button
                onClick={advanceToClose}
                disabled={advancing}
                className="btn btn-time text-[#d29922] border-[#d29922]/30 hover:bg-[#d29922]/10"
                title="Advance to market close (15:30)"
              >
                TO CLOSE
              </button>
              <button
                onClick={advanceToNextDay}
                disabled={advancing}
                className="btn btn-time text-[#3fb950] border-[#3fb950]/30 hover:bg-[#3fb950]/10"
                title="Advance to next business day 09:15"
              >
                NEXT DAY
              </button>
              {time.market_status === 'WEEKEND' && (
                <button
                  onClick={skipWeekend}
                  disabled={advancing}
                  className="btn btn-time text-[#00d4ff] font-bold"
                  title="Skip to Monday market open"
                >
                  <FastForward className="w-3 h-3" /> SKIP WEEKEND
                </button>
              )}
            </div>

            {advancing && (
              <div className="flex items-center gap-2 text-xs font-mono text-[#00d4ff]">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Simulating ticks...</span>
              </div>
            )}
          </div>

          {/* Main Active Screen */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeScreen === 'dashboard' && (
              <DashboardView
                state={state}
                onSelectStock={setSelectedStock}
                onTradeStock={handleOpenTrade}
                onNavigate={setActiveScreen}
              />
            )}

            {activeScreen === 'markets' && (
              <MarketsView
                stocks={market.stocks}
                onSelectStock={setSelectedStock}
                onTradeStock={handleOpenTrade}
              />
            )}

            {activeScreen === 'portfolio' && (
              <PortfolioView
                financials={financials}
                holdings={holdings}
                onTradeStock={(symbol, action) => {
                  const s = market.stocks.find((st) => st.symbol === symbol);
                  if (s) handleOpenTrade(s, action);
                }}
                onNavigate={setActiveScreen}
              />
            )}

            {activeScreen === 'trading' && (
              <TradingDeskView
                stocks={market.stocks}
                holdings={holdings}
                financials={financials}
                onExecuteTrade={async (symbol, action, qty) => {
                  const s = market.stocks.find((st) => st.symbol === symbol);
                  if (s) {
                    handleOpenTrade(s, action);
                  }
                }}
              />
            )}

            {activeScreen === 'news' && <NewsView news={recent_news} />}

            {activeScreen === 'career' && (
              <CareerView
                career={career}
                time={time}
                financials={financials}
                onTriggerReview={handleTriggerReview}
              />
            )}

            {activeScreen === 'performance' && (
              <PerformanceView financials={financials} risk={risk} />
            )}
          </div>
        </main>
      </div>

      {/* ─── STOCK DETAIL MODAL ───────────────────────────────────────────── */}
      {selectedStock && (
        <div className="modal-backdrop" onClick={() => setSelectedStock(null)}>
          <div
            className="modal-panel max-w-2xl w-full panel p-6 rounded-lg shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedStock(null)}
              className="absolute top-4 right-4 text-[#8b949e] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white font-mono">{selectedStock.symbol}</h2>
                  <span className="badge badge-neutral">{selectedStock.sector}</span>
                </div>
                <p className="text-sm text-[#8b949e]">{selectedStock.name}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold font-mono text-white">
                  ₹{selectedStock.current_price.toFixed(2)}
                </div>
                <div
                  className={`text-xs font-mono font-bold ${
                    selectedStock.daily_return >= 0 ? 'text-gain' : 'text-loss'
                  }`}
                >
                  {selectedStock.daily_return >= 0 ? '+' : ''}
                  {(selectedStock.daily_return * 100).toFixed(2)}% Today
                </div>
              </div>
            </div>

            {/* Fundamentals Grid */}
            <div className="grid grid-cols-3 gap-3 p-4 rounded bg-[#161b22] border border-[#21262d] mb-6 font-mono text-xs">
              <div>
                <span className="text-[#8b949e] text-[10px] block">DAY OPEN / PREV</span>
                <span className="text-white">₹{selectedStock.daily_open.toFixed(2)} / ₹{selectedStock.previous_price.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">DAY HIGH / LOW</span>
                <span className="text-white">₹{selectedStock.daily_high.toFixed(2)} / ₹{selectedStock.daily_low.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">BETA & VOLATILITY</span>
                <span className="text-[#00d4ff]">{selectedStock.beta.toFixed(2)}β · {(selectedStock.volatility * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">GROWTH / PROFIT</span>
                <span className="text-white">{(selectedStock.growth * 100).toFixed(0)}% / {(selectedStock.profitability * 100).toFixed(0)}%</span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">VALUATION MULTIPLE</span>
                <span className="text-white">{selectedStock.valuation.toFixed(2)}x</span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">MARKET SENTIMENT</span>
                <span className={selectedStock.sentiment > 0.5 ? 'text-gain' : 'text-loss'}>
                  {(selectedStock.sentiment * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  const s = selectedStock;
                  setSelectedStock(null);
                  handleOpenTrade(s, 'BUY');
                }}
                className="btn btn-buy px-6 py-2.5 text-sm"
              >
                BUY {selectedStock.symbol}
              </button>
              <button
                onClick={() => {
                  const s = selectedStock;
                  setSelectedStock(null);
                  handleOpenTrade(s, 'SELL');
                }}
                className="btn btn-sell px-6 py-2.5 text-sm"
              >
                SELL {selectedStock.symbol}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── TRADE MODAL ─────────────────────────────────────────────────── */}
      {tradeModalStock && (
        <div className="modal-backdrop" onClick={() => setTradeModalStock(null)}>
          <div
            className="modal-panel max-w-md w-full panel p-6 rounded-lg shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setTradeModalStock(null)}
              className="absolute top-4 right-4 text-[#8b949e] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-1">
              <span
                className={`badge font-mono ${
                  tradeAction === 'BUY' ? 'badge-gain' : 'badge-loss'
                }`}
              >
                ORDER DESK: {tradeAction}
              </span>
              <span className="text-xs text-[#8b949e] font-mono">{tradeModalStock.sector}</span>
            </div>

            <h2 className="text-xl font-bold text-white font-mono mb-1">
              {tradeModalStock.symbol} — {tradeModalStock.name}
            </h2>
            <div className="text-sm font-mono text-[#8b949e] mb-4">
              Market Price: <strong className="text-white">₹{tradeModalStock.current_price.toFixed(2)}</strong>
            </div>

            {/* Toggle Action */}
            <div className="grid grid-cols-2 gap-2 mb-4">
              <button
                onClick={() => {
                  setTradeAction('BUY');
                  setTradeFeedback(null);
                }}
                className={`btn justify-center py-2 ${
                  tradeAction === 'BUY' ? 'btn-buy font-bold' : 'btn-ghost'
                }`}
              >
                BUY (LONG)
              </button>
              <button
                onClick={() => {
                  setTradeAction('SELL');
                  setTradeFeedback(null);
                }}
                className={`btn justify-center py-2 ${
                  tradeAction === 'SELL' ? 'btn-sell font-bold' : 'btn-ghost'
                }`}
              >
                SELL (EXIT)
              </button>
            </div>

            {/* Quantity Input */}
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-xs font-mono text-[#8b949e] mb-1">
                  ORDER QUANTITY (SHARES)
                </label>
                <input
                  type="number"
                  min="1"
                  step="10"
                  value={tradeQuantity}
                  onChange={(e) => setTradeQuantity(Math.max(1, parseInt(e.target.value) || 0))}
                  className="input-field text-right text-base font-bold"
                />
              </div>

              {/* Quick Presets */}
              <div className="flex gap-1.5 justify-end text-[11px] font-mono">
                {[10, 50, 100, 500, 1000].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setTradeQuantity(q)}
                    className="px-2 py-0.5 rounded bg-[#161b22] border border-[#21262d] hover:border-[#00d4ff] text-[#8b949e] hover:text-white"
                  >
                    {q}
                  </button>
                ))}
                {tradeAction === 'BUY' && (
                  <button
                    type="button"
                    onClick={() => {
                      const max = Math.floor((financials.cash * 0.95) / tradeModalStock.current_price);
                      setTradeQuantity(Math.max(1, max));
                    }}
                    className="px-2 py-0.5 rounded bg-[#161b22] border border-[#00d4ff]/40 text-[#00d4ff]"
                  >
                    MAX
                  </button>
                )}
                {tradeAction === 'SELL' && (
                  <button
                    type="button"
                    onClick={() => {
                      const h = holdings.find((item) => item.symbol === tradeModalStock.symbol);
                      setTradeQuantity(h ? h.quantity : 0);
                    }}
                    className="px-2 py-0.5 rounded bg-[#161b22] border border-[#f85149]/40 text-[#f85149]"
                  >
                    ALL
                  </button>
                )}
              </div>

              {/* Order Calculation Box */}
              <div className="p-3 rounded bg-[#161b22] border border-[#21262d] space-y-1 text-xs font-mono">
                <div className="flex justify-between text-[#8b949e]">
                  <span>Order Value:</span>
                  <span className="text-white">
                    ₹{(tradeQuantity * tradeModalStock.current_price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between text-[#8b949e]">
                  <span>Est. Transaction Fee (0.1%):</span>
                  <span className="text-white">
                    ₹{(tradeQuantity * tradeModalStock.current_price * 0.001).toFixed(2)}
                  </span>
                </div>
                <div className="divider my-1" />
                <div className="flex justify-between font-bold">
                  <span className="text-white">Total Outlay:</span>
                  <span className="text-[#00d4ff]">
                    ₹{(tradeQuantity * tradeModalStock.current_price * 1.001).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between text-[11px] text-[#8b949e]">
                  <span>Available Cash:</span>
                  <span>₹{financials.cash_cr.toFixed(2)} Cr</span>
                </div>
              </div>
            </div>

            {/* Feedback Alert */}
            {tradeFeedback && (
              <div
                className={`p-2.5 rounded text-xs font-mono mb-4 flex items-center gap-2 ${
                  tradeFeedback.type === 'success'
                    ? 'bg-[#3fb950]/15 text-[#3fb950] border border-[#3fb950]/30'
                    : 'bg-[#f85149]/15 text-[#f85149] border border-[#f85149]/30'
                }`}
              >
                {tradeFeedback.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                )}
                <span>{tradeFeedback.text}</span>
              </div>
            )}

            {/* Execute Button */}
            <button
              onClick={handleExecuteTrade}
              disabled={isTrading || tradeQuantity <= 0}
              className={`btn w-full justify-center py-2.5 text-sm font-bold ${
                tradeAction === 'BUY' ? 'btn-buy' : 'btn-sell'
              }`}
            >
              {isTrading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> EXECUTING ORDER...
                </>
              ) : (
                `CONFIRM ${tradeAction} ORDER`
              )}
            </button>
          </div>
        </div>
      )}

      {/* ─── QUARTERLY REVIEW MODAL ──────────────────────────────────────── */}
      {reviewData && (
        <div className="modal-backdrop" onClick={() => setReviewData(null)}>
          <div
            className="modal-panel max-w-xl w-full panel p-8 rounded-lg shadow-2xl relative border-[#00d4ff]/40"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setReviewData(null)}
              className="absolute top-4 right-4 text-[#8b949e] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-2">
              <Award className="w-6 h-6 text-[#d29922]" />
              <span className="section-label text-[#d29922]">APEX CAPITAL BOARD EVALUATION</span>
            </div>

            <h2 className="text-2xl font-bold text-white font-mono mb-2">
              Quarter 1 Performance Verdict: {reviewData.outcome}
            </h2>

            {/* CEO Letter Dialogue Box */}
            <div className="dialogue-panel mb-6 space-y-3">
              <div className="flex items-center gap-2 font-mono text-xs text-[#00d4ff]">
                <User className="w-4 h-4" />
                <span>OFFICE OF THE CHIEF EXECUTIVE OFFICER</span>
              </div>
              <p className="text-sm text-white italic leading-relaxed">
                "{reviewData.ceo_message}"
              </p>
              <p className="text-xs text-[#8b949e] leading-relaxed">
                {reviewData.summary}
              </p>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-3 p-4 rounded bg-[#161b22] border border-[#21262d] mb-6 font-mono text-xs">
              <div>
                <span className="text-[#8b949e] text-[10px] block">FINAL RETURN ACHIEVED</span>
                <span
                  className={`stat-value ${
                    reviewData.final_return >= reviewData.target_return ? 'text-gain' : 'text-loss'
                  }`}
                >
                  {(reviewData.final_return * 100).toFixed(2)}%
                </span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">HURDLE TARGET</span>
                <span className="stat-value text-white">
                  {(reviewData.target_return * 100).toFixed(2)}%
                </span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">MAX DRAWDOWN</span>
                <span className="stat-value text-[#f85149]">
                  {(reviewData.max_drawdown * 100).toFixed(2)}%
                </span>
              </div>
              <div>
                <span className="text-[#8b949e] text-[10px] block">REPUTATION & XP</span>
                <span className="stat-value text-[#00d4ff]">
                  +{reviewData.xp_awarded} XP ({reviewData.reputation_change >= 0 ? '+' : ''}
                  {reviewData.reputation_change} Rep)
                </span>
              </div>
            </div>

            <button
              onClick={() => setReviewData(null)}
              className="btn btn-primary w-full justify-center py-2.5"
            >
              ACKNOWLEDGE AND CONTINUE MANDATE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-VIEWS / SCREENS
// ─────────────────────────────────────────────────────────────────────────────

function DashboardView({
  state,
  onSelectStock,
  onTradeStock,
  onNavigate,
}: {
  state: GameState;
  onSelectStock: (stock: StockInfo) => void;
  onTradeStock: (stock: StockInfo, action: 'BUY' | 'SELL') => void;
  onNavigate: (screen: ActiveScreen) => void;
}) {
  const { financials, market, holdings, recent_news } = state;

  const topGainers = useMemo(() => {
    return [...market.stocks].sort((a, b) => b.daily_return - a.daily_return).slice(0, 4);
  }, [market.stocks]);

  const topLosers = useMemo(() => {
    return [...market.stocks].sort((a, b) => a.daily_return - b.daily_return).slice(0, 4);
  }, [market.stocks]);

  return (
    <div className="space-y-4">
      {/* 4 Stat Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="panel p-4 rounded-lg">
          <span className="section-label">NET PORTFOLIO VALUE</span>
          <div className="stat-value-lg text-white mt-1">₹{financials.total_value_cr.toFixed(2)} Cr</div>
          <div className="text-[11px] font-mono text-[#8b949e] mt-1 flex justify-between">
            <span>Starting: ₹{financials.starting_capital_cr.toFixed(2)} Cr</span>
            <span className={financials.total_pnl_cr >= 0 ? 'text-gain' : 'text-loss'}>
              {financials.total_pnl_cr >= 0 ? '+' : ''}₹{financials.total_pnl_cr.toFixed(2)} Cr
            </span>
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">TARGET REQUIREMENT</span>
          <div className="stat-value-lg text-[#d29922] mt-1">₹{financials.quarterly_target_cr.toFixed(2)} Cr</div>
          <div className="text-[11px] font-mono text-[#8b949e] mt-1 flex justify-between">
            <span>Progress: {financials.target_progress.toFixed(1)}%</span>
            <span>Rem: ₹{financials.to_target_cr.toFixed(2)} Cr</span>
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">LIQUID CAPITAL</span>
          <div className="stat-value-lg text-[#00d4ff] mt-1">₹{financials.cash_cr.toFixed(2)} Cr</div>
          <div className="text-[11px] font-mono text-[#8b949e] mt-1 flex justify-between">
            <span>Invested: ₹{financials.invested_value_cr.toFixed(2)} Cr</span>
            <span>{((financials.cash / financials.total_value) * 100).toFixed(0)}% Liquid</span>
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">ACTIVE HOLDINGS</span>
          <div className="stat-value-lg text-white mt-1">{holdings.length} Positions</div>
          <div className="text-[11px] font-mono text-[#8b949e] mt-1 flex justify-between">
            <span>Max DD: {(financials.max_drawdown * 100).toFixed(1)}%</span>
            <span className="text-[#3fb950]">Risk: {state.risk.overall_level}</span>
          </div>
        </div>
      </div>

      {/* Center 2-Column Grid: Movers & Active Positions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Market Movers */}
        <div className="panel p-4 rounded-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="section-label">TOP MARKET MOVERS TODAY</span>
            <button
              onClick={() => onNavigate('markets')}
              className="text-xs font-mono text-[#00d4ff] hover:underline"
            >
              ALL 20 EQUITIES →
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 flex-1">
            {/* Gainers */}
            <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
              <span className="text-[10px] font-mono text-gain font-bold block mb-2">TOP GAINERS</span>
              <div className="space-y-2">
                {topGainers.map((s) => (
                  <div
                    key={s.symbol}
                    onClick={() => onSelectStock(s)}
                    className="flex justify-between items-center text-xs font-mono p-1 rounded hover:bg-white/5 cursor-pointer"
                  >
                    <div>
                      <span className="font-bold text-white">{s.symbol}</span>
                      <span className="text-[10px] text-[#8b949e] block">{s.name}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-white">₹{s.current_price.toFixed(2)}</span>
                      <span className="text-gain block font-bold text-[10px]">
                        +{(s.daily_return * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Losers */}
            <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
              <span className="text-[10px] font-mono text-loss font-bold block mb-2">TOP DECLINERS</span>
              <div className="space-y-2">
                {topLosers.map((s) => (
                  <div
                    key={s.symbol}
                    onClick={() => onSelectStock(s)}
                    className="flex justify-between items-center text-xs font-mono p-1 rounded hover:bg-white/5 cursor-pointer"
                  >
                    <div>
                      <span className="font-bold text-white">{s.symbol}</span>
                      <span className="text-[10px] text-[#8b949e] block">{s.name}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-white">₹{s.current_price.toFixed(2)}</span>
                      <span className="text-loss block font-bold text-[10px]">
                        {(s.daily_return * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Current Holdings Snapshot */}
        <div className="panel p-4 rounded-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="section-label">PORTFOLIO EXPOSURE</span>
            <button
              onClick={() => onNavigate('portfolio')}
              className="text-xs font-mono text-[#00d4ff] hover:underline"
            >
              DETAILED PORTFOLIO →
            </button>
          </div>

          {holdings.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-[#21262d] rounded">
              <Briefcase className="w-8 h-8 text-[#484f58] mb-2" />
              <p className="text-xs text-[#8b949e]">100% Cash Position (₹100 Cr Liquid).</p>
              <p className="text-[11px] text-[#484f58] mt-1">
                Browse the Market Universe to buy equities and generate target alpha.
              </p>
              <button
                onClick={() => onNavigate('markets')}
                className="btn btn-buy text-xs mt-3"
              >
                BROWSE STOCKS
              </button>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {holdings.map((h) => (
                <div
                  key={h.symbol}
                  className="p-2.5 rounded bg-[#161b22] border border-[#21262d] flex items-center justify-between font-mono text-xs"
                >
                  <div>
                    <span className="font-bold text-white">{h.symbol}</span>
                    <span className="text-[#8b949e] text-[10px] block">{h.quantity} shares · avg ₹{h.avg_buy_price.toFixed(2)}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-white font-bold">₹{h.current_value_cr.toFixed(2)} Cr</span>
                    <span
                      className={`text-[10px] block font-semibold ${
                        h.unrealized_pnl >= 0 ? 'text-gain' : 'text-loss'
                      }`}
                    >
                      {h.unrealized_pnl >= 0 ? '+' : ''}
                      {h.unrealized_pnl_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom News Wire */}
      <div className="panel p-4 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <span className="section-label">LATEST INTELLIGENCE & NEWS WIRE</span>
          <button
            onClick={() => onNavigate('news')}
            className="text-xs font-mono text-[#00d4ff] hover:underline"
          >
            ALL NEWS →
          </button>
        </div>

        {recent_news.length === 0 ? (
          <p className="text-xs text-[#8b949e] font-mono">No recent breaking events. Advance market hours to generate flow.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recent_news.slice(0, 4).map((n) => (
              <div
                key={n.id}
                className="p-3 rounded bg-[#161b22] border border-[#21262d] flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="badge badge-neutral text-[9px]">{n.category}</span>
                    <span className="text-[10px] font-mono text-[#8b949e]">
                      Day {n.career_day} · {n.game_hour}:00
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-white mb-1">{n.headline}</h4>
                  {n.body && <p className="text-[11px] text-[#8b949e] line-clamp-2">{n.body}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MarketsView({
  stocks,
  onSelectStock,
  onTradeStock,
}: {
  stocks: StockInfo[];
  onSelectStock: (stock: StockInfo) => void;
  onTradeStock: (stock: StockInfo, action: 'BUY' | 'SELL') => void;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sectorFilter, setSectorFilter] = useState('ALL');

  const sectors = useMemo(() => {
    const set = new Set(stocks.map((s) => s.sector));
    return ['ALL', ...Array.from(set)];
  }, [stocks]);

  const filteredStocks = useMemo(() => {
    return stocks.filter((s) => {
      const matchesSearch =
        s.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesSector = sectorFilter === 'ALL' || s.sector === sectorFilter;
      return matchesSearch && matchesSector;
    });
  }, [stocks, searchTerm, sectorFilter]);

  return (
    <div className="panel p-4 rounded-lg space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by symbol or company..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field pl-9 text-xs"
          />
        </div>

        <div className="flex gap-1 overflow-x-auto w-full sm:w-auto">
          {sectors.map((sec) => (
            <button
              key={sec}
              onClick={() => setSectorFilter(sec)}
              className={`px-2.5 py-1 rounded text-xs font-mono ${
                sectorFilter === sec
                  ? 'bg-[#00d4ff]/20 text-[#00d4ff] border border-[#00d4ff]/40'
                  : 'bg-[#161b22] text-[#8b949e] hover:text-white border border-[#21262d]'
              }`}
            >
              {sec}
            </button>
          ))}
        </div>
      </div>

      {/* Stock Screener Table */}
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>SYMBOL / COMPANY</th>
              <th>SECTOR</th>
              <th>PRICE (₹)</th>
              <th>CHANGE</th>
              <th>DAY RANGE</th>
              <th>BETA</th>
              <th>VALUATION</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map((s) => (
              <tr key={s.symbol} onClick={() => onSelectStock(s)}>
                <td>
                  <span className="font-bold text-white block">{s.symbol}</span>
                  <span className="text-[10px] text-[#8b949e] block">{s.name}</span>
                </td>
                <td>
                  <span className="badge badge-neutral text-[10px]">{s.sector}</span>
                </td>
                <td className="font-bold text-white">₹{s.current_price.toFixed(2)}</td>
                <td className={s.daily_return >= 0 ? 'text-gain' : 'text-loss'}>
                  {s.daily_return >= 0 ? '+' : ''}
                  {(s.daily_return * 100).toFixed(2)}%
                </td>
                <td className="text-[11px] text-[#8b949e]">
                  ₹{s.daily_low.toFixed(0)} - ₹{s.daily_high.toFixed(0)}
                </td>
                <td className="text-[#00d4ff]">{s.beta.toFixed(2)}</td>
                <td className="text-white">{s.valuation.toFixed(2)}x</td>
                <td onClick={(e) => e.stopPropagation()}>
                  <div className="flex gap-1.5 justify-end">
                    <button
                      onClick={() => onTradeStock(s, 'BUY')}
                      className="btn btn-buy text-[11px] py-1 px-2.5"
                    >
                      BUY
                    </button>
                    <button
                      onClick={() => onTradeStock(s, 'SELL')}
                      className="btn btn-sell text-[11px] py-1 px-2.5"
                    >
                      SELL
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PortfolioView({
  financials,
  holdings,
  onTradeStock,
  onNavigate,
}: {
  financials: GameState['financials'];
  holdings: HoldingInfo[];
  onTradeStock: (symbol: string, action: 'BUY' | 'SELL') => void;
  onNavigate: (screen: ActiveScreen) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="panel p-4 rounded-lg">
          <span className="section-label">PORTFOLIO VALUATION</span>
          <div className="stat-value-lg text-white mt-1">₹{financials.total_value_cr.toFixed(2)} Cr</div>
          <div className="text-xs text-[#8b949e] font-mono mt-1">
            Target: ₹{financials.quarterly_target_cr.toFixed(2)} Cr
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">CASH BALANCE</span>
          <div className="stat-value-lg text-[#00d4ff] mt-1">₹{financials.cash_cr.toFixed(2)} Cr</div>
          <div className="text-xs text-[#8b949e] font-mono mt-1">
            Invested: ₹{financials.invested_value_cr.toFixed(2)} Cr
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">UNREALIZED P&L</span>
          <div
            className={`stat-value-lg mt-1 ${
              financials.unrealized_pnl >= 0 ? 'text-gain' : 'text-loss'
            }`}
          >
            {financials.unrealized_pnl >= 0 ? '+' : ''}₹{(financials.unrealized_pnl / 1e7).toFixed(2)} Cr
          </div>
          <div className="text-xs text-[#8b949e] font-mono mt-1">
            Realized: ₹{(financials.realized_pnl / 1e7).toFixed(2)} Cr
          </div>
        </div>

        <div className="panel p-4 rounded-lg">
          <span className="section-label">TOTAL RETURN</span>
          <div
            className={`stat-value-lg mt-1 ${
              financials.total_return_pct >= 0 ? 'text-gain' : 'text-loss'
            }`}
          >
            {financials.total_return_pct >= 0 ? '+' : ''}
            {financials.total_return_pct.toFixed(2)}%
          </div>
          <div className="text-xs text-[#8b949e] font-mono mt-1">
            Max Drawdown: {(financials.max_drawdown * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="panel p-4 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <span className="section-label">EQUITY HOLDINGS & ALLOCATIONS</span>
          <button
            onClick={() => onNavigate('markets')}
            className="btn btn-buy text-xs py-1"
          >
            + ADD POSITIONS
          </button>
        </div>

        {holdings.length === 0 ? (
          <div className="text-center p-8 border border-dashed border-[#21262d] rounded">
            <p className="text-xs text-[#8b949e] font-mono">No active equity positions.</p>
            <button
              onClick={() => onNavigate('markets')}
              className="btn btn-primary text-xs mt-3"
            >
              DEPLOY CAPITAL IN MARKETS
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SECTOR</th>
                  <th>QUANTITY</th>
                  <th>AVG COST</th>
                  <th>CURRENT</th>
                  <th>VALUE (₹ CR)</th>
                  <th>UNREALIZED P&L</th>
                  <th>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.symbol}>
                    <td>
                      <span className="font-bold text-white block">{h.symbol}</span>
                      <span className="text-[10px] text-[#8b949e] block">{h.name}</span>
                    </td>
                    <td>
                      <span className="badge badge-neutral text-[10px]">{h.sector}</span>
                    </td>
                    <td>{h.quantity.toLocaleString('en-IN')}</td>
                    <td>₹{h.avg_buy_price.toFixed(2)}</td>
                    <td className="font-bold text-white">₹{h.current_price.toFixed(2)}</td>
                    <td className="font-bold text-[#00d4ff]">₹{h.current_value_cr.toFixed(2)} Cr</td>
                    <td className={h.unrealized_pnl >= 0 ? 'text-gain' : 'text-loss'}>
                      {h.unrealized_pnl >= 0 ? '+' : ''}₹{(h.unrealized_pnl / 1e7).toFixed(2)} Cr
                      <span className="block text-[10px]">
                        ({h.unrealized_pnl_pct >= 0 ? '+' : ''}{h.unrealized_pnl_pct.toFixed(2)}%)
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-1.5 justify-end">
                        <button
                          onClick={() => onTradeStock(h.symbol, 'BUY')}
                          className="btn btn-buy text-[11px] py-1 px-2.5"
                        >
                          BUY
                        </button>
                        <button
                          onClick={() => onTradeStock(h.symbol, 'SELL')}
                          className="btn btn-sell text-[11px] py-1 px-2.5"
                        >
                          SELL
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function TradingDeskView({
  stocks,
  holdings,
  financials,
  onExecuteTrade,
}: {
  stocks: StockInfo[];
  holdings: HoldingInfo[];
  financials: GameState['financials'];
  onExecuteTrade: (symbol: string, action: 'BUY' | 'SELL', qty: number) => void;
}) {
  const [selectedSymbol, setSelectedSymbol] = useState(stocks[0]?.symbol || '');
  const [action, setAction] = useState<'BUY' | 'SELL'>('BUY');
  const [qty, setQty] = useState(100);

  const currentStock = stocks.find((s) => s.symbol === selectedSymbol) || stocks[0];
  const holding = holdings.find((h) => h.symbol === selectedSymbol);

  const maxAffordable = currentStock
    ? Math.floor((financials.cash * 0.95) / currentStock.current_price)
    : 0;

  return (
    <div className="max-w-2xl mx-auto panel p-6 rounded-lg space-y-6">
      <div className="border-b border-[#21262d] pb-4">
        <span className="section-label">ORDER ENTRY DESK</span>
        <h2 className="text-xl font-bold text-white font-mono mt-1">
          Execute Equities Order
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => setAction('BUY')}
          className={`btn justify-center py-2.5 text-sm ${
            action === 'BUY' ? 'btn-buy font-bold' : 'btn-ghost'
          }`}
        >
          BUY (LONG)
        </button>
        <button
          onClick={() => setAction('SELL')}
          className={`btn justify-center py-2.5 text-sm ${
            action === 'SELL' ? 'btn-sell font-bold' : 'btn-ghost'
          }`}
        >
          SELL (EXIT)
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-mono text-[#8b949e] mb-1">SELECT EQUITIES TICKER</label>
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="input-field"
          >
            {stocks.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol} — {s.name} (₹{s.current_price.toFixed(2)}) [{s.sector}]
              </option>
            ))}
          </select>
        </div>

        {currentStock && (
          <div className="p-4 rounded bg-[#161b22] border border-[#21262d] grid grid-cols-3 gap-2 font-mono text-xs">
            <div>
              <span className="text-[#8b949e] text-[10px] block">CURRENT PRICE</span>
              <span className="text-white font-bold">₹{currentStock.current_price.toFixed(2)}</span>
            </div>
            <div>
              <span className="text-[#8b949e] text-[10px] block">TODAY RETURN</span>
              <span className={currentStock.daily_return >= 0 ? 'text-gain' : 'text-loss'}>
                {(currentStock.daily_return * 100).toFixed(2)}%
              </span>
            </div>
            <div>
              <span className="text-[#8b949e] text-[10px] block">CURRENT HOLDING</span>
              <span className="text-[#00d4ff]">{holding ? `${holding.quantity} shares` : '0 shares'}</span>
            </div>
          </div>
        )}

        <div>
          <label className="block text-xs font-mono text-[#8b949e] mb-1">ORDER QUANTITY (SHARES)</label>
          <input
            type="number"
            min="1"
            value={qty}
            onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 0))}
            className="input-field text-right font-bold text-base"
          />
          <div className="flex gap-2 justify-end mt-2 text-xs font-mono">
            {action === 'BUY' && (
              <>
                <button
                  type="button"
                  onClick={() => setQty(Math.max(1, Math.floor(maxAffordable * 0.25)))}
                  className="px-2 py-0.5 rounded bg-[#161b22] border border-[#21262d] text-[#8b949e] hover:text-white"
                >
                  25% Cash
                </button>
                <button
                  type="button"
                  onClick={() => setQty(Math.max(1, Math.floor(maxAffordable * 0.5)))}
                  className="px-2 py-0.5 rounded bg-[#161b22] border border-[#21262d] text-[#8b949e] hover:text-white"
                >
                  50% Cash
                </button>
                <button
                  type="button"
                  onClick={() => setQty(Math.max(1, maxAffordable))}
                  className="px-2 py-0.5 rounded bg-[#161b22] border border-[#00d4ff]/40 text-[#00d4ff]"
                >
                  Max Affordable ({maxAffordable})
                </button>
              </>
            )}
            {action === 'SELL' && holding && (
              <button
                type="button"
                onClick={() => setQty(holding.quantity)}
                className="px-2 py-0.5 rounded bg-[#161b22] border border-[#f85149]/40 text-[#f85149]"
              >
                Sell All ({holding.quantity})
              </button>
            )}
          </div>
        </div>

        {currentStock && (
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d] space-y-1 font-mono text-xs">
            <div className="flex justify-between text-[#8b949e]">
              <span>Estimated Value:</span>
              <span className="text-white">₹{(qty * currentStock.current_price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between text-[#8b949e]">
              <span>Brokerage Fee (0.1%):</span>
              <span className="text-white">₹{(qty * currentStock.current_price * 0.001).toFixed(2)}</span>
            </div>
          </div>
        )}

        <button
          onClick={() => currentStock && onExecuteTrade(currentStock.symbol, action, qty)}
          className={`btn w-full justify-center py-3 text-sm font-bold ${
            action === 'BUY' ? 'btn-buy' : 'btn-sell'
          }`}
        >
          CONFIRM AND ROUTE {action} ORDER
        </button>
      </div>
    </div>
  );
}

function NewsView({ news }: { news: GameState['recent_news'] }) {
  return (
    <div className="panel p-4 rounded-lg space-y-3">
      <div className="flex items-center justify-between border-b border-[#21262d] pb-2">
        <span className="section-label">FINANCIAL INTELLIGENCE WIRE</span>
        <span className="text-xs font-mono text-[#8b949e]">{news.length} Broadcasts</span>
      </div>

      {news.length === 0 ? (
        <div className="text-center p-8 text-[#8b949e] font-mono text-xs">
          No wire announcements yet. Advance market ticks to receive macroeconomic and corporate updates.
        </div>
      ) : (
        <div className="space-y-3">
          {news.map((item) => (
            <div
              key={item.id}
              className="p-4 rounded bg-[#161b22] border border-[#21262d] space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`badge ${
                      item.priority === 'BREAKING'
                        ? 'badge-critical'
                        : item.priority === 'HIGH'
                        ? 'badge-warn'
                        : 'badge-neutral'
                    }`}
                  >
                    {item.priority}
                  </span>
                  <span className="badge badge-neutral">{item.category}</span>
                  {item.affected_symbol && (
                    <span className="text-xs font-mono text-[#00d4ff] font-bold">
                      ${item.affected_symbol}
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono text-[#8b949e]">
                  Day {item.career_day} · {String(item.game_hour).padStart(2, '0')}:00
                </span>
              </div>
              <h3 className="text-sm font-bold text-white">{item.headline}</h3>
              {item.body && <p className="text-xs text-[#8b949e] leading-relaxed">{item.body}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CareerView({
  career,
  time,
  financials,
  onTriggerReview,
}: {
  career: GameState['career'];
  time: GameState['time'];
  financials: GameState['financials'];
  onTriggerReview: () => void;
}) {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="panel p-6 rounded-lg space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <span className="section-label">APEX CAPITAL PERSONNEL DOSSIER</span>
            <h2 className="text-2xl font-bold text-white font-mono mt-1">{career.role}</h2>
            <p className="text-xs text-[#8b949e] font-mono mt-0.5">
              Clearance Level: {career.level} · Reputation Rating: {career.reputation.toFixed(0)}%
            </p>
          </div>
          <span className="badge badge-neutral text-xs">STATUS: ACTIVE</span>
        </div>

        {/* XP Progress */}
        <div>
          <div className="flex justify-between text-xs font-mono mb-1.5">
            <span className="text-[#8b949e]">XP Progress to Next Promotion:</span>
            <span className="text-white font-bold">{career.xp} / {career.xp_to_next_level} XP</span>
          </div>
          <div className="xp-bar">
            <div
              className="xp-fill"
              style={{ width: `${Math.min(100, (career.xp / career.xp_to_next_level) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Q1 Objectives Box */}
      <div className="panel p-6 rounded-lg space-y-4">
        <span className="section-label">QUARTER 1 MANDATE OBJECTIVES</span>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">INITIAL ALLOCATION</span>
            <span className="text-white font-bold text-sm">₹100.00 Cr</span>
          </div>
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">HURDLE TARGET</span>
            <span className="text-[#3fb950] font-bold text-sm">₹112.00 Cr</span>
          </div>
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">REMAINING DAYS</span>
            <span className="text-[#00d4ff] font-bold text-sm">{90 - time.career_day} Days</span>
          </div>
        </div>

        <div className="p-4 rounded bg-[#161b22] border border-[#21262d] space-y-2 text-xs font-mono">
          <div className="flex items-center justify-between">
            <span className="text-[#8b949e]">Target Return:</span>
            <span className="text-white font-semibold">+12.00% absolute</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#8b949e]">Current Net Worth:</span>
            <span className="text-white font-semibold">₹{financials.total_value_cr.toFixed(2)} Cr</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#8b949e]">Distance to Target:</span>
            <span className={financials.to_target_cr <= 0 ? 'text-gain' : 'text-warn'}>
              {financials.to_target_cr <= 0 ? 'TARGET REACHED!' : `₹${financials.to_target_cr.toFixed(2)} Cr needed`}
            </span>
          </div>
        </div>

        <button
          onClick={onTriggerReview}
          className="btn btn-primary w-full justify-center py-2.5 text-xs font-bold"
        >
          REQUEST FORMAL QUARTERLY REVIEW NOW
        </button>
      </div>
    </div>
  );
}

function PerformanceView({
  financials,
  risk,
}: {
  financials: GameState['financials'];
  risk: GameState['risk'];
}) {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="panel p-6 rounded-lg space-y-4">
        <span className="section-label">RISK & EXPOSURE METRICS</span>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">OVERALL RISK LEVEL</span>
            <span
              className={`font-bold text-sm ${
                risk.overall_level === 'LOW'
                  ? 'text-gain'
                  : risk.overall_level === 'MEDIUM'
                  ? 'text-warn'
                  : 'text-loss'
              }`}
            >
              {risk.overall_level}
            </span>
          </div>
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">PORTFOLIO VOLATILITY</span>
            <span className="text-white font-bold text-sm">
              {(financials.portfolio_volatility * 100).toFixed(2)}%
            </span>
          </div>
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">MAX DRAWDOWN</span>
            <span className="text-[#f85149] font-bold text-sm">
              {(financials.max_drawdown * 100).toFixed(2)}%
            </span>
          </div>
          <div className="p-3 rounded bg-[#161b22] border border-[#21262d]">
            <span className="text-[#8b949e] text-[10px] block">CASH RATIO</span>
            <span className="text-[#00d4ff] font-bold text-sm">
              {risk.cash_ratio.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Warnings List */}
      <div className="panel p-6 rounded-lg space-y-3">
        <span className="section-label">ACTIVE RISK WARNINGS</span>
        {risk.warnings.length === 0 ? (
          <p className="text-xs text-gain font-mono">
            ✓ No risk limits currently breached. Portfolio is within compliance parameters.
          </p>
        ) : (
          <div className="space-y-2">
            {risk.warnings.map((w, idx) => (
              <div
                key={idx}
                className="p-3 rounded bg-[#f85149]/10 border border-[#f85149]/30 text-xs font-mono text-[#f85149]"
              >
                <strong>[{w.level}] {w.code}:</strong> {w.message}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
