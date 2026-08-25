import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, setToken, token } from "./api";
import { Lang } from "./i18n";
import Audit from "./pages/Audit";
import CaseRoom from "./pages/CaseRoom";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import NewCase from "./pages/NewCase";
import Queue from "./pages/Queue";
import Reports from "./pages/Reports";
import Shell from "./pages/Shell";
import Station from "./pages/Station";

export default function App() {
  const [lang, setLang] = useState<Lang>((localStorage.getItem("dt_lang") as Lang) || "en");
  const [op, setOp] = useState<any>(null);
  const [ready, setReady] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    localStorage.setItem("dt_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    if (!token()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setOp)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  function onLogin(data: any) {
    setToken(data.token);
    setOp(data.operator);
    nav("/app");
  }
  function logout() {
    setToken(null);
    setOp(null);
    nav("/");
  }

  if (!ready) return null;

  return (
    <div className={`lang-${lang}`}>
      <Routes>
        <Route path="/" element={op ? <Navigate to="/app" /> : <Login lang={lang} setLang={setLang} onLogin={onLogin} />} />
        <Route
          path="/app"
          element={op ? <Shell lang={lang} setLang={setLang} op={op} logout={logout} /> : <Navigate to="/" />}
        >
          <Route index element={<Dashboard lang={lang} />} />
          <Route path="cases" element={<Queue lang={lang} />} />
          <Route path="cases/new" element={<NewCase lang={lang} />} />
          <Route path="cases/:id" element={<CaseRoom lang={lang} />} />
          <Route path="reports" element={<Reports lang={lang} />} />
          <Route path="audit" element={<Audit lang={lang} />} />
          <Route path="station" element={<Station lang={lang} />} />
        </Route>
      </Routes>
    </div>
  );
}
