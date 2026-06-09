"""add_soft_delete_and_liveness_columns

Revision ID: 747e6ccc248b
Revises: 
Create Date: 2026-06-05 22:48:54.830280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '747e6ccc248b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('internships')]
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    if 'last_seen' not in columns:
        op.add_column('internships', sa.Column('last_seen', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
        columns.append('last_seen')
    if 'deactivated_at' not in columns:
        op.add_column('internships', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
        columns.append('deactivated_at')
    if 'consecutive_failures' not in columns:
        op.add_column('internships', sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default=sa.text('0')))
        columns.append('consecutive_failures')
        
    op.alter_column('internships', 'stipend_numeric',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False,
               existing_server_default=sa.text('0'))
    op.alter_column('internships', 'freshness_score',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False,
               existing_server_default=sa.text('0'))
    op.alter_column('internships', 'description',
               existing_type=mysql.TEXT(),
               type_=sa.String(length=5000),
               existing_nullable=True)
               
    # Create indexes conditionally
    for idx in ['confidence', 'confidence_score', 'confidence_tier', 'consecutive_failures', 
                'created_at', 'deactivated_at', 'freshness_score', 'is_active', 'last_seen', 
                'legitimacy_score', 'paid', 'posted_at', 'relevance_score', 'remote', 
                'source', 'stipend_numeric']:
        idx_name = f'ix_internships_{idx}'
        if idx_name not in indexes and idx in columns:
            op.create_index(op.f(idx_name), 'internships', [idx], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('internships')]
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    # Drop indexes conditionally
    for idx in ['confidence', 'confidence_score', 'confidence_tier', 'consecutive_failures', 
                'created_at', 'deactivated_at', 'freshness_score', 'is_active', 'last_seen', 
                'legitimacy_score', 'paid', 'posted_at', 'relevance_score', 'remote', 
                'source', 'stipend_numeric']:
        idx_name = f'ix_internships_{idx}'
        if idx_name in indexes:
            op.drop_index(op.f(idx_name), table_name='internships')
            
    op.alter_column('internships', 'description',
               existing_type=sa.String(length=5000),
               type_=mysql.TEXT(),
               existing_nullable=True)
    op.alter_column('internships', 'freshness_score',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True,
               existing_server_default=sa.text('0'))
    op.alter_column('internships', 'stipend_numeric',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True,
               existing_server_default=sa.text('0'))
               
    if 'consecutive_failures' in columns:
        op.drop_column('internships', 'consecutive_failures')
    if 'deactivated_at' in columns:
        op.drop_column('internships', 'deactivated_at')
    if 'last_seen' in columns:
        op.drop_column('internships', 'last_seen')
