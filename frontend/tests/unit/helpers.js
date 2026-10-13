// Minimal fetch Response stand-in for tests.
export function res(status, body, headers = {}) {
  const text = typeof body === 'string' ? body : JSON.stringify(body)
  return { ok: status >= 200 && status < 300, status, headers: { get: (k) => headers[k.toLowerCase()] ?? null }, text: async () => text }
}
export const errBody = (code, message, details = {}, request_id = 'rid123') => ({ error: { code, message, details, request_id } })
