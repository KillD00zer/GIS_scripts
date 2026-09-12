# -*- coding: utf-8 -*-
"""
===============================================================================
Cadastral Survey Intersection & Export Tool (ArcGIS Pro / ArcMap)
منظومة فحص وتقاطع الأراضي مع الأحواض والخرائط المساحية
===============================================================================
Inputs:
  1. Land Layer (Feature Layer with active selection, e.g., 'طلبات')
  2. Areas Layer (Feature Layer, e.g., 'قطع_احواض' / 'قطع')
  3. Output Folder (Folder path to save exported CSVs)

Outputs for each selected land feature:
  - Land_<id_no>_<name>.csv: All land attributes + corner vertices (WGS84 degrees)
  - Areas_<id_no>_<name>.csv: Intersected basins, parcel numbers, and map sheets
===============================================================================
"""

import os
import sys
import csv
import re

# Safely import arcpy
try:
    import arcpy
except ImportError:
    sys.stderr.write("Error: arcpy module not found. Please run within ArcGIS Python environment.\n")
    sys.exit(1)

# Helper for Unicode string cleanup
def clean_filename(name):
    """Remove illegal filename characters"""
    if name is None:
        return "Unknown"
    text = str(name).strip()
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text).strip()
    return cleaned if cleaned else "Unknown"

def find_field_value(row_dict, candidate_names, default=""):
    """Case-insensitive search for field value among candidate names"""
    row_dict_lower = {k.lower(): v for k, v in row_dict.items()}
    for cand in candidate_names:
        cand_lower = cand.lower()
        if cand_lower in row_dict_lower:
            val = row_dict_lower[cand_lower]
            return "" if val is None else val
    return default

def format_number(val, decimals=2):
    """Format float numbers cleanly"""
    if val is None or val == "":
        return ""
    try:
        f = float(val)
        return f"{f:.{decimals}f}" if decimals is not None else f"{f}"
    except (ValueError, TypeError):
        return str(val)

def export_cadastral_survey(land_layer, areas_layer, output_folder):
    """Main export routine"""
    arcpy.AddMessage("=== بدء عملية استخراج بيانات الرفع المساحي والتقاطعات ===")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Spatial Reference: WGS 1984 (EPSG: 4326) for degrees output
    wgs84_sr = arcpy.SpatialReference(4326)

    # Inspect Land Layer fields
    desc_land = arcpy.da.Describe(land_layer)
    oid_field_land = desc_land.get("OIDFieldName", "OBJECTID")
    
    # Check selection
    selected_oids = desc_land.get("FIDSet", None)
    if isinstance(selected_oids, (list, tuple, set)):
        has_selection = len(selected_oids) > 0
    elif isinstance(selected_oids, str):
        has_selection = len(selected_oids.strip()) > 0
    else:
        has_selection = False
    
    if not has_selection:
        arcpy.AddWarning("تنبيه: لا يوجد عناصر محددة (Selected Features) في طبقة الأراضي. سيتم تصدير كافة العناصر المتاحة في الطبقة.")

    # All non-geometry fields from Land Layer
    excluded_types = ["Geometry", "Blob", "Raster"]
    land_fields_info = [f for f in arcpy.ListFields(land_layer) if f.type not in excluded_types]
    land_attr_names = [f.name for f in land_fields_info if f.name != oid_field_land]
    
    # Candidate fields for key land attributes
    cursor_land_fields = ["OID@", "SHAPE@"] + land_attr_names

    # Inspect Areas Layer fields
    desc_areas = arcpy.da.Describe(areas_layer)
    areas_fields_info = [f for f in arcpy.ListFields(areas_layer) if f.type not in excluded_types]
    areas_attr_names = [f.name for f in areas_fields_info]

    # Map candidate field names for Areas
    hod_name_candidates = ["name", "hod_name", "hod", "اسم_الحوض", "اسم الحوض", "الحوض"]
    parcel_id_candidates = ["parcel_id", "parcel_no", "رقم_القطعة", "رقم القطعة", "قطعة", "رقم_القطعه"]
    map_id_candidates = ["map_id", "map_no", "map", "رقم_اللوحة", "رقم اللوحة", "لوحة", "اللوحة"]
    
    processed_count = 0

    with arcpy.da.SearchCursor(land_layer, cursor_land_fields) as land_cursor:
        for land_row in land_cursor:
            oid = land_row[0]
            geom = land_row[1]
            attr_values = list(land_row[2:])
            
            if geom is None:
                continue

            land_dict = dict(zip(land_attr_names, attr_values))
            
            # Extract key identifiers
            applicant_name = find_field_value(land_dict, ["name", "اسم_مقدم_الطلب", "اسم مقدم الطلب", "الاسم"], default=f"Land_{oid}")
            id_no = find_field_value(land_dict, ["id_no", "رقم_الطلب", "رقم الطلب", "id"], default=str(oid))
            
            clean_name = clean_filename(applicant_name)
            clean_id = clean_filename(id_no)
            file_base = f"{clean_id}_{clean_name}"

            # Create dedicated subfolder for the owner
            owner_folder_name = clean_name if clean_name != "Unknown" else f"طلب_{clean_id}"
            case_folder = os.path.join(output_folder, owner_folder_name)
            
            # If folder already exists for a different ID, append ID to avoid collisions
            if os.path.exists(case_folder):
                # Check if this case folder belongs to a different ID
                existing_files = os.listdir(case_folder)
                if existing_files and not any(clean_id in f for f in existing_files):
                    owner_folder_name = f"{clean_name}_{clean_id}"
                    case_folder = os.path.join(output_folder, owner_folder_name)

            if not os.path.exists(case_folder):
                os.makedirs(case_folder)

            arcpy.AddMessage(f"\n-> معالجة الطلب رقم: {clean_id} - مقدم الطلب: {applicant_name}")
            arcpy.AddMessage(f"   [📁] مجلد الحفظ: {owner_folder_name}")

            # -------------------------------------------------------------
            # 1. Export Land CSV (Attributes + Ordered WGS84 Coordinates)
            # -------------------------------------------------------------
            # Project geometry to WGS84 for Lat/Lon
            geom_wgs84 = geom.projectAs(wgs84_sr)
            
            # Extract unique polygon vertices in sequence
            vertices = []
            for part in geom_wgs84:
                for pt in part:
                    if pt:
                        vertices.append((pt.X, pt.Y))
            
            # If closed ring repeats first point at end, remove trailing duplicate for clear corner count
            if len(vertices) > 3 and vertices[0] == vertices[-1]:
                vertices.pop()

            land_csv_filename = f"Land_{file_base}.csv"
            land_csv_path = os.path.join(case_folder, land_csv_filename)

            land_headers = ["POINT_NUM"] + land_attr_names + ["ORIG_FID", "POINT_X", "POINT_Y"]
            
            with open(land_csv_path, mode="w", newline="", encoding="utf-8-sig") as f_land:
                writer = csv.writer(f_land)
                writer.writerow(land_headers)
                
                # Format attributes
                formatted_attrs = []
                for val, name in zip(attr_values, land_attr_names):
                    if isinstance(val, float):
                        formatted_attrs.append(format_number(val, 4 if "coord" in name.lower() else 2))
                    elif val is None:
                        formatted_attrs.append("")
                    else:
                        formatted_attrs.append(str(val))

                for pt_idx, (px, py) in enumerate(vertices, start=1):
                    row_data = [pt_idx] + formatted_attrs + [oid, f"{px:.8f}", f"{py:.8f}"]
                    writer.writerow(row_data)

            arcpy.AddMessage(f"   [+] تم تصدير ملف بيانات الأرض: {land_csv_filename} ({len(vertices)} نقطة أركان)")

            # -------------------------------------------------------------
            # 2. Intersect with Areas Layer & Export Areas CSV
            # -------------------------------------------------------------
            areas_csv_filename = f"Areas_{file_base}.csv"
            areas_csv_path = os.path.join(case_folder, areas_csv_filename)

            # Spatial query on areas_layer using the geometry of the current land parcel
            intersecting_areas = []
            areas_cursor_fields = ["SHAPE@"] + areas_attr_names

            # Select intersecting features using da.SearchCursor with spatial comparison
            with arcpy.da.SearchCursor(areas_layer, areas_cursor_fields) as areas_cursor:
                for area_row in areas_cursor:
                    area_geom = area_row[0]
                    if area_geom is None:
                        continue
                    
                    # Check if geometries intersect
                    if not geom.disjoint(area_geom):
                        area_attrs = dict(zip(areas_attr_names, area_row[1:]))
                        
                        # Calculate overlap area if projected (or standard area)
                        overlap_shape = geom.intersect(area_geom, 4) # 4 = polygon dimension
                        overlap_area_m2 = overlap_shape.area if overlap_shape else 0.0

                        hod_val = str(find_field_value(area_attrs, hod_name_candidates, default="")).strip()
                        parcel_val = find_field_value(area_attrs, parcel_id_candidates, default="")
                        map_val = str(find_field_value(area_attrs, map_id_candidates, default="")).strip()
                        
                        # Clean parcel number from floats like 22.0 -> 22
                        if isinstance(parcel_val, float) and parcel_val.is_integer():
                            parcel_val = int(parcel_val)
                        parcel_str = str(parcel_val).strip() if parcel_val is not None else ""
                        if parcel_str.lower() in ["nan", "none"]:
                            parcel_str = ""
                        
                        # Only include meaningful cadastral parcels (skip self-overlaps or empty parcel IDs)
                        if not parcel_str and not ("حوض" in hod_val):
                            continue

                        # Deduplicate multiple identical segments
                        key = (hod_val, parcel_str, map_val)
                        existing = [a for a in intersecting_areas if (a["hod_name"], a["parcel_id"], a["map_id"]) == key]
                        if existing:
                            try:
                                curr_area = float(existing[0]["overlap_area_m2"])
                                if overlap_area_m2 > curr_area:
                                    existing[0]["overlap_area_m2"] = format_number(overlap_area_m2, 2)
                            except ValueError:
                                pass
                        else:
                            intersecting_areas.append({
                                "id_no": id_no,
                                "hod_name": hod_val,
                                "parcel_id": parcel_str,
                                "map_id": map_val,
                                "overlap_area_m2": format_number(overlap_area_m2, 2)
                            })

            # Write Areas CSV
            areas_headers = ["id_no", "hod_name", "parcel_id", "map_id", "overlap_area_m2"]
            with open(areas_csv_path, mode="w", newline="", encoding="utf-8-sig") as f_areas:
                writer = csv.writer(f_areas)
                writer.writerow(areas_headers)
                
                if intersecting_areas:
                    for area_info in intersecting_areas:
                        writer.writerow([
                            area_info["id_no"],
                            area_info["hod_name"],
                            area_info["parcel_id"],
                            area_info["map_id"],
                            area_info["overlap_area_m2"]
                        ])
                    arcpy.AddMessage(f"   [+] تم تصدير ملف التقاطعات: {areas_csv_filename} ({len(intersecting_areas)} حوض/قطعة متقاطعة)")
                else:
                    # Write placeholder row if no intersection found
                    writer.writerow([id_no, "", "", "", "0.00"])
                    arcpy.AddWarning(f"   [!] لم يتم العثور على تقاطع مكاني مع طبقة الأحواض للطلب {id_no}.")

            processed_count += 1

    if processed_count > 0:
        arcpy.AddMessage(f"\n=======================================================")
        arcpy.AddMessage(f"تم الانتهاء بنجاح! تم تصدير {processed_count} طلب (أرض + تقاطعات).")
        arcpy.AddMessage(f"المسار: {output_folder}")
        arcpy.AddMessage(f"=======================================================")
    else:
        arcpy.AddWarning("لم يتم العثور على أي عناصر لمعالجتها.")

# Entry point for ArcGIS Script Tool & Standalone CLI
if __name__ == "__main__":
    if len(sys.argv) >= 4:
        # Standalone or Script Tool with arguments
        in_land = sys.argv[1]
        in_areas = sys.argv[2]
        out_folder = sys.argv[3]
    else:
        # ArcGIS Geoprocessing parameter interface
        in_land = arcpy.GetParameterAsText(0)
        in_areas = arcpy.GetParameterAsText(1)
        out_folder = arcpy.GetParameterAsText(2)

    export_cadastral_survey(in_land, in_areas, out_folder)
