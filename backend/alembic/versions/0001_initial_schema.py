"""Initial WayPilot schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("default_pace", sa.String(length=32), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("dietary_preferences", sa.JSON(), nullable=False),
        sa.Column("avoidances", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("destination", sa.String(length=160), nullable=False),
        sa.Column("start_date", sa.String(length=32)),
        sa.Column("end_date", sa.String(length=32)),
        sa.Column("travelers_count", sa.Integer(), nullable=False),
        sa.Column("budget_total", sa.Integer()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("active_version_id", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.create_index("ix_trips_destination", "trips", ["destination"])
    op.create_index("ix_trips_status", "trips", ["status"])
    op.create_index("ix_trips_active_version_id", "trips", ["active_version_id"])

    op.create_table(
        "trip_preferences",
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), primary_key=True),
        sa.Column("destination", sa.String(length=160), nullable=False),
        sa.Column("pace", sa.String(length=32), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("dietary_preferences", sa.JSON(), nullable=False),
        sa.Column("must_visit_places", sa.JSON(), nullable=False),
        sa.Column("avoidances", sa.JSON(), nullable=False),
        sa.Column("natural_language_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "trip_candidates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_agent_run_id", sa.String(length=64)),
        sa.Column("base_version_id", sa.String(length=64)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("itinerary_snapshot", sa.JSON(), nullable=False),
        sa.Column("budget_snapshot", sa.JSON(), nullable=False),
        sa.Column("preference_snapshot", sa.JSON(), nullable=False),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        sa.Column("conflict_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trip_candidates_trip_id", "trip_candidates", ["trip_id"])
    op.create_index("ix_trip_candidates_status", "trip_candidates", ["status"])
    op.create_index("ix_trip_candidates_created_by", "trip_candidates", ["created_by"])

    op.create_table(
        "trip_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("source_candidate_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_agent_run_id", sa.String(length=64)),
        sa.Column("rolled_back_from_version_id", sa.String(length=64)),
        sa.Column("itinerary_snapshot", sa.JSON(), nullable=False),
        sa.Column("budget_snapshot", sa.JSON(), nullable=False),
        sa.Column("preference_snapshot", sa.JSON(), nullable=False),
        sa.Column("conflict_snapshot", sa.JSON(), nullable=False),
        sa.Column("ignored_warning_conflict_ids", sa.JSON(), nullable=False),
        sa.Column("publish_note", sa.Text()),
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trip_versions_trip_id", "trip_versions", ["trip_id"])
    op.create_index("ix_trip_versions_trip_version_no", "trip_versions", ["trip_id", "version_no"], unique=True)

    op.create_table(
        "trip_days",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("date", sa.String(length=32), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trip_days_trip_id", "trip_days", ["trip_id"])

    op.create_table(
        "itinerary_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trip_day_id", sa.String(length=64), sa.ForeignKey("trip_days.id"), nullable=False),
        sa.Column("temp_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("place_id", sa.String(length=128)),
        sa.Column("place_name", sa.String(length=240)),
        sa.Column("start_time", sa.String(length=16)),
        sa.Column("end_time", sa.String(length=16)),
        sa.Column("estimated_cost", sa.Integer()),
        sa.Column("transport_to_next", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("preference_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_itinerary_items_trip_day_id", "itinerary_items", ["trip_day_id"])
    op.create_index("ix_itinerary_items_place_id", "itinerary_items", ["place_id"])

    op.create_table(
        "budget_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("source_item_id", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_budget_items_trip_id", "budget_items", ["trip_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("candidate_id", sa.String(length=64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_trip_id", "agent_runs", ["trip_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("agent_run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_run_events_agent_run_id", "agent_run_events", ["agent_run_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("agent_run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_tool_name", "tool_calls", ["tool_name"])

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("agent_run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trip_id", sa.String(length=64), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("user_intent", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("candidate_id", sa.String(length=64)),
        sa.Column("rag_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("tool_call_ids", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_traces_agent_run_id", "agent_traces", ["agent_run_id"])

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=64), sa.ForeignKey("users.id")),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128)),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("city", sa.String(length=120)),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rag_documents_owner_user_id", "rag_documents", ["owner_user_id"])
    op.create_index("ix_rag_documents_source_type", "rag_documents", ["source_type"])
    op.create_index("ix_rag_documents_city", "rag_documents", ["city"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("rag_documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])
    op.create_index("ix_rag_chunks_document_chunk", "rag_chunks", ["document_id", "chunk_index"], unique=True)


def downgrade() -> None:
    for table_name in [
        "rag_chunks",
        "rag_documents",
        "agent_traces",
        "tool_calls",
        "agent_run_events",
        "agent_runs",
        "budget_items",
        "itinerary_items",
        "trip_days",
        "trip_versions",
        "trip_candidates",
        "trip_preferences",
        "trips",
        "user_preferences",
        "users",
    ]:
        op.drop_table(table_name)
    op.execute("DROP EXTENSION IF EXISTS vector")
