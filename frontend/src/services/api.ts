import axios from "axios";

export const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export function getWebSocketSessionUrl(sessionId: number) {
  const token = localStorage.getItem("token");
  const baseApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
  const wsBaseUrl = baseApiUrl
    .replace(/^http:\/\//, "ws://")
    .replace(/^https:\/\//, "wss://")
    .replace(/\/api\/?$/, "");

  const url = new URL(`${wsBaseUrl}/ws/sessions/${sessionId}/`);
  if (token) {
    url.searchParams.set("token", token);
  }
  return url.toString();
}
