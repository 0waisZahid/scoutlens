import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../components/Icons";
import { Rail } from "../components/Rail";
import { SearchBox } from "../components/SearchBox";
import { LEAGUES } from "../format";
import { useTitle } from "../hooks";

export default function Home() {
  useTitle("");
  const nav = useNavigate();
  const [league, setLeague] = useState("");
  return (
    <>
      <section className="home-hero">
        <h1>Know what a player is really worth</h1>
        <p>Model valuations that show their uncertainty, for five leagues from 2012 to 2025.</p>
        <SearchBox label="Search a player" hideLabel placeholder="Search a player, for example Haaland or Yamal"
          className="search-hero" onSelect={(p) => nav(`/player/${p.player_id}`)} />
      </section>

      <div className="leaguebar" role="group" aria-label="Filter the rows below by league">
        <button className={`chip${league === "" ? " is-on" : ""}`} aria-pressed={league === ""} onClick={() => setLeague("")}>All leagues</button>
        {Object.entries(LEAGUES).map(([k, v]) => (
          <button key={k} className={`chip${league === k ? " is-on" : ""}`} aria-pressed={league === k} onClick={() => setLeague(k)}>{v}</button>
        ))}
      </div>

      <Rail title="Undervalued by the model" sub="Where the model's estimate is furthest above the market value" sort="undervalued" league={league} more="/explore?sort=undervalued" />
      <Rail title="Projected risers" sub="Biggest expected gains next season" sort="risers" league={league} more="/explore?sort=risers" />
      <Rail title="Rising talents" sub="Under 21, by market value" sort="young" league={league} more="/explore?sort=young" />
      <Rail title="Most valuable" sub="Highest market values in the latest season" sort="value" league={league} more="/explore?sort=value" />

      <section className="tools" aria-label="Tools">
        <Link to="/compare" className="tool"><Icon name="compare" /><div><strong>Compare two players</strong><span>Values, forecast and profile side by side</span></div></Link>
        <Link to="/connect" className="tool"><Icon name="connect" /><div><strong>Find the connection</strong><span>The shortest chain of teammates between any two players</span></div></Link>
        <Link to="/method" className="tool"><Icon name="explore" /><div><strong>How it works</strong><span>Accuracy, ranges and where the model is weak</span></div></Link>
      </section>
    </>
  );
}
