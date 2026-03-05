import numpy as np
from dataclasses import dataclass
from enum import Enum

class PatternType(str, Enum):
    FIXED_SEASONALITY = "fixed_seasonality"
    VARYING_SEASONALITY = "varying_seasonality"
    SLOW_TREND = "slow_trend"
    SUDDEN_SPIKE = "sudden_spike"
    SUDDEN_DIP = "sudden_dip"
    STABLE_FLAT = "stable_flat"
    HIGH_VOLATILITY = "high_volatility"
    COMPLEX = "complex"

@dataclass
class PatternResult:
    pattern_type: PatternType
    confidence: float
    metrics: dict

class PatternClassifier:
    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or {
            "seasonality_stability": 2.0,
            "trend_slope": 0.5,
            "volatility": 0.3,
            "spike_zscore": 3.0,
            "stability_cv": 0.1,
        }
    
    def classify(self, features: dict, signal: np.ndarray) -> PatternResult:
        scores = self._compute_pattern_scores(features, signal)
        pattern_type, confidence = self._select_pattern(scores)
        return PatternResult(pattern_type=pattern_type, confidence=confidence, metrics=scores)
    
    def _compute_pattern_scores(self, features: dict, signal: np.ndarray) -> dict:
        cv = features["stat_std"] / (abs(features["stat_mean"]) + 1e-8)
        return {
            "seasonality_fixed": self._score_fixed_seasonality(features),
            "seasonality_varying": self._score_varying_seasonality(features),
            "trend": self._score_trend(features),
            "spike": self._score_spike(signal),
            "dip": self._score_dip(signal),
            "stability": self._score_stability(cv),
            "volatility": self._score_volatility(cv, features),
        }
    
    def _score_fixed_seasonality(self, f: dict) -> float:
        stability = f.get("stft_frequency_stability", 0)
        energy_concentration = f.get("wavelet_energy_concentration", 0)
        return min(1.0, (stability / 10) * 0.5 + energy_concentration * 0.5)
    
    def _score_varying_seasonality(self, f: dict) -> float:
        freq_drift = f.get("hht_freq_drift", 0)
        freq_std = f.get("stft_dominant_freq_std", 0)
        return min(1.0, freq_drift * 0.5 + freq_std * 0.5)
    
    def _score_trend(self, f: dict) -> float:
        slope = abs(f.get("stat_trend_slope", 0))
        return min(1.0, slope / self.thresholds["trend_slope"])
    
    def _score_spike(self, signal: np.ndarray) -> float:
        z = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        return min(1.0, max(0, np.max(z) - 2) / 2)
    
    def _score_dip(self, signal: np.ndarray) -> float:
        z = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        return min(1.0, max(0, -np.min(z) - 2) / 2)
    
    def _score_stability(self, cv: float) -> float:
        return max(0, 1 - cv / self.thresholds["stability_cv"])
    
    def _score_volatility(self, cv: float, f: dict) -> float:
        flux = f.get("stft_flux_mean", 0)
        return min(1.0, cv / self.thresholds["volatility"] * 0.5 + flux * 0.5)
    
    def _select_pattern(self, scores: dict) -> tuple[PatternType, float]:
        pattern_map = [
            ("stability", PatternType.STABLE_FLAT),
            ("seasonality_fixed", PatternType.FIXED_SEASONALITY),
            ("seasonality_varying", PatternType.VARYING_SEASONALITY),
            ("trend", PatternType.SLOW_TREND),
            ("spike", PatternType.SUDDEN_SPIKE),
            ("dip", PatternType.SUDDEN_DIP),
            ("volatility", PatternType.HIGH_VOLATILITY),
        ]
        best_score, best_pattern = 0.0, PatternType.COMPLEX
        for key, pattern in pattern_map:
            if scores[key] > best_score and scores[key] > 0.4:
                best_score, best_pattern = scores[key], pattern
        return best_pattern, best_score