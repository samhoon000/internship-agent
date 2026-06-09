"""add_source_health_metrics_columns

Revision ID: 0bf5c12d4a6a
Revises: b61ebc592ffa
Create Date: 2026-06-09 20:13:01.164703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bf5c12d4a6a'
down_revision: Union[str, Sequence[str], None] = 'b61ebc592ffa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('source_health')]
    
    if 'last_jobs_found' not in columns:
        op.add_column('source_health', sa.Column('last_jobs_found', sa.Integer(), server_default='0', nullable=False))
    if 'last_jobs_saved' not in columns:
        op.add_column('source_health', sa.Column('last_jobs_saved', sa.Integer(), server_default='0', nullable=False))
    if 'success_count' not in columns:
        op.add_column('source_health', sa.Column('success_count', sa.Integer(), server_default='0', nullable=False))
    if 'failure_count' not in columns:
        op.add_column('source_health', sa.Column('failure_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('source_health')]
    
    if 'last_jobs_found' in columns:
        op.drop_column('source_health', 'last_jobs_found')
    if 'last_jobs_saved' in columns:
        op.drop_column('source_health', 'last_jobs_saved')
    if 'success_count' in columns:
        op.drop_column('source_health', 'success_count')
    if 'failure_count' in columns:
        op.drop_column('source_health', 'failure_count')
