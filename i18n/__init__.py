# -*- coding: utf-8 -*-
"""
Système de traduction du plugin GeoFixer.

Utilise des dictionnaires Python plutôt que les fichiers binaires .qm Qt,
ce qui évite toute dépendance aux outils Qt (lupdate/lrelease) et permet
de déployer les traductions simplement dans le ZIP du plugin.

Langues supportées :
  fr — Français   (langue source interne)
  en — English    (langue d'interface par défaut)
  en — English
  de — Deutsch
  es — Español
  pt — Português
  it — Italiano

Usage dans le code :
    from .i18n import tr
    label = QLabel(tr("Couche :"))

La langue est détectée automatiquement depuis les paramètres régionaux de QGIS.
Elle peut être forcée via set_language(code) pour les tests.
"""

from .translations import TRANSLATIONS

# Active language (2-letter ISO 639-1 code)
_current_lang: str = "en"


# All supported language codes: "fr" is the source language (no dict entry needed).
_SUPPORTED_LANGUAGES: frozenset = frozenset(TRANSLATIONS.keys()) | {"fr"}


def detect_language() -> str:
    """
    Detect the active language from QGIS settings.

    Priority order:
      1. QGIS setting  locale/userLocale  (e.g. "fr_FR", "en_US")
      2. Qt system locale
      3. Fallback to "en" (default interface language)

    Note: "fr" is the source language. tr() returns the source string
    unchanged when the active language is "fr", so no translation dict
    entry is needed for French.

    :return: ISO 639-1 two-letter language code ("fr", "en", "de", etc.)
    """
    try:
        from qgis.PyQt.QtCore import QSettings, QLocale
        raw = QSettings().value("locale/userLocale", "")
        if not raw:
            raw = QLocale.system().name()
        lang = raw[:2].lower()
        if lang in _SUPPORTED_LANGUAGES:
            return lang
    except Exception:
        pass
    return "en"


def set_language(code: str) -> None:
    """
    Force the active language (useful for tests or a preferences option).

    :param code: ISO 639-1 language code ("fr", "en", "de", "es", "pt", "it")
    """
    global _current_lang
    if code in _SUPPORTED_LANGUAGES:
        _current_lang = code


def init() -> None:
    """
    Initialise la langue depuis les paramètres QGIS.
    À appeler une fois dans GeoFixerPlugin.initGui().
    """
    global _current_lang
    _current_lang = detect_language()


def tr(text: str) -> str:
    """
    Traduit une chaîne dans la langue active.

    Ordre de repli :
      1. Traduction dans la langue active
      2. Traduction anglaise (langue par défaut de l'interface)
      3. Chaîne source française (jamais vide)

    :param text: Chaîne source en français
    :return:     Chaîne traduite
    """
    if _current_lang == "fr":
        return text
    # Chercher dans la langue active
    result = TRANSLATIONS.get(_current_lang, {}).get(text)
    if result is not None:
        return result
    # English fallback (default interface language)
    if _current_lang != "en":
        result = TRANSLATIONS.get("en", {}).get(text)
        if result is not None:
            return result
    # Final fallback: French source string
    return text
