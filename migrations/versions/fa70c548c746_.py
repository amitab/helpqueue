"""empty message

Revision ID: fa70c548c746
Revises: 653093fddc44
Create Date: 2020-09-27 01:53:05.441892

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa70c548c746'
down_revision = '653093fddc44'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('date_last_activity', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'date_last_activity')
