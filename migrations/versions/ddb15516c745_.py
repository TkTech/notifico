"""empty message

Revision ID: ddb15516c745
Revises: 2e379154b800
Create Date: 2022-10-11 05:18:04.008672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddb15516c745'
down_revision = '2e379154b800'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('channel', 'host')
    op.drop_column('channel', 'port')
    op.drop_column('channel', 'ssl')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('channel', sa.Column('ssl', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('channel', sa.Column('port', sa.BIGINT(), autoincrement=False, nullable=True))
    op.add_column('channel', sa.Column('host', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    # ### end Alembic commands ###