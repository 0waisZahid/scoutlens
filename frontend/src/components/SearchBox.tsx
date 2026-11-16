import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { eur, LEAGUES, posCode } from "../format";
import { Avatar } from "./Avatar";
import { useDebounced } from "../hooks";
import type { Summary } from "../types";

interface Props {
  onSelect: (p: Summary) => void;
  placeholder?: string;
  label: string;
  /** hide the visible label (e.g. in the header) */
  hideLabel?: boolean;
  autoFocus?: boolean;
  className?: string;
}

/** Autocomplete over the API's trie-backed search. Arrow keys, Enter and Escape work. */
export function SearchBox({ onSelect, placeholder = "Search a player", label, hideLabel, autoFocus, className }: Props) {
  const id = useId();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Summary[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const term = useDebounced(q.trim(), 140);

  useEffect(() => {
    if (!term) { setResults([]); setPending(false); setError(null); return; }
    const ctl = new AbortController();
    setPending(true);
    api.search(term, 8, ctl.signal).then(
      (r) => { setResults(r); setActive(0); setError(null); setPending(false); },
      (e: Error) => { if (e.name !== "AbortError") { setError(e.message); setPending(false); } },
    );
    return () => ctl.abort();
  }, [term]);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const choose = (p: Summary) => { setOpen(false); setQ(""); setResults([]); onSelect(p); };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter" && open && results[active]) { e.preventDefault(); choose(results[active]); }
    else if (e.key === "Escape") setOpen(false);
  };

  const showList = open && term.length > 0;
  return (
    <div className={`search ${className ?? ""}`} ref={wrap}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : "field-label"}>{label}</label>
      <input
        id={id}
        type="search"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={showList && results[active] ? `${id}-opt-${active}` : undefined}
        autoComplete="off"
        autoFocus={autoFocus}
        placeholder={placeholder}
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
      />
      {showList && (
        <ul className="search-list" id={`${id}-list`} role="listbox">
          {error && <li className="search-note" role="presentation">{error}</li>}
          {!error && !pending && results.length === 0 && (
            <li className="search-note" role="presentation">No player starts with “{term}”. Try a first name or surname.</li>
          )}
          {results.map((p, i) => (
            <li
              key={p.player_id}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "is-active" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => { e.preventDefault(); choose(p); }}
            >
              <Avatar name={p.name} pos={posCode(p.position)} size="sm" />
              <span className="search-name">{p.name}</span>
              <span className="search-meta">{p.position}, {LEAGUES[p.league] ?? p.league}, {Math.round(p.age)}</span>
              <span className="search-value">{eur(p.latest_value_eur)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
