"""Initial schema: users, profiles, catalog, recommendations.

Revision ID: 0001
Revises:
Create Date: 2026-04-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("height_cm", sa.Float()),
        sa.Column("weight_kg", sa.Float()),
        sa.Column("age", sa.Integer()),
        sa.Column("gender", sa.String(32)),
        sa.Column("body_type", sa.String(32)),
        sa.Column("wrist_to_floor_cm", sa.Float()),
        sa.Column("hand_size_cm", sa.Float()),
        sa.Column("bench_press_kg", sa.Float()),
        sa.Column("squat_kg", sa.Float()),
        sa.Column("vo2_max", sa.Float()),
        sa.Column("resting_hr", sa.Float()),
        sa.Column("fitness_level", sa.Integer()),
        sa.Column("handicap", sa.Float()),
        sa.Column("swing_speed_mph", sa.Float()),
        sa.Column("current_brand", sa.String(64)),
        sa.Column("preferred_brands", sa.JSON()),
        sa.Column("medical_flags", sa.JSON()),
        sa.Column("medical_notes", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)

    op.create_table(
        "brands",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("country", sa.String(64)),
        sa.Column("blurb", sa.Text()),
    )
    op.create_index("ix_brands_name", "brands", ["name"], unique=True)

    op.create_table(
        "club_heads",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("brand_id", sa.String(64), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("club_type", sa.String(32), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("launch", sa.String(16)),
        sa.Column("spin", sa.String(16)),
        sa.Column("offset", sa.String(16)),
        sa.Column("lofts", sa.JSON()),
        sa.Column("standard_loft", sa.Float()),
        sa.Column("pw_loft", sa.Float()),
        sa.Column("set_makeup", sa.String(16)),
        sa.Column("year", sa.Integer()),
        sa.Column("blurb", sa.Text()),
        sa.UniqueConstraint("brand_id", "model", name="uq_head_brand_model"),
    )
    op.create_index("ix_club_heads_brand_id", "club_heads", ["brand_id"])
    op.create_index("ix_club_heads_club_type", "club_heads", ["club_type"])

    op.create_table(
        "shafts",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("brand_id", sa.String(64), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("families", sa.JSON()),
        sa.Column("profile", sa.String(16), nullable=False),
        sa.Column("launch", sa.String(16)),
        sa.Column("spin", sa.String(16)),
        sa.Column("flex_weights", sa.JSON()),
        sa.Column("torque", sa.Float()),
        sa.Column("blurb", sa.Text()),
        sa.UniqueConstraint("brand_id", "model", name="uq_shaft_brand_model"),
    )
    op.create_index("ix_shafts_brand_id", "shafts", ["brand_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("profile_snapshot", sa.JSON()),
        sa.Column("result", sa.JSON()),
        sa.Column("taken_to_fitter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating", sa.Integer()),
        sa.Column("fitter_notes", sa.Text()),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("shafts")
    op.drop_table("club_heads")
    op.drop_table("brands")
    op.drop_table("profiles")
    op.drop_table("users")
