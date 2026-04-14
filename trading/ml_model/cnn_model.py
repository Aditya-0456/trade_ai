import numpy as np
import cv2
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ChartPatternCNN:
    def __init__(self):
        self.model = None
        self.model_path = Path("models/chart_pattern_cnn.h5")
        self.patterns = ['head_shoulders', 'double_top', 'double_bottom', 'triangle', 'none']
    
    def predict_pattern(self, image_data):
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = cv2.resize(img, (224, 224))
            img = img / 255.0
            
            # Simulate prediction (in production, use actual model)
            import random
            pattern = random.choice(self.patterns)
            confidence = random.uniform(0.5, 0.9)
            
            return {'pattern': pattern, 'confidence': confidence, 'all_predictions': {p: random.uniform(0, 1) for p in self.patterns}}
        except Exception as e:
            logger.error(f"CNN prediction error: {e}")
            return {'pattern': 'error', 'confidence': 0, 'error': str(e)}

cnn_model = ChartPatternCNN()