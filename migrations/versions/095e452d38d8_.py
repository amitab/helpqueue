"""empty message

Revision ID: 095e452d38d8
Revises: fa70c548c746
Create Date: 2020-09-28 22:57:21.406983

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '095e452d38d8'
down_revision = 'fa70c548c746'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('team', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'team')
