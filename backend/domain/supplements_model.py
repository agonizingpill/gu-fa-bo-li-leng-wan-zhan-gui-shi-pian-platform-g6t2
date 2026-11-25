from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table, UniqueConstraint

from core.db import metadata


# 补测候选工况：同一弯模下由两条最新签注曲线复算并按分歧排序，领片后跟踪到见证。
supplement_candidates = Table('supplement_candidates', metadata,
    Column('code', String(64), primary_key=True),
    Column('jig', String(160), ForeignKey('jigs.code'), nullable=False),
    Column('heat', Float, nullable=False),
    Column('thick', Float, nullable=False),
    Column('target', Float, nullable=False),
    Column('profile_a', String(64), ForeignKey('profiles.code'), nullable=False),
    Column('profile_b', String(64), ForeignKey('profiles.code'), nullable=False),
    Column('prediction_a', Float, nullable=False),
    Column('prediction_b', Float, nullable=False),
    Column('divergence', Float, nullable=False),
    Column('rank', Integer, nullable=False),
    Column('status', String(32), nullable=False, default='待领片'),
    Column('claimed_by', String(160), nullable=True),
    Column('coupon', String(64), ForeignKey('coupons.code'), nullable=True, unique=True),
    CheckConstraint('thick > 0'),
    CheckConstraint('target > 0'),
    CheckConstraint('divergence >= 0'),
    UniqueConstraint('jig', 'heat', 'thick', 'target', name='uq_candidate_condition'),
)
