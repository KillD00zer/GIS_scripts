# -*- coding: utf-8 -*-
import arcpy
import csv
import os
import re

def clean_filename(name):
    """تنظيف اسم الملف من أي رموز غير مسموحة في نظام التشغيل"""
    if name is None:
        return u"Unknown"
    if not isinstance(name, unicode):
        name = unicode(str(name), 'utf-8', errors='ignore')
    cleaned = re.sub(ur'[\\/*?:"<>|]', u"", name).strip()
    return cleaned if cleaned else u"Unknown"

def format_value(val, field_name):
    """تقريب حقول المساحة والمحيط لأقرب رقمين عشريين"""
    if val is None:
        return ""
    
    target_keywords = [u"مساحة", u"مساحه", u"محيط", u"area", u"length", u"perimeter"]
    fname_lower = unicode(field_name).lower()
    is_target_field = any(kw in fname_lower for kw in target_keywords)
    
    if is_target_field:
        try:
            num = float(val)
            return "{:.2f}".format(num)
        except (ValueError, TypeError):
            return val
            
    return val

def export_polygons_matching_structure():
    polygon_layer = arcpy.GetParameterAsText(0)
    output_folder = arcpy.GetParameterAsText(1)

    if not isinstance(output_folder, unicode):
        output_folder = unicode(output_folder, 'utf-8', errors='ignore')

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # WGS 1984 (EPSG: 4326)
    wgs84_sr = arcpy.SpatialReference(4326)

    # استخراج أسماء الحقول الوصفية
    excluded_types = ["Geometry", "Blob", "Raster"]
    fields_info = [f for f in arcpy.ListFields(polygon_layer) if f.type not in excluded_types]
    
    # استخدام arcpy.Describe المتوافقة مع ArcMap 10.8
    desc = arcpy.Describe(polygon_layer)
    oid_field_name = getattr(desc, 'OIDFieldName', 'OBJECTID')
    
    attr_field_names = [f.name for f in fields_info if f.name != oid_field_name]

    # البحث عن حقل اسم مقدم الطلب
    applicant_field_name = None
    possible_names = [u"اسم_مقدم_الطلب", u"اسم مقدم الطلب", u"مقدم_الطلب", u"الاسم"]
    for fname in attr_field_names:
        if unicode(fname).strip() in possible_names:
            applicant_field_name = fname
            break

    # رأس جدول الـ CSV
    headers = ["OBJECTID"] + [f.encode('utf-8') if isinstance(f, unicode) else str(f) for f in attr_field_names] + ["ORIG_FID", "POINT_X", "POINT_Y"]
    cursor_fields = ["OID@", "SHAPE@"] + attr_field_names

    exported_count = 0

    with arcpy.da.SearchCursor(polygon_layer, cursor_fields) as cursor:
        for row in cursor:
            oid = row[0]
            geom = row[1]
            raw_attr_values = list(row[2:])

            if geom is None:
                continue

            # تحويل الإحداثيات إلى WGS 84
            geom_wgs84 = geom.projectAs(wgs84_sr)

            # تقريب المساحة والمحيط
            formatted_attr_values = [
                format_value(val, fname)
                for val, fname in zip(raw_attr_values, attr_field_names)
            ]

            # اسم الملف بناءً على اسم مقدم الطلب
            file_title = u"Polygon_{}".format(oid)
            if applicant_field_name:
                field_idx = attr_field_names.index(applicant_field_name)
                applicant_val = raw_attr_values[field_idx]
                if applicant_val:
                    file_title = clean_filename(applicant_val)

            csv_filename = u"{}.csv".format(file_title)
            csv_path = os.path.join(output_folder, csv_filename)

            # تجنب تكرار الأسماء
            counter_dup = 1
            while os.path.exists(csv_path):
                csv_filename = u"{}_{}.csv".format(file_title, counter_dup)
                csv_path = os.path.join(output_folder, csv_filename)
                counter_dup += 1

            # فتح الملف مع إضافة BOM لضمان قراءة العربي في الإكسيل
            with open(csv_path, 'wb') as f:
                f.write('\xef\xbb\xbf')
                writer = csv.writer(f)
                writer.writerow(headers)

                point_counter = 1
                for part in geom_wgs84:
                    for pt in part:
                        if pt:
                            encoded_attrs = []
                            for v in formatted_attr_values:
                                if isinstance(v, unicode):
                                    encoded_attrs.append(v.encode('utf-8'))
                                elif v is None:
                                    encoded_attrs.append("")
                                else:
                                    encoded_attrs.append(str(v))

                            row_data = [point_counter] + encoded_attrs + [oid, pt.X, pt.Y]
                            writer.writerow(row_data)
                            point_counter += 1

            arcpy.AddMessage("Created: " + csv_filename.encode('utf-8'))
            exported_count += 1

    if exported_count > 0:
        arcpy.AddMessage("Done! Exported {} file(s).".format(exported_count))
    else:
        arcpy.AddWarning("No features selected or found.")

if __name__ == "__main__":
    export_polygons_matching_structure()