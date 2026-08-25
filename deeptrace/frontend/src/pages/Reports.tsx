import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, reportUrl } from "../api";
import Stamp from "../components/Stamp";
import { Lang, t } from "../i18n";

export default function Reports({ lang }: { lang: Lang }) {
  const [rows, setRows] = useState<any[] | null>(null);
  const nav = useNavigate();
  useEffect(() => {
    api.reports().then(setRows);
  }, []);
  if (!rows) return <div className="page">Loading annexures…</div>;
  return (
    <div className="page">
      <div className="eyebrow">BSA 2023 · s.63</div>
      <h1 className="page-title">{t(lang, "annex")}</h1>
      <p className="sub">HMAC-signed PDFs ready to annex to an FIR or GD. Each file seals case ID, exhibit hash, and verdict.</p>
      {rows.length === 0 ? (
        <p className="sub">{t(lang, "noReports")}</p>
      ) : (
        <table className="queue">
          <thead>
            <tr>
              <th>ID</th>
              <th>{t(lang, "title")}</th>
              <th>{t(lang, "verdict")}</th>
              <th>HMAC</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} onClick={() => nav(`/app/cases/${r.case_id}`)}>
                <td className="pid">{r.public_id}</td>
                <td>{r.title}</td>
                <td>
                  <Stamp v={r.verdict} lang={lang} />
                </td>
                <td className="pid">{r.signature?.slice(0, 16)}…</td>
                <td>
                  <a className="btn btn-ghost" href={reportUrl(r.id)} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                    {t(lang, "download")}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
