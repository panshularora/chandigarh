import { useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { api } from "../api";
import { Lang, t } from "../i18n";

gsap.registerPlugin(useGSAP);

export default function Login({
  lang,
  setLang,
  onLogin,
}: {
  lang: Lang;
  setLang: (l: Lang) => void;
  onLogin: (d: any) => void;
}) {
  const root = useRef<HTMLDivElement>(null);
  const [username, setUsername] = useState("inspector");
  const [password, setPassword] = useState("chandigarh2026");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useGSAP(
    () => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.from(".reveal", { opacity: 0, y: 18, stagger: 0.07, duration: 0.55, ease: "power3.out" });
      gsap.from(".docket", { opacity: 0, x: 24, duration: 0.6, ease: "power3.out" });
    },
    { scope: root },
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const data = await api.login(username, password);
      onLogin(data);
    } catch (ex: any) {
      setErr(ex.message || "Denied");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login" ref={root}>
      <div className="login-left">
        <img className="seal reveal" src="/seal.jpg" alt="DeepTrace seal" />
        <div className="eyebrow reveal">Chandigarh Police · Cyber Cell · PS4</div>
        <h1 className="wordmark reveal">{t(lang, "product")}</h1>
        <p className="lede reveal">
          {t(lang, "lede")} <strong>Detect. Trace. Report.</strong>
        </p>
        <div className="team-line reveal">{t(lang, "team")}</div>
      </div>
      <form className="docket" onSubmit={submit}>
        <div className="eyebrow" style={{ color: "#c65a1a" }}>
          {t(lang, "docket")}
        </div>
        <h2>{t(lang, "signin")}</h2>
        <p className="hint">{t(lang, "demo")}</p>
        <label className="field">
          <span>{t(lang, "user")}</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label className="field">
          <span>{t(lang, "pass")}</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        <div className="lang-switch" style={{ marginBottom: 12 }}>
          {(["en", "hi", "pa"] as Lang[]).map((l) => (
            <button type="button" key={l} className={l === lang ? "on" : ""} onClick={() => setLang(l)} style={{ color: l === lang ? "#12141a" : "#6a6254" }}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="err">{err}</div>
        <button className="btn btn-ink" disabled={busy}>
          {busy ? "…" : t(lang, "enter")}
        </button>
      </form>
    </div>
  );
}
