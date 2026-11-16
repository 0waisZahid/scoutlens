/** Monogram avatar tinted by position. A photo URL can be passed later without changing callers. */
export function Avatar({ name, pos, size = "md", photo }: { name: string; pos: string; size?: "sm" | "md" | "xl"; photo?: string | null }) {
  const words = name.replace(/[^\p{L}\s-]/gu, "").split(/[\s-]+/).filter(Boolean);
  const initials = ((words[0]?.[0] ?? "") + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
  return (
    <span className={`avatar avatar-${size} pos-${pos}`} aria-hidden="true">
      {photo ? <img src={photo} alt="" /> : initials}
    </span>
  );
}
