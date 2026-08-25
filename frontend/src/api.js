export async function fetchLeads() {
  const res = await fetch("/api/leads");
  if (!res.ok) throw new Error("failed to load leads");
  return res.json();
}

export async function fetchLead(id) {
  const res = await fetch(`/api/leads/${id}`);
  if (!res.ok) throw new Error("failed to load lead");
  return res.json();
}

export async function fetchBudget() {
  const res = await fetch("/api/budget");
  if (!res.ok) throw new Error("failed to load budget");
  return res.json();
}

export async function fetchStats() {
  const res = await fetch("/api/stats");
  if (!res.ok) return { raw_tokens: 0, brief_tokens: 0, saved_pct: 0, brief_count: 0 };
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch("/api/settings");
  if (!res.ok) return { send_mode: "dry_run" };
  return res.json();
}

export async function setSendMode(send_mode) {
  const res = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ send_mode }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "could not update send mode");
  return data;
}

export async function simulateReply(id, body) {
  const res = await fetch(`/api/leads/${id}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "reply failed");
  return data;
}

export async function fetchCampaigns() {
  const res = await fetch("/api/campaigns");
  if (!res.ok) throw new Error("failed to load campaigns");
  return res.json();
}

export async function runPipeline({ problem, campaign_id, limit, demo, onEvent }) {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem, campaign_id, limit, demo }),
  });
  if (!res.ok || !res.body) {
    throw new Error("run failed to start");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {
        // ignore malformed chunks
      }
    }
  }
}
