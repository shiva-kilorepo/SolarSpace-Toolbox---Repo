############################################################
"""TERRAIN LOSSES

Revision log
0.0.1 - 08/05/2022 - Revised POA script for mechical blocks rather than inverters
1.0.0 - 08/10/2022 - Internal release
1.1.0 - 03/30/2023 - Converted to PYT format, added external slope down 1 foot external/exposed rows, combined all terrain loss scripts into one
2.0.0 - 12/12/2023 - Added ability for blocks and strings production calculations
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "2.0.0"
__license__     = "Internal"
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
import numpy as np

class terrainLoss(object):
    def __init__(self):
        self.label = "Calculate Terrain Losses"
        self.description = "Calculates production-based losses from the plane of array or from the terrain"
        self.canRunInBackground = False
        self.category = "SolarAnalytics"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Analyze strings or tracker rows?",
            name="strings_or_rows",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param0.filter.type = "ValueList"
        param0.filter.list = ["Tracker rows", "Strings"]

        param1 = arcpy.Parameter(
            displayName="Tracker rows input feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Polygon"]

        param2 = arcpy.Parameter(
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param1.name]

        param3 = arcpy.Parameter(
            displayName="Strings input feature class",
            name="stringsInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param3.filter.list = ["Polygon"]

        param4 = arcpy.Parameter(
            displayName="Unique string ID field",
            name="string_ID",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param4.parameterDependencies = [param3.name]

        param5 = arcpy.Parameter(
            displayName="Strings per full row",
            name="stringsRow",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Modules per string",
            name="modsString",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Module power (W)",
            name="modPower",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Terrain-based or plane of array-based",
            name="poaTerrainOption",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param8.filter.type = "ValueList"
        param8.filter.list = ["Terrain-based", "Plane of array-based"]

        param9 = arcpy.Parameter(
            displayName="Elevation raster dataset",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Optional",
            direction="Input")

        param10 = arcpy.Parameter(
            displayName="Number of standard deviations",
            name="numbSTDs",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        param11 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param11.filter.list = ["Point"]

        param12 = arcpy.Parameter(
            displayName="Plane of array or top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param12.parameterDependencies = [param11.name]

        param13 = arcpy.Parameter(
            displayName="Use the maximum or mean of the north-south slope?",
            name="maxMeanSlope",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param13.filter.type = "ValueList"
        param13.filter.list = ["MAXIMUM", "MEAN"]

        param14 = arcpy.Parameter(
            displayName="Rows/strings or mechanical blocks",
            name="rowsBlocksOption",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["Rows/strings", "Mechanical blocks"]

        param15 = arcpy.Parameter(
            displayName="Mechanical blocks input feature class",
            name="blockInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param15.filter.list = ["Polygon"]

        param16 = arcpy.Parameter(
            displayName="Unique block ID field",
            name="blockID",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param16.parameterDependencies = [param15.name]

        param17 = arcpy.Parameter(
            displayName="Specific production (kWh/year)",
            name="specProd",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param18 = arcpy.Parameter(
            displayName="East-west variable",
            name="ewVar",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param19 = arcpy.Parameter(
            displayName="North-south intercept",
            name="nsVarA",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param20 = arcpy.Parameter(
            displayName="North-south slope",
            name="nsVarB",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param21 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Foot", "Meter"]

        param22 = arcpy.Parameter(
            displayName="Mechanical block output feature class",
            name="blockOutput",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output")

        param23 = arcpy.Parameter(
            displayName="Rows output feature class",
            name="rowsOutput",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output")

        param24 = arcpy.Parameter(
            displayName="Strings output feature class",
            name="stringsOutput",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output")

        param25 = arcpy.Parameter(
            displayName="Summary table",
            name="summaryOut",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14, param15, param16, param17, param18, param19, param20, param21, param22, param23, param24, param25]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[0].altered:
            parameters[0].value = "Tracker rows"

        if parameters[0].value == "Tracker rows":
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[23].enabled = True
            parameters[24].enabled = False
        if parameters[0].value == "Strings":
            parameters[3].enabled = True
            parameters[4].enabled = True
            parameters[23].enabled = False
            parameters[24].enabled = True

        if not parameters[8].altered:
            parameters[8].value = "Terrain-based"

        if not parameters[10].altered:
            parameters[10].value = "4"

        if not parameters[13].altered:
            parameters[13].value = "MEAN"

        if parameters[8].value == "Terrain-based":
            parameters[9].enabled = True
            parameters[10].enabled = True
            parameters[11].enabled = False
            parameters[12].enabled = False
        if parameters[8].value == "Plane of array-based":
            parameters[9].enabled = False
            parameters[10].enabled = False
            parameters[11].enabled = True
            parameters[12].enabled = True

        if parameters[14].value == "Mechanical blocks":
            parameters[15].enabled = True
            parameters[16].enabled = True
            parameters[22].enabled = True
        else:
            parameters[15].enabled = False
            parameters[16].enabled = False
            parameters[22].enabled = False

        if not parameters[22].altered:
            parameters[22].value = "prodBlocks"

        if not parameters[23].altered:
            parameters[23].value = "prodRows"

        if not parameters[24].altered:
            parameters[24].value = "prodStrings"

        if not parameters[25].altered:
            parameters[25].value = "prodSummary"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].value == "Tracker rows":
            if not parameters[1].valueAsText:
                parameters[1].setIDMessage("ERROR", 735)
            if not parameters[2].valueAsText:
                parameters[2].setIDMessage("ERROR", 735)

        if parameters[0].value == "Strings":
            if not parameters[3].valueAsText:
                parameters[3].setIDMessage("ERROR", 735)
            if not parameters[4].valueAsText:
                parameters[4].setIDMessage("ERROR", 735)

        if parameters[8].value == "Terrain-based":
            if not parameters[9].valueAsText:
                parameters[9].setIDMessage("ERROR", 735)
            if not parameters[10].valueAsText:
                parameters[10].setIDMessage("ERROR", 735)
                
        if parameters[8].value == "Plane of array-based":
            if not parameters[11].valueAsText:
                parameters[11].setIDMessage("ERROR", 735)
            if not parameters[12].valueAsText:
                parameters[12].setIDMessage("ERROR", 735)

        if parameters[14].value == "Mechanical blocks":
            if not parameters[15].valueAsText:
                parameters[15].setIDMessage("ERROR", 735)
            if not parameters[16].valueAsText:
                parameters[16].setIDMessage("ERROR", 735)
            if not parameters[22].valueAsText:
                parameters[22].setIDMessage("ERROR", 735)

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        strings_or_rows     = parameters[0].valueAsText
        rowsInput           = parameters[1].valueAsText
        row_ID              = parameters[2].valueAsText
        stringsInput        = parameters[3].valueAsText
        string_ID           = parameters[4].valueAsText
        stringsRow          = parameters[5].valueAsText
        modsString          = parameters[6].valueAsText
        modPower            = parameters[7].valueAsText
        poaTerrainOption    = parameters[8].valueAsText
        demInput            = parameters[9].valueAsText
        numbSTDs            = parameters[10].valueAsText
        pilesInput          = parameters[11].valueAsText
        poaField            = parameters[12].valueAsText
        maxMeanSlope        = parameters[13].valueAsText
        rowsBlocksOption    = parameters[14].valueAsText
        blockInput          = parameters[15].valueAsText
        blockID             = parameters[16].valueAsText
        specProd            = parameters[17].valueAsText
        ewVar               = parameters[18].valueAsText
        nsVarA              = parameters[19].valueAsText
        nsVarB              = parameters[20].valueAsText
        xyzUnit             = parameters[21].valueAsText
        blockOutput         = parameters[22].valueAsText
        rowsOutput          = parameters[23].valueAsText
        stringsOutput       = parameters[24].valueAsText
        prodSummary         = parameters[25].valueAsText
        
        if strings_or_rows == "Tracker rows":
            poaNSInput = rowsInput
            poaEWInput = rowsInput
            ns_ID = row_ID
            ew_ID = row_ID
        else:
            poaNSInput = stringsInput
            poaEWInput = rowsInput
            ns_ID = string_ID
            ew_ID = row_ID
            
        if maxMeanSlope == "MEAN":
            slopeField = "MEAN_nsSlope"
            slopeOutput = "MEAN_nsSlope"
        else:
            slopeField = "MAX_nsSlope"
            slopeOutput = "MAX_nsSlope"

        outputPath = os.path.dirname(workspace)
        spatialRef = arcpy.Describe(rowsInput).spatialReference

        # Copy input rows to preserve original input
        if strings_or_rows == "Tracker rows":
            prodRowsOut = os.path.basename(rowsOutput)
            prodRows = arcpy.conversion.FeatureClassToFeatureClass(rowsInput,workspace,prodRowsOut)
            # Determine the number of strings for each row
            arcpy.management.CalculateField(prodRows, "numStrings","!Shape_Area!/"+stringsRow+"", "PYTHON3", "","LONG")
            arcpy.management.CalculateField(prodRows, "power_kW","!numStrings! * "+modPower+" * "+modsString+"/1000", "PYTHON3", "","FLOAT")

        if strings_or_rows == "Strings":
            prodStringsOut = os.path.basename(stringsOutput)
            prodStrings = arcpy.conversion.FeatureClassToFeatureClass(stringsInput,workspace,prodStringsOut)
            arcpy.management.CalculateField(prodStrings, "numStrings","1", "PYTHON3", "","LONG")
            arcpy.management.CalculateField(prodStrings, "power_kW","!numStrings! * "+modPower+" * "+modsString+"/1000", "PYTHON3", "","FLOAT")

        if poaTerrainOption == "Terrain-based":
            gridRes = arcpy.Describe(demInput).meanCellWidth
            arcpy.env.snapRaster = demInput

            # Process aspect
            AspectDEM = arcpy.sa.SurfaceParameters(
                in_raster=demInput,
                parameter_type="ASPECT",
                local_surface_type="QUADRATIC",
                neighborhood_distance="3 Feet",
                use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
                z_unit=xyzUnit,
                output_slope_measurement="DEGREE",
                project_geodesic_azimuths="GEODESIC_AZIMUTHS",
                use_equatorial_aspect="NORTH_POLE_ASPECT",
                in_analysis_mask=None
            )

            AspectRad = AspectDEM * math.pi / 180

            # Process slope
            terrainSlopeRaster = arcpy.sa.SurfaceParameters(
                in_raster=demInput,
                parameter_type="SLOPE",
                local_surface_type="QUADRATIC",
                use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
                z_unit=xyzUnit,
                output_slope_measurement="DEGREE",
                project_geodesic_azimuths="GEODESIC_AZIMUTHS",
                use_equatorial_aspect="NORTH_POLE_ASPECT",
                in_analysis_mask=None
            )
            
            SlopeRad = terrainSlopeRaster * math.pi / 180

            # Process north-south and east-west slope in degrees
            ewSlope = Sin(AspectRad) * SlopeRad * 180 / math.pi
            nsSlope = Cos(AspectRad) * SlopeRad * 180 / math.pi

            nsStats = arcpy.sa.ZonalStatisticsAsTable(poaNSInput,ns_ID,nsSlope,r"in_memory\nsStats","DATA","ALL")

            if strings_or_rows == "Tracker rows":
                arcpy.management.JoinField(prodRows,ns_ID,nsStats,ns_ID,[["MEAN"],["MAX"]])
                arcpy.management.AlterField(prodRows, "MEAN", "MEAN_nsSlope", "MEAN_nsSlope")
                arcpy.management.AlterField(prodRows, "MAX", "MAX_nsSlope", "MAX_nsSlope")
            if strings_or_rows == "Strings":
                arcpy.management.JoinField(prodStrings,ns_ID,nsStats,ns_ID,[["MEAN"],["MAX"]])
                arcpy.management.AlterField(prodStrings, "MEAN", "MEAN_nsSlope", "MEAN_nsSlope")
                arcpy.management.AlterField(prodStrings, "MAX", "MAX_nsSlope", "MAX_nsSlope")

        if poaTerrainOption == "Plane of array-based":

            poaPoints = arcpy.management.CreateFeatureclass(workspace, "poaPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)

            arcpy.management.AddField(poaPoints, "PolygonOID", "LONG")
            arcpy.management.AddField(poaPoints, "Position", "TEXT")

            result = arcpy.GetCount_management(rowsInput)
            count = int(result.getOutput(0))

            insert_cursor = arcpy.da.InsertCursor(poaPoints, ["SHAPE@", "PolygonOID", "Position"])
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

            rowPointsJoin = arcpy.analysis.SpatialJoin(poaPoints, rowsInput, "rowPointsJoin", "JOIN_ONE_TO_ONE", "KEEP_ALL")

            # Separate out end and corner points
            rowEndPoints = arcpy.analysis.Select(rowPointsJoin, "rowEndPoints", "Position = 'S' Or Position = 'N'")
            rowCornerPoints = arcpy.analysis.Select(rowPointsJoin, r"in_memory\rowCornerPoints","Position = 'NW' Or Position = 'NE' Or Position = 'SW' Or Position = 'SE'")

            piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")
            arcpy.management.AddXY(piles_working)


            if strings_or_rows == "Tracker rows":

                # Summary Statistics by ns_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
                coorStatsInput = [[poaField, "MEAN"], ["POINT_Y", "MEAN"]]
                coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

                statPOAMean = "MEAN_" + poaField

                # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
                arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, [statPOAMean, "MEAN_POINT_Y"])

                # Calculate zy_bar, y_ybar_sq
                arcpy.management.CalculateField(piles_working, "zy_bar","(!"+poaField+"! + !"+statPOAMean+"!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","FLOAT")
                arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","FLOAT")

                # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
                sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

                # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
                arcpy.management.CalculateField(sumStats, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","FLOAT")

                # Join slope to piles_working
                arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope"])

                # Find the intercept
                arcpy.management.CalculateField(piles_working, "bInit", "!"+poaField+"! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "FLOAT")

                endPointStats = arcpy.analysis.Statistics(piles_working, "endPointStats", [["bInit", "MEAN"],["nsSlope", maxMeanSlope]], row_ID)
                
                # Join the ns slope to the rows for calculations
                arcpy.management.JoinField(prodRows, row_ID, endPointStats, row_ID, [slopeField])
                arcpy.management.CalculateField(prodRows, slopeOutput, "180 * math.atan(!"+slopeField+"!) / math.pi", "PYTHON3", "", "FLOAT")

                arcpy.management.JoinField(rowEndPoints, row_ID, endPointStats, row_ID, [[slopeField],["MEAN_bInit"]])

                arcpy.management.AddXY(rowEndPoints)

                arcpy.management.CalculateField(rowEndPoints, "poaEnd", "!"+slopeField+"! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "FLOAT")

                # Make the end points 3d based on the POA
                rowEnd3d = arcpy.ddd.FeatureTo3DByAttribute(rowEndPoints, "in_memory/rowEnd3d", "poaEnd", None)

                # Create 3D lines
                axis_line = arcpy.management.PointsToLine(rowEnd3d, "axis_line", row_ID, None, "NO_CLOSE")

            if strings_or_rows == "Strings":

                poaPointsStrings = piles_working

                # Make the end points 3d based on the POA
                poaPoint3D = arcpy.ddd.FeatureTo3DByAttribute(poaPointsStrings, "in_memory/poaPoint3D", poaField, None)

                # Create 3D lines
                axis_line = arcpy.management.PointsToLine(poaPoint3D, "axis_line", row_ID, None, "NO_CLOSE")

            # Determine the spacing east-west
            ewSpacingAxis = arcpy.analysis.GenerateNearTable(axis_line, axis_line, "ewSpacingAxis", "30 Feet", "NO_LOCATION", "ANGLE", "ALL", 4, "PLANAR")

            # Select only those that are east-west
            ewSpacingAxis_ewONLY = arcpy.analysis.TableSelect(
                in_table=ewSpacingAxis,
                out_table="ewSpacingAxis_ewONLY",
                where_clause="""(NEAR_ANGLE >= 0 AND NEAR_ANGLE <  2) OR (NEAR_ANGLE <= 0 AND NEAR_ANGLE > -2) OR (NEAR_ANGLE >= -180 AND NEAR_ANGLE < -178) OR (NEAR_ANGLE <= 180 AND NEAR_ANGLE > 178)"""
            )

            # Take the average of the spacing
            spacingAvg = arcpy.analysis.Statistics(ewSpacingAxis_ewONLY, "spacingAvg", "NEAR_DIST MEAN")

            # Get the max length of the rows and define a distance to expand them by
            with arcpy.da.SearchCursor(spacingAvg, "MEAN_NEAR_DIST") as cursor:
                meanEWDist = max(cursor)
            meanEWDist = float(".".join(str(elem) for elem in meanEWDist))

            axisEast = arcpy.conversion.FeatureClassToFeatureClass(axis_line, workspace, "axisEast")
            axisWest = arcpy.conversion.FeatureClassToFeatureClass(axis_line, workspace, "axisWest")

            west_shift = -1 * meanEWDist

            with arcpy.da.UpdateCursor(axisEast, ["SHAPE@XY"]) as cursor:
                for row in cursor:
                    cursor.updateRow([[row[0][0] + (meanEWDist or 0),
                                       row[0][1]]])
                    
            with arcpy.da.UpdateCursor(axisWest, ["SHAPE@XY"]) as cursor:
                for row in cursor:
                    cursor.updateRow([[row[0][0] + (west_shift or 0),
                                       row[0][1]]])

            arcpy.management.Adjust3DZ(axisEast, "NO_REVERSE", "-1")
            arcpy.management.Adjust3DZ(axisWest, "NO_REVERSE", "-1")

            axisEast_input = arcpy.management.SelectLayerByLocation(axisEast, "INTERSECT", rowsInput,"" , "NEW_SELECTION", "INVERT")
            axisWest_input = arcpy.management.SelectLayerByLocation(axisWest, "INTERSECT", rowsInput, "", "NEW_SELECTION", "INVERT")

            axisLinesAll = arcpy.management.Merge([[axisEast_input],[axisWest_input],[axis_line]], "axisLinesAll")

            # Create a TIN of the east-west slope between the axis lines
            tin_name = str(outputPath + "\poaEW_TIN")
            poaEW_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "axisLinesAll Shape.Z Hard_Line")

            # Create the row domain and clip the TIN to the domain
            arcpy.management.AddXY(rowCornerPoints)

            # Calculate new point coordinates
            codeblock_newXTG = """ 
def xNew(pos,x,ctc):
    if pos == "NW" or pos == "SW":
        return x - ctc - 15
    if pos == "NE" or pos == "SE":
        return x + ctc + 15
"""

            if xyzUnit == "Foot":
                xyzUnitAlt = "Feet"
            else:
                xyzUnitAlt = xyzUnit

            boundFactor = 1.1 * meanEWDist/2
            boundFactorInput = str(boundFactor) + " " + xyzUnitAlt
            axixBounds = arcpy.analysis.GraphicBuffer(axisLinesAll, "poaBounds", boundFactorInput, "SQUARE", "MITER", 10, "0 Feet")

            axixBoundsDiss = arcpy.analysis.PairwiseDissolve(axixBounds, "axixBoundsDiss", "", "", "SINGLE_PART")

            boundFactorInvInput = - 0.9 * meanEWDist/2
            poaBounds = arcpy.analysis.GraphicBuffer(axixBoundsDiss, "poaBounds", boundFactorInvInput, "SQUARE", "MITER", 10, "0 Feet")

            # Clip the raster to the row domain
            arcpy.ddd.EditTin(poaEW_TIN,  "poaBounds <None> <None> Hard_Clip false", "DELAUNAY")

            # Convert to a raster
            poaEWRaster = arcpy.ddd.TinRaster(poaEW_TIN, "poaEWRaster", "FLOAT", "LINEAR", "CELLSIZE", 1,1)

            # Derive slope
            # Process aspect in radians
            AspectDEM = arcpy.sa.SurfaceParameters(
                in_raster=poaEWRaster,
                parameter_type="ASPECT",
                local_surface_type="QUADRATIC",
                neighborhood_distance="3 Feet",
                use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
                z_unit=xyzUnit,
                output_slope_measurement="DEGREE",
                project_geodesic_azimuths="GEODESIC_AZIMUTHS",
                use_equatorial_aspect="NORTH_POLE_ASPECT",
                in_analysis_mask=None
            )
       
        
            AspectRad = AspectDEM * math.pi / 180

            # Process slope in radians
            SlopeRaster = arcpy.sa.SurfaceParameters(
                in_raster=poaEWRaster,
                parameter_type="SLOPE",
                local_surface_type="QUADRATIC",
                use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
                z_unit=xyzUnit,
                output_slope_measurement="DEGREE",
                project_geodesic_azimuths="GEODESIC_AZIMUTHS",
                use_equatorial_aspect="NORTH_POLE_ASPECT",
                in_analysis_mask=None
            )

            SlopeRad = SlopeRaster * math.pi / 180

            # Process the east-west slope in degrees
            ewSlope = Sin( AspectRad) * SlopeRad * 180 / math.pi
        
            if strings_or_rows == "Strings":
                nsSlope = Cos( AspectRad) * SlopeRad * 180 / math.pi
                nsStringBuffer = -2
                nsStringClip = arcpy.analysis.GraphicBuffer(stringsInput,  r"in_memory\nsStringClip", nsStringBuffer)
                nsStringStats = arcpy.sa.ZonalStatisticsAsTable(nsStringClip, string_ID, nsSlope, "nsStringStats", "DATA", "ALL")

                # Join the ns stats to the strings
                arcpy.management.JoinField(prodStrings,string_ID,nsStringStats,string_ID,[["MAX"],["MEAN"]])
                arcpy.management.AlterField(prodStrings, "MEAN", "MEAN_nsSlope", "MEAN_nsSlope")
                arcpy.management.AlterField(prodStrings, "MAX", "MAX_nsSlope", "MAX_nsSlope")

        if rowsBlocksOption == "Mechanical blocks":

            if strings_or_rows == "Tracker rows":
                # Calculate the power per block
                prodBlocks = arcpy.analysis.SummarizeWithin(blockInput, prodRows, blockOutput, "KEEP_ALL", "power_kW Sum")
            if strings_or_rows == "Strings":
                # Calculate the power per block
                prodBlocks = arcpy.analysis.SummarizeWithin(blockInput, prodStrings, blockOutput, "KEEP_ALL", "power_kW Sum")

            # Calculate east-west statistics, north-south statistics, add production and loss fields
            ewStatsBlocks = arcpy.sa.ZonalStatisticsAsTable(prodBlocks,blockID,ewSlope,r"in_memory\ewStatsBlocks","DATA","ALL")

            if poaTerrainOption == "Terrain-based":
                nsStatsBlocks = arcpy.sa.ZonalStatisticsAsTable(prodBlocks,blockID,nsSlope,r"in_memory\nsStatsBlocks","DATA","ALL")
                arcpy.management.CalculateField(ewStatsBlocks, "prod_ew", ""+specProd+" + "+ewVar+" * (abs(0.5*!STD! * "+numbSTDs+"))", "PYTHON3","", "FLOAT")
                arcpy.management.JoinField(prodBlocks,blockID,ewStatsBlocks,blockID,["STD","prod_ew"])
                arcpy.management.AlterField(prodBlocks, "STD", "STD_ewSlope", "STD_ewSlope")
                arcpy.management.CalculateField(prodBlocks,"numSTDs",""+numbSTDs+"", "PYTHON3", "", "LONG")
                arcpy.management.AlterField(nsStatsBlocks, "MEAN", slopeOutput, slopeOutput)

            if poaTerrainOption == "Plane of array-based":
                if strings_or_rows == "Tracker rows":
                    nsStatsBlocks = arcpy.analysis.SummarizeWithin(prodBlocks, prodRows, r"in_memory\nsStatsBlocks", "KEEP_ALL", [[slopeOutput, "MEAN"]])
                if strings_or_rows == "Strings":
                    nsStatsBlocks = arcpy.analysis.SummarizeWithin(prodBlocks, prodStrings, r"in_memory\nsStatsBlocks", "KEEP_ALL", [[slopeOutput, "MEAN"]]) 
                    meanSlopeStat = "mean_" + slopeOutput   
                    arcpy.management.AlterField(nsStatsBlocks, meanSlopeStat, slopeOutput, slopeOutput)
                arcpy.management.CalculateField(ewStatsBlocks, "prod_ew", ""+specProd+" + "+ewVar+" * (abs(0.5*!RANGE!))", "PYTHON3","", "FLOAT")
                arcpy.management.JoinField(prodBlocks,blockID,ewStatsBlocks,blockID,["RANGE","prod_ew"])
                arcpy.management.AlterField(prodBlocks, "RANGE", "RANGE_nsSlope", "RANGE_nsSlope")

            # Calculate east-west losses negative means loss, there should be no positive
            arcpy.management.CalculateField(prodBlocks,"loss_ew","(1 - !prod_ew!/"+specProd+")*-100", "PYTHON3","", "FLOAT")

            # Join production and losses to production layer, join north-south statistic to production layer
            arcpy.management.JoinField(prodBlocks,blockID,nsStatsBlocks,blockID,[slopeOutput])

            # Calculate north-south production
            arcpy.management.CalculateField(prodBlocks,"prod_ns",""+specProd+"-"+nsVarA+" * !"+slopeOutput+"! + "+nsVarB+" * pow(!"+slopeOutput+"!,2)","PYTHON3","", "FLOAT")

            # Calculate north-south losses - Negative means loss
            arcpy.management.CalculateField(prodBlocks,"loss_ns","(1-!prod_ns!/"+specProd+")*-100","PYTHON3","", "FLOAT")

            # Calculate production from both east-west and north-south
            arcpy.management.CalculateField(prodBlocks,"prod_ewns","!prod_ew! + (!prod_ns!-"+specProd+")","PYTHON3","", "FLOAT")

            # Calculate losses from both east-west and north-south
            arcpy.management.CalculateField(prodBlocks,"loss_ewns","(1 - !prod_ewns!/"+specProd+")*-100","PYTHON3","", "FLOAT")

            arcpy.management.CalculateField(prodBlocks,"annual_prod_MWh","!sum_power_kW! * !prod_ewns!/1000","PYTHON3","", "FLOAT")

            aprxMap.addDataFromPath(prodBlocks)

            # Clean up
            arcpy.management.Delete(ewStatsBlocks)
            arcpy.management.Delete(nsStatsBlocks)

        # Calculate east-west statistics, north-south statistics, add production and loss fields
        arcpy.AddMessage("Calculating east-west statistics, north-south statistics, adding production and loss fields")
        
        # save ewSlope to a raster
        #ewSlope.save(os.path.join(workspace, "ewSlope_testing")) 
        try:
            ewStatsRows = arcpy.sa.ZonalStatisticsAsTable(rowsInput,row_ID,ewSlope,r"in_memory\ewStatsRows","DATA","ALL")
        except Exception as e:
            arcpy.AddMessage(e)
            arcpy.AddMessage("Failed to calculate east-west statistics; trying clipping rows to the raster extent & recalculating")
            
            # take the domain of the raster
            domain_ewSlope = arcpy.ddd.RasterDomain(ewSlope, "in_memory/domain", "POLYGON")
            
            # clip the rows to the domain
            rowsClip = arcpy.analysis.Clip(rowsInput, domain_ewSlope, "rowsClip")
            
            # calculate the zonal statistics
            ewStatsRows = arcpy.sa.ZonalStatisticsAsTable(rowsClip, row_ID, ewSlope, r"in_memory\ewStatsRows", "DATA", "ALL")
            
            return

        # Calculate east-west production based on variation from east to west
        if poaTerrainOption == "Terrain-based":
            arcpy.management.CalculateField(ewStatsRows, "prod_ew", ""+specProd+" + "+ewVar+" * (abs(0.5*!STD! * "+numbSTDs+"))", "PYTHON3", "", "FLOAT")
        if poaTerrainOption == "Plane of array-based":
            arcpy.management.CalculateField(ewStatsRows, "prod_ew", ""+specProd+" + "+ewVar+" * (abs(0.5*!RANGE!))", "PYTHON3", "", "FLOAT")

        # Calculate east-west losses negative means loss, there should be no positive
        arcpy.management.CalculateField(ewStatsRows,"loss_ew","(1 - !prod_ew!/"+specProd+")*-100", "PYTHON3", "", "FLOAT")

        # Join production and losses to production layer, join north-south mean to production layer
        if poaTerrainOption == "Terrain-based":
            if strings_or_rows == "Tracker rows":
                arcpy.management.JoinField(prodRows,row_ID,ewStatsRows,row_ID,["STD","prod_ew","loss_ew"])
                arcpy.management.AlterField(prodRows, "STD", "STD_ewSlope", "STD_ewSlope")
                arcpy.management.CalculateField(prodRows,"numSTDs",""+numbSTDs+"", "PYTHON3", "", "LONG")
            if strings_or_rows == "Strings":
                arcpy.management.JoinField(prodStrings,row_ID,ewStatsRows,row_ID,["STD","prod_ew","loss_ew"])
                arcpy.management.AlterField(prodStrings, "STD", "STD_ewSlope", "STD_ewSlope")
                arcpy.management.CalculateField(prodStrings,"numSTDs",""+numbSTDs+"", "PYTHON3", "", "LONG")

        if poaTerrainOption == "Plane of array-based":
            if strings_or_rows == "Tracker rows":
                arcpy.management.JoinField(prodRows,row_ID,ewStatsRows,row_ID,["RANGE","prod_ew","loss_ew"])
                arcpy.management.AlterField(prodRows, "RANGE", "RANGE_ewSlope", "RANGE_ewSlope")
            if strings_or_rows == "Strings":
                arcpy.management.JoinField(prodStrings,row_ID,ewStatsRows,row_ID,["RANGE","prod_ew","loss_ew"])
                arcpy.management.AlterField(prodStrings, "RANGE", "RANGE_ewSlope", "RANGE_ewSlope")
            
        # Calculate production and losses
        if strings_or_rows == "Tracker rows":
            arcpy.management.CalculateField(prodRows,"prod_ns",""+specProd+"-"+nsVarA+" * !"+slopeOutput+"! + "+nsVarB+" * pow(!"+slopeOutput+"!,2)", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodRows,"loss_ns","(1-!prod_ns!/"+specProd+")*-100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodRows,"prod_ewns","!prod_ew! + (!prod_ns!-"+specProd+")", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodRows,"loss_ewns","(1 - !prod_ewns!/"+specProd+")*-100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodRows,"annual_prod_MWh","!power_kW! * !prod_ewns! / 1000","PYTHON3","", "FLOAT")

        if strings_or_rows == "Strings":
            arcpy.management.CalculateField(prodStrings,"prod_ns",""+specProd+"-"+nsVarA+" * !"+slopeOutput+"! + "+nsVarB+" * pow(!"+slopeOutput+"!,2)", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodStrings,"loss_ns","(1-!prod_ns!/"+specProd+")*-100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodStrings,"prod_ewns","!prod_ew! + (!prod_ns!-"+specProd+")", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodStrings,"loss_ewns","(1 - !prod_ewns!/"+specProd+")*-100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodStrings,"annual_prod_MWh","!power_kW! * !prod_ewns! / 1000","PYTHON3","", "FLOAT")

        if rowsBlocksOption == "Mechanical blocks":
            arcpy.management.CalculateField(prodBlocks,"prod_EWLoss","!sum_power_kW! * !loss_ew! / 100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodBlocks,"prod_NSLoss","!sum_power_kW! * !loss_ns! / 100", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(prodBlocks,"prod_Loss","!sum_power_kW! * !loss_ewns! / 100", "PYTHON3", "", "FLOAT")
            sumTable = arcpy.analysis.Statistics(prodBlocks, prodSummary, [["prod_EWLoss", "SUM"], ["prod_NSLoss", "SUM"], ["prod_Loss", "SUM"], ["sum_power_kW", "SUM"], ["annual_prod_MWh", "SUM"]])
            arcpy.management.CalculateField(sumTable,"ewAVG_loss","100*!SUM_prod_EWLoss!/!SUM_sum_power_kW!", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(sumTable,"nsAVG_loss","100*!SUM_prod_NSLoss!/!SUM_sum_power_kW!", "PYTHON3", "", "FLOAT")
            arcpy.management.CalculateField(sumTable,"AVG_loss","100*!SUM_prod_Loss!/!SUM_sum_power_kW!", "PYTHON3", "", "FLOAT")

            arcpy.management.DeleteField(prodBlocks, [["prod_EWLoss"],["prod_NSLoss"],["prod_Loss"]])
            arcpy.management.DeleteField(sumTable, [["SUM_prod_EWLoss"],["SUM_prod_NSLoss"],["SUM_prod_Loss"]])

        if rowsBlocksOption == "Rows/strings":
            if strings_or_rows == "Tracker rows":
                arcpy.management.CalculateField(prodRows,"prod_EWLoss","!power_kW! * !loss_ew! / 100", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(prodRows,"prod_NSLoss","!power_kW! * !loss_ns! / 100", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(prodRows,"prod_Loss","!power_kW! * !loss_ewns! /100 ", "PYTHON3", "", "FLOAT")
                sumTable = arcpy.analysis.Statistics(prodRows, prodSummary, [["prod_EWLoss", "SUM"], ["prod_NSLoss", "SUM"], ["prod_Loss", "SUM"], ["power_kW", "SUM"], ["annual_prod_MWh", "SUM"]])
                arcpy.management.CalculateField(sumTable,"ewAVG_loss","100*!SUM_prod_EWLoss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(sumTable,"nsAVG_loss","100*!SUM_prod_NSLoss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(sumTable,"AVG_loss","100*!SUM_prod_Loss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")

                arcpy.management.DeleteField(prodRows, [["prod_EWLoss"],["prod_NSLoss"],["prod_Loss"]])
                arcpy.management.DeleteField(sumTable, [["SUM_prod_EWLoss"],["SUM_prod_NSLoss"],["SUM_prod_Loss"]])

            if strings_or_rows == "Strings":
                arcpy.management.CalculateField(prodStrings,"prod_EWLoss","!power_kW! * !loss_ew! / 100", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(prodStrings,"prod_NSLoss","!power_kW! * !loss_ns! / 100", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(prodStrings,"prod_Loss","!power_kW! * !loss_ewns! /100 ", "PYTHON3", "", "FLOAT")
                sumTable = arcpy.analysis.Statistics(prodStrings, prodSummary, [["prod_EWLoss", "SUM"], ["prod_NSLoss", "SUM"], ["prod_Loss", "SUM"], ["power_kW", "SUM"], ["annual_prod_MWh", "SUM"]])
                arcpy.management.CalculateField(sumTable,"ewAVG_loss","100*!SUM_prod_EWLoss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(sumTable,"nsAVG_loss","100*!SUM_prod_NSLoss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")
                arcpy.management.CalculateField(sumTable,"AVG_loss","100*!SUM_prod_Loss! / !SUM_power_kW!", "PYTHON3", "", "FLOAT")

                arcpy.management.DeleteField(prodStrings, [["prod_EWLoss"],["prod_NSLoss"],["prod_Loss"]])
                arcpy.management.DeleteField(sumTable, [["SUM_prod_EWLoss"],["SUM_prod_NSLoss"],["SUM_prod_Loss"]])


        # Add output files to current map
        if strings_or_rows == "Tracker rows":
            aprxMap.addDataFromPath(prodRows)
        if strings_or_rows == "Strings":
            aprxMap.addDataFromPath(prodStrings)
        aprxMap.addDataFromPath(sumTable)

        return