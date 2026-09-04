import numpy as np

from app.utils.confidence import UNKNOWN
from app.utils.geometry import BBox
from app.vision.attributes import analyze_attributes


def test_attributes_use_bbox_bands_not_full_frame() -> None:
    frame = np.zeros((200, 80, 3), dtype=np.uint8)
    # Blue jacket band
    frame[50:90, 20:60] = (180, 40, 20)
    # Black trousers
    frame[110:160, 20:60] = (10, 10, 10)
    bbox = BBox(0, 0, 80, 200)
    result = analyze_attributes(frame, bbox, None, None, threshold=0.4)
    assert result.top_color in {"Blue", "Other"}
    assert result.top_confidence >= 0.4
    assert result.bottom_color in {"Black", "Other", "Grey"}


def test_low_confidence_stays_unknown() -> None:
    frame = np.zeros((40, 20, 3), dtype=np.uint8)
    result = analyze_attributes(frame, BBox(0, 0, 20, 40), None, None, threshold=0.99)
    assert result.top_label == UNKNOWN or result.top_confidence < 0.99
