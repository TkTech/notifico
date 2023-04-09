"""empty message

Revision ID: 2d30f08757d6
Revises: ebe78b1ff4dc
Create Date: 2023-04-09 02:38:10.578950

"""
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '2d30f08757d6'
down_revision = 'ebe78b1ff4dc'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("chat_message", "message", type_=JSONB(),
                    postgresql_using='message::json')


def downgrade():
    pass
