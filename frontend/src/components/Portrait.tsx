import { useState } from "react";
import { photoUrl } from "../format";

/** Pitch-line plates: four variants picked by id so a grid of fallbacks never looks cloned. */
function Plate({ initials, variant }: { initials: string; variant: number }) {
  const cx = [50, 0, 100, 50][variant];
  const cy = [118, 125, 125, 20][variant];
  return (
    <svg className="portrait-art" viewBox="0 0 100 125" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.5">
        <circle cx={cx} cy={cy} r="34" />
        <circle cx={cx} cy={cy} r="2" fill="currentColor" />
        <path d={variant === 3 ? "M0 20H100" : "M0 118H100"} />
        <rect x="22" y={variant === 3 ? 20 : 92} width="56" height="26" opacity="0.6" />
      </g>
      <text x="50" y="76" textAnchor="middle" className="portrait-initials">{initials}</text>
    </svg>
  );
}

export function Portrait({ id, name, pos, size = "md" }: { id: number; name: string; pos?: string; size?: "xs" | "sm" | "md" | "lg" | "fill" }) {
  const [broken, setBroken] = useState(false);
  const src = photoUrl(id);
  const words = name.replace(/[^\p{L}\s-]/gu, "").split(/[\s-]+/).filter(Boolean);
  const initials = ((words[0]?.[0] ?? "") + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
  return (
    <span className={`portrait portrait-${size}`} aria-hidden="true">
      {src && !broken
        ? <img src={src} alt="" loading="lazy" onError={() => setBroken(true)} />
        : <Plate initials={initials} variant={id % 4} />}
      {pos && size !== "xs" && size !== "sm" && <span className="portrait-pos">{pos}</span>}
    </span>
  );
}
