"""baseline current SQLModel schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-04-25 00:00:00
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from models import SQLModel  # noqa: E402
import models  # noqa: F401,E402

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.drop_all(bind=bind)
