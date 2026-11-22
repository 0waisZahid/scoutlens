export function securePhotoUrl(template: string | undefined, id: number): string | null {
  if (!template) return null;
  try {
    const url = new URL(template.replace(/\{id\}/g, encodeURIComponent(String(id))));
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}
