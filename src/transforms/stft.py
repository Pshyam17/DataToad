import numpy as np
from scipy.signal import stft
from dataclasses import dataclass
from src.config import get_settings

@dataclass
class STFTFeatures:
    dominant_frequencies: np.ndarray
    spectral_energy: np.ndarray
    spectral_centroid: np.ndarray
    spectral_flux: np.ndarray
    frequency_stability: float
    time_bins: np.ndarray
    freq_bins: np.ndarray

class STFTTransform:
    def __init__(self, fs: int = None, nperseg: int = None, noverlap: int = None):
        settings = get_settings()
        self.fs = fs or 12
        self.nperseg = nperseg or settings.stft_nperseg
        self.noverlap = noverlap or settings.stft_noverlap
    
    def extract(self, signal: np.ndarray) -> STFTFeatures:
        signal = np.asarray(signal, dtype=np.float64)
        signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        
        f, t, Zxx = stft(signal, fs=self.fs, nperseg=self.nperseg, noverlap=self.noverlap)
        magnitude = np.abs(Zxx)
        
        dominant_freq_idx = np.argmax(magnitude, axis=0)
        dominant_frequencies = f[dominant_freq_idx]
        spectral_energy = np.sum(magnitude ** 2, axis=0)
        
        freq_matrix = f[:, np.newaxis] * np.ones((1, magnitude.shape[1]))
        spectral_centroid = np.sum(freq_matrix * magnitude, axis=0) / (np.sum(magnitude, axis=0) + 1e-8)
        
        spectral_flux = np.zeros(len(t))
        spectral_flux[1:] = np.sqrt(np.sum(np.diff(magnitude, axis=1) ** 2, axis=0))
        
        frequency_stability = 1.0 / (np.std(dominant_frequencies) + 1e-8)
        
        return STFTFeatures(
            dominant_frequencies=dominant_frequencies,
            spectral_energy=spectral_energy,
            spectral_centroid=spectral_centroid,
            spectral_flux=spectral_flux,
            frequency_stability=frequency_stability,
            time_bins=t,
            freq_bins=f
        )
    
    def to_dict(self, features: STFTFeatures) -> dict:
        return {
            "stft_dominant_freq_mean": float(np.mean(features.dominant_frequencies)),
            "stft_dominant_freq_std": float(np.std(features.dominant_frequencies)),
            "stft_energy_mean": float(np.mean(features.spectral_energy)),
            "stft_energy_std": float(np.std(features.spectral_energy)),
            "stft_centroid_mean": float(np.mean(features.spectral_centroid)),
            "stft_flux_mean": float(np.mean(features.spectral_flux)),
            "stft_frequency_stability": float(features.frequency_stability),
        }