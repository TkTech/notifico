"""empty message

Revision ID: 75770b11c67a
Revises: a24f38bb188b
Create Date: 2022-10-31 09:11:21.087572

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75770b11c67a'
down_revision = 'a24f38bb188b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    status = sa.Enum('UNKNOWN', 'HEALTHY', 'DEGRADING', 'TEMPORARY_BLOCK', 'BLOCKED', name='status')
    status.create(op.get_bind())

    op.create_table('network_event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('network_id', sa.BigInteger(), nullable=True),
    sa.Column('event', sa.Enum('CRITICAL', 'ERROR', 'WARNING', 'INFO', name='event'), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['network_id'], ['irc_network.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('irc_network', sa.Column('status', sa.Enum('UNKNOWN', 'HEALTHY', 'DEGRADING', 'TEMPORARY_BLOCK', 'BLOCKED', name='status'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute('DROP type status')
    op.execute('DROP type event')
    op.drop_column('irc_network', 'status')
    op.drop_table('network_event')
    # ### end Alembic commands ###
