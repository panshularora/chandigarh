import { Lang, t } from "../i18n";

export default function Station({ lang }: { lang: Lang }) {
  const blocks = [t(lang, "sop1"), t(lang, "sop2"), t(lang, "sop3"), t(lang, "sop4")];
  return (
    <div className="page">
      <div className="eyebrow">Chandigarh Police Hackathon 2026 · PS4</div>
      <h1 className="page-title">{t(lang, "sop")}</h1>
      <p className="sub">{t(lang, "sopLead")}</p>
      <ul className="spine sop-spine">
        {blocks.map((text) => (
          <li key={text.slice(0, 24)}>
            <p>{text}</p>
          </li>
        ))}
      </ul>
      <div className="paper-form" style={{ marginTop: 28 }}>
        <div className="eyebrow" style={{ color: "#c65a1a" }}>
          Pilot
        </div>
        <h2 style={{ fontFamily: "var(--display)", letterSpacing: "0.04em", margin: "6px 0 12px" }}>
          Cyber Cell, 30-day station trial
        </h2>
        <p>
          Week 1 — install on two Cyber Cell laptops, offline. Week 2 — run live digital-arrest and voice-clone exhibits
          beside existing SOPs. Week 3 — annex signed PDFs to two test FIRs. Week 4 — SP Cyber review; ONNX detector pack
          if the heuristic ensemble holds.
        </p>
        <p className="hint">{t(lang, "team")}</p>
      </div>
    </div>
  );
}
