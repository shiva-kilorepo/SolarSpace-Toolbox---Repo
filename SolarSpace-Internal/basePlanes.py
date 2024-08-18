########################################################################
"""DERIVE BASE PLANES

Revision log
0.0.1 - 8/30/2021- Updated to match KN coding standards
0.0.2 - 2/14/2022 - Completely rebuilt, incorporated zones into algorithm, much faster
1.0.0 - 12/9/2022 - Converted to PYT format
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *

class BasePlanes(object):
    def __init__(self):
        self.label = "Derive Base Planes of Array"
        self.description = "Creates base planes for single axis tracker rows to derive grading, reveals, and the tracker plane of array"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input elevation raster dataset",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Tracker rows input feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Polygon"]

        param2 = arcpy.Parameter(
            displayName="Horizontal and vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Base plane raster output dataset",
            name="basePlanesBoundsOut",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param4 = arcpy.Parameter(
            displayName="Base plane raster output dataset",
            name="basePlanesOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            parameters[2].value = 'Foot'

        if not parameters[3].altered:
            parameters[3].value = 'basePlanesBounds'

        if not parameters[4].altered:
            parameters[4].value = 'basePlanes'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[2].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[2].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[2].value == "Meter":
                if "Meter" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[2].setErrorMessage("Vertical and horizontal units do not match")
            else:
                parameters[2].clearMessage()
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText  # Existing elevation in raster format
        rowsInput = parameters[1].valueAsText  # Array rows
        xyzUnit = parameters[2].valueAsText
        basePlanesBoundsOut = parameters[3].valueAsText  # Output boundary for base planes for checking
        basePlanesOut = parameters[4].valueAsText  # Output base planes

        outputPath = os.path.dirname(workspace)

        # Set the DEM as the snap raster and reference for grid resolution and spatial reference
        spatialRef = arcpy.Describe(demInput).spatialReference
        gridRes = arcpy.Describe(demInput).meanCellWidth
        arcpy.env.snapRaster = demInput
        mapUnits = spatialRef.linearUnitName

        arcpy.SetProgressor('default', 'Determining the ideal planes of array for each row...')

        # Call the base planes script - implement this later
        #sys.path.append(util_path)

        # Create corner points of the rows 
        rowCornerPoints = arcpy.management.CreateFeatureclass("in_memory", "rowCornerPoints", "POINT", "#", "DISABLED","DISABLED", rowsInput)
        arcpy.management.AddField(rowCornerPoints, "PolygonOID", "LONG")
        arcpy.management.AddField(rowCornerPoints, "Position", "TEXT")

        insert_cursor = arcpy.da.InsertCursor(rowCornerPoints, ["SHAPE@", "PolygonOID", "Position"])
        search_cursor = arcpy.da.SearchCursor(rowsInput, ["SHAPE@", "OID@"])

        for row in search_cursor:
            try:
                polygon_oid = str(row[1])

                coordinateList = []

                for part in row[0]:
                    for pnt in part:
                        if pnt:
                            coordinateList.append((pnt.X, pnt.Y))

                # Determine the extent of each row
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

            except Exception as err:
                arcpy.AddMessage(str(err.message))

        del insert_cursor
        del search_cursor

        arcpy.management.AddXY(rowCornerPoints)

        # Calculate new point coordinates
        codeblock_newXTG = """ 
def xNewTG(pos,x):
    if pos == "NW" or pos == "SW":
        return x - 10
    if pos == "NE" or pos == "SE":
        return x + 10
    """

        arcpy.management.CalculateField(rowCornerPoints, "xNewTG", "xNewTG(!Position!,!POINT_X!)", "PYTHON3",codeblock_newXTG, "DOUBLE")
        expTable = arcpy.conversion.TableToTable(rowCornerPoints, workspace, "expTable")
        expPoints = arcpy.management.XYTableToPoint(expTable, r"in_memory\expPoints", "xNewTG", "POINT_Y", None,spatialRef)

        tGroupExp = arcpy.management.MinimumBoundingGeometry(expPoints, "tGroupExp", "RECTANGLE_BY_AREA", "LIST","PolygonOID", "NO_MBG_FIELDS")
        tGroupDiss = arcpy.Dissolve_management(tGroupExp, "tGroupDiss")
        tGroup = arcpy.management.MultipartToSinglepart(tGroupDiss, "tGroup")
        arcpy.AddField_management(tGroup, "tGroup", "LONG")
        arcpy.management.CalculateField(tGroup, "tGroup", "!OBJECTID!", "PYTHON3", None)

        # Find distance between rows east-west
        rowsNear = arcpy.analysis.GenerateNearTable(rowsInput, rowsInput, r'in_memory\rowsNear', None, 'NO_LOCATION','ANGLE', 'ALL', 8, 'GEODESIC')

        codeblock_pos = """
def direction(angle, nearDist):
    if (angle < -80 and angle > -100) or (angle > 80 and angle < 100):
        return "delta_x"
    else:
        return "NA"
    """

        arcpy.management.CalculateField(rowsNear, 'delta_pos', 'direction(!NEAR_ANGLE!, !NEAR_DIST!)', 'PYTHON3', codeblock_pos, 'TEXT')

        near_stats = arcpy.analysis.Statistics(rowsNear, r'in_memory\near_stats', 'NEAR_DIST MIN','IN_FID; delta_pos')

        # Screen out outliers
        dist_x = arcpy.analysis.TableSelect(near_stats, r'in_memory\dist_x', "delta_pos = 'delta_x'")
        minMaxXRows = arcpy.analysis.Statistics(rowCornerPoints, r'in_memory\minMaxXRows', 'POINT_X MIN; POINT_X MAX','PolygonOID')
        arcpy.management.CalculateField(minMaxXRows, 'rowWidth', '(!MAX_POINT_X!- !MIN_POINT_X!)', 'PYTHON3', "", 'DOUBLE')

        arcpy.management.AlterField(dist_x, "MIN_NEAR_DIST", "delta_zone_x")
        screenTable = arcpy.conversion.TableToTable(dist_x, workspace, "screenTable")
        arcpy.management.JoinField(screenTable, 'IN_FID', minMaxXRows, 'PolygonOID', 'rowWidth')

        codeblock_screen = """
def xScreen(rowWidth,dX):
    if dX > 5 * rowWidth:
        return ""
    else:
        return dX
"""
        arcpy.management.CalculateField(screenTable, 'dXScreen', 'xScreen(!rowWidth!, !delta_zone_x!)', 'PYTHON3', codeblock_screen, 'DOUBLE')
        meanDx = arcpy.analysis.Statistics(screenTable, r'in_memory\meanDx', 'dXScreen MEAN')

        arcpy.management.CalculateField(screenTable, 'joinField', '1', 'PYTHON3', "", 'LONG')

        arcpy.management.JoinField(screenTable, 'joinField', meanDx, 'OBJECTID', 'MEAN_dXScreen')

        codeblock_dX_final = """
def dXfinal(dXScreen, dxMean):
    if dXScreen == None:
        return dxMean
    else:
        return dXScreen
"""
        arcpy.management.CalculateField(screenTable, 'dXfinal', 'dXfinal(!dXScreen!, !MEAN_dXScreen!)', 'PYTHON3', codeblock_dX_final, 'DOUBLE')

        arcpy.management.JoinField(rowCornerPoints, 'PolygonOID', screenTable, 'IN_FID', 'dXfinal')

        codeblock_nsDist = """
def direction(angle, nearDist):
    if ((angle < -175) or (angle >= 0 and angle < 5)) or (angle > 175 and angle < 185):
        return nearDist
    else:
        return ""
    """
        arcpy.management.CalculateField(rowsNear, 'delta_y', 'direction(!NEAR_ANGLE!, !NEAR_DIST!)', 'PYTHON3', codeblock_nsDist, 'DOUBLE')

        near_y_stats = arcpy.analysis.Statistics(rowsNear, r'in_memory\near_y_stats', "NEAR_DIST MIN")
        arcpy.management.AlterField(near_y_stats, "MIN_NEAR_DIST", "minYdist")

        arcpy.management.CalculateField(rowCornerPoints, 'joinField', '1', 'PYTHON3', "", 'LONG')

        arcpy.management.JoinField(rowCornerPoints, 'joinField', near_y_stats, 'OBJECTID', 'minYdist')

        arcpy.management.CalculateField(rowCornerPoints, 'gridRes', gridRes, 'PYTHON3', "", 'DOUBLE')

        # Calculate north-south distance expansion
        codeblock_nsDistSep = """
def nsExp(minYdist,gridRes):
    if minYdist > gridRes * 4:
        return 4
    else:
        return minYdist/2
    """

        arcpy.management.CalculateField(rowCornerPoints, 'nsExp', 'nsExp(!minYdist!,!gridRes!)', 'PYTHON3', codeblock_nsDistSep, 'DOUBLE')

        xFactor = "0.8"

        arcpy.SetProgressor('default', 'Creating new boundaries for planes...')

        # Calculate new point coordinates
        codeblock_newX = """
def xNew(pos,x,deltaX,xFactor):
    if pos == 'NW' or pos == 'SW':
        return x - deltaX*xFactor
    if pos == 'NE' or pos == 'SE':
        return x + deltaX*xFactor
    """

        arcpy.management.CalculateField(rowCornerPoints, 'xNew','xNew(!Position!,!POINT_X!,!dXfinal!,' + xFactor + ')', 'PYTHON3',codeblock_newX, "DOUBLE")

        codeblock_newY = """
def yNew(pos,y,ydist):
    if pos == 'NW' or pos == 'NE':
        return y + ydist
    if pos == 'SW' or pos == 'SE':
        return y - ydist
    """

        arcpy.management.CalculateField(rowCornerPoints, 'yNew', 'yNew(!Position!,!POINT_Y!,!nsExp!)', 'PYTHON3',codeblock_newY, "DOUBLE")
        new_points_table = arcpy.conversion.TableToTable(rowCornerPoints, workspace, 'new_points_table')
        new_points = arcpy.management.XYTableToPoint(new_points_table, r'in_memory\new_points', 'xNew', 'yNew', None,spatialRef)

        basePlane_bounds = arcpy.management.MinimumBoundingGeometry(new_points, basePlanesBoundsOut,'RECTANGLE_BY_AREA', 'LIST', 'PolygonOID','NO_MBG_FIELDS')

        aprxMap.addDataFromPath(basePlane_bounds)

        rowsGrouped = arcpy.analysis.SpatialJoin(basePlane_bounds, tGroup, "rowsGrouped", "JOIN_ONE_TO_ONE", "KEEP_ALL","", "INTERSECT", None, "")

        # Create scratch geodatabase for the base planes
        basePlaneScratchGDB = arcpy.management.CreateFileGDB(outputPath, "bpWorking.gdb", "CURRENT")

        arcpy.analysis.SplitByAttributes(rowsGrouped, basePlaneScratchGDB, "tGroup")

        # List feature classes
        scratchWS = arcpy.env.workspace = (outputPath + "/bpWorking.gdb")
        tGroupClasses = arcpy.ListFeatureClasses()

        for tG in tGroupClasses:
            try:
                demClip = arcpy.management.Clip(demInput, "", "demClip", tG)
                demPoint = arcpy.conversion.RasterToPoint(demClip, "demPoint", "Value")
                planes = arcpy.management.CreateRasterDataset(scratchWS, "planes" + "_" + tG, gridRes, "32_BIT_FLOAT", spatialRef, "1")
                with arcpy.da.SearchCursor(tG, "SHAPE@") as cursor:
                    for row in cursor:
                        demClipPoint = arcpy.analysis.Clip(demPoint, row[0], "demClipPoint")
                        outPlanes = arcpy.sa.Trend(demClipPoint, "grid_code", gridRes, 1, "LINEAR", None)
                        arcpy.Mosaic_management(outPlanes, planes, "MEAN")
            except Exception as err:
                arcpy.AddMessage(str(err.message))

        del cursor
        arcpy.management.Delete(demClip)

        # List all the rasters and mosaic them
        planesAll = arcpy.ListRasters()

        bpName = os.path.basename(basePlanesOut)

        baseplanesRaster = arcpy.management.MosaicToNewRaster(planesAll, workspace, bpName,spatialRef,"32_BIT_FLOAT",gridRes,1,"BLEND","FIRST")

        # Clean up
        arcpy.management.Delete(expTable)
        arcpy.management.Delete(new_points_table)
        arcpy.management.Delete(rowsGrouped)
        arcpy.management.Delete(screenTable)
        arcpy.management.Delete(tGroup)
        arcpy.management.Delete(tGroupDiss)
        arcpy.management.Delete(tGroupExp)
        arcpy.management.Delete(basePlaneScratchGDB)

        aprxMap.addDataFromPath(baseplanesRaster)

        
        return
