"""可复算的二次曲线引擎。

生产拟合仍由 ``domain.learning.py`` 的 sklearn Lasso 管线
（PolynomialFeatures → StandardScaler → Lasso）完成；本模块只依赖 Python
标准库，负责两件事：

1. 按签注曲线保存的标准化参数、二次特征系数复算任意候选工况的弯度；
2. 给出曲线训练样本在（保温温度、片厚、目标弯度）上的包络范围，用于判断
   候选工况是否落在训练范围内。

注意标准化发生在二次特征展开之后，因此保存的 means/scales 长度为 9，
与 sklearn 管线里 StandardScaler 的统计口径一致。

为让演示数据在没有 sklearn 的环境里也能复算，这里额外提供一个确定性的
岭回归拟合 ``fit_bundle``，其产物结构与 Lasso 产物一致，可被 ``predict`` 复算。
"""

FEATURES = ('heat', 'thick', 'target')
FEATURE_LABELS = ('温度', '片厚', '目标弯度')
TERM_COUNT = 9


def _poly_terms(point):
    """二次（不含偏置）多项式特征，顺序与 PolynomialFeatures(degree=2) 对齐。"""
    x1, x2, x3 = point['heat'], point['thick'], point['target']
    return [
        x1, x2, x3,
        x1 * x1, x1 * x2, x1 * x3,
        x2 * x2, x2 * x3, x3 * x3,
    ]


def _stats(values):
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    scale = variance ** 0.5
    if scale == 0:  # 与 sklearn StandardScaler 一致：常量列退化为 1。
        scale = 1.0
    return mean, scale


def fit_bundle(rows, alpha=0.035):
    """确定性岭回归拟合二次交互，返回可序列化、可复算的曲线参数。

    刻意贴近 learning.py 的管线：先展开二次特征，再对展开后的特征标准化，
    最后对标准化特征做带 L2 惩罚的最小二乘。
    """
    if len(rows) < 4:
        raise ValueError('已确认历史少于四张，无法拟合二次曲线')
    raw_columns = [[row[name] for row in rows] for name in FEATURES]
    design = [_poly_terms(row) for row in rows]
    targets = [row['measured'] for row in rows]
    means, scales = [], []
    for column in range(TERM_COUNT):
        mean, scale = _stats([row[column] for row in design])
        means.append(mean)
        scales.append(scale)
    standardized = [[(design[r][c] - means[c]) / scales[c] for c in range(TERM_COUNT)]
                    for r in range(len(rows))]
    gram = [[sum(standardized[r][i] * standardized[r][j] for r in range(len(rows)))
             for j in range(TERM_COUNT)] for i in range(TERM_COUNT)]
    for i in range(TERM_COUNT):
        gram[i][i] += alpha
    rhs = [sum(standardized[r][i] * targets[r] for r in range(len(rows)))
           for i in range(TERM_COUNT)]
    coef = _solve(gram, rhs)
    intercept = sum(targets) / len(targets) - sum(
        c * sum(row[i] for row in standardized) / len(rows) for i, c in enumerate(coef))
    bounds = {name: {'min': min(values), 'max': max(values)}
              for name, values in zip(FEATURES, raw_columns)}
    labels = term_labels()
    return {
        'features': list(FEATURES),
        'means': [round(value, 6) for value in means],
        'scales': [round(value, 6) for value in scales],
        'coef': [round(value, 6) for value in coef],
        'intercept': round(intercept, 6),
        'terms': [label for label, value in zip(labels, coef) if abs(value) > 1e-10],
        'bounds': bounds,
    }


def _solve(matrix, vector):
    """高斯-约当消元求解线性方程组。"""
    size = len(vector)
    aug = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError('曲线特征矩阵奇异，无法复算')
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        aug[col] = [value / pivot_value for value in aug[col]]
        for r in range(size):
            if r == col:
                continue
            factor = aug[r][col]
            aug[r] = [a - factor * b for a, b in zip(aug[r], aug[col])]
    return [aug[i][-1] for i in range(size)]


def term_labels():
    x1, x2, x3 = FEATURE_LABELS
    return [x1, x2, x3, f'{x1} {x1}', f'{x1} {x2}', f'{x1} {x3}',
            f'{x2} {x2}', f'{x2} {x3}', f'{x3} {x3}']


def predict(curve, point):
    """按签注曲线参数复算候选工况（heat/thick/target）的弯度。"""
    expanded = _poly_terms(point)
    value = curve['intercept'] + sum(
        coef * ((term - mean) / scale)
        for coef, term, mean, scale in zip(curve['coef'], expanded, curve['means'], curve['scales']))
    return round(float(value), 3)


def in_training_range(curve, point):
    """候选工况的每个特征都要落在该曲线训练样本的闭区间包络内。"""
    bounds = curve.get('bounds')
    if not bounds:
        return False
    return all(bounds[name]['min'] <= point[name] <= bounds[name]['max'] for name in FEATURES)


def recomputable(curve):
    """老版本演示曲线只存了改善说明，缺少复算参数时排除出排序。"""
    if not all(key in curve for key in ('means', 'scales', 'coef', 'intercept', 'bounds')):
        return False
    return len(curve['means']) == TERM_COUNT and len(curve['coef']) == TERM_COUNT
