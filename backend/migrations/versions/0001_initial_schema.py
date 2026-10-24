"""The v1 schema from docs/database-schema.md, with the 16 seeded movements.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SEEDED_MOVEMENTS = [
    "Gothic",
    "Renaissance",
    "Mannerism",
    "Baroque",
    "Rococo",
    "Neoclassicism",
    "Romanticism",
    "Realism",
    "Impressionism",
    "Post-Impressionism",
    "Symbolism",
    "Expressionism",
    "Cubism",
    "Surrealism",
    "Abstract Expressionism",
    "Pop Art",
]


def timestamp(name):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        timestamp("created_at"),
        timestamp("updated_at"),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    # Community entities: names are unique ignoring capital letters.
    for table in ("artists", "movements", "subjects"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.Text, nullable=False),
            timestamp("created_at"),
        )
        op.create_index(f"uq_{table}_name_lower", table, [sa.text("lower(name)")], unique=True)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        timestamp("created_at"),
        sa.CheckConstraint("usage_count >= 0", name="ck_tags_usage_count_not_negative"),
    )
    op.create_index("uq_tags_name_lower", "tags", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("collection_state", sa.Text, nullable=False, server_default="COLLECTION"),
        sa.Column("title", sa.Text, nullable=False, server_default=""),
        sa.Column("artist_id", sa.Integer, sa.ForeignKey("artists.id")),
        sa.Column("date_display", sa.Text),
        sa.Column("year_start", sa.Integer),
        sa.Column("year_end", sa.Integer),
        sa.Column("date_is_circa", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id")),
        sa.Column("movement_id", sa.Integer, sa.ForeignKey("movements.id")),
        sa.Column("museum", sa.Text, nullable=False, server_default=""),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("is_discoverable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("are_notes_discoverable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("artwork_photo_path", sa.Text),
        timestamp("created_at"),
        timestamp("updated_at"),
        sa.CheckConstraint(
            "collection_state IN ('COLLECTION', 'WATCHLIST')",
            name="ck_artworks_collection_state",
        ),
        sa.CheckConstraint(
            "collection_state <> 'COLLECTION' OR artwork_photo_path IS NOT NULL",
            name="ck_artworks_collection_has_photo",
        ),
        # There is no year 0: 1 BC is stored as -1.
        sa.CheckConstraint("year_start <> 0 AND year_end <> 0", name="ck_artworks_no_year_zero"),
        sa.CheckConstraint(
            "year_end IS NULL OR (year_start IS NOT NULL AND year_end >= year_start)",
            name="ck_artworks_year_end_after_start",
        ),
    )
    for column in ("user_id", "collection_state", "artist_id", "subject_id", "movement_id", "is_discoverable"):
        op.create_index(f"ix_artworks_{column}", "artworks", [column])

    op.create_table(
        "artwork_tags",
        sa.Column("artwork_id", sa.Integer, sa.ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), primary_key=True),
        sa.Column("source", sa.Text, nullable=False, server_default="USER"),
        sa.CheckConstraint("source IN ('USER', 'SYSTEM')", name="ck_artwork_tags_source"),
    )
    op.create_index("ix_artwork_tags_artwork_id", "artwork_tags", ["artwork_id"])
    op.create_index("ix_artwork_tags_tag_id", "artwork_tags", ["tag_id"])

    op.create_table(
        "detail_photos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artwork_id", sa.Integer, sa.ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        timestamp("created_at"),
    )

    movements = sa.table("movements", sa.column("name", sa.Text))
    op.bulk_insert(movements, [{"name": name} for name in SEEDED_MOVEMENTS])
