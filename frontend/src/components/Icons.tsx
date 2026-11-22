const P: Record<string, string> = {
  home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  explore: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17l-5-5",
  compare: "M8 4v16M16 4v16M3 8h5M16 14h5",
  connect: "M6 7a2 2 0 1 0 0-.01M18 7a2 2 0 1 0 0-.01M12 18a2 2 0 1 0 0-.01M7.7 8.4l3.2 7.6M16.3 8.4l-3.2 7.6M8 7h8",
  saved: "M12 3.5l2.6 5.5 6 .7-4.4 4.1 1.2 6L12 16.8 6.6 19.8l1.2-6L3.4 9.7l6-.7z",
};
export function Icon({ name }: { name: keyof typeof P }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[name]} /></svg>
  );
}
