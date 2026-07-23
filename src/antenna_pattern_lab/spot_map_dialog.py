from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from statistics import median

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import PolyCollection
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from .analysis import LocatedSpot
from .geo import great_circle_segments, maidenhead_to_latlon
from .world_map import load_land_polygons


TEXT = {
    "CZE": {
        "title": "Mapa spotů",
        "map_title": "Kde byl můj signál zachycen",
        "summary": "{spots} spotů · {receivers} přijímačů · {context}",
        "empty": "Pro aktuální filtry nejsou k dispozici spoty se souřadnicemi.",
        "hint": "Najeďte na bod přijímače: zobrazí se trasa, azimut a vzdálenost.",
        "detail": (
            "{call} · {grid} · {count} reportů · medián {snr:+.1f} dB\n"
            "Azimut {bearing:.1f}° · vzdálenost {distance:.0f} km · naposledy {last_seen}"
        ),
        "snr": "Medián SNR (dB)",
        "tx": "Vysílač {call}",
        "rx": "Přijímače",
    },
    "ENG": {
        "title": "Spot map",
        "map_title": "Where my signal was received",
        "summary": "{spots} spots · {receivers} receivers · {context}",
        "empty": "No spots with coordinates are available for the current filters.",
        "hint": "Hover over a receiver: its route, bearing and distance will appear.",
        "detail": (
            "{call} · {grid} · {count} reports · median {snr:+.1f} dB\n"
            "Bearing {bearing:.1f}° · distance {distance:.0f} km · last heard {last_seen}"
        ),
        "snr": "Median SNR (dB)",
        "tx": "Transmitter {call}",
        "rx": "Receivers",
    },
}


@dataclass(frozen=True, slots=True)
class SpotMapPoint:
    rx_call: str
    rx_grid: str
    rx_latitude: float
    rx_longitude: float
    tx_latitude: float
    tx_longitude: float
    median_snr_db: float
    spot_count: int
    distance_km: float
    bearing_deg: float
    last_seen: object


def aggregate_map_points(
    located: list[LocatedSpot], fallback_tx_grid: str
) -> list[SpotMapPoint]:
    grouped: dict[tuple[str, str], list[LocatedSpot]] = {}
    for item in located:
        grouped.setdefault((item.spot.rx_call, item.spot.rx_grid), []).append(item)

    points: list[SpotMapPoint] = []
    for (rx_call, rx_grid), items in grouped.items():
        try:
            rx_latitude, rx_longitude = maidenhead_to_latlon(rx_grid)
            latest = max(items, key=lambda item: item.spot.observed_at)
            tx_latitude, tx_longitude = maidenhead_to_latlon(
                latest.spot.tx_grid or fallback_tx_grid
            )
        except ValueError:
            continue
        points.append(
            SpotMapPoint(
                rx_call=rx_call,
                rx_grid=rx_grid,
                rx_latitude=rx_latitude,
                rx_longitude=rx_longitude,
                tx_latitude=tx_latitude,
                tx_longitude=tx_longitude,
                median_snr_db=float(median(item.spot.snr_db for item in items)),
                spot_count=len(items),
                distance_km=latest.distance_km,
                bearing_deg=latest.bearing_deg,
                last_seen=latest.spot.observed_at,
            )
        )
    return sorted(points, key=lambda point: (point.rx_call, point.rx_grid))


class SpotMapDialog(QDialog):
    def __init__(
        self,
        located: list[LocatedSpot],
        tx_grid: str,
        tx_call: str,
        language: str,
        filter_context: str,
        parent=None,
    ):
        super().__init__(parent)
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.tx_call = tx_call.strip().upper() or "TX"
        self.points = aggregate_map_points(located, tx_grid)
        self._active_index: int | None = None
        self._route_artists = []
        self.setWindowTitle(self.text["title"])
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1280, 820)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        self.summary = QLabel(
            self.text["summary"].format(
                spots=len(located),
                receivers=len(self.points),
                context=filter_context,
            )
        )
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.figure = Figure(figsize=(12, 7), facecolor="#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)
        self.detail = QLabel(self.text["hint"] if self.points else self.text["empty"])
        self.detail.setMinimumHeight(40)
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

        self.axis = self.figure.add_subplot(111)
        self._draw_map()
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _draw_map(self) -> None:
        axis = self.axis
        axis.set_facecolor("#dff1fb")
        land = PolyCollection(
            load_land_polygons(),
            facecolor="#edf2e8",
            edgecolor="#8c959f",
            linewidth=0.45,
            closed=True,
            zorder=1,
        )
        axis.add_collection(land)
        axis.set_xlim(-180, 180)
        axis.set_ylim(-90, 90)
        axis.set_aspect("equal", adjustable="box")
        axis.set_xticks(range(-180, 181, 30))
        axis.set_yticks(range(-90, 91, 30))
        axis.grid(color="#b6c2cf", linewidth=0.5, alpha=0.65, zorder=0)
        axis.tick_params(colors="#57606a", labelsize=8)
        axis.set_xlabel("Longitude (°)", color="#1f2328")
        axis.set_ylabel("Latitude (°)", color="#1f2328")
        axis.set_title(self.text["map_title"], color="#1f2328", pad=8)

        self.scatter = axis.scatter(
            [point.rx_longitude for point in self.points],
            [point.rx_latitude for point in self.points],
            c=[point.median_snr_db for point in self.points],
            s=[30 + min(point.spot_count, 40) * 3 for point in self.points],
            cmap="viridis",
            vmin=-25,
            vmax=10,
            alpha=0.9,
            edgecolors="#ffffff",
            linewidths=0.7,
            label=self.text["rx"],
            zorder=4,
        )
        if self.points:
            colorbar = self.figure.colorbar(
                self.scatter, ax=axis, orientation="horizontal", pad=0.08, fraction=0.045
            )
            colorbar.set_label(self.text["snr"], color="#1f2328")
            colorbar.ax.tick_params(colors="#57606a", labelsize=8)

        transmitters = {
            (point.tx_latitude, point.tx_longitude) for point in self.points
        }
        if not transmitters:
            transmitters = set()
        for index, (latitude, longitude) in enumerate(sorted(transmitters)):
            axis.scatter(
                [longitude],
                [latitude],
                marker="*",
                s=170,
                color="#b42318",
                edgecolors="#ffffff",
                linewidths=0.8,
                label=self.text["tx"].format(call=self.tx_call) if index == 0 else None,
                zorder=6,
            )
        if self.points:
            legend = axis.legend(loc="lower left")
            legend.get_frame().set_facecolor("#ffffff")
            legend.get_frame().set_alpha(0.92)

        self.annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": "#ffffff", "ec": "#0969da"},
            color="#1f2328",
            fontsize=9,
            zorder=8,
        )
        self.annotation.set_visible(False)
        self.figure.subplots_adjust(left=0.055, right=0.985, top=0.94, bottom=0.14)
        self.canvas.draw_idle()

    def _point_text(self, point: SpotMapPoint) -> str:
        return self.text["detail"].format(
            call=point.rx_call,
            grid=point.rx_grid,
            count=point.spot_count,
            snr=point.median_snr_db,
            bearing=point.bearing_deg,
            distance=point.distance_km,
            last_seen=point.last_seen.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        )

    def show_receiver(self, index: int) -> None:
        if not 0 <= index < len(self.points):
            return
        if self._active_index == index:
            return
        self._active_index = index
        for artist in self._route_artists:
            artist.remove()
        self._route_artists.clear()

        point = self.points[index]
        for segment in great_circle_segments(
            (point.tx_latitude, point.tx_longitude),
            (point.rx_latitude, point.rx_longitude),
        ):
            artist, = self.axis.plot(
                [coordinate[1] for coordinate in segment],
                [coordinate[0] for coordinate in segment],
                color="#f0883e",
                linewidth=2.2,
                alpha=0.95,
                zorder=3,
            )
            self._route_artists.append(artist)
        text = self._point_text(point)
        self.detail.setText(text)
        self.annotation.xy = (point.rx_longitude, point.rx_latitude)
        self.annotation.set_text(text)
        self.annotation.set_visible(True)
        self.canvas.draw_idle()

    def clear_receiver(self) -> None:
        if self._active_index is None:
            return
        self._active_index = None
        for artist in self._route_artists:
            artist.remove()
        self._route_artists.clear()
        self.annotation.set_visible(False)
        self.detail.setText(self.text["hint"] if self.points else self.text["empty"])
        self.canvas.draw_idle()

    def _on_hover(self, event) -> None:
        if event.inaxes is not self.axis or not self.points:
            self.clear_receiver()
            return
        contains, details = self.scatter.contains(event)
        if not contains or not len(details.get("ind", [])):
            self.clear_receiver()
            return
        self.show_receiver(int(details["ind"][0]))
