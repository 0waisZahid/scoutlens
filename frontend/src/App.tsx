import { lazy, Suspense } from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Icon } from "./components/Icons";
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

function Header() {
  const nav = useNavigate();
  const { list } = useWatchlist();
  const [theme, toggle] = useTheme();
  return (
    <header className="topbar">
      <div className="wrap topbar-in">
        <Link to="/" className="brand" aria-label="ScoutLens home">
          <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
            <rect width="32" height="32" rx="9" fill="var(--brand)" />
            <rect x="6" y="14" width="20" height="4" rx="2" fill="var(--brand-tint)" />
            <rect x="15" y="8" width="3.2" height="16" rx="1.6" fill="#fff" />
          </svg>
          ScoutLens
        </Link>
        <nav aria-label="Main" className="nav">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/explore">Explore</NavLink>
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/connect">Connections</NavLink>
          <NavLink to="/watchlist">Watchlist{list.length > 0 && <span className="count">{list.length}</span>}</NavLink>
          <NavLink to="/method">Method</NavLink>
        </nav>
        <SearchBox label="Search players" hideLabel placeholder="Search players" className="search-head"
          onSelect={(p) => nav(`/player/${p.player_id}`)} />
        <button className="btn-icon" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} title="Switch theme">
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </div>
    </header>
  );
}

function BottomBar() {
  const { list } = useWatchlist();
  const items: [string, string, "home" | "explore" | "compare" | "connect" | "saved", boolean?][] = [
    ["/", "Home", "home", true], ["/explore", "Explore", "explore"], ["/compare", "Compare", "compare"],
    ["/connect", "Connect", "connect"], ["/watchlist", "Saved", "saved"],
  ];
  return (
    <nav className="bottombar" aria-label="Main">
      {items.map(([to, label, icon, end]) => (
        <NavLink key={to} to={to} end={end}>
          <span className="bb-icon"><Icon name={icon} />{icon === "saved" && list.length > 0 && <i className="count">{list.length}</i>}</span>
          {label}
        </NavLink>
      ))}
    </nav>
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
            <Route path="*" element={<div className="state state-empty">That page doesn't exist. <Link to="/">Back home</Link>.</div>} />
          </Routes>
        </Suspense>
      </main>
      <footer className="wrap foot">
        <p>
          Data: Transfermarkt (via Kaggle), five leagues, 2012–2025. Valuations are statistical estimates for
          research and scouting prompts, not financial or transfer advice. <Link to="/method">How it works and where it's weak</Link>.
        </p>
      </footer>
      <BottomBar />
    </>
  );
}
