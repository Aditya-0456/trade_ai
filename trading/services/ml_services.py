import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = "model.pkl"

def prepare_features(df):
    df = df.copy()

    df['returns'] = df['close'].pct_change()
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_10'] = df['close'].rolling(10).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['volatility'] = df['returns'].rolling(5).std()
    df['momentum'] = df['close'] - df['close'].shift(5)

    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)

    df = df.dropna()

    return df


def train_model(df):
    df = prepare_features(df)

    X = df[['returns','ma_5','ma_10','ma_20','volatility','momentum']]
    y = df['target']

    split = int(len(df) * 0.8)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=5,
        min_samples_split=10,
        random_state=42
    )

    model.fit(X[:split], y[:split])

    joblib.dump(model, MODEL_PATH)

    return model


def load_model():
    return joblib.load(MODEL_PATH)


def predict_signal(model, df):
    df = prepare_features(df)

    latest = df[['returns','ma_5','ma_10','ma_20','volatility','momentum']].iloc[-1:]

    pred = model.predict(latest)[0]

    return "BUY 📈" if pred == 1 else "SELL 📉"