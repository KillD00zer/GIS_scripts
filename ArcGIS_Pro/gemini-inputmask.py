import os
import re
import arcpy
import numpy as np
from PIL import Image


def main():
    arcpy.env.overwriteOutput = True

    # 1. Read tool parameters
    orig_tif = arcpy.GetParameterAsText(0)
    ai_mask_img = arcpy.GetParameterAsText(1)
    out_folder = arcpy.GetParameterAsText(2)
    min_area_str = arcpy.GetParameterAsText(3)
    min_roof_area_m2 = float(min_area_str) if min_area_str else 15.0

    os.makedirs(out_folder, exist_ok=True)

    # Derive a clean output prefix from the input raster's source filename
    desc = arcpy.Describe(orig_tif)
    src_path = getattr(desc, "catalogPath", orig_tif)
    raw_name = os.path.splitext(os.path.basename(src_path))[0]
    base_name = re.sub(r"[^A-Za-z0-9_]", "_", raw_name)

    out_mask_tif = os.path.join(out_folder, f"{base_name}_mask.tif")
    out_polygons = os.path.join(out_folder, f"{base_name}_rooftops.shp")

    # 2. Read grid size and spatial metadata from the original GeoTIFF + TFW
    arcpy.AddMessage(f"Reading spatial metadata from: {orig_tif}")
    orig_raster = arcpy.Raster(orig_tif)
    width = orig_raster.width
    height = orig_raster.height
    x_cell = orig_raster.meanCellWidth
    y_cell = orig_raster.meanCellHeight
    lower_left = arcpy.Point(orig_raster.extent.XMin, orig_raster.extent.YMin)
    sr = orig_raster.spatialReference
    has_valid_sr = sr is not None and sr.name != "Unknown"

    # 3. Match AI mask pixel dimensions 1:1 and binarize (1 = roof, 0 = background)
    arcpy.AddMessage(f"Aligning mask to {width}x{height} pixels...")
    resample_mode = getattr(Image, "Resampling", Image).NEAREST
    img = Image.open(ai_mask_img).convert("L").resize((width, height), resample_mode)
    binary_mask = np.where(np.array(img) > 127, 1, 0).astype(np.uint8)

    # 4. Save georeferenced GeoTIFF and generate matching .tfw world file
    mask_raster = arcpy.NumPyArrayToRaster(
        binary_mask,
        lower_left_corner=lower_left,
        x_cell_size=x_cell,
        y_cell_size=y_cell,
        value_to_nodata=0,
    )
    mask_raster.save(out_mask_tif)

    if has_valid_sr:
        arcpy.management.DefineProjection(out_mask_tif, sr)
    else:
        arcpy.AddWarning("Input raster has an Unknown spatial reference; projection was not defined on output.")

    arcpy.management.ExportRasterWorldFile(out_mask_tif)
    arcpy.AddMessage(f"Saved GeoTIFF + TFW: {out_mask_tif}")

    # 5. Convert binary mask to individual polygons
    arcpy.AddMessage("Converting mask to rooftop polygons...")
    arcpy.conversion.RasterToPolygon(
        in_raster=out_mask_tif,
        out_polygon_features=out_polygons,
        simplify="SIMPLIFY",
        raster_field="Value",
        create_multipart_features="SINGLE_OUTER_PART",
    )

    # 6. Filter out small noise/watermarks and assign clean sequential IDs
    arcpy.management.AddField(out_polygons, "ROOF_ID", "LONG")
    arcpy.management.AddField(out_polygons, "ROOF_LABEL", "TEXT", field_length=30)
    arcpy.management.AddField(out_polygons, "AREA_M2", "DOUBLE")

    roof_counter = 1
    removed_count = 0
    with arcpy.da.UpdateCursor(
        out_polygons, ["SHAPE@", "ROOF_ID", "ROOF_LABEL", "AREA_M2"]
    ) as cursor:
        for row in cursor:
            geom = row[0]
            area_m2 = (
                geom.getArea("GEODESIC", "SQUAREMETERS")
                if has_valid_sr
                else geom.area
            )
            if area_m2 < min_roof_area_m2:
                cursor.deleteRow()
                removed_count += 1
            else:
                row[1] = roof_counter
                row[2] = f"ROOFTOP #{roof_counter}"
                row[3] = round(area_m2, 2)
                cursor.updateRow(row)
                roof_counter += 1

    arcpy.AddMessage(
        f"Done! Kept {roof_counter - 1} rooftops (removed {removed_count} noise polygons < {min_roof_area_m2} m²)."
    )
    arcpy.AddMessage(f"Saved Polygons: {out_polygons}")

    # 7. Pass outputs back to ArcGIS Pro Derived parameters
    try:
        arcpy.SetParameterAsText(4, out_mask_tif)
        arcpy.SetParameterAsText(5, out_polygons)
    except Exception:
        pass


if __name__ == "__main__":
    main()