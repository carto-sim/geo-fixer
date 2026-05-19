# GeoFixer

A QGIS plugin for correcting or defining the geometry of vector features from attribute fields (longitude/latitude or WKT) or by reprojection.

---

## Table of contents

- [Overview](#overview)
- [Supported formats](#supported-formats)
- [Installation](#installation)
- [Usage](#usage)
  - [Step 1 — Layer selection and CRS](#step-1--layer-selection-and-crs)
  - [Layers without geometry (CSV, DBF…)](#layers-without-geometry-csv-dbf)
  - [Step 2 — Feature correction](#step-2--feature-correction)
- [Languages](#languages)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Changelog](#changelog)

---

## Overview

GeoFixer addresses a common problem in GIS workflows: vector layers whose features have **missing, incorrect, or inconsistent geometries**. This includes:

- Features with null geometries (e.g. CSV files, attribute-only tables)
- Features projected in the wrong CRS (geometry exists but is in the wrong place)
- Features whose coordinates are stored in attribute fields rather than as actual geometry

The plugin guides the user through a two-step assistant:

1. **Select** the layer and define/verify its CRS
2. **Identify and correct** the problematic features

The plugin window is **non-modal**: QGIS remains fully usable while GeoFixer is open.

---

## Supported formats

GeoFixer can open any format supported by GDAL/OGR:

| Format | Extension |
|---|---|
| Shapefile | `.shp` |
| GeoPackage | `.gpkg` |
| GeoJSON / JSON | `.geojson`, `.json` |
| KML / KMZ | `.kml`, `.kmz` |
| GML | `.gml` |
| CSV / TSV | `.csv`, `.tsv` |
| MapInfo TAB | `.tab` |
| MapInfo MIF/MID | `.mif`, `.mid` |
| GPS Exchange Format | `.gpx` |
| AutoCAD DXF | `.dxf` |
| AutoCAD DWG | `.dwg` |
| ESRI File Geodatabase | `.gdb` |
| SQLite / SpatiaLite | `.sqlite`, `.db` |
| Compressed archives | `.gz`, `.zip` |

Multi-layer formats (GeoPackage, GDB, KML, DWG, DXF…) display a layer picker dialog listing available layers with their feature count and geometry type.

**CSV files**: the delimiter is detected automatically by analysing the header line (candidates: `;`, `\t`, `,`, `|`, `:`). No manual configuration required.

---

## Installation

1. Download the latest ZIP from the [Releases](../../releases) page
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded ZIP file
4. The plugin appears in **Vector → GeoFixer** and in the toolbar

**Requirements**: QGIS 3.16 or later (QGIS 4.x supported).

---

## Usage

### Step 1 — Layer selection and CRS

**Select a layer** from the combobox (lists layers already loaded in QGIS) or click **Open a file…** to load a new one.

**The preview map** shows:
- Grey: world country boundaries
- Red: extent of the selected CRS
- Purple: extent of the layer's coordinates, **interpreted in the selected CRS**

This distinction is important: the purple rectangle shows where the layer's *raw coordinates* would land if the selected CRS were applied — not where the layer currently is. This lets you verify CRS coherence visually before applying it.

**Apply CRS** button: declares the selected CRS on the layer without reprojecting coordinates.
The button is **disabled** if the layer extent does not fit within the selected CRS bounds (uses `contains()`, not `intersects()`).

An informational line below the map indicates the number of features without geometry.

---

### Layers without geometry (CSV, DBF…)

When a layer without geometry is selected (or opened), GeoFixer automatically opens the **Field Configuration** dialog.

#### Tab 1 — Field types

A table showing up to 10 sample rows. The first row (blue background) contains type selectors for each column. Types are detected automatically from the actual values (100-row sample, 80% threshold) and only compatible types are offered.

| Detected type | Compatible types |
|---|---|
| Integer | Integer, Real, String |
| Real | Real, String |
| Date | Date, String |
| String | String |

#### Tab 2 — CRS and preview

Choose how geometry will be constructed from the fields:

- **No geometry** — the layer is exported as-is; geometry can be defined later at Step 2
- **Longitude / Latitude → Point** — select the X and Y fields (auto-detected by field name)
- **WKT field** — select a field containing WKT strings (auto-detected from values)

Select the **CRS** of the coordinates and click **Preview** to verify on the map. The OK button is locked until a valid preview has been performed with the geometry fully inside the selected CRS extent.

A **Shapefile** is then created with the geometries already built from the fields. The file is saved to the same directory as the source file. The plugin checks that none of the associated Shapefile components (`.shp`, `.dbf`, `.shx`, `.prj`, `.cpg`) are locked by another application before writing.

---

### Step 2 — Feature correction

#### The feature table

The table lists **problematic features** (no geometry or outside CRS extent), or all features if the "All features" filter is selected.

Columns displayed: FID + fields detected as potentially containing coordinates (numeric fields and WKT fields) + a **Reason** column.

| Row colour | Meaning |
|---|---|
| Red | No geometry |
| Yellow | Outside CRS extent |
| Green | Valid feature (in "All features" mode) |

Click column headers to sort. Multiple selection with Ctrl+click, Shift+click, or Ctrl+A.

#### Available actions

**Reproject**: the user specifies the *source CRS* of the misplaced features (the CRS they were accidentally drawn in). GeoFixer reprojects them to the layer's current CRS.

**Define from fields**:
- *Longitude / Latitude → Point*: constructs a Point geometry from two numeric fields
- *WKT field*: parses a WKT string field; supports all geometry types

Both modes include an optional **Reproject coordinates** checkbox: if the coordinate values are in a different CRS than the layer, check this box and specify the source CRS.

#### Preview

Click **Preview transformation** (purple button) to see the result on a map **before modifying the layer**:
- ≤ 20 features: individual geometries are drawn in green
- \> 20 features: the global bounding box of the transformed features is drawn

The zoom always includes the result extent, even if features fall outside the CRS bounds.

---

## Languages

The plugin detects the active language from QGIS preferences (**Settings → Options → General → User interface language**).

Supported languages:

| Code | Language |
|---|---|
| `en` | English *(default)* |
| `fr` | Français |
| `de` | Deutsch |
| `es` | Español |
| `pt` | Português |
| `it` | Italiano |

If QGIS is configured in an unsupported language, the interface falls back to English.

---

## Architecture

```
geo_fixer/
├── __init__.py                 QGIS entry point + bytecode cache invalidation
├── metadata.txt                QGIS plugin metadata
├── geo_fixer_plugin.py         Plugin class (menu, toolbar, lifecycle)
├── geo_fixer_dialog.py         Main dialog — 2-step assistant
├── field_config_dialog.py      Field config dialog (layers without geometry)
├── FONCTIONNALITES.txt         Feature tracking (French, developer reference)
│
├── core/
│   ├── __init__.py
│   ├── layer_inspector.py      Feature inspection (no geometry, outside CRS)
│   │                           Field type detection from values
│   ├── geometry_fixer.py       Geometry corrections (reproject, lon/lat, WKT)
│   ├── qt_compat.py            Qt5/Qt6 constant compatibility (single location)
│   └── utils.py                Shared UI utilities (_NoWheelCombo, canvas, CRS selector)
│
└── i18n/
    ├── __init__.py             tr(), detect_language(), init()
    └── translations.py         Translation dictionaries (en/de/es/pt/it)
```

### Key design decisions

**Non-modal window**: `parent=None` gives the plugin window its own taskbar entry, independent of QGIS.

**CRS extent check uses `contains()` not `intersects()`**: an `intersects()` check would pass for a Lambert II layer interpreted as WGS84 (coordinates like 938435 are technically within [-180,180]). `contains()` requires the full extent to fit within the CRS bounds.

**Field type detection by values, not metadata**: CSV and DBF formats often declare all fields as String. GeoFixer samples up to 100 rows and uses a 50% success threshold for numeric detection, and requires ≥2 valid WKT values starting with a recognised keyword.

**No `lrelease` dependency**: translations use plain Python dictionaries, making the plugin self-contained with no build step for localisation.

---

## Requirements

- QGIS 3.16 or later
- Python 3.9 or later (included with QGIS)
- GDAL ≥ 3.0 (included with QGIS)

No additional Python packages required.

---

## Changelog

| Version | Summary |
|---|---|
| **1.3.1** | Internationalisation: EN/DE/ES/PT/IT, English as default |
| **1.3.0** | i18n infrastructure (`i18n/` package, `tr()` function) |
| **1.2.1** | FONCTIONNALITES.txt audit, Qt compat and utils refactoring |
| **1.2.0** | Bug fix: geometry construction (removed erroneous WGS84→CRS transform) |
| **1.1.9** | Dynamic geometry type (Point/LineString/Polygon from WKT), lock check on all .shp components |
| **1.1.8** | Auto-open FieldConfigDialog, multi-file lock check, source directory in file picker |
| **1.1.7** | Extent cache for canvas after Shapefile creation, enriched format filter |
| **1.1.6** | OK blocked if extent outside CRS, side-by-side layout in FieldConfigDialog |
| **1.1.5** | Full "CRS and preview" tab in FieldConfigDialog (GeoAggregator logic) |
| **1.1.3** | CSV delimiter fix: literal character in URI, not URL-encoded |
| **1.1.0** | Shapefile export via memory layer, FieldConfigDialog with field types |
| **1.0.7** | Multi-layer file support, side-by-side layout at Step 2, zoom inclusive |
| **1.0.5** | Field type detection by values, reprojection from source CRS |
| **1.0.3** | Non-modal window, Apply CRS button conditional on `contains()` |
| **1.0.0** | Initial release |
