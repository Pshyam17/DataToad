import numpy as np
from PyEMD import EMD
from scipy.signal import hilbert
from dataclasses import dataclass
from src.config import get_settings

@dataclass
class HHTFeatures:
    imfs: np.ndarray
    instantaneous_frequencies: list[np.ndarray]
    instantaneous_amplitudes: list[np.ndarray]
    num_imfs: int
    dominant_imf_idx: int
    mean_frequencies: np.ndarray

class HHTTransform:
    def __init__(self, max_imfs: int = None):
        settings = get_settings()
        self.max_imfs = max_imfs or settings.hht_max_imfs
        self.emd = EMD()
    
    def extract(self, signal: np.ndarray, fs: int = 12) -> HHTFeatures:
        signal = np.asarray(signal, dtype=np.float64)
        signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-8)
        
        imfs = self.emd.emd(signal, max_imf=self.max_imfs)
        if imfs.ndim == 1:
            imfs = imfs.reshape(1, -1)
        
        inst_freqs, inst_amps, mean_freqs = [], [], []
        
        for imf in imfs:
            analytic = hilbert(imf)
            amplitude = np.abs(analytic)
            phase = np.unwrap(np.angle(analytic))
            frequency = np.diff(phase) * fs / (2 * np.pi)
            frequency = np.clip(frequency, 0, fs / 2)
            frequency = np.append(frequency, frequency[-1])
            
            inst_freqs.append(frequency)
            inst_amps.append(amplitude)
            mean_freqs.append(float(np.mean(frequency)))
        
        imf_energies = [np.sum(imf ** 2) for imf in imfs]
        dominant_imf_idx = int(np.argmax(imf_energies))
        
        return HHTFeatures(
            imfs=imfs,
            instantaneous_frequencies=inst_freqs,
            instantaneous_amplitudes=inst_amps,
            num_imfs=len(imfs),
            dominant_imf_idx=dominant_imf_idx,
            mean_frequencies=np.array(mean_freqs)
        )
    
    def to_dict(self, features: HHTFeatures) -> dict:
        return {
            "hht_num_imfs": features.num_imfs,
            "hht_dominant_imf": features.dominant_imf_idx,
            "hht_mean_freq_imf0": float(features.mean_frequencies[0]) if len(features.mean_frequencies) > 0 else 0.0,
            "hht_mean_freq_imf1": float(features.mean_frequencies[1]) if len(features.mean_frequencies) > 1 else 0.0,
            "hht_freq_drift": float(np.std(features.instantaneous_frequencies[0])) if features.instantaneous_frequencies else 0.0,
            "hht_amplitude_variation": float(np.std(features.instantaneous_amplitudes[0])) if features.instantaneous_amplitudes else 0.0,
        }