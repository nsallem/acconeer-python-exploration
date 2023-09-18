# Copyright (c) Acconeer AB, 2023
# All rights reserved

from __future__ import annotations

import copy
import itertools
import typing as t

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

import pyqtgraph as pg

from acconeer.exptool import a121
from acconeer.exptool.a121._core import utils as core_utils
from acconeer.exptool.a121.model import power
from acconeer.exptool.app.new.ui.resource_tab.event_system import (
    EventBroker,
    IdentifiedServiceUninstalledEvent,
)
from acconeer.exptool.utils import pg_pen_cycler

from .session_config_input import SessionConfigEvent


_T = t.TypeVar("_T")


def incremental_plot(
    xs: list[float],
    f: t.Callable[[float], float],
    ordering_strategy: t.Callable[[int], t.Iterable[int]],
) -> t.Iterator[tuple[list[float], list[float]]]:
    """Generator that adds one (x, y)-point to the plot each time it's iterated"""
    done: list[tuple[float, float]] = []

    for i in ordering_strategy(len(xs)):
        x = xs[i]

        done += [(x, f(x))]
        done.sort(key=lambda t: t[0])

        all_xs = [done_x for done_x, _ in done]
        all_ys = [done_y for _, done_y in done]
        yield (all_xs, all_ys)


class _PowerConsumptionVsRatePlot(pg.PlotWidget):
    def __init__(self) -> None:
        super().__init__()

        self.getPlotItem().setLabel("bottom", "Update rate", units="Hz")
        self.getPlotItem().setLabel("left", "Sensor + XM125", units="A")
        self.getPlotItem().setContentsMargins(0, 0, 0, 10)
        self.getPlotItem().addLegend()
        self.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        self._ready_plotter: t.Iterator[tuple[list[float], list[float]]] = iter([])
        self._sleep_plotter: t.Iterator[tuple[list[float], list[float]]] = iter([])
        self._deep_sleep_plotter: t.Iterator[tuple[list[float], list[float]]] = iter([])
        self._hibernate_plotter: t.Iterator[tuple[list[float], list[float]]] = iter([])
        self._off_plotter: t.Iterator[tuple[list[float], list[float]]] = iter([])

        self._ready_curve: t.Optional[pg.PlotDataItem] = None
        self._sleep_curve: t.Optional[pg.PlotDataItem] = None
        self._deep_sleep_curve: t.Optional[pg.PlotDataItem] = None
        self._hibernate_curve: t.Optional[pg.PlotDataItem] = None
        self._off_curve: t.Optional[pg.PlotDataItem] = None

        self._plot_increment_timer = QTimer()
        self._plot_increment_timer.timeout.connect(self._increment_plots)

    @staticmethod
    def _get_update_rates(update_rate: float) -> list[float]:
        return list(
            itertools.takewhile(
                lambda e: e < update_rate * 1.5,
                itertools.chain(
                    [i / 100 for i in range(1, 100)],  # [0.01, 0.99] in 0.01 steps
                    [1 + i / 10 for i in range(90)],  # [1, 9.9] in 0.1 steps
                    itertools.count(start=10),  # [10, inf) in 1.0 steps
                ),
            )
        )

    @staticmethod
    def _evolve_config(
        config: a121.SessionConfig,
        *,
        update_rate: t.Optional[float] = None,
        inter_frame_idle_state: t.Optional[a121.IdleState] = None,
    ) -> a121.SessionConfig:
        config_copy = copy.deepcopy(config)

        if update_rate is not None:
            config_copy.update_rate = update_rate

        if inter_frame_idle_state is not None:
            config_copy.sensor_config.inter_frame_idle_state = inter_frame_idle_state

        return config_copy

    def _increment_plots(self) -> None:
        (self._sleep_curve, sleep_done) = self._increment_plot(
            "Sleep", pg_pen_cycler(0), self._sleep_plotter, self._sleep_curve
        )
        (self._deep_sleep_curve, deep_sleep_done) = self._increment_plot(
            "Deep sleep", pg_pen_cycler(1), self._deep_sleep_plotter, self._deep_sleep_curve
        )
        (self._hibernate_curve, hibernate_done) = self._increment_plot(
            "Hibernate", pg_pen_cycler(2), self._hibernate_plotter, self._hibernate_curve
        )
        (self._off_curve, off_done) = self._increment_plot(
            "Off", pg_pen_cycler(3), self._off_plotter, self._off_curve
        )
        (self._ready_curve, ready_done) = self._increment_plot(
            "Ready", pg_pen_cycler(4), self._ready_plotter, self._ready_curve
        )

        if all([sleep_done, deep_sleep_done, hibernate_done, off_done]):
            self._plot_increment_timer.stop()

    def _increment_plot(
        self,
        name: str,
        pen: t.Any,
        incremental_plotter: t.Iterator[tuple[list[float], list[float]]],
        reused_curve: t.Optional[pg.PlotDataItem],
    ) -> tuple[pg.PlotDataItem, bool]:
        """
        Plots the next increment of incremental_plotter.
        If reused_curve is None, a new curve will be created with name and pen.

        Returns the updated curve (migth be the same as reused_curve) and whether
        plotting is completed
        """
        try:
            (xs, ys) = next(incremental_plotter)
        except StopIteration:
            return (reused_curve, True)
        else:
            if reused_curve is None:
                return (
                    self.plot(xs, ys, name=name, pen=pen),
                    False,
                )
            else:
                reused_curve.setData(xs, ys)
                return (reused_curve, False)

    def update_power_curves(self, event: SessionConfigEvent) -> None:
        self._plot_increment_timer.stop()
        self.clear()

        configured_rate = power.configured_rate(event.session_config)

        if configured_rate is None:
            self.disableAutoRange()
            ((x_min, x_max), (y_min, y_max)) = self.viewRange()

            text_item = pg.InfiniteLine(
                pos=0.75 * x_max,
                angle=0,
                label="Set update rate to compare\npower states over rates",
                labelOpts={"color": "#111", "fill": "#ddd"},
                pen=pg.mkPen(None),
            )
            self.addItem(text_item)
            return

        self._ready_curve = None
        self._sleep_curve = None
        self._deep_sleep_curve = None
        self._hibernate_curve = None
        self._off_curve = None
        self._increment_plots()
        self.addItem(
            pg.ScatterPlotItem(
                [configured_rate],
                [
                    power.converged_average_current(
                        event.session_config,
                        lower_power_state=event.lower_power_state,
                        absolute_tolerance=1e-3,
                    )
                ],
                name="Current config",
            )
        )

        update_rates = self._get_update_rates(configured_rate)

        self.enableAutoRange()
        self.setXRange(min(update_rates), max(update_rates))

        if any(
            sensor_config.inter_frame_idle_state == a121.IdleState.READY
            for sensor_config in core_utils.iterate_extended_structure_values(
                event.session_config.groups
            )
        ):

            def ready_f(update_rate: float) -> float:
                return power.converged_average_current(
                    self._evolve_config(
                        event.session_config,
                        update_rate=update_rate,
                        inter_frame_idle_state=a121.IdleState.READY,
                    ),
                    lower_power_state=None,
                    absolute_tolerance=1e-3,
                )

            self._ready_plotter = incremental_plot(update_rates, ready_f, ordering_strategy=range)

        def sleep_f(update_rate: float) -> float:
            return power.converged_average_current(
                self._evolve_config(
                    event.session_config,
                    update_rate=update_rate,
                    inter_frame_idle_state=a121.IdleState.SLEEP,
                ),
                lower_power_state=None,
                absolute_tolerance=1e-3,
            )

        self._sleep_plotter = incremental_plot(update_rates, sleep_f, ordering_strategy=range)

        def deep_sleep_f(update_rate: float) -> float:
            return power.converged_average_current(
                self._evolve_config(
                    event.session_config,
                    update_rate=update_rate,
                    inter_frame_idle_state=a121.IdleState.DEEP_SLEEP,
                ),
                lower_power_state=None,
                absolute_tolerance=1e-3,
            )

        self._deep_sleep_plotter = incremental_plot(
            update_rates, deep_sleep_f, ordering_strategy=range
        )

        def hibernate_f(update_rate: float) -> float:
            return power.converged_average_current(
                self._evolve_config(event.session_config, update_rate=update_rate),
                lower_power_state=power.Sensor.PowerState.HIBERNATE,
                absolute_tolerance=1e-3,
            )

        self._hibernate_plotter = incremental_plot(
            update_rates, hibernate_f, ordering_strategy=range
        )

        def off_f(update_rate: float) -> float:
            return power.converged_average_current(
                self._evolve_config(event.session_config, update_rate=update_rate),
                lower_power_state=power.Sensor.PowerState.OFF,
                absolute_tolerance=1e-3,
            )

        self._off_plotter = incremental_plot(update_rates, off_f, ordering_strategy=range)
        self._plot_increment_timer.start(10)


class PowerConsumptionVsRateOutput(QWidget):
    INTERESTS: t.ClassVar[set[type]] = {
        SessionConfigEvent,
        IdentifiedServiceUninstalledEvent,
    }
    description: t.ClassVar[str] = "\n\n".join(
        [
            "Comparse power consumption and rate for differend power- & idle states.",
            "NOTE: A curve flatlining means that the rate is the maximum for that power state.",
        ]
    )
    window_title = "Power consumption vs rate"

    def __init__(
        self,
        broker: EventBroker,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet("QTabBar { font: bold 14px; font-family: monospace; }")
        self._tab_widget = QTabWidget()
        self._tabs: dict[str, _PowerConsumptionVsRatePlot] = {}

        layout.addWidget(self._tab_widget)
        self.setLayout(layout)

        self.uninstall_function = broker.install_service(self)
        broker.brief_service(self)

    def handle_event(self, event: t.Any) -> None:
        if isinstance(event, SessionConfigEvent):
            self._handle_session_config_event(event)
        elif isinstance(event, IdentifiedServiceUninstalledEvent):
            self._handle_identified_service_uninstalled_event(event)
        else:
            raise NotImplementedError

    def _handle_session_config_event(self, event: SessionConfigEvent) -> None:
        if event.service_id not in self._tabs:
            plot_widget = _PowerConsumptionVsRatePlot()
            self._tabs[event.service_id] = plot_widget
            self._tab_widget.addTab(plot_widget, event.service_id)

        self._tabs[event.service_id].update_power_curves(event)

    def _handle_identified_service_uninstalled_event(
        self, event: IdentifiedServiceUninstalledEvent
    ) -> None:
        tab_widget = self._tabs.pop(event.id_)
        tab_index = self._tab_widget.indexOf(tab_widget)
        if tab_index != -1:
            self._tab_widget.removeTab(tab_index)
