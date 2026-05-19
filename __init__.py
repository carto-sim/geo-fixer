# -*- coding: utf-8 -*-
"""
Point d'entrée du plugin GeoFixer pour QGIS.

QGIS appelle automatiquement la fonction classFactory() lors du
chargement du plugin. Cette fonction retourne une instance de la
classe principale du plugin.
"""

# ---------------------------------------------------------------------------
# Invalidation du cache bytecode — doit être fait EN PREMIER, avant toute
# importation des modules du plugin.
#
# Pourquoi : quand on installe une mise à jour par extraction de ZIP, les
# fichiers .py reçoivent le timestamp stocké dans l'archive (date de création
# du ZIP), souvent ANTÉRIEUR aux .pyc existants. Python compare les timestamps
# et, voyant le .pyc plus récent, ne recompile pas — l'ancienne version tourne.
#
# Solution : supprimer les __pycache__ ici, avant que le moindre import
# du plugin n'ait lieu. Python les recrée automatiquement avec les bons .pyc.
# ---------------------------------------------------------------------------
import os as _os
import shutil as _shutil
import importlib as _importlib


def _clear_pycache() -> None:
    """Supprime récursivement tous les __pycache__ du dossier du plugin."""
    plugin_dir = _os.path.dirname(_os.path.abspath(__file__))
    for root, dirs, _ in _os.walk(plugin_dir):
        for d in dirs:
            if d == '__pycache__':
                path = _os.path.join(root, d)
                try:
                    _shutil.rmtree(path)
                except OSError:
                    pass   # droits insuffisants — ignoré silencieusement


_clear_pycache()
_importlib.invalidate_caches()   # notifie Python des changements sur le disque


def classFactory(iface):
    """
    Fonction requise par QGIS pour instancier le plugin.

    :param iface: Instance de QgisInterface fournie par QGIS,
                  permettant d'interagir avec l'application
                  (menus, barres d'outils, canvas, etc.)
    :type iface:  QgisInterface
    :return:      Instance du plugin
    :rtype:       GeoFixerPlugin
    """
    from .geo_fixer_plugin import GeoFixerPlugin
    return GeoFixerPlugin(iface)
