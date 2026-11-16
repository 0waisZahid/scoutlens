import { Fragment } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { SearchBox } from "../components/SearchBox";
import { Empty, ErrorBox, Loading } from "../components/State";
import { clubLabel, eur, LEAGUES, seasonLabel } from "../format";
import { useAsync, useTitle } from "../hooks";

const EXAMPLES: [string, string][] = [["Haaland", "Messi"], ["Kane", "Modric"], ["Salah", "Neuer"]];

function useName(id: number | null) {
  return useAsync(async (s) => (id === null ? null : (await api.player(id, s)).name), [id]);
}

export default function Connections() {
  useTitle("Connections");
  const [sp, setSp] = useSearchParams();
  const a = sp.get("a") ? Number(sp.get("a")) : null;
  const b = sp.get("b") ? Number(sp.get("b")) : null;
  const nameA = useName(a);
  const nameB = useName(b);
  const conn = useAsync(async (s) => (a !== null && b !== null ? api.connection(a, b, s) : null), [a, b]);

  const set = (slot: "a" | "b") => (p: { player_id: number }) => {
    const n = new URLSearchParams(sp);
    n.set(slot, String(p.player_id));
    setSp(n);
  };
  const clear = (slot: "a" | "b") => { const n = new URLSearchParams(sp); n.delete(slot); setSp(n); };

  const example = async ([x, y]: [string, string]) => {
    const [px, py] = await Promise.all([api.search(x, 1), api.search(y, 1)]);
    if (px[0] && py[0]) setSp({ a: String(px[0].player_id), b: String(py[0].player_id) });
  };

  const c = conn.data;
  return (
    <>
      <h1>Connections</h1>
      <p className="lede">
        Two players are linked if they shared a club in the same season. Pick any two and see the shortest
        chain of teammates between them, like six degrees of Kevin Bacon.
      </p>

      <div className="pickers">
        {([["a", a, nameA.data], ["b", b, nameB.data]] as const).map(([slot, id, name]) => (
          <div className="picker" key={slot}>
            {id !== null && name ? (
              <div className="picked">
                <Link to={`/player/${id}`} className="player-link">{name}</Link>
                <button className="link-btn" onClick={() => clear(slot)}>Change</button>
              </div>
            ) : (
              <SearchBox label={slot === "a" ? "From" : "To"} placeholder={slot === "a" ? "Search a player" : "Search another player"} onSelect={set(slot)} />
            )}
          </div>
        ))}
      </div>

      <p className="examples">
        Try:{" "}
        {EXAMPLES.map((e) => (
          <button key={e.join()} className="chip" onClick={() => example(e)}>{e[0]} and {e[1]}</button>
        ))}
      </p>

      {a === null || b === null ? <Empty>Choose two players to find the link between them.</Empty> : null}
      {conn.loading && a !== null && b !== null && <Loading label="Searching the teammate graph" />}
      {conn.error && <ErrorBox message={conn.error} />}

      {c && c.separation === null && (
        <Empty>These two players aren't connected through any chain of teammates in this data.</Empty>
      )}
      {c && c.separation !== null && (
        <section className="block" aria-live="polite">
          <h2>
            {c.separation === 0 ? "That's the same player" :
              c.separation === 1 ? "Teammates: 1 step apart" : `${c.separation} steps apart`}
          </h2>
          <ol className="chain">
            {c.path.map((s, i) => (
              <Fragment key={i}>
                {s.type === "player" ? (
                  <li className="chain-player">
                    <Link to={`/player/${s.player_id}`} className="player-link">{s.name}</Link>
                    <span className="sub">{s.sub_position ?? s.position}, {LEAGUES[s.league] ?? s.league}, {eur(s.market_value_eur)}</span>
                  </li>
                ) : (
                  <li className="chain-club" aria-label="played together at">
                    <span>{clubLabel(s)}</span>
                    <span className="sub">{seasonLabel(s.season)}</span>
                  </li>
                )}
              </Fragment>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}
