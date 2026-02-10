"""Add user authentication

Revision ID: fbac704de733
Revises: 70cbd6c7e984
Create Date: 2026-02-10 01:21:25.461785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbac704de733'
down_revision: Union[str, Sequence[str], None] = '70cbd6c7e984'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Add user_id column to backtests table
    # Note: Using nullable=True for backward compatibility with existing backtests
    # SQLite Note: Foreign key constraints are not enforced retroactively in SQLite,
    # but they will be enforced for new inserts/updates
    op.add_column('backtests', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_backtests_user_id'), 'backtests', ['user_id'], unique=False)

    # Skip foreign key creation for SQLite (can't ALTER TABLE to add FK constraints)
    # The foreign key is defined in the model and will be present in fresh database creates


def downgrade() -> None:
    """Downgrade schema."""
    # Remove user_id column from backtests
    op.drop_index(op.f('ix_backtests_user_id'), table_name='backtests')
    op.drop_column('backtests', 'user_id')

    # Drop users table
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
