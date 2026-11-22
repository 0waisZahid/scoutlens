import { useEffect, useMemo, useRef, useState } from "react";
import { clubLabel, eur, LEAGUES, seasonLabel } from "../format";
import type { Card, PathStep } from "../types";

interface Props {
  path: PathStep[];
  /** teammates of the first and last player, drawn as faint satellites */
  satellites: { anchor: number; players: Card[] }[];
  onOpen: (playerId: number) => void;
}

type Node =
  | { kind: "player"; id: number; x: number; y: number; r: number; card: Card; main: boolean }
  | { kind: "club"; id: string; x: number; y: number; label: string; season: number };
type Edge = { a: string; b: string; soft: boolean };

const W = 1000, H = 520;
const initialsOf = (n: string) => { const w = n.split(/[\s-]+/).filter(Boolean); return ((w[0]?.[0] ?? "") + (w.length > 1 ? w[w.length - 1][0] : "")).toUpperCase(); };

/** Interactive teammate graph: the shortest chain as large nodes, teammates of both ends as satellites. */
export function NetworkGraph({ path, satellites, onOpen }: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const [tip, setTip] = useState<{ x: number; y: number; lines: string[] } | null>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null);

  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [], edges: Edge[] = [];
    const n = path.length, pos: [number, number][] = [];
    path.forEach((_, i) => pos.push([n === 1 ? W / 2 : 250 + (i * (W - 500)) / (n - 1), H / 2 + (i % 4 === 1 ? -46 : i % 4 === 3 ? 46 : 0)]));
    path.forEach((s, i) => {
      if (s.type === "player") nodes.push({ kind: "player", id: s.player_id, x: pos[i][0], y: pos[i][1], r: 30, card: s, main: true });
      else nodes.push({ kind: "club", id: `c${i}`, x: pos[i][0], y: pos[i][1], label: clubLabel(s), season: s.season });
      if (i > 0) edges.push({ a: keyOf(path[i - 1], i - 1), b: keyOf(s, i), soft: false });
    });
    satellites.forEach(({ anchor, players }, si) => {
      const idx = path.findIndex((s) => s.type === "player" && s.player_id === anchor);
      if (idx < 0) return;
      const [ax, ay] = pos[idx];
      const left = si === 0;
      const list = players.filter((p) => !path.some((s) => s.type === "player" && s.player_id === p.player_id)).slice(0, 8);
      list.forEach((p, j) => {
        const t = list.length === 1 ? 0.5 : j / (list.length - 1);
        const ang = (left ? Math.PI * (0.62 + t * 0.76) : Math.PI * (-0.38 + t * 0.76));
        nodes.push({ kind: "player", id: p.player_id, x: ax + Math.cos(ang) * 150, y: ay + Math.sin(ang) * 165, r: 15, card: p, main: false });
        edges.push({ a: `p${anchor}`, b: `p${p.player_id}`, soft: true });
      });
    });
    return { nodes, edges };
    function keyOf(s: PathStep, i: number) { return s.type === "player" ? `p${s.player_id}` : `c${i}`; }
  }, [path, satellites]);

  const byKey = useMemo(() => new Map(nodes.map((nd) => [nd.kind === "player" ? `p${nd.id}` : nd.id, nd])), [nodes]);

  useEffect(() => {
    const el = svg.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setView((v) => ({ ...v, k: Math.min(3, Math.max(0.6, v.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12))) }));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const showTip = (e: React.PointerEvent | React.FocusEvent, lines: string[]) => {
    const r = wrap.current!.getBoundingClientRect();
    const cx = "clientX" in e ? e.clientX : r.left + r.width / 2, cy = "clientY" in e ? e.clientY : r.top + 40;
    setTip({ x: cx - r.left, y: cy - r.top, lines });
  };
  const cardLines = (c: Card) => [c.name, `${c.sub_position ?? c.position}, ${clubLabel(c)}`, `${LEAGUES[c.league] ?? c.league}, market ${eur(c.market_value_eur)}`, "Click to open profile"];

  return (
    <div className="graph" ref={wrap}>
      <div className="graph-tools" role="group" aria-label="Graph zoom">
        <button className="btn btn-secondary btn-icon" onClick={() => setView((v) => ({ ...v, k: Math.min(3, v.k * 1.25) }))} aria-label="Zoom in">+</button>
        <button className="btn btn-secondary btn-icon" onClick={() => setView((v) => ({ ...v, k: Math.max(0.6, v.k / 1.25) }))} aria-label="Zoom out">−</button>
        <button className="btn btn-secondary" onClick={() => setView({ k: 1, x: 0, y: 0 })}>Reset</button>
      </div>
      <svg ref={svg} className="graph-svg" viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Teammate graph. Drag to pan, scroll to zoom."
        onPointerDown={(e) => { drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false }; }}
        onPointerMove={(e) => {
          const d = drag.current; if (!d) return;
          const box = svg.current!.getBoundingClientRect(), s = W / box.width;
          if (!d.moved && Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 4) { d.moved = true; svg.current!.setPointerCapture(e.pointerId); } // capture only once a real drag starts, so plain clicks still reach the node
          if (d.moved) { setTip(null); setView((v) => ({ ...v, x: d.vx + (e.clientX - d.x) * s, y: d.vy + (e.clientY - d.y) * s })); }
        }}
        onPointerUp={() => { setTimeout(() => (drag.current = null), 0); }}>
        <g transform={`translate(${W / 2 + view.x} ${H / 2 + view.y}) scale(${view.k}) translate(${-W / 2} ${-H / 2})`}>
          {edges.map((e, i) => { const a = byKey.get(e.a), b = byKey.get(e.b); return a && b ? <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={e.soft ? "edge edge-soft" : "edge"} /> : null; })}
          {nodes.map((nd) => nd.kind === "club" ? (
            <g key={nd.id} transform={`translate(${nd.x} ${nd.y})`} className="node-club"
              onPointerEnter={(e) => showTip(e, [nd.label, `Teammates in ${seasonLabel(nd.season)}`])} onPointerLeave={() => setTip(null)}>
              <rect x="-10" y="-10" width="20" height="20" rx="3" transform="rotate(45)" />
              <text y="-22" textAnchor="middle" className="node-label">{nd.label}</text>
              <text y="30" textAnchor="middle" className="node-sub mono">{seasonLabel(nd.season)}</text>
            </g>
          ) : (
            <g key={`p${nd.id}`} transform={`translate(${nd.x} ${nd.y})`} className={`node-player${nd.main ? " is-main" : ""}`} tabIndex={0} role="link"
              aria-label={`${nd.card.name}, open profile`}
              onClick={() => { if (!drag.current?.moved) onOpen(nd.id); }}
              onKeyDown={(e) => { if (e.key === "Enter") onOpen(nd.id); }}
              onPointerEnter={(e) => showTip(e, cardLines(nd.card))} onPointerLeave={() => setTip(null)}
              onFocus={(e) => showTip(e, cardLines(nd.card))} onBlur={() => setTip(null)}>
              <circle r={nd.r} />
              <text y={nd.main ? 6 : 4} textAnchor="middle" className="node-initials">{initialsOf(nd.card.name)}</text>
              <text y={nd.r + 17} textAnchor="middle" className="node-label">{nd.main ? nd.card.name : nd.card.name.split(" ").slice(-1)[0]}</text>
            </g>
          ))}
        </g>
      </svg>
      {tip && <div className="graph-tip" style={{ left: Math.min(tip.x + 14, (wrap.current?.clientWidth ?? 600) - 230), top: tip.y + 14 }} role="tooltip">
        {tip.lines.map((l, i) => <span key={i} className={i === 0 ? "strong" : ""}>{l}</span>)}
      </div>}
      <ul className="legend graph-legend">
        <li><i className="key-node main" />Players on the shortest chain</li>
        <li><i className="key-node sat" />Other teammates of either end</li>
        <li><i className="key-diamond" />Club season they shared</li>
      </ul>
    </div>
  );
}
