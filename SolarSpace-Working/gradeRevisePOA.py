############################################################
"""REVISE GRADING BASED ON ADJUSTED PLANES OF ARRAY

Description: Revises grading to planes of array that have been adjusted

Revision log
0.0.1 - 10/31/2022 - Initial scripting
1.0.0 - 01/10/2023 - Tested and deployed
1.1.0 - 03/16/2023 - Added catch if max and min reveal present in row, then just use average of max and min reveal, otherwise us the average of the reveals
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import shapefile
import lxml.etree as ET

class gradeRevisePOA(object):
    def __init__(self):
        self.label = "Revise Grading Based on Adjusted Planes of Array"
        self.description = "Revises grading to planes of array that have been adjusted"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demExist",
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
            displayName="Revised plane of array field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.parameterDependencies = [param3.name]

        param5 = arcpy.Parameter(
            displayName="Revised reveal field",
            name="revField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.parameterDependencies = [param3.name]

        param6 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param6.filter.type = "ValueList"
        param6.filter.list = ["Foot", "Meter"]

        param7 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Graded raster dataset",
            name="gradeRevOutput",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param10 = arcpy.Parameter(
            displayName="Grading boundary output feature class",
            name="gradeBoundsOut",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param11 = arcpy.Parameter(
            displayName="Output grading volume statistics?",
            name="cutFillOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param11.value = False

        param12 = arcpy.Parameter(
            displayName="Cut output raster dataset",
            name="cutOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param13 = arcpy.Parameter(
            displayName="Fill output raster dataset",
            name="fillOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param14 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
            parameterType="Optional",
            direction="Output")

        param15 = arcpy.Parameter(
            displayName="Output LandXML?",
            name="lxmlOutputOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param15.value = False

        param16 = arcpy.Parameter(
            displayName="Output LandXML file",
            name="lxmlOutput",
            datatype="DEFile",
            parameterType="Optional",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14, param15, param16]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[9].altered:
            parameters[9].value = 'demGradeRev'

        if not parameters[10].altered:
            parameters[10].value = 'demGradeRev_bounds'

        if parameters[11].value == True:
            parameters[12].enabled = True
            parameters[13].enabled = True
            parameters[14].enabled = True

        else:
            parameters[12].enabled = False
            parameters[13].enabled = False
            parameters[14].enabled = False

        if not parameters[12].altered:
            parameters[12].value = 'Cut_rev'

        if not parameters[13].altered:
            parameters[13].value = 'Fill_rev'

        if not parameters[14].altered:
            parameters[14].value = 'CutFill_Statistics_rev'

        if parameters[15].value == True:
            parameters[16].enabled = True

        else:
            parameters[16].enabled = False

        if parameters[16].altered:
            (dirnm, basenm) = os.path.split(parameters[16].valueAsText)
            if not basenm.endswith(".xml"):
                parameters[16].value = os.path.join(dirnm, "{}.xml".format(basenm))

        if not parameters[16].altered:
            parameters[16].value = 'demGradeRev_LXML.xml'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[6].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[6].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[6].value == "Meter":
                if "Meter" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[6].setErrorMessage("Vertical and horizontal units do not match")
            else:
                parameters[6].clearMessage()
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demExist = parameters[0].valueAsText
        rowsInput = parameters[1].valueAsText
        row_ID = parameters[2].valueAsText
        pilesInput = parameters[3].valueAsText
        poaField = parameters[4].valueAsText
        revField = parameters[5].valueAsText
        xyzUnit = parameters[6].valueAsText # Vertical and horizontal units
        minReveal = parameters[7].valueAsText
        maxReveal = parameters[8].valueAsText
        gradeRevOutput = parameters[9].valueAsText
        gradeBoundsOut = parameters[10].valueAsText
        cutFillOption = parameters[11].value 
        cutOut = parameters[12].valueAsText
        fillOut = parameters[13].valueAsText
        statsOutput = parameters[14].valueAsText
        lxmlOutputOption = parameters[15].value
        lxmlOutput = parameters[16].valueAsText

        outputPath = os.path.dirname(workspace)

        # Set spatial reference and grid resolution as the same as the DEM raster
        spatialRef = arcpy.Describe(demExist).spatialReference
        gridRes = arcpy.Describe(demExist).meanCellWidth
        mapUnits = spatialRef.linearUnitName

        # Set all raster outputs to snap to the DEM
        arcpy.env.snapRaster = demExist

        arcpy.SetProgressor('default', 'Analyzing the grade at the piles...')

        # Calculate north-south plane of array slope
        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

        # Add xy coordinates - will overwrite if already present
        arcpy.management.AddXY(piles_working)

        # Calculate derived base plane of array
        avgRev_stats = arcpy.analysis.Statistics(piles_working, "avgRev_stats", [[revField, "MEAN"], [revField, "MAX"], [revField, "MIN"]], row_ID)
        revealMeanField = "MEAN_" + revField
        revealMaxField = "MAX_" + revField
        revealMinField = "MIN_" + revField

        poaDevCode = """
def poaDev(maxRevRow, minRevRow, meanRevRow, maxR, minR):
    if (maxRevRow == maxR) or (minRevRow == minR):
        return (maxR + minR)/2
    else:
        return meanRevRow
"""

        arcpy.management.CalculateField(avgRev_stats, "poaDevFactor", "poaDev(!"+revealMaxField+"!, !"+revealMinField+"!, !"+revealMeanField+"!, "+maxReveal+", "+minReveal+")", "PYTHON3", poaDevCode, "DOUBLE")

        revTolerance = float(maxReveal) - float(minReveal)
        arcpy.management.JoinField(piles_working, row_ID, avgRev_stats, row_ID, "poaDevFactor")
        arcpy.management.CalculateField(piles_working, "basePlaneDev","(!"+poaField+"! - !poaDevFactor!)", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
        coorStatsInput = [["basePlaneDev", "MEAN"], ["POINT_Y", "MEAN"]]
        coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, ["MEAN_basePlaneDev", "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(piles_working, "zy_bar","(!basePlaneDev! + !MEAN_basePlaneDev!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStats, "nsSlope_BP", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

        # Join slope to piles_working
        arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope_BP"])

        # Find the intercept
        arcpy.management.CalculateField(piles_working, "bInit_BP", "!basePlaneDev! - !nsSlope_BP! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        newPointStats = arcpy.analysis.Statistics(piles_working, "newPointStats", [["bInit_BP", "MEAN"],["nsSlope_BP", "MEAN"]], row_ID)

        arcpy.SetProgressor('default', 'Interpolating the planes of array...')

        # Create a working feature class for the rows
        rows_working = arcpy.conversion.FeatureClassToFeatureClass(rowsInput, workspace, "rows_working")

        # Get the extents of the rows. This assumes rows are directly north-south
        # THIS WOULD WORK FOR V3.0.2 AND UP: arcpy.management.CalculateGeometryAttributes(rows_working, [["maxX", "EXTENT_MAX_X"],["minX", "EXTENT_MIN_X"],["maxY", "EXTENT_MAX_Y"],["minY", "EXTENT_MIN_Y"]])

        # Create corner points of the rows
        rowCornerPoints = arcpy.management.CreateFeatureclass("in_memory", "rowCornerPoints", "POINT", "#", "DISABLED", "DISABLED", rows_working)
        arcpy.management.AddField(rowCornerPoints, "PolygonOID", "LONG")
        arcpy.management.AddField(rowCornerPoints, "Position", "TEXT")

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
        return y + .5
    else:
        return y - .5
"""
        
        arcpy.management.CalculateField(rowCornerPoints, "newY", "newPTy(!Position!,!POINT_Y!)", "PYTHON3", codeblock_newPTy, "DOUBLE")

        # Create new points
        newBoundPoints_pre = arcpy.management.XYTableToPoint(rowCornerPoints, "in_memory/newBoundPoints_pre", "newX", "newY", "", spatialRef)

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

        arcpy.management.CalculateField(newBoundPoints_pre, "ptOrder", "ordPoint(!Position!)", "PYTHON3", codeblock_order, "LONG")

        newBoundPoints = arcpy.analysis.SpatialJoin(newBoundPoints_pre, rowsInput, "newBoundPoints","JOIN_ONE_TO_ONE","KEEP_ALL","","INTERSECT", "2 Feet")

        # Calculate base plane of array elevation at each point
        arcpy.management.JoinField(newBoundPoints, "PolygonOID", rows_working, "OBJECTID", row_ID)
        arcpy.management.JoinField(newBoundPoints, row_ID, newPointStats, row_ID, [["MEAN_nsSlope_BP"],["MEAN_bInit_BP"]])

        arcpy.management.CalculateField(newBoundPoints, "basePlaneDev", "!MEAN_nsSlope_BP! * !newY! + !MEAN_bInit_BP!", "PYTHON3", "", "DOUBLE")

        # Make points 3D
        bound3Dpoints = arcpy.ddd.FeatureTo3DByAttribute(newBoundPoints, "bound3Dpoints", "basePlaneDev")

        # Create lines
        boundLine = arcpy.management.PointsToLine(bound3Dpoints, "boundLine", "PolygonOID", "ptOrder", "CLOSE")

        # Create TIN
        tin_name = str(outputPath + "/basePlaneTIN") 
        basePlaneTIN = arcpy.ddd.CreateTin(tin_name, spatialRef,"boundLine Shape.Z Hard_Line <None>")

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
        rowBounds_pre_diss = arcpy.management.Dissolve(rowBounds_pre, "rowBounds_pre_diss")

        extentStats = arcpy.analysis.Statistics(rowCornerPoints, "extentStats", [["POINT_X", "MAX"], ["POINT_X", "MIN"], ["POINT_Y", "MAX"], ["POINT_Y", "MIN"]],"PolygonOID")
        arcpy.management.CalculateField(extentStats, "rowWidth", "!MAX_POINT_X! - !MIN_POINT_X!", "PYTHON3", "", "DOUBLE")

        arcpy.management.JoinField(rowBounds_pre_diss, "OBJECTID", extentStats, "PolygonOID", [["rowWidth"]])
        arcpy.management.CalculateField(rowBounds_pre_diss, "buffDist", "!rowWidth! - 10", "PYTHON3", "", "DOUBLE")

        # Buffer back in for rows on the edge 
        # NEED AN OPTION FOR METERS
        basePlanesBounds = arcpy.analysis.GraphicBuffer(rowBounds_pre_diss, "basePlanesBounds", "buffDist")

        # Clip TIN
        arcpy.ddd.EditTin(basePlaneTIN, "basePlanesBounds <None> <None> Hard_Clip false", "DELAUNAY")

        # Convert to raster
        basePlaneDev = arcpy.ddd.TinRaster(basePlaneTIN, "basePlaneDev","FLOAT", "LINEAR", "CELLSIZE", 1, gridRes)

        arcpy.SetProgressor('default', 'Deriving grading for the site...')

        # Calculate spacing above and below base planes for the new reveal tolerance
        spacing = revTolerance/2

        rowBoundsExpand = arcpy.analysis.GraphicBuffer(rowsInput, "rowBoundsExpand", "3 Feet", "SQUARE", "MITER", 10, "0 Feet")

        # Create the upper bound
        upperLimit = arcpy.sa.Plus(basePlaneDev, spacing)
        upperBound = arcpy.management.MosaicToNewRaster([demExist,upperLimit],'in_memory','upperBound',spatialRef,'32_BIT_FLOAT',gridRes,1,'MINIMUM','FIRST')

        # Create the lower bound
        lowerLimit = arcpy.sa.Minus(basePlaneDev, spacing)
        lowerBound = arcpy.management.MosaicToNewRaster([demExist,lowerLimit],'in_memory','lowerBound',spatialRef,'32_BIT_FLOAT',gridRes,1,'MAXIMUM','FIRST')

        # Create and the final grading DEM
        upperGrade = arcpy.sa.Minus(upperBound, demExist)
        demGrade = arcpy.sa.Plus(lowerBound, upperGrade)

        # Calculate reveals 
        grade_trends = arcpy.sa.Minus(demGrade, basePlaneDev)
        min_rev_grade = arcpy.sa.Plus(float(minReveal), grade_trends)
        max_min_reveal = arcpy.sa.ZonalStatistics(rowBoundsExpand, row_ID, min_rev_grade, 'MAXIMUM', 'DATA')
        reveals = arcpy.sa.Minus(max_min_reveal,grade_trends)

        # Create plane of array raster
        POA =  arcpy.sa.Plus(reveals, demGrade)

        # Extract ungraded and graded elevation layers
        arcpy.management.CalculateField(piles_working, "demGrade_rev", "!"+poaField+"!-!"+revField+"!", "PYTHON3","","DOUBLE")

        arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[demExist, 'demExist_temp']], 'BILINEAR')

        # Create a cutFill column and create a layer with only piles that require grading
        arcpy.management.CalculateField(piles_working, "cutFill_rev", "!demGrade_rev!-!demExist_temp!", "PYTHON3","","DOUBLE")

        piles_graded_pre = arcpy.analysis.Select(piles_working, 'in_memory\piles_graded_pre', 'cutFill_rev < -0.0415 OR cutFill_rev > 0.0415' )

        # Subtract the existing elevation from the graded elevation
        cutFill = arcpy.sa.Minus(demGrade,demExist)

        # Reclassify cut-fill raster using tolerance
        reclass_code = RemapRange([[-300,-1*float(.0415), 1],[-1*float(.0415), float(.0415), 0],[float(.0415), 300, 2]])
        cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
        reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "in_memory\cutFill_poly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
        grade_area = arcpy.analysis.Select(reclass_poly, "in_memory\grade_area", "gridcode <> 0")

        # Select areas that intersect piles that are graded
        grade_intersect = arcpy.management.SelectLayerByLocation(grade_area, 'INTERSECT', piles_graded_pre)

        arcpy.SetProgressor('default', 'Refining the grading boundaries...')
        
        # Buffer the graded areas by 5 feet close small holes and merge areas within 10 feet of each other
        hole_close_buffer = "10 Feet"
        grade_area_rows_buff = arcpy.analysis.PairwiseBuffer(grade_intersect, "in_memory\grade_area_rows_buff", hole_close_buffer, "ALL")
        
        # Invert the buffer to just inside the graded area to eliminate small areas
        buffer_in = "-9 Feet"
        bounds_invert = arcpy.analysis.PairwiseBuffer(grade_area_rows_buff, "bounds_invert", buffer_in, "ALL")

        # Extend the graded areas to 2 the raster resolution outside of the graded areas to join close areas  
        bounds_extend = "3 Feet"

        grade_bounds_pre = arcpy.analysis.PairwiseBuffer(bounds_invert, "grade_bounds_pre", bounds_extend, "ALL") 

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
        piles_intersect = arcpy.management.SelectLayerByLocation(piles_working, 'INTERSECT', grade_bounds)
        piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, 'piles_graded')

        # Convert the buffered layer to polylines and interpolate the existing elevation
        grade_area_line = arcpy.management.FeatureToLine(grade_bounds, "grade_area_line")
        grade_bound_3D = arcpy.sa.InterpolateShape(demExist, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

        arcpy.SetProgressor('default', 'Creating the final graded raster...')

        # Create TIN between graded piles and refine to graded area, and extract the 3D edges
        tin_name_piles = str(outputPath + "\piles_TIN")
        piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, "piles_graded demGrade_rev masspoints")
        tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
        tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line, None, "NEW_SELECTION", "INVERT")
        tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace, "tinEdge_final")

        # Create a TIN from the bound and piles layer
        tin_name = str(outputPath + "\grade_TIN")
        grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
        grade_raster = arcpy.ddd.TinRaster(grade_TIN, "grade_raster","FLOAT", "NATURAL_NEIGHBORS", "CELLSIZE", 1, gridRes)

        gradeName = os.path.basename(gradeRevOutput)

        # Clip the grade raster to the grading areas
        grade_final = arcpy.management.Clip(grade_raster,"",gradeName, grade_bounds, "", "ClippingGeometry")

        aprxMap.addDataFromPath(grade_final)
        aprxMap.addDataFromPath(grade_bounds)

        if cutFillOption == True:
            arcpy.SetProgressor('default', 'Comparing the graded surface to the existing surface...')

            # Calculate the area of one raster square
            grid_area = str(gridRes ** 2)

            # Create a polygon of the domain of the existing elevation
            TotalCutFill = arcpy.ddd.RasterDomain(demExist, 'TotalCutFill', 'POLYGON')
            
            # Create new cut and fill rasters based on the final grade
            cutFillFinal = arcpy.sa.Minus(grade_final, demExist)
            
            # Create individual cut rasters and fill rasters
            cut_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, 'VALUE > 0')
            cut_raster.save(cutOut)
            fill_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, 'VALUE < 0')
            fill_raster.save(fillOut)

            arcpy.SetProgressorLabel('Calculating total graded area')

            # Sum the graded area and convert to acres from square feet
            if xyzUnit == "Foot":
                total_graded_area = arcpy.analysis.Statistics(grade_bounds, 'total_graded_area', 'Shape_Area SUM', None)
                arcpy.management.AddFields(total_graded_area,[['graded_area_acres', 'DOUBLE', 'Total Graded Area (acres)']])
                arcpy.management.CalculateField(total_graded_area, 'graded_area_acres', 'round(!SUM_Shape_Area!/43560,2)','PYTHON3', None)

            if xyzUnit == "Meter":
                total_graded_area = arcpy.analysis.Statistics(grade_bounds, 'total_graded_area', 'Shape_Area SUM', None)
                arcpy.management.AddFields(total_graded_area, [['graded_area_m2', 'DOUBLE', 'Total Graded Area (m^2)']])
                arcpy.management.CalculateField(total_graded_area, 'graded_area_m2', 'round(!SUM_Shape_Area!,2)', 'PYTHON3',None)

            arcpy.SetProgressorLabel('Calculating cut and fill statistics')

            # Calculate the cut-fill statistics
            Cut_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, 'OID', cut_raster, 'Cut_Total', 'DATA', 'ALL')
            Fill_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, 'OID', fill_raster, 'Fill_Total', 'DATA', 'ALL')

            # Add fields to convert to cubic yards, multiply the sum by the grid resolution and convert to cubic yards or meters
            if xyzUnit == "Foot":
                arcpy.management.CalculateField(Cut_Total, 'cut_y3', 'round((!SUM!*' + grid_area + ')/27,2)', 'PYTHON3',"", "DOUBLE")
                arcpy.management.CalculateField(Fill_Total, 'fill_y3', 'round((!SUM!*' + grid_area + ')/27,2)', 'PYTHON3',"","DOUBLE")
                arcpy.management.JoinField(TotalCutFill, 'OID', Cut_Total, 'OID', ['cut_y3'])
                arcpy.management.JoinField(TotalCutFill, 'OID', Fill_Total, 'OID', ['fill_y3'])

                # Calculate net, gross, and ratio statistics for cubic yards
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, 'Cut_Fill_Totals', 'cut_y3 SUM; fill_y3 SUM', None)
                arcpy.management.CalculateField(CutFill_Total, 'Net_Volume', 'round(!SUM_cut_y3! + !SUM_fill_y3!,2)','PYTHON3', "","DOUBLE")
                arcpy.management.CalculateField(CutFill_Total, 'Total_Volume', 'round(!SUM_fill_y3! - !SUM_cut_y3!,2)','PYTHON3', "","DOUBLE")
                arcpy.management.CalculateField(CutFill_Total, 'cut_fill_ratio','round(abs(!SUM_cut_y3!) / !SUM_fill_y3!,2)', 'PYTHON3', "","DOUBLE")

                # Merge area and volume tables and transpose table for final output
                arcpy.management.JoinField(CutFill_Total, 'OBJECTID', total_graded_area, 'OBJECTID', 'graded_area_acres')
                output_table = arcpy.management.TransposeFields(CutFill_Total, [['SUM_cut_y3', 'Cut Volume (y^3)'],['SUM_fill_y3', 'Fill Volume (y^3)'],['Net_Volume', 'Net Volume (y^3)'],['Total_Volume', 'Total Volume (y^3)'],['cut_fill_ratio', 'Cut/Fill Ratio'],['graded_area_acres','Graded Area (acres)']], statsOutput,'Grading', 'Summary', None)

            if xyzUnit == "Meter":
                arcpy.management.CalculateField(Cut_Total, 'cut_m3', 'round((!SUM!*' + grid_area + '),2)', 'PYTHON3', "","DOUBLE")
                arcpy.management.CalculateField(Fill_Total, 'fill_m3', 'round((!SUM!*' + grid_area + '),2)', 'PYTHON3',"","DOUBLE")
                arcpy.management.JoinField(TotalCutFill, 'OID', Cut_Total, 'OID', ['cut_m3'])
                arcpy.management.JoinField(TotalCutFill, 'OID', Fill_Total, 'OID', ['fill_m3'])

                # Calculate net, gross, and ratio statistics for cubic meters
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, 'Cut_Fill_Totals', 'cut_m3 SUM; fill_m3 SUM', None)
                arcpy.management.CalculateField(CutFill_Total, 'Net_Volume', 'round(!SUM_cut_m3! + !SUM_fill_m3!,2)','PYTHON3', "","DOUBLE")
                arcpy.management.CalculateField(CutFill_Total, 'Total_Volume', 'round(!SUM_fill_m3! - !SUM_cut_m3!,2)','PYTHON3', "","DOUBLE")
                arcpy.management.CalculateField(CutFill_Total, 'cut_fill_ratio','round(abs(!SUM_cut_m3!) / !SUM_fill_m3!,2)', 'PYTHON3', "","DOUBLE")

                # Merge area and volume tables and transpose table for final output for metric NEED TO CHANGE ACRES
                arcpy.management.JoinField(CutFill_Total, 'OBJECTID', total_graded_area, 'OBJECTID', 'graded_area_m2')
                output_table = arcpy.management.TransposeFields(CutFill_Total, [['SUM_cut_m3', 'Cut Volume (m^3)'],['SUM_fill_m3', 'Fill Volume (m^3)'],['Net_Volume', 'Net Volume (m^3)'],['Total_Volume', 'Total Volume (m^3)'],['cut_fill_ratio', 'Cut/Fill Ratio'],['graded_area_m2', 'Graded Area (m^2)']],statsOutput, 'Grading', 'Summary', None)

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
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    if l.name == cutName:
                        symCut = l.symbology
                        symCut.colorizer.stretchType = "MinimumMaximum"
                        cr = aprx.listColorRamps('Cut')[0]
                        symCut.colorizer.colorRamp = cr

                        if xyzUnit == "Foot":
                            l.label = "Cut (ft)"
                        else:
                            l.label = "Cut (m)"

                        l.symbology = symCut

                    if l.name == fillName:
                        symFill = l.symbology
                        symFill.colorizer.stretchType = "MinimumMaximum"
                        cr = aprx.listColorRamps('Fill')[0]
                        symFill.colorizer.colorRamp = cr

                        if xyzUnit == "Foot":
                            l.label = "Fill (ft)"
                        else:
                            l.label = "Fill (m)"

                        l.symbology = symFill

        if lxmlOutputOption == True:
            tempDir = arcpy.management.CreateFolder(outputPath, "lxml_temp")
            tempDirOut = outputPath + "/lxml_temp"

            # Convert to TIN Triangles
            tinTriangle = arcpy.ddd.TinTriangle(grade_TIN, "tinTriangle", "PERCENT", 1, '', '')

            # Convert tinTriangle to shapefile
            tinShapefile = arcpy.conversion.FeatureClassToShapefile(tinTriangle, tempDir)

            tin_shp = str(tempDirOut + "/tinTriangle")

            # Reading input TIN shapefile using PyShp
            in_shp = shapefile.Reader(tin_shp)
            shapeRecs = in_shp.shapeRecords()

            # Initializing landxml surface items
            namespace = {'xsi' : "http://www.w3.org/2001/XMLSchema"}
            landxml = ET.Element('LandXML',
                                 nsmap=namespace,
                                 xmlns="http://www.landxml.org/schema/LandXML-1.2",
                                 language = 'English',
                                 readOnly = 'false',
                                 time = '08:00:00',
                                 date = '2019-01-01',
                                 version="1.2")
            units = ET.SubElement(landxml, 'Units')
            surfaces = ET.SubElement(landxml, 'Surfaces')
            surface = ET.SubElement(surfaces, 'Surface', name="demGrade")
            definition = ET.SubElement(surface, 'Definition',
                                       surfType="TIN")
            pnts = ET.SubElement(definition, 'Pnts')
            faces = ET.SubElement(definition, 'Faces')

            # Dictionary to define correct units based on input
            unit_opt = {'ft':('Imperial', 'squareFoot', 'USSurveyFoot',
                              'cubicFeet', 'fahrenheit', 'inHG'),
                        'm': ('Metric', 'squareMeter', 'meter',
                              'cubicMeter', 'celsius', 'mmHG'),
                        'ft-int': ('Imperial', 'squareFoot', 'foot',
                                   'cubicFeet', 'fahrenheit', 'inHG')}

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
                        pnt_text = f'{coord[0]:.5f} {coord[1]:.5f} {coord[2]:.3f}'
                        pnt = ET.SubElement(pnts, 'P', id=str(cnt)).text = pnt_text

                    # If point is already in the point dictionary, append existing point id
                    else:
                        shape_pnt_ids.append(pnt_dict[coord])

                # Reference face list for each shape
                face_list.append(shape_pnt_ids)

            # Writing faces to landxml
            for face in face_list:
                ET.SubElement(faces, 'F').text = f'{face[0]} {face[1]} {face[2]}'

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
        arcpy.management.Delete("grade_area")
        arcpy.management.Delete("grade_area_line")
        arcpy.management.Delete("grade_bound_3D")
        arcpy.management.Delete("grade_raster")
        arcpy.management.Delete("piles_graded")
        arcpy.management.Delete("piles_graded_pre")
        arcpy.management.Delete("tinEdge_final")
        arcpy.management.Delete(piles_TIN)
        arcpy.management.Delete(rows_working)
        arcpy.management.Delete(coorStats)
        arcpy.management.Delete(avgRev_stats)
        arcpy.management.Delete(sumStats)
        arcpy.management.Delete(newPointStats)
        arcpy.management.Delete(rowCornerPoints)
        arcpy.management.Delete(newBoundPoints)
        arcpy.management.Delete(tin_name)
        arcpy.management.Delete(tinEdge_piles)
        arcpy.management.Delete(tin_name_piles)
        arcpy.management.Delete(piles_working)
        arcpy.management.Delete(basePlaneDev)
        arcpy.management.Delete(basePlanesBounds)
        arcpy.management.Delete(bound3Dpoints)
        arcpy.management.Delete(boundLine)
        arcpy.management.Delete(expTable)
        arcpy.management.Delete(extentStats)
        arcpy.management.Delete(grade_bounds_pre)
        arcpy.management.Delete(rowBounds_pre)
        arcpy.management.Delete(rowBounds_pre_diss)
        arcpy.management.Delete(rowBoundsExpand)

        return
