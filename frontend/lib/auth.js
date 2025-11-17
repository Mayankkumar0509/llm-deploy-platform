
const TOKEN_KEY = 'llm_token';

export function saveToken(token) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function removeToken() {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}
