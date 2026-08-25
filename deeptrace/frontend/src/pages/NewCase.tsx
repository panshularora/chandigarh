import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Lang, t } from "../i18n";

export default function NewCase({ lang }: { lang: Lang }) {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    title: "",
    fir_number: "",
    offence_type: "digital_arrest",
    station: "Cyber Cell, Chandigarh",
    priority: "P1",
    summary: "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const c = await api.createCase(form);
      nav(`/app/cases/${c.id}`);
    } catch (ex: any) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <form className="paper-form" onSubmit={submit}>
        <div className="eyebrow" style={{ color: "#c65a1a" }}>
          {t(lang, "docket")}
        </div>
        <h1>{t(lang, "newCase")}</h1>
        <p className="hint">Opens a hash-chained custody file. Attach the exhibit on the next screen.</p>
        <div className="form-grid">
          <label className="field">
            <span>{t(lang, "title")}</span>
            <input required value={form.title} onChange={(e) => set("title", e.target.value)} />
          </label>
          <label className="field">
            <span>{t(lang, "fir")}</span>
            <input value={form.fir_number} onChange={(e) => set("fir_number", e.target.value)} placeholder="FIR 77/2026" />
          </label>
          <label className="field">
            <span>{t(lang, "offence")}</span>
            <select value={form.offence_type} onChange={(e) => set("offence_type", e.target.value)}>
              {["digital_arrest", "blackmail", "investment_scam", "planted_evidence", "other"].map((k) => (
                <option key={k} value={k}>
                  {t(lang, k)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t(lang, "priority")}</span>
            <select value={form.priority} onChange={(e) => set("priority", e.target.value)}>
              <option>P1</option>
              <option>P2</option>
              <option>P3</option>
            </select>
          </label>
        </div>
        <label className="field">
          <span>{t(lang, "station")}</span>
          <input value={form.station} onChange={(e) => set("station", e.target.value)} />
        </label>
        <label className="field">
          <span>{t(lang, "summary")}</span>
          <textarea value={form.summary} onChange={(e) => set("summary", e.target.value)} />
        </label>
        <div className="err">{err}</div>
        <button className="btn btn-ink" disabled={busy}>
          {t(lang, "openCase")}
        </button>
      </form>
    </div>
  );
}
