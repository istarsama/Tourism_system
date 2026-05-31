"""add OSM graph cache metadata

Revision ID: 0003_osm_graph_cache
Revises: 0002_diary_poi_id
Create Date: 2026-05-31 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_osm_graph_cache"
down_revision: Union[str, Sequence[str], None] = "0002_diary_poi_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "osm_graph_cache" in inspector.get_table_names():
        return

    op.create_table(
        "osm_graph_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("transport", sa.String(), nullable=False),
        sa.Column("place_query", sa.String(), nullable=False),
        sa.Column("graph_path", sa.String(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city", "transport", name="uq_osm_graph_cache_city_transport"),
    )
    op.create_index("ix_osm_graph_cache_city", "osm_graph_cache", ["city"])
    op.create_index("ix_osm_graph_cache_transport", "osm_graph_cache", ["transport"])
    op.create_index("ix_osm_graph_cache_status", "osm_graph_cache", ["status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "osm_graph_cache" not in inspector.get_table_names():
        return

    op.drop_index("ix_osm_graph_cache_status", table_name="osm_graph_cache")
    op.drop_index("ix_osm_graph_cache_transport", table_name="osm_graph_cache")
    op.drop_index("ix_osm_graph_cache_city", table_name="osm_graph_cache")
    op.drop_table("osm_graph_cache")
