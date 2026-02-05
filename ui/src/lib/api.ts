export const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

export async function getModels() {
  const response = await fetch(`${API_BASE}/models`);
  if (!response.ok) {
    throw new Error("Failed to load models");
  }
  return response.json();
}

export async function getConfig() {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) {
    throw new Error("Failed to load config");
  }
  return response.json();
}

export async function updateConfig(config: unknown) {
  const response = await fetch(`${API_BASE}/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error("Failed to update config");
  }
  return response.json();
}

export async function sendChat(payload: unknown) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const err = new Error(error.detail ?? "Chat failed");
    (err as Error & { detail?: unknown }).detail = error.detail;
    throw err;
  }
  return response.json();
}

export function openChatStream(payload: unknown) {
  const socket = new WebSocket(`${API_BASE.replace("http", "ws")}/ws/chat`);
  socket.addEventListener("open", () => {
    socket.send(JSON.stringify(payload));
  });
  return socket;
}

export async function getAuditLogs(tail = 200) {
  const response = await fetch(`${API_BASE}/logs/audit?tail=${tail}`);
  if (!response.ok) {
    throw new Error("Failed to load audit logs");
  }
  return response.json();
}

export async function getDreamLogs(tail = 50) {
  const response = await fetch(`${API_BASE}/logs/dreams?tail=${tail}`);
  if (!response.ok) {
    throw new Error("Failed to load dream logs");
  }
  return response.json();
}

export async function getReflectionLogs(tail = 50) {
  const response = await fetch(`${API_BASE}/logs/reflections?tail=${tail}`);
  if (!response.ok) {
    throw new Error("Failed to load reflection logs");
  }
  return response.json();
}

export async function runSkill(payload: unknown) {
  const response = await fetch(`${API_BASE}/skills/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const err = new Error(error.detail ?? "Skill failed");
    (err as Error & { detail?: unknown }).detail = error.detail;
    throw err;
  }
  return response.json();
}
