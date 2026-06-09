"""add_composite_indexes

Revision ID: b61ebc592ffa
Revises: e34c9c8112d8
Create Date: 2026-06-09 20:10:22.763521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b61ebc592ffa'
down_revision: Union[str, Sequence[str], None] = 'e34c9c8112d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    # 1. Create new composite indexes defensively
    if 'ix_internships_active_category_posted' not in indexes:
        op.create_index('ix_internships_active_category_posted', 'internships', ['is_active', 'role_category', sa.text('posted_at DESC')], unique=False)
        
    if 'ix_internships_active_category_created' not in indexes:
        op.create_index('ix_internships_active_category_created', 'internships', ['is_active', 'role_category', sa.text('created_at DESC')], unique=False)
        
    if 'ix_internships_active_category_stipend' not in indexes:
        op.create_index('ix_internships_active_category_stipend', 'internships', ['is_active', 'role_category', sa.text('stipend_numeric DESC')], unique=False)
        
    if 'ix_internships_active_company' not in indexes:
        op.create_index('ix_internships_active_company', 'internships', ['is_active', 'company_name'], unique=False)
        
    if 'ix_internships_active_source' not in indexes:
        op.create_index('ix_internships_active_source', 'internships', ['is_active', 'source'], unique=False)
        
    # 2. Drop redundant indexes defensively
    redundant = ['ix_internships_paid', 'ix_internships_remote', 'ix_internships_confidence', 
                 'ix_internships_confidence_tier', 'ix_internships_relevance_tier', 'ix_internships_consecutive_failures']
    for r_idx in redundant:
        if r_idx in indexes:
            op.drop_index(r_idx, table_name='internships')


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('internships')]
    
    # 1. Drop the composite indexes
    composites = ['ix_internships_active_category_posted', 'ix_internships_active_category_created', 
                  'ix_internships_active_category_stipend', 'ix_internships_active_company', 
                  'ix_internships_active_source']
    for c_idx in composites:
        if c_idx in indexes:
            op.drop_index(c_idx, table_name='internships')
            
    # 2. Re-create the dropped redundant indexes defensively
    redundant_mapping = {
        'ix_internships_paid': 'paid',
        'ix_internships_remote': 'remote',
        'ix_internships_confidence': 'confidence',
        'ix_internships_confidence_tier': 'confidence_tier',
        'ix_internships_relevance_tier': 'relevance_tier',
        'ix_internships_consecutive_failures': 'consecutive_failures'
    }
    for r_idx, column in redundant_mapping.items():
        if r_idx not in indexes:
            op.create_index(r_idx, 'internships', [column], unique=False)
