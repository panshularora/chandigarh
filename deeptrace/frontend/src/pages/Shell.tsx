import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Lang, t } from "../i18n";

const LINKS = [
  { to: "/app", end: true, key: "desk", short: "DESK" },
  { to: "/app/cases", end: false, key: "cases", short: "FILE" },
  { to: "/app/cases/new", end: false, key: "newCase", short: "NEW" },
  { to: "/app/reports", end: false, key: "annex", short: "PDF" },
  { to: "/app/audit", end: false, key: "audit", short: "LOG" },
  { to: "/app/station", end: false, key: "sop", short: "SOP" },
] as const;

export default function Shell({
  lang,
  setLang,
  op,
  logout,
}: {
  lang: Lang;
  setLang: (l: Lang) => void;
  op: { station: string; full_name: string; badge_no: string };
  logout: () => void;
}) {
  const [clock, setClock] = useState("");
  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          day: "2-digit",
          month: "short",
        }) + " IST",
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const nav = (
    <>
      {LINKS.map((l) => (
        <NavLink key={l.to} to={l.to} end={l.end} title={t(lang, l.key)}>
          {l.short}
        </NavLink>
      ))}
    </>
  );

  return (
    <div className="shell">
      <aside className="rail">
        <div className="eyebrow" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", fontSize: 9 }}>
          PS4
        </div>
        <div className="rail-mark">DEEPTRACE</div>
        <nav>{nav}</nav>
      </aside>
      <div className="shell-main">
        <header className="topbar">
          <div className="meta">
            <span>{op.station}</span>
            <span>
              {op.full_name} · {op.badge_no}
            </span>
            <span>{clock}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div className="lang-switch" role="group" aria-label={t(lang, "lang")}>
              {(["en", "hi", "pa"] as Lang[]).map((l) => (
                <button key={l} className={l === lang ? "on" : ""} onClick={() => setLang(l)}>
                  {l.toUpperCase()}
                </button>
              ))}
            </div>
            <button className="btn btn-ghost" onClick={logout}>
              {t(lang, "logout")}
            </button>
          </div>
        </header>
        <Outlet />
        <nav className="mobile-nav">{nav}</nav>
      </div>
    </div>
  );
}
