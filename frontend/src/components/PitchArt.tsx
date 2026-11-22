/** Pitch geometry used as quiet backdrop art. Pure line work, no photography needed. */
export function PitchArt({ className = "" }: { className?: string }) {
  return (
    <svg className={`pitch-art ${className}`} viewBox="0 0 400 520" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1.2">
        <rect x="20" y="20" width="360" height="480" rx="4" />
        <path d="M20 260H380" />
        <circle cx="200" cy="260" r="62" />
        <circle cx="200" cy="260" r="3" fill="currentColor" />
        <rect x="95" y="20" width="210" height="92" />
        <rect x="145" y="20" width="110" height="38" />
        <path d="M160 112a48 48 0 0 0 80 0" />
        <rect x="95" y="408" width="210" height="92" />
        <rect x="145" y="462" width="110" height="38" />
        <path d="M160 408a48 48 0 0 1 80 0" />
      </g>
    </svg>
  );
}
