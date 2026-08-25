import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Lang, t } from "../i18n";

export default function Audit({ lang }: { lang: Lang }) {
  const [rows, setRows] = useState<any[] | null>(null);
  const nav = useNavigate();
  useEffect(() => {
    api.audit().then(setRows);
  }, []);
  if (!rows) return <div className="page">Loading custody chain…</div>;
  return (
    <div className="page">
      <div className="eyebrow">Immutable log</div>
      <h1 className="page-title">{t(lang, "audit")}</h1>
      <p className="sub">Every ingest, analysis and signature is hash-chained. A broken prev-hash is detectable.</p>
      {rows.length === 0 ? (
        <p className="sub">{t(lang, "noAudit")}</p>
      ) : (
        <table className="queue">
          <thead>
            <tr>
              <th>{t(lang, "when")}</th>
              <th>ID</th>
              <th>{t(lang, "action")}</th>
              <th>Operator</th>
              <th>Event hash</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id} onClick={() => e.case_id && nav(`/app/cases/${e.case_id}`)}>
                <td className="pid">{e.timestamp?.replace("T", " ").slice(0, 19)}</td>
                <td className="pid">{e.public_id}</td>
                <td>
                  <b>{e.action}</b>
                  <div className="sub" style={{ margin: "4px 0 0" }}>
                    {e.detail}
                  </div>
                </td>
                <td>{e.operator}</td>
                <td className="pid">{e.event_hash?.slice(0, 20)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
