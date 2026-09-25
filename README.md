# 🗺️ Shared GIS & ArcPy Automation Scripts
### حزمة أدوات وسكريبتات المعالجة المساحية لبيئات ArcGIS Pro و ArcMap 10.x

[![ArcGIS](https://img.shields.io/badge/ArcGIS-Pro%20%2F%20ArcMap%2010.8-green.svg)](https://www.esri.com/)
[![Python](https://img.shields.io/badge/Python-2.7%20%2F%203.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

---

## 📖 Overview / نظرة عامة
مجموعة أدوات برمجية مساعدة ومستقلة للاستخدام المباشر داخل بيئات نظم المعلومات الجغرافية (Esri ArcGIS)، مقسمة ومضغوطة لكل تطبيق مع دليل تثبيت وضبط المعاملات (Parameters):

1. **حزمة ArcMap 10.x (`ArcMap_Scripts.zip` / مجلد `ArcMap_10.x/`)**:
   - `arcmap code.py`: أداة تصدير بيانات قطع الأراضي وإحداثيات أركانها بنظام WGS84 إلى CSV (متوافق مع Python 2.7).
   - `export_cadastral_survey_arcmap.py`: أداة التقاطع المكاني المساحي مع الأحواض والقطع في ArcMap.
   - `HOW_TO_ADD_TO_ARCMAP.txt`: دليل خطوة بخطوة لكيفية إنشاء Toolbox وإضافة السكريبت وضبط المعاملات.

2. **حزمة ArcGIS Pro (`ArcGIS_Pro_Scripts.zip` / مجلد `ArcGIS_Pro/`)**:
   - `export_vertices.py`: أداة تصدير أركان المضلعات WGS84 بالدرجات العشرية في ArcGIS Pro (Python 3.x).
   - `export_cadastral_survey.py`: أداة التقاطع المكاني المساحي وإصدار ملفات المعاملات في ArcGIS Pro.
   - `HOW_TO_ADD_TO_ARCPRO.txt`: دليل خطوة بخطوة لكيفية إنشاء `.atbx` وضبط المعاملات والأنواع (Data Types).

---

## 🗂️ Files & Distributions / الملفات والحزم

| Script / File | Environment | Description / الوصف |
|---|---|---|
| `ArcMap_Scripts.zip` | **ArcMap 10.x** | أرشيف مضغوط يضم أداتي ArcMap + ملف تعليمات وضبط المعاملات. |
| `ArcGIS_Pro_Scripts.zip` | **ArcGIS Pro** | أرشيف مضغوط يضم أداتي ArcGIS Pro + ملف تعليمات وضبط المعاملات. |
| `ArcMap_10.x/HOW_TO_ADD_TO_ARCMAP.txt` | **ArcMap 10.x** | دليل التثبيت وضبط معاملات الأدوات (Parameters) بالتفصيل. |
| `ArcGIS_Pro/HOW_TO_ADD_TO_ARCPRO.txt` | **ArcGIS Pro** | دليل التثبيت وضبط معاملات الأدوات (Parameters) بالتفصيل. |
| `ArcMap_10.x/arcmap code.py` | **ArcMap 10.8** | تصدير بيانات الطبقة المضلعة وإحداثيات الأركان WGS84 إلى CSV. |
| `ArcMap_10.x/export_cadastral_survey_arcmap.py` | **ArcMap 10.8** | التقاطع المكاني واستخراج ملفات `Land_*.csv` و `Areas_*.csv`. |
| `ArcGIS_Pro/export_vertices.py` | **ArcGIS Pro** | استخراج إحداثيات رؤوس وأركان المضلعات إلى CSV بـ UTF-8 BOM. |
| `ArcGIS_Pro/export_cadastral_survey.py` | **ArcGIS Pro** | التقاطع المكاني واستخراج ملفات `Land_*.csv` و `Areas_*.csv`. |
