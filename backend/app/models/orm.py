from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserORM(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120))

    preference: Mapped["UserPreferenceORM | None"] = relationship(back_populates="user")


class UserPreferenceORM(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    default_pace: Mapped[str] = mapped_column(String(32), default="standard")
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    dietary_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    avoidances: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped[UserORM] = relationship(back_populates="preference")


class TripORM(TimestampMixin, Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(160), index=True)
    start_date: Mapped[str | None] = mapped_column(String(32))
    end_date: Mapped[str | None] = mapped_column(String(32))
    travelers_count: Mapped[int] = mapped_column(Integer, default=1)
    budget_total: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    active_version_id: Mapped[str | None] = mapped_column(String(64), index=True)

    preference: Mapped["TripPreferenceORM | None"] = relationship(back_populates="trip")
    days: Mapped[list["TripDayORM"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class TripPreferenceORM(TimestampMixin, Base):
    __tablename__ = "trip_preferences"

    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), primary_key=True)
    destination: Mapped[str] = mapped_column(String(160))
    pace: Mapped[str] = mapped_column(String(32), default="standard")
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    dietary_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    must_visit_places: Mapped[list[str]] = mapped_column(JSON, default=list)
    avoidances: Mapped[list[str]] = mapped_column(JSON, default=list)
    natural_language_note: Mapped[str] = mapped_column(Text, default="")

    trip: Mapped[TripORM] = relationship(back_populates="preference")


class TripCandidateORM(TimestampMixin, Base):
    __tablename__ = "trip_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_agent_run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    base_version_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    itinerary_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    budget_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preference_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    conflict_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)


class TripVersionORM(TimestampMixin, Base):
    __tablename__ = "trip_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    source_candidate_id: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_agent_run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    rolled_back_from_version_id: Mapped[str | None] = mapped_column(String(64), index=True)
    itinerary_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    budget_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preference_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    conflict_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    ignored_warning_conflict_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    publish_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    __table_args__ = (Index("ix_trip_versions_trip_version_no", "trip_id", "version_no", unique=True),)


class TripDayORM(TimestampMixin, Base):
    __tablename__ = "trip_days"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    date: Mapped[str] = mapped_column(String(32))
    day_index: Mapped[int] = mapped_column(Integer)

    trip: Mapped[TripORM] = relationship(back_populates="days")
    items: Mapped[list["ItineraryItemORM"]] = relationship(back_populates="day", cascade="all, delete-orphan")


class ItineraryItemORM(TimestampMixin, Base):
    __tablename__ = "itinerary_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trip_day_id: Mapped[str] = mapped_column(ForeignKey("trip_days.id"), index=True)
    temp_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(240))
    item_type: Mapped[str] = mapped_column(String(32), default="note")
    place_id: Mapped[str | None] = mapped_column(String(128), index=True)
    place_name: Mapped[str | None] = mapped_column(String(240))
    start_time: Mapped[str | None] = mapped_column(String(16))
    end_time: Mapped[str | None] = mapped_column(String(16))
    estimated_cost: Mapped[int | None] = mapped_column(Integer)
    transport_to_next: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    preference_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    day: Mapped[TripDayORM] = relationship(back_populates="items")


class BudgetItemORM(TimestampMixin, Base):
    __tablename__ = "budget_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(240))
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    source_item_id: Mapped[str | None] = mapped_column(String(64), index=True)


class AgentRunORM(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    user_message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    candidate_id: Mapped[str | None] = mapped_column(String(64), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)


class AgentRunEventORM(TimestampMixin, Base):
    __tablename__ = "agent_run_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(240))
    detail: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ToolCallORM(TimestampMixin, Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class AgentTraceORM(TimestampMixin, Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    user_intent: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    candidate_id: Mapped[str | None] = mapped_column(String(64), index=True)
    rag_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    tool_call_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)


class RagDocumentORM(TimestampMixin, Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str | None] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(240))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="en")
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class RagChunkORM(TimestampMixin, Base):
    __tablename__ = "rag_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    __table_args__ = (Index("ix_rag_chunks_document_chunk", "document_id", "chunk_index", unique=True),)
