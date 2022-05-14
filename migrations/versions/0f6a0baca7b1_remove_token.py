"""Remove Token

Revision ID: 0f6a0baca7b1
Revises: d19e3d2edab2
Create Date: 2022-05-14 00:19:07.984602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f6a0baca7b1'
down_revision = 'd19e3d2edab2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('auth_token')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('auth_token',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('created', sa.TIMESTAMP(), nullable=True),
    sa.Column('name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('token', sa.VARCHAR(length=512), nullable=False),
    sa.Column('owner_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
