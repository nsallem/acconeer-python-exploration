from __future__ import annotations

import abc
from enum import Enum
from typing import Any, Generic, Optional, Tuple, Type, TypeVar

import attrs

from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from acconeer.exptool.a121._core.entities import Criticality


def widget_wrap_layout(layout: QLayout) -> QWidget:
    dummy = QWidget()
    dummy.setLayout(layout)
    return dummy


T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


@attrs.frozen(kw_only=True)
class ParameterWidgetFactory(abc.ABC):
    name_label_text: str
    note_label_text: Optional[str] = None

    @abc.abstractmethod
    def create(self, parent: QWidget) -> ParameterWidget:
        ...


class ParameterWidget(QWidget):
    """Base class for a parameter-bound widget.

    A ``ParameterWidget`` comes with a
    ``name`` label and an ``note`` label by default.
    """

    sig_parameter_changed = QtCore.Signal(object)

    def __init__(self, factory: ParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(parent=parent)

        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)

        self._body_widget = QWidget(self)
        self.layout().addWidget(self._body_widget)

        self.__label_widget = QLabel(factory.name_label_text, parent=self._body_widget)

        self._body_layout = self._create_body_layout(self.__label_widget)
        self._body_widget.setLayout(self._body_layout)

        self.__note_widget = QLabel(parent=self)
        self.__note_widget.setWordWrap(True)
        self.__note_widget.setContentsMargins(5, 5, 5, 5)
        self.set_note_text(factory.note_label_text)
        self.layout().addWidget(self.__note_widget)

    def _create_body_layout(self, note_label_widget: QWidget) -> QLayout:
        """Called by ParameterWidget.__init__"""

        layout = QVBoxLayout(self._body_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(note_label_widget)
        return layout

    def set_note_text(
        self, message: Optional[str], criticality: Optional[Criticality] = None
    ) -> None:
        if not message:
            self.__note_widget.hide()
            return

        COLOR_MAP = {
            Criticality.ERROR: "#E6635A",
            Criticality.WARNING: "#FCC842",
            None: "white",
        }

        self.__note_widget.show()
        self.__note_widget.setText(message)
        self.__note_widget.setStyleSheet(
            f"background-color: {COLOR_MAP[criticality]}; color: white; font: bold italic;"
        )

    @abc.abstractmethod
    def set_parameter(self, value: Any) -> None:
        pass


@attrs.frozen(kw_only=True)
class IntParameterWidgetFactory(ParameterWidgetFactory):
    limits: Optional[Tuple[Optional[int], Optional[int]]] = None
    suffix: Optional[str] = None

    def create(self, parent: QWidget) -> IntParameterWidget:
        return IntParameterWidget(self, parent)


class IntParameterWidget(ParameterWidget):
    def __init__(self, factory: IntParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)

        self.__spin_box = _PidgetSpinBox(
            self._body_widget,
            limits=factory.limits,
            suffix=factory.suffix,
        )
        self.__spin_box.valueChanged.connect(self.__on_changed)
        self._body_layout.addWidget(self.__spin_box)

    def set_parameter(self, value: Any) -> None:
        if value is None:
            return

        self.__spin_box.setValue(int(value))

    def __on_changed(self) -> None:
        self.sig_parameter_changed.emit(self.__spin_box.value())


@attrs.frozen(kw_only=True)
class OptionalParameterWidgetFactory(ParameterWidgetFactory):
    checkbox_label_text: Optional[str] = None


class OptionalParameterWidget(ParameterWidget):
    """Optional parameter, not optional widget"""

    def __init__(self, factory: OptionalParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)

        self._optional_widget = QWidget(self._body_widget)
        self._body_layout.addWidget(self._optional_widget)

        self._none_checkbox = QCheckBox(self._optional_widget)
        if factory.checkbox_label_text:
            self._none_checkbox.setText(factory.checkbox_label_text)

        self._optional_layout = self._create_optional_layout(self._none_checkbox)

    def _create_optional_layout(self, none_checkbox: QWidget) -> QLayout:
        """Called by OptionalParameterWidget.__init__"""

        layout = QHBoxLayout(self._optional_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(none_checkbox)
        layout.addStretch(1)
        return layout

    def set_parameter(self, value: Any) -> None:
        if value is None:
            self._none_checkbox.setChecked(False)
        else:
            self._none_checkbox.setChecked(True)


@attrs.frozen(kw_only=True)
class OptionalFloatParameterWidgetFactory(OptionalParameterWidgetFactory):
    suffix: Optional[str] = None
    decimals: int = 1
    limits: Optional[Tuple[Optional[float], Optional[float]]] = None
    init_set_value: Optional[float] = None

    def create(self, parent: QWidget) -> OptionalFloatParameterWidget:
        return OptionalFloatParameterWidget(self, parent)


class OptionalFloatParameterWidget(OptionalParameterWidget):
    def __init__(self, factory: OptionalFloatParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)

        self.__spin_box = _PidgetDoubleSpinBox(
            self._optional_widget,
            decimals=factory.decimals,
            limits=factory.limits,
            suffix=factory.suffix,
            init_set_value=factory.init_set_value,
        )
        self._optional_layout.addWidget(self.__spin_box)

        self._none_checkbox.stateChanged.connect(self.__on_changed)
        self.__spin_box.valueChanged.connect(self.__on_changed)

    def __on_changed(self) -> None:
        checked = self._none_checkbox.isChecked()

        self.__spin_box.setEnabled(checked)

        value = self.__spin_box.value() if checked else None
        self.sig_parameter_changed.emit(value)

    def set_parameter(self, value: Any) -> None:
        super().set_parameter(value)

        if value is None:
            self.__spin_box.setEnabled(False)
        else:
            self.__spin_box.setValue(value)
            self.__spin_box.setEnabled(True)


@attrs.frozen(kw_only=True)
class CheckboxParameterWidgetFactory(ParameterWidgetFactory):
    def create(self, parent: QWidget) -> CheckboxParameterWidget:
        return CheckboxParameterWidget(self, parent)


class CheckboxParameterWidget(ParameterWidget):
    def __init__(self, factory: CheckboxParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)

        self.__checkbox = QCheckBox(self._body_widget)
        self.__checkbox.clicked.connect(self.__on_checkbox_click)
        self._body_layout.addWidget(self.__checkbox)
        assert isinstance(self._body_layout, QBoxLayout)
        self._body_layout.addStretch(1)

    def _create_body_layout(self, note_label_widget: QWidget) -> QLayout:
        """Called by ParameterWidget.__init__"""

        layout = QHBoxLayout(self._body_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(note_label_widget)
        return layout

    def __on_checkbox_click(self, checked: bool) -> None:
        self.sig_parameter_changed.emit(checked)

    def set_parameter(self, param: Any) -> None:
        self.__checkbox.setChecked(bool(param))


@attrs.frozen(kw_only=True)
class ComboboxParameterWidgetFactory(ParameterWidgetFactory, Generic[T]):
    items: list[tuple[str, T]]

    def create(self, parent: QWidget) -> ComboboxParameterWidget[T]:
        return ComboboxParameterWidget[T](self, parent)


class ComboboxParameterWidget(ParameterWidget, Generic[T]):
    def __init__(self, factory: ComboboxParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)

        self.__combobox = _PidgetComboBox(self._body_widget)
        self._body_layout.addWidget(self.__combobox)

        for displayed_text, user_data in factory.items:
            self.__combobox.addItem(displayed_text, user_data)

        self.__combobox.currentIndexChanged.connect(self.__emit_data_of_combobox_item)

    def __emit_data_of_combobox_item(self, index: int) -> None:
        data = self.__combobox.itemData(index)
        self.sig_parameter_changed.emit(data)

    def set_parameter(self, param: Any) -> None:
        index = self.__combobox.findData(param)
        if index == -1:
            raise ValueError(f"Data item {param} could not be found in {self}.")
        self.__combobox.setCurrentIndex(index)


@attrs.frozen(kw_only=True)
class EnumParameterWidgetFactory(ComboboxParameterWidgetFactory, Generic[EnumT]):
    enum_type: Type[EnumT] = attrs.field()
    label_mapping: dict[EnumT, str] = attrs.field()

    items: list[tuple[str, EnumT]] = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        if self.label_mapping.keys() != set(self.enum_type):
            raise ValueError("label_mapping does not match enum_type")

        items = [(v, k) for k, v in self.label_mapping.items()]

        # The instance is immutable at this point, which is circumvented by the next row. See:
        # - https://www.attrs.org/en/stable/api.html#attr.ib
        # - https://github.com/python-attrs/attrs/issues/120
        # - https://github.com/python-attrs/attrs/issues/147

        object.__setattr__(self, "items", items)

    def create(self, parent: QWidget) -> EnumParameterWidget[EnumT]:
        return EnumParameterWidget[EnumT](self, parent)


class EnumParameterWidget(ComboboxParameterWidget[EnumT]):
    def __init__(self, factory: EnumParameterWidgetFactory, parent: QWidget) -> None:
        super().__init__(factory, parent)


class _PidgetComboBox(QComboBox):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class _PidgetSpinBox(QSpinBox):
    def __init__(
        self,
        parent: QWidget,
        *,
        limits: Optional[Tuple[Optional[int], Optional[int]]] = None,
        suffix: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self.setKeyboardTracking(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAlignment(QtCore.Qt.AlignRight)

        self.setRange(*_convert_int_limits_to_qt_range(limits))

        if suffix:
            self.setSuffix(f" {suffix}")

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class _PidgetDoubleSpinBox(QDoubleSpinBox):
    def __init__(
        self,
        parent: QWidget,
        *,
        limits: Optional[Tuple[Optional[float], Optional[float]]] = None,
        init_set_value: Optional[float] = None,
        decimals: int = 1,
        suffix: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self.setKeyboardTracking(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAlignment(QtCore.Qt.AlignRight)

        self.setRange(*_convert_float_limits_to_qt_range(limits))
        self.setDecimals(decimals)
        self.setSingleStep(10 ** (-decimals))

        if suffix:
            self.setSuffix(f" {suffix}")

        if init_set_value is not None:
            self.setValue(init_set_value)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


def _convert_int_limits_to_qt_range(
    limits: Optional[Tuple[Optional[int], Optional[int]]]
) -> Tuple[int, int]:
    if limits is None:
        limits = (None, None)

    lower, upper = limits

    if lower is None:
        lower = int(-1e9)

    if upper is None:
        upper = int(1e9)

    return (lower, upper)


def _convert_float_limits_to_qt_range(
    limits: Optional[Tuple[Optional[float], Optional[float]]]
) -> Tuple[float, float]:
    if limits is None:
        limits = (None, None)

    lower, upper = limits

    if lower is None:
        lower = -1e9

    if upper is None:
        upper = 1e9

    return (lower, upper)
