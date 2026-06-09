"""add_missing_columns_and_tables

Revision ID: 568331f11e10
Revises: 747e6ccc248b
Create Date: 2026-06-06 13:20:04.399393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '568331f11e10'
down_revision: Union[str, Sequence[str], None] = '747e6ccc248b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('internships')]
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    # Conditionally add relevance fields
    if 'relevance_score' not in columns:
        op.add_column('internships', sa.Column('relevance_score', sa.Integer(), server_default='0', nullable=False))
    if 'ix_internships_relevance_score' not in indexes:
        op.create_index(op.f('ix_internships_relevance_score'), 'internships', ['relevance_score'], unique=False)
    
    if 'relevance_tier' not in columns:
        op.add_column('internships', sa.Column('relevance_tier', sa.String(length=50), server_default='IRRELEVANT', nullable=False))
    if 'ix_internships_relevance_tier' not in indexes:
        op.create_index(op.f('ix_internships_relevance_tier'), 'internships', ['relevance_tier'], unique=False)
        
    # Conditionally add role category
    if 'role_category' not in columns:
        op.add_column('internships', sa.Column('role_category', sa.String(length=50), server_default='Other', nullable=False))
    if 'ix_internships_role_category' not in indexes:
        op.create_index(op.f('ix_internships_role_category'), 'internships', ['role_category'], unique=False)

    # Conditionally add soft delete & monitoring columns
    if 'is_active' not in columns:
        op.add_column('internships', sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False))
    if 'ix_internships_is_active' not in indexes:
        op.create_index(op.f('ix_internships_is_active'), 'internships', ['is_active'], unique=False)

    if 'inactive_reason' not in columns:
        op.add_column('internships', sa.Column('inactive_reason', sa.String(length=255), nullable=True))

    if 'last_seen' not in columns:
        op.add_column('internships', sa.Column('last_seen', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False))
    if 'ix_internships_last_seen' not in indexes:
        op.create_index(op.f('ix_internships_last_seen'), 'internships', ['last_seen'], unique=False)

    if 'deactivated_at' not in columns:
        op.add_column('internships', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    if 'ix_internships_deactivated_at' not in indexes:
        op.create_index(op.f('ix_internships_deactivated_at'), 'internships', ['deactivated_at'], unique=False)

    if 'consecutive_failures' not in columns:
        op.add_column('internships', sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False))
    if 'ix_internships_consecutive_failures' not in indexes:
        op.create_index(op.f('ix_internships_consecutive_failures'), 'internships', ['consecutive_failures'], unique=False)

    # Rejections and Health tables
    tables = inspector.get_table_names()
    if 'internship_rejections' not in tables:
        op.create_table('internship_rejections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('reasons', sa.String(length=500), nullable=False),
        sa.Column('relevance_score', sa.Integer(), nullable=False),
        sa.Column('legitimacy_score', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_internship_rejections_created_at'), 'internship_rejections', ['created_at'], unique=False)
        op.create_index(op.f('ix_internship_rejections_source'), 'internship_rejections', ['source'], unique=False)

    if 'source_health' not in tables:
        op.create_table('source_health',
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('last_successful_scrape', sa.DateTime(), nullable=True),
        sa.Column('last_failure', sa.DateTime(), nullable=True),
        sa.Column('health_status', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('source')
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'source_health' in tables:
        op.drop_table('source_health')
        
    if 'internship_rejections' in tables:
        rejections_indexes = [idx['name'] for idx in inspector.get_indexes('internship_rejections')]
        if 'ix_internship_rejections_source' in rejections_indexes:
            op.drop_index(op.f('ix_internship_rejections_source'), table_name='internship_rejections')
        if 'ix_internship_rejections_created_at' in rejections_indexes:
            op.drop_index(op.f('ix_internship_rejections_created_at'), table_name='internship_rejections')
        op.drop_table('internship_rejections')
        
    columns = [c['name'] for c in inspector.get_columns('internships')]
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    if 'consecutive_failures' in columns:
        if 'ix_internships_consecutive_failures' in indexes:
            op.drop_index(op.f('ix_internships_consecutive_failures'), table_name='internships')
        op.drop_column('internships', 'consecutive_failures')
        
    if 'deactivated_at' in columns:
        if 'ix_internships_deactivated_at' in indexes:
            op.drop_index(op.f('ix_internships_deactivated_at'), table_name='internships')
        op.drop_column('internships', 'deactivated_at')
        
    if 'last_seen' in columns:
        if 'ix_internships_last_seen' in indexes:
            op.drop_index(op.f('ix_internships_last_seen'), table_name='internships')
        op.drop_column('internships', 'last_seen')
        
    if 'inactive_reason' in columns:
        op.drop_column('internships', 'inactive_reason')
        
    if 'is_active' in columns:
        if 'ix_internships_is_active' in indexes:
            op.drop_index(op.f('ix_internships_is_active'), table_name='internships')
        op.drop_column('internships', 'is_active')
        
    if 'role_category' in columns:
        if 'ix_internships_role_category' in indexes:
            op.drop_index(op.f('ix_internships_role_category'), table_name='internships')
        op.drop_column('internships', 'role_category')
        
    if 'relevance_tier' in columns:
        if 'ix_internships_relevance_tier' in indexes:
            op.drop_index(op.f('ix_internships_relevance_tier'), table_name='internships')
        op.drop_column('internships', 'relevance_tier')
        
    if 'relevance_score' in columns:
        if 'ix_internships_relevance_score' in indexes:
            op.drop_index(op.f('ix_internships_relevance_score'), table_name='internships')
        op.drop_column('internships', 'relevance_score')
