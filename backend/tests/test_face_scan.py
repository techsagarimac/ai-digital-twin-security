import numpy as np

from app.utils.geometry import BBox
from app.vision.face_mesh import SkinFaceProcessor, person_bbox_from_face


def test_skin_face_finds_face_like_region() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[40:140, 110:210] = (90, 150, 210)  # BGR skin-ish oval block
    hits = SkinFaceProcessor().detect_all(frame)
    assert hits, "expected a face-like region"
    face = hits[0]
    assert face.bbox.area > 1000
    assert len(face.landmarks) >= 5


def test_person_box_expands_below_face() -> None:
    face = BBox(100, 40, 180, 140)
    person = person_bbox_from_face(face, 640, 480)
    assert person.y2 > face.y2
    assert person.width >= face.width
