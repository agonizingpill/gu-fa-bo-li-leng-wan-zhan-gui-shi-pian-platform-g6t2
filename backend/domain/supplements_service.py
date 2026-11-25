from fastapi import HTTPException
from sqlalchemy import select

from core.records import get, insert, need, update
from domain import curves
from domain.coupons_model import coupons
from domain.jigs_model import jigs
from domain.profiles_model import profiles
from domain.supplements_model import supplement_candidates

# 与 coupons_service 保持一致的试制保温与片厚档范围。
HEAT_RANGE = (350.0, 650.0)
THICK_RANGE = (1.5, 10.0)


def _point(data):
    return {'heat': data.heat, 'thick': data.thick, 'target': data.target}


def _latest_pair(conn):
    """取最新两条签注曲线（按自增序号倒序），并要求都可复算。"""
    rows = [dict(row) for row in conn.execute(
        select(profiles).order_by(profiles.c.id.desc()).limit(2)).mappings()]
    need(len(rows) == 2, '可复算的签注曲线不足两条，无法安排分歧补测')
    for row in rows:
        need(curves.recomputable(row['curve']), f'曲线 {row["code"]} 缺少复算参数，不能参与排序')
    return rows[0], rows[1]  # 较新、次新


def register_candidate(conn, user, data):
    jig = get(conn, jigs, data.jig)
    need(jig['calibrated'], '弯模量具尚未确认')
    need(HEAT_RANGE[0] <= data.heat <= HEAT_RANGE[1]
         and THICK_RANGE[0] <= data.thick <= THICK_RANGE[1], '超出试制保温或片厚范围')
    need(0 < data.target <= jig['max_throw'], '候选目标弯度超过弯模行程')

    point = _point(data)
    newer, older = _latest_pair(conn)
    # 两条曲线均能复算且工况落在各自训练范围内，才允许进入排序。
    for profile in (newer, older):
        need(curves.in_training_range(profile['curve'], point),
             f'工况落在曲线 {profile["code"]} 的训练范围之外')
    pred_newer = curves.predict(newer['curve'], point)
    pred_older = curves.predict(older['curve'], point)
    divergence = round(abs(pred_newer - pred_older), 3)

    existing = conn.execute(select(supplement_candidates).where(
        supplement_candidates.c.jig == data.jig,
        supplement_candidates.c.heat == data.heat,
        supplement_candidates.c.thick == data.thick,
        supplement_candidates.c.target == data.target)).mappings().first()
    if existing is not None:
        # 同一工况重复提交直接返回既有候选，不重复建账。
        return dict(existing)

    insert(conn, supplement_candidates, code=data.code, jig=data.jig, heat=data.heat,
            thick=data.thick, target=data.target, profile_a=newer['code'], profile_b=older['code'],
            prediction_a=pred_newer, prediction_b=pred_older, divergence=divergence,
            rank=0, status='待领片')
    _rerank(conn, data.jig, newer['code'], older['code'])
    return get(conn, supplement_candidates, data.code)


def _rerank(conn, jig, profile_a, profile_b):
    """同一弯模、同一对曲线的待领片候选按分歧自高到低重新编号。"""
    rows = [dict(row) for row in conn.execute(select(supplement_candidates).where(
        supplement_candidates.c.jig == jig,
        supplement_candidates.c.profile_a == profile_a,
        supplement_candidates.c.profile_b == profile_b,
        supplement_candidates.c.status == '待领片').order_by(
        supplement_candidates.c.divergence.desc(),
        supplement_candidates.c.code.asc())).mappings()]
    for index, row in enumerate(rows, start=1):
        conn.execute(supplement_candidates.update().where(
            supplement_candidates.c.code == row['code']).values(rank=index))


def claim(conn, user):
    """领取剩余最靠前（rank 最小）的待领片工况；重试不重复领片。"""
    owner = user['sub']
    # 仅尚未见证（已领片或已登记）的工况算手上占用；已见证后该人可继续领下一片。
    mine = conn.execute(select(supplement_candidates).where(
        supplement_candidates.c.claimed_by == owner,
        supplement_candidates.c.status.in_(('已领片', '已登记')))
        .order_by(supplement_candidates.c.rank.asc()).with_for_update()).mappings().first()
    if mine is not None:
        # 同一人重试或重复提交：返回其手上尚未见证的工况，不再占新片。
        return dict(mine)

    # 行级 FOR UPDATE 在 Postgres 上串行化并发领片；再叠加“仅待领片可更新”的
    # 条件 UPDATE 兜底，保证任何后端下两人同时提交都不会领到同一片。
    while True:
        candidate = conn.execute(select(supplement_candidates).where(
            supplement_candidates.c.status == '待领片')
            .order_by(supplement_candidates.c.rank.asc(), supplement_candidates.c.code.asc())
            .with_for_update()).mappings().first()
        if candidate is None:
            raise HTTPException(409, detail='暂无可领取的补测工况')
        candidate = dict(candidate)
        coupon_code = 'SP-' + candidate['code']
        snapshot = {
            '候选工况': candidate['code'], '弯模': candidate['jig'],
            '保温温度': candidate['heat'], '片厚': candidate['thick'], '目标弯度': candidate['target'],
            candidate['profile_a']: candidate['prediction_a'],
            candidate['profile_b']: candidate['prediction_b'],
            '曲线分歧mm': candidate['divergence'], '领取人': owner,
        }
        result = conn.execute(supplement_candidates.update().where(
            supplement_candidates.c.code == candidate['code'],
            supplement_candidates.c.status == '待领片').values(
            status='已领片', claimed_by=owner, coupon=coupon_code))
        if result.rowcount == 0:
            # 并发下被另一人抢先领取，顺延到下一个最靠前工况。
            continue
        insert(conn, coupons, code=coupon_code, jig=candidate['jig'], heat=candidate['heat'],
               thick=candidate['thick'], target=candidate['target'], measured=None, locked=False,
               source='补测领片', claim_snapshot=snapshot)
        return get(conn, supplement_candidates, candidate['code'])


def record_reading(conn, user, data):
    """领到的工况只登记一次冷却读数。"""
    candidate = get(conn, supplement_candidates, data.candidate, lock=True)
    coupon = get(conn, coupons, candidate['coupon'], lock=True)
    need(coupon['measured'] is None, '冷却读数已登记，每张补测片只允许登记一次')
    need(candidate['status'] == '已领片', '该工况未处于待登记读数状态')
    jig = get(conn, jigs, coupon['jig'])
    need(0 <= data.measured <= jig['max_throw'], '冷却弯度超过弯模行程')
    update(conn, coupons, coupon['code'], measured=data.measured)
    return update(conn, supplement_candidates, data.candidate, status='已登记')


def witness(conn, user, data):
    """复核见证后补测片才进入拟合训练账。"""
    candidate = get(conn, supplement_candidates, data.candidate, lock=True)
    need(candidate['status'] == '已登记', '须先登记唯一一次冷却读数再见证')
    coupon = get(conn, coupons, candidate['coupon'], lock=True)
    need(coupon['measured'] is not None, '冷却读数缺失，不能见证')
    update(conn, coupons, coupon['code'], locked=True)
    return update(conn, supplement_candidates, data.candidate, status='已见证')


def list_candidates(conn):
    return [dict(row) for row in conn.execute(select(supplement_candidates).order_by(
        supplement_candidates.c.jig.asc(), supplement_candidates.c.rank.asc(),
        supplement_candidates.c.code.asc())).mappings()]
