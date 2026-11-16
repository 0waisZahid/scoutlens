import { useWatchlist } from "../hooks";

export function StarButton({ id, name, withLabel = false }: { id: number; name: string; withLabel?: boolean }) {
  const { has, toggle } = useWatchlist();
  const saved = has(id);
  return (
    <button
      type="button"
      className={`star${saved ? " is-saved" : ""}${withLabel ? " star-label" : ""}`}
      aria-pressed={saved}
      aria-label={saved ? `Remove ${name} from watchlist` : `Add ${name} to watchlist`}
      title={saved ? "Remove from watchlist" : "Add to watchlist"}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggle({ id, name }); }}
    >
      <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
        <path d="M10 2.5l2.2 4.8 5.3.6-3.9 3.6 1.1 5.2L10 14l-4.7 2.7 1.1-5.2L2.5 7.9l5.3-.6z"
          fill={saved ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
      {withLabel && <span>{saved ? "On watchlist" : "Add to watchlist"}</span>}
    </button>
  );
}
