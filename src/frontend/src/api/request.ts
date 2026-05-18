const BASE = '/api'

export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`${response.status}: ${await response.text()}`)
  }
  return response.json()
}
