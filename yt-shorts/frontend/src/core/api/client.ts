const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createSSEStream(path: string): [EventSource, () => void] {
  const es = new EventSource(`${BASE_URL}${path}`);
  return [es, () => es.close()];
}
