"""initial_schema

Revision ID: d834f6570808
Revises:
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd834f6570808'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(), nullable=False),
        sa.Column('buyer_id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=True),
        sa.Column('store_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('payment_method', sa.String(), nullable=False),
        sa.Column('total_price', sa.Float(), nullable=False),
        sa.Column('pickup_expected_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='order_schema',
    )
    op.create_index('ix_order_schema_orders_id', 'orders', ['id'], unique=False, schema='order_schema')
    op.create_index('ix_order_schema_orders_order_number', 'orders', ['order_number'], unique=True, schema='order_schema')
    op.create_index('ix_order_schema_orders_buyer_id', 'orders', ['buyer_id'], unique=False, schema='order_schema')
    op.create_index('ix_order_schema_orders_store_id', 'orders', ['store_id'], unique=False, schema='order_schema')

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['order_schema.orders.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='order_schema',
    )
    op.create_index('ix_order_schema_order_items_id', 'order_items', ['id'], unique=False, schema='order_schema')
    op.create_index('ix_order_schema_order_items_product_id', 'order_items', ['product_id'], unique=False, schema='order_schema')


def downgrade() -> None:
    op.drop_index('ix_order_schema_order_items_product_id', table_name='order_items', schema='order_schema')
    op.drop_index('ix_order_schema_order_items_id', table_name='order_items', schema='order_schema')
    op.drop_table('order_items', schema='order_schema')
    op.drop_index('ix_order_schema_orders_store_id', table_name='orders', schema='order_schema')
    op.drop_index('ix_order_schema_orders_buyer_id', table_name='orders', schema='order_schema')
    op.drop_index('ix_order_schema_orders_order_number', table_name='orders', schema='order_schema')
    op.drop_index('ix_order_schema_orders_id', table_name='orders', schema='order_schema')
    op.drop_table('orders', schema='order_schema')
