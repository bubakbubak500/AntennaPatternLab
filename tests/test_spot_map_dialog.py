import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.analysis import locate_spot
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.spot_map_dialog import SpotMapDialog, aggregate_map_points
from antenna_pattern_lab.world_map import load_land_polygons


def test_bundled_world_map_has_real_land_geometry():
    polygons = load_land_polygons()
    assert len(polygons) > 100
    assert sum(len(polygon) for polygon in polygons) > 5000


def test_spot_map_groups_receivers_and_draws_hover_route():
    application = QApplication.instance() or QApplication([])
    located = [
        item
        for spot in generate_demo_spots(count=100)
        if (item := locate_spot(spot))
    ]
    points = aggregate_map_points(located, "JN79")
    assert len(points) == 10

    dialog = SpotMapDialog(
        located,
        "JN79",
        "OK7PS",
        "ENG",
        "OK7PS · 20m · all data",
    )
    assert dialog.size().width() >= 1200
    assert not hasattr(dialog, "toolbar")
    assert dialog.scatter.get_offsets().shape[0] == 10
    dialog.show_receiver(0)
    assert dialog._route_artists
    assert dialog.annotation.get_visible()
    assert "Bearing" in dialog.detail.text()
    assert "km" in dialog.detail.text()
    dialog.clear_receiver()
    assert not dialog.annotation.get_visible()
    dialog.close()
    application.processEvents()
