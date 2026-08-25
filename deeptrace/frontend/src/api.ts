const TOKEN_KEY = "dt_token";

export function token(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function req(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const tok = token();
  if (tok) headers.set("Authorization", `Bearer ${tok}`);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    setToken(null);
    if (!path.includes("/auth/login")) window.location.href = "/";
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail || JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(typeof msg === "string" ? msg : "Request failed");
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

export const api = {
  login: (username: string, password: string) =>
    req("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => req("/api/me"),
  dashboard: () => req("/api/dashboard"),
  cases: () => req("/api/cases"),
  createCase: (body: unknown) => req("/api/cases", { method: "POST", body: JSON.stringify(body) }),
  case: (id: number) => req(`/api/cases/${id}`),
  upload: (caseId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req(`/api/cases/${caseId}/evidence`, { method: "POST", body: fd });
  },
  analyze: (evidenceId: number) => req(`/api/evidence/${evidenceId}/analyze`, { method: "POST" }),
  briefing: (analysisId: number) =>
    req(`/api/analyses/${analysisId}/briefing`, { method: "POST", body: JSON.stringify({ use_grok: true }) }),
  report: (analysisId: number) => req(`/api/analyses/${analysisId}/report`, { method: "POST" }),
  reports: () => req("/api/reports"),
  audit: () => req("/api/audit"),
};

export function mediaUrl(kind: string, name: string) {
  const tok = token();
  const q = tok ? `?access_token=${encodeURIComponent(tok)}` : "";
  return `/api/media/${kind}/${encodeURIComponent(name)}${q}`;
}
export function reportUrl(id: number) {
  const tok = token();
  const q = tok ? `?access_token=${encodeURIComponent(tok)}` : "";
  return `/api/reports/${id}/file${q}`;
}

export function authHeaders(): HeadersInit {
  const tok = token();
  return tok ? { Authorization: `Bearer ${tok}` } : {};
}
