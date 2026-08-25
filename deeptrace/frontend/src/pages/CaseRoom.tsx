import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, mediaUrl, reportUrl } from "../api";
import Stamp from "../components/Stamp";
import { Lang, t } from "../i18n";

export default function CaseRoom({ lang }: { lang: Lang }) {
  const { id } = useParams();
  const [pack, setPack] = useState<any>(null);
  const [heat, setHeat] = useState(0.55);
  const [busy, setBusy] = useState("");
  const [stage, setStage] = useState(0);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState<number | null>(null);
  const [hover, setHover] = useState(false);

  async function load() {
    const p = await api.case(Number(id));
    setPack(p);
    setSel((prev) => prev ?? p.evidence?.[0]?.id ?? null);
  }
  useEffect(() => {
    setSel(null);
    setStage(0);
    setPack(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const evidence = pack?.evidence?.find((e: any) => e.id === sel) || pack?.evidence?.[0];
  const analysis = useMemo(() => {
    if (!pack || !evidence) return null;
    return pack.analyses.find((a: any) => a.evidence_id === evidence.id) || null;
  }, [pack, evidence]);

  async function onFile(file: File) {
    setErr("");
    setBusy("ingest");
    setStage(1);
    try {
      const ev = await api.upload(Number(id), file);
      setSel(ev.id);
      await load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  }

  async function run() {
    if (!evidence) return;
    setErr("");
    setBusy("analyze");
    setStage(1);
    const timers = [2, 3, 4].map((s, i) => setTimeout(() => setStage(s), 420 * (i + 1)));
    try {
      await api.analyze(evidence.id);
      await load();
      setStage(4);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      timers.forEach(clearTimeout);
      setBusy("");
    }
  }

  async function brief() {
    if (!analysis) return;
    setBusy("brief");
    try {
      await api.briefing(analysis.id);
      await load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  }

  async function sign() {
    if (!analysis) return;
    setBusy("sign");
    try {
      await api.report(analysis.id);
      await load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  }

  if (!pack) return <div className="page">Opening case file…</div>;
  const c = pack.case;
  const overlay = analysis?.overlay_name ? mediaUrl("heatmaps", analysis.overlay_name) : "";
  const original = evidence ? mediaUrl("uploads", evidence.stored_name) : "";
  const heatOnly = analysis?.heatmap_name ? mediaUrl("heatmaps", analysis.heatmap_name) : "";
  const report = pack.reports?.find((r: any) => r.analysis_id === analysis?.id) || pack.reports?.[0];
  const stages = [t(lang, "ingesting"), t(lang, "detect"), t(lang, "tracing"), t(lang, "explain")];
  const activeStage = analysis && !busy ? 4 : stage;

  return (
    <div className="room">
      <section className="table">
        <div className="table-head">
          <div>
            <div className="eyebrow">
              {c.public_id} · {c.fir_number || "No FIR yet"}
            </div>
            <h1>{c.title}</h1>
            <div className="sub" style={{ margin: "6px 0 0" }}>
              {t(lang, c.offence_type)} · {c.station} · {c.priority}
            </div>
          </div>
          {analysis && <Stamp v={analysis.verdict} lang={lang} />}
        </div>

        <div className="pipeline" aria-label="Forensic pipeline">
          {stages.map((label, i) => (
            <div key={label} className={activeStage >= i + 1 ? "on" : ""}>
              <div className="k">{label}</div>
            </div>
          ))}
        </div>

        <div className="stage">
          {busy === "analyze" && <div className="veil">{t(lang, "analyzing")}</div>}
          {evidence && evidence.media_type === "image" && original ? (
            <div className="light">
              <img src={original} alt="exhibit" />
              {overlay && <img className="over" src={overlay} alt="manipulation overlay" style={{ opacity: heat }} />}
            </div>
          ) : evidence && evidence.media_type === "audio" ? (
            <div className="empty">
              <audio controls src={original} />
              {heatOnly && <img src={heatOnly} alt="spectral heatmap" style={{ height: 180, marginTop: 16 }} />}
            </div>
          ) : evidence && evidence.media_type === "video" ? (
            <div className="light">
              <video controls src={original} />
              {overlay && <img className="over" src={overlay} alt="frame overlay" style={{ opacity: heat, pointerEvents: "none" }} />}
            </div>
          ) : (
            <div className="empty">{t(lang, "noHeat")}</div>
          )}
        </div>

        {overlay && (
          <div className="heat-ctrl">
            <span>{t(lang, "heat")}</span>
            <input type="range" min={0} max={1} step={0.01} value={heat} onChange={(e) => setHeat(Number(e.target.value))} />
            <span>{Math.round(heat * 100)}%</span>
          </div>
        )}

        <label
          className={`drop ${hover ? "over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setHover(true);
          }}
          onDragLeave={() => setHover(false)}
          onDrop={(e) => {
            e.preventDefault();
            setHover(false);
            const f = e.dataTransfer.files?.[0];
            if (f) onFile(f);
          }}
        >
          {hover ? t(lang, "drag") : t(lang, "drop")}
          <input type="file" accept="image/*,video/*,audio/*" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
        </label>

        <div className="actions">
          {pack.evidence?.map((e: any) => (
            <button key={e.id} className={`btn btn-ghost ${e.id === evidence?.id ? "on" : ""}`} onClick={() => setSel(e.id)}>
              {e.filename}
            </button>
          ))}
        </div>
        <div className="actions">
          <button className="btn btn-saffron" disabled={!evidence || !!busy} onClick={run}>
            {busy === "analyze" ? "…" : t(lang, "analyze")}
          </button>
          <button className="btn btn-ghost" disabled={!analysis || !!busy} onClick={brief}>
            {busy === "brief" ? "…" : t(lang, "brief")}
          </button>
          <button className="btn btn-ghost" disabled={!analysis || !!busy} onClick={sign}>
            {busy === "sign" ? "…" : t(lang, "sign")}
          </button>
          {report && (
            <a className="btn btn-ghost" href={reportUrl(report.id)} target="_blank" rel="noreferrer">
              {t(lang, "download")}
            </a>
          )}
        </div>
        {evidence && (
          <div className="pid">
            {t(lang, "sha")} {evidence.sha256}
          </div>
        )}
        {err && <div className="err">{err}</div>}
        {c.summary && <p className="sub">{c.summary}</p>}
      </section>

      <aside className="panel">
        <div className="verdict-block">
          <h3>{t(lang, "confidence")}</h3>
          <div className="big">{analysis ? <Stamp v={analysis.verdict} lang={lang} /> : "—"}</div>
          {analysis && (
            <>
              <div className="meter">
                <i style={{ width: `${analysis.confidence}%`, background: analysis.verdict === "REAL" ? "var(--green)" : "var(--saffron)" }} />
              </div>
              <div className="pid">
                {analysis.confidence}% · {t(lang, "likelihood")} {analysis.ai_likelihood}
              </div>
            </>
          )}
        </div>

        <h3>{t(lang, "rationale")}</h3>
        {(analysis?.signals || []).map((s: any) => (
          <div className="sig" key={s.code + s.weight}>
            <span className={`w ${s.weight < 0 ? "neg" : ""}`}>
              {s.weight > 0 ? "+" : ""}
              {s.weight}
            </span>
            <span className="c"> {s.code}</span>
            <p>{s.rationale}</p>
          </div>
        ))}
        {!analysis && <p className="sub">{t(lang, "noHeat")}</p>}

        <h3 style={{ marginTop: 22 }}>{t(lang, "source")}</h3>
        <Provenance graph={analysis?.provenance} generators={analysis?.generators} />

        {analysis?.briefing && (
          <>
            <h3>{t(lang, "brief")}</h3>
            <div className="brief">{analysis.briefing}</div>
          </>
        )}

        <h3 style={{ marginTop: 22 }}>{t(lang, "custody")}</h3>
        <ul className="spine">
          {pack.custody.map((ev: any) => (
            <li key={ev.id}>
              <time>
                {ev.timestamp?.replace("T", " ").slice(0, 19)} · {ev.operator}
              </time>
              <b>{ev.action}</b>
              <div>{ev.detail}</div>
              <div className="hash">{ev.event_hash}</div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

function Provenance({ graph, generators }: { graph?: any; generators?: any[] }) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const placed = nodes.map((n: any, i: number) => {
    const angle = (i / Math.max(nodes.length, 1)) * Math.PI * 1.2 - 0.4;
    return { ...n, x: 150 + Math.cos(angle) * 90, y: 85 + Math.sin(angle) * 52 };
  });
  const byId: Record<string, any> = Object.fromEntries(placed.map((n: any) => [n.id, n]));
  return (
    <div className="graph">
      <div className="pid" style={{ marginBottom: 8 }}>
        {generators?.length ? generators.map((g: any) => g.generator).join(" · ") : "No generator metadata hit"}
      </div>
      <svg viewBox="0 0 300 170">
        {edges.map((e: any, i: number) => {
          const a = byId[e.from];
          const b = byId[e.to];
          if (!a || !b) return null;
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#7eb6c9" strokeOpacity="0.5" />;
        })}
        {placed.map((n: any) => (
          <g key={n.id}>
            <circle cx={n.x} cy={n.y} r={n.kind === "exhibit" ? 7 : 5} fill={n.kind === "generator" ? "#c65a1a" : "#7eb6c9"} />
            <text x={n.x + 10} y={n.y + 4} fill="#e8e0cc" fontSize="9" fontFamily="IBM Plex Mono">
              {n.label.slice(0, 22)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
