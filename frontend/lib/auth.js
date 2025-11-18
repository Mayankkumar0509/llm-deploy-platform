import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function isLoggedIn() {
  const token = localStorage.getItem("token");
  if (!token) return false;

  try {
    await axios.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return true;
  } catch (err) {
    // token invalid → logout user
    localStorage.removeItem("token");
    return false;
  }
}

export function clearToken() {
  localStorage.removeItem("token");
}
