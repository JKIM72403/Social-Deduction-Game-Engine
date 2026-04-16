import axios from "axios";

function getDefaultApiUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000/api";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000/api`;
}

export const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || getDefaultApiUrl(),
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
  const baseApiUrl = import.meta.env.VITE_API_URL || getDefaultApiUrl();
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
