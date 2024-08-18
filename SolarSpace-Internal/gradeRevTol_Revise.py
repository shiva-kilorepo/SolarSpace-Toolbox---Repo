############################################################
"""REVISE GRADING TO NEW REVEAL TOLERANCE

Description: Revises grading to newly defined reveal tolerance

While this script can be used independently, it will be a foundation for many of the adjustment scripts upcoming

Revision log
0.0.1 - 10/31/202 - Initial scripting
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2022, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
__license__     = "Testing"
__ArcVersion__  = "ArcPro 3.0.1"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Testing"

import arcpy
from arcpy.sa import *
from arcpy.ddd import *
import os.path
import sys

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

# Set parameters
demExist = r"C:\Users\MGagne\Documents\SolarSpace Tools\Grading Testing.gdb\demExist"
demGrade = r"C:\Users\MGagne\Documents\SolarSpace Tools\Grading Testing.gdb\demGrade_v1f_1ft_r" # Is this even needed?
rowsInput = r"C:\Users\MGagne\Documents\SolarSpace Tools\Grading Testing.gdb\rowsInput"
row_ID = "row_ID"
pilesInput = r"C:\Users\MGagne\Documents\SolarSpace Tools\Grading Testing.gdb\piles_v1f_1ft_r"
poaField = "TOP_elv"
revField = "reveal"
minRevealpre = "4" # These can actually be derived
maxRevealpre = "5" # These can actually be derived
minRevealNew = "4"
maxRevealNew = "5.5"
gradeOutput = "demGrade_rev_v2f"
gradeBoundsOut = "gradeBounds_v2f"
pilesGradedOut = "piles_rev_v2f"

outputPath = os.path.dirname(workspace)

# Set spatial reference and grid resolution as the same as the DEM raster
spatialRef = arcpy.Describe(demExist).spatialReference
gridRes = arcpy.Describe(demExist).meanCellWidth
mapUnits = spatialRef.linearUnitName

# Set all raster outputs to snap to the DEM
arcpy.env.snapRaster = demExist

# Calculate north-south plane of array slope
piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

# Add xy coordinates - will overwrite if already present
arcpy.management.AddXY(piles_working)

# Change poaField to TOP_elv_orig
arcpy.management.AlterField(piles_working, poaField, "TOP_elv_orig")

# Calculate derived base plane of array
revTol = float(maxRevealpre) - float(minRevealpre)
minTOP_elv_stats = arcpy.analysis.Statistics(piles_working, "minTOP_elv_stats", [["TOP_elv_orig", "MIN"]], row_ID)
arcpy.management.JoinField(piles_working, row_ID, minTOP_elv_stats, row_ID, "MIN_TOP_elv_orig")
arcpy.management.CalculateField(piles_working, "basePlaneDev","(!TOP_elv_orig! - !MIN_TOP_elv_orig! - "+" revTol "+"/2)", "PYTHON3", "","DOUBLE")

# Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
coorStatsInput = [["TOP_elv_orig", "MEAN"], ["POINT_Y", "MEAN"]]
coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

# Join the mean of the plane of array and MEAN_POINT_Y back to the piles
arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, ["MEAN_TOP_elv_orig", "MEAN_POINT_Y"])

# Calculate zy_bar, y_ybar_sq
arcpy.management.CalculateField(piles_working, "zy_bar","(!TOP_elv_orig! + !MEAN_TOP_elv_orig!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

# Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

# Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
arcpy.management.CalculateField(sumStats, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

# Join slope to piles_working
arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope"])

# Find the intercept
arcpy.management.CalculateField(piles_working, "bInit", "!TOP_elv_orig! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

newPointStats = arcpy.analysis.Statistics(piles_working, "newPointStats", [["bInit", "MEAN"],["nsSlope", "MEAN"]], row_ID)

# Create a working feature class for the rows
rows_working = arcpy.conversion.FeatureClassToFeatureClass(rowsInput, workspace, "rows_working")

# Get the extents of the rows. This assumes rows are directly north-south
# THIS WOULD WORK FOR V3.0.2 AND UP: arcpy.management.CalculateGeometryAttributes(rows_working, [["maxX", "EXTENT_MAX_X"],["minX", "EXTENT_MIN_X"],["maxY", "EXTENT_MAX_Y"],["minY", "EXTENT_MIN_Y"]])

# Create corner points of the rows
rowCornerPoints = arcpy.CreateFeatureclass_management("in_memory", "rowCornerPoints", "POINT", "#", "DISABLED", "DISABLED", rows_working)
arcpy.AddField_management(rowCornerPoints, "PolygonOID", "LONG")
arcpy.AddField_management(rowCornerPoints, "Position", "TEXT")

insert_cursor = arcpy.da.InsertCursor(rowCornerPoints, ["SHAPE@", "PolygonOID", "Position"])
search_cursor = arcpy.da.SearchCursor(rows_working, ["SHAPE@", "OID@"])

for row in search_cursor:
    polygon_oid = str(row[1])

    coordinateList = []

    for part in row[0]:
        for pnt in part:
            if pnt:
                coordinateList.append((pnt.X, pnt.Y))
    
    #Determine the extent of each row
    rowExtent = row[0].extent

    sw_coordinate = rowExtent.lowerLeft
    se_coordinate = rowExtent.lowerRight
    nw_coordinate = rowExtent.upperLeft
    ne_coordinate = rowExtent.upperRight
    
    sw_point = arcpy.PointGeometry(sw_coordinate)
    se_point = arcpy.PointGeometry(se_coordinate)
    nw_point = arcpy.PointGeometry(nw_coordinate)
    ne_point = arcpy.PointGeometry(ne_coordinate)
    
    insert_cursor.insertRow((nw_point, polygon_oid, "NW"))
    insert_cursor.insertRow((ne_point, polygon_oid, "NE"))
    insert_cursor.insertRow((sw_point, polygon_oid, "SW"))
    insert_cursor.insertRow((se_point, polygon_oid, "SE"))

del insert_cursor
del search_cursor

# Expand rows east/west by 10 ft
# NOTE - NEED AN OPTION FOR METERS
arcpy.management.AddXY(rowCornerPoints)

# Extend the northings and eastings - northing should be an input, and easting should be a function of the grid resolution - for now a placeholder of 4 feet is input
# CHANGE THE FACTOR FOR MAX AND MIN X/Y - CALCULATED OR INPUT

codeblock_newPTx = """
def newPTx(pos,x):
    if pos == "NW" or pos == "SW":
        return x - .5
    else:
        return x + .5
"""

arcpy.management.CalculateField(rowCornerPoints, "newX", "newPTx(!Position!,!POINT_X!)", "PYTHON3", codeblock_newPTx, "DOUBLE")

codeblock_newPTy = """
def newPTy(pos,y):
    if pos == "NW" or pos == "NE":
        return y + 3
    else:
        return y - 3
"""
        
arcpy.management.CalculateField(rowCornerPoints, "newY", "newPTy(!Position!,!POINT_Y!)", "PYTHON3", codeblock_newPTy, "DOUBLE")

# Create new points
newBoundPoints = arcpy.management.XYTableToPoint(rowCornerPoints, "in_memory/newBoundPoints", "newX", "newY", "", spatialRef)

# Add order field
codeblock_order = """
def ordPoint(pos):
    if pos == "NW":
        return 1
    if pos == "NE":
        return 2
    if pos == "SE":
        return 3
    else:
        return 4
"""

arcpy.management.CalculateField(newBoundPoints, "ptOrder", "ordPoint(!Position!)", "PYTHON3", codeblock_order, "LONG")

# Calculate base plane of array elevation at each point
arcpy.management.JoinField(newBoundPoints, "PolygonOID", rows_working, "OBJECTID", row_ID)
arcpy.management.JoinField(newBoundPoints, row_ID, newPointStats, row_ID, [["MEAN_nsSlope"],["MEAN_bInit"]])

arcpy.management.CalculateField(newBoundPoints, "poaPlaneDev", "!MEAN_nsSlope! * !newY! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

# Make points 3D
bound3Dpoints = arcpy.ddd.FeatureTo3DByAttribute(newBoundPoints, "bound3Dpoints", "poaPlaneDev")

# Create lines
boundLine = arcpy.management.PointsToLine(bound3Dpoints, "boundLine", "PolygonOID", "ptOrder", "CLOSE")

# Create TIN
tin_name = str(outputPath + "/poaOrig_TIN") 
poaOrig_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef,"boundLine Shape.Z Hard_Line <None>")

# Calculate new point x coordinates
codeblock_newX = """
def xNew(pos,x):
    if pos == "NW" or pos == "SW":
        return x - 10
    if pos == "NE" or pos == "SE":
        return x + 10
"""

arcpy.management.CalculateField(rowCornerPoints, "newX", "xNew(!Position!,!POINT_X!)", "PYTHON3", codeblock_newX)

# Calculate new point y coordinates
codeblock_newY = """
def yNew(pos,y):
    if pos == "NW" or pos == "NE":
        return y + 10
    if pos == "SW" or pos == "SE":
        return y - 10
"""

arcpy.management.CalculateField(rowCornerPoints, "newY", "yNew(!Position!,!POINT_Y!)", "PYTHON3", codeblock_newY)

expTable = arcpy.conversion.TableToTable(rowCornerPoints, workspace, "expTable")
expPoints = arcpy.management.XYTableToPoint(expTable, r"in_memory\expPoints", "newX", "newY", None, spatialRef)

rowBounds_pre = arcpy.management.MinimumBoundingGeometry(expPoints, "rowBounds_pre", "RECTANGLE_BY_AREA", "LIST", "PolygonOID", "NO_MBG_FIELDS")
rowBounds_pre_diss = arcpy.Dissolve_management(rowBounds_pre, "rowBounds_pre_diss")

extentStats = arcpy.analysis.Statistics(rowCornerPoints, "extentStats", [["POINT_X", "MAX"], ["POINT_X", "MIN"], ["POINT_Y", "MAX"], ["POINT_Y", "MIN"]],"PolygonOID")
arcpy.management.CalculateField(extentStats, "rowWidth", "!MAX_POINT_X! - !MIN_POINT_X!", "PYTHON3", "", "DOUBLE")

arcpy.management.JoinField(rowBounds_pre_diss, "OBJECTID", extentStats, "PolygonOID", [["rowWidth"]])
arcpy.management.CalculateField(rowBounds_pre_diss, "buffDist", "!rowWidth! - 10", "PYTHON3", "", "DOUBLE")

# Buffer back in for rows on the edge 
# NEED AN OPTION FOR METERS
basePlanesBounds = arcpy.analysis.GraphicBuffer(rowBounds_pre_diss, "basePlanesBounds", "buffDist")

# Clip TIN
arcpy.ddd.EditTin(poaOrig_TIN, "basePlanesBounds <None> <None> Hard_Clip false", "DELAUNAY")

# Convert to raster
poaRev = arcpy.ddd.TinRaster(poaOrig_TIN, "poaRev","FLOAT", "LINEAR", "CELLSIZE", 1, gridRes)

# Calculate spacing above and below base planes for the new reveal tolerance
delta_poa = (float(maxRevealNew) - float(minRevealNew))
arcpy.AddMessage('Reveal tolerance: ' + str(delta_poa) + ' ' + mapUnits)
spacing = delta_poa/2

# Calculate the base planes
bpPre = arcpy.sa.Minus(poaRev,float(minRevealpre)) 

basePlanesRev = arcpy.sa.Minus(bpPre,spacing) 

rowBoundsExpand = arcpy.analysis.GraphicBuffer(rowsInput, "rowBoundsExpand", "3 Feet", "SQUARE", "MITER", 10, "0 Feet")

# Create the upper bound
upperLimit = arcpy.sa.Plus(basePlanesRev, spacing)
upperBound = arcpy.management.MosaicToNewRaster([demExist,upperLimit],'in_memory','upperBound',spatialRef,'32_BIT_FLOAT',gridRes,1,'MINIMUM','FIRST')

# Create the lower bound
lowerLimit = arcpy.sa.Minus(basePlanesRev, spacing)
lowerBound = arcpy.management.MosaicToNewRaster([demExist,lowerLimit],'in_memory','lowerBound',spatialRef,'32_BIT_FLOAT',gridRes,1,'MAXIMUM','FIRST')

# Create and the final grading DEM
upperGrade = arcpy.sa.Minus(upperBound, demExist)
demGrade = arcpy.sa.Plus(lowerBound, upperGrade)

# Calculate reveals - GET RID OF REVEAL RASTER
grade_trends = arcpy.sa.Minus(demGrade, basePlanesRev)
min_rev_grade = arcpy.sa.Plus(float(minRevealNew), grade_trends)
max_min_reveal = arcpy.sa.ZonalStatistics(rowBoundsExpand, row_ID, min_rev_grade, 'MAXIMUM', 'DATA')
reveals = arcpy.sa.Minus(max_min_reveal,grade_trends)

# Create plane of array raster - CREATE 3D FEATURE CLASS HERE, GET RID OF POA RASTER 
POA =  arcpy.sa.Plus(reveals, demGrade)

# Extract ungraded and graded elevation layers
piles_output = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_output")
arcpy.sa.ExtractMultiValuesToPoints(piles_output, [[demExist,'demExist'],[demGrade,'demGrade_REV'],[reveals,'reveal_REV'],[POA,'TOP_elv_REV']],'BILINEAR')

# Create a cutFill column and create a layer with only piles that require grading
arcpy.management.CalculateField(piles_output, "cutFill_REV", "!demGrade_REV!-!demExist!", "PYTHON3","","DOUBLE")

piles_graded_pre = arcpy.Select_analysis(piles_output, 'piles_graded_pre', 'cutFill_REV < -0.083 OR cutFill_REV > 0.083' )

# Subtract the existing elevation from the graded elevation
cutFill = arcpy.sa.Minus(demGrade,demExist)

# Reclassify cut-fill raster using tolerance
reclass_code = RemapRange([[-300,-1*float(.083), 1],[-1*float(.083), float(.083), 0],[float(.083), 300, 2]])
cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
grade_area = arcpy.analysis.Select(reclass_poly, "grade_area", "gridcode <> 0")

# Select areas that intersect piles that are graded
grade_intersect = arcpy.SelectLayerByLocation_management(grade_area, 'INTERSECT', piles_graded_pre)
grade_area_rows = arcpy.conversion.FeatureClassToFeatureClass(grade_intersect, workspace, 'grade_area_rows')

# Buffer the graded areas by 5 feet close small holes and merge areas within 10 feet of each other
hole_close_buffer = "10 Feet"
grade_area_rows_buff = arcpy.Buffer_analysis(grade_area_rows, 'grade_area_rows_buff', hole_close_buffer, "FULL", "ROUND", "ALL", None, "PLANAR")

# Invert the buffer to just inside the graded area to eliminate small areas
buffer_in = "-9 Feet"
bounds_invert = arcpy.Buffer_analysis(grade_area_rows_buff, 'bounds_invert', buffer_in, "FULL", "ROUND", "ALL", None, "PLANAR")

# Extend the graded areas to 2 the raster resolution outside of the graded areas to join close areas  
bounds_extend = "3 Feet"
grade_bounds = arcpy.Buffer_analysis(bounds_invert, "grade_bounds", bounds_extend, "FULL", "ROUND", "ALL", None, "PLANAR")

# Select the sample points and the piles within graded areas
piles_intersect = arcpy.SelectLayerByLocation_management(piles_output, 'INTERSECT', grade_bounds)
piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, 'piles_graded')

# Convert the buffered layer to polylines and interpolate the existing elevation
grade_area_line = arcpy.FeatureToLine_management(grade_bounds, "grade_area_line")
grade_bound_3D = arcpy.sa.InterpolateShape(demExist, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

# Create TIN between graded piles and refine to graded area, and extract the 3D edges
tin_name_piles = str(outputPath + "\piles_TIN")
piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, "piles_graded demGrade masspoints")
tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line, None, "NEW_SELECTION", "INVERT")
tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace, "tinEdge_final")

# Create a TIN from the bound and piles layer
tin_name = str(outputPath + "\grade_TIN")
grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
grade_raster = arcpy.ddd.TinRaster(grade_TIN, "grade_raster","FLOAT", "NATURAL_NEIGHBORS", "CELLSIZE", 1, gridRes)

# Clip the grade raster to the grading areas
grade_only = arcpy.Clip_management(grade_raster,"","demGradeFinal_only", grade_bounds, "", "ClippingGeometry")

# Mosaic the clipped grading to demExist
# NEED TO FIX TO BE OUTPUT
grade_final = arcpy.management.MosaicToNewRaster([demExist,grade_only],workspace,"demGradeFinal", spatialRef,"32_BIT_FLOAT","",1,"LAST","FIRST")

# NEED TO OUTPUT GRADE BOUNDS
# NEED TO OUTPUT PILES, CLEAN UP FIELDS
# ADD IN CUT AND FILL OPTION
# ADD IN LANDXML OUTPUT OPTION
# NEED TO DO CLEAN UP OF FILES
# NEED TO ADD OPTIONS FOR METERS

# Clean up - check and see if in_memory works
# arcpy.management.Delete(rows_working)
# arcpy.management.Delete(newPointStats)
# arcpy.management.Delete(sumStats)
# arcpy.management.Delete(piles_working)
# arcpy.management.Delete(minTOP_elv_stats)
# arcpy.management.Delete(bound3Dpoints)
# arcpy.management.Delete(newBoundPoints)


