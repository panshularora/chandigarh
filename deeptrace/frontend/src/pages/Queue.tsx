import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Stamp from "../components/Stamp";
import { Lang, t } from "../i18n";

export default function Queue({ lang }: { lang: Lang }) {
  const [rows, setRows] = useState<any[] | null>(null);
  const nav = useNavigate();
  useEffect(() => {
    api.cases().then(setRows);
  }, []);
  if (!rows) return <div className="page">Loading files…</div>;
  return (
    <div className="page">
      <div className="eyebrow">Cyber Cell</div>
      <h1 className="page-title">{t(lang, "cases")}</h1>
      <table className="queue">
        <thead>
          <tr>
            <th>ID</th>
            <th>{t(lang, "title")}</th>
            <th>{t(lang, "offence")}</th>
            <th>{t(lang, "priority")}</th>
            <th>{t(lang, "verdict")}</th>
            <th>{t(lang, "exhibits")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} onClick={() => nav(`/app/cases/${c.id}`)}>
              <td className="pid">{c.public_id}</td>
              <td>{c.title}</td>
              <td>{t(lang, c.offence_type) || c.offence_type}</td>
              <td className={c.priority === "P1" ? "p1" : "p2"}>{c.priority}</td>
              <td>
                <Stamp v={c.latest_verdict} lang={lang} />
              </td>
              <td>{c.evidence_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
