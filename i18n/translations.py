# -*- coding: utf-8 -*-
"""
Dictionnaires de traduction pour GeoFixer.

Clé   = chaîne source en français
Valeur = traduction dans la langue cible

Conventions :
  - Les accolades {var} sont conservées identiques dans toutes les langues.
  - Les séquences d'échappement (\\n, \\t) sont conservées.
  - Les emojis (📁, 🔍, ●, ←, →) sont conservés.
  - Les noms propres (QGIS, Shapefile, GeoPackage, WKT, SCR/CRS, OGR, etc.)
    ne sont pas traduits dans les langues où ils sont universels.
"""

TRANSLATIONS: dict = {

    # ==========================================================================
    # ENGLISH
    # ==========================================================================
    "en": {
        # ── Fenêtre principale ────────────────────────────────────────────────
        "GeoFixer — Correction de géométrie":
            "GeoFixer — Geometry Correction",
        "GeoFixer":
            "GeoFixer",
        "GeoFixer\n"
        "Corrige ou définit la géométrie d'entités vectorielles\n"
        "depuis des champs de coordonnées ou par reprojection.":
            "GeoFixer\n"
            "Corrects or defines geometry of vector features\n"
            "from coordinate fields or by reprojection.",

        # ── Barre d'étapes ────────────────────────────────────────────────────
        "● Étape 1 — Sélection et SCR":
            "● Step 1 — Selection and CRS",
        "● Étape 2 — Correction des entités":
            "● Step 2 — Feature Correction",
        "→": "→",
        "Étape suivante  →": "Next step  →",
        "←  Retour": "←  Back",

        # ── Étape 1 : Source de données ───────────────────────────────────────
        "Source de données": "Data Source",
        "Couche :": "Layer:",
        "ou": "or",
        "📁  Ouvrir un fichier…": "📁  Open a file…",
        "Ouvre un fichier vectoriel et le charge dans QGIS.":
            "Opens a vector file and loads it into QGIS.",
        "Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
        "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
        "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip":
            "Formats: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
            "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
            "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip",

        # ── Étape 1 : SCR ─────────────────────────────────────────────────────
        "Système de coordonnées de référence (SCR)":
            "Coordinate Reference System (CRS)",
        "SCR :": "CRS:",
        "Appliquer le SCR": "Apply CRS",
        "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
        "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi.":
            "Declares this CRS on the layer without reprojecting coordinates.\n"
            "Disabled if the layer extent exceeds the bounds of the chosen CRS.",

        # ── Sélection de couche (multi-couches) ───────────────────────────────
        "Sélection de couche": "Layer Selection",
        "Ouvrir un fichier vectoriel": "Open a vector file",
        "Enregistrer la copie Shapefile": "Save Shapefile copy",

        # ── Étape 2 : Tableau des entités ─────────────────────────────────────
        "Entités à corriger": "Features to correct",
        "Entités sans géométrie ou hors emprise SCR":
            "Features without geometry or outside CRS extent",
        "Toutes les entités": "All features",
        "Tout sélectionner": "Select all",
        "Désélectionner": "Deselect",
        "Aucune entité chargée.": "No features loaded.",
        "Raison": "Reason",
        "Sans géométrie": "No geometry",
        "Hors emprise SCR": "Outside CRS extent",
        "FID": "FID",

        # ── Étape 2 : Actions ─────────────────────────────────────────────────
        "Action à appliquer sur la sélection":
            "Action to apply to selection",
        "Reprojeter — les entités sont dans un SCR différent de la couche":
            "Reproject — features are in a different CRS than the layer",
        "SCR d'origine des entités :": "Source CRS of features:",
        "Définir la géométrie depuis des champs attributaires":
            "Define geometry from attribute fields",
        "Longitude / Latitude  →  Point": "Longitude / Latitude  →  Point",
        "Longitude :": "Longitude:",
        "Latitude :": "Latitude:",
        "Champ WKT (Well-Known Text)": "WKT field (Well-Known Text)",
        "Champ WKT :": "WKT field:",
        "Reprojeter les coordonnées vers le SCR de la couche":
            "Reproject coordinates to the layer CRS",
        "Si les coordonnées dans les champs sont dans un SCR différent\n"
        "de la couche, cochez cette case et indiquez le SCR source.":
            "If the coordinates in the fields are in a different CRS\n"
            "than the layer, check this box and specify the source CRS.",
        "SCR source des coordonnées :": "Source CRS of coordinates:",
        "🔍  Prévisualiser la transformation":
            "🔍  Preview transformation",
        "Appliquer les corrections": "Apply corrections",

        # ── Étape 2 : Messages résultat ───────────────────────────────────────
        "Aucune action sélectionnée.\n"
        "Choisissez « Reprojeter » ou « Définir depuis les champs ».":
            "No action selected.\n"
            "Choose 'Reproject' or 'Define from fields'.",
        "Aucune entité sélectionnée.\n"
        "Sélectionnez au moins une entité dans le tableau.":
            "No feature selected.\n"
            "Select at least one feature in the table.",

        # ── FieldConfigDialog ─────────────────────────────────────────────────
        "Types de champs": "Field types",
        "SCR et aperçu": "CRS and preview",
        "Aucune géométrie": "No geometry",
        "Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
        "Vous pourrez définir la géométrie à l'étape 2.":
            "No numeric (Integer/Real) or WKT field detected.\n"
            "You can define geometry at step 2.",

        # ── Boîtes de dialogue ────────────────────────────────────────────────
        "GeoFixer — Erreur": "GeoFixer — Error",
        "GeoFixer — Erreur export": "GeoFixer — Export error",
        "GeoFixer — Fichier verrouillé": "GeoFixer — File locked",
        "GeoFixer — Géométrie requise": "GeoFixer — Geometry required",
        "GeoFixer — Shapefile créé": "GeoFixer — Shapefile created",
        "GeoFixer — Couche CSV": "GeoFixer — CSV layer",
        "GeoFixer — Couche sans géométrie": "GeoFixer — Layer without geometry",
        "GeoFixer — Création Shapefile requise":
            "GeoFixer — Shapefile creation required",
        "(Canvas non disponible)": "(Canvas not available)",
        "Configuration des champs": "Field configuration",
        'Si les coordonnées dans les champs sont dans un SCR différent\nde la couche, cochez cette case et indiquez le SCR source.':
            "If the coordinates in the fields are in a different CRS\nthan the layer, check this box and specify the source CRS.",
        'Aucune action sélectionnée.\nChoisissez « Reprojeter » ou « Définir depuis les champs ».':
            "No action selected.\nChoose 'Reproject' or 'Define from fields'.",
        'Aucune entité sélectionnée.\nSélectionnez au moins une entité dans le tableau.':
            "No feature selected.\nSelect at least one feature in the table.",
        'Aucune couche sélectionnée.':
            'No layer selected.',
        '🔍  Prévisualiser':
            '🔍  Preview',
        'Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip':
            'Formats: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip',

        # ── Nouvelles chaînes (corr. bugs) ────────────────────────────────────
        "Colonnes numériques candidates (lon/lat) — {n} entité(s)":
            "Numeric candidate columns (lon/lat) — {n} feature(s)",
        "Colonnes WKT détectées — {n} entité(s)":
            "WKT columns detected — {n} feature(s)",
        "Aperçu — {n} entité(s)":
            "Preview — {n} feature(s)",
        "Le fichier <b>{filename}</b> contient {count} couche(s).<br>"
        "Sélectionnez la couche à traiter :":
            "The file <b>{filename}</b> contains {count} layer(s).<br>"
            "Select the layer to process:",
        "La couche « {name} » ne possède aucune géométrie.\n\n"
        "La fenêtre de configuration des champs va s'ouvrir. "
        "Définissez les types de champs et le mode géométrique "
        "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
        "Un Shapefile sera créé avec les géométries construites depuis les champs — "
        "vous pourrez corriger les éventuelles géométries manquantes à l'étape 2.":
            "The layer '{name}' has no geometry.\n\n"
            "The field configuration window will open. "
            "Set the field types and geometry mode "
            "(Lon/Lat or WKT), then preview to validate the CRS.\n\n"
            "A Shapefile will be created with geometries built from the fields — "
            "you can correct any missing geometries at step 2.",
        "Veuillez sélectionner ou ouvrir une couche avant de continuer.":
            "Please select or open a layer before continuing.",
        "{n_total} entité(s) listée(s)  —  {n_sel} sélectionnée(s).":
            "{n_total} feature(s) listed  —  {n_sel} selected.",
    },

    # ==========================================================================
    # DEUTSCH
    # ==========================================================================
    "de": {
        "GeoFixer — Correction de géométrie":
            "GeoFixer — Geometriekorrektur",
        "GeoFixer": "GeoFixer",
        "GeoFixer\n"
        "Corrige ou définit la géométrie d'entités vectorielles\n"
        "depuis des champs de coordonnées ou par reprojection.":
            "GeoFixer\n"
            "Korrigiert oder definiert die Geometrie von Vektorelementen\n"
            "aus Koordinatenfeldern oder durch Reprojektion.",

        "● Étape 1 — Sélection et SCR":
            "● Schritt 1 — Auswahl und KBS",
        "● Étape 2 — Correction des entités":
            "● Schritt 2 — Elementkorrektur",
        "→": "→",
        "Étape suivante  →": "Nächster Schritt  →",
        "←  Retour": "←  Zurück",

        "Source de données": "Datenquelle",
        "Couche :": "Layer:",
        "ou": "oder",
        "📁  Ouvrir un fichier…": "📁  Datei öffnen…",
        "Ouvre un fichier vectoriel et le charge dans QGIS.":
            "Öffnet eine Vektordatei und lädt sie in QGIS.",
        "Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
        "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
        "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip":
            "Formate: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
            "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
            "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip",

        "Système de coordonnées de référence (SCR)":
            "Koordinatenbezugssystem (KBS)",
        "SCR :": "KBS:",
        "Appliquer le SCR": "KBS anwenden",
        "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
        "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi.":
            "Deklariert dieses KBS auf dem Layer ohne Koordinaten zu reprojizieren.\n"
            "Deaktiviert, wenn die Layerausdehnung die Grenzen des gewählten KBS überschreitet.",

        "Sélection de couche": "Layerauswahl",
        "Ouvrir un fichier vectoriel": "Vektordatei öffnen",
        "Enregistrer la copie Shapefile": "Shapefile-Kopie speichern",

        "Entités à corriger": "Zu korrigierende Elemente",
        "Entités sans géométrie ou hors emprise SCR":
            "Elemente ohne Geometrie oder außerhalb der KBS-Ausdehnung",
        "Toutes les entités": "Alle Elemente",
        "Tout sélectionner": "Alle auswählen",
        "Désélectionner": "Auswahl aufheben",
        "Aucune entité chargée.": "Keine Elemente geladen.",
        "Raison": "Ursache",
        "Sans géométrie": "Ohne Geometrie",
        "Hors emprise SCR": "Außerhalb der KBS-Ausdehnung",
        "FID": "FID",

        "Action à appliquer sur la sélection":
            "Aktion für die Auswahl",
        "Reprojeter — les entités sont dans un SCR différent de la couche":
            "Reprojizieren — Elemente haben ein anderes KBS als der Layer",
        "SCR d'origine des entités :": "Ursprungs-KBS der Elemente:",
        "Définir la géométrie depuis des champs attributaires":
            "Geometrie aus Attributfeldern definieren",
        "Longitude / Latitude  →  Point": "Längengrad / Breitengrad  →  Punkt",
        "Longitude :": "Längengrad:",
        "Latitude :": "Breitengrad:",
        "Champ WKT (Well-Known Text)": "WKT-Feld (Well-Known Text)",
        "Champ WKT :": "WKT-Feld:",
        "Reprojeter les coordonnées vers le SCR de la couche":
            "Koordinaten in das Layer-KBS reprojizieren",
        "SCR source des coordonnées :": "Quell-KBS der Koordinaten:",
        "🔍  Prévisualiser la transformation":
            "🔍  Transformation vorschau",
        "Appliquer les corrections": "Korrekturen anwenden",

        "Types de champs": "Feldtypen",
        "SCR et aperçu": "KBS und Vorschau",
        "Aucune géométrie": "Keine Geometrie",
        "Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
        "Vous pourrez définir la géométrie à l'étape 2.":
            "Kein numerisches (Integer/Real) oder WKT-Feld erkannt.\n"
            "Sie können die Geometrie in Schritt 2 definieren.",

        "GeoFixer — Erreur": "GeoFixer — Fehler",
        "GeoFixer — Erreur export": "GeoFixer — Exportfehler",
        "GeoFixer — Fichier verrouillé": "GeoFixer — Datei gesperrt",
        "GeoFixer — Géométrie requise": "GeoFixer — Geometrie erforderlich",
        "GeoFixer — Shapefile créé": "GeoFixer — Shapefile erstellt",
        "GeoFixer — Couche CSV": "GeoFixer — CSV-Layer",
        "GeoFixer — Couche sans géométrie": "GeoFixer — Layer ohne Geometrie",
        "GeoFixer — Création Shapefile requise":
            "GeoFixer — Shapefile-Erstellung erforderlich",
        "(Canvas non disponible)": "(Kartenansicht nicht verfügbar)",
        'Si les coordonnées dans les champs sont dans un SCR différent\nde la couche, cochez cette case et indiquez le SCR source.':
            'Wenn die Koordinaten in den Feldern ein anderes KBS haben\nals der Layer, aktivieren Sie dieses Feld und geben Sie das Quell-KBS an.',
        'Aucune action sélectionnée.\nChoisissez « Reprojeter » ou « Définir depuis les champs ».':
            'Keine Aktion ausgewählt.\nWählen Sie „Reprojizieren" oder „Aus Feldern definieren".',
        'Aucune entité sélectionnée.\nSélectionnez au moins une entité dans le tableau.':
            'Kein Element ausgewählt.\nWählen Sie mindestens ein Element in der Tabelle.',
        'Configuration des champs':
            'Feldkonfiguration',
        'Aucune couche sélectionnée.':
            'Kein Layer ausgewählt.',
        '🔍  Prévisualiser':
            '🔍  Vorschau',
        'Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip':
            'Formate: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip',

        # ── Nouvelles chaînes (corr. bugs) ────────────────────────────────────
        "Colonnes numériques candidates (lon/lat) — {n} entité(s)":
            "Numerische Kandidatenspalten (Lon/Lat) — {n} Element(e)",
        "Colonnes WKT détectées — {n} entité(s)":
            "WKT-Spalten erkannt — {n} Element(e)",
        "Aperçu — {n} entité(s)":
            "Vorschau — {n} Element(e)",
        "Le fichier <b>{filename}</b> contient {count} couche(s).<br>"
        "Sélectionnez la couche à traiter :":
            "Die Datei <b>{filename}</b> enthält {count} Layer.<br>"
            "Wählen Sie den zu verarbeitenden Layer:",
        "La couche « {name} » ne possède aucune géométrie.\n\n"
        "La fenêtre de configuration des champs va s'ouvrir. "
        "Définissez les types de champs et le mode géométrique "
        "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
        "Un Shapefile sera créé avec les géométries construites depuis les champs — "
        "vous pourrez corriger les éventuelles géométries manquantes à l'étape 2.":
            "Der Layer „{name}" besitzt keine Geometrie.\n\n"
            "Das Feldkonfigurationsfenster wird geöffnet. "
            "Legen Sie die Feldtypen und den Geometriemodus fest "
            "(Lon/Lat oder WKT), und erstellen Sie eine Vorschau, um das KBS zu bestätigen.\n\n"
            "Eine Shapefile wird mit den aus den Feldern erstellten Geometrien erzeugt — "
            "fehlende Geometrien können in Schritt 2 korrigiert werden.",
        "Veuillez sélectionner ou ouvrir une couche avant de continuer.":
            "Bitte wählen Sie einen Layer aus oder öffnen Sie eine Datei, bevor Sie fortfahren.",
        "{n_total} entité(s) listée(s)  —  {n_sel} sélectionnée(s).":
            "{n_total} Element(e) aufgelistet  —  {n_sel} ausgewählt.",
    },

    # ==========================================================================
    # ESPAÑOL
    # ==========================================================================
    "es": {
        "GeoFixer — Correction de géométrie":
            "GeoFixer — Corrección de geometría",
        "GeoFixer": "GeoFixer",
        "GeoFixer\n"
        "Corrige ou définit la géométrie d'entités vectorielles\n"
        "depuis des champs de coordonnées ou par reprojection.":
            "GeoFixer\n"
            "Corrige o define la geometría de entidades vectoriales\n"
            "desde campos de coordenadas o mediante reproyección.",

        "● Étape 1 — Sélection et SCR":
            "● Paso 1 — Selección y SRC",
        "● Étape 2 — Correction des entités":
            "● Paso 2 — Corrección de entidades",
        "→": "→",
        "Étape suivante  →": "Siguiente paso  →",
        "←  Retour": "←  Volver",

        "Source de données": "Fuente de datos",
        "Couche :": "Capa:",
        "ou": "o",
        "📁  Ouvrir un fichier…": "📁  Abrir un archivo…",
        "Ouvre un fichier vectoriel et le charge dans QGIS.":
            "Abre un archivo vectorial y lo carga en QGIS.",
        "Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
        "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
        "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip":
            "Formatos: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
            "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
            "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip",

        "Système de coordonnées de référence (SCR)":
            "Sistema de coordenadas de referencia (SRC)",
        "SCR :": "SRC:",
        "Appliquer le SCR": "Aplicar SRC",
        "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
        "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi.":
            "Declara este SRC en la capa sin reproyectar las coordenadas.\n"
            "Desactivado si la extensión de la capa supera los límites del SRC elegido.",

        "Sélection de couche": "Selección de capa",
        "Ouvrir un fichier vectoriel": "Abrir archivo vectorial",
        "Enregistrer la copie Shapefile": "Guardar copia Shapefile",

        "Entités à corriger": "Entidades a corregir",
        "Entités sans géométrie ou hors emprise SCR":
            "Entidades sin geometría o fuera del SRC",
        "Toutes les entités": "Todas las entidades",
        "Tout sélectionner": "Seleccionar todo",
        "Désélectionner": "Deseleccionar",
        "Aucune entité chargée.": "Ninguna entidad cargada.",
        "Raison": "Motivo",
        "Sans géométrie": "Sin geometría",
        "Hors emprise SCR": "Fuera del SRC",
        "FID": "FID",

        "Action à appliquer sur la sélection":
            "Acción a aplicar a la selección",
        "Reprojeter — les entités sont dans un SCR différent de la couche":
            "Reproyectar — las entidades tienen un SRC diferente al de la capa",
        "SCR d'origine des entités :": "SRC de origen de las entidades:",
        "Définir la géométrie depuis des champs attributaires":
            "Definir geometría desde campos de atributos",
        "Longitude / Latitude  →  Point": "Longitud / Latitud  →  Punto",
        "Longitude :": "Longitud:",
        "Latitude :": "Latitud:",
        "Champ WKT (Well-Known Text)": "Campo WKT (Well-Known Text)",
        "Champ WKT :": "Campo WKT:",
        "Reprojeter les coordonnées vers le SCR de la couche":
            "Reproyectar coordenadas al SRC de la capa",
        "SCR source des coordonnées :": "SRC de origen de las coordenadas:",
        "🔍  Prévisualiser la transformation":
            "🔍  Vista previa de la transformación",
        "Appliquer les corrections": "Aplicar correcciones",

        "Types de champs": "Tipos de campo",
        "SCR et aperçu": "SRC y vista previa",
        "Aucune géométrie": "Sin geometría",
        "Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
        "Vous pourrez définir la géométrie à l'étape 2.":
            "No se detectó ningún campo numérico (Integer/Real) ni WKT.\n"
            "Podrá definir la geometría en el paso 2.",

        "GeoFixer — Erreur": "GeoFixer — Error",
        "GeoFixer — Erreur export": "GeoFixer — Error de exportación",
        "GeoFixer — Fichier verrouillé": "GeoFixer — Archivo bloqueado",
        "GeoFixer — Géométrie requise": "GeoFixer — Geometría requerida",
        "GeoFixer — Shapefile créé": "GeoFixer — Shapefile creado",
        "GeoFixer — Couche CSV": "GeoFixer — Capa CSV",
        "GeoFixer — Couche sans géométrie": "GeoFixer — Capa sin geometría",
        "GeoFixer — Création Shapefile requise":
            "GeoFixer — Creación de Shapefile requerida",
        "(Canvas non disponible)": "(Lienzo no disponible)",
        'Si les coordonnées dans les champs sont dans un SCR différent\nde la couche, cochez cette case et indiquez le SCR source.':
            'Si las coordenadas en los campos tienen un SRC diferente\nal de la capa, marque esta casilla e indique el SRC de origen.',
        'Aucune action sélectionnée.\nChoisissez « Reprojeter » ou « Définir depuis les champs ».':
            'Ninguna acción seleccionada.\nElija «Reproyectar» o «Definir desde los campos».',
        'Aucune entité sélectionnée.\nSélectionnez au moins une entité dans le tableau.':
            'Ninguna entidad seleccionada.\nSeleccione al menos una entidad en la tabla.',
        'Configuration des champs':
            'Configuración de campos',
        'Aucune couche sélectionnée.':
            'Ninguna capa seleccionada.',
        '🔍  Prévisualiser':
            '🔍  Previsualizar',
        'Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip':
            'Formatos: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip',

        # ── Nouvelles chaînes (corr. bugs) ────────────────────────────────────
        "Colonnes numériques candidates (lon/lat) — {n} entité(s)":
            "Columnas numéricas candidatas (lon/lat) — {n} entidad(es)",
        "Colonnes WKT détectées — {n} entité(s)":
            "Columnas WKT detectadas — {n} entidad(es)",
        "Aperçu — {n} entité(s)":
            "Vista previa — {n} entidad(es)",
        "Le fichier <b>{filename}</b> contient {count} couche(s).<br>"
        "Sélectionnez la couche à traiter :":
            "El archivo <b>{filename}</b> contiene {count} capa(s).<br>"
            "Seleccione la capa a procesar:",
        "La couche « {name} » ne possède aucune géométrie.\n\n"
        "La fenêtre de configuration des champs va s'ouvrir. "
        "Définissez les types de champs et le mode géométrique "
        "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
        "Un Shapefile sera créé avec les géométries construites depuis les champs — "
        "vous pourrez corriger les éventuelles géométries manquantes à l'étape 2.":
            "La capa «{name}» no tiene geometría.\n\n"
            "Se abrirá la ventana de configuración de campos. "
            "Defina los tipos de campo y el modo de geometría "
            "(Lon/Lat o WKT), luego previsualice para validar el SRC.\n\n"
            "Se creará un Shapefile con las geometrías construidas desde los campos — "
            "podrá corregir las geometrías faltantes en el paso 2.",
        "Veuillez sélectionner ou ouvrir une couche avant de continuer.":
            "Seleccione o abra una capa antes de continuar.",
        "{n_total} entité(s) listée(s)  —  {n_sel} sélectionnée(s).":
            "{n_total} entidad(es) listada(s)  —  {n_sel} seleccionada(s).",
    },

    # ==========================================================================
    # PORTUGUÊS
    # ==========================================================================
    "pt": {
        "GeoFixer — Correction de géométrie":
            "GeoFixer — Correção de geometria",
        "GeoFixer": "GeoFixer",
        "GeoFixer\n"
        "Corrige ou définit la géométrie d'entités vectorielles\n"
        "depuis des champs de coordonnées ou par reprojection.":
            "GeoFixer\n"
            "Corrige ou define a geometria de feições vetoriais\n"
            "a partir de campos de coordenadas ou por reprojeção.",

        "● Étape 1 — Sélection et SCR":
            "● Etapa 1 — Seleção e SRC",
        "● Étape 2 — Correction des entités":
            "● Etapa 2 — Correção de feições",
        "→": "→",
        "Étape suivante  →": "Próxima etapa  →",
        "←  Retour": "←  Voltar",

        "Source de données": "Fonte de dados",
        "Couche :": "Camada:",
        "ou": "ou",
        "📁  Ouvrir un fichier…": "📁  Abrir arquivo…",
        "Ouvre un fichier vectoriel et le charge dans QGIS.":
            "Abre um arquivo vetorial e carrega no QGIS.",
        "Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
        "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
        "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip":
            "Formatos: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
            "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
            "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip",

        "Système de coordonnées de référence (SCR)":
            "Sistema de referência de coordenadas (SRC)",
        "SCR :": "SRC:",
        "Appliquer le SCR": "Aplicar SRC",
        "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
        "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi.":
            "Declara este SRC na camada sem reprojetar as coordenadas.\n"
            "Desativado se a extensão da camada exceder os limites do SRC escolhido.",

        "Sélection de couche": "Seleção de camada",
        "Ouvrir un fichier vectoriel": "Abrir arquivo vetorial",
        "Enregistrer la copie Shapefile": "Salvar cópia Shapefile",

        "Entités à corriger": "Feições a corrigir",
        "Entités sans géométrie ou hors emprise SCR":
            "Feições sem geometria ou fora da extensão do SRC",
        "Toutes les entités": "Todas as feições",
        "Tout sélectionner": "Selecionar tudo",
        "Désélectionner": "Desselecionar",
        "Aucune entité chargée.": "Nenhuma feição carregada.",
        "Raison": "Motivo",
        "Sans géométrie": "Sem geometria",
        "Hors emprise SCR": "Fora do SRC",
        "FID": "FID",

        "Action à appliquer sur la sélection":
            "Ação a aplicar à seleção",
        "Reprojeter — les entités sont dans un SCR différent de la couche":
            "Reprojetar — as feições estão num SRC diferente da camada",
        "SCR d'origine des entités :": "SRC de origem das feições:",
        "Définir la géométrie depuis des champs attributaires":
            "Definir geometria a partir de campos de atributos",
        "Longitude / Latitude  →  Point": "Longitude / Latitude  →  Ponto",
        "Longitude :": "Longitude:",
        "Latitude :": "Latitude:",
        "Champ WKT (Well-Known Text)": "Campo WKT (Well-Known Text)",
        "Champ WKT :": "Campo WKT:",
        "Reprojeter les coordonnées vers le SCR de la couche":
            "Reprojetar coordenadas para o SRC da camada",
        "SCR source des coordonnées :": "SRC de origem das coordenadas:",
        "🔍  Prévisualiser la transformation":
            "🔍  Pré-visualizar transformação",
        "Appliquer les corrections": "Aplicar correções",

        "Types de champs": "Tipos de campo",
        "SCR et aperçu": "SRC e pré-visualização",
        "Aucune géométrie": "Sem geometria",
        "Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
        "Vous pourrez définir la géométrie à l'étape 2.":
            "Nenhum campo numérico (Integer/Real) ou WKT detectado.\n"
            "Você poderá definir a geometria na etapa 2.",

        "GeoFixer — Erreur": "GeoFixer — Erro",
        "GeoFixer — Erreur export": "GeoFixer — Erro de exportação",
        "GeoFixer — Fichier verrouillé": "GeoFixer — Arquivo bloqueado",
        "GeoFixer — Géométrie requise": "GeoFixer — Geometria necessária",
        "GeoFixer — Shapefile créé": "GeoFixer — Shapefile criado",
        "GeoFixer — Couche CSV": "GeoFixer — Camada CSV",
        "GeoFixer — Couche sans géométrie": "GeoFixer — Camada sem geometria",
        "GeoFixer — Création Shapefile requise":
            "GeoFixer — Criação de Shapefile necessária",
        "(Canvas non disponible)": "(Tela de mapa não disponível)",
        'Aucune couche sélectionnée.':
            'Nenhuma camada selecionada.',
        '🔍  Prévisualiser':
            '🔍  Pré-visualizar',
        'Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip':
            'Formatos: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip',
        'Si les coordonnées dans les champs sont dans un SCR différent\nde la couche, cochez cette case et indiquez le SCR source.':
            'Se as coordenadas nos campos estiverem num SRC diferente\ndo da camada, marque esta caixa e indique o SRC de origem.',
        'Aucune action sélectionnée.\nChoisissez « Reprojeter » ou « Définir depuis les champs ».':
            'Nenhuma ação selecionada.\nEscolha «Reprojetar» ou «Definir a partir dos campos».',
        'Aucune entité sélectionnée.\nSélectionnez au moins une entité dans le tableau.':
            'Nenhuma feição selecionada.\nSelecione pelo menos uma feição na tabela.',
        'Configuration des champs':
            'Configuração de campos',

        # ── Nouvelles chaînes (corr. bugs) ────────────────────────────────────
        "Colonnes numériques candidates (lon/lat) — {n} entité(s)":
            "Colunas numéricas candidatas (lon/lat) — {n} feição(ões)",
        "Colonnes WKT détectées — {n} entité(s)":
            "Colunas WKT detectadas — {n} feição(ões)",
        "Aperçu — {n} entité(s)":
            "Pré-visualização — {n} feição(ões)",
        "Le fichier <b>{filename}</b> contient {count} couche(s).<br>"
        "Sélectionnez la couche à traiter :":
            "O arquivo <b>{filename}</b> contém {count} camada(s).<br>"
            "Selecione a camada a processar:",
        "La couche « {name} » ne possède aucune géométrie.\n\n"
        "La fenêtre de configuration des champs va s'ouvrir. "
        "Définissez les types de champs et le mode géométrique "
        "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
        "Un Shapefile sera créé avec les géométries construites depuis les champs — "
        "vous pourrez corriger les éventuelles géométries manquantes à l'étape 2.":
            "A camada «{name}» não possui geometria.\n\n"
            "A janela de configuração de campos será aberta. "
            "Defina os tipos de campo e o modo de geometria "
            "(Lon/Lat ou WKT), depois pré-visualize para validar o SRC.\n\n"
            "Um Shapefile será criado com as geometrias construídas a partir dos campos — "
            "poderá corrigir geometrias em falta na etapa 2.",
        "Veuillez sélectionner ou ouvrir une couche avant de continuer.":
            "Selecione ou abra uma camada antes de continuar.",
        "{n_total} entité(s) listée(s)  —  {n_sel} sélectionnée(s).":
            "{n_total} feição(ões) listada(s)  —  {n_sel} selecionada(s).",
    },

    # ==========================================================================
    # ITALIANO
    # ==========================================================================
    "it": {
        "GeoFixer — Correction de géométrie":
            "GeoFixer — Correzione geometria",
        "GeoFixer": "GeoFixer",
        "GeoFixer\n"
        "Corrige ou définit la géométrie d'entités vectorielles\n"
        "depuis des champs de coordonnées ou par reprojection.":
            "GeoFixer\n"
            "Corregge o definisce la geometria di elementi vettoriali\n"
            "da campi di coordinate o per riproiezione.",

        "● Étape 1 — Sélection et SCR":
            "● Fase 1 — Selezione e SRC",
        "● Étape 2 — Correction des entités":
            "● Fase 2 — Correzione elementi",
        "→": "→",
        "Étape suivante  →": "Fase successiva  →",
        "←  Retour": "←  Indietro",

        "Source de données": "Sorgente dati",
        "Couche :": "Layer:",
        "ou": "o",
        "📁  Ouvrir un fichier…": "📁  Apri file…",
        "Ouvre un fichier vectoriel et le charge dans QGIS.":
            "Apre un file vettoriale e lo carica in QGIS.",
        "Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
        "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
        "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip":
            "Formati: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · "
            "CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · "
            "ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip",

        "Système de coordonnées de référence (SCR)":
            "Sistema di riferimento delle coordinate (SRC)",
        "SCR :": "SRC:",
        "Appliquer le SCR": "Applica SRC",
        "Déclare ce SCR sur la couche sans reprojeter les coordonnées.\n"
        "Désactivé si l'emprise de la couche dépasse les bounds du SCR choisi.":
            "Dichiara questo SRC sul layer senza riproiettare le coordinate.\n"
            "Disabilitato se l'estensione del layer supera i limiti del SRC scelto.",

        "Sélection de couche": "Selezione layer",
        "Ouvrir un fichier vectoriel": "Apri file vettoriale",
        "Enregistrer la copie Shapefile": "Salva copia Shapefile",

        "Entités à corriger": "Elementi da correggere",
        "Entités sans géométrie ou hors emprise SCR":
            "Elementi senza geometria o fuori dall'estensione SRC",
        "Toutes les entités": "Tutti gli elementi",
        "Tout sélectionner": "Seleziona tutto",
        "Désélectionner": "Deseleziona",
        "Aucune entité chargée.": "Nessun elemento caricato.",
        "Raison": "Motivo",
        "Sans géométrie": "Senza geometria",
        "Hors emprise SCR": "Fuori dall'estensione SRC",
        "FID": "FID",

        "Action à appliquer sur la sélection":
            "Azione da applicare alla selezione",
        "Reprojeter — les entités sont dans un SCR différent de la couche":
            "Riproiettare — gli elementi hanno un SRC diverso dal layer",
        "SCR d'origine des entités :": "SRC di origine degli elementi:",
        "Définir la géométrie depuis des champs attributaires":
            "Definisci geometria dai campi attributi",
        "Longitude / Latitude  →  Point": "Longitudine / Latitudine  →  Punto",
        "Longitude :": "Longitudine:",
        "Latitude :": "Latitudine:",
        "Champ WKT (Well-Known Text)": "Campo WKT (Well-Known Text)",
        "Champ WKT :": "Campo WKT:",
        "Reprojeter les coordonnées vers le SCR de la couche":
            "Riproiettare le coordinate nel SRC del layer",
        "SCR source des coordonnées :": "SRC di origine delle coordinate:",
        "🔍  Prévisualiser la transformation":
            "🔍  Anteprima trasformazione",
        "Appliquer les corrections": "Applica correzioni",

        "Types de champs": "Tipi di campo",
        "SCR et aperçu": "SRC e anteprima",
        "Aucune géométrie": "Nessuna geometria",
        "Aucun champ numérique (Integer/Real) ni champ WKT détecté.\n"
        "Vous pourrez définir la géométrie à l'étape 2.":
            "Nessun campo numerico (Integer/Real) o WKT rilevato.\n"
            "Potrete definire la geometria nella fase 2.",

        "GeoFixer — Erreur": "GeoFixer — Errore",
        "GeoFixer — Erreur export": "GeoFixer — Errore di esportazione",
        "GeoFixer — Fichier verrouillé": "GeoFixer — File bloccato",
        "GeoFixer — Géométrie requise": "GeoFixer — Geometria richiesta",
        "GeoFixer — Shapefile créé": "GeoFixer — Shapefile creato",
        "GeoFixer — Couche CSV": "GeoFixer — Layer CSV",
        "GeoFixer — Couche sans géométrie": "GeoFixer — Layer senza geometria",
        "GeoFixer — Création Shapefile requise":
            "GeoFixer — Creazione Shapefile richiesta",
        "(Canvas non disponible)": "(Canvas non disponibile)",
        'Aucune couche sélectionnée.':
            'Nessun layer selezionato.',
        '🔍  Prévisualiser':
            '🔍  Anteprima',
        'Formats : Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip':
            'Formati: Shapefile · GeoPackage · GeoJSON · KML/KMZ · GML · CSV/TSV · MapInfo TAB/MIF · GPX · DXF · DWG · ESRI FileGDB · SQLite/SpatiaLite · .gz · .zip',
        'Si les coordonnées dans les champs sont dans un SCR différent\nde la couche, cochez cette case et indiquez le SCR source.':
            'Se le coordinate nei campi sono in un SRC diverso\nda quello del layer, attivare questa casella e indicare il SRC sorgente.',
        'Aucune action sélectionnée.\nChoisissez « Reprojeter » ou « Définir depuis les champs ».':
            'Nessuna azione selezionata.\nScegliere «Riproiettare» o «Definire dai campi».',
        'Aucune entité sélectionnée.\nSélectionnez au moins une entité dans le tableau.':
            'Nessun elemento selezionato.\nSelezionare almeno un elemento nella tabella.',
        'Configuration des champs':
            'Configurazione dei campi',

        # ── Nouvelles chaînes (corr. bugs) ────────────────────────────────────
        "Colonnes numériques candidates (lon/lat) — {n} entité(s)":
            "Colonne numeriche candidate (lon/lat) — {n} elemento/i",
        "Colonnes WKT détectées — {n} entité(s)":
            "Colonne WKT rilevate — {n} elemento/i",
        "Aperçu — {n} entité(s)":
            "Anteprima — {n} elemento/i",
        "Le fichier <b>{filename}</b> contient {count} couche(s).<br>"
        "Sélectionnez la couche à traiter :":
            "Il file <b>{filename}</b> contiene {count} layer.<br>"
            "Selezionare il layer da elaborare:",
        "La couche « {name} » ne possède aucune géométrie.\n\n"
        "La fenêtre de configuration des champs va s'ouvrir. "
        "Définissez les types de champs et le mode géométrique "
        "(Lon/Lat ou WKT), puis prévisualisez pour valider le SCR.\n\n"
        "Un Shapefile sera créé avec les géométries construites depuis les champs — "
        "vous pourrez corriger les éventuelles géométries manquantes à l'étape 2.":
            "Il layer «{name}» non ha geometria.\n\n"
            "Si aprirà la finestra di configurazione dei campi. "
            "Definire i tipi di campo e la modalità geometrica "
            "(Lon/Lat o WKT), quindi visualizzare l'anteprima per convalidare il SRC.\n\n"
            "Verrà creato uno Shapefile con le geometrie costruite dai campi — "
            "le geometrie mancanti potranno essere corrette nella fase 2.",
        "Veuillez sélectionner ou ouvrir une couche avant de continuer.":
            "Selezionare o aprire un layer prima di continuare.",
        "{n_total} entité(s) listée(s)  —  {n_sel} sélectionnée(s).":
            "{n_total} elemento/i elencato/i  —  {n_sel} selezionato/i.",
    },
}
