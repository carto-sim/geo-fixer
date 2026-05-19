# -*- coding: utf-8 -*-
"""
Classe principale du plugin GeoFixer.

Le dialogue est NON-MODAL : l'utilisateur peut continuer à utiliser QGIS
pendant que le plugin est ouvert. La référence au dialogue est conservée en
attribut pour éviter sa destruction par le garbage collector.

Si l'utilisateur clique à nouveau sur le bouton alors que le dialogue est
déjà ouvert, la fenêtre est remise au premier plan sans en créer une nouvelle.

Fichier icône attendu : geo_fixer/icon.png (24x24 ou 32x32 px, fond transparent).
"""

import os
import logging
from typing import Optional

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication

from .geo_fixer_dialog import GeoFixerDialog
from .i18n import init as _init_translations

logger = logging.getLogger(__name__)
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


class GeoFixerPlugin:
    """
    Plugin QGIS pour la correction de géométrie des entités vectorielles.

    Lifecycle :
      1. QGIS instancie la classe via classFactory() (voir __init__.py)
      2. QGIS appelle initGui() pour ajouter l'interface
      3. L'utilisateur clique -> run() ouvre ou remet au premier plan la fenetre
      4. QGIS appelle unload() lors de la desactivation
    """

    def __init__(self, iface):
        self.iface   = iface
        self._action: Optional[QAction]      = None
        # Persistent reference — prevents the garbage collector from destroying the window
        self._dialog: Optional[GeoFixerDialog] = None

    # ------------------------------------------------------------------
    # Lifecycle QGIS
    # ------------------------------------------------------------------

    def initGui(self) -> None:
        """Ajoute le plugin dans le menu Vecteur et la barre d'outils."""
        icon_path = os.path.join(PLUGIN_DIR, 'icon.png')
        icon = (QIcon(icon_path) if os.path.exists(icon_path)
                else QgsApplication.getThemeIcon('/algorithms/mAlgorithmCheckGeometry.svg'))

        _init_translations()  # Detect the language from QGIS settings
        self._action = QAction(icon, "GeoFixer", self.iface.mainWindow())
        self._action.setToolTip(
            "GeoFixer\n"
            "Corrige ou définit la géométrie d'entités vectorielles\n"
            "depuis des champs de coordonnées ou par reprojection."
        )
        self._action.triggered.connect(self.run)

        self.iface.addPluginToVectorMenu("&GeoFixer", self._action)
        self.iface.addToolBarIcon(self._action)

    def unload(self) -> None:
        """Retire le plugin de l'interface QGIS et ferme la fenêtre si ouverte."""
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None
        if self._action:
            self.iface.removePluginVectorMenu("&GeoFixer", self._action)
            self.iface.removeToolBarIcon(self._action)
            self._action = None

    # ------------------------------------------------------------------
    # User entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Ouvre la fenêtre GeoFixer en mode non-modal.

        Si la fenêtre est déjà visible, elle est simplement remise au premier
        plan — aucune nouvelle instance n'est créée.
        """
        try:
            if self._dialog is not None and self._dialog.isVisible():
                self._dialog.raise_()
                self._dialog.activateWindow()
                return

            # parent = mainWindow for OS integration (shared taskbar icon),
            # but the Qt.Window flag (set in GeoFixerDialog) ensures
            # an independent non-modal window.
            # parent=None: fully independent window from QGIS,
            # with its own entry in the Windows taskbar.
            # Lifetime is managed manually via self._dialog.
            self._dialog = GeoFixerDialog(self.iface, parent=None)
            self._dialog.show()

        except Exception as exc:
            logger.exception("Erreur à l'ouverture de GeoFixer : %s", exc)
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.iface.mainWindow(),
                "GeoFixer — Erreur",
                f"Impossible d'ouvrir le plugin :\n{exc}"
            )
