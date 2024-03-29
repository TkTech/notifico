"""empty message

Revision ID: 2e379154b800
Revises: a50852b553b1
Create Date: 2022-10-11 01:38:02.121012

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e379154b800'
down_revision = 'a50852b553b1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('irc_network',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('host', sa.String(length=255), nullable=False),
    sa.Column('port', sa.Integer(), nullable=True),
    sa.Column('ssl', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('channel', sa.Column('network_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(None, 'channel', 'irc_network', ['network_id'], ['id'])

    op.execute(
        'INSERT INTO irc_network(created, host, port, ssl)'
        ' SELECT NOW(), host, port, ssl'
        ' FROM channel GROUP BY distinct(host, port, ssl);'
    )
    op.execute(
        'UPDATE channel SET network_id=(SELECT id FROM irc_network WHERE'
        ' host=channel.host AND port=channel.port AND ssl=channel.ssl LIMIT 1);'
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'channel', type_='foreignkey')
    op.alter_column('channel', 'id',
               existing_type=sa.BIGINT(),
               server_default=sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
               existing_nullable=False,
               autoincrement=True)
    op.drop_column('channel', 'network_id')
    op.drop_table('irc_network')
    # ### end Alembic commands ###
