import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { SearchBox } from "./components/SearchBox";
import { Loading } from "./components/State";
import { useTheme, useWatchlist } from "./hooks";
import Explore from "./pages/Explore";
import Home from "./pages/Home";

const Player = lazy(() => import("./pages/Player"));
const Compare = lazy(() => import("./pages/Compare"));
const Connections = lazy(() => import("./pages/Connections"));
const Watchlist = lazy(() => import("./pages/Watchlist"));
const Method = lazy(() => import("./pages/Method"));

function Mark() {
  return (
    <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--accent)" />
      <circle cx="16" cy="16" r="8" fill="none" stroke="var(--accent-ink)" strokeWidth="2.4" />
      <path d="M16 4v6M16 22v6M4 16h6M22 16h6" stroke="var(--accent-ink)" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

function Header() {
  const nav = useNavigate();
  const loc = useLocation();
  const { list } = useWatchlist();
  const [theme, toggle] = useTheme();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [loc.pathname]);
  const links = (
    <>
      <NavLink to="/" end>Home</NavLink>
      <NavLink to="/explore">Explore</NavLink>
      <NavLink to="/compare">Compare</NavLink>
      <NavLink to="/connect">Connections</NavLink>
      <NavLink to="/watchlist">Watchlist{list.length > 0 && <span className="count mono">{list.length}</span>}</NavLink>
      <NavLink to="/method">Method</NavLink>
    </>
  );
  return (
    <header className="topbar">
      <div className="wrap topbar-in">
        <Link to="/" className="brand" aria-label="ScoutLens home"><Mark />ScoutLens</Link>
        <nav aria-label="Main" className="nav">{links}</nav>
        <SearchBox label="Search players" hideLabel placeholder="Search players" className="search-head" onSelect={(p) => nav(`/player/${p.player_id}`)} />
        <button className="btn btn-secondary btn-icon" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} title="Switch theme">{theme === "dark" ? "☀" : "☾"}</button>
        <button className="btn btn-secondary btn-icon menu-btn" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-nav" aria-label="Menu">{open ? "✕" : "☰"}</button>
      </div>
      {open && <nav id="mobile-nav" className="mobile-nav" aria-label="Mobile">{links}</nav>}
    </header>
  );
}

export default function App() {
  return (
    <>
      <a href="#main" className="skip">Skip to content</a>
      <Header />
      <main id="main" className="wrap">
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/player/:id" element={<Player />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/connect" element={<Connections />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/method" element={<Method />} />
            <Route path="*" element={<div className="state-empty"><strong>That page doesn't exist.</strong><p><Link to="/">Back home</Link></p></div>} />
          </Routes>
        </Suspense>
      </main>
      <footer className="wrap foot">
        <div className="foot-brand"><Mark /><span>ScoutLens</span></div>
        <p>Data: Transfermarkt (via Kaggle), five leagues, 2012–2025. Valuations are statistical estimates for research and scouting prompts, not financial or transfer advice. <Link to="/method">How it works and where it's weak</Link>.</p>
      </footer>
    </>
  );
}
