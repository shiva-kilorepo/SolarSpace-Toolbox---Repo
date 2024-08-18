############################################################
"""DERIVE PLANE OF ARRAY ROW END POINTS FROM PILES

Revision log
0.0.1 - 12/06/2022 - Initial scripting
1.0.0 - 12/29/2022 - Conversion to Python toolbox format
1.1.0 - 12/12/2023 - Added calculation of "reveals" and grading at pile end points
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.1.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.1.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import sys
import os

class poaRowEnds(object):
    def __init__(self):
        self.label = "Derive POA at Row Ends from Piles"
        self.description = "Derives the plane of array at the end of rows as points from piles with a top of pile/plane of array height field"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Civil Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input row feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Unique row ID",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param1.parameterDependencies = [param0.name]

        param2 = arcpy.Parameter(
            displayName="Input pile feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["Point"]

        param3 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["Foot", "Meter"]

        param4 = arcpy.Parameter(
            displayName="Top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.parameterDependencies = [param2.name]

        param5 = arcpy.Parameter(
            displayName="Input existing elevation raster",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Output end of row point feature class",
            name="endofRowPt_out",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")
            
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[8].altered:
            parameters[8].value = "eorPOA"

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
        rowsInput       = parameters[0].valueAsText
        row_ID          = parameters[1].valueAsText
        pilesInput      = parameters[2].valueAsText
        xyzUnit         = parameters[3].valueAsText  
        poaField        = parameters[4].valueAsText
        demInput        = parameters[5].valueAsText  
        minReveal       = parameters[6].valueAsText  
        maxReveal       = parameters[7].valueAsText 
        endofRowPt_out  = parameters[8].valueAsText

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

        eorOutput = arcpy.analysis.SpatialJoin(rowEndPoints, rowsInput, endofRowPt_out, "JOIN_ONE_TO_ONE", "KEEP_ALL")

        arcpy.management.JoinField(eorOutput, row_ID, endPointStats, row_ID, [["MEAN_nsSlope"],["MEAN_bInit"]])

        arcpy.management.AddXY(eorOutput)

        arcpy.management.CalculateField(eorOutput, "poaEnd", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

        arcpy.management.DeleteField(eorOutput, ["MEAN_nsSlope", "MEAN_bInit"])
        arcpy.management.Delete(rowEndPoints)
        arcpy.management.Delete(coorStats)
        arcpy.management.Delete(endPointStats)
        arcpy.management.Delete(piles_working)
        arcpy.management.Delete(sumStats)

        # Determine valid grading at the points
        arcpy.sa.ExtractMultiValuesToPoints(eorOutput,[[demInput, "demExist"]], "BILINEAR")
        
        codeblock_grade = """ 
def grade(topE, EG, minR, maxR):
    if (topE - EG) > maxR:
        return topE - maxR
    if (topE - EG) < minR:
        return TopE - minR
    else:
        return EG

"""

        arcpy.management.CalculateField(eorOutput, "demGrade_eor", "grade(!"+poaField+"!, !demExist!, "+minReveal+", "+maxReveal+")", "PYTHON3", codeblock_grade, "FLOAT")

        aprxMap.addDataFromPath(eorOutput)

        return