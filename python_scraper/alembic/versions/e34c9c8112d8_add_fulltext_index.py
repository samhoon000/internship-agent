"""add_fulltext_index

Revision ID: e34c9c8112d8
Revises: 568331f11e10
Create Date: 2026-06-06 13:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e34c9c8112d8'
down_revision: Union[str, Sequence[str], None] = '568331f11e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = inspector.get_indexes('internships')
    index_names = [idx['name'] for idx in indexes]
    
    if 'ix_internships_fulltext' not in index_names:
        op.execute(sa.text("CREATE FULLTEXT INDEX ix_internships_fulltext ON internships (company_name, role, skills, description)"))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = inspector.get_indexes('internships')
    index_names = [idx['name'] for idx in indexes]
    
    if 'ix_internships_fulltext' in index_names:
        op.execute(sa.text("ALTER TABLE internships DROP INDEX ix_internships_fulltext"))
