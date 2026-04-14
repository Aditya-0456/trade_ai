from .lightgbm_model import LightGBMModel
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.models = {}
    
    def get_model(self, symbol):
        if symbol not in self.models:
            self.models[symbol] = LightGBMModel(symbol)
        return self.models[symbol]
    
    def train_for_symbol(self, symbol, df):
        model = self.get_model(symbol)
        return model.train(df)
    
    def predict_for_symbol(self, symbol, df):
        model = self.get_model(symbol)
        return model.predict(df)

model_trainer = ModelTrainer()