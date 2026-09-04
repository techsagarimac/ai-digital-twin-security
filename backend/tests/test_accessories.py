from app.vision.accessories import associate_objects
from app.utils.geometry import BBox
from app.vision.types import Detection


def test_objects_below_threshold_are_dropped() -> None:
    person = BBox(10, 10, 100, 200)
    objs = [Detection(BBox(20, 40, 50, 80), 0.2, "backpack")]
    hits = associate_objects(objs, person, threshold=0.5)
    assert hits == []


def test_overlapping_object_is_kept() -> None:
    person = BBox(10, 10, 100, 200)
    objs = [Detection(BBox(12, 40, 40, 90), 0.88, "backpack")]
    hits = associate_objects(objs, person, threshold=0.5)
    assert len(hits) == 1
    assert hits[0].name == "backpack"
