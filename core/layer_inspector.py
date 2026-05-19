# -*- coding: utf-8 -*-
"""
Inspection d'une couche vectorielle pour détecter les entités problématiques.

Une entité est considérée "problématique" si :
  1. Sa géométrie est nulle ou vide
  2. Sa géométrie se trouve entièrement hors de l'emprise du SCR courant

Détection des types de champs par valeurs (et non par métadonnées déclarées) :
  _detect_field_types() échantillonne les données réelles pour classer chaque
  champ en "numeric", "wkt" ou "other". Cela est plus robuste pour les formats
  comme CSV où les métadonnées de type ne sont pas fiables.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum number of features inspected for problem detection
MAX_FEATURES_INSPECT = 50_000

# Number of features sampled for field type detection
SAMPLE_SIZE_TYPES = 100

# Fraction threshold of convertible values to classify a field as numeric
NUMERIC_THRESHOLD = 0.5


# ===========================================================================
# Data structures
# ===========================================================================

@dataclass
class ProblematicFeature:
    """
    Représente une entité avec un problème de géométrie.

    Attributes:
        feature_id  : identifiant QGIS (QgsFeature.id())
        reason      : code du problème ("no_geometry" | "outside_crs" | "ok")
        reason_label: libellé affiché dans le tableau
        attributes  : dictionnaire {nom_champ: valeur_str} pour affichage
    """
    feature_id:   int
    reason:       str
    reason_label: str
    attributes:   dict = field(default_factory=dict)


# Keywords recognised as valid WKT prefixes (ISO 19125)
_WKT_KEYWORDS = frozenset([
    "POINT", "LINESTRING", "POLYGON",
    "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON",
    "GEOMETRYCOLLECTION", "CIRCULARSTRING", "COMPOUNDCURVE",
    "CURVEPOLYGON", "MULTICURVE", "MULTISURFACE",
])

# Nombre minimum de valeurs WKT valides pour classer un champ comme WKT
WKT_MIN_HITS = 2


@dataclass
class FieldTypeInfo:
    """
    Résultat de la détection de type d'un champ par échantillonnage de ses valeurs.

    Attributes:
        is_numeric : True si les valeurs sont majoritairement convertibles en float
        is_wkt     : True si au moins WKT_MIN_HITS valeurs parsent comme WKT
                     ET commencent par un mot-clé WKT reconnu
        n_sampled  : nombre de valeurs lues pendant l'échantillonnage
    """
    is_numeric: bool = False
    is_wkt:     bool = False
    n_sampled:  int  = 0


# ===========================================================================
# Field type detection by sampling values
# ===========================================================================

def detect_field_types_by_values(layer) -> Dict[str, FieldTypeInfo]:
    """
    Détermine le type effectif de chaque champ en lisant les valeurs réelles
    d'un échantillon d'entités.

    Stratégie par champ :
      - Numérique : on tente float(valeur) pour chaque valeur non-nulle.
        Si la fraction de succès ≥ NUMERIC_THRESHOLD → is_numeric = True.
      - WKT : on tente QgsGeometry.fromWkt(str(valeur)).
        Si au moins une valeur parse en géométrie valide → is_wkt = True.

    Avantage vs. inspection du type déclaré :
      Les CSV et certains formats DBF déclarent tout en String même pour
      des colonnes de coordonnées. Cette approche fonctionne indépendamment
      des métadonnées de format.

    :param layer: QgsVectorLayer à inspecter
    :return:      Dict {nom_champ: FieldTypeInfo}
    """
    try:
        from qgis.core import QgsGeometry, QgsFeatureRequest
    except ImportError:
        return {}

    field_names = [f.name() for f in layer.fields()]
    result: Dict[str, FieldTypeInfo] = {name: FieldTypeInfo() for name in field_names}

    # Intermediate counters for the numeric success rate calculation
    numeric_total:   Dict[str, int] = {n: 0 for n in field_names}
    numeric_success: Dict[str, int] = {n: 0 for n in field_names}

    # Read a sample of features
    request = QgsFeatureRequest().setLimit(SAMPLE_SIZE_TYPES)
    n_read  = 0

    try:
        for feat in layer.getFeatures(request):
            n_read += 1
            for fname in field_names:
                raw = feat[fname]

                # NULL value → ignored (not counted in the total)
                if raw is None:
                    continue
                if hasattr(raw, '__class__') and raw.__class__.__name__ == 'QPyNullVariant':
                    continue

                val_str = str(raw).strip()
                if not val_str:
                    continue

                # ── Numeric test ─────────────────────────────────────────
                numeric_total[fname] += 1
                try:
                    fval = float(val_str.replace(',', '.'))
                    # Reject NaN and Inf (not valid coordinate values)
                    if fval == fval and abs(fval) != float('inf'):
                        numeric_success[fname] += 1
                except (ValueError, TypeError):
                    pass

                # ── Test WKT ─────────────────────────────────────────────
                # Strict criteria to avoid false positives:
                #   1. The value must start with a recognised WKT keyword
                #   2. It must parse as a valid QGIS geometry
                #   3. Au moins WKT_MIN_HITS valeurs doivent satisfaire 1 + 2
                upper_start = val_str.upper().split('(', 1)[0].strip()
                if upper_start in _WKT_KEYWORDS:
                    try:
                        geom = QgsGeometry.fromWkt(val_str)
                        if geom is not None and not geom.isNull():
                            # Increment a counter (temporarily stored in n_sampled)
                            if not hasattr(result[fname], '_wkt_hits'):
                                result[fname].__dict__['_wkt_hits'] = 0
                            result[fname].__dict__['_wkt_hits'] += 1
                    except Exception:
                        pass

    except Exception as exc:
        logger.warning("GeoFixer : erreur lors de l'échantillonnage des champs : %s", exc)

    # ── Calculer is_numeric et is_wkt pour chaque champ ──────────────────
    for fname in field_names:
        total = numeric_total[fname]
        if total > 0:
            ratio = numeric_success[fname] / total
            result[fname].is_numeric = (ratio >= NUMERIC_THRESHOLD)
        result[fname].n_sampled = n_read
        # is_wkt: true only if at least WKT_MIN_HITS valid values were detected
        wkt_hits = result[fname].__dict__.pop('_wkt_hits', 0)
        result[fname].is_wkt = (wkt_hits >= WKT_MIN_HITS)

    logger.debug(
        "GeoFixer : types détectés sur %d entités — %d champs numériques, %d WKT.",
        n_read,
        sum(1 for v in result.values() if v.is_numeric),
        sum(1 for v in result.values() if v.is_wkt),
    )
    return result


# ===========================================================================
# Problematic feature inspection
# ===========================================================================

def find_problematic_features(
    layer,
    crs=None,
    include_ok:      bool = False,
    display_fields:  Optional[List[str]] = None,
) -> List[ProblematicFeature]:
    """
    Parcourt la couche et retourne les entités problématiques.

    Stratégie de comparaison d'emprise :
      Les bounds du SCR cible (toujours en WGS84) sont transformés dans
      le SCR natif de la couche. Les bbox des entités sont ensuite comparées
      à ce rectangle de référence — sans aucune copie ni transformation de
      géométrie individuelle.

    :param layer:         QgsVectorLayer à inspecter
    :param crs:           SCR de référence (ses bounds définissent la zone valide).
                          Si None, seules les géométries nulles sont signalées.
    :param include_ok:    Si True, inclut aussi les entités sans problème.
    :param display_fields: Champs à inclure dans `attributes`. Si None : 6 premiers.
    :return: Liste de ProblematicFeature triée par feature_id.
    """
    # ── Columns to display ────────────────────────────────────────────────
    all_field_names = [f.name() for f in layer.fields()]
    if display_fields is not None:
        show_fields = [f for f in display_fields if f in all_field_names]
    else:
        show_fields = all_field_names[:6]

    # ── Prepare the reference rectangle in the layer's native CRS ─────────
    #
    # On transforme les bounds WGS84 du SCR cible vers le SCR de la couche.
    # Avantage : une seule transformation de rectangle, pas N transformations
    # individual geometries.
    #
    # Important : on utilise contains() et non intersects() pour rejeter les
    # layers where only part of the extent exceeds the bounds —
    # which clearly signals a CRS that is inconsistent with the data.
    crs_bounds_native = None
    layer_crs = layer.crs()

    if crs is not None and crs.isValid():
        try:
            from qgis.core import (
                QgsCoordinateReferenceSystem,
                QgsCoordinateTransform, QgsProject,
            )
            wgs84  = QgsCoordinateReferenceSystem("EPSG:4326")
            bounds = crs.bounds()   # toujours en WGS84

            if not bounds.isNull() and bounds.width() > 0:
                if layer_crs.isValid() and layer_crs.authid() != "EPSG:4326":
                    xform = QgsCoordinateTransform(
                        wgs84, layer_crs, QgsProject.instance()
                    )
                    crs_bounds_native = xform.transformBoundingBox(bounds)
                else:
                    crs_bounds_native = bounds
        except Exception:
            crs_bounds_native = None

    # ── Iterate over features ─────────────────────────────────────────────
    results: List[ProblematicFeature] = []
    count   = 0

    try:
        for feat in layer.getFeatures():
            count += 1
            if count > MAX_FEATURES_INSPECT:
                logger.warning(
                    "GeoFixer : inspection stoppée à %d entités (limite de sécurité).",
                    MAX_FEATURES_INSPECT
                )
                break

            fid  = feat.id()
            geom = feat.geometry()

            # Attributes to display
            attrs: dict = {}
            for fname in show_fields:
                val = feat[fname]
                if val is None or (hasattr(val, '__class__')
                                   and val.__class__.__name__ == 'QPyNullVariant'):
                    attrs[fname] = ""
                else:
                    attrs[fname] = str(val)

            # ── Test 1: missing geometry ──────────────────────────────────
            if geom is None or geom.isNull() or geom.isEmpty():
                results.append(ProblematicFeature(
                    feature_id=fid,
                    reason="no_geometry",
                    reason_label="Sans géométrie",
                    attributes=attrs,
                ))
                continue

            # ── Test 2: geometry outside CRS extent ───────────────────────
            # Compare the feature's bbox (in native coordinates) with
            # the reference rectangle transformed into the same CRS.
            if crs_bounds_native is not None:
                bbox = geom.boundingBox()
                if not crs_bounds_native.intersects(bbox):
                    results.append(ProblematicFeature(
                        feature_id=fid,
                        reason="outside_crs",
                        reason_label="Hors emprise SCR",
                        attributes=attrs,
                    ))
                    continue

            # ── Valid feature (included only if requested) ─────────────────
            if include_ok:
                results.append(ProblematicFeature(
                    feature_id=fid,
                    reason="ok",
                    reason_label="",
                    attributes=attrs,
                ))

    except Exception as exc:
        logger.exception("GeoFixer : erreur lors de l'inspection : %s", exc)

    results.sort(key=lambda pf: pf.feature_id)
    logger.debug(
        "GeoFixer : %d entités inspectées, %d problèmes détectés.",
        count, sum(1 for r in results if r.reason != "ok")
    )
    return results


def is_csv_layer(layer) -> bool:
    """
    Détecte si une couche est chargée depuis un CSV (provider 'delimitedtext').

    :param layer: QgsVectorLayer
    :return:      True si la couche est un CSV
    """
    if layer is None:
        return False
    provider_name = layer.dataProvider().name() if layer.dataProvider() else ""
    if provider_name == "delimitedtext":
        return True
    source = layer.source().lower()
    return source.endswith('.csv') or '.csv?' in source
