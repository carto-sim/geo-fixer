# -*- coding: utf-8 -*-
"""
Dialogue de configuration avant export Shapefile d'une couche sans géométrie.

Deux onglets, reproduisant fidèlement la logique de CsvConfigDialog (GeoAggregator) :

  Onglet 1 — « Types de champs »
    Tableau avec :
      - Ligne 0 (fond bleu) : comboboxes de type par colonne
      - Lignes 1..10 : échantillon de données
    Seuls les types compatibles avec le contenu détecté sont proposés.

  Onglet 2 — « SCR et aperçu »
    ┌── Splitter vertical ─────────────────────────────────────────────┐
    │  Haut : tableau échantillon filtré sur les colonnes pertinentes  │
    │  Bas  :                                                          │
    │    ○ Aucune géométrie                                            │
    │    ○ Longitude / Latitude → Point  [combo lon] [combo lat]       │
    │    ○ Champ WKT             [combo wkt]                           │
    │    SCR : [QgsProjectionSelectionWidget]                          │
    │    [Prévisualiser]                                               │
    │    Canvas : fond monde (gris) / SCR (rouge) / données (violet)   │
    │    Info : emprise + statut SCR                                   │
    └──────────────────────────────────────────────────────────────────┘

  Bouton OK :
    - Mode tr("Aucune géométrie") → toujours actif
    - Mode lon/lat ou WKT     → actif seulement APRÈS prévisualisation
      (règle identique à GeoAggregator : garantit la cohérence SCR/données)

Usage :
    dlg = FieldConfigDialog(layer, parent=self)
    if dlg.exec() == QDialog.Accepted:
        type_map = dlg.get_field_types()
        crs      = dlg.get_crs()           # QgsCoordinateReferenceSystem ou None
"""

import logging
from typing import Dict, List, Optional

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QWidget, QDialogButtonBox, QTabWidget, QSplitter,
    QRadioButton, QButtonGroup,
)
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QColor

from .i18n import tr
logger = logging.getLogger(__name__)

# Qt5/Qt6 compatibility and shared utilities — centralised in core/
from .core.qt_compat import (
    _QHeaderView_ResizeToContents, _QTable_NoEditTriggers, _QTable_NoSelection,
    _Qt_Window, _Qt_Vertical, _Qt_Horizontal, _QDialog_Accepted,
    _is_null,
)
from .core.utils import _NoWheelCombo, get_world_layer, make_crs_selector, make_map_canvas

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_TYPE_ROW_BG = "#d4e8fa"

_COMPATIBLE_TYPES: Dict[str, List[str]] = {
    "Integer": ["Integer", "Real", "String"],
    "Real":    ["Real",    "String"],
    "Date":    ["Date",    "String"],
    "String":  ["String"],
}

_TYPE_LABELS: Dict[str, str] = {
    "Integer": "Entier",
    "Real":    "Décimal",
    "Date":    "Date",
    "String":  "Texte",
}


# ===========================================================================
# Dialogue principal
# ===========================================================================

class FieldConfigDialog(QDialog):
    """
    Dialogue de configuration des types de champs et du SCR/géométrie
    avant export Shapefile d'une couche sans géométrie.

    Attributs internes clés :
      _crs_is_valid : None = pas encore prévisualisé
                      True  = emprise compatible avec le SCR → OK autorisé
                      False = emprise hors SCR → OK autorisé (avertissement)
      _btn_ok       : référence au bouton OK pour activer/désactiver
    """

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self._layer = layer

        # ── Widgets ────────────────────────────────────────────────────────
        self._type_combos:    Dict[str, _NoWheelCombo] = {}
        self._geom_bg:        Optional[QButtonGroup]   = None
        self._lon_combo:      Optional[_NoWheelCombo]  = None
        self._lat_combo:      Optional[_NoWheelCombo]  = None
        self._wkt_combo:      Optional[_NoWheelCombo]  = None
        self._crs_widget_ref  = None
        self._btn_preview     = None
        self._canvas          = None
        self._preview_info    = None
        self._geom_sample_label = None
        self._geom_sample_table = None
        self._btn_ok          = None
        self._preview_layers:       list = []
        self._last_data_extent_wgs  = None   # QgsRectangle WGS84, rempli par _run_preview

        # _crs_is_valid :
        #   None  → not yet previewed (or CRS/mode changed since)
        #   True  → preview OK, extent compatible with CRS
        #   False → preview OK, extent outside CRS bounds (tolerated with warning)
        self._crs_is_valid: Optional[bool] = None

        # ── Data ───────────────────────────────────────────────────────
        self._field_names  = [f.name() for f in layer.fields()]
        self._sample_rows  = self._load_sample()
        self._detected     = self._detect_types()

        # Numeric and WKT fields (for the CRS tab combos)
        self._numeric_fields = [
            n for n in self._field_names
            if self._detected.get(n) in ("Integer", "Real")
        ]
        self._wkt_fields = [
            n for n in self._field_names
            if self._detected.get(n) == "String" and self._has_wkt_values(n)
        ]

        # Window title: translated prefix + layer name (f-string safe for all languages)
        self.setWindowTitle(tr("Configuration des champs") + f" — {layer.name()}")
        self.resize(950, 620)
        self.setMinimumSize(680, 440)
        self.setWindowFlags(self.windowFlags() | _Qt_Window)

        self._build_ui()

    # ======================================================================
    # Data loading and type detection
    # ======================================================================

    def _load_sample(self) -> List[Dict[str, str]]:
        """Charge jusqu'à 10 entités pour l'affichage de l'échantillon."""
        rows = []
        try:
            from qgis.core import QgsFeatureRequest
            for feat in self._layer.getFeatures(QgsFeatureRequest().setLimit(10)):
                row = {}
                for fname in self._field_names:
                    val = feat[fname]
                    row[fname] = "" if _is_null(val) else str(val)
                rows.append(row)
        except Exception:
            pass
        return rows

    def _detect_types(self) -> Dict[str, str]:
        """
        Détecte le type effectif de chaque champ (100 entités, seuil 80 %).
        Priorité : Integer > Real > Date > String.
        """
        result = {}
        try:
            from qgis.core import QgsFeatureRequest
            import datetime

            counters = {n: {"Integer": 0, "Real": 0, "Date": 0}
                        for n in self._field_names}
            totals   = {n: 0 for n in self._field_names}

            for feat in self._layer.getFeatures(QgsFeatureRequest().setLimit(100)):
                for fname in self._field_names:
                    val = feat[fname]
                    if _is_null(val):
                        continue
                    s = str(val).strip()
                    if not s:
                        continue
                    totals[fname] += 1
                    try:
                        int(s); counters[fname]["Integer"] += 1
                    except ValueError:
                        pass
                    try:
                        float(s.replace(',', '.')); counters[fname]["Real"] += 1
                    except ValueError:
                        pass
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            datetime.datetime.strptime(s, fmt)
                            counters[fname]["Date"] += 1; break
                        except ValueError:
                            pass

            THRESHOLD = 0.8
            for fname in self._field_names:
                total = totals[fname]
                if total == 0:
                    result[fname] = "String"; continue
                if counters[fname]["Integer"] / total >= THRESHOLD:
                    result[fname] = "Integer"
                elif counters[fname]["Real"] / total >= THRESHOLD:
                    result[fname] = "Real"
                elif counters[fname]["Date"] / total >= THRESHOLD:
                    result[fname] = "Date"
                else:
                    result[fname] = "String"
        except Exception:
            result = {n: "String" for n in self._field_names}
        return result

    def _has_wkt_values(self, field_name: str) -> bool:
        """
        Vérifie si un champ String contient des valeurs WKT valides
        (au moins 2, commençant par un mot-clé WKT reconnu).
        """
        _WKT_KW = frozenset([
            "POINT", "LINESTRING", "POLYGON",
            "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
        ])
        try:
            from qgis.core import QgsGeometry, QgsFeatureRequest
            hits = 0
            for feat in self._layer.getFeatures(QgsFeatureRequest().setLimit(50)):
                val = feat[field_name]
                if _is_null(val):
                    continue
                s = str(val).strip()
                if not s:
                    continue
                kw = s.upper().split('(', 1)[0].strip()
                if kw in _WKT_KW:
                    try:
                        g = QgsGeometry.fromWkt(s)
                        if g and not g.isNull():
                            hits += 1
                            if hits >= 2:
                                return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    # ======================================================================
    # Construction de l'interface
    # ======================================================================

    def _build_ui(self) -> None:
        """Deux onglets + boutons OK/Annuler."""
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        lay.setContentsMargins(8, 8, 8, 8)

        tabs = QTabWidget()
        tabs.addTab(self._build_types_tab(), tr("Types de champs"))
        tabs.addTab(self._build_geom_tab(),  tr("SCR et aperçu"))
        lay.addWidget(tabs, stretch=1)

        try:
            _Ok  = QDialogButtonBox.StandardButton.Ok
            _Can = QDialogButtonBox.StandardButton.Cancel
        except AttributeError:
            _Ok  = QDialogButtonBox.Ok      # type: ignore
            _Can = QDialogButtonBox.Cancel  # type: ignore

        btns = QDialogButtonBox(_Ok | _Can, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self._btn_ok = btns.button(_Ok)
        lay.addWidget(btns)

        # Initialise the OK button state
        self._update_ok_button()

    # ------------------------------------------------------------------
    # Onglet 1 — Types de champs
    # ------------------------------------------------------------------

    def _build_types_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        if len(self._field_names) <= 1:
            warn = QLabel(
                "<span style='color:#a04000;font-size:10px;font-weight:bold;'>"
                "⚠ Une seule colonne détectée — délimiteur CSV peut-être incorrect."
                " Fermez, supprimez la couche et rouvrez via « Ouvrir un fichier… »."
                "</span>"
            )
            warn.setWordWrap(True)
            lay.addWidget(warn)

        info = QLabel(
            "<span style='color:#555;font-size:10px;'>"
            "Ligne bleue : type de chaque colonne. "
            "Cliquez pour modifier. "
            "Seuls les types compatibles avec le contenu détecté sont proposés."
            "</span>"
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        n_cols = len(self._field_names)
        n_data = len(self._sample_rows)
        table  = QTableWidget(1 + n_data, n_cols)
        table.setEditTriggers(_QTable_NoEditTriggers)
        table.setSelectionMode(_QTable_NoSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(22)
        table.setRowHeight(0, 30)
        table.setAlternatingRowColors(False)

        for col, fname in enumerate(self._field_names):
            auto_type  = self._detected.get(fname, "String")
            compatible = _COMPATIBLE_TYPES.get(auto_type, ["String"])

            hdr = QTableWidgetItem(fname)
            hdr.setToolTip(f"Type détecté automatiquement : {auto_type}")
            table.setHorizontalHeaderItem(col, hdr)

            cb = _NoWheelCombo()
            cb.setStyleSheet(f"background-color:{_TYPE_ROW_BG};border:none;")
            for t in compatible:
                cb.addItem(f"{t}  —  {_TYPE_LABELS.get(t, t)}", t)
            table.setCellWidget(0, col, cb)
            self._type_combos[fname] = cb

            for row, row_data in enumerate(self._sample_rows):
                item = QTableWidgetItem(row_data.get(fname, ""))
                if row % 2 == 0:
                    item.setBackground(QColor("#f5f5f5"))
                table.setItem(1 + row, col, item)

        table.horizontalHeader().setSectionResizeMode(_QHeaderView_ResizeToContents)
        lay.addWidget(table, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Tab 2 — CRS and preview
    # ------------------------------------------------------------------

    def _build_geom_tab(self) -> QWidget:
        """
        Reproduit l'onglet "Géométrie et aperçu" de GeoAggregator.

        Splitter vertical :
          Haut : échantillon filtré sur les colonnes pertinentes au mode choisi
          Bas  : radios de mode + SCR + bouton Prévisualiser + canvas + info

        Bouton OK :
          - Mode tr("Aucune géométrie") → toujours actif
          - Mode lon/lat ou WKT → actif seulement après prévisualisation
            (même règle que GeoAggregator)
        """
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        has_num = bool(self._numeric_fields)
        has_wkt = bool(self._wkt_fields)

        if not has_num and not has_wkt:
            lay.addWidget(QLabel(
                tr("Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
                   "Vous pourrez définir la géométrie à l'étape 2.")
            ))
            lay.addStretch()
            return w

        # ── Global vertical splitter: sample (top) / bottom area (bottom) ──
        v_splitter = QSplitter(_Qt_Vertical)

        # ── Top: filtered sample table ────────────────────────────────
        sample_top = QWidget()
        sl = QVBoxLayout(sample_top)
        sl.setContentsMargins(4, 4, 4, 0)
        sl.setSpacing(2)
        self._geom_sample_label = QLabel("")
        self._geom_sample_label.setStyleSheet("color:#555;font-size:10px;")
        sl.addWidget(self._geom_sample_label)
        self._geom_sample_table = QTableWidget()
        self._geom_sample_table.setEditTriggers(_QTable_NoEditTriggers)
        self._geom_sample_table.setAlternatingRowColors(True)
        self._geom_sample_table.setMaximumHeight(150)
        self._geom_sample_table.verticalHeader().setDefaultSectionSize(22)
        sl.addWidget(self._geom_sample_table)
        v_splitter.addWidget(sample_top)

        # ── Bottom: horizontal splitter — params (left) / canvas (right) ─
        # Same layout as step 2 of the main GeoFixer dialog.
        # _Qt_Horizontal is already resolved in the qt_compat import at the top.
        h_splitter = QSplitter()
        h_splitter.setOrientation(_Qt_Horizontal)

        # ── Left: radios + CRS + Preview button ──────────────────────────
        left_w = QWidget()
        bl = QVBoxLayout(left_w)
        bl.setContentsMargins(6, 4, 4, 4)
        bl.setSpacing(4)

        self._geom_bg = QButtonGroup(left_w)
        rb_none = QRadioButton(tr("Aucune géométrie"))
        rb_none.setChecked(True)
        self._geom_bg.addButton(rb_none, 0)
        bl.addWidget(rb_none)

        lonlat_w = self._build_lonlat_widget(bl) if has_num else None
        wkt_w    = self._build_wkt_widget(bl)    if has_wkt else None

        crs_w = self._build_crs_widget()
        crs_w.setVisible(False)
        bl.addWidget(crs_w)

        self._btn_preview = QPushButton(tr("🔍  Prévisualiser"))
        self._btn_preview.setEnabled(False)
        self._btn_preview.setStyleSheet(
            "QPushButton{background:#27ae60;color:white;"
            "padding:4px 14px;border-radius:3px;}"
            "QPushButton:disabled{background:#bdc3c7;}"
        )
        bl.addWidget(self._btn_preview)

        # Info label below the parameters
        self._preview_info = QLabel("")
        self._preview_info.setStyleSheet("color:#555;font-size:10px;")
        self._preview_info.setWordWrap(True)
        bl.addWidget(self._preview_info)
        bl.addStretch()

        h_splitter.addWidget(left_w)

        # ── Droite : canvas ───────────────────────────────────────────────
        right_w = QWidget()
        rl = QVBoxLayout(right_w)
        rl.setContentsMargins(4, 4, 6, 4)
        rl.setSpacing(0)

        try:
            from qgis.gui import QgsMapCanvas
            self._canvas = QgsMapCanvas()
            self._canvas.setMinimumHeight(200)
            self._canvas.setMinimumWidth(280)
            self._canvas.setCanvasColor(QColor("#e8e8e8"))
            self._canvas.setVisible(False)
            rl.addWidget(self._canvas, stretch=1)
        except Exception:
            self._canvas = None

        h_splitter.addWidget(right_w)
        h_splitter.setSizes([400, 360])

        v_splitter.addWidget(h_splitter)
        v_splitter.setSizes([130, 420])
        lay.addWidget(v_splitter, stretch=1)

        # ── Connexions ────────────────────────────────────────────────────
        def _on_mode(btn_id,
                     _lw=lonlat_w, _ww=wkt_w, _cw=crs_w,
                     _bp=self._btn_preview):
            if _lw: _lw.setVisible(btn_id == 1)
            if _ww: _ww.setVisible(btn_id == 2)
            _cw.setVisible(btn_id != 0)
            _bp.setEnabled(btn_id != 0)
            if self._canvas:
                self._canvas.setVisible(False)
            if self._preview_info:
                self._preview_info.setText("")
                self._preview_info.setStyleSheet("color:#555;font-size:10px;")
            # Changing mode invalidates the previous preview
            self._crs_is_valid = None
            self._update_ok_button()
            self._refresh_geom_sample(btn_id)

        self._geom_bg.idClicked.connect(_on_mode)
        self._btn_preview.clicked.connect(self._run_preview)

        # Initialisation
        if has_wkt and not has_num:
            self._geom_bg.button(2).setChecked(True)
            _on_mode(2)
        else:
            _on_mode(0)

        return w

    def _build_lonlat_widget(self, parent_layout) -> QWidget:
        """Sous-widget Lon/Lat avec pré-sélection automatique."""
        rb = QRadioButton(tr("Longitude / Latitude  →  Point"))
        self._geom_bg.addButton(rb, 1)
        parent_layout.addWidget(rb)

        w  = QWidget()
        ll = QHBoxLayout(w)
        ll.setContentsMargins(20, 0, 0, 0)
        ll.setSpacing(8)
        ll.addWidget(QLabel(tr("Longitude :")))
        self._lon_combo = _NoWheelCombo()
        self._lon_combo.addItems(self._numeric_fields)
        ll.addWidget(self._lon_combo)
        ll.addWidget(QLabel(tr("Latitude :")))
        self._lat_combo = _NoWheelCombo()
        self._lat_combo.addItems(self._numeric_fields)
        ll.addWidget(self._lat_combo)
        ll.addStretch()
        w.setVisible(False)
        parent_layout.addWidget(w)

        # Automatic pre-selection by field name
        for f in self._numeric_fields:
            fl = f.lower()
            if any(k in fl for k in ("lon", "lng", "longitude", "x_coord", "xcoord")):
                self._lon_combo.setCurrentText(f)
            if any(k in fl for k in ("lat", "latitude", "y_coord", "ycoord")):
                self._lat_combo.setCurrentText(f)

        return w

    def _build_wkt_widget(self, parent_layout) -> QWidget:
        """Sous-widget sélection du champ WKT."""
        rb = QRadioButton(tr("Champ WKT (Well-Known Text)"))
        self._geom_bg.addButton(rb, 2)
        parent_layout.addWidget(rb)

        w  = QWidget()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(20, 0, 0, 0)
        wl.setSpacing(8)
        wl.addWidget(QLabel(tr("Champ WKT :")))
        self._wkt_combo = _NoWheelCombo()
        self._wkt_combo.addItems(self._wkt_fields)
        wl.addWidget(self._wkt_combo)
        wl.addStretch()
        w.setVisible(False)
        parent_layout.addWidget(w)
        return w

    def _build_crs_widget(self) -> QWidget:
        """Sélecteur de SCR — délégué à core.utils.make_crs_selector()."""
        crs_w = QWidget()
        cr    = QHBoxLayout(crs_w)
        cr.setContentsMargins(0, 2, 0, 0)
        cr.setSpacing(8)
        cr.addWidget(QLabel(tr("SCR :")))
        self._crs_widget_ref = make_crs_selector()
        self._crs_widget_ref.crsChanged.connect(self._on_crs_changed)
        cr.addWidget(self._crs_widget_ref, stretch=1)
        return crs_w

    # ======================================================================
    # Filtered sample table
    # ======================================================================

    def _refresh_geom_sample(self, mode_id: int) -> None:
        """Met à jour le tableau d'échantillon selon le mode actif."""
        n = len(self._sample_rows)
        if mode_id == 1:
            cols  = self._numeric_fields
            title = tr("Colonnes numériques candidates (lon/lat) — {n} entité(s)").format(n=n)
        elif mode_id == 2:
            cols  = self._wkt_fields
            title = tr("Colonnes WKT détectées — {n} entité(s)").format(n=n)
        else:
            all_useful = list(dict.fromkeys(self._numeric_fields + self._wkt_fields))
            cols  = all_useful[:6] or self._field_names[:6]
            title = tr("Aperçu — {n} entité(s)").format(n=n)

        if self._geom_sample_label:
            self._geom_sample_label.setText(
                f"<span style='color:#555;font-size:10px;'>{title}</span>"
            )

        t = self._geom_sample_table
        if t is None:
            return
        t.clear()
        t.setColumnCount(len(cols))
        t.setRowCount(len(self._sample_rows))
        t.setHorizontalHeaderLabels([
            f"{c}  ({self._detected.get(c, 'String')})" for c in cols
        ])
        for row, row_data in enumerate(self._sample_rows):
            for ci, fname in enumerate(cols):
                t.setItem(row, ci, QTableWidgetItem(row_data.get(fname, "")))
        t.horizontalHeader().setSectionResizeMode(_QHeaderView_ResizeToContents)

    # ======================================================================
    # Map preview
    # ======================================================================

    def _run_preview(self) -> None:
        """
        Calcule l'emprise des données depuis les champs sélectionnés,
        l'affiche sur le canvas et met à jour _crs_is_valid.

        Logique identique à GeoAggregator _run_preview :
          1. Parcourir les entités de la couche et calculer la bounding box
          2. Convertir en WGS84
          3. Construire les couches canvas (données violet / SCR rouge / monde gris)
          4. Zoom sur l'union SCR + données
          5. Valider la compatibilité SCR/données
          6. Mettre à jour le bouton OK
        """
        try:
            from qgis.core import (
                QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
                QgsRectangle, QgsCoordinateReferenceSystem,
                QgsCoordinateTransform, QgsProject,
                QgsSingleSymbolRenderer, QgsFillSymbol,
            )

            mode_id = self._geom_bg.checkedId() if self._geom_bg else 0

            # ── Lire le SCR ───────────────────────────────────────────────
            crs_str = "EPSG:4326"
            try:
                from qgis.gui import QgsProjectionSelectionWidget as _QPSW
                if isinstance(self._crs_widget_ref, _QPSW):
                    crs_obj = self._crs_widget_ref.crs()
                    crs_str = crs_obj.authid() if crs_obj.isValid() else "EPSG:4326"
                else:
                    crs_str = f"EPSG:{self._crs_widget_ref.currentData() or 4326}"
            except Exception:
                pass

            crs_wgs84   = QgsCoordinateReferenceSystem("EPSG:4326")
            crs_display = QgsCoordinateReferenceSystem(crs_str)

            # ── Compute the data extent ───────────────────────────────────
            min_x = min_y =  1e18
            max_x = max_y = -1e18
            n_valid = 0
            errors  = 0

            lon_col = self._lon_combo.currentText() if self._lon_combo else ""
            lat_col = self._lat_combo.currentText() if self._lat_combo else ""
            wkt_col = self._wkt_combo.currentText() if self._wkt_combo else ""

            for feat in self._layer.getFeatures():
                try:
                    if mode_id == 1 and lon_col and lat_col:
                        rx = feat[lon_col]; ry = feat[lat_col]
                        if _is_null(rx) or _is_null(ry):
                            errors += 1; continue
                        x = float(str(rx).replace(',', '.'))
                        y = float(str(ry).replace(',', '.'))
                        if x != x or y != y:   # NaN
                            errors += 1; continue
                        if x < min_x: min_x = x
                        if x > max_x: max_x = x
                        if y < min_y: min_y = y
                        if y > max_y: max_y = y
                        n_valid += 1

                    elif mode_id == 2 and wkt_col:
                        raw = feat[wkt_col]
                        if _is_null(raw) or not str(raw).strip():
                            errors += 1; continue
                        geom = QgsGeometry.fromWkt(str(raw).strip())
                        if geom and not geom.isNull():
                            bb = geom.boundingBox()
                            if bb.xMinimum() < min_x: min_x = bb.xMinimum()
                            if bb.xMaximum() > max_x: max_x = bb.xMaximum()
                            if bb.yMinimum() < min_y: min_y = bb.yMinimum()
                            if bb.yMaximum() > max_y: max_y = bb.yMaximum()
                            n_valid += 1
                        else:
                            errors += 1
                except Exception:
                    errors += 1

            if n_valid == 0:
                self._preview_info.setStyleSheet("color:#cc0000;font-size:10px;")
                parts = ["Aucune géométrie valide dans les champs sélectionnés."]
                if errors:
                    parts.append(f"({errors} valeur(s) invalide(s) ou nulle(s))")
                self._preview_info.setText("  ".join(parts))
                self._crs_is_valid = None
                return

            data_native = QgsRectangle(min_x, min_y, max_x, max_y)

            # Convertir en WGS84
            if crs_str != "EPSG:4326":
                xform = QgsCoordinateTransform(
                    crs_display, crs_wgs84, QgsProject.instance()
                )
                data_wgs = xform.transformBoundingBox(data_native)
            else:
                data_wgs = data_native

            # Stocker l'emprise WGS84 pour que l'appelant puisse l'utiliser
            # (the created Shapefile has NULL geometries → extent() would be empty)
            self._last_data_extent_wgs = data_wgs

            # ── Zoom = union of CRS extent + data extent ─────────────────
            crs_bounds = crs_display.bounds()
            if crs_bounds.isNull() or crs_bounds.width() == 0:
                zoom = QgsRectangle(data_wgs)
            else:
                zoom = QgsRectangle(crs_bounds)
                zoom.combineExtentWith(data_wgs)

            # ── Construire les couches canvas ─────────────────────────────
            self._preview_layers = []

            # Data extent (purple)
            lyr_d = QgsVectorLayer("Polygon?crs=EPSG:4326", "data_extent", "memory")
            fd = QgsFeature()
            fd.setGeometry(QgsGeometry.fromRect(data_wgs))
            lyr_d.dataProvider().addFeature(fd)
            lyr_d.setRenderer(QgsSingleSymbolRenderer(
                QgsFillSymbol.createSimple({
                    "color": "120,0,180,128",
                    "outline_color": "120,0,180,220",
                    "outline_width": "1.2",
                })
            ))
            self._preview_layers.append(lyr_d)

            # Emprise SCR (rouge)
            has_crs_bounds = not crs_bounds.isNull() and crs_bounds.width() > 0
            if has_crs_bounds:
                lyr_c = QgsVectorLayer("Polygon?crs=EPSG:4326", "crs_bounds", "memory")
                fc = QgsFeature()
                fc.setGeometry(QgsGeometry.fromRect(crs_bounds))
                lyr_c.dataProvider().addFeature(fc)
                lyr_c.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "220,0,0,80",
                        "outline_color": "220,0,0,220",
                        "outline_width": "0.8",
                    })
                ))
                self._preview_layers.append(lyr_c)

            # Fond monde (gris)
            world = get_world_layer()
            if world:
                world.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "#d0d0d0",
                        "outline_color": "#888888",
                        "outline_width": "0.15",
                    })
                ))
                self._preview_layers.append(world)

            # ── Afficher ──────────────────────────────────────────────────
            if self._canvas:
                self._canvas.setVisible(True)
                self._canvas.setDestinationCrs(crs_wgs84)
                self._canvas.setLayers(self._preview_layers)
                self._canvas.setExtent(zoom)
                # Deferred refresh: the canvas was just made visible and
                # does not yet have its final dimensions.
                QTimer.singleShot(80, self._canvas.refresh)

            # ── Validation: data extent within CRS bounds? ────────────────
            if has_crs_bounds:
                self._crs_is_valid = crs_bounds.intersects(data_wgs)
            else:
                self._crs_is_valid = True   # CRS without known bounds → accepted

            # ── Texte d'info ──────────────────────────────────────────────
            e = data_wgs
            info_txt = (
                f"Emprise des données — "
                f"X [{e.xMinimum():.4f} … {e.xMaximum():.4f}]  "
                f"Y [{e.yMinimum():.4f} … {e.yMaximum():.4f}]"
                + (f"  ({errors} valeur(s) invalide(s) ignorée(s))" if errors else "")
            )
            if self._crs_is_valid:
                status = (
                    f"✔ L'emprise des données est compatible avec {crs_str} — "
                    f"SCR appliqué au Shapefile"
                )
                self._preview_info.setStyleSheet("color:#1a6e1a;font-size:10px;")
            else:
                status = (
                    f"⚠ L'emprise des données est hors de l'emprise de {crs_str} — "
                    f"vérifiez le SCR sélectionné"
                )
                self._preview_info.setStyleSheet("color:#a04000;font-size:10px;")
            self._preview_info.setText(info_txt + "\n" + status)

        except Exception as exc:
            logger.exception("FieldConfigDialog : erreur lors de la prévisualisation.")
            self._crs_is_valid = None
            self._preview_info.setStyleSheet("color:#cc0000;font-size:10px;")
            self._preview_info.setText(f"Erreur : {exc}")
        finally:
            self._update_ok_button()

    # ======================================================================
    # OK button state and CRS change handler
    # ======================================================================

    def _update_ok_button(self) -> None:
        """
        Active/désactive le bouton OK.

        Règles :
          - Mode 0 (aucune géométrie) → OK toujours actif
          - Mode 1 ou 2              → OK actif seulement si _crs_is_valid == True
            (prévisualisation obligatoire ET emprise dans les bounds du SCR)
            Si l'emprise est hors du SCR (_crs_is_valid == False), OK est bloqué :
            l'utilisateur doit choisir un SCR cohérent avec ses données.
        """
        if self._btn_ok is None:
            return
        mode_id = self._geom_bg.checkedId() if self._geom_bg else 0
        if mode_id == 0:
            self._btn_ok.setEnabled(True)
        else:
            # Strictly True: False (outside bounds) and None (not previewed) both block
            self._btn_ok.setEnabled(self._crs_is_valid is True)

    def _on_crs_changed(self, *_args) -> None:
        """
        Invalidation de la prévisualisation quand le SCR change.
        Masque le canvas et verrouille OK jusqu'à la prochaine prévisualisation.
        """
        self._crs_is_valid = None
        if self._canvas:
            self._canvas.setVisible(False)
        if self._preview_info:
            self._preview_info.setText(
                "⚠ SCR modifié — veuillez prévisualiser à nouveau avant de valider."
            )
            self._preview_info.setStyleSheet("color:#a04000;font-size:10px;")
        self._update_ok_button()

    # ======================================================================
    # Public API
    # ======================================================================

    def get_geometry_mode(self) -> int:
        """Return the selected geometry mode: 0=none, 1=lon/lat, 2=WKT."""
        return self._geom_bg.checkedId() if self._geom_bg else 0

    def get_coordinate_fields(self) -> tuple:
        """Return (lon_field, lat_field, wkt_field) for the current selection."""
        lon = self._lon_combo.currentText() if self._lon_combo else ""
        lat = self._lat_combo.currentText() if self._lat_combo else ""
        wkt = self._wkt_combo.currentText() if self._wkt_combo else ""
        return (lon, lat, wkt)

    def get_data_extent_wgs84(self):
        """
        Retourne la bounding box WGS84 calculée lors de la dernière prévisualisation.

        Utilisée par l'appelant pour afficher l'emprise des données dans le
        canvas de l'étape 1, même quand toutes les géométries du Shapefile
        sont encore NULL (elles le sont toujours à la création).

        :return: QgsRectangle en WGS84, ou None si aucune prévisualisation n'a eu lieu.
        """
        return self._last_data_extent_wgs

    def get_field_types(self) -> Dict[str, str]:
        """Retourne {nom_champ: type} choisi par l'utilisateur."""
        return {
            fname: cb.currentData()
            for fname, cb in self._type_combos.items()
        }

    def get_crs(self):
        """
        Retourne le SCR sélectionné si la prévisualisation a été effectuée
        et que le mode géométrique est lon/lat ou WKT.

        Règle identique à GeoAggregator : si _crs_is_valid est None (pas
        prévisualisé) ou False (hors emprise), retourne None pour que
        l'appelant puisse décider du comportement.

        :return: QgsCoordinateReferenceSystem valide ou None
        """
        mode_id = self._geom_bg.checkedId() if self._geom_bg else 0
        if mode_id == 0 or self._crs_is_valid is None:
            return None
        try:
            from qgis.gui import QgsProjectionSelectionWidget as _QPSW
            if isinstance(self._crs_widget_ref, _QPSW):
                crs = self._crs_widget_ref.crs()
                return crs if crs.isValid() else None
        except Exception:
            pass
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            epsg = self._crs_widget_ref.currentData()
            if epsg:
                return QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        except Exception:
            pass
        return None
