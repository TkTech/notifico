"""empty message

Revision ID: cad59c3d601a
Revises: 39bbc57ae19d
Create Date: 2022-10-23 21:30:39.655712

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cad59c3d601a'
down_revision = '39bbc57ae19d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('group')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('group',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('owner_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], name='group_owner_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='group_pkey'),
    sa.UniqueConstraint('name', name='group_name_key')
    )
    # ### end Alembic commands ###
