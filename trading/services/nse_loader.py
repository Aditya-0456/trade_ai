import pandas as pd
from pathlib import Path
from django.conf import settings
from ..models import NSEStock

class NSELoader:
    @staticmethod
    def load_from_csv():
        csv_path = Path(settings.BASE_DIR) / 'NSE.csv'
        if not csv_path.exists():
            print(f"NSE.csv not found at {csv_path}")
            return False
        try:
            df = pd.read_csv(csv_path)
            symbol_col = None
            for col in ['SYMBOL', 'SYMBOL_NAME', 'NAME', 'TICKER']:
                if col in df.columns:
                    symbol_col = col
                    break
            if not symbol_col:
                symbol_col = df.columns[0]
            NSEStock.objects.all().delete()
            count = 0
            for _, row in df.iterrows():
                symbol = str(row[symbol_col]).strip().upper()
                if symbol and symbol != 'NAN' and len(symbol) <= 20:
                    NSEStock.objects.create(symbol=symbol, name=row.get('NAME_OF_COMPANY', row.get('COMPANY_NAME', ''))[:200])
                    count += 1
                    if count >= 500:
                        break
            print(f"Loaded {count} NSE stocks")
            return True
        except Exception as e:
            print(f"Error loading NSE.csv: {e}")
            return False
    
    @staticmethod
    def get_active_symbols():
        return list(NSEStock.objects.filter(is_active=True).values_list('symbol', flat=True))