import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { api } from "../api";
import Stamp from "../components/Stamp";
import { Lang, t } from "../i18n";

gsap.registerPlugin(useGSAP);

export default function Dashboard({ lang }: { lang: Lang }) {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");
  const nav = useNavigate();
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setErr(e.message));
  }, []);

  useGSAP(
    () => {
      if (!data) return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.from(".strip div", { opacity: 0, y: 10, stagger: 0.05, duration: 0.4, ease: "power2.out" });
      gsap.from(".queue tbody tr", { opacity: 0, y: 8, stagger: 0.04, duration: 0.35, ease: "power2.out" });
    },
    { scope: root, dependencies: [data] },
  );

  if (err) return <div className="page err">{err}</div>;
  if (!data) return <div className="page">Loading duty desk…</div>;
  const k = data.kpis;

  return (
    <div className="page" ref={root}>
      <div className="eyebrow">{t(lang, "product")} · UT Chandigarh</div>
      <h1 className="page-title">{t(lang, "dash")}</h1>
      <p className="sub">{t(lang, "dashSub")}</p>
      <div className="strip">
        {[
          [k.open_cases, t(lang, "open")],
          [k.exhibits, t(lang, "exhibits")],
          [k.ai_flagged, t(lang, "flagged")],
          [k.reports, t(lang, "reports")],
          [k.p1_queue, t(lang, "p1")],
        ].map(([n, l]) => (
          <div key={String(l)}>
            <div className="n">{n}</div>
            <div className="l">{l}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ fontFamily: "var(--display)", letterSpacing: "0.08em", fontSize: 22 }}>{t(lang, "queue")}</h2>
        <button className="btn btn-saffron" onClick={() => nav("/app/cases/new")}>
          {t(lang, "newCase")}
        </button>
      </div>
      <table className="queue">
        <thead>
          <tr>
            <th>ID</th>
            <th>{t(lang, "title")}</th>
            <th>{t(lang, "offence")}</th>
            <th>{t(lang, "priority")}</th>
            <th>{t(lang, "verdict")}</th>
            <th>FIR</th>
          </tr>
        </thead>
        <tbody>
          {data.queue.map((c: any) => (
            <tr key={c.id} onClick={() => nav(`/app/cases/${c.id}`)}>
              <td className="pid">{c.public_id}</td>
              <td>{c.title}</td>
              <td>{t(lang, c.offence_type) || c.offence_type}</td>
              <td className={c.priority === "P1" ? "p1" : "p2"}>{c.priority}</td>
              <td>
                <Stamp v={c.latest_verdict} lang={lang} />
              </td>
              <td className="pid">{c.fir_number}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
