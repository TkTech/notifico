"""Add owners to networks

Revision ID: 39bbc57ae19d
Revises: 2622cc62927e
Create Date: 2022-10-19 15:05:31.174361

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39bbc57ae19d'
down_revision = '2622cc62927e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('irc_network', sa.Column('owner_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(None, 'irc_network', 'user', ['owner_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'irc_network', type_='foreignkey')
    op.drop_column('irc_network', 'owner_id')
    # ### end Alembic commands ###
