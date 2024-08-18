########################################################################
"""SUB-OPTIMIZED SINGLE AXIS TRACKER GRADING ESTIMATE

Description: Grading estimate using the conventional method by pinning the ends of the tracker rows 

Revision log
0.0.1 - 1/14/2022 - Initial scripting
0.0.2 - 5/20/2022 - Eliminated output path and made it automatically detect
1.0.0 - 6/10/2022 - Updated parameters for specific outputs to be more clear, simplified output
1.1.0 - 12/21/2022 - Added ability to calculate cut and fill volumes and export a landxml
1.2.0 - 2/19/2024 - Added error checking & implemented resampling of the input raster
"""

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import shapefile
import os
import lxml.etree as ET

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.2.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Zane Nordquist"]
__status__      = "Deployed"


class SATGradeConventional(object):
    def __init__(self):
        self.label = "Conventional Single Axis Tracker Grading Estimate"
        self.description = "Grading estimate using a conventional grading method by pinning the ends of the tracker rows"
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
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param1.name]

        param3 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ["Point"]

        param4 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["Foot", "Meter"]

        param5 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Graded raster output dataset",
            name="gradeOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        param8 = arcpy.Parameter(
            displayName="Pile detail output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param9 = arcpy.Parameter(
            displayName="Grading boundary output feature class",
            name="gradeBoundsOut",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param10 = arcpy.Parameter(
            displayName="Output grading volume statistics?",
            name="cutFillOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param10.value = False

        param11 = arcpy.Parameter(
            displayName="Cut output raster dataset",
            name="cutOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param12 = arcpy.Parameter(
            displayName="Fill output raster dataset",
            name="fillOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param13 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
            parameterType="Optional",
            direction="Output")

        param14 = arcpy.Parameter(
            displayName="Output LandXML?",
            name="lxmlOutputOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param14.value = False

        param15 = arcpy.Parameter(
            displayName="Output LandXML file",
            name="lxmlOutput",
            datatype="DEFile",
            parameterType="Optional",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14, param15]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[7].altered:
            parameters[7].value = "demGradeCV"

        if not parameters[8].altered:
            parameters[8].value = "pilesGradeCV"

        if not parameters[9].altered:
            parameters[9].value = "demGradeCV_bounds"

        if parameters[10].value == True:
            parameters[11].enabled = True
            parameters[12].enabled = True
            parameters[13].enabled = True

        else:
            parameters[11].enabled = False
            parameters[12].enabled = False
            parameters[13].enabled = False

        if not parameters[11].altered:
            parameters[11].value = "Cut_CV"

        if not parameters[12].altered:
            parameters[12].value = "Fill_CV"

        if not parameters[13].altered:
            parameters[13].value = "CutFill_Statistics_CV"

        if parameters[14].value == True:
            parameters[15].enabled = True

        else:
            parameters[15].enabled = False

        if not parameters[15].altered:
            parameters[15].value = "demGradeCV_LXML.xml"

        if parameters[15].altered:
            (dirnm, basenm) = os.path.split(parameters[15].valueAsText)
            if not basenm.endswith(".xml"):
                parameters[15].value = os.path.join(dirnm, "{}.xml".format(basenm))

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[4].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[4].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[4].value == "Meter":
                if "Meter" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[4].setErrorMessage("Vertical and horizontal units do not match")
            else:
                parameters[4].clearMessage()
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText  # Existing elevation in raster format
        rowsInput = parameters[1].valueAsText  # Array rows
        row_ID = parameters[2].valueAsText  # Array row unique ID
        pilesInput = parameters[3].valueAsText # Input pile feature class
        xyzUnit = parameters[4].valueAsText # Vertical and horizontal units
        minReveal = parameters[5].valueAsText  # Minimum reveal height in units of map
        maxReveal = parameters[6].valueAsText  # Maximum reveal height in units of map
        gradeOut = parameters[7].valueAsText  # Output grade raster
        pileOutput = parameters[8].valueAsText  # Piles output
        gradeBoundsOut = parameters[9].valueAsText # Output grading boundary
        cutFillOption = parameters[10].value # Allows output of volume statistics and cut and fill rasters
        cutOut = parameters[11].valueAsText # Cut output raster dataset
        fillOut = parameters[12].valueAsText # fill output raster dataset
        statsOutput = parameters[13].valueAsText # Volume summary statistics table output
        lxmlOutputOption = parameters[14].value
        lxmlOutput = parameters[15].valueAsText
        
        outputPath = os.path.dirname(workspace)

        spatialRef = arcpy.Describe(demInput).spatialReference
        gridRes = arcpy.Describe(demInput).meanCellWidth
        arcpy.env.snapRaster = demInput
        mapUnits = spatialRef.linearUnitName

        # Run inputCheck function
        SATGradeConventional.inputCheck(demInput, rowsInput, pilesInput, minReveal, maxReveal, gridRes, mapUnits)

        # Create end points on the rows
        rowPoints = arcpy.management.CreateFeatureclass("in_memory", "rowPoints", "POINT", "#", "DISABLED", "DISABLED",rowsInput)
        arcpy.management.AddFields(rowPoints, [["PolygonOID", "LONG"], ["Position", "TEXT"]])

        insert_cursor = arcpy.da.InsertCursor(rowPoints, ["SHAPE@", "PolygonOID", "Position"])
        search_cursor = arcpy.da.SearchCursor(rowsInput, ["SHAPE@", "OID@"])

        for row in search_cursor:
            try:
                polygon_oid = str(row[1])

                coordinateList = []
                lowerLeft_distances = {}
                lowerRight_distances = {}
                upperLeft_distances = {}
                upperRight_distances = {}

                for part in row[0]:
                    for pnt in part:
                        if pnt:
                            coordinateList.append((pnt.X, pnt.Y))

                # Finds the extent of each polygon
                polygonExtent = row[0].extent

                lowerLeft_coordinate = polygonExtent.lowerLeft
                lowerRight_coordinate = polygonExtent.lowerRight
                upperLeft_coordinate = polygonExtent.upperLeft
                upperRight_coordinate = polygonExtent.upperRight

                lowerLeft_point = arcpy.PointGeometry(lowerLeft_coordinate)
                lowerRight_point = arcpy.PointGeometry(lowerRight_coordinate)
                upperLeft_point = arcpy.PointGeometry(upperLeft_coordinate)
                upperRight_point = arcpy.PointGeometry(upperRight_coordinate)

                # Finds the vertex closest to each corner of the polygon extent
                for vertex in coordinateList:
                    vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                    vertex_point = arcpy.PointGeometry(vertex_coordinates)
                    lowerLeft_distances[float(lowerLeft_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

                for vertex in coordinateList:
                    vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                    vertex_point = arcpy.PointGeometry(vertex_coordinates)
                    lowerRight_distances[float(lowerRight_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

                for vertex in coordinateList:
                    vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                    vertex_point = arcpy.PointGeometry(vertex_coordinates)
                    upperLeft_distances[float(upperLeft_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

                for vertex in coordinateList:
                    vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                    vertex_point = arcpy.PointGeometry(vertex_coordinates)
                    upperRight_distances[float(upperRight_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

                # Calculates where quarter quarter sections would intersect polygon
                LLminDistance = min(lowerLeft_distances)
                LRminDistance = min(lowerRight_distances)
                ULminDistance = min(upperLeft_distances)
                URminDistance = min(upperRight_distances)

                top_left_X = float(upperLeft_distances[ULminDistance][0])
                top_left_Y = float(upperLeft_distances[ULminDistance][1])
                top_right_X = float(upperRight_distances[URminDistance][0])
                top_right_Y = float(upperRight_distances[URminDistance][1])

                bottom_left_X = float(lowerLeft_distances[LLminDistance][0])
                bottom_left_Y = float(lowerLeft_distances[LLminDistance][1])
                bottom_right_X = float(lowerRight_distances[LRminDistance][0])
                bottom_right_Y = float(lowerRight_distances[LRminDistance][1])

                top_left_point = arcpy.PointGeometry(arcpy.Point(top_left_X, top_left_Y))
                top_right_point = arcpy.PointGeometry(arcpy.Point(top_right_X, top_right_Y))
                bottom_left_point = arcpy.PointGeometry(arcpy.Point(bottom_left_X, bottom_left_Y))
                bottom_right_point = arcpy.PointGeometry(arcpy.Point(bottom_right_X, bottom_right_Y))

                insert_cursor.insertRow((top_left_point, polygon_oid, "NW"))
                insert_cursor.insertRow((top_right_point, polygon_oid, "NE"))
                insert_cursor.insertRow((bottom_left_point, polygon_oid, "SW"))
                insert_cursor.insertRow((bottom_right_point, polygon_oid, "SE"))

                west_line = arcpy.Polyline(
                    arcpy.Array([arcpy.Point(top_left_X, top_left_Y), arcpy.Point(bottom_left_X, bottom_left_Y)]))
                east_line = arcpy.Polyline(
                    arcpy.Array([arcpy.Point(top_right_X, top_right_Y), arcpy.Point(bottom_right_X, bottom_right_Y)]))
                north_line = arcpy.Polyline(
                    arcpy.Array([arcpy.Point(top_left_X, top_left_Y), arcpy.Point(top_right_X, top_right_Y)]))
                south_line = arcpy.Polyline(arcpy.Array(
                    [arcpy.Point(bottom_left_X, bottom_left_Y), arcpy.Point(bottom_right_X, bottom_right_Y)]))

                west_point = west_line.positionAlongLine(0.5, True)
                east_point = east_line.positionAlongLine(0.5, True)
                north_point = north_line.positionAlongLine(0.5, True)
                south_point = south_line.positionAlongLine(0.5, True)

                insert_cursor.insertRow((west_point, polygon_oid, "W"))
                insert_cursor.insertRow((east_point, polygon_oid, "E"))
                insert_cursor.insertRow((north_point, polygon_oid, "N"))
                insert_cursor.insertRow((south_point, polygon_oid, "S"))

            except Exception as err:
                arcpy.AddMessage(str(err.message))

        del insert_cursor
        del search_cursor

        # Separate out end and corner points
        rowEndPoints = arcpy.analysis.Select(rowPoints, "rowEndPoints", "Position = 'S' Or Position = 'N'")
        rowCornerPoints = arcpy.analysis.Select(rowPoints, r"in_memory\rowCornerPoints","Position = 'NW' Or Position = 'NE' Or Position = 'SW' Or Position = 'SE'")

        # Extract the existing elevation at the end points
        arcpy.sa.ExtractMultiValuesToPoints(rowEndPoints, [[demInput, "demExist"]])

        # Add a point ID and line ID field and create unique ids per row and point position and line IDs for east and west per row

        poaIDcode = """
def poaID(pos,row_ID):
    if pos == "NW" or pos == "NE":
        return str(row_ID) + "N"
    else:
        return str(row_ID) + "S"
"""

        arcpy.management.CalculateField(rowEndPoints, "pointID", "str(!PolygonOID!) + !Position!", "PYTHON3", poaIDcode,"TEXT")

        lineIDcode = """
def lineID(pos,row_ID):
    if pos == "NW" or pos == "SW":
        return str(row_ID) + "W"
    else:
        return str(row_ID) + "E"
"""

        arcpy.management.CalculateField(rowCornerPoints, "lineID", "lineID(!Position!,!PolygonOID!)", "PYTHON3",lineIDcode, "TEXT")

        # Add coordinates to the corner points and make a field to associate them with the end points
        arcpy.management.AddXY(rowCornerPoints)

        arcpy.management.CalculateField(rowCornerPoints, "pointID", "poaID(!Position!,!PolygonOID!)", "PYTHON3",poaIDcode, "TEXT")

        # Join the existing elevation to the coner points from the end points
        arcpy.management.JoinField(rowCornerPoints, "pointID", rowEndPoints, "pointID", "demExist")

        # Make the corner points 3D and create 3D lines for each set
        rowCornerPoints_3D = arcpy.ddd.FeatureTo3DByAttribute(rowCornerPoints, r"in_memory\rowCornerPoints_3D", "demExist", None)
        boundLines = arcpy.management.PointsToLine(rowCornerPoints_3D, "boundLines", "lineID")

        # Create a TIN from the bound lines
        tin_name = str(outputPath + "\poaBase_TIN_ST")
        poaBase_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "boundLines Shape.Z Hard_Line <None>", "DELAUNAY")

        # Find distance between rows east-west
        rowsNear = arcpy.analysis.GenerateNearTable(rowsInput, rowsInput, r"in_memory\rowsNear", None, "NO_LOCATION","ANGLE", "ALL", 8, "GEODESIC")

        codeblock_pos = """
def direction(angle, nearDist):
    if (angle < -85 and angle > -95) or (angle > 85 and angle < 95):
        return "delta_x"
    else:
        return "NA"
"""

        arcpy.management.CalculateField(rowsNear, "delta_pos", "direction(!NEAR_ANGLE!, !NEAR_DIST!)", "PYTHON3", codeblock_pos, "TEXT")

        near_stats = arcpy.analysis.Statistics(rowsNear, r"in_memory\near_stats", "NEAR_DIST MIN","IN_FID; delta_pos")

        # Screen out outliers east-west
        dist_x = arcpy.analysis.TableSelect(near_stats, r"in_memory\dist_x", "delta_pos = 'delta_x'")

        minMaxXRows = arcpy.analysis.Statistics(rowCornerPoints, r"in_memory\minMaxXRows", "POINT_X MIN; POINT_X MAX","PolygonOID")
        arcpy.management.CalculateField(minMaxXRows, "rowWidth", "(!MAX_POINT_X!- !MIN_POINT_X!)", "PYTHON3", "", "DOUBLE")

        arcpy.management.AlterField(dist_x, "MIN_NEAR_DIST", "delta_zone_x")
        screenTable = arcpy.conversion.TableToTable(dist_x, workspace, r"screenTable")
        arcpy.management.JoinField(screenTable, "IN_FID", minMaxXRows, "PolygonOID", "rowWidth")

        codeblock_screen = """
def xScreen(rowWidth,dX):
    if dX > 5 * rowWidth:
        return ""
    else:
        return dX
"""
        arcpy.management.CalculateField(screenTable, "dXScreen", "xScreen(!rowWidth!, !delta_zone_x!)", "PYTHON3", codeblock_screen, "DOUBLE")
        maxDx = arcpy.analysis.Statistics(screenTable, r"in_memory\maxDx", "dXScreen MAX")

        xFactor = "0.55"

        arcpy.management.CalculateField(maxDx, "graphicBuffer", "(!MAX_dXScreen!/"+xFactor+")/2", "PYTHON3", "", "DOUBLE")

        arcpy.management.CalculateField(rowsInput, "joinField", "1", "PYTHON3", "", "LONG")

        arcpy.management.JoinField(rowsInput, "joinField", maxDx, "OBJECTID", "graphicBuffer")

        basePlane_bounds_exp = arcpy.analysis.GraphicBuffer(rowsInput,r"in_memory\basePlane_bounds_exp", "graphicBuffer", "SQUARE", "MITER", 10, "0 Feet")

        basePlane_bounds_exp_diss = arcpy.analysis.PairwiseDissolve(basePlane_bounds_exp, r"in_memory\basePlane_bounds_exp_diss", None, None, "MULTI_PART", "")

        arcpy.management.JoinField(basePlane_bounds_exp_diss, "OBJECTID", rowsInput, "joinField", "graphicBuffer")

        arcpy.management.CalculateField(basePlane_bounds_exp_diss, "graphicBuffer", "!graphicBuffer! * -1", "PYTHON3", "", "DOUBLE")

        basePlane_bounds = arcpy.analysis.GraphicBuffer(basePlane_bounds_exp_diss,"basePlane_bounds", "graphicBuffer", "SQUARE", "MITER", 10, "0 Feet")

        arcpy.management.DeleteField(rowsInput, [["graphicBuffer"],["joinField"]], "DELETE_FIELDS")

        arcpy.ddd.EditTin(
            in_tin=poaBase_TIN,
            in_features="basePlane_bounds <None> <None> Hard_Clip false",
            constrained_delaunay="DELAUNAY"
        )

        # Convert TIN to raster
        basePlanes_CG = arcpy.ddd.TinRaster(poaBase_TIN, "basePlanes_CG", "FLOAT", "LINEAR", "CELLSIZE", 1,gridRes)

        # Clip the basePlanes to the row areas
        # basePlanes_CG = arcpy.management.Clip(basePlanes_pre, "", "basePlanes_CG", basePlane_bounds, "3.4e+38","ClippingGeometry", "NO_MAINTAIN_EXTENT")

        # Calculate spacing above and below plane of array
        delta_poa = (float(maxReveal) - float(minReveal))
        arcpy.AddMessage("Reveal tolerance: " + str(delta_poa) + " " + mapUnits)
        spacing = delta_poa / 2

        # Create the upper bound
        upperLimit = arcpy.sa.Plus(basePlanes_CG, spacing)
        upperBound = arcpy.management.MosaicToNewRaster([demInput, upperLimit], "in_memory", "upperBound", spatialRef,"32_BIT_FLOAT", gridRes, 1, "MINIMUM", "FIRST")

        # Create the lower bound
        lowerLimit = arcpy.sa.Minus(basePlanes_CG, spacing)
        lowerBound = arcpy.management.MosaicToNewRaster([demInput, lowerLimit], "in_memory", "lowerBound", spatialRef,"32_BIT_FLOAT", gridRes, 1, "MAXIMUM", "FIRST")

        # Create and the final grading DEM
        upperGrade = arcpy.sa.Minus(upperBound, demInput)
        demGrade = arcpy.sa.Plus(lowerBound, upperGrade)
        cutFill = arcpy.sa.Minus(demGrade, demInput)

        arcpy.SetProgressor("default", "Calculating reveals...")

        # Calculate reveals 
        grade_trends = arcpy.sa.Minus(demGrade, basePlanes_CG)
        min_rev_grade = arcpy.sa.Plus(float(minReveal), grade_trends)
        max_min_reveal = arcpy.sa.ZonalStatistics(rowsInput, row_ID, min_rev_grade, "MAXIMUM", "DATA")
        reveals = arcpy.sa.Minus(max_min_reveal, grade_trends)

        arcpy.SetProgressor("default", "Calculating plane of array...")

        # Create plane of array raster - CREATE 3D FEATURE CLASS HERE
        POA = arcpy.sa.Plus(reveals, demGrade)

        arcpy.SetProgressor("default", "Adding statistics to piles...")

        # Extract ungraded and graded elevation layers
        pileName = os.path.basename(pileOutput)

        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pileName)
        arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[demInput, "demExist"], [demGrade, "demGrade"],[POA, "poa_pre"]], "BILINEAR")

        # Select piles where the poa is not null
        pilesPOAvalid = arcpy.analysis.Select(piles_working, "pilesPOAvalid","poa_pre IS NOT NULL")

        # Find the slope and intercept of the valid poa
        arcpy.management.AddXY(pilesPOAvalid)

        coorStatsInputPOA = [["poa_pre", "MEAN"], ["POINT_Y", "MEAN"]]
        coorStatsPOA = arcpy.analysis.Statistics(pilesPOAvalid, "coorStatsPOA", coorStatsInputPOA, row_ID)

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(pilesPOAvalid, row_ID, coorStatsPOA, row_ID, ["MEAN_poa_pre", "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(pilesPOAvalid, "zy_bar","(!poa_pre! + !MEAN_poa_pre!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3","", "DOUBLE")
        arcpy.management.CalculateField(pilesPOAvalid, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3","", "DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStatsPOA = arcpy.analysis.Statistics(pilesPOAvalid, "sumStatsPOA", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq)
        arcpy.management.CalculateField(sumStatsPOA, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3","", "DOUBLE")

        # Join slope to pilesPOAvalid
        arcpy.management.JoinField(pilesPOAvalid, row_ID, sumStatsPOA, row_ID, ["nsSlope"])

        # Find the intercept
        arcpy.management.CalculateField(pilesPOAvalid, "bInit", "!poa_pre! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        poaPreStats = arcpy.analysis.Statistics(pilesPOAvalid, "poaPreStats", [["bInit", "MEAN"],["nsSlope", "MEAN"]], row_ID)

        # Calculate north-south plane of array slope
        arcpy.management.AddXY(piles_working)

        arcpy.management.JoinField(piles_working, row_ID, poaPreStats, row_ID, [["MEAN_nsSlope"],["MEAN_bInit"]])
        
        # Calculate the plane of array
        arcpy.management.CalculateField(piles_working, "TOP_elv", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

        # Calculate reveals at the piles
        arcpy.management.CalculateField(piles_working, "reveal", "round(!TOP_elv! - !demGrade!,3)", "PYTHON3", "", "DOUBLE")
        revealScreen = arcpy.analysis.Statistics(piles_working, "revealScreen", "reveal MAX;reveal MIN",row_ID)

        poaAdjCode = """
def poaAdjust(maxR, minR, maxRev, minRev):
    if maxR > maxRev:
        return maxR - maxRev
    if minR < minRev:
        return minRev - minR
    else:
        return 0
"""

        arcpy.management.CalculateField(revealScreen, "poaAdj", "poaAdjust(!MAX_reveal!,!MIN_reveal!, "+maxReveal+", "+minReveal+")", "PYTHON3", poaAdjCode, "DOUBLE")

        arcpy.management.JoinField(piles_working, row_ID, revealScreen, row_ID, "poaAdj")

        arcpy.management.CalculateField(piles_working, "TOP_elv", "!TOP_elv! + !poaAdj!", "PYTHON3", "")

        arcpy.management.CalculateField(piles_working, "reveal", "round(!TOP_elv! - !demGrade!,3)", "PYTHON3", "")

        arcpy.management.DeleteField(piles_working, ["MEAN_nsSlope", "MEAN_bInit", "poa_pre", "poaAdj"])

        # Clean up
        arcpy.management.Delete(sumStatsPOA)
        arcpy.management.Delete(coorStatsPOA)
        arcpy.management.Delete(pilesPOAvalid)
        arcpy.management.Delete(poaPreStats)
        arcpy.management.Delete(revealScreen)

        # Create a cutFill column and create a layer with only piles that require grading
        arcpy.management.CalculateField(piles_working, "cutFill", "!demGrade!-!demExist!", "PYTHON3", None, "DOUBLE")

        # Calculate POA NS slope
        # Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
        coorStatsInput = [["TOP_elv", "MEAN"], ["POINT_Y", "MEAN"]]
        coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, ["MEAN_TOP_elv", "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(piles_working, "zy_bar","(!TOP_elv! + !MEAN_TOP_elv!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3","", "DOUBLE")
        arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3","", "DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStats, "nsSlopePercPOA", "-100*!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3","", "DOUBLE")

        # Join slope to piles_working
        arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlopePercPOA"])

        # Alter all fields to have alias
        arcpy.management.AlterField(piles_working, "POINT_X", "", "Easting")
        arcpy.management.AlterField(piles_working, "POINT_Y", "", "Northing")
        arcpy.management.AlterField(piles_working, "demExist", "", "Existing Elevation")
        arcpy.management.AlterField(piles_working, "demGrade", "", "Graded Elevation")
        arcpy.management.AlterField(piles_working, "reveal", "", "Reveal")
        arcpy.management.AlterField(piles_working, "TOP_elv", "", "Top of Pile Elevation")
        arcpy.management.AlterField(piles_working, "nsSlopePercPOA", "", "North-South POA Slope")
        arcpy.management.AlterField(piles_working, "cutFill", "", "Cut Fill")

        arcpy.management.DeleteField(piles_working, ["MEAN_TOP_elv", "MEAN_POINT_Y", "zy_bar", "y_ybar_sq"])

        aprxMap.addDataFromPath(piles_working)

        # Clean up
        arcpy.management.Delete(max_min_reveal)
        arcpy.management.Delete("coorStats")
        arcpy.management.Delete("sumStats")

        cutFillMAXResult = arcpy.GetRasterProperties_management(cutFill, "MAXIMUM")
        cutFillMINResult = arcpy.GetRasterProperties_management(cutFill, "MINIMUM")
        cutFillMAX = cutFillMAXResult.getOutput(0)
        cutFillMIN = cutFillMINResult.getOutput(0)

        arcpy.AddMessage("Fill Max: " + str(cutFillMAX))
        arcpy.AddMessage("Cut Max: " + str(cutFillMIN))

        if cutFillMAX == 0 and cutFillMIN == 0:
            arcpy.AddMessage("No grading required for site")
            sys.exit(0)
        else:
            arcpy.SetProgressor("default", "Determining the grading areas...")

            piles_graded_pre = arcpy.analysis.Select(piles_working, "piles_graded_pre","cutFill < -0.0415 OR cutFill > 0.0415")

            # Reclassify cut-fill raster using tolerance
            reclass_code = RemapRange([[-300, -1 * float(.0415), 1], [-1 * float(.0415), float(.0415), 0], [float(.0415), 300, 2]])
            cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
            cutFill_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
            grade_area = arcpy.analysis.Select(cutFill_poly, "grade_area", "gridcode <> 0")

            # Select areas that intersect piles that are graded
            grade_intersect = arcpy.management.SelectLayerByLocation(grade_area, "INTERSECT", piles_graded_pre)
            grade_area_rows = arcpy.conversion.FeatureClassToFeatureClass(grade_intersect, workspace, "grade_area_rows")

            arcpy.SetProgressor("default", "Refining the grading areas...")

            # Buffer the graded areas by 5 feet close small holes and merge areas within 10 feet of each other
            hole_close_buffer = "10 Feet"
            grade_area_rows_buff = arcpy.analysis.PairwiseBuffer(grade_intersect, "in_memory\grade_area_rows_buff", hole_close_buffer, "ALL")

            # Invert the buffer to just inside the graded area to eliminate small areas
            buffer_in = "-9 Feet"
            bounds_invert = arcpy.analysis.PairwiseBuffer(grade_area_rows_buff, "bounds_invert", buffer_in, "ALL")

            # Extend the graded areas to 2 the raster resolution outside of the graded areas to join close areas
            bounds_extend = "3 Feet"
            grade_bounds_pre = arcpy.analysis.PairwiseBuffer(bounds_invert, r"in_memory\grade_bounds_pre", bounds_extend, "ALL")

            if gridRes > 2:
                simplifyFactor = 1
            else:
                simplifyFactor = gridRes/2

            if xyzUnit == "Foot":
                simpInput = str(simplifyFactor) + " Feet"
            else:
                simpInput = str(simplifyFactor) + " Meter"
                
            gradeBoundsName = os.path.basename(gradeBoundsOut)

            grade_bounds = arcpy.cartography.SimplifyPolygon(grade_bounds_pre, gradeBoundsName, "WEIGHTED_AREA", simpInput, "0 SquareFeet", "RESOLVE_ERRORS", "NO_KEEP", None)

            # Select the sample points and the piles within graded areas
            piles_intersect = arcpy.management.SelectLayerByLocation(piles_working, "INTERSECT", grade_bounds)
            piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, "piles_graded")
            arcpy.management.AlterField(piles_graded, "demGrade", "", "", "FLOAT", 4, "NULLABLE", "CLEAR_ALIAS")

            # Convert the buffered layer to polylines and interpolate the existing elevation
            grade_area_line = arcpy.management.FeatureToLine(grade_bounds, "grade_area_line")
            grade_bound_3D = arcpy.sa.InterpolateShape(demInput, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR","DENSIFY", 0, "EXCLUDE")

            # Create TIN between graded piles and refine to graded area, and extract the 3D edges
            tin_name_piles = str(outputPath + "\piles_TIN")
            piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, "piles_graded demGrade Mass_Points")
            tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
            tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line,None, "NEW_SELECTION", "INVERT")
            tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace,"tinEdge_final")

            # Create a TIN from the bound and piles layer
            tin_name = str(outputPath + "/grade_TIN")
            grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef,"grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
            editTinInput = gradeBoundsName + " <None> <None> Hard_Clip false"
            arcpy.ddd.EditTin(grade_TIN, editTinInput, "DELAUNAY")

            gradeRasterName = os.path.basename(gradeOut)

            output_grade = arcpy.ddd.TinRaster(grade_TIN, gradeRasterName, "FLOAT", "NATURAL_NEIGHBORS", "CELLSIZE", 1,gridRes)

            aprxMap.addDataFromPath(grade_bounds)

            if cutFillOption == True:
                arcpy.SetProgressor("default", "Comparing the graded surface to the existing surface...")

                # Calculate the area of one raster square
                grid_area = str(gridRes ** 2)

                # Create a polygon of the domain of the existing elevation
                TotalCutFill = arcpy.ddd.RasterDomain(demInput, "TotalCutFill", "POLYGON")

                # Create new cut and fill rasters based on the final grade
                cutFillFinal = arcpy.sa.Minus(output_grade, demInput)
                
                # Create individual cut rasters and fill rasters
                cut_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, "VALUE > 0")
                cut_raster.save(cutOut)
                fill_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, "VALUE < 0")
                fill_raster.save(fillOut)

                arcpy.SetProgressorLabel("Calculating total graded area")

                # Sum the graded area and convert to acres from square feet
                if xyzUnit == "Foot":
                    total_graded_area = arcpy.analysis.Statistics(grade_bounds, "total_graded_area", "Shape_Area SUM", None)
                    arcpy.management.AddFields(total_graded_area,[["graded_area_acres", "DOUBLE", "Total Graded Area (acres)"]])
                    arcpy.management.CalculateField(total_graded_area, "graded_area_acres", "round(!SUM_Shape_Area!/43560,2)","PYTHON3", None)

                if xyzUnit == "Meter":
                    total_graded_area = arcpy.analysis.Statistics(grade_bounds, "total_graded_area", "Shape_Area SUM", None)
                    arcpy.management.AddFields(total_graded_area, [["graded_area_m2", "DOUBLE", "Total Graded Area (m^2)"]])
                    arcpy.management.CalculateField(total_graded_area, "graded_area_m2", "round(!SUM_Shape_Area!,2)", "PYTHON3",None)

                arcpy.SetProgressorLabel("Calculating cut and fill statistics")

                # Calculate the cut-fill statistics
                Cut_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, "OID", cut_raster, "Cut_Total", "DATA", "ALL")
                Fill_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, "OID", fill_raster, "Fill_Total", "DATA", "ALL")

                # Add fields to convert to cubic yards, multiply the sum by the grid resolution and convert to cubic yards or meters
                if xyzUnit == "Foot":
                    arcpy.management.CalculateField(Cut_Total, "cut_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3","", "DOUBLE")
                    arcpy.management.CalculateField(Fill_Total, "fill_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3","","DOUBLE")
                    arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_y3"])
                    arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_y3"])

                    # Calculate net, gross, and ratio statistics for cubic yards
                    CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_y3 SUM; fill_y3 SUM", None)
                    arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_y3! + !SUM_fill_y3!,2)","PYTHON3", "","DOUBLE")
                    arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_y3! - !SUM_cut_y3!,2)","PYTHON3", "","DOUBLE")
                    arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_y3!) / !SUM_fill_y3!,2)", "PYTHON3", "","DOUBLE")

                    # Merge area and volume tables and transpose table for final output
                    arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_acres")
                    output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_y3", "Cut Volume (y^3)"],["SUM_fill_y3", "Fill Volume (y^3)"],["Net_Volume", "Net Volume (y^3)"],["Total_Volume", "Total Volume (y^3)"],["cut_fill_ratio", "Cut/Fill Ratio"],["graded_area_acres","Graded Area (acres)"]], statsOutput,"Grading", "Summary", None)

                if xyzUnit == "Meter":
                    arcpy.management.CalculateField(Cut_Total, "cut_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3", "","DOUBLE")
                    arcpy.management.CalculateField(Fill_Total, "fill_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3","","DOUBLE")
                    arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_m3"])
                    arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_m3"])

                    # Calculate net, gross, and ratio statistics for cubic meters
                    CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_m3 SUM; fill_m3 SUM", None)
                    arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_m3! + !SUM_fill_m3!,2)","PYTHON3", "","DOUBLE")
                    arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_m3! - !SUM_cut_m3!,2)","PYTHON3", "","DOUBLE")
                    arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_m3!) / !SUM_fill_m3!,2)", "PYTHON3", "","DOUBLE")

                    # Merge area and volume tables and transpose table for final output for metric NEED TO CHANGE ACRES
                    arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_m2")
                    output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_m3", "Cut Volume (m^3)"],["SUM_fill_m3", "Fill Volume (m^3)"],["Net_Volume", "Net Volume (m^3)"],["Total_Volume", "Total Volume (m^3)"],["cut_fill_ratio", "Cut/Fill Ratio"],["graded_area_m2", "Graded Area (m^2)"]],statsOutput, "Grading", "Summary", None)

                # Clean up
                arcpy.management.Delete("Cut_Fill_Totals")
                arcpy.management.Delete("Cut_Total")
                arcpy.management.Delete("cutFill_poly")
                arcpy.management.Delete("Fill_Total")
                arcpy.management.Delete("total_graded_area")
                arcpy.management.Delete("TotalCutFill")

                aprxMap.addDataFromPath(cut_raster)
                aprxMap.addDataFromPath(fill_raster)

                cutName = os.path.basename(cutOut)
                fillName = os.path.basename(fillOut)

                # Apply symbology
                try:
                    for l in aprxMap.listLayers():
                        if l.isRasterLayer:
                            if l.name == cutName:
                                symCut = l.symbology
                                symCut.colorizer.stretchType = "PercentClip"
                                cr = aprx.listColorRamps("Cut")[0]
                                symCut.colorizer.colorRamp = cr

                                if xyzUnit == "Foot":
                                    symCut.colorizer.minLabel = symCut.colorizer.minLabel + " ft"
                                    symCut.colorizer.maxLabel = symCut.colorizer.maxLabel + " ft"
                                else:
                                    symCut.colorizer.minLabel = symCut.colorizer.minLabel + " m"
                                    symCut.colorizer.maxLabel = symCut.colorizer.maxLabel + " m"
                                    
                                l.symbology = symCut

                            if l.name == fillName:
                                symFill = l.symbology
                                symFill.colorizer.stretchType = "PercentClip"
                                cr = aprx.listColorRamps("Fill")[0]
                                symFill.colorizer.colorRamp = cr

                                if xyzUnit == "Foot":
                                    symFill.colorizer.minLabel = symFill.colorizer.minLabel + " ft"
                                    symFill.colorizer.maxLabel = symFill.colorizer.maxLabel + " ft"
                                else:
                                    symFill.colorizer.minLabel = symFill.colorizer.minLabel + " m"
                                    symFill.colorizer.maxLabel = symFill.colorizer.maxLabel + " m"

                                l.symbology = symFill
                except:
                    arcpy.AddMessage("Symbology not applied")
                    

            if lxmlOutputOption == True:
                tempDir = arcpy.management.CreateFolder(outputPath, "lxml_temp")
                tempDirOut = outputPath + "/lxml_temp"                
                
                arcpy.SetProgressor("default", "Converting TIN to LandXML...")
                # Convert to TIN Triangles
                tinTriangle = arcpy.ddd.TinTriangle(grade_TIN, r"in_memory\tinTriangle", "PERCENT", 1, "", "")

                # Convert tinTriangle to shapefile
                tinShapefile = arcpy.conversion.FeatureClassToShapefile(tinTriangle, tempDir)

                tin_shp = str(tempDirOut + "/tinTriangle")

                # Reading input TIN shapefile using PyShp
                in_shp = shapefile.Reader(tin_shp)
                shapeRecs = in_shp.shapeRecords()

                # Initializing landxml surface items
                namespace = {"xsi" : "http://www.w3.org/2001/XMLSchema"}
                landxml = ET.Element("LandXML",
                                     nsmap=namespace,
                                     xmlns="http://www.landxml.org/schema/LandXML-1.2",
                                     language = "English",
                                     readOnly = "false",
                                     time = "08:00:00",
                                     date = "2019-01-01",
                                     version="1.2")
                units = ET.SubElement(landxml, "Units")
                surfaces = ET.SubElement(landxml, "Surfaces")
                surface = ET.SubElement(surfaces, "Surface", name="demGrade")
                definition = ET.SubElement(surface, "Definition",
                                           surfType="TIN")
                pnts = ET.SubElement(definition, "Pnts")
                faces = ET.SubElement(definition, "Faces")

                # Dictionary to define correct units based on input
                unit_opt = {"ft":("Imperial", "squareFoot", "USSurveyFoot",
                                  "cubicFeet", "fahrenheit", "inHG"),
                            "m": ("Metric", "squareMeter", "meter",
                                  "cubicMeter", "celsius", "mmHG"),
                            "ft-int": ("Imperial", "squareFoot", "foot",
                                       "cubicFeet", "fahrenheit", "inHG")}

                if xyzUnit == "Foot":
                    unit_len = "ft"
                else:
                    unit_len = "m"

                # Define units here. Has not been tested with metric.
                unit = ET.SubElement(units,
                                     unit_opt[unit_len][0],
                                     areaUnit=unit_opt[unit_len][1],
                                     linearUnit=unit_opt[unit_len][2],
                                     volumeUnit=unit_opt[unit_len][3],
                                     temperatureUnit=unit_opt[unit_len][4],
                                     pressureUnit=unit_opt[unit_len][5])

                # Initializing output variables
                pnt_dict = {}
                face_list = []
                cnt = 0

                # Creating reference point dictionary/id for each coordinate
                # As well as LandXML points, and list of faces
                for sr in shapeRecs:
                    shape_pnt_ids = []   # id of each shape point

                    # Each shape should only have 3 points
                    for pnt in range(3):   
                        # Coordinate with y, x, z format
                        coord = (sr.shape.points[pnt][1],
                                 sr.shape.points[pnt][0],
                                 sr.shape.z[pnt])

                        # If element is new, add to dictionary and
                        # write xml point element
                        if coord not in pnt_dict:
                            cnt+=1
                            pnt_dict[coord] = cnt

                            shape_pnt_ids.append(cnt)  # Add point id to list 

                            # Individual point landxml features
                            pnt_text = f"{coord[0]:.5f} {coord[1]:.5f} {coord[2]:.3f}"
                            pnt = ET.SubElement(pnts, "P", id=str(cnt)).text = pnt_text

                        # If point is already in the point dictionary, append existing point id
                        else:
                            shape_pnt_ids.append(pnt_dict[coord])

                    # Reference face list for each shape
                    face_list.append(shape_pnt_ids)

                # Writing faces to landxml
                for face in face_list:
                    ET.SubElement(faces, "F").text = f"{face[0]} {face[1]} {face[2]}"

                # Writing output
                tree = ET.ElementTree(landxml)
                tree.write(lxmlOutput, pretty_print=True, xml_declaration=True, encoding="iso-8859-1")

                del tinShapefile
                del in_shp
                del shapeRecs

                arcpy.management.Delete(tempDir)
                arcpy.management.Delete(tinTriangle)

                arcpy.AddMessage("LandXML Exported Successfully")

            arcpy.management.Delete("grade_bounds")
            arcpy.management.Delete(grade_TIN)
            arcpy.management.Delete("grade_area_rows_buff")
            arcpy.management.Delete("cutFill_poly")
            arcpy.management.Delete("bounds_invert")
            arcpy.management.Delete("grade_area_rows")
            arcpy.management.Delete("grade_area")
            arcpy.management.Delete("grade_area_line")
            arcpy.management.Delete("grade_bound_3D")
            arcpy.management.Delete("grade_raster")
            arcpy.management.Delete("piles_graded")
            arcpy.management.Delete("piles_graded_pre")
            arcpy.management.Delete("tinEdge_final")
            arcpy.management.Delete(piles_TIN)
        
        try:
        
            arcpy.management.Delete(basePlanes_CG)
            arcpy.management.Delete(boundLines)
            arcpy.management.Delete(screenTable)
            #arcpy.management.Delete(basePlanes_pre)
            arcpy.management.Delete(rowEndPoints)
        except:
            arcpy.AddMessage("Clean up failed")

        arcpy.ResetProgressor()

        return

    def inputCheck(demInput, rowsInput, pilesInput, minReveal, maxReveal, gridRes, mapUnits):
        """Check the input for errors"""

        # Check the input for errors
        if arcpy.Exists(demInput) == False:
            arcpy.AddError("The DEM input does not exist")
            sys.exit(0)

        if arcpy.Exists(rowsInput) == False:
            arcpy.AddError("The rows input does not exist")
            sys.exit(0)

        if arcpy.Exists(pilesInput) == False:
            arcpy.AddError("The piles input does not exist")
            sys.exit(0)

        if float(minReveal) > float(maxReveal):
            arcpy.AddError("The minimum reveal is greater than the maximum reveal")
            sys.exit(0)

        arcpy.AddMessage("Grid Resolution: " + str(gridRes))
        if float(gridRes) <= 0:
            arcpy.AddError("The grid resolution is less than or equal to zero")
            sys.exit(0)

        # arcpy.AddMessage("Map Units: " + mapUnits)
        # if mapUnits not in ["Foot", "Meter"]:
        #     arcpy.AddError("The map units are not valid")
        #     sys.exit(0)
        
        # Check the spatial reference of the inputs and make sure they are the same
        demSR = arcpy.Describe(demInput).spatialReference
        rowsSR = arcpy.Describe(rowsInput).spatialReference
        pilesSR = arcpy.Describe(pilesInput).spatialReference
        
        # Check the spatial reference of the inputs and make sure they are projected
        if demSR.type != "Projected" or rowsSR.type != "Projected" or pilesSR.type != "Projected":
            arcpy.AddError("The spatial reference of the inputs are not projected")
            sys.exit(0)
        
        if demSR.name != rowsSR.name or demSR.name != pilesSR.name:
            arcpy.AddError("The spatial reference of the inputs are not the same")
            sys.exit(0)
        
        # check in the spatial resolution of the DEM in terms of the grid resolution and resample it if neccessary (>1.5 x 1.5)
        demCellSize = arcpy.GetRasterProperties_management(demInput, "CELLSIZEX")
        demCellSize = float(demCellSize.getOutput(0))
        if demCellSize > 2:
            try:
                arcpy.AddMessage(f"demExist cell size = {demCellSize}; Resampling the DEM to be within optimal grid resolution range")
                demResample = arcpy.management.Resample(demInput, "in_memory\demResample", gridRes, "NEAREST")
                
                # rename the resampled DEM to the original DEM
                arcpy.management.Rename(demResample, demInput)
                # add message if all checks pass
                arcpy.AddMessage("Input checks passed; resample complete- proceeding with analysis...")
                return demInput
            except:
                arcpy.AddMessage("Resampling the DEM failed")
                
                return demInput
        else:
            # add message if all checks pass
            arcpy.AddMessage("Input checks passed; resample not needed- proceeding with analysis...")
            return demInput
    