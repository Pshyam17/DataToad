import numpy as np
import pywt
from dataclasses import dataclass
from src.config import get_settings

@dataclass
class WaveletFeatures:
    coefficients: np.ndarray
    scales: np.ndarray
    energy_by_scale: np.ndarray
    max_coefficient_time: np.ndarray
    total_energy: float
    dominant_scale: int

class WaveletTransform:
    def __init__(self, wavelet: str = "morl", max_scale: int = None):
        settings = get_settings()
        self.wavelet = wavelet
        self.max_scale = max_scale or settings.wavelet_max_scale
    
    def extract(self, signal: np.ndarray) -> WaveletFeatures:
        signal = np.asarray(signal, dtype=np.float64)
        signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        
        scales = np.arange(1, min(self.max_scale + 1, len(signal) // 2))
        coefficients, _ = pywt.cwt(signal, scales, self.wavelet)
        
        energy_by_scale = np.sum(np.abs(coefficients) ** 2, axis=1)
        max_coefficient_time = np.argmax(np.abs(coefficients), axis=1)
        total_energy = float(np.sum(energy_by_scale))
        dominant_scale = int(scales[np.argmax(energy_by_scale)])
        
        return WaveletFeatures(
            coefficients=coefficients,
            scales=scales,
            energy_by_scale=energy_by_scale,
            max_coefficient_time=max_coefficient_time,
            total_energy=total_energy,
            dominant_scale=dominant_scale
        )
    
    def to_dict(self, features: WaveletFeatures) -> dict:
        return {
            "wavelet_total_energy": features.total_energy,
            "wavelet_dominant_scale": features.dominant_scale,
            "wavelet_energy_low_scales": float(np.sum(features.energy_by_scale[:len(features.scales)//3])),
            "wavelet_energy_mid_scales": float(np.sum(features.energy_by_scale[len(features.scales)//3:2*len(features.scales)//3])),
            "wavelet_energy_high_scales": float(np.sum(features.energy_by_scale[2*len(features.scales)//3:])),
            "wavelet_energy_concentration": float(np.max(features.energy_by_scale) / (features.total_energy + 1e-8)),
        }