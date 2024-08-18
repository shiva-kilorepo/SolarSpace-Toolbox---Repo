# ------------------------------------------------------------------------------
#!/usr/bin/env python
"""
Description: Applies pre-grading to a surface with high slopes
Revision log
0.0.1 - 2/14/2022 - Initial scripting
0.0.2 - 5/20/2022 - Eliminated output path and made it automatically detect, added slope fixed areas output
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2022, KiloNewton, LLC"
__credits__     = "John Williamson"
__version__     = "0.0.2"
__license__     = "internal"
__ArcVersion__  = "ArcPro 2.9.3"
__maintainer__  = "Matthew Gagne"
__status__      = "Testing"

# Load modules 
import arcpy
from arcpy import env
import os.path
import sys

# Load extension modules
from arcpy.sa import *
from arcpy.ddd import *

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

focusArea =  r"C:\Users\MGagne\Documents\Clients\Sundt\Green River.gdb\FocusAreaPregrade"
hardBound = r"C:\Users\MGagne\Documents\Clients\Sundt\Green River.gdb\FocusAreaPregrade"
rowLength =  "320" # arcpy.GetParameterAsText(2) # row length
demInput =  r"C:\Users\MGagne\Documents\Clients\Sundt\Green River.gdb\demGrade_v1" # arcpy.GetParameterAsText(3) # Input elevation model - raster
slopeUnits = "Percent"
nLimit = "10" # arcpy.GetParameterAsText(5) # North slope production limit 
sLimit = "10" #arcpy.GetParameterAsText(6) # South slope structural limit 
ewLimit = "12" #arcpy.GetParameterAsText(7) # East/west mechanical/structural limit 
boundExpand = "25" # arcpy.GetParameterAsText(8) # slope area boundary expansion (typically 10-25 feet based on terrain)
xyzUnit = "Foot" # arcpy.GetParameterAsText(9) # Foot or Meter
version = "v1" #arcpy.GetParameterAsText(10) # Version control

outputPath = os.path.dirname(workspace)
    
# Set grid resolution to the DEM raster and snap to raster
spatialRef = arcpy.Describe(demInput).spatialReference
arcpy.env.snapRaster = demInput
gridRes = arcpy.Describe(demInput).meanCellWidth

# Expand the domain of the focus area by the boundExpand
area_expand = arcpy.analysis.GraphicBuffer(focusArea, "area_expand", boundExpand, "SQUARE", "MITER", 10, "0 Feet")
area_domain = arcpy.analysis.Clip(area_expand, hardBound, "area_domain", None)

# Run focal statistics to get rid of small areas
lengthRes = str(round(float(rowLength)/2,0))
if xyzUnit == "Foot":
    widthRes = "30"
if xyzUnit == "Meter": 
    widthRes = "10"

focalInput = ("Rectangle " + lengthRes + " " + widthRes + " MAP")
demFocal = arcpy.sa.FocalStatistics(demInput, focalInput, "MEAN", "DATA", 90)

# Clip the elevation to the area_domain
demFocal_clip = arcpy.management.Clip(demFocal, "", "demFocal_clip2", area_domain, "3.4e+38", "ClippingGeometry", "NO_MAINTAIN_EXTENT")

# Process the directional slope
AspectRad = arcpy.sa.Aspect(demFocal_clip,"PLANAR",xyzUnit) * math.pi / 180

# Process slope in radians
SlopeRad = arcpy.sa.Slope(demFocal_clip,"DEGREE","1","PLANAR",xyzUnit) * math.pi / 180

if slopeUnits == "Percent":
    ewSlope = Tan( Sin( AspectRad) * SlopeRad) * 100
    nsSlope = Tan( Cos( AspectRad) * SlopeRad) * 100
if slopeUnits == "Degrees":
    ewSlope = Sin( AspectRad) * SlopeRad * 180 / math.pi
    nsSlope = Cos( AspectRad) * SlopeRad * 180 / math.pi

nClass = '-2000 '+nLimit+' NODATA; '+nLimit+' 2000 1'
sClass = '-2000 -'+sLimit+' 1; -'+sLimit+' 2000 NODATA'
ewClass = '-2000 -'+ewLimit+' 1; -'+ewLimit+' '+ewLimit+' NODATA; '+ewLimit+' 2000 1'

reclassN = arcpy.sa.Reclassify(nsSlope, "VALUE", nClass, "DATA")
reclassS = arcpy.sa.Reclassify(nsSlope, "VALUE", sClass, "DATA")
reclassEW = arcpy.sa.Reclassify(ewSlope, "VALUE", ewClass, "DATA")

# Convert to polygon
nPoly = arcpy.conversion.RasterToPolygon(reclassN, r"in_memory\nPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
sPoly = arcpy.conversion.RasterToPolygon(reclassS, r"in_memory\sPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
ewPoly = arcpy.conversion.RasterToPolygon(reclassEW, r"in_memory\ewPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
exclusionPoly = arcpy.management.Merge([[nPoly],[sPoly],[ewPoly]], r"in_memory\exclusionPoly")

# Aggregate within 25 feet and minimum areas and holes of 5000 sq ft
exclusionAgg = arcpy.cartography.AggregatePolygons(exclusionPoly, r"in_memory\exclusionAgg", "25 Feet", "5000 SquareFeet", "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)

# Buffer out by 1/16 of the row length to merge close areas
bufferOut = str(float( rowLength) / 16) + " " + xyzUnit
bufferOutPoly = arcpy.analysis.Buffer(exclusionAgg, r"in_memory\bufferOutPoly", bufferOut, "FULL", "ROUND", "NONE", None, "PLANAR")

# Buffer in by 1/8 of the row area to get rid of small areas
bufferIn = str(float( rowLength) / -8) + " " + xyzUnit
bufferInPoly = arcpy.analysis.Buffer(bufferOutPoly, r"in_memory\bufferInPoly", bufferIn, "FULL", "ROUND", "NONE", None, "PLANAR")

# Buffer out by 1/32 of the row length
bufferFinal = str(float( rowLength) / 32) + " " + xyzUnit
preFinal = arcpy.analysis.Buffer(bufferInPoly, r"in_memory\preFinal", bufferFinal, "FULL", "ROUND", "NONE", None, "PLANAR")

# Split up areas that may have been combined
preFinal_split = arcpy.management.MultipartToSinglepart(preFinal, "preFinal_split")

# Get rid of areas smaller than 5000 square feet or 465 meters
if xyzUnit == "Foot":
    areaMax = "Shape_Area > 1000"
if xyzUnit == "Meter": 
    areaMax = "Shape_Area > 465"
slopeAreas = arcpy.analysis.Select(preFinal_split,"slopeAreas", areaMax)

# Expand slopeAreas by the expansion parameter
if xyzUnit == "Foot":
    bufferUnit = boundExpand + " Feet"
if xyzUnit == "Meter": 
    bufferUnit = boundExpand + " Meter"

slopeAreas_expand = arcpy.analysis.PairwiseBuffer(slopeAreas, "slopeFix_areas", bufferUnit, "ALL", None, "PLANAR", "0 Feet")
slopeAreasFinal = arcpy.analysis.Clip(slopeAreas_expand, hardBound, "adjusted_areas_"  + version, None)

# Convert boundary to line and interpolate the original surface
slopeAreas_line = arcpy.management.FeatureToLine(slopeAreasFinal, "slopeAreas_line", None, "ATTRIBUTES")
area_line_3D = arcpy.sa.InterpolateShape(demInput, slopeAreas_line, "area_line_3D", None, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

# Convert to TIN, then to raster, clip and mosaic to original surface
tin_name = str(outputPath + "\slopeFix")
slopeFix = arcpy.ddd.CreateTin(tin_name, spatialRef, "area_line_3D Shape.Z Hard_Line")
slopeFix_raster = arcpy.ddd.TinRaster(slopeFix, "slopeFix_raster","FLOAT", "NATURAL_NEIGHBORS", "CELLSIZE", 1, gridRes)
demSlopeFix = arcpy.Clip_management(slopeFix_raster,"","demSlopeFix", slopeAreasFinal, "", "ClippingGeometry")

demSlopeFix_all = arcpy.management.MosaicToNewRaster([demInput,demSlopeFix],workspace,"demSlopeFix_" + version, spatialRef,"32_BIT_FLOAT","",1,"LAST","FIRST")

# Clean up
arcpy.management.Delete(slopeFix)
arcpy.management.Delete("demFocal")
arcpy.management.Delete("area_line_3D")
arcpy.management.Delete("demFocal_clip")
arcpy.management.Delete("AspectRad")
arcpy.management.Delete("SlopeRad")
arcpy.management.Delete("reclassNS")
arcpy.management.Delete("reclassEW")
arcpy.management.Delete("preFinal_split")
arcpy.management.Delete("slopeAreas")
arcpy.management.Delete("slopeFix_raster")
arcpy.management.Delete("demSlopeFix")
arcpy.management.Delete("slopeAreas_line")

# Add results to map
aprxMap.addDataFromPath(demSlopeFix_all)
aprxMap.addDataFromPath(slopeAreasFinal)











