########################################################################
"""NORTH-SOUTH TRANSITION AND SHADING CHECKING TOOL

Description: Checks the ends of the rows for transition issues and shading

Revision log
0.0.1 - 12/01/2022 - Initial scripting
"""

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import math

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS 3.1.3"
__maintainer__  = ["Zane Nordquist"]
__status__      = "Testing"

class NSPOACheck(object):
    def __init__(self):
        self.label = "North-South Transition and Shading Checking Tool"
        self.description = "Checks the ends of the rows for transition issues and shading"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Checking Tools"
        
    def getParameterInfo(self):

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
            displayName="Plane of array or top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param3.parameterDependencies = [param2.name]
        
        param4 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["Feet", "Meters"]

        param5 = arcpy.Parameter(
            displayName="Slope measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["Percent", "Degrees", "Radians"]

        param6 = arcpy.Parameter(
            displayName="Maximum slope between ends of planes of array",
            name="maxPOAslope",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Output end of row point feature class",
            name="eorOutput",
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

        if not parameters[7].altered:
            parameters[7].value = "eorPOA_check"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        rowsInput           = parameters[0].valueAsText
        row_ID              = parameters[1].valueAsText
        pilesInput          = parameters[2].valueAsText
        poaField            = parameters[3].valueAsText
        xyzUnit             = parameters[4].valueAsText
        slopeUnits          = parameters[5].valueAsText
        maxPOAslope         = parameters[6].valueAsText
        eorOutput           = parameters[7].valueAsText
        
        outputPath = os.path.dirname(workspace)
        spatialRef = arcpy.Describe(rowsInput).spatialReference

        # Calculate north-south plane of array slope
        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

        # Add xy coordinates - will overwrite if already present
        arcpy.management.AddXY(piles_working)

        # Change poaField to TOP_elv_orig
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

        rowEndPoints = arcpy.management.CreateFeatureclass(workspace, "rowEndPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)

        arcpy.management.AddField(rowEndPoints, "PolygonOID", "LONG")
        arcpy.management.AddField(rowEndPoints, "Position", "TEXT")

        result = arcpy.GetCount_management(rowsInput)
        count = int(result.getOutput(0))

        insert_cursor = arcpy.da.InsertCursor(rowEndPoints, ["SHAPE@", "PolygonOID", "Position"])
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

        del insert_cursor
        del search_cursor

        eorInitial = arcpy.analysis.SpatialJoin(rowEndPoints, rowsInput, eorOutput, "JOIN_ONE_TO_ONE", "KEEP_ALL")

        arcpy.management.JoinField(eorInitial, row_ID, endPointStats, row_ID, [["MEAN_nsSlope"],["MEAN_bInit"]])

        arcpy.management.AddXY(eorInitial)

        arcpy.management.CalculateField(eorInitial, "poaEnd", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

        arcpy.management.DeleteField(eorInitial, ["MEAN_nsSlope", "MEAN_bInit"])
        arcpy.management.Delete(rowEndPoints)
        arcpy.management.Delete(coorStats)
        arcpy.management.Delete(endPointStats)
        arcpy.management.Delete(piles_working)
        arcpy.management.Delete(sumStats)

        eorPOA_N = arcpy.analysis.Select(eorInitial, "eorPOA_N", "Position = 'N'")
        eorPOA_S = arcpy.analysis.Select(eorInitial, "eorPOA_S", "Position = 'S'")

        arcpy.management.CalculateField(eorPOA_N, "poaEnd_NEAR_N", "!poaEnd!", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(eorPOA_S, "poaEnd_NEAR_S", "!poaEnd!", "PYTHON3", "","DOUBLE")

        arcpy.analysis.Near(eorPOA_N,eorPOA_S,"11 Feet","NO_LOCATION","NO_ANGLE","PLANAR","",xyzUnit)
        arcpy.analysis.Near(eorPOA_S,eorPOA_N,"11 Feet","NO_LOCATION","NO_ANGLE","PLANAR","",xyzUnit)

        arcpy.management.JoinField(eorPOA_N, "NEAR_FID", eorPOA_S, "OBJECTID", [["poaEnd_NEAR_S"], ["NEAR_DIST"]])
        arcpy.management.JoinField(eorPOA_S, "NEAR_FID", eorPOA_N, "OBJECTID", [["poaEnd_NEAR_N"], ["NEAR_DIST"]])
        
        eorOutput_feature = arcpy.management.Merge([[eorPOA_N],[eorPOA_S]], eorOutput)

        poaEndNearCode = """
def poaEnd(poaN, poaS):
    if poaN == None:
        return poaS
    else:
        return poaN
"""

        arcpy.management.CalculateField(eorOutput_feature, "poaEnd_NEAR", "poaEnd(!poaEnd_NEAR_S!,!poaEnd_NEAR_N!)", "PYTHON3", poaEndNearCode,"DOUBLE")

        # Calculate the delta between the planes of array
        arcpy.management.CalculateField(eorOutput_feature, "poaDelta", "!poaEnd! - !poaEnd_NEAR!", "PYTHON3", "","DOUBLE")

        # Add a Latitude field and calculate the value at each point
        arcpy.management.AddFields(eorOutput_feature, [["latitude", "DOUBLE"]])
        arcpy.management.CalculateGeometryAttributes(eorOutput_feature, "latitude POINT_Y", "", "", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]", "SAME_AS_INPUT")
        
        # Calculate the max and min deltas
        arcpy.management.CalculateField(eorOutput_feature, "maxDelta_shade", "abs(!NEAR_DIST!) * math.floor(math.pi * (90 - !latitude! - 23.5) / 180)", "PYTHON3", "", "DOUBLE")
        arcpy.management.CalculateField(eorOutput_feature, "minDelta_shade", "abs(!NEAR_DIST!) * math.ceil(math.pi * (-90 - !latitude! + 23.5) / 180)", "PYTHON3", "", "DOUBLE")

        if slopeUnits == "Degrees":
            arcpy.management.CalculateField(eorOutput_feature, "maxDelta_slope", "abs(!NEAR_DIST!) * "+maxPOAslope+" * math.pi / 180", "PYTHON3", "", "DOUBLE")
        if slopeUnits == "Percent":
            arcpy.management.CalculateField(eorOutput_feature, "maxDelta_slope", "abs(!NEAR_DIST!) * "+maxPOAslope+"/100", "PYTHON3", "", "DOUBLE")

        # Calculate if shading or over max slopes
        codeblockSlope = """
def deltaSlope(poaDelta, maxDelta_slope):
    if abs(poaDelta) > maxDelta_slope:
        return "Y"
    else:
        return "N"
"""

        arcpy.management.CalculateField(eorOutput_feature, "overMaxSlope", "deltaSlope(!poaDelta!, !maxDelta_slope!)", "PYTHON3", codeblockSlope, "TEXT")

        codeblockShade = """
def deltaShade(poaDelta, maxDelta_shade, minDelta_shade, position):
    if position == "S":
        if poaDelta > maxDelta_shade:
            return "Y"
        else:
            return "N"
    if position == "N":
        if poaDelta < minDelta_shade:
            return "Y"
        else:
            return "N"
"""
        arcpy.management.CalculateField(eorOutput_feature, "shading_NS", "deltaShade(!poaDelta!, !maxDelta_shade!, !minDelta_shade!, !Position!)", "PYTHON3", codeblockShade, "TEXT")

        aprxMap.addDataFromPath(eorOutput_feature)

        return