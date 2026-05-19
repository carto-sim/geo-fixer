# -*- coding: utf-8 -*-
"""
Dialogue principal du plugin GeoFixer.

Deux étapes (QStackedWidget) :

  Étape 1 — Sélection et SCR
    - Combobox de couche (vide au démarrage) + ouverture de fichier
    - Sélecteur SCR + bouton tr("Appliquer le SCR")
      → Désactivé si l'emprise de la couche n'est pas contenue dans les bounds du SCR
    - Canvas : fond monde / emprise SCR (rouge) / emprise couche (violet)
      L'emprise couche est interprétée dans le SCR sélectionné (vérification visuelle
      de cohérence SCR / coordonnées)

  Étape 2 — Correction
    - Tableau des entités problématiques (champs utiles détectés par valeurs + Raison)
    - Action "Reprojeter" : l'utilisateur renseigne le SCR D'ORIGINE des entités
      mal projetées → le plugin reprojette vers le SCR courant de la couche (étape 1)
    - Action "Depuis les champs" : lon/lat ou WKT + sélecteur "SCR source"
      optionnel pour reprojeter vers le SCR couche
    - Bouton "Prévisualiser" : canvas identique à l'étape 1

Architecture :
  - Fenêtre NON-MODALE (Qt.Window), parent=None pour entrée taskbar indépendante
  - Logique métier dans core/ (layer_inspector, geometry_fixer)
  - Refresh canvas via QTimer.singleShot(80 ms)
"""

import copy
import logging
from typing import Dict, List, Optional

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QWidget, QGroupBox,
    QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QStackedWidget,
    QSplitter, QCheckBox, QFrame,
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QColor, QFont

# Qt5/Qt6 compatibility and shared utilities — centralised in core/
from .core.qt_compat import (
    _QFrame_HLine, _QFrame_Sunken,
    _QTable_ExtendedSelection, _QTable_SelectRows, _QTable_NoEditTriggers,
    _QHeaderView_ResizeToContents, _QHeaderView_Stretch,
    _Qt_UserRole, _Qt_DisplayRole,
    _Qt_Window, _Qt_WindowMaximize, _Qt_Vertical, _Qt_Horizontal,
    _QMsgBox_Yes, _QMsgBox_No, _QDialog_Accepted,
    _QMapLayerProxyModel_VectorLayer,
)
from .core.utils import _NoWheelCombo, get_world_layer, make_crs_selector, make_map_canvas

from .i18n import tr
from .core.layer_inspector import (
    find_problematic_features, is_csv_layer,
    detect_field_types_by_values, ProblematicFeature,
)
from .field_config_dialog import FieldConfigDialog
from .core.geometry_fixer import (
    apply_crs_to_layer,
    reproject_features,
    build_geometry_from_lonlat,
    build_geometry_from_wkt,
    build_memory_layer_from_lonlat,
    build_memory_layer_from_wkt,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes visuelles
# ---------------------------------------------------------------------------
_COLOR_SUCCESS       = "#1a6e1a"
_COLOR_WARNING       = "#a04000"
_COLOR_DANGER        = "#cc0000"
_COLOR_INFO          = "#555555"
_COLOR_STEP_ACTIVE   = "#1a6e1a"
_COLOR_STEP_INACTIVE = "#888888"

_FILE_FILTER = (
    "Fichiers vectoriels "
    "(*.shp *.gpkg *.geojson *.json *.kml *.kmz *.gml *.gdb"
    " *.csv *.tsv *.tab *.mif *.mid *.gpx *.dxf *.dwg"
    " *.sqlite *.db *.gz *.zip);;"
    "Shapefile (*.shp);;"
    "GeoPackage (*.gpkg);;"
    "GeoJSON / JSON (*.geojson *.json);;"
    "KML / KMZ (*.kml *.kmz);;"
    "GML (*.gml);;"
    "CSV / TSV (*.csv *.tsv);;"
    "MapInfo TAB (*.tab);;"
    "MapInfo MIF/MID (*.mif *.mid);;"
    "GPS Exchange Format (*.gpx);;"
    "AutoCAD DXF (*.dxf);;"
    "AutoCAD DWG (*.dwg);;"
    "ESRI FileGDB (*.gdb);;"
    "SQLite / SpatiaLite (*.sqlite *.db);;"
    "Fichiers compressés (*.gz *.zip);;"
    "Tous les fichiers (*)"
)

# Additional multi-layer formats (DWG, DXF included)
# Note: *.mif opens the layer via its associated .mid file automatically.

_MAX_PREVIEW_FEATURES = 1000


# ===========================================================================
# Automatic CSV delimiter detection
# ===========================================================================

def _detect_csv_delimiter(file_path: str) -> str:
    """
    Détecte automatiquement le délimiteur d'un fichier CSV.

    Stratégie :
      La ligne d'en-tête (première ligne non vide) est analysée en priorité.
      Les noms de champs ne contiennent généralement pas de texte libre, ce
      qui les rend beaucoup plus fiables pour la détection que les lignes de
      données (qui peuvent contenir du texte avec virgules, points, etc.).

      Algorithme :
        1. Lire la ligne d'en-tête et compter les occurrences de chaque
           délimiteur candidat. Le délimiteur avec le plus grand nombre
           d'occurrences est le vainqueur provisoire.
        2. Vérifier la cohérence sur les 5 premières lignes de données :
           le vainqueur doit donner un nombre de colonnes identique sur
           au moins 2 des 3 premières lignes de données non vides.
        3. Si la vérification échoue, relancer sur la ligne d'en-tête seule
           (parfois les données sont très hétérogènes).
        4. Repli sur la virgule si tout échoue.

    :param file_path: Chemin du fichier CSV à analyser
    :return:          Caractère délimiteur détecté (',', ';', '\t', '|', etc.)
    """
    _CANDIDATES = [';', '\t', ',', '|', ':']   # ';' first (very common in French locale exports)

    # ── Lire le fichier (encodage auto) ──────────────────────────────────────
    header_line  = ""
    data_lines   = []
    encoding_ok  = "utf-8"

    for encoding in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as fh:
                all_lines = []
                for line in fh:
                    stripped = line.rstrip('\n\r')
                    if stripped:
                        all_lines.append(stripped)
                    if len(all_lines) >= 8:
                        break
            if all_lines:
                encoding_ok  = encoding
                header_line  = all_lines[0]
                data_lines   = all_lines[1:6]
                break
        except OSError:
            continue

    if not header_line:
        return ','

    # ── Step 1: count delimiter occurrences in the header line ──────────────
    header_counts = {d: header_line.count(d) for d in _CANDIDATES}

    # Sort by occurrence count descending
    ranked = sorted(_CANDIDATES, key=lambda d: header_counts[d], reverse=True)

    # Le candidat avec 0 occurrence est inutile
    ranked = [d for d in ranked if header_counts[d] > 0]
    if not ranked:
        return ','   # No candidate delimiter found in the header

    # ── Step 2: verify consistency across data lines ────────────────────────
    # For each candidate (most to least frequent), verify that the column
    # count on the first data line is ≥ 2 and consistent.
    for candidate in ranked:
        n_header_cols = header_counts[candidate] + 1   # column count = separator count + 1

        if n_header_cols < 2:
            continue   # Only one delimiter in header = cannot be a real separator

        if not data_lines:
            # No data lines: trust the header alone
            return candidate

        # Count columns on each data line
        data_col_counts = [line.count(candidate) + 1 for line in data_lines]

        # Accept if at least half the lines yield ≥ 2 columns AND
        # at least 1 line matches the header column count exactly
        n_matching = sum(1 for c in data_col_counts if c == n_header_cols)
        n_at_least_2 = sum(1 for c in data_col_counts if c >= 2)

        # The candidate is accepted if:
        #   - at least 1 data line matches the header exactly, OR
        #   - at least half the lines yield ≥ 2 columns
        if n_matching >= 1 or n_at_least_2 >= max(1, len(data_lines) // 2):
            return candidate

    # ── Step 3: fallback — trust the header line alone ──────────────────────
    # Data lines are too heterogeneous for reliable verification.
    # Return the delimiter with the most occurrences in the header.
    return ranked[0]


# ===========================================================================
# Dialogue principal
# ===========================================================================

class GeoFixerDialog(QDialog):
    """
    Assistant de correction de géométrie en deux étapes.

    Attributs clés :
      _iface             : QgisInterface
      _current_layer     : QgsVectorLayer sélectionnée
      _applied_crs       : QgsCoordinateReferenceSystem appliqué à la couche
      _field_type_info   : Dict {nom_champ: FieldTypeInfo} — détection par valeurs
      _numeric_fields    : champs numériques (candidats lon/lat)
      _wkt_fields        : champs WKT candidats
    """

    def __init__(self, iface, parent=None):
        # parent=None: independent window with its own taskbar entry
        super().__init__(parent)
        self._iface = iface

        # ── État interne ──────────────────────────────────────────────────
        self._current_layer      = None
        self._applied_crs        = None
        self._field_type_info:   Dict = {}
        self._numeric_fields:    List[str] = []
        self._wkt_fields:        List[str] = []
        self._problematic_feats: List[ProblematicFeature] = []
        self._preview_layers:    list = []
        self._preview_layers_s2: list = []
        # WGS84 extent computed from fields during Shapefile configuration.
        # Used in the step-1 canvas when the Shapefile has NULL geometries.
        self._cached_data_extent_wgs = None

        # ── Widget references (initialised in _build_*) ─────────────────
        # Étape 1
        self._layer_combo      = None
        self._crs_widget_s1    = None
        self._btn_apply_crs    = None
        self._canvas           = None
        self._map_info_label   = None
        # Étape 2
        self._filter_bg        = None
        self._entity_table     = None
        self._entity_count_lbl = None
        self._action_bg        = None
        # Reprojection
        self._reproject_w      = None
        self._crs_widget_src   = None   # SCR d'ORIGINE (reprojection)
        self._lbl_target_crs   = None   # label SCR cible (= couche)
        # Depuis les champs
        self._fields_w         = None
        self._fields_mode_bg   = None
        self._lonlat_w         = None
        self._lon_combo        = None
        self._lat_combo        = None
        self._wkt_w            = None
        self._wkt_combo        = None
        self._chk_reproject    = None   # checkbox "Reprojeter depuis un SCR source"
        self._crs_src_fields_w = None   # widget SCR source pour les champs
        self._crs_widget_src_fields = None
        # Step-2 canvas
        self._btn_preview_s2   = None
        self._canvas_s2        = None
        self._preview_info_s2  = None
        self._apply_btn        = None
        self._result_label     = None
        # True if the last preview placed geometries outside the CRS extent;
        # the Apply button is disabled until a new valid preview is performed.
        self._preview_has_outside_crs: bool = False

        # ── Construction ──────────────────────────────────────────────────
        self.setWindowTitle(tr("GeoFixer — Correction de géométrie"))
        self.resize(1000, 720)
        self.setMinimumSize(800, 580)
        self.setWindowFlags(
            self.windowFlags() | _Qt_Window | _Qt_WindowMaximize
        )

        self._build_ui()
        # NE PAS appeler _init_with_active_layer() —
        # the combobox is intentionally empty at startup.

    # ======================================================================
    # Construction de l'interface
    # ======================================================================

    def _build_ui(self) -> None:
        """Structure globale : barre d'étapes + séparateur + QStackedWidget."""
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(10, 10, 10, 10)

        self._step_bar = self._build_step_bar()
        lay.addWidget(self._step_bar)

        line = QFrame()
        line.setFrameShape(_QFrame_HLine)
        line.setFrameShadow(_QFrame_Sunken)
        lay.addWidget(line)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        lay.addWidget(self._stack, stretch=1)

    def _build_step_bar(self) -> QWidget:
        """Barre visuelle indiquant l'étape active (vert) / inactive (gris)."""
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        self._lbl_step1 = QLabel(tr("● Étape 1 — Sélection et SCR"))
        self._lbl_step2 = QLabel(tr("● Étape 2 — Correction des entités"))
        for lbl in (self._lbl_step1, self._lbl_step2):
            f = QFont(); f.setBold(True); lbl.setFont(f)
        self._update_step_bar(1)
        lay.addWidget(self._lbl_step1)
        lay.addWidget(QLabel("→"))
        lay.addWidget(self._lbl_step2)
        lay.addStretch()
        return bar

    def _update_step_bar(self, step: int) -> None:
        self._lbl_step1.setStyleSheet(
            f"color:{_COLOR_STEP_ACTIVE if step == 1 else _COLOR_STEP_INACTIVE};"
        )
        self._lbl_step2.setStyleSheet(
            f"color:{_COLOR_STEP_ACTIVE if step == 2 else _COLOR_STEP_INACTIVE};"
        )

    # ------------------------------------------------------------------
    # Étape 1
    # ------------------------------------------------------------------

    def _build_step1(self) -> QWidget:
        """
        Page 0 : source de données, SCR, canvas de prévisualisation.

        Le canvas montre l'emprise de la couche interprétée DANS le SCR
        sélectionné (pas dans le SCR déclaré) → permet de vérifier si le
        SCR choisi est cohérent avec les coordonnées brutes.

        Le bouton tr("Appliquer le SCR") est désactivé si l'emprise de la couche
        n'est pas entièrement contenue dans les bounds du SCR (contains).
        """
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(8)
        lay.setContentsMargins(0, 4, 0, 0)

        # ── Groupe Source ────────────────────────────────────────────────
        grp_src = QGroupBox(tr("Source de données"))
        gl = QHBoxLayout(grp_src)
        gl.addWidget(QLabel(tr("Couche :")))

        try:
            from qgis.gui import QgsMapLayerComboBox
            self._layer_combo = QgsMapLayerComboBox()
            if _QMapLayerProxyModel_VectorLayer is not None:
                self._layer_combo.setFilters(_QMapLayerProxyModel_VectorLayer)
            self._layer_combo.setAllowEmptyLayer(True)
            # Block signals while clearing to prevent
            # QgsMapLayerComboBox from auto-selecting the first layer at startup
            self._layer_combo.blockSignals(True)
            self._layer_combo.setLayer(None)
            self._layer_combo.blockSignals(False)
        except Exception:
            self._layer_combo = _NoWheelCombo()

        self._layer_combo.layerChanged.connect(self._on_layer_changed)
        gl.addWidget(self._layer_combo, stretch=1)

        lbl_or = QLabel(tr("ou"))
        lbl_or.setStyleSheet("color:#888;")
        gl.addWidget(lbl_or)

        btn_open = QPushButton(tr("📁  Ouvrir un fichier…"))
        btn_open.setToolTip(tr("Ouvre un fichier vectoriel et le charge dans QGIS."))
        btn_open.clicked.connect(self._on_open_file)
        gl.addWidget(btn_open)
        lay.addWidget(grp_src)


        # Supported formats label — displayed below the data source group
        _fmt_label = QLabel(
            "<span style='color:#555;font-size:9px;'>"
            + tr("Formats : Shapefile \u00b7 GeoPackage \u00b7 GeoJSON \u00b7 KML/KMZ \u00b7 GML \u00b7 "
               "CSV/TSV \u00b7 MapInfo TAB/MIF \u00b7 GPX \u00b7 DXF \u00b7 DWG \u00b7 "
               "ESRI FileGDB \u00b7 SQLite/SpatiaLite \u00b7 .gz \u00b7 .zip")
            + "</span>"
        )
        _fmt_label.setWordWrap(True)
        lay.addWidget(_fmt_label)

        # ── Groupe SCR ───────────────────────────────────────────────────
        grp_crs = QGroupBox(tr("Système de coordonnées de référence (SCR)"))
        cl = QHBoxLayout(grp_crs)
        cl.addWidget(QLabel(tr("SCR :")))

        self._crs_widget_s1 = make_crs_selector()
        self._crs_widget_s1.crsChanged.connect(self._on_s1_crs_changed)
        cl.addWidget(self._crs_widget_s1, stretch=1)

        self._btn_apply_crs = QPushButton(tr("Appliquer le SCR"))
        self._btn_apply_crs.setToolTip(
            "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
            "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi."
        )
        self._btn_apply_crs.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;padding:4px 12px;border-radius:3px;}"
            "QPushButton:hover{background:#3498db;}"
            "QPushButton:disabled{background:#bdc3c7;color:#888;}"
        )
        self._btn_apply_crs.setEnabled(False)
        self._btn_apply_crs.clicked.connect(self._on_apply_crs)
        cl.addWidget(self._btn_apply_crs)
        lay.addWidget(grp_crs)

        # ── Canvas ───────────────────────────────────────────────────────
        self._canvas = make_map_canvas(min_height=280)
        if self._canvas:
            lay.addWidget(self._canvas, stretch=1)
        else:
            lay.addWidget(QLabel(tr("(Canvas non disponible)")), stretch=1)

        self._map_info_label = QLabel("")
        self._map_info_label.setStyleSheet(f"color:{_COLOR_INFO};font-size:10px;")
        self._map_info_label.setWordWrap(True)
        lay.addWidget(self._map_info_label)

        # ── Navigation ────────────────────────────────────────────────────
        nav = QHBoxLayout()
        nav.addStretch()
        btn_next = QPushButton(tr("Étape suivante  →"))
        btn_next.setStyleSheet(
            "QPushButton{background:#27ae60;color:white;"
            "padding:6px 18px;border-radius:3px;font-weight:bold;}"
            "QPushButton:hover{background:#2ecc71;}"
        )
        btn_next.clicked.connect(self._go_to_step2)
        nav.addWidget(btn_next)
        lay.addLayout(nav)
        return page

    # ------------------------------------------------------------------
    # Étape 2
    # ------------------------------------------------------------------

    def _build_step2(self) -> QWidget:
        """
        Page 1 : tableau des entités, actions, prévisualisation.

        Reprojection : l'utilisateur renseigne le SCR D'ORIGINE des entités
        mal projetées. La cible est automatiquement le SCR de la couche défini
        à l'étape 1.

        Depuis les champs : lon/lat ou WKT + sélecteur "SCR source" optionnel
        pour reprojeter vers le SCR couche après reconstruction.
        """
        page  = QWidget()
        outer = QVBoxLayout(page)
        outer.setSpacing(6)
        outer.setContentsMargins(0, 4, 0, 0)

        # Splitter vertical : tableau (haut) / zone basse (bas)
        # The bottom area is itself split by a horizontal QSplitter:
        #   left = action parameters  |  right = preview canvas
        splitter = QSplitter(_Qt_Vertical)

        # ── Haut : tableau ────────────────────────────────────────────────
        top_w = QWidget()
        tl = QVBoxLayout(top_w)
        tl.setContentsMargins(0, 0, 0, 0)

        grp_ent = QGroupBox(tr("Entités à corriger"))
        el = QVBoxLayout(grp_ent)

        filter_row = QHBoxLayout()
        self._filter_bg = QButtonGroup(page)
        rb_prob = QRadioButton(tr("Entités sans géométrie ou hors emprise SCR"))
        rb_all  = QRadioButton(tr("Toutes les entités"))
        rb_prob.setChecked(True)
        self._filter_bg.addButton(rb_prob, 0)
        self._filter_bg.addButton(rb_all,  1)
        self._filter_bg.idClicked.connect(self._on_filter_changed)
        filter_row.addWidget(rb_prob)
        filter_row.addSpacing(20)
        filter_row.addWidget(rb_all)
        filter_row.addStretch()
        el.addLayout(filter_row)

        self._entity_table = QTableWidget()
        self._entity_table.setMinimumHeight(140)
        self._entity_table.setAlternatingRowColors(True)
        self._entity_table.setSelectionMode(_QTable_ExtendedSelection)
        self._entity_table.setSelectionBehavior(_QTable_SelectRows)
        self._entity_table.setEditTriggers(_QTable_NoEditTriggers)
        self._entity_table.verticalHeader().setDefaultSectionSize(22)
        self._entity_table.verticalHeader().setVisible(False)
        # Sort by clicking the column header
        self._entity_table.setSortingEnabled(True)
        self._entity_table.horizontalHeader().setSortIndicatorShown(True)
        self._entity_table.itemSelectionChanged.connect(self._on_selection_changed)
        el.addWidget(self._entity_table, stretch=1)

        sel_row = QHBoxLayout()
        btn_all  = QPushButton(tr("Tout sélectionner"))
        btn_none = QPushButton(tr("Désélectionner"))
        btn_all.clicked.connect(self._entity_table.selectAll)
        btn_none.clicked.connect(self._entity_table.clearSelection)
        self._entity_count_lbl = QLabel(tr("Aucune entité chargée."))
        self._entity_count_lbl.setStyleSheet(f"color:{_COLOR_INFO};font-size:10px;")
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        sel_row.addWidget(self._entity_count_lbl)
        el.addLayout(sel_row)

        tl.addWidget(grp_ent, stretch=1)
        splitter.addWidget(top_w)

        # ── Bas : splitter horizontal gauche (params) / droite (canvas) ──
        h_splitter = QSplitter()  # horizontal orientation by default
        try:
            from qgis.PyQt.QtCore import Qt as _Qt2
            h_splitter.setOrientation(_Qt2.Orientation.Horizontal)
        except AttributeError:
            pass   # Qt5: horizontal is already the default

        # Left panel: action parameters
        left_w = QWidget()
        bl = QVBoxLayout(left_w)
        bl.setContentsMargins(0, 4, 4, 0)
        bl.setSpacing(6)

        grp_action = QGroupBox(tr("Action à appliquer sur la sélection"))
        al = QVBoxLayout(grp_action)
        al.setSpacing(6)
        self._action_bg = QButtonGroup(page)

        # ── Option 1 : Reprojeter depuis un SCR d'origine ─────────────
        rb_repr = QRadioButton(
            tr("Reprojeter — les entités sont dans un SCR différent de la couche")
        )
        self._action_bg.addButton(rb_repr, 0)
        al.addWidget(rb_repr)

        self._reproject_w = QWidget()
        rw = QVBoxLayout(self._reproject_w)
        rw.setContentsMargins(20, 2, 0, 2)
        rw.setSpacing(4)

        row_src = QHBoxLayout()
        row_src.addWidget(QLabel(tr("SCR d'origine des entités :")))
        self._crs_widget_src = make_crs_selector()
        row_src.addWidget(self._crs_widget_src, stretch=1)
        rw.addLayout(row_src)

        self._lbl_target_crs = QLabel("")
        self._lbl_target_crs.setStyleSheet(f"color:{_COLOR_INFO};font-size:10px;")
        rw.addWidget(self._lbl_target_crs)

        self._reproject_w.setVisible(False)
        al.addWidget(self._reproject_w)

        # ── Option 2: Define from fields ──────────────────────────────
        rb_fields = QRadioButton(
            tr("Définir la géométrie depuis des champs attributaires")
        )
        self._action_bg.addButton(rb_fields, 1)
        al.addWidget(rb_fields)

        self._fields_w = QWidget()
        fw = QVBoxLayout(self._fields_w)
        fw.setContentsMargins(20, 2, 0, 2)
        fw.setSpacing(4)
        self._fields_mode_bg = QButtonGroup(page)

        # Sous-option Lon/Lat
        rb_ll = QRadioButton(tr("Longitude / Latitude  →  Point"))
        self._fields_mode_bg.addButton(rb_ll, 0)
        rb_ll.setChecked(True)
        fw.addWidget(rb_ll)

        self._lonlat_w = QWidget()
        lw = QHBoxLayout(self._lonlat_w)
        lw.setContentsMargins(20, 0, 0, 0)
        lw.setSpacing(8)
        lw.addWidget(QLabel(tr("Longitude :")))
        self._lon_combo = _NoWheelCombo()
        lw.addWidget(self._lon_combo)
        lw.addWidget(QLabel(tr("Latitude :")))
        self._lat_combo = _NoWheelCombo()
        lw.addWidget(self._lat_combo)
        lw.addStretch()
        fw.addWidget(self._lonlat_w)

        # Sous-option WKT
        rb_wkt = QRadioButton(tr("Champ WKT (Well-Known Text)"))
        self._fields_mode_bg.addButton(rb_wkt, 1)
        fw.addWidget(rb_wkt)

        self._wkt_w = QWidget()
        ww = QHBoxLayout(self._wkt_w)
        ww.setContentsMargins(20, 0, 0, 0)
        ww.setSpacing(8)
        ww.addWidget(QLabel(tr("Champ WKT :")))
        self._wkt_combo = _NoWheelCombo()
        ww.addWidget(self._wkt_combo)
        ww.addStretch()
        self._wkt_w.setVisible(False)
        fw.addWidget(self._wkt_w)

        # ── Reprojection optionnelle depuis les champs ────────────────
        self._chk_reproject = QCheckBox(
            tr("Reprojeter les coordonnées vers le SCR de la couche")
        )
        self._chk_reproject.setToolTip(
            "Si les coordonnées dans les champs sont dans un SCR différent\n"
            "de la couche, cochez cette case et indiquez le SCR source."
        )
        self._chk_reproject.toggled.connect(self._on_chk_reproject_toggled)
        fw.addWidget(self._chk_reproject)

        self._crs_src_fields_w = QWidget()
        cfw = QHBoxLayout(self._crs_src_fields_w)
        cfw.setContentsMargins(20, 0, 0, 0)
        cfw.addWidget(QLabel(tr("SCR source des coordonnées :")))
        self._crs_widget_src_fields = make_crs_selector()
        cfw.addWidget(self._crs_widget_src_fields, stretch=1)
        self._crs_src_fields_w.setVisible(False)
        fw.addWidget(self._crs_src_fields_w)

        self._fields_w.setVisible(False)
        al.addWidget(self._fields_w)

        bl.addWidget(grp_action)

        self._action_bg.idClicked.connect(self._on_action_mode_changed)
        self._fields_mode_bg.idClicked.connect(self._on_fields_mode_changed)

        # ── Preview button (bottom of left panel) ──────────────────────
        self._btn_preview_s2 = QPushButton(tr("🔍  Prévisualiser la transformation"))
        self._btn_preview_s2.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;"
            "padding:4px 14px;border-radius:3px;}"
            "QPushButton:hover{background:#9b59b6;}"
        )
        self._btn_preview_s2.clicked.connect(self._run_step2_preview)
        bl.addWidget(self._btn_preview_s2)

        # Result label (after applying corrections) — left panel
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet(f"color:{_COLOR_INFO};font-size:10px;")
        bl.addWidget(self._result_label)

        bl.addStretch()   # pousse les widgets vers le haut
        h_splitter.addWidget(left_w)

        # Partie droite : canvas + message d'info
        right_w = QWidget()
        rl = QVBoxLayout(right_w)
        rl.setContentsMargins(4, 4, 0, 0)
        rl.setSpacing(4)

        self._canvas_s2 = make_map_canvas(min_height=200, min_width=300)
        if self._canvas_s2:
            self._canvas_s2.setVisible(False)
            rl.addWidget(self._canvas_s2, stretch=1)

        self._preview_info_s2 = QLabel("")
        self._preview_info_s2.setWordWrap(True)
        self._preview_info_s2.setStyleSheet(f"color:{_COLOR_INFO};font-size:10px;")
        rl.addWidget(self._preview_info_s2)

        h_splitter.addWidget(right_w)
        h_splitter.setSizes([420, 380])

        # The h_splitter forms the bottom half of the vertical splitter
        splitter.addWidget(h_splitter)
        splitter.setSizes([280, 340])
        outer.addWidget(splitter, stretch=1)

        # ── Navigation ────────────────────────────────────────────────────
        nav = QHBoxLayout()
        btn_back = QPushButton(tr("←  Retour"))
        btn_back.clicked.connect(self._go_to_step1)
        nav.addWidget(btn_back)
        nav.addStretch()
        self._apply_btn = QPushButton(tr("Appliquer les corrections"))
        self._apply_btn.setStyleSheet(
            "QPushButton{background:#e67e22;color:white;"
            "padding:6px 18px;border-radius:3px;font-weight:bold;}"
            "QPushButton:hover{background:#f39c12;}"
            "QPushButton:disabled{background:#bdc3c7;color:#888;}"
        )
        self._apply_btn.clicked.connect(self._on_apply_fixes)
        nav.addWidget(self._apply_btn)
        outer.addLayout(nav)

        return page

    # ======================================================================
    # Handlers — Étape 1
    # ======================================================================

    def _on_layer_changed(self, layer) -> None:
        """
        Appelé quand l'utilisateur change de couche.
        Synchronise le SCR et rafraîchit le canvas.
        """
        self._current_layer = layer

        if layer is None:
            self._set_map_info("", _COLOR_INFO)
            if self._canvas:
                self._canvas.setLayers([])
                self._canvas.refresh()
            if self._btn_apply_crs is not None:
                self._btn_apply_crs.setEnabled(False)
            self._cached_data_extent_wgs = None
            return

        try:
            lyr_crs = layer.crs()
            if lyr_crs.isValid() and self._crs_widget_s1 is not None:
                self._crs_widget_s1.setCrs(lyr_crs)
            self._applied_crs = lyr_crs if lyr_crs.isValid() else None
        except Exception:
            pass

        QTimer.singleShot(80, self._refresh_map_preview)
        # If the layer has no geometry, open the configuration dialog
        # immediately (120 ms delay so the map is rendered first)
        QTimer.singleShot(120, lambda: self._open_field_config_if_needed(layer))

    def _on_s1_crs_changed(self, _crs=None) -> None:
        """Rafraîchit le canvas quand le SCR change dans le sélecteur."""
        QTimer.singleShot(80, self._refresh_map_preview)

    # Formats pouvant contenir plusieurs couches vectorielles
    _MULTILAYER_EXTS = frozenset([
        '.gpkg', '.gdb', '.kml', '.kmz', '.dwg', '.dxf',
        '.gml', '.gpx', '.sqlite', '.db', '.gz', '.zip',
    ])

    def _on_open_file(self) -> None:
        """
        Ouvre un fichier vectoriel et le charge dans QGIS.

        Pour les formats multi-couches (GPKG, GDB, KML, KMZ, DWG, DXF…),
        une boîte de dialogue liste les couches disponibles et demande à
        l'utilisateur laquelle il souhaite traiter.

        La couche chargée est ajoutée au projet QGIS et sélectionnée dans
        le combobox de l'étape 1.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("Ouvrir un fichier vectoriel"), "", _FILE_FILTER
        )
        if not file_path:
            return

        import os
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ext       = os.path.splitext(file_path)[1].lower()

        try:
            from qgis.core import QgsVectorLayer, QgsProject

            # ── CSV: detect delimiter then build the URI ────────────────────
            if ext == '.csv':
                delimiter = _detect_csv_delimiter(file_path)

                # QGIS delimitedtext provider expects the LITERAL character
                # in the URI — NOT URL-encoded (quote(';') = '%3B' would be wrong).
                #   ';'  → delimiter=;
                #   '\t' → delimiter=\t  (two characters \ and t, not a real tab)
                #   ','  → delimiter=,
                if delimiter == '\t':
                    delim_str = "\t"   # QGIS interprets the literal \t as a tab character
                else:
                    delim_str = delimiter   # pass the character as-is

                uri = (
                    f"file:///{file_path}"
                    f"?delimiter={delim_str}"
                    f"&detectTypes=yes"
                    f"&useHeader=yes"
                )
                layer = QgsVectorLayer(uri, base_name, "delimitedtext")

                # Check: if only one column detected → wrong delimiter
                if not layer.isValid() or layer.fields().count() <= 1:
                    # Fallback: URI without forcing delimiter (let QGIS auto-detect)
                    uri_fallback = f"file:///{file_path}?detectTypes=yes&useHeader=yes"
                    layer_fb = QgsVectorLayer(uri_fallback, base_name, "delimitedtext")
                    if layer_fb.isValid() and layer_fb.fields().count() > 1:
                        layer = layer_fb
                    elif not layer.isValid():
                        QMessageBox.warning(self, "GeoFixer",
                                            f"Impossible de charger :\n{file_path}")
                        return

                QgsProject.instance().addMapLayer(layer)
                if hasattr(self._layer_combo, 'setLayer'):
                    self._layer_combo.setLayer(layer)
                return

            # ── Formats potentiellement multi-couches ────────────────────────
            if ext in self._MULTILAYER_EXTS:
                # Interroger OGR pour obtenir la liste des sous-couches
                probe = QgsVectorLayer(file_path, "__probe__", "ogr")
                sublayers = probe.dataProvider().subLayers() if probe.isValid() else []
                # OGR sublayer entry format:
                #   "index!!::!!name!!::!!feature_count!!::!!geom_type!!::!!…"
                # Extract the name (field 2) and geometry type (field 4)
                parsed = []
                for sl in sublayers:
                    parts = sl.split("!!::!!")
                    if len(parts) >= 4:
                        parsed.append({
                            "name":  parts[1],
                            "count": parts[2],
                            "geom":  parts[3],
                        })

                if len(parsed) > 1:
                    # Multiple layers → ask the user to choose
                    chosen_name = self._ask_layer_choice(parsed, file_path)
                    if chosen_name is None:
                        return   # Cancelled
                    uri   = f"{file_path}|layername={chosen_name}"
                    layer = QgsVectorLayer(uri, chosen_name, "ogr")
                elif len(parsed) == 1:
                    # Une seule couche → charger directement
                    uri   = f"{file_path}|layername={parsed[0]['name']}"
                    layer = QgsVectorLayer(uri, parsed[0]['name'], "ogr")
                else:
                    # Pas de sublayers (format ne les expose pas) → URI directe
                    layer = QgsVectorLayer(file_path, base_name, "ogr")
            else:
                # Format mono-couche standard
                layer = QgsVectorLayer(file_path, base_name, "ogr")

            if not layer.isValid():
                QMessageBox.warning(self, "GeoFixer",
                                    f"Impossible de charger :\n{file_path}\n\n"
                                    "Vérifiez que le format est supporté par QGIS.")
                return

            QgsProject.instance().addMapLayer(layer)
            if hasattr(self._layer_combo, 'setLayer'):
                self._layer_combo.setLayer(layer)

        except Exception as exc:
            QMessageBox.critical(self, tr("GeoFixer — Erreur"),
                                 f"Erreur lors du chargement :\n{exc}")

    def _ask_layer_choice(self, layers: list, file_path: str) -> "Optional[str]":
        """
        Affiche une boîte de dialogue listant les couches d'un fichier multi-couches.

        :param layers:    Liste de dict {name, count, geom} issus des sublayers OGR
        :param file_path: Chemin du fichier (affiché dans le titre)
        :return:          Nom de la couche choisie, ou None si annulé
        """
        import os
        from qgis.PyQt.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
            QListWidgetItem, QDialogButtonBox, QLabel,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Sélection de couche"))
        dlg.setMinimumWidth(480)
        lay = QVBoxLayout(dlg)

        lbl = QLabel(
            f"Le fichier <b>{os.path.basename(file_path)}</b> contient "
            f"{len(layers)} couche(s).<br>Sélectionnez la couche à traiter :"
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        lst = QListWidget()
        for info in layers:
            count_txt = f"  ({info['count']} entités)" if info['count'].isdigit() else ""
            geom_txt  = f"  [{info['geom']}]" if info['geom'] else ""
            item = QListWidgetItem(f"{info['name']}{count_txt}{geom_txt}")
            item.setData(_Qt_UserRole, info['name'])
            lst.addItem(item)
        lst.setCurrentRow(0)
        lay.addWidget(lst)

        try:
            _Btn_Ok     = QDialogButtonBox.StandardButton.Ok
            _Btn_Cancel = QDialogButtonBox.StandardButton.Cancel
        except AttributeError:
            _Btn_Ok     = QDialogButtonBox.Ok      # type: ignore
            _Btn_Cancel = QDialogButtonBox.Cancel  # type: ignore

        btns = QDialogButtonBox(_Btn_Ok | _Btn_Cancel, parent=dlg)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        # exec() retourne 1 (Accepted) ou 0 (Rejected) dans Qt5 et Qt6 —
        # compare directly to the integer to avoid attribute resolution issues.
        if not dlg.exec():
            return None

        selected = lst.currentItem()
        return selected.data(_Qt_UserRole) if selected else None

    def _open_field_config_if_needed(self, layer) -> None:
        """
        Ouvre automatiquement FieldConfigDialog si la couche n'a pas de géométrie.

        Appelé 120 ms après le chargement d'une couche (délai pour que le canvas
        soit rendu avant l'ouverture du dialogue).

        Si l'utilisateur choisit un mode géométrique et valide, _export_to_shapefile
        est appelé. Si le dialogue est annulé ou si "Aucune géométrie" est choisi,
        la couche reste telle quelle — l'utilisateur peut reprendre plus tard.
        """
        if layer is None or layer != self._current_layer:
            return   # Layer has changed since the timer was scheduled
        try:
            from qgis.core import QgsWkbTypes
            wkb = layer.wkbType()
            is_no_geom = (
                QgsWkbTypes.geometryType(wkb) == QgsWkbTypes.NullGeometry
                or wkb == QgsWkbTypes.NoGeometry
                or (wkb == QgsWkbTypes.Unknown and layer.extent().isNull())
            )
        except Exception:
            is_no_geom = False

        if not is_no_geom:
            return

        # Informer l'utilisateur avant d'ouvrir le dialogue
        QMessageBox.information(
            self, tr("GeoFixer — Couche sans géométrie"),
            f"La couche « {layer.name()} » ne possède aucune géométrie.\n\n"
            "La fenêtre de configuration des champs va s'ouvrir. "
            "Définissez les types de champs et le mode géométrique "
            "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
            "Un Shapefile sera créé avec les géométries construites depuis les champs \u2014 "
            "vous pourrez corriger les éventuelles géométries manquantes à l'\u00e9tape 2."
        )
        self._export_to_shapefile()

    def _on_apply_crs(self) -> None:
        """Applique le SCR sélectionné à la couche (déclaration sans reprojection)."""
        if self._current_layer is None:
            QMessageBox.warning(self, tr("GeoFixer"), tr("Aucune couche sélectionnée."))
            return
        crs = self._get_s1_crs()
        if crs is None or not crs.isValid():
            QMessageBox.warning(self, "GeoFixer", "SCR invalide.")
            return
        error = apply_crs_to_layer(self._current_layer, crs)
        if error:
            QMessageBox.critical(self, tr("GeoFixer — Erreur"), error)
            return
        self._applied_crs = crs
        self._set_map_info(
            f"✔ SCR {crs.authid()} appliqué à la couche « {self._current_layer.name()} ».",
            _COLOR_SUCCESS,
        )
        QTimer.singleShot(80, self._refresh_map_preview)

    def _go_to_step2(self) -> None:
        """
        Passe à l'étape 2 après validation.

        Si la couche est sans géométrie (wkbType == NoGeometry), l'export
        Shapefile est OBLIGATOIRE avant de pouvoir continuer. L'utilisateur
        ne peut pas passer à l'étape 2 sans avoir créé ce fichier, car aucun
        format sans géométrie ne supporte l'édition de géométrie en place.
        """
        if self._current_layer is None:
            QMessageBox.warning(
                self, "GeoFixer",
                "Veuillez sélectionner ou ouvrir une couche avant de continuer."
            )
            return

        # ── Detect layers that are entirely without geometry ─────────────
        try:
            from qgis.core import QgsWkbTypes
            wkb = self._current_layer.wkbType()
            is_no_geom = (
                QgsWkbTypes.geometryType(wkb) == QgsWkbTypes.NullGeometry
                or wkb == QgsWkbTypes.NoGeometry
                or (wkb == QgsWkbTypes.Unknown
                    and self._current_layer.extent().isNull())
            )
        except Exception:
            is_no_geom = False

        if is_no_geom:
            # Ouvrir le dialogue de configuration des champs.
            # If the user chooses "No geometry" (mode 0), block
            # navigation to step 2 and inform that CRS + fields are required.
            # If a geometry mode is chosen and previewed, create the SHP.
            self._export_to_shapefile()
            return   # User must click "Next step" again after the SHP has been created

        self._stack.setCurrentIndex(1)
        self._update_step_bar(2)
        self._detect_and_populate_fields()
        self._populate_entity_table()
        self._update_target_crs_label()

    def _export_to_shapefile(self) -> None:
        """
        Crée un Shapefile à partir d'une couche sans géométrie.

        Le type géométrique (Point, LineString, Polygon) est déterminé
        par le mode choisi dans FieldConfigDialog (lon/lat → Point,
        WKT → type détecté depuis les valeurs du champ).

        Étapes :
          1. FieldConfigDialog : configurer les types de champs.
          2. QFileDialog : choisir l'emplacement du fichier.
          3. Créer une couche mémoire Point avec les champs configurés.
          4. Copier les entités (géométries nulles, attributs convertis).
          5. Écrire la couche mémoire en Shapefile (writeAsVectorFormatV3).
          6. Charger le Shapefile dans le projet et le sélectionner.

        Pourquoi pas writeAsVectorFormatV3 directement sur la couche source ?
          Le format Shapefile exige un type géométrique explicite. Exporter
          une couche NoGeometry produit un .shp invalide (OGR refuse). On
          passe par une couche mémoire Point intermédiaire.
        """
        if self._current_layer is None:
            return

        # ── 1. Configurer les types de champs ─────────────────────────────
        field_dlg = FieldConfigDialog(self._current_layer, parent=self)
        _accepted = _QDialog_Accepted
        if field_dlg.exec() != _accepted:
            return
        type_map = field_dlg.get_field_types()

        # Verify that the user has defined a geometry mode (lon/lat or WKT).
        # If "No geometry" (mode 0) → no Shapefile, no step 2.
        geom_mode = (field_dlg._geom_bg.checkedId()
                     if field_dlg._geom_bg is not None else 0)
        if geom_mode == 0:
            QMessageBox.information(
                self, tr("GeoFixer — Géométrie requise"),
                "Aucune géométrie n'a été définie dans l'onglet « SCR et aperçu »."
                "\n\nPour créer le Shapefile, vous devez sélectionner le mode "
                "« Longitude / Latitude → Point » ou « Champ WKT », configurer "
                "les champs et prévisualiser pour valider le SCR."
            )
            return

        # Retrieve the CRS validated by the preview
        user_crs = field_dlg.get_crs()

        # Retrieve the coordinate fields chosen in FieldConfigDialog
        # (used to populate geometries at Shapefile creation time)
        _lon_field = (field_dlg._lon_combo.currentText()
                      if field_dlg._lon_combo else "")
        _lat_field = (field_dlg._lat_combo.currentText()
                      if field_dlg._lat_combo else "")
        _wkt_field = (field_dlg._wkt_combo.currentText()
                      if field_dlg._wkt_combo else "")

        # ── 2. Choisir l'emplacement du fichier ───────────────────────────
        import os as _os
        from qgis.PyQt.QtWidgets import QFileDialog as _QFD

        # Default directory: the source file's directory (if known)
        _src_dir = ""
        try:
            _src_path = self._current_layer.source()
            # Nettoyer l'URI pour obtenir le chemin pur (CSV, OGR, etc.)
            if "?" in _src_path:
                _src_path = _src_path.split("?")[0]
            if _src_path.startswith("file:///"):
                _src_path = _src_path[8:]
            if _os.path.exists(_src_path):
                _src_dir = _os.path.dirname(_src_path)
        except Exception:
            pass

        # Nettoyer le nom de la couche pour en faire un nom de fichier valide :
        # strip suffixes added automatically (e.g. "[SHP]", "[CSV]")
        import re as _re
        _clean_name = _re.sub(r"\s*\[.*?\]\s*$", "", self._current_layer.name()).strip()
        _clean_name = _re.sub(r'[\\/:*?"<>|]', "_", _clean_name)  # characters forbidden on Windows
        if not _clean_name:
            _clean_name = "export"

        if _src_dir:
            _default_name = _os.path.join(_src_dir, _clean_name + ".shp")
        else:
            _default_name = _clean_name + ".shp"

        save_path, _ = _QFD.getSaveFileName(
            self,
            tr("Enregistrer la copie Shapefile"),
            _default_name,
            "Shapefile (*.shp)",
        )
        if not save_path:
            return

        # Normalise the path (Windows separators → universal slashes for GDAL)
        # and ensure the .shp extension is present
        save_path = _os.path.normpath(save_path)
        if not save_path.lower().endswith(".shp"):
            save_path += ".shp"

        # ── Verify that the Shapefile components are not locked ─────────
        # A Shapefile consists of several files (.shp, .dbf, .shx...).
        # GDAL may fail if any of them is locked. Check all
        # existing associated files before starting the export.
        _base_path = _os.path.splitext(save_path)[0]
        for _ext_to_check in (".shp", ".dbf", ".shx", ".prj", ".cpg"):
            _candidate = _base_path + _ext_to_check
            if _os.path.exists(_candidate):
                try:
                    with open(_candidate, "r+b"):
                        pass
                except PermissionError:
                    QMessageBox.critical(
                        self, tr("GeoFixer — Fichier verrouillé"),
                        f"Le fichier {_ext_to_check} est en cours d'utilisation "
                        f"par un autre logiciel :\n{_candidate}\n\n"
                        "Fermez le fichier dans l'autre application puis réessayez."
                    )
                    return

        try:
            from qgis.core import (
                QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                QgsVectorFileWriter, QgsProject,
                QgsCoordinateTransformContext,
            )
            from qgis.PyQt.QtCore import QVariant

            # ── 3. Build the memory layer ────────────────────────────────
            # Memory layer CRS: priority to the CRS chosen in the dialog,
            # then the CRS declared on the source layer, then EPSG:4326 as default.
            src_crs = self._current_layer.crs()
            if user_crs is not None and user_crs.isValid():
                crs_str = user_crs.authid()
            elif src_crs.isValid():
                crs_str = src_crs.authid()
            else:
                crs_str = "EPSG:4326"

            # The memory layer geometry type depends on the chosen mode:
            # mode 1 (lon/lat) → Point, mode 2 (WKT) → type detected from field values
            if geom_mode == 2 and _wkt_field:
                from qgis.core import QgsFeatureRequest as _QFR2
                _detected_wkb_type = "Point"   # repli
                _WKT_TYPE_MAP = {
                    "POINT": "Point", "MULTIPOINT": "MultiPoint",
                    "LINESTRING": "LineString", "MULTILINESTRING": "MultiLineString",
                    "POLYGON": "Polygon", "MULTIPOLYGON": "MultiPolygon",
                    "GEOMETRYCOLLECTION": "GeometryCollection",
                }
                for _f2 in self._current_layer.getFeatures(
                        _QFR2().setLimit(20)):
                    _raw2 = _f2[_wkt_field]
                    if _raw2:
                        _kw2 = str(_raw2).strip().upper().split("(", 1)[0].strip()
                        if _kw2 in _WKT_TYPE_MAP:
                            _detected_wkb_type = _WKT_TYPE_MAP[_kw2]
                            break
                mem_geom_type = _detected_wkb_type
            else:
                mem_geom_type = "Point"

            mem_layer = QgsVectorLayer(
                f"{mem_geom_type}?crs={crs_str}", "__tmp__", "memory"
            )
            if not mem_layer.isValid():
                raise RuntimeError("Impossible de créer la couche mémoire.")

            _qv = {
                "Integer": QVariant.Int,
                "Real":    QVariant.Double,
                "Date":    QVariant.Date,
                "String":  QVariant.String,
            }
            mem_layer.dataProvider().addAttributes([
                QgsField(f.name(), _qv.get(type_map.get(f.name(), "String"),
                                           QVariant.String))
                for f in self._current_layer.fields()
            ])
            mem_layer.updateFields()

            # ── 4. Copy features with geometries built from fields ────────────
            # Geometries are built immediately from the lon/lat
            # or WKT fields — no need to defer to step 2.
            # If a value is missing/invalid, the geometry stays null
            # for that feature only.
            from qgis.core import QgsPointXY
            # Coordinates in the fields are already in the CRS selected
            # by the user (visible in the "CRS and preview" tab).
            # The memory layer uses the same CRS → no transformation needed.
            # Creating QgsPointXY(x, y) directly is sufficient and correct.

            mem_layer.startEditing()
            n_geom_ok  = 0
            n_geom_err = 0
            for feat in self._current_layer.getFeatures():
                nf = QgsFeature(mem_layer.fields())

                # ── Build geometry from the fields ─────────────────────
                geom_built = QgsGeometry()
                if geom_mode == 1 and _lon_field and _lat_field:
                    try:
                        rx = feat[_lon_field]; ry = feat[_lat_field]
                        if rx is not None and ry is not None:
                            x = float(str(rx).replace(",", "."))
                            y = float(str(ry).replace(",", "."))
                            if x == x and y == y:   # pas NaN
                                geom_built = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                                n_geom_ok += 1
                            else:
                                n_geom_err += 1
                        else:
                            n_geom_err += 1
                    except Exception:
                        n_geom_err += 1
                elif geom_mode == 2 and _wkt_field:
                    try:
                        raw_wkt = feat[_wkt_field]
                        if raw_wkt and str(raw_wkt).strip():
                            g = QgsGeometry.fromWkt(str(raw_wkt).strip())
                            if g and not g.isNull():
                                geom_built = g
                                n_geom_ok += 1
                            else:
                                n_geom_err += 1
                        else:
                            n_geom_err += 1
                    except Exception:
                        n_geom_err += 1

                nf.setGeometry(geom_built)

                for field in self._current_layer.fields():
                    fname  = field.name()
                    raw    = feat[fname]
                    target = type_map.get(fname, "String")
                    is_null = (raw is None or (
                        hasattr(raw, "__class__")
                        and raw.__class__.__name__ == "QPyNullVariant"
                    ))
                    if is_null:
                        nf[fname] = None
                    else:
                        try:
                            if target == "Integer":
                                nf[fname] = int(float(str(raw)))
                            elif target == "Real":
                                nf[fname] = float(str(raw).replace(",", "."))
                            else:
                                nf[fname] = str(raw)
                        except (ValueError, TypeError):
                            nf[fname] = str(raw)
                mem_layer.dataProvider().addFeature(nf)
            mem_layer.commitChanges()
            mem_layer.updateExtents()

            logger.info(
                "GeoFixer export SHP : %d géométries construites, %d entités sans valeur.",
                n_geom_ok, n_geom_err
            )

            # ── 5. Écrire en Shapefile ─────────────────────────────────────
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName   = "ESRI Shapefile"
            options.fileEncoding = "UTF-8"

            result     = QgsVectorFileWriter.writeAsVectorFormatV3(
                mem_layer, save_path,
                QgsCoordinateTransformContext(), options,
            )
            error_code = result[0]
            error_msg  = result[1] if len(result) > 1 else ""

            if error_code != QgsVectorFileWriter.NoError:
                QMessageBox.critical(
                    self, tr("GeoFixer — Erreur export"),
                    f"L'export a échoué :\n{error_msg}"
                )
                return

            # ── 6. Load and select the Shapefile ──────────────────────
            new_layer = QgsVectorLayer(
                save_path,
                self._current_layer.name() + " [SHP]",
                "ogr"
            )
            if not new_layer.isValid():
                QMessageBox.critical(
                    self, tr("GeoFixer — Erreur"),
                    f"Shapefile créé mais impossible à charger :\n{save_path}"
                )
                return

            # Remove the source layer (no geometry) from the project.
            # IMPORTANT: update self._current_layer to new_layer BEFORE
            # calling removeMapLayer, so any subsequent code that accesses
            # self._current_layer finds a valid object, not a deleted one.
            source_layer_id = self._current_layer.id()
            QgsProject.instance().addMapLayer(new_layer)
            self._current_layer = new_layer
            QgsProject.instance().removeMapLayer(source_layer_id)
            if hasattr(self._layer_combo, "setLayer"):
                self._layer_combo.setLayer(new_layer)

            # Explicitly sync the CRS selector to the new layer's CRS.
            # Cannot rely on _on_layer_changed firing at the right time because
            # removeMapLayer may trigger a spurious layerChanged signal first.
            new_crs = new_layer.crs()
            if new_crs.isValid() and self._crs_widget_s1 is not None:
                self._crs_widget_s1.setCrs(new_crs)
            self._applied_crs = new_crs if new_crs.isValid() else None

            # Store the extent computed from fields (the Shapefile geometries
            # are NULL at this point, so layer.extent() would be empty).
            # This lets the step-1 canvas display the purple extent rectangle.
            self._cached_data_extent_wgs = field_dlg.get_data_extent_wgs84()

            n_total    = new_layer.featureCount()
            _geom_info = (
                f"{n_geom_ok} géométrie(s) construite(s)"
                + (f", {n_geom_err} entité(s) sans coordonnées valides" if n_geom_err else "")
            ) if geom_mode != 0 else "aucune géométrie"
            QMessageBox.information(
                self, tr("GeoFixer — Shapefile créé"),
                f"Shapefile créé et chargé :\n{save_path}\n"
                f"{n_total} entité(s) exportée(s) — {_geom_info}.\n\n"
                + ("Cliquez sur « Étape suivante » pour vérifier les géométries."
                   if n_geom_err == 0
                   else "Attention : certaines entités sont sans géométrie"
                        " (coordonnées manquantes). Passez à l'étape 2 pour les corriger.")
            )

            # Refresh the step-1 canvas now that the new layer is in place.
            # Use a short delay so Qt finishes processing the dialog close first.
            QTimer.singleShot(80, self._refresh_map_preview)

        except Exception as exc:
            logger.exception("GeoFixer : erreur export Shapefile.")
            QMessageBox.critical(
                self, tr("GeoFixer — Erreur"),
                f"Erreur lors de la création du Shapefile :\n{exc}"
            )

    def _refresh_map_preview(self) -> None:
        """
        Rafraîchit le canvas de l'étape 1.

        L'emprise de la couche est calculée en INTERPRÉTANT les coordonnées
        brutes DANS le SCR sélectionné (pas dans le SCR déclaré).

        Le bouton tr("Appliquer le SCR") est activé uniquement si l'emprise de la
        couche est ENTIÈREMENT contenue dans les bounds du SCR (contains).
        Cela garantit qu'une couche en Lambert II interprétée en WGS84 (dont
        les coordonnées dépassent largement [-180,180]) est bien rejetée.
        """
        if self._canvas is None:
            return

        try:
            from qgis.core import (
                QgsCoordinateReferenceSystem, QgsVectorLayer,
                QgsFeature, QgsGeometry, QgsRectangle,
                QgsSingleSymbolRenderer, QgsFillSymbol,
                QgsCoordinateTransform, QgsProject,
            )

            crs_wgs84   = QgsCoordinateReferenceSystem("EPSG:4326")
            crs_display = self._get_s1_crs() or crs_wgs84
            crs_bounds  = crs_display.bounds()
            has_crs_bounds = not crs_bounds.isNull() and crs_bounds.width() > 0

            # Layer extent interpreted in the selected CRS → WGS84.
            # If the layer has no geometries (e.g. a freshly created Shapefile
            # with NULL geometries), use the extent computed from
            # attribute fields during configuration (cache _cached_data_extent_wgs).
            data_extent_wgs = None
            if self._current_layer is not None:
                ext_native = self._current_layer.extent()
                if not ext_native.isNull() and not ext_native.isEmpty():
                    if crs_display.authid() != "EPSG:4326":
                        xform = QgsCoordinateTransform(
                            crs_display, crs_wgs84, QgsProject.instance()
                        )
                        try:
                            data_extent_wgs = xform.transformBoundingBox(ext_native)
                        except Exception:
                            data_extent_wgs = ext_native
                    else:
                        data_extent_wgs = ext_native

            # Fallback: extent computed from fields (NULL geometries)
            if (data_extent_wgs is None or data_extent_wgs.isNull())                     and self._cached_data_extent_wgs is not None                     and not self._cached_data_extent_wgs.isNull():
                data_extent_wgs = self._cached_data_extent_wgs

            # Zoom = union SCR + couche
            zoom = None
            if has_crs_bounds:
                zoom = QgsRectangle(crs_bounds)
            if data_extent_wgs is not None and not data_extent_wgs.isNull():
                zoom = QgsRectangle(data_extent_wgs) if zoom is None else (
                    zoom.__class__(zoom) or zoom
                )
                if zoom is not None:
                    zoom.combineExtentWith(data_extent_wgs)
                else:
                    zoom = QgsRectangle(data_extent_wgs)
            if zoom is None or zoom.isNull():
                zoom = QgsRectangle(-180, -90, 180, 90)

            # Couches canvas
            self._preview_layers = []

            if data_extent_wgs is not None and not data_extent_wgs.isNull():
                lyr_d = QgsVectorLayer("Polygon?crs=EPSG:4326", "layer_extent", "memory")
                fd = QgsFeature()
                fd.setGeometry(QgsGeometry.fromRect(data_extent_wgs))
                lyr_d.dataProvider().addFeature(fd)
                lyr_d.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "120,0,180,128", "outline_color": "120,0,180,220",
                        "outline_width": "1.2",
                    })
                ))
                self._preview_layers.append(lyr_d)

            if has_crs_bounds:
                lyr_c = QgsVectorLayer("Polygon?crs=EPSG:4326", "crs_bounds", "memory")
                fc = QgsFeature()
                fc.setGeometry(QgsGeometry.fromRect(crs_bounds))
                lyr_c.dataProvider().addFeature(fc)
                lyr_c.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "220,0,0,80", "outline_color": "220,0,0,220",
                        "outline_width": "0.8",
                    })
                ))
                self._preview_layers.append(lyr_c)

            world = get_world_layer()
            if world:
                world.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "#d0d0d0", "outline_color": "#888888",
                        "outline_width": "0.15",
                    })
                ))
                self._preview_layers.append(world)

            self._canvas.setDestinationCrs(crs_wgs84)
            self._canvas.setLayers(self._preview_layers)
            self._canvas.setExtent(zoom)
            QTimer.singleShot(80, self._canvas.refresh)

            # ── Chevauchement : contains() (pas intersects) ───────────────
            # Verify that the layer extent is ENTIRELY within the
            # CRS bounds. If any part exceeds them (e.g. Lambert coordinates
            # interpreted as WGS84 with xMax=994873), the button is disabled.
            has_overlap = True
            if data_extent_wgs is not None and has_crs_bounds:
                has_overlap = crs_bounds.contains(data_extent_wgs)

            if self._btn_apply_crs is not None:
                self._btn_apply_crs.setEnabled(
                    self._current_layer is not None and has_overlap
                )

            # ── Count features without geometry (sample up to 50,000) ───
            n_no_geom = 0
            if self._current_layer is not None:
                try:
                    from qgis.core import QgsFeatureRequest as _QFR
                    _count = 0
                    for _feat in self._current_layer.getFeatures():
                        _count += 1
                        if _count > 50_000:
                            break
                        _g = _feat.geometry()
                        if _g is None or _g.isNull() or _g.isEmpty():
                            n_no_geom += 1
                except Exception:
                    n_no_geom = 0

            # ── Label ─────────────────────────────────────────────────────
            parts = []
            if self._current_layer is not None:
                n = self._current_layer.featureCount()
                cur = (self._current_layer.crs().authid()
                       if self._current_layer.crs().isValid() else "Inconnu")
                parts.append(
                    f"Couche « {self._current_layer.name()} » — "
                    f"{n:,} entité(s) · SCR déclaré : {cur}"
                )
                # Message for features without geometry:
                # - If the extent cache is set → freshly created Shapefile,
                #   geometries will be defined at step 2 → neutral informational message.
                # - Otherwise → standard warning prompting the user to correct.
                if n_no_geom > 0:
                    if self._cached_data_extent_wgs is not None:
                        # Freshly created Shapefile: geometries intentionally empty,
                        # to be defined at step 2 → neutral info message, no alert.
                        parts.append(
                            f"ℹ {n_no_geom} entité(s) sans géométrie"
                            " (Shapefile créé — cliquez sur « Étape suivante »"
                            " pour définir les géométries à l'étape 2)"
                        )
                    else:
                        parts.append(
                            f"⚠ {n_no_geom} entité(s) sans géométrie détectée(s)"
                            " — passez à l'étape 2 pour les corriger."
                        )
                if data_extent_wgs is not None:
                    e = data_extent_wgs
                    suffix = ("" if has_overlap
                              else "  ⚠ Emprise hors bounds du SCR — SCR incohérent")
                    parts.append(
                        f"Emprise interprétée en {crs_display.authid()} → WGS84 : "
                        f"X [{e.xMinimum():.4f}…{e.xMaximum():.4f}]  "
                        f"Y [{e.yMinimum():.4f}…{e.yMaximum():.4f}]"
                        + suffix
                    )
                else:
                    parts.append("Pas d'emprise disponible (couche sans géométrie).")

            # Colour: warning if no extent at all, warning if CRS is inconsistent
            label_color = (_COLOR_INFO if has_overlap else _COLOR_WARNING)
            if n_no_geom > 0 and data_extent_wgs is None:
                label_color = _COLOR_WARNING
            self._set_map_info("\n".join(parts), label_color)

        except Exception as exc:
            logger.exception("GeoFixer : erreur canvas étape 1.")
            self._set_map_info(f"Erreur canvas : {exc}", _COLOR_DANGER)
            if self._btn_apply_crs is not None:
                self._btn_apply_crs.setEnabled(False)

    def _set_map_info(self, text: str, color: str) -> None:
        if self._map_info_label is not None:
            self._map_info_label.setText(text)
            self._map_info_label.setStyleSheet(f"color:{color};font-size:10px;")

    # ======================================================================
    # Handlers — Étape 2
    # ======================================================================

    def _go_to_step1(self) -> None:
        self._stack.setCurrentIndex(0)
        self._update_step_bar(1)
        # Refresh the step-1 canvas to reflect any modifications
        # (reprojection, extent update) made at step 2
        QTimer.singleShot(100, self._refresh_map_preview)

    def _on_filter_changed(self, _: int) -> None:
        self._populate_entity_table()

    def _on_action_mode_changed(self, mode_id: int) -> None:
        self._reproject_w.setVisible(mode_id == 0)
        self._fields_w.setVisible(mode_id == 1)
        if self._canvas_s2:
            self._canvas_s2.setVisible(False)
        if self._preview_info_s2:
            self._preview_info_s2.setText("")
        # Reset the outside-CRS block when the action mode changes.
        self._preview_has_outside_crs = False
        if self._apply_btn is not None:
            self._apply_btn.setEnabled(True)

    def _on_fields_mode_changed(self, mode_id: int) -> None:
        self._lonlat_w.setVisible(mode_id == 0)
        self._wkt_w.setVisible(mode_id == 1)
        if self._canvas_s2:
            self._canvas_s2.setVisible(False)
        if self._preview_info_s2:
            self._preview_info_s2.setText("")
        # Reset the outside-CRS block when the fields mode changes.
        self._preview_has_outside_crs = False
        if self._apply_btn is not None:
            self._apply_btn.setEnabled(True)

    def _on_chk_reproject_toggled(self, checked: bool) -> None:
        """Affiche/masque le sélecteur SCR source pour le mode 'depuis les champs'."""
        if self._crs_src_fields_w is not None:
            self._crs_src_fields_w.setVisible(checked)

    def _on_selection_changed(self) -> None:
        self._update_entity_count()

    def _on_apply_fixes(self) -> None:
        selected_ids = self._get_selected_feature_ids()
        if not selected_ids:
            QMessageBox.warning(
                self, "GeoFixer",
                "Aucune entité sélectionnée.\n"
                "Sélectionnez au moins une entité dans le tableau."
            )
            return
        action_mode = self._action_bg.checkedId() if self._action_bg else -1
        if   action_mode == 0: self._apply_reproject(selected_ids)
        elif action_mode == 1: self._apply_from_fields(selected_ids)
        else:
            QMessageBox.warning(
                self, "GeoFixer",
                "Aucune action sélectionnée."
            )

    # ======================================================================
    # Field detection and table population
    # ======================================================================

    def _detect_and_populate_fields(self) -> None:
        """
        Détecte les types de champs par valeurs (detect_field_types_by_values),
        puis remplit les comboboxes lon/lat et WKT avec les champs appropriés.

        Stocke les résultats dans self._numeric_fields et self._wkt_fields
        pour que le tableau ne montre que les colonnes pertinentes.
        """
        if self._current_layer is None:
            return

        # Detect field types by sampling values
        self._field_type_info = detect_field_types_by_values(self._current_layer)

        all_names     = [f.name() for f in self._current_layer.fields()]
        self._numeric_fields = [
            n for n in all_names
            if self._field_type_info.get(n) and self._field_type_info[n].is_numeric
        ]
        self._wkt_fields = [
            n for n in all_names
            if self._field_type_info.get(n) and self._field_type_info[n].is_wkt
        ]

        lon_lat_list = self._numeric_fields or all_names
        wkt_list     = self._wkt_fields     or all_names

        # ── Longitude ────────────────────────────────────────────────────
        self._lon_combo.clear()
        self._lon_combo.addItems(lon_lat_list)
        for fname in lon_lat_list:
            if any(k in fname.lower() for k in ("lon", "lng", "longitude", "x_coord", "xcoord")):
                self._lon_combo.setCurrentText(fname)
                break

        # ── Latitude ─────────────────────────────────────────────────────
        self._lat_combo.clear()
        self._lat_combo.addItems(lon_lat_list)
        for fname in lon_lat_list:
            if any(k in fname.lower() for k in ("lat", "latitude", "y_coord", "ycoord")):
                self._lat_combo.setCurrentText(fname)
                break

        # ── WKT ──────────────────────────────────────────────────────────
        self._wkt_combo.clear()
        self._wkt_combo.addItems(wkt_list)
        for fname in wkt_list:
            if any(k in fname.lower() for k in ("wkt", "geometry", "geom", "shape")):
                self._wkt_combo.setCurrentText(fname)
                break

    def _update_target_crs_label(self) -> None:
        """Met à jour le label SCR cible dans le widget de reprojection."""
        if self._lbl_target_crs is None:
            return
        if self._current_layer is not None and self._current_layer.crs().isValid():
            auth = self._current_layer.crs().authid()
            self._lbl_target_crs.setText(
                f"→ Reprojection vers le SCR de la couche : {auth}"
            )
        else:
            self._lbl_target_crs.setText(
                "→ Reprojection vers le SCR de la couche (non défini à l'étape 1)"
            )

    def _populate_entity_table(self) -> None:
        """
        Remplit le tableau avec les entités problématiques.

        Colonnes affichées : FID + champs utiles détectés (numériques ∪ WKT) + Raison.
        Si aucun champ utile n'est détecté, on prend les 6 premiers champs.
        """
        if self._current_layer is None:
            self._entity_table.setRowCount(0)
            self._entity_count_lbl.setText(tr("Aucune couche sélectionnée."))
            return

        include_ok = (self._filter_bg.checkedId() == 1 if self._filter_bg else False)
        crs = self._applied_crs or (
            self._current_layer.crs()
            if self._current_layer.crs().isValid() else None
        )

        # Useful columns = numeric ∪ WKT candidates (no duplicates)
        useful = list(dict.fromkeys(self._numeric_fields + self._wkt_fields))
        if not useful:
            useful = [f.name() for f in self._current_layer.fields()][:6]

        self._problematic_feats = find_problematic_features(
            layer=self._current_layer,
            crs=crs,
            include_ok=include_ok,
            display_fields=useful,
        )

        all_cols = ["FID"] + useful + [tr("Raison")]
        # Disable sorting during fill to avoid row index conflicts
        # (sorting can reorder rows mid-insertion)
        self._entity_table.setSortingEnabled(False)
        self._entity_table.clear()
        self._entity_table.setColumnCount(len(all_cols))
        self._entity_table.setHorizontalHeaderLabels(all_cols)
        self._entity_table.setRowCount(len(self._problematic_feats))

        reason_colors = {
            "no_geometry": QColor("#ffd6d6"),
            "outside_crs": QColor("#fff3cd"),
            "ok":          QColor("#d4edda"),
        }

        for row, pf in enumerate(self._problematic_feats):
            fid_item = QTableWidgetItem()
            # Store FID as int in DisplayRole → correct numeric sort
            fid_item.setData(_Qt_UserRole, pf.feature_id)
            fid_item.setData(_Qt_DisplayRole, pf.feature_id)
            self._entity_table.setItem(row, 0, fid_item)

            for ci, col in enumerate(useful, start=1):
                self._entity_table.setItem(
                    row, ci,
                    QTableWidgetItem(pf.attributes.get(col, ""))
                )

            reason_item = QTableWidgetItem(pf.reason_label)
            bg = reason_colors.get(pf.reason)
            if bg:
                reason_item.setBackground(bg)
            self._entity_table.setItem(row, len(all_cols) - 1, reason_item)

        try:
            hdr = self._entity_table.horizontalHeader()
            hdr.setSectionResizeMode(_QHeaderView_ResizeToContents)
            hdr.setSectionResizeMode(len(all_cols) - 1, _QHeaderView_Stretch)
        except Exception:
            pass

        # Re-enable sorting once the table is fully populated
        self._entity_table.setSortingEnabled(True)
        self._update_entity_count()

    def _update_entity_count(self) -> None:
        n_total    = self._entity_table.rowCount()
        n_sel_items = len(self._entity_table.selectedItems() or [])
        n_cols      = max(1, self._entity_table.columnCount())
        n_sel_rows  = n_sel_items // n_cols
        self._entity_count_lbl.setText(
            f"{n_total} entité(s) listée(s)  —  {n_sel_rows} sélectionnée(s)."
        )

    # ======================================================================
    # Step-2 preview
    # ======================================================================

    def _run_step2_preview(self) -> None:
        """
        Affiche une carte de prévisualisation de la transformation choisie.

        Couches affichées (ordre avant-plan → arrière-plan) :
          1. Résultat de la transformation (vert) :
               - ≤ 20 entités sélectionnées → géométries individuelles
               - > 20 entités sélectionnées → emprise globale (QgsRectangle)
          2. Emprise de la couche entière (violet) — indépendante de la sélection
          3. Emprise du SCR de référence (rouge)
          4. Fond pays du monde (gris)

        En cas d'erreur, un message détaillé par catégorie est affiché :
          - Entités sans géométrie (no_geom)
          - Coordonnées non numériques ou NaN (bad_value)
          - WKT non parseable (bad_wkt)
          - Erreur de transformation de coordonnées (xform_error)
        """
        # Clear the previous apply-result label and reset the blocking flag
        # so that a successful preview always re-enables the Apply button.
        self._set_result("", _COLOR_INFO)
        self._preview_has_outside_crs = False
        if self._apply_btn is not None:
            self._apply_btn.setEnabled(True)

        if self._canvas_s2 is None or self._current_layer is None:
            return

        selected_ids = self._get_selected_feature_ids()
        if not selected_ids:
            self._set_preview_info_s2(
                "Sélectionnez au moins une entité.", _COLOR_WARNING
            )
            return

        action_mode = self._action_bg.checkedId() if self._action_bg else -1
        if action_mode == -1:
            self._set_preview_info_s2("Choisissez d'abord une action.", _COLOR_WARNING)
            return

        try:
            from qgis.core import (
                QgsCoordinateReferenceSystem, QgsVectorLayer, QgsFeature,
                QgsGeometry, QgsPointXY, QgsRectangle,
                QgsCoordinateTransform, QgsProject,
                QgsSingleSymbolRenderer, QgsFillSymbol,
                QgsMarkerSymbol, QgsLineSymbol, QgsWkbTypes,
            )

            crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

            # ── Per-category error counters ────────────────────────────
            err_no_geom   = 0   # null or empty geometry
            err_bad_value = 0   # non-numeric value / NaN
            err_bad_wkt   = 0   # WKT non parseable
            err_xform     = 0   # erreur de transformation

            # ── Compute the transformed geometries (in WGS84) ────────────
            preview_geoms = []
            display_crs   = None

            if action_mode == 0:
                # Reprojection depuis SCR d'origine → SCR couche
                source_crs = (self._crs_widget_src.crs()
                              if self._crs_widget_src else None)
                target_crs = (self._current_layer.crs()
                              if self._current_layer.crs().isValid() else crs_wgs84)
                if source_crs is None or not source_crs.isValid():
                    self._set_preview_info_s2("SCR d'origine invalide.", _COLOR_WARNING)
                    return
                display_crs = target_crs

                xform_to_tgt  = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
                xform_to_wgs  = QgsCoordinateTransform(target_crs, crs_wgs84, QgsProject.instance())

                # Direct source_crs → WGS84 transform, used as fallback.
                xform_src_to_wgs = QgsCoordinateTransform(
                    source_crs, crs_wgs84, QgsProject.instance()
                )
                # Allow approximate transforms (no datum grid required).
                # This matches QGIS's own rendering behaviour when datum grids are
                # absent — it shows the "approximate transform" warning but succeeds.
                for _xf in (xform_to_tgt, xform_to_wgs, xform_src_to_wgs):
                    try:
                        _xf.setAllowFallbackTransforms(True)
                    except AttributeError:
                        pass  # Older QGIS builds without this method

                # Skip the source → target step when both CRS are identical
                # (identity transform is a no-op and may still raise on bad datum).
                same_crs = source_crs.authid() == target_crs.authid()

                for fid in selected_ids:
                    feat = self._current_layer.getFeature(fid)
                    geom = feat.geometry()
                    if geom is None or geom.isNull():
                        err_no_geom += 1
                        continue
                    try:
                        g = QgsGeometry(geom)  # deep copy — copy.copy() is shallow for C++ objects
                        if not same_crs:
                            g.transform(xform_to_tgt)
                        g.transform(xform_to_wgs)
                        if g.isNull() or g.isEmpty():
                            raise ValueError("Transform produced null/empty geometry")
                        preview_geoms.append(g)
                    except Exception:
                        err_xform += 1
                        # Fallback: transform source_crs → WGS84 directly
                        # so the geometry appears at its current position.
                        try:
                            g_fb = QgsGeometry(geom)
                            g_fb.transform(xform_src_to_wgs)
                            if not g_fb.isNull() and not g_fb.isEmpty():
                                preview_geoms.append(g_fb)
                        except Exception:
                            pass  # Untransformable even with fallback

            else:
                # Depuis les champs (Lon/Lat ou WKT)
                fields_mode  = (self._fields_mode_bg.checkedId()
                                if self._fields_mode_bg else 0)
                do_reproject = (self._chk_reproject is not None
                                and self._chk_reproject.isChecked())
                src_crs = (self._crs_widget_src_fields.crs()
                           if do_reproject and self._crs_widget_src_fields else None)
                tgt_crs = (self._current_layer.crs()
                           if self._current_layer.crs().isValid() else crs_wgs84)
                display_crs = tgt_crs

                xform_to_tgt = None
                if do_reproject and src_crs is not None and src_crs.isValid():
                    xform_to_tgt = QgsCoordinateTransform(src_crs, tgt_crs, QgsProject.instance())
                    try:
                        xform_to_tgt.setAllowFallbackTransforms(True)
                    except AttributeError:
                        pass
                xform_to_wgs = QgsCoordinateTransform(tgt_crs, crs_wgs84, QgsProject.instance())
                try:
                    xform_to_wgs.setAllowFallbackTransforms(True)
                except AttributeError:
                    pass

                if fields_mode == 0:
                    # Lon / Lat → Point
                    lon_f = self._lon_combo.currentText() if self._lon_combo else ""
                    lat_f = self._lat_combo.currentText() if self._lat_combo else ""
                    if not lon_f or not lat_f:
                        self._set_preview_info_s2(
                            "Sélectionnez les champs Longitude et Latitude.", _COLOR_WARNING
                        )
                        return
                    for fid in selected_ids:
                        feat = self._current_layer.getFeature(fid)
                        try:
                            rx, ry = feat[lon_f], feat[lat_f]
                            if rx is None or ry is None:
                                err_bad_value += 1; continue
                            x, y = float(str(rx).replace(',', '.')), float(str(ry).replace(',', '.'))
                            if x != x or y != y:   # NaN
                                err_bad_value += 1; continue
                            g = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                            if xform_to_tgt:
                                g.transform(xform_to_tgt)
                            g.transform(xform_to_wgs)
                            preview_geoms.append(g)
                        except (ValueError, TypeError):
                            err_bad_value += 1
                        except Exception:
                            err_xform += 1
                else:
                    # WKT
                    wkt_f = self._wkt_combo.currentText() if self._wkt_combo else ""
                    if not wkt_f:
                        self._set_preview_info_s2("Sélectionnez le champ WKT.", _COLOR_WARNING)
                        return
                    for fid in selected_ids:
                        feat = self._current_layer.getFeature(fid)
                        try:
                            raw = feat[wkt_f]
                            if raw is None or str(raw).strip() == "":
                                err_bad_value += 1; continue
                            g = QgsGeometry.fromWkt(str(raw).strip())
                            if g is None or g.isNull():
                                err_bad_wkt += 1; continue
                            if xform_to_tgt:
                                g.transform(xform_to_tgt)
                            g.transform(xform_to_wgs)
                            preview_geoms.append(g)
                        except Exception:
                            err_xform += 1

            # ── Detailed error message if no valid geometry ───────────────
            n_errors = err_no_geom + err_bad_value + err_bad_wkt + err_xform
            # ── Build error message ────────────────────────────────────────────
            # We do NOT return early: the canvas always shows the layer extent
            # (purple) and the CRS bounds (red) to help diagnose the problem.
            # In reproject mode, fallback geometries (source CRS → WGS84) are
            # added to preview_geoms so the green layer still appears.
            has_xform_error = (err_xform > 0)
            # no_geom_parts collects error details shown BELOW the success line,
            # or as the main message when nothing could be displayed at all.
            no_geom_parts = []
            if not preview_geoms:
                no_geom_parts = ["Aucune géométrie valide à prévisualiser."]
            elif has_xform_error:
                # Fallback geometries ARE shown (green), but they reflect the
                # current position, not the reprojected one. Warn the user.
                no_geom_parts.append(
                    f"⚠ {err_xform} entité(s) : position actuelle affichée"
                    " (reprojection impossible — vérifiez le SCR d'origine)")
            if err_no_geom:
                no_geom_parts.append(
                    f"  • {err_no_geom} entité(s) sans géométrie source")
            if err_bad_value:
                no_geom_parts.append(
                    f"  • {err_bad_value} valeur(s) non numérique(s), nulle(s) ou NaN"
                    " — vérifiez que les champs lon/lat contiennent des nombres")
            if err_bad_wkt:
                no_geom_parts.append(
                    f"  • {err_bad_wkt} valeur(s) WKT non valide(s)"
                    " — le champ sélectionné contient peut-être du texte libre")

            # Block Apply when: no geometry at all, OR transformation errors
            # (fallback geometries show the current position, not the target).
            if has_xform_error or not preview_geoms:
                self._preview_has_outside_crs = True
                if self._apply_btn is not None:
                    self._apply_btn.setEnabled(False)

            # ── Build the result layer (green) — skipped if no valid geom ──
            wkb_type = preview_geoms[0].wkbType() if preview_geoms else None
            geom_enum = QgsWkbTypes.geometryType(wkb_type) if wkb_type is not None else None
            mem_type  = {0: "Point", 1: "LineString", 2: "Polygon"}.get(
                int(geom_enum), "Point") if geom_enum is not None else "Point"

            self._preview_layers_s2 = []

            # Display choice: individual geometries (≤20) or bounding box (>20)
            N_GEOM_THRESHOLD = 20
            lyr_result = None
            if preview_geoms:
                lyr_result = QgsVectorLayer(f"{mem_type}?crs=EPSG:4326", "result", "memory")

                if len(preview_geoms) <= N_GEOM_THRESHOLD:
                    # Individual geometries
                    for g in preview_geoms:
                        f = QgsFeature(); f.setGeometry(g)
                        lyr_result.dataProvider().addFeature(f)
                else:
                    # Global extent of the transformed features
                    bbox = QgsRectangle()
                    for g in preview_geoms:
                        bbox.combineExtentWith(g.boundingBox())
                    f = QgsFeature()
                    f.setGeometry(QgsGeometry.fromRect(bbox))
                    lyr_result.dataProvider().addFeature(f)

                lyr_result.updateExtents()

                if mem_type == "Point" and len(preview_geoms) <= N_GEOM_THRESHOLD:
                    # Reduced size (≈ 3× smaller than QGIS default)
                    sym_result = QgsMarkerSymbol.createSimple({
                        "color":         "0,160,60,220",
                        "outline_color": "0,100,30,255",
                        "size":          "1.3",
                    })
                elif mem_type == "LineString" and len(preview_geoms) <= N_GEOM_THRESHOLD:
                    # Thick stroke to remain visible at small scale
                    sym_result = QgsLineSymbol.createSimple({
                        "color": "0,160,60,230",
                        "width": "1.5",
                    })
                else:
                    # Polygons (individual or bbox): very thick outline
                    sym_result = QgsFillSymbol.createSimple({
                        "color":         "0,160,60,70",
                        "outline_color": "0,130,30,255",
                        "outline_width": "2.0",
                    })
                lyr_result.setRenderer(QgsSingleSymbolRenderer(sym_result))
                self._preview_layers_s2.append(lyr_result)

            # ── Emprise de la COUCHE ENTIÈRE (violet) ─────────────────────
            # Computed independently of the selection, in WGS84
            layer_ext_native = self._current_layer.extent()
            if (display_crs is not None and display_crs.isValid()
                    and not layer_ext_native.isNull()):
                try:
                    xform_layer_to_wgs = QgsCoordinateTransform(
                        display_crs, crs_wgs84, QgsProject.instance()
                    )
                    layer_ext_wgs = xform_layer_to_wgs.transformBoundingBox(layer_ext_native)
                except Exception:
                    layer_ext_wgs = layer_ext_native
            else:
                layer_ext_wgs = layer_ext_native

            if not layer_ext_wgs.isNull() and not layer_ext_wgs.isEmpty():
                lyr_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "layer_extent", "memory")
                fl = QgsFeature()
                fl.setGeometry(QgsGeometry.fromRect(layer_ext_wgs))
                lyr_layer.dataProvider().addFeature(fl)
                lyr_layer.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "120,0,180,60",
                        "outline_color": "120,0,180,200",
                        "outline_width": "1.0",
                    })
                ))
                self._preview_layers_s2.append(lyr_layer)

            # ── Reference CRS extent (red) ────────────────────────────────
            if display_crs is not None and display_crs.isValid():
                cb = display_crs.bounds()
                if not cb.isNull() and cb.width() > 0:
                    lyr_c = QgsVectorLayer("Polygon?crs=EPSG:4326", "crs_bounds", "memory")
                    fc = QgsFeature()
                    fc.setGeometry(QgsGeometry.fromRect(cb))
                    lyr_c.dataProvider().addFeature(fc)
                    lyr_c.setRenderer(QgsSingleSymbolRenderer(
                        QgsFillSymbol.createSimple({
                            "color": "220,0,0,40",
                            "outline_color": "220,0,0,180",
                            "outline_width": "0.8",
                        })
                    ))
                    self._preview_layers_s2.append(lyr_c)

            # ── Fond monde (gris) ─────────────────────────────────────────
            world = get_world_layer()
            if world:
                world.setRenderer(QgsSingleSymbolRenderer(
                    QgsFillSymbol.createSimple({
                        "color": "#d0d0d0",
                        "outline_color": "#888888",
                        "outline_width": "0.15",
                    })
                ))
                self._preview_layers_s2.append(world)

            # ── Zoom = union (result extent + layer extent + CRS extent) ──
            # When no geometry was produced, zoom on layer + CRS extents only.
            zoom = None
            if lyr_result is not None:
                result_ext = lyr_result.extent()
                if not result_ext.isNull():
                    zoom = QgsRectangle(result_ext)

            if not layer_ext_wgs.isNull():
                if zoom is None:
                    zoom = QgsRectangle(layer_ext_wgs)
                else:
                    zoom.combineExtentWith(layer_ext_wgs)

            if display_crs is not None and display_crs.isValid():
                cb2 = display_crs.bounds()
                if not cb2.isNull() and cb2.width() > 0:
                    if zoom is None:
                        zoom = QgsRectangle(cb2)
                    else:
                        zoom.combineExtentWith(cb2)

            if zoom is None or zoom.isNull():
                zoom = QgsRectangle(-180, -90, 180, 90)

            # ── Afficher ──────────────────────────────────────────────────
            self._canvas_s2.setVisible(True)
            self._canvas_s2.setDestinationCrs(crs_wgs84)
            self._canvas_s2.setLayers(self._preview_layers_s2)
            self._canvas_s2.setExtent(zoom)
            QTimer.singleShot(80, self._canvas_s2.refresh)

            # ── Count result geometries outside the CRS extent ──────────
            n_outside_crs = 0
            if display_crs is not None and display_crs.isValid():
                _crs_b = display_crs.bounds()
                if not _crs_b.isNull() and _crs_b.width() > 0:
                    for _pg in preview_geoms:
                        _bb = _pg.boundingBox()
                        if not _crs_b.intersects(_bb):
                            n_outside_crs += 1

            # ── Update Apply button based on preview result ──────────────
            # If any geometry falls outside the CRS bounds, block Apply.
            # (The flag may already be True if set earlier in this run.)
            if n_outside_crs > 0:
                self._preview_has_outside_crs = True
            if self._apply_btn is not None:
                self._apply_btn.setEnabled(not self._preview_has_outside_crs)

            # ── Result message ────────────────────────────────────────────
            if no_geom_parts:
                # No valid geometry: show the error details as the main message.
                self._set_preview_info_s2("\n".join(no_geom_parts), _COLOR_WARNING)
            else:
                n_ok = len(preview_geoms)
                bbox_note = (" — emprise globale affichée (> 20 entités)"
                             if n_ok > N_GEOM_THRESHOLD else "")
                msg = f"✔ {n_ok} géométrie(s) prévisualisée(s){bbox_note}"
                if n_outside_crs:
                    msg += (
                        f"\n⚠ {n_outside_crs} entité(s) hors de l'emprise du SCR"
                        f" {display_crs.authid()}"
                        " — correction bloquée, corrigez le SCR d'origine"
                    )
                if n_errors:
                    parts_err = []
                    if err_no_geom:   parts_err.append(f"{err_no_geom} sans géométrie")
                    if err_bad_value: parts_err.append(f"{err_bad_value} valeur(s) invalide(s)")
                    if err_bad_wkt:   parts_err.append(f"{err_bad_wkt} WKT non parseable")
                    if err_xform:     parts_err.append(f"{err_xform} erreur transformation")
                    msg += f"  ·  ⚠ ignorées : {', '.join(parts_err)}"
                final_color = (_COLOR_SUCCESS if (not n_errors and not n_outside_crs)
                               else _COLOR_WARNING)
                self._set_preview_info_s2(msg, final_color)

        except Exception as exc:
            logger.exception("GeoFixer : erreur prévisualisation étape 2.")
            self._set_preview_info_s2(f"Erreur inattendue : {exc}", _COLOR_DANGER)

    def _set_preview_info_s2(self, text: str, color: str) -> None:
        if self._preview_info_s2 is not None:
            self._preview_info_s2.setText(text)
            self._preview_info_s2.setStyleSheet(f"color:{color};font-size:10px;")

    # ======================================================================
    # Application des corrections
    # ======================================================================

    def _apply_reproject(self, selected_ids: List[int]) -> None:
        """
        Reprojette les entités sélectionnées DEPUIS le SCR d'origine
        VERS le SCR courant de la couche (défini à l'étape 1).
        """
        source_crs = (self._crs_widget_src.crs()
                      if self._crs_widget_src else None)
        if source_crs is None or not source_crs.isValid():
            QMessageBox.warning(self, "GeoFixer", "SCR d'origine invalide.")
            return

        target_crs = (self._current_layer.crs()
                      if self._current_layer.crs().isValid() else None)
        if target_crs is None:
            QMessageBox.warning(
                self, "GeoFixer",
                "La couche n'a pas de SCR défini.\n"
                "Définissez d'abord le SCR à l'étape 1."
            )
            return

        n_ok, n_err, error = reproject_features(
            layer=self._current_layer,
            feature_ids=selected_ids,
            source_crs=source_crs,
            target_crs=target_crs,
        )
        self._show_apply_result(n_ok, n_err, error, "reprojection")

    def _apply_from_fields(self, selected_ids: List[int]) -> None:
        """
        Crée ou remplace les géométries depuis des champs attributaires,
        avec reprojection optionnelle vers le SCR couche.
        """
        fields_mode  = (self._fields_mode_bg.checkedId()
                        if self._fields_mode_bg else 0)
        do_reproject = (self._chk_reproject is not None
                        and self._chk_reproject.isChecked())
        src_crs = (self._crs_widget_src_fields.crs()
                   if do_reproject and self._crs_widget_src_fields else None)
        # Target CRS = the layer's CRS (not the step-1 selector)
        tgt_crs = (self._current_layer.crs()
                   if self._current_layer.crs().isValid() else None)

        # Si l'utilisateur demande une reprojection mais n'a pas de SCR source valide
        if do_reproject and (src_crs is None or not src_crs.isValid()):
            QMessageBox.warning(
                self, "GeoFixer",
                "Reprojection demandée mais SCR source invalide."
            )
            return

        if is_csv_layer(self._current_layer):
            self._apply_csv_from_fields(fields_mode, src_crs or tgt_crs, src_crs, tgt_crs)
            return

        if fields_mode == 0:
            lon = self._lon_combo.currentText() if self._lon_combo else ""
            lat = self._lat_combo.currentText() if self._lat_combo else ""
            n_ok, n_err, error = build_geometry_from_lonlat(
                layer=self._current_layer,
                feature_ids=selected_ids,
                lon_field=lon, lat_field=lat,
                crs=src_crs or tgt_crs,
                target_crs=tgt_crs if do_reproject else None,
            )
        else:
            wkt = self._wkt_combo.currentText() if self._wkt_combo else ""
            n_ok, n_err, error = build_geometry_from_wkt(
                layer=self._current_layer,
                feature_ids=selected_ids,
                wkt_field=wkt,
                crs=src_crs or tgt_crs,
                target_crs=tgt_crs if do_reproject else None,
            )

        self._show_apply_result(n_ok, n_err, error, "champs")

    def _apply_csv_from_fields(self, fields_mode, crs, src_crs, tgt_crs) -> None:
        reply = QMessageBox.question(
            self, tr("GeoFixer — Couche CSV"),
            "La couche source est un CSV — l'édition de géométrie en place n'est\n"
            "pas supportée. Une nouvelle couche en mémoire sera créée.\n\nContinuer ?",
            _QMsgBox_Yes | _QMsgBox_No,
        )
        if reply != _QMsgBox_Yes:
            return

        if fields_mode == 0:
            lon = self._lon_combo.currentText() if self._lon_combo else ""
            lat = self._lat_combo.currentText() if self._lat_combo else ""
            new_layer, error = build_memory_layer_from_lonlat(
                source_layer=self._current_layer,
                lon_field=lon, lat_field=lat,
                crs=crs, target_crs=tgt_crs if src_crs else None,
            )
        else:
            wkt = self._wkt_combo.currentText() if self._wkt_combo else ""
            new_layer, error = build_memory_layer_from_wkt(
                source_layer=self._current_layer,
                wkt_field=wkt,
                crs=crs, target_crs=tgt_crs if src_crs else None,
            )

        if error:
            self._set_result(f"Erreur : {error}", _COLOR_DANGER)
            QMessageBox.critical(self, tr("GeoFixer — Erreur"), error)
        elif new_layer:
            msg = (f"✔ Couche « {new_layer.name()} » créée "
                   f"({new_layer.featureCount()} entité(s)).")
            self._set_result(msg, _COLOR_SUCCESS)
            QMessageBox.information(self, "GeoFixer", msg)
            # Hide the preview canvas after successful correction.
            self._hide_preview_canvas()

    def _hide_preview_canvas(self) -> None:
        """
        Hide the step-2 preview canvas and clear the preview info label.

        Called after corrections are applied so the user sees a clean state
        and must explicitly click "Preview transformation" again if they want
        to check a new selection.
        """
        if self._canvas_s2 is not None:
            self._canvas_s2.setVisible(False)
            self._canvas_s2.setLayers([])
        self._preview_layers_s2 = []
        self._set_preview_info_s2("", _COLOR_INFO)
        # Re-enable the Apply button for the next correction attempt.
        self._preview_has_outside_crs = False
        if self._apply_btn is not None:
            self._apply_btn.setEnabled(True)

    def _show_apply_result(
        self, n_ok: int, n_err: int,
        error: Optional[str], mode: str,
    ) -> None:
        if error:
            self._set_result(f"Erreur : {error}", _COLOR_DANGER)
            QMessageBox.critical(self, tr("GeoFixer — Erreur"), error)
            return
        if n_ok == 0 and n_err > 0:
            msg = (f"Aucune correction. "
                   f"{n_err} entité(s) ignorée(s) (valeurs invalides).")
            self._set_result(msg, _COLOR_WARNING)
            QMessageBox.warning(self, "GeoFixer", msg)
            return
        msg = (
            f"✔ {n_ok} entité(s) corrigée(s) par {mode}."
            + (f"\n⚠ {n_err} entité(s) ignorée(s)." if n_err else "")
        )
        self._set_result(msg, _COLOR_SUCCESS if not n_err else _COLOR_WARNING)
        QMessageBox.information(self, "GeoFixer", msg)
        # Hide the preview canvas: it shows the pre-correction state and would
        # be misleading after corrections have been applied.
        self._hide_preview_canvas()
        self._populate_entity_table()

    def _set_result(self, text: str, color: str) -> None:
        if self._result_label is not None:
            self._result_label.setText(text)
            self._result_label.setStyleSheet(f"color:{color};font-size:10px;")

    # ======================================================================
    # Utilitaires
    # ======================================================================

    def _get_s1_crs(self):
        try:
            if self._crs_widget_s1 is not None:
                crs = self._crs_widget_s1.crs()
                if crs.isValid():
                    return crs
        except Exception:
            pass
        return None

    def _get_selected_feature_ids(self) -> List[int]:
        ids  = []
        seen = set()
        for idx in self._entity_table.selectedIndexes():
            if idx.column() == 0:
                item = self._entity_table.item(idx.row(), 0)
                if item is not None:
                    raw = item.data(_Qt_UserRole)
                    if raw is not None and raw not in seen:
                        ids.append(int(raw)); seen.add(raw)
        return ids

    # make_crs_selector() → core.utils

