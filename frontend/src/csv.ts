export function csvCell(value: string | number | null): string {
  const original = value === null ? "" : String(value);
  const safe = /^[=+\-@\t\r]/.test(original) ? `'${original}` : original;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}
