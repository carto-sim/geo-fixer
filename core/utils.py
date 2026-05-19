# -*- coding: utf-8 -*-
"""
Utilitaires partagés entre les dialogues du plugin GeoFixer.

Ce module regroupe les composants réutilisables qui étaient dupliqués
entre geo_fixer_dialog.py et field_config_dialog.py :

  _NoWheelCombo    — QComboBox ignorant la molette de la souris
  get_world_layer  — Chargement du fond de carte pays du monde (QGIS)
  make_crs_selector — Création d'un sélecteur de SCR (QgsProjectionSelectionWidget)
  build_map_canvas  — Création d'un QgsMapCanvas préconfigurée
"""

import logging
import os

logger = logging.getLogger(__name__)


# ===========================================================================
# _NoWheelCombo
# ===========================================================================

from qgis.PyQt.QtWidgets import QComboBox


class _NoWheelCombo(QComboBox):
    """
    QComboBox ignorant la molette de la souris.

    Évite les changements involontaires quand l'utilisateur scrolle
    dans un formulaire contenant des comboboxes.
    """
    def wheelEvent(self, event):
        event.ignore()


# ===========================================================================
# Fond de carte pays du monde
# ===========================================================================

def get_world_layer():
    """
    Charge le fond de carte pays du monde fourni avec QGIS.

    Teste plusieurs chemins candidats (OSGeo4W Windows, Linux, macOS)
    pour world_map.gpkg ou world_map.shp.

    :return: QgsVectorLayer valide, ou None si le fichier est introuvable.
    """
    try:
        from qgis.core import QgsApplication, QgsVectorLayer
    except ImportError:
        return None

    pkg = QgsApplication.pkgDataPath()
    candidates = [
        os.path.join(pkg, "resources", "data", "world_map.gpkg"),
        os.path.join(pkg, "resources", "world_map.gpkg"),
        os.path.join(pkg, "resources", "data", "world_map.shp"),
        # OSGeo4W Windows (plusieurs variantes de nom)
        r"C:\OSGeo4W\apps\qgis\resources\data\world_map.gpkg",
        r"C:\OSGeo4W\apps\qgis-ltr\resources\data\world_map.gpkg",
        r"C:\OSGeo4W\apps\qgis-ltr-dev\resources\data\world_map.gpkg",
        # Linux
        "/usr/share/qgis/resources/data/world_map.gpkg",
        # macOS
        "/Applications/QGIS.app/Contents/MacOS/share/qgis/resources/data/world_map.gpkg",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                lyr = QgsVectorLayer(path, "world", "ogr")
                if lyr.isValid():
                    return lyr
            except Exception:
                pass
    logger.debug("GeoFixer : fond de carte pays du monde introuvable.")
    return None


# ===========================================================================
# CRS selector widget
# ===========================================================================

def make_crs_selector(default_crs_authid: str = "EPSG:4326"):
    """
    Crée un sélecteur de SCR complet (QgsProjectionSelectionWidget).

    Si QGIS n'est pas disponible, retourne une combobox de repli
    avec 3 SCR courants.

    :param default_crs_authid: EPSG ou authid du SCR par défaut.
    :return: Widget de sélection exposant .crs(), .setCrs(),
             signal .crsChanged.
    """
    try:
        from qgis.gui import QgsProjectionSelectionWidget
        from qgis.core import QgsCoordinateReferenceSystem
        w = QgsProjectionSelectionWidget()
        w.setCrs(QgsCoordinateReferenceSystem(default_crs_authid))
        return w
    except Exception:
        # Fallback minimal si QGIS n'est pas disponible (tests unitaires, etc.)
        cb = _NoWheelCombo()
        for lbl, epsg in [
            ("WGS 84 (EPSG:4326)", 4326),
            ("Lambert 93 (EPSG:2154)", 2154),
            ("Web Mercator (EPSG:3857)", 3857),
        ]:
            cb.addItem(lbl, epsg)
        cb.crs      = lambda: None
        cb.setCrs   = lambda _: None
        cb.crsChanged = type("Signal", (), {"connect": lambda self, fn: None})()
        return cb


# ===========================================================================
# Pre-configured map canvas
# ===========================================================================

def make_map_canvas(min_height: int = 200, min_width: int = 0):
    """
    Crée et retourne un QgsMapCanvas préconfiguré pour les dialogues GeoFixer.

    :param min_height: Hauteur minimale en pixels.
    :param min_width:  Largeur minimale en pixels (0 = pas de contrainte).
    :return: QgsMapCanvas ou None si QGIS n'est pas disponible.
    """
    try:
        from qgis.gui import QgsMapCanvas
        from qgis.PyQt.QtGui import QColor
        canvas = QgsMapCanvas()
        canvas.setMinimumHeight(min_height)
        if min_width > 0:
            canvas.setMinimumWidth(min_width)
        canvas.setCanvasColor(QColor("#e8e8e8"))
        return canvas
    except Exception:
        return None
