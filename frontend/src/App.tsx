import { useState } from "react";

type Status = { kind: "idle" } | { kind: "ok"; text: string } | { kind: "err"; text: string };

/** Production API origin when the SPA is not served by FastAPI (e.g. Vercel → API on Railway). Leave unset for dev (Vite proxy) or same-origin deploys. */
function apiUrl(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

async function postJson(path: string, body: object): Promise<{ message?: string }> {
  const r = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data: unknown = {};
  try {
    data = await r.json();
  } catch {
    /* ignore */
  }
  if (!r.ok) {
    const d = data as { detail?: unknown };
    const detail = d.detail;
    let msg: string;
    if (Array.isArray(detail)) {
      msg = detail.map((x: { msg?: string }) => x.msg ?? "").filter(Boolean).join(", ");
    } else if (typeof detail === "string") {
      msg = detail;
    } else {
      msg = r.statusText;
    }
    throw new Error(msg || "Request failed");
  }
  return data as { message?: string };
}

export default function App() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [loading, setLoading] = useState<null | "subscribe" | "demo">(null);

  const payload = () => ({
    email: email.trim(),
    first_name: firstName.trim(),
    last_name: lastName.trim(),
  });

  async function handleSubscribe() {
    setStatus({ kind: "idle" });
    setLoading("subscribe");
    try {
      const data = await postJson("/subscribe", payload());
      setStatus({ kind: "ok", text: data.message ?? "You're subscribed." });
    } catch (e) {
      setStatus({ kind: "err", text: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      setLoading(null);
    }
  }

  async function handleDemo() {
    setStatus({ kind: "idle" });
    setLoading("demo");
    try {
      const data = await postJson("/demo", payload());
      setStatus({ kind: "ok", text: data.message ?? "Sample sent." });
    } catch (e) {
      setStatus({ kind: "err", text: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      setLoading(null);
    }
  }

  const busy = loading !== null;

  return (
    <div className="page">
      <div className="glow" aria-hidden />
      <main className="card">
        <p className="eyebrow">Portfolio demo</p>
        <h1>Daily AI News Digest</h1>
        <p className="lede">
          Curated updates from public feeds—subscribe for the daily run, or request a one-time sample
          to your inbox.
        </p>

        <div className="fields">
          <label>
            <span>First name</span>
            <input
              type="text"
              name="first_name"
              autoComplete="given-name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              disabled={busy}
            />
          </label>
          <label>
            <span>Last name</span>
            <input
              type="text"
              name="last_name"
              autoComplete="family-name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              disabled={busy}
            />
          </label>
          <label>
            <span>Email</span>
            <input
              type="email"
              name="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
            />
          </label>
        </div>

        <div className="actions">
          <button
            type="button"
            className="btn primary"
            onClick={handleSubscribe}
            disabled={busy || !email.trim()}
          >
            {loading === "subscribe" ? "Working…" : "Subscribe to Daily Digest"}
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={handleDemo}
            disabled={busy || !email.trim()}
          >
            {loading === "demo" ? "Sending…" : "Send Sample Digest"}
          </button>
        </div>

        {status.kind === "ok" && (
          <p className="banner ok" role="status">
            {status.text}
          </p>
        )}
        {status.kind === "err" && (
          <p className="banner err" role="alert">
            {status.text}
          </p>
        )}
      </main>
    </div>
  );
}
