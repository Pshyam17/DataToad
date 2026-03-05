import numpy as np
import pandas as pd
from typing import Iterator
from .stft import STFTTransform
from .wavelet import WaveletTransform
from .hht import HHTTransform

class TransformPipeline:
    def __init__(self):
        self.stft = STFTTransform()
        self.wavelet = WaveletTransform()
        self.hht = HHTTransform()
    
    def extract_features(self, signal: np.ndarray) -> dict:
        stft_features = self.stft.extract(signal)
        wavelet_features = self.wavelet.extract(signal)
        hht_features = self.hht.extract(signal)
        
        combined = {}
        combined.update(self.stft.to_dict(stft_features))
        combined.update(self.wavelet.to_dict(wavelet_features))
        combined.update(self.hht.to_dict(hht_features))
        combined.update(self._extract_statistical_features(signal))
        
        return combined
    
    def _extract_statistical_features(self, signal: np.ndarray) -> dict:
        return {
            "stat_mean": float(np.mean(signal)),
            "stat_std": float(np.std(signal)),
            "stat_min": float(np.min(signal)),
            "stat_max": float(np.max(signal)),
            "stat_range": float(np.max(signal) - np.min(signal)),
            "stat_skewness": float(self._skewness(signal)),
            "stat_kurtosis": float(self._kurtosis(signal)),
            "stat_trend_slope": float(np.polyfit(np.arange(len(signal)), signal, 1)[0]),
        }
    
    def _skewness(self, x: np.ndarray) -> float:
        n, mean, std = len(x), np.mean(x), np.std(x)
        return np.sum(((x - mean) / (std + 1e-8)) ** 3) / n
    
    def _kurtosis(self, x: np.ndarray) -> float:
        n, mean, std = len(x), np.mean(x), np.std(x)
        return np.sum(((x - mean) / (std + 1e-8)) ** 4) / n - 3
    
    def process_dataframe(self, df: pd.DataFrame, product_col: str, date_col: str, value_col: str) -> Iterator[dict]:
        for product_id, group in df.groupby(product_col):
            group = group.sort_values(date_col)
            signal = group[value_col].values
            
            if len(signal) < 12:
                continue
            
            features = self.extract_features(signal)
            features["product_id"] = product_id
            features["start_date"] = str(group[date_col].iloc[0])
            features["end_date"] = str(group[date_col].iloc[-1])
            features["num_observations"] = len(signal)
            
            yield features