import lightgbm as lgb
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class LightGBMModel:
    def __init__(self, symbol):
        self.symbol = symbol
        self.model = None
        self.model_path = Path(f"models/lightgbm_{symbol}.pkl")
    
    def create_features(self, df):
        features = pd.DataFrame(index=df.index)
        for period in [1, 2, 3, 5, 10, 20]:
            features[f'return_{period}'] = df['close'].pct_change(period)
        for period in [5, 10, 20]:
            features[f'sma_{period}'] = df['close'].rolling(period).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        features['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        return features.dropna()
    
    def train(self, df):
        features = self.create_features(df)
        if len(features) < 100:
            return {'success': False, 'error': 'Insufficient data'}
        X = features.drop('target', axis=1)
        y = features['target']
        self.model = lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.01, verbose=-1)
        self.model.fit(X, y)
        self.model_path.parent.mkdir(exist_ok=True)
        joblib.dump(self.model, self.model_path)
        return {'success': True, 'accuracy': self.model.score(X, y)}
    
    def predict(self, df):
        if self.model is None and self.model_path.exists():
            self.model = joblib.load(self.model_path)
        if self.model is None:
            return 0.5
        features = self.create_features(df)
        if len(features) == 0:
            return 0.5
        X = features.drop('target', axis=1).iloc[-1:].values
        return float(self.model.predict_proba(X)[0][1])