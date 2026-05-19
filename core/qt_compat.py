# -*- coding: utf-8 -*-
"""
Compatibilité Qt5 (QGIS 3) / Qt6 (QGIS 4) pour le plugin GeoFixer.

Qt6 a déplacé toutes les constantes des widgets dans des énumérations imbriquées.
Ce module centralise la résolution de toutes ces constantes en un seul endroit,
évitant les blocs try/except dispersés dans chaque fichier.

Usage :
    from .core.qt_compat import (
        _QFrame_HLine, _QFrame_Sunken,
        _QTable_ExtendedSelection, _QTable_SelectRows, _QTable_NoEditTriggers,
        _QTable_NoSelection,
        _QHeaderView_ResizeToContents, _QHeaderView_Stretch,
        _Qt_UserRole, _Qt_DisplayRole,
        _Qt_Window, _Qt_WindowMaximize, _Qt_Vertical, _Qt_Horizontal,
        _QMsgBox_Yes, _QMsgBox_No,
        _QDialog_Accepted,
    )
"""

from qgis.PyQt.QtWidgets import (
    QFrame, QAbstractItemView, QHeaderView,
    QMessageBox, QDialog,
)
from qgis.PyQt.QtCore import Qt

try:
    # ── Qt6 / PyQt6 — QGIS 4 ─────────────────────────────────────────────────
    _QFrame_HLine   = QFrame.Shape.HLine
    _QFrame_Sunken  = QFrame.Shadow.Sunken

    _QTable_ExtendedSelection = QAbstractItemView.SelectionMode.ExtendedSelection
    _QTable_SelectRows        = QAbstractItemView.SelectionBehavior.SelectRows
    _QTable_NoEditTriggers    = QAbstractItemView.EditTrigger.NoEditTriggers
    _QTable_NoSelection       = QAbstractItemView.SelectionMode.NoSelection

    _QHeaderView_ResizeToContents = QHeaderView.ResizeMode.ResizeToContents
    _QHeaderView_Stretch          = QHeaderView.ResizeMode.Stretch

    _Qt_UserRole       = Qt.ItemDataRole.UserRole
    _Qt_DisplayRole    = Qt.ItemDataRole.DisplayRole
    _Qt_WindowMaximize = Qt.WindowType.WindowMaximizeButtonHint
    _Qt_Window         = Qt.WindowType.Window
    _Qt_Vertical       = Qt.Orientation.Vertical
    _Qt_Horizontal     = Qt.Orientation.Horizontal

    _QMsgBox_Yes = QMessageBox.StandardButton.Yes
    _QMsgBox_No  = QMessageBox.StandardButton.No

    _QDialog_Accepted = QDialog.DialogCode.Accepted

except AttributeError:
    # ── Qt5 / PyQt5 — QGIS 3 ─────────────────────────────────────────────────
    _QFrame_HLine   = QFrame.HLine    # type: ignore[attr-defined]
    _QFrame_Sunken  = QFrame.Sunken   # type: ignore[attr-defined]

    _QTable_ExtendedSelection = QAbstractItemView.ExtendedSelection  # type: ignore
    _QTable_SelectRows        = QAbstractItemView.SelectRows          # type: ignore
    _QTable_NoEditTriggers    = QAbstractItemView.NoEditTriggers      # type: ignore
    _QTable_NoSelection       = QAbstractItemView.NoSelection         # type: ignore

    _QHeaderView_ResizeToContents = QHeaderView.ResizeToContents  # type: ignore
    _QHeaderView_Stretch          = QHeaderView.Stretch           # type: ignore

    _Qt_UserRole       = Qt.UserRole                  # type: ignore
    _Qt_DisplayRole    = Qt.DisplayRole               # type: ignore
    _Qt_WindowMaximize = Qt.WindowMaximizeButtonHint  # type: ignore
    _Qt_Window         = Qt.Window                    # type: ignore
    _Qt_Vertical       = Qt.Vertical                  # type: ignore
    _Qt_Horizontal     = Qt.Horizontal                # type: ignore

    _QMsgBox_Yes = QMessageBox.Yes   # type: ignore
    _QMsgBox_No  = QMessageBox.No    # type: ignore

    _QDialog_Accepted = QDialog.Accepted  # type: ignore


# ── NULL attribute value detection ───────────────────────────────────────────
# In QGIS 3 / PyQt5, null attribute values are QPyNullVariant objects.
# In QGIS 4 / PyQt6, they are Python None or a falsy QVariant sentinel.
# qgis.core.NULL is a singleton that compares equal to any null variant
# across both versions and is the recommended cross-version null check.
try:
    from qgis.core import NULL as _QGIS_NULL

    def _is_null(val) -> bool:
        """Return True if a QGIS attribute value is NULL (QGIS 3 and 4 safe)."""
        return val is None or val == _QGIS_NULL
except ImportError:
    def _is_null(val) -> bool:  # type: ignore[misc]
        return val is None or (
            hasattr(val, '__class__') and
            val.__class__.__name__ in ('QPyNullVariant', 'QVariant')
        )


# ── QgsMapLayerProxyModel filter constant ────────────────────────────────────
# Qt6 / QGIS 4 moved enum values into nested enum classes.
try:
    from qgis.core import QgsMapLayerProxyModel as _QMLPM
    try:
        _QMapLayerProxyModel_VectorLayer = _QMLPM.Filter.VectorLayer  # QGIS 4
    except AttributeError:
        _QMapLayerProxyModel_VectorLayer = _QMLPM.VectorLayer          # QGIS 3
except ImportError:
    _QMapLayerProxyModel_VectorLayer = None


# ── QgsVectorDataProvider.ChangeGeometries capability flag ───────────────────
# Qt6 / QGIS 4 moved capability flags into a nested Capability enum.
try:
    from qgis.core import QgsVectorDataProvider as _QVDP
    try:
        _QVDataProvider_ChangeGeometries = _QVDP.Capability.ChangeGeometries  # QGIS 4
    except AttributeError:
        _QVDataProvider_ChangeGeometries = _QVDP.ChangeGeometries              # QGIS 3
except ImportError:
    _QVDataProvider_ChangeGeometries = 4  # numeric fallback (historic value)
