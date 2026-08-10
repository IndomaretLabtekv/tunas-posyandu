"""Segmentasi subjek terhadap alas + ekstraksi endpoint (V4, CV-05).

Dua backend sekarang (registry dapat diperluas):

- `ColorSegmenter`   -- baseline NON-AI: segmentasi warna terhadap alas
                        seragam (wajib ada, DEC-005 alasan 2; juga pembanding).
- `BiRefNetSegmenter`-- model segmentasi primary (DEC-014): BiRefNet_dynamic
                        (ZhengPeng7/BiRefNet_dynamic) via transformers,
                        lazy-load, resolusi dinamis.

Endpoint kepala/tumit TIDAK berasal dari keypoint pose (DEC-006): dihitung
dari ekstrem siluet sepanjang sumbu utama tubuh pada citra teregistrasi.
Kontrak backend: `segment(image_bgr) -> SegmentResult` dengan `mask` bool.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

# Model id BiRefNet_dynamic di Hugging Face (DEC-014).
BIRENET_MODEL_ID = "ZhengPeng7/BiRefNet_dynamic"
BIRENET_INPUT_SIZE = 1024


@dataclass
class SegmentResult:
    mask: np.ndarray          # bool (H, W)
    model: str                # nama backend
    latency_s: float
    ok: bool = True
    reason: str = ""


class BaseSegmenter(ABC):
    model_name = "base"

    @abstractmethod
    def segment(self, image_bgr: np.ndarray) -> SegmentResult:
        ...


def endpoints_from_mask(mask: np.ndarray) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Endpoint kepala/tumit: titik ekstrem sepanjang sumbu utama siluet.

    Sumbu utama dari PCA (eigenvector terbesar kovarians piksel mask),
    lalu proyeksikan semua piksel mask ke sumbu dan ambil dua ekstrem.
    Untuk panjang badan, label kepala/tumit tidak perlu dibedakan.
    Mengembalikan None bila mask terlalu kecil/tidak valid.
    """
    ys, xs = np.nonzero(mask)
    if len(xs) < 16:
        return None
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    center = pts.mean(axis=0)
    cov = np.cov(pts.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    axis = eigvecs[:, int(np.argmax(eigvals))]  # sumbu utama
    proj = (pts - center) @ axis
    lo, hi = int(np.argmin(proj)), int(np.argmax(proj))
    return (int(round(pts[lo, 0])), int(round(pts[lo, 1]))), \
           (int(round(pts[hi, 0])), int(round(pts[hi, 1])))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Pertahankan komponen terbesar (tubuh); buang noise/pecahan kecil."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return np.zeros_like(mask)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return labels == largest


class ColorSegmenter(BaseSegmenter):
    """Baseline non-AI: subjek = "lubang" terbesar di dalam region alas.

    Alas dideteksi sebagai komponen terbesar yang warnanya dekat dengan
    warna alas standar, lalu subjek = komponen terbesar dari piksel yang
    BUKAN alas di dalam region alas. Warna alas standar adalah spesifikasi
    produk (alas dicetak seragam, DEC-015); `mat_color` opsional: bila
    None, diestimasi dari cincin tepi (hanya andal bila alas mengisi tepi
    bingkai -- mode marker lama).
    """

    model_name = "color"

    def __init__(self, mat_color: tuple[int, int, int] | None = None,
                 color_dist_thresh: float = 40.0):
        self.mat_color = mat_color          # BGR; None -> diestimasi per citra
        self.color_dist_thresh = color_dist_thresh

    @staticmethod
    def _estimate_mat_color(image_bgr: np.ndarray) -> tuple[int, int, int]:
        """Median warna cincin tepi 2% citra -- hanya andal bila tepi = alas."""
        h, w = image_bgr.shape[:2]
        ring = np.concatenate([
            image_bgr[: max(2, h // 50)].reshape(-1, 3),
            image_bgr[-max(2, h // 50):].reshape(-1, 3),
            image_bgr[:, : max(2, w // 50)].reshape(-1, 3),
            image_bgr[:, -max(2, w // 50):].reshape(-1, 3),
        ])
        return tuple(int(v) for v in np.median(ring, axis=0))

    def segment(self, image_bgr: np.ndarray) -> SegmentResult:
        t0 = time.perf_counter()
        color = self.mat_color or self._estimate_mat_color(image_bgr)
        dist = np.linalg.norm(
            image_bgr.astype(np.float32) - np.asarray(color, np.float32), axis=2)
        mat_mask = _largest_component(dist <= self.color_dist_thresh)
        if not mat_mask.any():
            return SegmentResult(mask=mat_mask, model=self.model_name,
                                 latency_s=time.perf_counter() - t0,
                                 ok=False, reason="warna alas tidak ditemukan")
        ys, xs = np.nonzero(mat_mask)
        region = (slice(int(ys.min()), int(ys.max()) + 1),
                  slice(int(xs.min()), int(xs.max()) + 1))
        subj = np.zeros_like(mat_mask)
        subj[region] = ~mat_mask[region]        # "bukan alas" di dalam region alas
        mask = _largest_component(subj)
        if not mask.any():
            return SegmentResult(mask=mask, model=self.model_name,
                                 latency_s=time.perf_counter() - t0,
                                 ok=False, reason="tidak ada objek terdeteksi")
        return SegmentResult(mask=mask, model=self.model_name,
                             latency_s=time.perf_counter() - t0)


class BiRefNetSegmenter(BaseSegmenter):
    """Segmentasi primary (DEC-014): BiRefNet_dynamic, lazy-load via transformers.

    Menolak keras kalau dependensi/berkas tidak tersedia agar kegagalan
    terlihat jelas (model ini 445 MB, diload hanya saat pertama dipakai).
    """

    model_name = "birefnet_dynamic"

    def __init__(self, model_id: str = BIRENET_MODEL_ID,
                 device: str | None = None, threshold: float = 0.5):
        self.model_id = model_id
        self.device = device
        self.threshold = threshold
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForImageSegmentation
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "BiRefNetSegmenter butuh torch + transformers. "
                "Install: pip install transformers timm einops") from e
        self._model = AutoModelForImageSegmentation.from_pretrained(
            self.model_id, trust_remote_code=True).eval()
        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self.device)

    def segment(self, image_bgr: np.ndarray) -> SegmentResult:
        t0 = time.perf_counter()
        try:
            return self._segment(image_bgr, t0)
        except Exception as e:  # noqa: BLE001 -- kegagalan model = ok=False,
            # bukan crash; pipeline punya fallback ke baseline warna (DEC-014).
            return SegmentResult(
                mask=np.zeros(image_bgr.shape[:2], bool), model=self.model_name,
                latency_s=time.perf_counter() - t0,
                ok=False, reason=f"model tidak tersedia: {e}")

    def _segment(self, image_bgr: np.ndarray, t0: float) -> SegmentResult:
        self._load()
        import torch

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (BIRENET_INPUT_SIZE, BIRENET_INPUT_SIZE),
                         interpolation=cv2.INTER_LINEAR)
        x = rgb.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], np.float32)
        std = np.array([0.229, 0.224, 0.225], np.float32)
        x = (x - mean) / std
        tensor = torch.from_numpy(x.transpose(2, 0, 1))[None].to(self.device)

        with torch.no_grad():
            out = self._model(tensor)
        # Keluaran BiRefNet: tuple, elemen terakhir = logits tunggal-channel.
        logits = out[-1].sigmoid().squeeze().cpu().numpy()
        pred = cv2.resize(logits, (image_bgr.shape[1], image_bgr.shape[0]),
                          interpolation=cv2.INTER_LINEAR)
        mask = _largest_component(pred > self.threshold)
        if not mask.any():
            return SegmentResult(mask=mask, model=self.model_name,
                                 latency_s=time.perf_counter() - t0,
                                 ok=False, reason="tidak ada objek terdeteksi")
        return SegmentResult(mask=mask, model=self.model_name,
                             latency_s=time.perf_counter() - t0)


# Registry backend; tambahkan YOLO26n-seg / SAM 3 di sini bila dibutuhkan
# (SAM 3 butuh Python 3.12 + GPU + akses checkpoint gated).
SEGMENTERS: dict[str, type] = {
    "color": ColorSegmenter,
    "birefnet": BiRefNetSegmenter,
}


def get_segmenter(name: str = "birefnet", **kwargs) -> BaseSegmenter:
    if name not in SEGMENTERS:
        raise ValueError(f"backend segmentasi tidak dikenal: {name} "
                         f"(pilihan: {sorted(SEGMENTERS)})")
    return SEGMENTERS[name](**kwargs)
