import numpy as np
import pandas as pd
from dataclasses import dataclass
from .classifier import PatternResult, PatternType

@dataclass
class ValidationResult:
    product_id: str
    detected_pattern: str
    confidence: float
    overlay_r2: float
    fit_quality: str
    recommendation: str
    pattern_details: dict

class PatternValidator:
    def validate(self, product_id: str, signal: np.ndarray, pattern: PatternResult, dates: pd.Series) -> ValidationResult:
        overlay = self._generate_overlay(signal, pattern)
        r2 = self._compute_r2(signal, overlay)
        fit_quality = self._assess_fit(r2, pattern.confidence)
        recommendation = self._generate_recommendation(r2, pattern.confidence)
        details = self._extract_pattern_details(signal, pattern, dates)
        
        return ValidationResult(
            product_id=product_id, detected_pattern=pattern.pattern_type.value,
            confidence=pattern.confidence, overlay_r2=r2, fit_quality=fit_quality,
            recommendation=recommendation, pattern_details=details
        )
    
    def _generate_overlay(self, signal: np.ndarray, pattern: PatternResult) -> np.ndarray:
        n, t = len(signal), np.arange(len(signal))
        
        if pattern.pattern_type == PatternType.STABLE_FLAT:
            return np.full(n, np.mean(signal))
        elif pattern.pattern_type == PatternType.SLOW_TREND:
            slope, intercept = np.polyfit(t, signal, 1)
            return slope * t + intercept
        elif pattern.pattern_type in (PatternType.FIXED_SEASONALITY, PatternType.VARYING_SEASONALITY):
            period = 12
            seasonal = np.array([np.mean(signal[i::period]) for i in range(period)])
            overlay = np.tile(seasonal, n // period + 1)[:n]
            trend = np.polyval(np.polyfit(t, signal, 1), t)
            return overlay + trend - np.mean(trend)
        return np.full(n, np.mean(signal))
    
    def _compute_r2(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        return max(0, 1 - ss_res / (ss_tot + 1e-8))
    
    def _assess_fit(self, r2: float, confidence: float) -> str:
        combined = 0.6 * r2 + 0.4 * confidence
        if combined >= 0.8: return "excellent"
        elif combined >= 0.6: return "good"
        elif combined >= 0.4: return "fair"
        return "poor"
    
    def _generate_recommendation(self, r2: float, confidence: float) -> str:
        if r2 >= 0.7 and confidence >= 0.7: return "high_confidence"
        elif r2 >= 0.5 and confidence >= 0.5: return "medium_confidence"
        elif r2 >= 0.3 or confidence >= 0.3: return "low_confidence"
        return "needs_review"
    
    def _extract_pattern_details(self, signal: np.ndarray, pattern: PatternResult, dates: pd.Series) -> dict:
        details = {
            "start_date": str(dates.iloc[0]), "end_date": str(dates.iloc[-1]),
            "window_months": len(signal), "avg_sales": float(np.mean(signal)),
            "min_sales": float(np.min(signal)), "max_sales": float(np.max(signal)),
        }
        
        if pattern.pattern_type == PatternType.SLOW_TREND:
            slope = np.polyfit(np.arange(len(signal)), signal, 1)[0]
            pct_change = (signal[-1] - signal[0]) / (signal[0] + 1e-8) * 100
            details["trend_direction"] = "increasing" if slope > 0 else "decreasing"
            details["trend_pct_change"] = round(pct_change, 2)
        
        elif pattern.pattern_type in (PatternType.FIXED_SEASONALITY, PatternType.VARYING_SEASONALITY):
            monthly_avg = [np.mean(signal[i::12]) for i in range(min(12, len(signal)))]
            details["peak_month"] = int(np.argmax(monthly_avg)) + 1
            details["trough_month"] = int(np.argmin(monthly_avg)) + 1
            details["seasonal_swing_pct"] = round((max(monthly_avg) - min(monthly_avg)) / (np.mean(signal) + 1e-8) * 100, 2)
        
        elif pattern.pattern_type == PatternType.SUDDEN_SPIKE:
            z = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
            spike_indices = np.where(z > 2)[0]
            details["spike_count"] = len(spike_indices)
            if len(spike_indices) > 0:
                details["spike_dates"] = [str(dates.iloc[i]) for i in spike_indices[:5]]
        
        elif pattern.pattern_type == PatternType.SUDDEN_DIP:
            z = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
            dip_indices = np.where(z < -2)[0]
            details["dip_count"] = len(dip_indices)
            if len(dip_indices) > 0:
                details["dip_dates"] = [str(dates.iloc[i]) for i in dip_indices[:5]]
        
        return details