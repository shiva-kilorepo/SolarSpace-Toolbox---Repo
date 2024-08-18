############################################################
"""PLANE OF ARRAY EAST-WEST TOLERANCE CHECK

Revision log
0.0.1 - 02/14/2022 - Initial scripting
1.0.0 - 05/17/2022 - Updated metadata, released internally
1.0.1 - 05/20/2022 - Made outputPath automatically detect
2.0.0 - 02/07/2023 - Combined tools into one, converted into PYT format
2.0.1 - 03/09/2023 - Fixed minor reference error

FUTURE UPDATES - ADD SYMBOLOGY 
"""
__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "2.0.1"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.1.0"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
import math
from arcpy.sa import *
from arcpy.ddd import *

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

class poaEWcheck(object):
    def __init__(self):
        self.label = "Plane of Array East-West Tolerance Check"
        self.description = "Creates a raster that defines the slope east-west between the axis of single axis trackers for checking"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Checking Tools"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Tracker rows input feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param1.parameterDependencies = [param0.name]

        param2 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["Point"]

        param3 = arcpy.Parameter(
            displayName="Top of pile field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param2.name]

        param4 = arcpy.Parameter(
            displayName="Slope output measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["Percent", "Degrees"]

        param5 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["Foot", "Meter"]

        param6 = arcpy.Parameter(
            displayName="Output checking raster",
            name="rasterCheckOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param7 = arcpy.Parameter(
            displayName="Row output checking feature class",
            name="rowCheckOut",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap
        
        # Set parameters
        rowsInput = parameters[0].valueAsText
        row_ID = parameters[1].valueAsText
        pilesInput = parameters[2].valueAsText
        poaField = parameters[3].valueAsText
        slopeUnits = parameters[4].valueAsText
        xyzUnit = parameters[5].valueAsText
        rasterCheckOut = parameters[6].valueAsText
        rowCheckOut = parameters[7].valueAsText

        outputPath = os.path.dirname(workspace)
        spatialRef = arcpy.Describe(rowsInput).spatialReference

        # Calculate north-south plane of array slope
        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

        # Add xy coordinates - will overwrite if already present
        arcpy.management.AddXY(piles_working)

        # Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
        coorStatsInput = [[poaField, "MEAN"], ["POINT_Y", "MEAN"]]
        coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

        statPOAMean = "MEAN_" + poaField

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, [statPOAMean, "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(piles_working, "zy_bar","(!"+poaField+"! + !"+statPOAMean+"!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStats, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

        # Join slope to piles_working
        arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope"])

        # Find the intercept
        arcpy.management.CalculateField(piles_working, "bInit", "!"+poaField+"! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        endPointStats = arcpy.analysis.Statistics(piles_working, "endPointStats", [["bInit", "MEAN"],["nsSlope", "MEAN"]], row_ID)


        rowPoints = arcpy.management.CreateFeatureclass(workspace, "rowPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)

        arcpy.management.AddField(rowPoints, "PolygonOID", "LONG")
        arcpy.management.AddField(rowPoints, "Position", "TEXT")

        result = arcpy.GetCount_management(rowsInput)
        count = int(result.getOutput(0))

        insert_cursor = arcpy.da.InsertCursor(rowPoints, ["SHAPE@", "PolygonOID", "Position"])
        search_cursor = arcpy.da.SearchCursor(rowsInput, ["SHAPE@", "OID@"])

        for row in search_cursor:
            polygon_oid = str(row[1])

            coordinateList = []
            sw_dist = {}
            se_dist = {}
            nw_dist = {}
            ne_dist = {}

            for part in row[0]:
                for pnt in part:
                    if pnt:
                        coordinateList.append((pnt.X, pnt.Y))

            # Find the extent of each row
            rowExtent = row[0].extent

            sw_coordinate = rowExtent.lowerLeft
            se_coordinate = rowExtent.lowerRight
            nw_coordinate = rowExtent.upperLeft
            ne_coordinate = rowExtent.upperRight

            sw_point = arcpy.PointGeometry(sw_coordinate)
            se_point = arcpy.PointGeometry(se_coordinate)
            nw_point = arcpy.PointGeometry(nw_coordinate)
            ne_point = arcpy.PointGeometry(ne_coordinate)

            # Find the vertex closest to each corner of the row extent
            for vertex in coordinateList:
                vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                vertex_point = arcpy.PointGeometry(vertex_coordinates)
                sw_dist[float(sw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                se_dist[float(se_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                nw_dist[float(nw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                ne_dist[float(ne_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

            #Calculates where quarter quarter sections would intersect polygon
            swMinDist = min(sw_dist)
            seMinDist = min(se_dist)
            nwMinDist = min(nw_dist)
            neMinDist = min(ne_dist)

            sw_X = float(sw_dist[swMinDist][0])
            sw_Y = float(sw_dist[swMinDist][1])
            se_X = float(se_dist[seMinDist][0])
            se_Y = float(se_dist[seMinDist][1])

            nw_X = float(nw_dist[nwMinDist][0])
            nw_Y = float(nw_dist[nwMinDist][1])
            ne_X = float(ne_dist[neMinDist][0])
            ne_Y = float(ne_dist[neMinDist][1])

            north_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(nw_X, nw_Y), arcpy.Point(ne_X, ne_Y)]))
            south_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(sw_X, sw_Y), arcpy.Point(se_X, se_Y)]))

            north_row_end = north_bound_line.positionAlongLine(0.5, True)
            south_row_end = south_bound_line.positionAlongLine(0.5, True)

            insert_cursor.insertRow((north_row_end, polygon_oid, "N"))
            insert_cursor.insertRow((south_row_end, polygon_oid, "S"))

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

        rowPointsJoin = arcpy.analysis.SpatialJoin(rowPoints, rowsInput, "rowPointsJoin", "JOIN_ONE_TO_ONE", "KEEP_ALL")

        # Separate out end and corner points
        rowEndPoints = arcpy.analysis.Select(rowPointsJoin, "rowEndPoints", "Position = 'S' Or Position = 'N'")
        rowCornerPoints = arcpy.analysis.Select(rowPointsJoin, r"in_memory\rowCornerPoints","Position = 'NW' Or Position = 'NE' Or Position = 'SW' Or Position = 'SE'")

        arcpy.management.JoinField(rowEndPoints, row_ID, endPointStats, row_ID, [["MEAN_nsSlope"],["MEAN_bInit"]])

        arcpy.management.AddXY(rowEndPoints)

        arcpy.management.CalculateField(rowEndPoints, "poaEnd", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

        arcpy.management.Delete(coorStats)
        arcpy.management.Delete(endPointStats)
        arcpy.management.Delete(piles_working)
        arcpy.management.Delete(sumStats)
        
        # Make the end points 3d based on the POA
        rowEnd3d = arcpy.ddd.FeatureTo3DByAttribute(rowEndPoints, "in_memory/rowEnd3d", "poaEnd", None)
        
        # Create 3D lines
        axis_line = arcpy.management.PointsToLine(rowEnd3d, "axis_line", row_ID, None, "NO_CLOSE")

        # Create a TIN of the east-west slope between the axis lines
        tin_name = str(outputPath + "\poaEW_TIN")
        poaEW_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "axis_line Shape.Z Hard_Line")

        # Create the row domain and clip the TIN to the domain
        arcpy.management.AddXY(rowCornerPoints)

        # Calculate new point coordinates
        codeblock_newXTG = """ 
def xNew(pos,x):
    if pos == "NW" or pos == "SW":
        return x - 11
    if pos == "NE" or pos == "SE":
        return x + 11
    """

        arcpy.management.CalculateField(rowCornerPoints, "xNew", "xNew(!Position!,!POINT_X!)", "PYTHON3",codeblock_newXTG, "DOUBLE")
        expTable = arcpy.conversion.TableToTable(rowCornerPoints, workspace, "expTable")
        expPoints = arcpy.management.XYTableToPoint(expTable, r"in_memory\expPoints", "xNew", "POINT_Y", None,spatialRef)

        tGroupExp = arcpy.management.MinimumBoundingGeometry(expPoints, "tGroupExp", "RECTANGLE_BY_AREA", "LIST","PolygonOID", "NO_MBG_FIELDS")
        tGroupDiss = arcpy.Dissolve_management(tGroupExp, "tGroupDiss")

        poaBounds = arcpy.analysis.GraphicBuffer(tGroupDiss, "poaBounds", "-11 Feet", "SQUARE", "MITER", 10, "0 Feet")

        # Clip the raster to the row domain
        arcpy.ddd.EditTin(poaEW_TIN,  "poaBounds <None> <None> Hard_Clip false", "DELAUNAY")

        # Convert to a raster
        poaRaster = arcpy.ddd.TinRaster(poaEW_TIN, "poaRaster", "FLOAT", "LINEAR", "CELLSIZE", 1,1)

        # Derive slope
        # Process aspect in radians
        AspectRad = arcpy.sa.Aspect(poaRaster,"PLANAR",xyzUnit) * math.pi / 180

        # Process slope in radians
        SlopeRad = arcpy.sa.Slope(poaRaster,"DEGREE","1","PLANAR",xyzUnit) * math.pi / 180

        if slopeUnits == "Percent":
            ewSlope = Tan( Sin( AspectRad) * SlopeRad) * 100
            ewSlope.save(rasterCheckOut)

        if slopeUnits == "Degrees":
            ewSlope = Sin( AspectRad) * SlopeRad * 180 / math.pi
            ewSlope.save(rasterCheckOut)

        aprxMap.addDataFromPath(ewSlope)

        rowsOutName = os.path.basename(rowCheckOut)

        rowsOutput = arcpy.conversion.FeatureClassToFeatureClass(rowsInput, workspace, rowsOutName)

        # Get the statistics of the slope of the POA
        ewStats_PoA = arcpy.sa.ZonalStatisticsAsTable(rowsOutput, row_ID, ewSlope, "ewStats_PoA", "DATA", "ALL", "CURRENT_SLICE", 90, "AUTO_DETECT")

        # Join back to the rows and rename the fields
        arcpy.management.JoinField(rowsOutput, row_ID, ewStats_PoA, row_ID, "MAX;MEAN;MIN")

        arcpy.management.AlterField(rowsOutput, "MAX", "maxSlope_" + slopeUnits, '', "DOUBLE", 4, "NULLABLE", "CLEAR_ALIAS")
        arcpy.management.AlterField(rowsOutput, "MIN", "minSlope_" + slopeUnits, '', "DOUBLE", 4, "NULLABLE", "CLEAR_ALIAS")
        arcpy.management.AlterField(rowsOutput, "MEAN", "meanSlope_" + slopeUnits, '', "DOUBLE", 4, "NULLABLE", "CLEAR_ALIAS")

        # CONVERT RASTER TO POLYGON, ERASE FROM ROWS, DETERMINE HOW MUCH OF ROW IS OUT OF TOLERANCE
        # SET LIMIT OR MAKE AN INPUT
        # SYMBOLIZE ROWS BY IF AN ISSUE/NOT AN ISSUE, SYMBOLIZE RASTER

        # Add results to map
        aprxMap.addDataFromPath(rowsOutput)

        arcpy.management.Delete(poaEW_TIN)
        
        return


