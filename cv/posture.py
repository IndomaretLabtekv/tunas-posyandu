"""QC postur (V5a wajib + V5b opsional, DEC-006).

- `SilhouettePostureQC` -- jalur utama, NON-AI, berbasis geometri siluet:
  rasio panjang-lebar, kelengkungan sumbu tubuh, isi bbox (keandalan
  segmentasi), dan indikasi tungkai tertekuk/terpisah.
- `ViTPosePostureQC`    -- QC tambahan berbasis pose pretrained, BERSYARAT:
  hanya menurunkan skor kepercayaan, TIDAK pernah menggagalkan pengukuran
  dan TIDAK pernah menjadi sumber angka ukur. Masuk produk hanya bila
  lolos CV-06 (keandalan pada subjek berbaring dilihat dari atas).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SilhouettePostureQC:
    """Ambang operasional; kalibrasi dari CV-03/CV-06 sebelum dipakai final."""

    min_aspect_ratio: float = 3.0        # panjang/lebar siluet
    max_curvature_deg: float = 20.0      # kelengkungan sumbu tubuh
    min_bbox_fill: float = 0.30          # isi bbox; rendah = segmentasi tidak stabil
    max_bottom_legs_ratio: float = 1.9   # rasio lebar kaki/lengan vs tengah tubuh

    def check(self, mask: np.ndarray) -> dict:
        ys, xs = np.nonzero(mask)
        if len(xs) < 16:
            return {"passed": False, "reasons": ["siluet terlalu kecil"],
                    "aspect_ratio": float("nan"), "curvature_deg": float("nan"),
                    "bbox_fill": 0.0, "legs_ratio": float("nan")}

        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        area = len(xs)
        aspect = max(bw, bh) / max(1, min(bw, bh))
        fill = area / (bw * bh)
        reasons = []

        if aspect < self.min_aspect_ratio:
            reasons.append(f"siluet terlalu pendek-lebar (aspect {aspect:.1f})")
        if fill < self.min_bbox_fill:
            reasons.append(f"segmentasi tidak stabil (bbox fill {fill:.2f})")

        curvature = self._curvature_deg(mask)
        if curvature > self.max_curvature_deg:
            reasons.append(f"sumbu tubuh melengkung ({curvature:.0f} deg)")

        legs = self._legs_ratio(mask, (bw, bh))
        if legs > self.max_bottom_legs_ratio:
            reasons.append(f"tungkai tertekuk/terpisah (lebar bawah {legs:.1f}x tengah)")

        return {
            "passed": not reasons,
            "reasons": reasons,
            "aspect_ratio": round(aspect, 2),
            "curvature_deg": round(curvature, 1),
            "bbox_fill": round(fill, 3),
            "legs_ratio": round(legs, 2),
        }

    @staticmethod
    def _curvature_deg(mask: np.ndarray) -> float:
        """Deviasi sumbu tubuh dari GARIS ANTAR-ENDPOINT (chord), dalam derajat.

        Siluet dipecah menjadi pita sepanjang sumbu panjang; centroid tiap
        pita difit; resid = jarak tegak lurus centroid terhadap garis yang
        menghubungkan dua ujung sumbu; kelengkungan = atan(resid / panjang).
        Chord dipakai (bukan best-fit) agar tekukan tajam (sikap menggunting)
        tidak "tertelan" garis regresi yang ikut miring.
        """
        ys, xs = np.nonzero(mask)
        if mask.shape[0] >= mask.shape[1]:  # tubuh vertikal -> pita per baris
            bands = [(y, xs[ys == y].mean() if (ys == y).any() else np.nan)
                     for y in range(mask.shape[0])]
        else:                                # tubuh horizontal -> pita per kolom
            bands = [(x, ys[xs == x].mean() if (xs == x).any() else np.nan)
                     for x in range(mask.shape[1])]
        pts = np.array([[k, v] for k, v in bands if not np.isnan(v)])
        if len(pts) < 4:
            return 0.0
        p0, p1 = pts[0], pts[-1]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        norm = float(np.hypot(dx, dy))
        if norm < 1e-9:
            return 0.0
        dist = np.abs(dx * (p0[1] - pts[:, 1]) - dy * (p0[0] - pts[:, 0])) / norm
        return float(np.degrees(np.arctan2(dist.max(), norm)))

    @staticmethod
    def _legs_ratio(mask: np.ndarray, bbox: tuple[int, int]) -> float:
        """Indikasi tungkai tertekuk/terpisah: lebar sepertiga bawah vs tengah."""
        bw, bh = bbox
        if bw >= bh:  # horizontal: pita kolom sepanjang sumbu panjang
            def span(f0, f1):
                band = mask[:, int(mask.shape[1] * f0):int(mask.shape[1] * f1)]
                return int(band.any(axis=1).sum())
        else:         # vertikal: pita baris sepanjang sumbu panjang
            def span(f0, f1):
                band = mask[int(mask.shape[0] * f0):int(mask.shape[0] * f1), :]
                return int(band.any(axis=0).sum())
        w_mid, w_bot = span(0.45, 0.55), span(0.75, 0.95)
        return float(max(1, w_bot) / max(1, w_mid))


class ViTPosePostureQC:
    """QC pose opsional (V5b), lazy-load via transformers.

    Gated CV-06: kalau tidak andal pada subjek berbaring, cukup jangan
    dipakai -- jalur utama (siluet) tetap jalan. `available()` mengecek
    dependensi; `check()` mengembalikan None bila tidak tersedia.
    """

    def __init__(self, model_id: str = "nielsr/vitpose_base",
                 min_mean_conf: float = 0.4, device: str | None = None):
        self.model_id = model_id
        self.min_mean_conf = min_mean_conf
        self.device = device
        self._model = None
        self._processor = None
        self._err = ""

    def available(self) -> bool:
        try:
            self._load()
            return True
        except Exception as e:  # noqa: BLE001 -- sinyal ketersediaan, bukan error
            self._err = str(e)
            return False

    def _load(self):
        if self._model is not None:
            return
        import torch  # noqa: F401
        from transformers import AutoImageProcessor, VitPoseForPoseEstimation
        self._processor = AutoImageProcessor.from_pretrained(self.model_id)
        self._model = VitPoseForPoseEstimation.from_pretrained(self.model_id).eval()
        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self.device)

    def check(self, image_bgr: np.ndarray) -> dict | None:
        """Skor kepercayaan keypoint; None bila model tidak tersedia.

        Hanya sinyal QC: tidak menghasilkan angka ukur (DEC-006).
        """
        if not self.available():
            return None
        import cv2
        import torch

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        inputs = self._processor(images=rgb, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self._model(**inputs)
        logits = out.logits  # (B, K, h, w)
        k = logits.shape[1]
        flat = logits.flatten(2).softmax(dim=2)          # prob per keypoint
        peak = flat.max(dim=2).values                    # skor puncak per keypoint
        mean_conf = float(peak.mean().item())
        return {
            "passed": mean_conf >= self.min_mean_conf,
            "mean_conf": round(mean_conf, 3),
            "n_keypoints": int(k),
        }
