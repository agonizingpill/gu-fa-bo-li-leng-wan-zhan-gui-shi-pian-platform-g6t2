from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table, UniqueConstraint

from core.db import metadata


coupons = Table('coupons', metadata,
    Column('code', String(64), primary_key=True),
    Column('jig', String(160), ForeignKey('jigs.code'), nullable=False),
    Column('heat', Float, nullable=False),
    Column('thick', Float, nullable=False),
    Column('target', Float, nullable=False),
    # 补测领片先建账、冷却后才登记读数，因此实测弯度允许为空。
    Column('measured', Float, nullable=True),
    Column('locked', Boolean, nullable=False),
    # 来源：常规冷却登记或补测领片；领片时两条签注曲线的预测随单留档。
    Column('source', String(32), nullable=False, default='常规'),
    Column('claim_snapshot', JSON, nullable=True),
    CheckConstraint('thick > 0'),
    CheckConstraint('measured is null or measured >= 0'),
    CheckConstraint('target > 0'),
)
