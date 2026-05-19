# -*- coding: utf-8 -*-
"""
Application des corrections de géométrie sur des entités vectorielles QGIS.

Trois modes de correction sont disponibles :

  1. Reprojection
     Transforme mathématiquement les coordonnées des entités sélectionnées
     depuis le SCR source vers un SCR cible.
     → Les coordonnées changent, mais représentent le même endroit géographique.

  2. Depuis champs Longitude / Latitude → Point
     Crée une géométrie Point en lisant deux champs numériques (lon, lat).
     → Utile quand les coordonnées sont dans les attributs mais pas en géométrie.

  3. Depuis champ WKT
     Crée une géométrie en parsant un champ contenant du WKT (Well-Known Text).
     → Supporte tous les types géométriques (Point, LineString, Polygon...).

Cas spécial CSV :
  Les couches chargées depuis un CSV avec le provider 'delimitedtext' ne
  supportent pas l'édition de géométrie via l'API QGIS standard. Pour ces
  couches, une nouvelle couche en mémoire est créée avec les géométries
  reconstruites, et ajoutée au projet QGIS.
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ===========================================================================
# API publique — fonctions de correction
# ===========================================================================

def apply_crs_to_layer(layer, crs) -> Optional[str]:
    """
    Déclare un nouveau SCR sur une couche sans reprojeter ses coordonnées.

    Cas d'usage : la couche a des coordonnées correctes mais le SCR est
    mal renseigné (ou absent). On corrige uniquement le métadonnées du SCR.

    :param layer: QgsVectorLayer cible
    :param crs:   QgsCoordinateReferenceSystem à appliquer
    :return:      Message d'erreur (str) ou None si succès
    """
    if layer is None:
        return "Aucune couche sélectionnée."
    if crs is None or not crs.isValid():
        return "Le SCR sélectionné est invalide."
    try:
        layer.setCrs(crs)
        logger.info(
            "GeoFixer : SCR '%s' appliqué à la couche '%s'.",
            crs.authid(), layer.name()
        )
        return None
    except Exception as exc:
        logger.exception("GeoFixer : erreur lors de l'application du SCR.")
        return f"Erreur lors de l'application du SCR : {exc}"


def reproject_features(
    layer,
    feature_ids: List[int],
    source_crs,
    target_crs,
) -> Tuple[int, int, Optional[str]]:
    """
    Reprojette les géométries des entités spécifiées vers un nouveau SCR.

    Les coordonnées sont transformées mathématiquement :
    l'entité représente le même endroit géographique, mais dans un autre SCR.

    Étapes :
      1. Ouvrir la couche en mode édition (startEditing)
      2. Transformer chaque géométrie via QgsCoordinateTransform
      3. Écrire les nouvelles géométries (changeGeometry)
      4. Valider les modifications (commitChanges)
      5. Mettre à jour le SCR déclaré de la couche

    :param layer:       QgsVectorLayer cible (doit être éditable)
    :param feature_ids: Liste des IDs d'entités à reprojeter
    :param source_crs:  SCR source (celui de la couche avant correction)
    :param target_crs:  SCR cible (vers lequel reprojeter)
    :return:            (nb_succès, nb_erreurs, message_erreur_ou_None)
    """
    if not feature_ids:
        return 0, 0, "Aucune entité sélectionnée."

    error = _check_editable(layer)
    if error:
        return 0, 0, error

    try:
        from qgis.core import QgsCoordinateTransform, QgsProject
        xform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
    except Exception as exc:
        return 0, 0, f"Impossible de créer la transformation de coordonnées : {exc}"

    n_ok = 0
    n_err = 0

    try:
        if not layer.isEditable():
            layer.startEditing()

        for fid in feature_ids:
            feat = layer.getFeature(fid)
            if not feat.isValid():
                n_err += 1
                continue

            geom = feat.geometry()
            if geom is None or geom.isNull():
                n_err += 1
                continue

            try:
                # transform() modifies geometry in-place → use the copy constructor
                new_geom = QgsGeometry(geom)
                new_geom.transform(xform)
                if layer.changeGeometry(fid, new_geom):
                    n_ok += 1
                else:
                    n_err += 1
            except Exception:
                n_err += 1

        # Valider les modifications
        if not layer.commitChanges():
            layer.rollBack()
            return 0, len(feature_ids), "Échec de la validation des modifications (commitChanges)."

        # Update the declared CRS and recompute the extent
        # (required for step 1 to reflect the new coordinates)
        layer.setCrs(target_crs)
        layer.updateExtents()
        layer.triggerRepaint()

    except Exception as exc:
        try:
            layer.rollBack()
        except Exception:
            pass
        logger.exception("GeoFixer : erreur lors de la reprojection.")
        return 0, len(feature_ids), f"Erreur lors de la reprojection : {exc}"

    logger.info(
        "GeoFixer : reprojection terminée — %d succès, %d erreurs.", n_ok, n_err
    )
    return n_ok, n_err, None


def build_geometry_from_lonlat(
    layer,
    feature_ids: List[int],
    lon_field: str,
    lat_field: str,
    crs=None,
    target_crs=None,
) -> Tuple[int, int, Optional[str]]:
    """
    Crée ou remplace des géométries Point depuis des champs Longitude/Latitude.

    :param layer:       QgsVectorLayer cible (doit être éditable)
    :param feature_ids: Liste des IDs d'entités à corriger
    :param lon_field:   Nom du champ contenant la longitude (X)
    :param lat_field:   Nom du champ contenant la latitude (Y)
    :param crs:         SCR source des coordonnées (pour la géométrie construite)
    :param target_crs:  Si fourni, reprojeter la géométrie de crs → target_crs
    :return:            (nb_succès, nb_erreurs, message_erreur_ou_None)
    """
    if not feature_ids:
        return 0, 0, "Aucune entité sélectionnée."
    if not lon_field or not lat_field:
        return 0, 0, "Les champs Longitude et Latitude doivent être sélectionnés."

    error = _check_editable(layer)
    if error:
        return 0, 0, error

    try:
        from qgis.core import QgsGeometry, QgsPointXY, QgsCoordinateTransform, QgsProject
    except ImportError as exc:
        return 0, 0, f"Import QGIS impossible : {exc}"

    # Prepare the optional crs → target_crs transformation
    xform_to_target = None
    if (target_crs is not None and target_crs.isValid()
            and crs is not None and crs.isValid()):
        try:
            xform_to_target = QgsCoordinateTransform(
                crs, target_crs, QgsProject.instance()
            )
        except Exception:
            xform_to_target = None

    n_ok = 0
    n_err = 0

    try:
        if not layer.isEditable():
            layer.startEditing()

        for fid in feature_ids:
            feat = layer.getFeature(fid)
            if not feat.isValid():
                n_err += 1
                continue

            try:
                raw_x = feat[lon_field]
                raw_y = feat[lat_field]

                x = _to_float(raw_x)
                y = _to_float(raw_y)

                if x is None or y is None:
                    n_err += 1
                    continue

                geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                # Reprojection optionnelle : SCR source → SCR couche
                if xform_to_target is not None:
                    geom.transform(xform_to_target)
                if layer.changeGeometry(fid, geom):
                    n_ok += 1
                else:
                    n_err += 1

            except Exception:
                n_err += 1

        if not layer.commitChanges():
            layer.rollBack()
            return 0, len(feature_ids), "Échec de la validation des modifications (commitChanges)."

        # Apply the declared CRS (= target_crs if provided, else crs)
        final_crs = target_crs if target_crs is not None else crs
        if final_crs is not None and final_crs.isValid():
            layer.setCrs(final_crs)

        layer.triggerRepaint()

    except Exception as exc:
        try:
            layer.rollBack()
        except Exception:
            pass
        logger.exception("GeoFixer : erreur lors de la création de géométrie lon/lat.")
        return 0, len(feature_ids), f"Erreur : {exc}"

    logger.info(
        "GeoFixer : lon/lat → géométrie — %d succès, %d erreurs.", n_ok, n_err
    )
    return n_ok, n_err, None


def build_geometry_from_wkt(
    layer,
    feature_ids: List[int],
    wkt_field: str,
    crs=None,
    target_crs=None,
) -> Tuple[int, int, Optional[str]]:
    """
    Crée ou remplace des géométries depuis un champ WKT (Well-Known Text).

    Supporte tous les types géométriques (Point, LineString, Polygon,
    MultiPoint, MultiLineString, MultiPolygon, GeometryCollection).

    :param layer:       QgsVectorLayer cible (doit être éditable)
    :param feature_ids: Liste des IDs d'entités à corriger
    :param wkt_field:   Nom du champ contenant la chaîne WKT
    :param crs:         SCR à appliquer à la couche après correction (optionnel)
    :return:            (nb_succès, nb_erreurs, message_erreur_ou_None)
    """
    if not feature_ids:
        return 0, 0, "Aucune entité sélectionnée."
    if not wkt_field:
        return 0, 0, "Le champ WKT doit être sélectionné."

    error = _check_editable(layer)
    if error:
        return 0, 0, error

    try:
        from qgis.core import QgsGeometry, QgsCoordinateTransform, QgsProject
    except ImportError as exc:
        return 0, 0, f"Import QGIS impossible : {exc}"

    xform_to_target = None
    if (target_crs is not None and target_crs.isValid()
            and crs is not None and crs.isValid()):
        try:
            xform_to_target = QgsCoordinateTransform(
                crs, target_crs, QgsProject.instance()
            )
        except Exception:
            xform_to_target = None

    n_ok = 0
    n_err = 0

    try:
        if not layer.isEditable():
            layer.startEditing()

        for fid in feature_ids:
            feat = layer.getFeature(fid)
            if not feat.isValid():
                n_err += 1
                continue

            try:
                raw_wkt = feat[wkt_field]
                if raw_wkt is None or str(raw_wkt).strip() == "":
                    n_err += 1
                    continue

                geom = QgsGeometry.fromWkt(str(raw_wkt).strip())
                if geom is None or geom.isNull():
                    n_err += 1
                    continue

                if xform_to_target is not None:
                    geom.transform(xform_to_target)

                if layer.changeGeometry(fid, geom):
                    n_ok += 1
                else:
                    n_err += 1

            except Exception:
                n_err += 1

        if not layer.commitChanges():
            layer.rollBack()
            return 0, len(feature_ids), "Échec de la validation des modifications (commitChanges)."

        final_crs = target_crs if target_crs is not None else crs
        if final_crs is not None and final_crs.isValid():
            layer.setCrs(final_crs)

        layer.triggerRepaint()

    except Exception as exc:
        try:
            layer.rollBack()
        except Exception:
            pass
        logger.exception("GeoFixer : erreur lors de la création de géométrie WKT.")
        return 0, len(feature_ids), f"Erreur : {exc}"

    logger.info(
        "GeoFixer : WKT → géométrie — %d succès, %d erreurs.", n_ok, n_err
    )
    return n_ok, n_err, None


def build_memory_layer_from_lonlat(
    source_layer,
    lon_field: str,
    lat_field: str,
    crs,
) -> Tuple[Optional[object], Optional[str]]:
    """
    Cas spécial CSV : crée une nouvelle couche en mémoire avec des géométries
    Point construites depuis des champs de coordonnées.

    Utilisé pour les couches dont le provider ne supporte pas l'édition de
    géométrie (ex : couches 'delimitedtext' chargées sans géométrie).

    La nouvelle couche reprend tous les champs attributaires de la source.
    Elle est ajoutée au projet QGIS et la source reste intacte.

    :param source_layer: QgsVectorLayer source (CSV)
    :param lon_field:    Nom du champ contenant la longitude
    :param lat_field:    Nom du champ contenant la latitude
    :param crs:          SCR de la nouvelle couche
    :return:             (nouvelle_couche_ou_None, message_erreur_ou_None)
    """
    if not lon_field or not lat_field:
        return None, "Les champs Longitude et Latitude doivent être sélectionnés."

    try:
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
            QgsProject,
        )

        # ── Build the memory layer URI ─────────────────────────────────────
        crs_auth = crs.authid() if (crs and crs.isValid()) else "EPSG:4326"
        uri = f"Point?crs={crs_auth}"
        new_layer = QgsVectorLayer(uri, source_layer.name() + " [géo]", "memory")
        if not new_layer.isValid():
            return None, "Impossible de créer la couche en mémoire."

        # ── Copier les champs de la couche source ───────────────────────────
        prov = new_layer.dataProvider()
        prov.addAttributes(source_layer.fields().toList())
        new_layer.updateFields()

        # ── Copy features with the reconstructed geometries ─────────────────
        new_layer.startEditing()
        n_ok = 0
        n_err = 0

        for feat in source_layer.getFeatures():
            raw_x = feat[lon_field]
            raw_y = feat[lat_field]
            x = _to_float(raw_x)
            y = _to_float(raw_y)

            new_feat = QgsFeature(new_layer.fields())
            new_feat.setAttributes(feat.attributes())

            if x is not None and y is not None:
                new_feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                n_ok += 1
            else:
                # Null geometry → still include the feature (without geometry)
                n_err += 1

            prov.addFeature(new_feat)

        new_layer.commitChanges()
        new_layer.updateExtents()

        # ── Ajouter la nouvelle couche au projet ─────────────────────────────
        QgsProject.instance().addMapLayer(new_layer)

        logger.info(
            "GeoFixer CSV : nouvelle couche '%s' créée — %d géométries OK, %d sans coordonnées.",
            new_layer.name(), n_ok, n_err
        )
        return new_layer, None

    except Exception as exc:
        logger.exception("GeoFixer : erreur lors de la création de la couche mémoire CSV.")
        return None, f"Erreur : {exc}"


def build_memory_layer_from_wkt(
    source_layer,
    wkt_field: str,
    crs,
) -> Tuple[Optional[object], Optional[str]]:
    """
    Cas spécial CSV : crée une nouvelle couche en mémoire avec des géométries
    issues d'un champ WKT.

    :param source_layer: QgsVectorLayer source (CSV)
    :param wkt_field:    Nom du champ contenant les chaînes WKT
    :param crs:          SCR de la nouvelle couche
    :return:             (nouvelle_couche_ou_None, message_erreur_ou_None)
    """
    if not wkt_field:
        return None, "Le champ WKT doit être sélectionné."

    try:
        from qgis.core import (
            QgsVectorLayer, QgsFeature, QgsGeometry, QgsProject,
        )

        # Determine the geometry type by reading the first valid WKT value
        geom_type_uri = _detect_wkt_geom_type(source_layer, wkt_field)
        crs_auth = crs.authid() if (crs and crs.isValid()) else "EPSG:4326"
        uri = f"{geom_type_uri}?crs={crs_auth}"

        new_layer = QgsVectorLayer(uri, source_layer.name() + " [géo]", "memory")
        if not new_layer.isValid():
            return None, "Impossible de créer la couche en mémoire."

        prov = new_layer.dataProvider()
        prov.addAttributes(source_layer.fields().toList())
        new_layer.updateFields()

        new_layer.startEditing()
        n_ok = 0
        n_err = 0

        for feat in source_layer.getFeatures():
            raw_wkt = feat[wkt_field]
            new_feat = QgsFeature(new_layer.fields())
            new_feat.setAttributes(feat.attributes())

            if raw_wkt and str(raw_wkt).strip():
                geom = QgsGeometry.fromWkt(str(raw_wkt).strip())
                if geom and not geom.isNull():
                    new_feat.setGeometry(geom)
                    n_ok += 1
                else:
                    n_err += 1
            else:
                n_err += 1

            prov.addFeature(new_feat)

        new_layer.commitChanges()
        new_layer.updateExtents()
        QgsProject.instance().addMapLayer(new_layer)

        logger.info(
            "GeoFixer CSV WKT : nouvelle couche '%s' créée — %d géométries OK, %d erreurs.",
            new_layer.name(), n_ok, n_err
        )
        return new_layer, None

    except Exception as exc:
        logger.exception("GeoFixer : erreur lors de la création de la couche mémoire WKT.")
        return None, f"Erreur : {exc}"


# ===========================================================================
# Private utilities
# ===========================================================================

def _check_editable(layer) -> Optional[str]:
    """
    Vérifie que la couche peut être mise en édition.

    :return: Message d'erreur si la couche n'est pas éditable, sinon None.
    """
    if layer is None:
        return "Aucune couche sélectionnée."
    if not layer.isValid():
        return "La couche n'est pas valide."
    from .qt_compat import _QVDataProvider_ChangeGeometries
    if not (layer.dataProvider().capabilities() & _QVDataProvider_ChangeGeometries):
        return (
            "Le format de cette couche ne supporte pas l'édition de géométrie.\n"
            "Pour un fichier CSV, utilisez le mode de création d'une nouvelle couche."
        )
    return None


def _to_float(value) -> Optional[float]:
    """
    Convertit une valeur attributaire en float.

    Gère les types int, float, str et les valeurs NULL QGIS.

    :return: float ou None si la conversion échoue.
    """
    from .qt_compat import _is_null
    if _is_null(value):
        return None
    try:
        result = float(value)
        # Rejeter NaN et Inf
        if result != result or abs(result) == float('inf'):
            return None
        return result
    except (ValueError, TypeError):
        return None


def _detect_wkt_geom_type(layer, wkt_field: str) -> str:
    """
    Détecte le type géométrique principal d'un champ WKT en lisant
    les premières entités valides.

    :return: Type géométrique pour l'URI mémoire (ex: "Point", "Polygon")
    """
    # Common types to detect, in priority order
    type_map = {
        "GEOMETRYCOLLECTION": "GeometryCollection",
        "MULTIPOLYGON":       "MultiPolygon",
        "MULTILINESTRING":    "MultiLineString",
        "MULTIPOINT":         "MultiPoint",
        "POLYGON":            "Polygon",
        "LINESTRING":         "LineString",
        "POINT":              "Point",
    }
    try:
        from qgis.core import QgsFeatureRequest
        for feat in layer.getFeatures(QgsFeatureRequest().setLimit(20)):
            raw = feat[wkt_field]
            if raw and str(raw).strip():
                upper = str(raw).strip().upper()
                for keyword, geom_type in type_map.items():
                    if upper.startswith(keyword):
                        return geom_type
    except Exception:
        pass
    return "Point"   # Safe fallback
