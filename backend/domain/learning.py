import numpy as np
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from domain.curves import FEATURES, TERM_COUNT

def features(row):
    return [row[key] for key in FEATURES]

def calculate(data):
    archive = sorted(data['history'], key=lambda row: row['heat'])
    holdout = [row for index, row in enumerate(archive) if index % 4 == 0]
    train = [row for index, row in enumerate(archive) if index % 4 != 0]
    model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False),
                          StandardScaler(), Lasso(alpha=data['penalty'],max_iter=20000))
    model.fit([features(row) for row in train], [row['measured'] for row in train])
    errors = model.predict([features(row) for row in holdout]) - [row['measured'] for row in holdout]
    poly, scaler, lasso = model[0], model[1], model[-1]
    terms = poly.get_feature_names_out(list(FEATURES))
    # 导出完整管线参数，签注后可在无 sklearn 的复算侧（domain.curves）原样复算。
    # 标准化作用于展开后的 9 个二次特征，因此 means/scales 长度为 9。
    assert len(scaler.mean_) == TERM_COUNT
    history = data['history'] + [data['coupon']]
    bounds = {name: {'min': min(row[name] for row in history),
                     'max': max(row[name] for row in history)} for name in FEATURES}
    return {'prediction': round(float(model.predict([features(data['coupon'])])[0]),3),
            'mae': round(float(np.mean(np.abs(errors))),3), 'held_out': len(holdout),
            'terms': [term for term, coef in zip(terms, lasso.coef_) if abs(coef) > 1e-10],
            'features': list(FEATURES),
            'means': [round(float(value), 6) for value in scaler.mean_],
            'scales': [round(float(value), 6) for value in scaler.scale_],
            'coef': [round(float(value), 6) for value in lasso.coef_],
            'intercept': round(float(lasso.intercept_), 6),
            'bounds': bounds}
