# -*- coding: utf-8 -*-
"""
===============================================================================
Cadastral Survey Intersection & Export Tool for ArcMap 10.x (Python 2.7)
أداة فحص وتقاطع الأراضي المساحية مع الأحواض لبرنامج ArcMap
===============================================================================
المدخلات (Parameters):
  0. طبقة الطلبات / الأراضي (Feature Layer - 'طلبات')
  1. طبقة الأحواض والقطع (Feature Layer - 'قطع_احواض')
  2. مجلد الإخراج (Folder)

المخرجات (Outputs لكل مواطن/طلب):
  - مجلد مخصص باسم صاحب الطلب
  - Land_<id_no>_<name>.csv: بيانات الطلب + أركان المضلع WGS84
  - Areas_<id_no>_<name>.csv: نتائج التقاطع المكاني الفعلي مع الأحواض والقطع
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
    sys.stderr.write("Error: arcpy module not found. Please run within ArcMap Python environment.\n")
    sys.exit(1)

def clean_filename(name):
    """تنظيف اسم الملف من أي رموز غير مسموحة"""
    if name is None:
        return u"Unknown"
    if not isinstance(name, unicode):
        name = unicode(str(name), 'utf-8', errors='ignore')
    cleaned = re.sub(ur'[\\/*?:"<>|]', u"", name).strip()
    return cleaned if cleaned else u"Unknown"

def find_field_value(row_dict, candidate_names, default=u""):
    """البحث غير الحساس لحالة الأحرف عن قيمة الحقل"""
    row_dict_lower = {unicode(k).lower(): v for k, v in row_dict.items()}
    for cand in candidate_names:
        cand_lower = unicode(cand).lower()
        if cand_lower in row_dict_lower:
            val = row_dict_lower[cand_lower]
            return u"" if val is None else val
    return default

def format_number(val, decimals=2):
    """تنسيق الأرقام العشرية"""
    if val is None or val == "":
        return u""
    try:
        f = float(val)
        if decimals is not None:
            return u"{:.{}f}".format(f, decimals)
        return u"{}".format(f)
    except (ValueError, TypeError):
        return unicode(val)

def export_cadastral_survey(land_layer, areas_layer, output_folder):
    """دالة التصدير والتقاطع المكاني الرئيسية لأرك ماب"""
    arcpy.AddMessage(u"=== بدء عملية استخراج بيانات الرفع المساحي والتقاطعات (ArcMap) ===".encode('utf-8'))
    
    if not isinstance(output_folder, unicode):
        output_folder = unicode(output_folder, 'utf-8', errors='ignore')

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # WGS 1984 (EPSG: 4326)
    wgs84_sr = arcpy.SpatialReference(4326)

    # استخراج وصف طبقة الأراضي
    desc_land = arcpy.Describe(land_layer)
    oid_field_land = getattr(desc_land, 'OIDFieldName', 'OBJECTID')
    
    # فحص التحديد
    fid_set = getattr(desc_land, 'FIDSet', '')
    has_selection = bool(fid_set and fid_set.strip())
    
    if not has_selection:
        arcpy.AddWarning(u"تنبيه: لا يوجد عناصر محددة في طبقة الأراضي. سيتم تصدير كافة العناصر المتاحة بالطبقة.".encode('utf-8'))

    excluded_types = ["Geometry", "Blob", "Raster"]
    land_fields_info = [f for f in arcpy.ListFields(land_layer) if f.type not in excluded_types]
    land_attr_names = [f.name for f in land_fields_info if f.name != oid_field_land]
    cursor_land_fields = ["OID@", "SHAPE@"] + land_attr_names

    # استخراج وصف طبقة الأحواض
    areas_fields_info = [f for f in arcpy.ListFields(areas_layer) if f.type not in excluded_types]
    areas_attr_names = [f.name for f in areas_fields_info]

    hod_name_candidates = [u"name", u"hod_name", u"hod", u"اسم_الحوض", u"اسم الحوض", u"الحوض"]
    parcel_id_candidates = [u"parcel_id", u"parcel_no", u"رقم_القطعة", u"رقم القطعة", u"قطعة", u"رقم_القطعه"]
    map_id_candidates = [u"map_id", u"map_no", u"map", u"رقم_اللوحة", u"رقم اللوحة", u"لوحة", u"اللوحة"]
    
    processed_count = 0

    with arcpy.da.SearchCursor(land_layer, cursor_land_fields) as land_cursor:
        for land_row in land_cursor:
            oid = land_row[0]
            geom = land_row[1]
            attr_values = list(land_row[2:])
            
            if geom is None:
                continue

            land_dict = dict(zip(land_attr_names, attr_values))
            
            applicant_name = find_field_value(land_dict, [u"name", u"اسم_مقدم_الطلب", u"اسم مقدم الطلب", u"الاسم"], default=u"Land_{}".format(oid))
            id_no = find_field_value(land_dict, [u"id_no", u"رقم_الطلب", u"رقم الطلب", u"id"], default=unicode(oid))
            
            clean_name = clean_filename(applicant_name)
            clean_id = clean_filename(id_no)
            file_base = u"{}_{}".format(clean_id, clean_name)

            owner_folder_name = clean_name if clean_name != u"Unknown" else u"طلب_{}".format(clean_id)
            case_folder = os.path.join(output_folder, owner_folder_name)
            
            if os.path.exists(case_folder):
                existing_files = os.listdir(case_folder)
                if existing_files and not any(clean_id in unicode(f) for f in existing_files):
                    owner_folder_name = u"{}_{}".format(clean_name, clean_id)
                    case_folder = os.path.join(output_folder, owner_folder_name)

            if not os.path.exists(case_folder):
                os.makedirs(case_folder)

            msg_start = u"\n-> معالجة الطلب رقم: {} - مقدم الطلب: {}".format(clean_id, applicant_name)
            arcpy.AddMessage(msg_start.encode('utf-8'))

            # 1. تصدير ملف بيانات الأرض والإحداثيات
            geom_wgs84 = geom.projectAs(wgs84_sr)
            vertices = []
            for part in geom_wgs84:
                for pt in part:
                    if pt:
                        vertices.append((pt.X, pt.Y))
            
            if len(vertices) > 3 and vertices[0] == vertices[-1]:
                vertices.pop()

            land_csv_filename = u"Land_{}.csv".format(file_base)
            land_csv_path = os.path.join(case_folder, land_csv_filename)

            land_headers = ["POINT_NUM"] + [f.encode('utf-8') if isinstance(f, unicode) else str(f) for f in land_attr_names] + ["ORIG_FID", "POINT_X", "POINT_Y"]
            
            with open(land_csv_path, 'wb') as f_land:
                f_land.write('\xef\xbb\xbf')
                writer = csv.writer(f_land)
                writer.writerow(land_headers)
                
                formatted_attrs = []
                for val, name in zip(attr_values, land_attr_names):
                    if isinstance(val, float):
                        formatted_attrs.append(format_number(val, 4 if "coord" in name.lower() else 2).encode('utf-8'))
                    elif val is None:
                        formatted_attrs.append("")
                    elif isinstance(val, unicode):
                        formatted_attrs.append(val.encode('utf-8'))
                    else:
                        formatted_attrs.append(str(val))

                for pt_idx, (px, py) in enumerate(vertices, start=1):
                    row_data = [pt_idx] + formatted_attrs + [oid, "{:.8f}".format(px), "{:.8f}".format(py)]
                    writer.writerow(row_data)

            msg_land = u"   [+] تم تصدير ملف بيانات الأرض: {} ({} نقطة أركان)".format(land_csv_filename, len(vertices))
            arcpy.AddMessage(msg_land.encode('utf-8'))

            # 2. التقاطع المكاني وتصدير ملف الأحواض والقطع
            areas_csv_filename = u"Areas_{}.csv".format(file_base)
            areas_csv_path = os.path.join(case_folder, areas_csv_filename)

            intersecting_areas = []
            areas_cursor_fields = ["SHAPE@"] + areas_attr_names

            with arcpy.da.SearchCursor(areas_layer, areas_cursor_fields) as areas_cursor:
                for area_row in areas_cursor:
                    area_geom = area_row[0]
                    if area_geom is None:
                        continue
                    
                    if not geom.disjoint(area_geom):
                        area_attrs = dict(zip(areas_attr_names, area_row[1:]))
                        overlap_shape = geom.intersect(area_geom, 4)
                        overlap_area_m2 = overlap_shape.area if overlap_shape else 0.0

                        hod_val = unicode(find_field_value(area_attrs, hod_name_candidates, default=u"")).strip()
                        parcel_val = find_field_value(area_attrs, parcel_id_candidates, default=u"")
                        map_val = unicode(find_field_value(area_attrs, map_id_candidates, default=u"")).strip()
                        
                        if isinstance(parcel_val, float) and parcel_val.is_integer():
                            parcel_val = int(parcel_val)
                        parcel_str = unicode(parcel_val).strip() if parcel_val is not None else u""
                        if parcel_str.lower() in [u"nan", u"none"]:
                            parcel_str = u""
                        
                        if not parcel_str and not (u"حوض" in hod_val):
                            continue

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

            areas_headers = ["id_no", "hod_name", "parcel_id", "map_id", "overlap_area_m2"]
            with open(areas_csv_path, 'wb') as f_areas:
                f_areas.write('\xef\xbb\xbf')
                writer = csv.writer(f_areas)
                writer.writerow(areas_headers)
                
                if intersecting_areas:
                    for area_info in intersecting_areas:
                        writer.writerow([
                            unicode(area_info["id_no"]).encode('utf-8'),
                            unicode(area_info["hod_name"]).encode('utf-8'),
                            unicode(area_info["parcel_id"]).encode('utf-8'),
                            unicode(area_info["map_id"]).encode('utf-8'),
                            unicode(area_info["overlap_area_m2"]).encode('utf-8')
                        ])
                    msg_areas = u"   [+] تم تصدير ملف التقاطعات: {} ({} حوض/قطعة)".format(areas_csv_filename, len(intersecting_areas))
                    arcpy.AddMessage(msg_areas.encode('utf-8'))
                else:
                    writer.writerow([unicode(id_no).encode('utf-8'), "", "", "", "0.00"])
                    msg_warn = u"   [!] لم يتم العثور على تقاطع مكاني مع طبقة الأحواض للطلب {}".format(id_no)
                    arcpy.AddWarning(msg_warn.encode('utf-8'))

            processed_count += 1

    if processed_count > 0:
        arcpy.AddMessage(u"\n=======================================================".encode('utf-8'))
        arcpy.AddMessage(u"تم الانتهاء بنجاح! تم تصدير {} طلب (أرض + تقاطعات).".format(processed_count).encode('utf-8'))
        arcpy.AddMessage(u"المسار: {}".format(output_folder).encode('utf-8'))
        arcpy.AddMessage(u"=======================================================".encode('utf-8'))
    else:
        arcpy.AddWarning(u"لم يتم العثور على أي عناصر لمعالجتها.".encode('utf-8'))

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        in_land = sys.argv[1]
        in_areas = sys.argv[2]
        out_folder = sys.argv[3]
    else:
        in_land = arcpy.GetParameterAsText(0)
        in_areas = arcpy.GetParameterAsText(1)
        out_folder = arcpy.GetParameterAsText(2)

    export_cadastral_survey(in_land, in_areas, out_folder)
