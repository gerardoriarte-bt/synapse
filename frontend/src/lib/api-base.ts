/**
 * Base URL del API FastAPI (misma convención que useSynapseQuery).
 */
export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw === undefined) {
    return 'http://127.0.0.1:8000';
  }
  if (raw.trim() === '') {
    return '';
  }
  const t = raw.trim();
  return t.startsWith('http') ? t : `https://${t}`;
}
