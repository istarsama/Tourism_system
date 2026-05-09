"""add diary poi_id for unified place mapping

Revision ID: 0002_diary_poi_id
Revises: 0001_baseline
Create Date: 2026-04-25 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_diary_poi_id"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _has_column("diary", "poi_id"):
        op.add_column("diary", sa.Column("poi_id", sa.Integer(), nullable=True))

    if not _has_index("diary", "ix_diary_poi_id"):
        op.create_index("ix_diary_poi_id", "diary", ["poi_id"])

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        constraint_names = {
            fk["name"]
            for fk in sa.inspect(bind).get_foreign_keys("diary")
            if fk.get("name")
        }
        if "fk_diary_poi_id_poi" not in constraint_names:
            op.create_foreign_key(
                "fk_diary_poi_id_poi",
                "diary",
                "poi",
                ["poi_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        constraint_names = {
            fk["name"]
            for fk in sa.inspect(bind).get_foreign_keys("diary")
            if fk.get("name")
        }
        if "fk_diary_poi_id_poi" in constraint_names:
            op.drop_constraint("fk_diary_poi_id_poi", "diary", type_="foreignkey")

    if _has_index("diary", "ix_diary_poi_id"):
        op.drop_index("ix_diary_poi_id", table_name="diary")

    if _has_column("diary", "poi_id"):
        op.drop_column("diary", "poi_id")
