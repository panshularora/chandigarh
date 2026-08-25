import { Lang, t } from "../i18n";

export default function Stamp({ v, lang }: { v?: string | null; lang: Lang }) {
  if (!v) return <span className="stamp inc">—</span>;
  if (v === "AI_GENERATED") return <span className="stamp ai">{t(lang, "ai")}</span>;
  if (v === "REAL") return <span className="stamp real">{t(lang, "real")}</span>;
  return <span className="stamp inc">{t(lang, "inc")}</span>;
}
