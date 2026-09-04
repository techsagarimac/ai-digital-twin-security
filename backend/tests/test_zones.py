from app.utils.geometry import BBox
from app.vision.zones import ZoneDef, ZoneResolver


def zones() -> ZoneResolver:
    return ZoneResolver(
        [
            ZoneDef("zone-a", "Entrance", BBox(0, 0, 0.33, 1)),
            ZoneDef("zone-b", "Reception", BBox(0.33, 0, 0.66, 1)),
            ZoneDef("zone-c", "Restricted", BBox(0.66, 0, 1, 1)),
        ]
    )


def test_zone_from_normalized_point() -> None:
    z = zones()
    assert z.resolve(0.1, 0.5).id == "zone-a"
    assert z.resolve(0.5, 0.5).id == "zone-b"
    assert z.resolve(0.9, 0.2).id == "zone-c"


def test_zone_from_bbox_centroid() -> None:
    z = zones()
    found = z.resolve_bbox(BBox(100, 10, 200, 200), 1000, 500)
    assert found is not None
    assert found.id == "zone-a"
