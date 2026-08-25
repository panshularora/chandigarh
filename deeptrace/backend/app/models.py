from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    station: Mapped[str] = mapped_column(String(128))
    badge_no: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8), default="en")
    password_hash: Mapped[str] = mapped_column(String(256))

    cases: Mapped[list["Case"]] = relationship(back_populates="creator")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    fir_number: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(256))
    offence_type: Mapped[str] = mapped_column(String(64))
    station: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="open")
    priority: Mapped[str] = mapped_column(String(8), default="P2")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    creator: Mapped[Operator] = relationship(back_populates="cases")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    custody: Mapped[list["CustodyEvent"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    stored_name: Mapped[str] = mapped_column(String(256))
    media_type: Mapped[str] = mapped_column(String(16))
    mime: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    sha1: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship(back_populates="evidence")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    status: Mapped[str] = mapped_column(String(16), default="complete")
    verdict: Mapped[str] = mapped_column(String(24))
    confidence: Mapped[float] = mapped_column(Float)
    ai_likelihood: Mapped[float] = mapped_column(Float)
    signals_json: Mapped[str] = mapped_column(Text)
    generators_json: Mapped[str] = mapped_column(Text)
    provenance_json: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text)
    heatmap_name: Mapped[str] = mapped_column(String(256), default="")
    overlay_name: Mapped[str] = mapped_column(String(256), default="")
    briefing: Mapped[str] = mapped_column(Text, default="")
    model_versions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[Evidence] = relationship(back_populates="analyses")


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), index=True)

    case: Mapped[Case] = relationship(back_populates="custody")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    filename: Mapped[str] = mapped_column(String(256))
    content_hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(128))
    generated_by: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship(back_populates="reports")
