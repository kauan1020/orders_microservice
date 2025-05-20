"""add_user_info_to_orders_and_update_enum

Revision ID: 7e1ef9497ea4
Revises: ca3b6e97d80b
Create Date: 2025-04-20 21:36:21.325373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1ef9497ea4'
down_revision: Union[str, None] = 'ca3b6e97d80b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicione as novas colunas à tabela orders
    op.add_column('orders', sa.Column('user_name', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('user_email', sa.String(), nullable=True))

    # Update the enum to include AWAITING_PAYMENT status
    op.execute('ALTER TYPE orderstatus RENAME TO orderstatus_old')
    op.execute("CREATE TYPE orderstatus AS ENUM ('RECEIVED', 'PREPARING', 'READY', 'FINISHED', 'AWAITING_PAYMENT', 'PAID', 'PAYMENT_FAILED', 'PAYMENT_ERROR')")
    op.execute('ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::text::orderstatus')
    op.execute('DROP TYPE orderstatus_old')


def downgrade() -> None:
    # Revert the enum change first (remove AWAITING_PAYMENT)
    op.execute('ALTER TYPE orderstatus RENAME TO orderstatus_old')
    op.execute("CREATE TYPE orderstatus AS ENUM ('RECEIVED', 'PREPARING', 'READY', 'FINISHED', 'PAID', 'PAYMENT_FAILED', 'PAYMENT_ERROR')")
    op.execute('ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::text::orderstatus')
    op.execute('DROP TYPE orderstatus_old')

    # Remova as colunas em caso de rollback
    op.drop_column('orders', 'user_email')
    op.drop_column('orders', 'user_name')