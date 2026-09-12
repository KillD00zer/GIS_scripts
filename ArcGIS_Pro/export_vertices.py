import arcpy
import csv
import os
import re

def clean_filename(name):
    """تنظيف اسم الملف من أي رموز غير مسموحة في نظام التشغيل"""
    if not name:
        return "Unknown"
    cleaned = re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()
    return cleaned if cleaned else "Unknown"

def format_value(val, field_name):
    """تقريب حقول المساحة والمحيط لأقرب رقمين عشريين"""
    if val is None:
        return ""
    
    target_keywords = ["مساحة", "مساحه", "محيط", "area", "length", "perimeter"]
    is_target_field = any(kw in field_name.lower() for kw in target_keywords)
    
    if is_target_field:
        try:
            num = float(val)
            return f"{num:.2f}"
        except (ValueError, TypeError):
            return val
            
    return val

def export_polygons_matching_structure():
    polygon_layer = arcpy.GetParameterAsText(0)
    output_folder = arcpy.GetParameterAsText(1)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # تعريف نظام الإحداثيات الجغرافي WGS 84 بالدرجات العشرية (WKID: 4326)
    wgs84_sr = arcpy.SpatialReference(4326)

    # استخراج أسماء الحقول الوصفية
    excluded_types = ["Geometry", "Blob", "Raster"]
    fields_info = [f for f in arcpy.ListFields(polygon_layer) if f.type not in excluded_types]
    
    desc = arcpy.da.Describe(polygon_layer)
    oid_field_name = desc.get("OIDFieldName", "OBJECTID")
    
    attr_field_names = [f.name for f in fields_info if f.name != oid_field_name]

    # البحث عن حقل اسم مقدم الطلب
    applicant_field_name = None
    possible_names = ["اسم_مقدم_الطلب", "اسم مقدم الطلب", "مقدم_الطلب", "الاسم"]
    for fname in attr_field_names:
        if fname.strip() in possible_names:
            applicant_field_name = fname
            break

    # بناء رأس جدول الـ CSV
    headers = ["OBJECTID"] + attr_field_names + ["ORIG_FID", "POINT_X", "POINT_Y"]
    cursor_fields = ["OID@", "SHAPE@"] + attr_field_names

    exported_count = 0

    with arcpy.da.SearchCursor(polygon_layer, cursor_fields) as cursor:
        for row in cursor:
            oid = row[0]
            geom = row[1]
            raw_attr_values = list(row[2:])

            if geom is None:
                continue

            # تحويل الشكل الهندسي إلى WGS 84 (درجات عشرية)
            geom_wgs84 = geom.projectAs(wgs84_sr)

            # تقريب قيم حقول المساحة والمحيط
            formatted_attr_values = [
                format_value(val, fname)
                for val, fname in zip(raw_attr_values, attr_field_names)
            ]

            # استخراج اسم الملف بناءً على اسم مقدم الطلب
            file_title = f"Polygon_{oid}"
            if applicant_field_name:
                field_idx = attr_field_names.index(applicant_field_name)
                applicant_value = raw_attr_values[field_idx]
                if applicant_value:
                    file_title = clean_filename(applicant_value)

            csv_filename = f"{file_title}.csv"
            csv_path = os.path.join(output_folder, csv_filename)

            # معالجة تكرار نفس الاسم
            counter_dup = 1
            while os.path.exists(csv_path):
                csv_filename = f"{file_title}_{counter_dup}.csv"
                csv_path = os.path.join(output_folder, csv_filename)
                counter_dup += 1

            # كتابة محتوى ملف الـ CSV
            with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                point_counter = 1
                # قراءة النقاط بعد التحويل لنظام الدرجات
                for part in geom_wgs84:
                    for pt in part:
                        if pt:
                            # pt.X سيكون Longitude و pt.Y سيكون Latitude بدقة كاملة بالدرجات
                            row_data = [point_counter] + formatted_attr_values + [oid, pt.X, pt.Y]
                            writer.writerow(row_data)
                            point_counter += 1

            arcpy.AddMessage(f"تم إنشاء الملف بنجاح: {csv_filename}")
            exported_count += 1

    if exported_count > 0:
        arcpy.AddMessage(f"اكتملت العملية! تم تصدير {exported_count} ملف بإحداثيات الدرجات (WGS84).")
    else:
        arcpy.AddWarning("لم يتم العثور على أي عناصر لتصديرها.")

if __name__ == "__main__":
    export_polygons_matching_structure()