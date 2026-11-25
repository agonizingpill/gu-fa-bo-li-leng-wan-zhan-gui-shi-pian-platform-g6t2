# 古法玻璃冷弯展柜试片台

棠镜玻璃试制组保留每次冷却后的实弯读数，根据材料交互修订曲线并安排唯一试制机位。

## 现场工作与联系人

模拟客户为棠镜玻璃试制组。夹具登记、温区试片、交互项比较、打样委托；夹具有效行程不足拒排且不占机位。

- 弯模与行程 `jigs`，字段为 `spread`（台面跨度 mm）、`max_throw`（最大行程 mm）、`calibrated`（量具在校）。模型约束位于 `backend/domain/jigs_model.py`，规则位于 `jigs_service.py`。
- 温区试片 `coupons`，字段为 `jig`（弯模）、`heat`（保温温度 °C）、`thick`（片厚 mm）、`target`（目标弯度 mm）、`measured`（冷却弯度 mm）、`locked`（已确认）。模型约束位于 `backend/domain/coupons_model.py`，规则位于 `coupons_service.py`。
- 预测曲线签注 `profiles`，字段为 `coupon`（基准试片）、`prediction`（拟合弯度 mm）、`mae`（留出 MAE mm）、`curve`（改善说明）、`token`（拟合编号）。模型约束位于 `backend/domain/profiles_model.py`，规则位于 `profiles_service.py`。
- 试制工位委托 `work_orders`，字段为 `profile`（依据）、`jig`（工位弯模）、`slot`（机位时段）、`quantity`（试片数）、`state`（状态）。模型约束位于 `backend/domain/work_orders_model.py`，规则位于 `work_orders_service.py`。
- 补测候选与领片 `supplement_candidates`，字段为 `jig`（弯模）、`heat/thick/target`（候选工况）、`profile_a/profile_b`（最新两条签注曲线）、`prediction_a/prediction_b`（两条复算预测）、`divergence`（曲线分歧）、`rank`（分歧名次）、`status`（待领片/已领片/已登记/已见证）、`claimed_by`（领取人）、`coupon`（补测试片）。模型约束位于 `backend/domain/supplements_model.py`，规则位于 `supplements_service.py`。补测试片写在 `coupons` 中，以 `source='补测领片'` 区分，`claim_snapshot` 留档领片时的两条曲线预测；冷却读数允许先空、登记一次后见证锁定。

团队为模拟的6 人打样组，负责展柜旧式玻璃的冷弯样件。

试制员分开记尺规、片厚和热区读数。换夹具后有效行程容易漏核，两个参数的互相影响难从单列趋势看出，打样回执难追到原试片。

夹具检定和历史试片进入比较工作台，打样师领取附试片依据的委托单。

### 一天的业务操作

1. 08:35 在 CL-08 上校验量具，记录 25 mm 行程。
2. 09:10 用 CL-44 测量 GP-NEW 的 4 mm 玻璃冷却弯度 8.4 mm。
3. 10:20 复核员查验尺规并确认 GP-NEW。
4. 11:10 以 0.035 正则强度计算温区拟合。
5. 13:00 签注 PRO-24，核对留出误差。
6. 14:10 CL-18 有效行程不足，拒绝机位委托；换用 CL-44。
7. 16:20 核对 W-0302 完成打样。

## 启动

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

打开 `http://127.0.0.1:18306`。FastAPI OpenAPI 在 `http://127.0.0.1:19306/docs`。
Compose 运行 Nginx、Python FastAPI、独立 Redis 消费进程、SQL 数据库和 Redis，SQL 与 Redis 使用命名卷。
本机开发时，在 Python 3.11 环境安装 `backend/requirements.txt` 后从 backend 目录运行 `uvicorn core.app:app`。须提供 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET`，`SEED_DEMO` 控制演示初始化。

| 演示账号 | 权限 |
|---|---|
| operator@demo.test | 提交领域记录和计算请求 |
| reviewer@demo.test | 提交记录并执行有业务约束的复核操作 |
| viewer@demo.test | 浏览业务台账 |

三个本地演示账号均使用 `DemoC0de!2026`。角色在 `backend/core/roles.py` 和 `frontend/src/store.js` 中声明。计算状态在 worker、queueing、API 和同一前端 store 中使用。

## 页面与接口

| 业务任务 | FastAPI 路由 | 页面 |
|---|---|---|
| 弯模与行程 | `/jigs` /jigs/calibrate | `frontend/src/pages/jigs.js` |
| 温区试片 | `/coupons` /coupons/record-coupon，/coupons/witness | `frontend/src/pages/coupons.js` |
| 预测曲线签注 | `/profiles` /profiles/fit-curve，/profiles/sign-profile | `frontend/src/pages/profiles.js` |
| 试制工位委托 | `/work_orders` /work_orders/book-jig，/work_orders/complete | `frontend/src/pages/work_orders.js` |
| 补测领片 | `/supplements` /supplements/register-candidate，/supplements/claim，/supplements/record-reading，/supplements/witness | `frontend/src/pages/supplements.js` |

SQL 实体与约束在 `backend/domain` 下维护。前端使用原生 ES modules。核心算子为 PolynomialFeatures + Lasso。算法按温度排序每四条留出一条；训练拟合二次多项式和标准化。报告使用 mm 和可复现特征系数。

曲线分歧补测只取最新两条可复算签注曲线（`profiles.id` 自增序号倒序）。候选工况（炉温、片厚、目标弯度）必须同时落在两条曲线训练样本的特征包络内才参与排序，按两条复算预测之差的绝对值自高到低编号。领片在 Postgres 上以 `FOR UPDATE` 行锁配合“仅待领片可更新”的条件 UPDATE 串行化，两人同时提交各拿不同工况，同一人重试返回其手上尚未见证的同一片。签注曲线在 `curve` 中保存标准化参数、九项二次特征系数与训练范围，`backend/domain/curves.py` 为纯标准库复算侧，与 worker 的 sklearn 管线导出参数一致。

数据为模拟试制记录。工单留在本地数据库供核查。

[MIT](LICENSE)
