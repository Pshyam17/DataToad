import numpy as np
import pandas as pd
from dataclasses import dataclass
from src.detection.classifier import PatternType

@dataclass
class ForecastResult:
    product_id: str
    dates: list[str]
    values: list[float]
    lower_bound: list[float]
    upper_bound: list[float]
    method: str
    confidence_interval: float

class PatternForecaster:
    def __init__(self, confidence_interval: float = 0.95):
        self.ci = confidence_interval
        self.z_score = 1.96 if confidence_interval == 0.95 else 1.645
    
    def forecast(self, product_id: str, signal: np.ndarray, pattern_type: PatternType,
                 last_date: pd.Timestamp, horizon: int = 6) -> ForecastResult:
        method_map = {
            PatternType.STABLE_FLAT: self._forecast_stable,
            PatternType.SLOW_TREND: self._forecast_trend,
            PatternType.FIXED_SEASONALITY: self._forecast_seasonal,
            PatternType.VARYING_SEASONALITY: self._forecast_seasonal,
            PatternType.HIGH_VOLATILITY: self._forecast_volatile,
        }
        method = method_map.get(pattern_type, self._forecast_naive)
        values, std = method(signal, horizon)
        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq='MS')
        
        return ForecastResult(
            product_id=product_id, dates=[str(d.date()) for d in future_dates],
            values=[round(v, 2) for v in values],
            lower_bound=[round(v - self.z_score * std, 2) for v in values],
            upper_bound=[round(v + self.z_score * std, 2) for v in values],
            method=pattern_type.value, confidence_interval=self.ci
        )
    
    def _forecast_stable(self, signal: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
        return np.full(horizon, np.mean(signal)), np.std(signal)
    
    def _forecast_trend(self, signal: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
        t = np.arange(len(signal))
        slope, intercept = np.polyfit(t, signal, 1)
        future_t = np.arange(len(signal), len(signal) + horizon)
        forecast = slope * future_t + intercept
        residuals = signal - (slope * t + intercept)
        return forecast, np.std(residuals)
    
    def _forecast_seasonal(self, signal: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
        period, n = 12, len(signal)
        t = np.arange(n)
        slope, intercept = np.polyfit(t, signal, 1)
        detrended = signal - (slope * t + intercept)
        seasonal = np.array([np.mean(detrended[i::period]) for i in range(period)])
        
        forecast = []
        for h in range(horizon):
            month_idx = (n + h) % period
            trend_value = slope * (n + h) + intercept
            forecast.append(trend_value + seasonal[month_idx])
        
        residuals = detrended - np.tile(seasonal, n // period + 1)[:n]
        return np.array(forecast), np.std(residuals)
    
    def _forecast_volatile(self, signal: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
        recent = signal[-12:] if len(signal) >= 12 else signal
        return np.full(horizon, np.mean(recent)), np.std(recent) * 1.5
    
    def _forecast_naive(self, signal: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
        recent = signal[-3:] if len(signal) >= 3 else signal
        return np.full(horizon, np.mean(recent)), np.std(signal)