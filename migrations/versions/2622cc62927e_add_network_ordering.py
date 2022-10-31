"""Add network ordering

Revision ID: 2622cc62927e
Revises: ddb15516c745
Create Date: 2022-10-19 11:06:52.348032

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2622cc62927e'
down_revision = 'ddb15516c745'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('irc_network', sa.Column('public', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('irc_network', 'public')
    # ### end Alembic commands ###