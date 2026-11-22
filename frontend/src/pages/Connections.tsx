import { Fragment } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { NetworkGraph } from "../components/NetworkGraph";
import { SearchBox } from "../components/SearchBox";
import { Empty, ErrorBox, Loading } from "../components/State";
import { clubLabel, eur, LEAGUES, seasonLabel } from "../format";
import { useAsync, useTitle } from "../hooks";

const EXAMPLES: [string, string][] = [["Haaland", "Messi"], ["Kane", "Modric"], ["Salah", "Neuer"]];
const useName = (id: number | null) => useAsync(async (s) => (id === null ? null : (await api.player(id, s)).name), [id]);

export default function Connections() {
  useTitle("Connections");
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const a = sp.get("a") ? Number(sp.get("a")) : null, b = sp.get("b") ? Number(sp.get("b")) : null;
  const nameA = useName(a), nameB = useName(b);
  const graph = useAsync(async (s) => {
    if (a === null || b === null) return null;
    const [conn, ta, tb] = await Promise.all([api.connection(a, b, s), api.teammates(a, 8, s), api.teammates(b, 8, s)]);
    return { conn, ta, tb };
  }, [a, b]);

  const set = (slot: "a" | "b") => (p: { player_id: number }) => { const n = new URLSearchParams(sp); n.set(slot, String(p.player_id)); setSp(n); };
  const clear = (slot: "a" | "b") => { const n = new URLSearchParams(sp); n.delete(slot); setSp(n); };
  const example = async ([x, y]: [string, string]) => {
    const [px, py] = await Promise.all([api.search(x, 1), api.search(y, 1)]);
    if (px[0] && py[0]) setSp({ a: String(px[0].player_id), b: String(py[0].player_id) });
  };
  const c = graph.data?.conn;

  return (
    <>
      <header className="page-head">
        <p className="eyebrow">Relationship graph</p>
        <h1>Connections</h1>
        <p className="lede">Two players are linked if they shared a club in the same season. Pick any two to see the shortest chain of teammates between them.</p>
      </header>

      <div className="compare-slots">
        {([["a", a, nameA.data, "From"], ["b", b, nameB.data, "To"]] as const).map(([slot, id, name, label]) => (
          <div className={`slot tone-${slot === "a" ? "a" : "b"}`} key={slot}>
            {id !== null && name ? (
              <div className="slot-id"><div><span className="label">{label}</span><Link to={`/player/${id}`} className="slot-name">{name}</Link><div className="slot-actions"><button className="link-btn" onClick={() => clear(slot)}>Change</button></div></div></div>
            ) : <SearchBox label={label} placeholder={slot === "a" ? "Search a player" : "Search another player"} onSelect={set(slot)} />}
          </div>
        ))}
      </div>
      <p className="examples"><span className="muted">Try</span>{EXAMPLES.map((e) => <button key={e.join()} className="filter-chip" onClick={() => example(e)}>{e[0]} and {e[1]}</button>)}</p>

      {(a === null || b === null) && <Empty title="Choose two players">The graph shows the shortest chain, plus other teammates of each end.</Empty>}
      {graph.loading && a !== null && b !== null && <Loading label="Searching the teammate graph" />}
      {graph.error && <ErrorBox message={graph.error} />}
      {c && c.separation === null && <Empty title="No connection found">These two players aren't connected through any chain of teammates in this data.</Empty>}

      {c && c.separation !== null && graph.data && (
        <section className="panel" aria-live="polite" aria-labelledby="chain-h">
          <div className="panel-head">
            <h2 id="chain-h">{c.separation === 0 ? "The same player" : c.separation === 1 ? "Teammates: 1 step apart" : `${c.separation} steps apart`}</h2>
            <span className="tag">Drag to pan, scroll to zoom</span>
          </div>
          <NetworkGraph path={c.path} onOpen={(id) => nav(`/player/${id}`)}
            satellites={[{ anchor: a!, players: graph.data.ta.players }, { anchor: b!, players: graph.data.tb.players }]} />
          <ol className="chain" aria-label="The chain as a list">
            {c.path.map((s, i) => (
              <Fragment key={i}>
                {s.type === "player" ? (
                  <li className="chain-player"><Link to={`/player/${s.player_id}`} className="player-link">{s.name}</Link><span className="sub">{s.sub_position ?? s.position}, {LEAGUES[s.league] ?? s.league}, <span className="mono">{eur(s.market_value_eur)}</span></span></li>
                ) : (
                  <li className="chain-club" aria-label="played together at"><span>{clubLabel(s)}</span><span className="sub mono">{seasonLabel(s.season)}</span></li>
                )}
              </Fragment>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}
