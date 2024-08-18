########################################################################
"""SINGLE AXIS TRACKER LAYOUT TOOL

Revision log
0.0.1 - 10/01/2021 - built from existing script
0.0.2 - 03/15/2022 - added row boundary expansion variable and piles for extraction of values
1.0.0 - 02/03/2023 - Updated to PYT
1.0.1 - 02/28/2023 - Added spatial join for piles if row ID doesn't exist in piles
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "John Williamson"]
__version__     = "1.1.0"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS Pro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"


import arcpy
import os
import sys
from arcpy.sa import *
from arcpy.ddd import *

class SATSiTE_Rough(object):
    def __init__(self):
        self.label = "SAT Single Reveal - Rough Grading"
        self.description = " Grading algorithm for single axis trackers with a constant reveal tolerance for every pile"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Base plane of array raster dataset",
            name="poa_base",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Tracker rows input feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["Polygon"]

        param3 = arcpy.Parameter(
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param2.name]

        param4 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param4.filter.list = ["Point"]

        param5 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["Foot", "Meter"]

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
            displayName="Graded raster output dataset",
            name="gradeOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        param9 = arcpy.Parameter(
            displayName="Pile detail output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param10 = arcpy.Parameter(
            displayName="Output plane of array and reveal rasters?",
            name="outputRevPOARasters",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param10.value = False

        param11 = arcpy.Parameter(
            displayName="Reveal output raster dataset",
            name="revOutput",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param12 = arcpy.Parameter(
            displayName="Plane of array output raster dataset",
            name="poaOutput",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param13 = arcpy.Parameter(
            displayName="Output grading volume statistics?",
            name="cutFillOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param13.value = False

        param14 = arcpy.Parameter(
            displayName="Cut output raster dataset",
            name="cutOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param15 = arcpy.Parameter(
            displayName="Fill output raster dataset",
            name="fillOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param16 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
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
        if not parameters[8].altered:
            parameters[8].value = "demGrade_r"

        if not parameters[9].altered:
            parameters[9].value = "pilesGrade"

        if parameters[10].value == True:
            parameters[11].enabled = True
            parameters[12].enabled = True

        else:
            parameters[11].enabled = False
            parameters[12].enabled = False

        if not parameters[11].altered:
            parameters[11].value = "reveal_r"

        if not parameters[12].altered:
            parameters[12].value = "poa_r"

        if parameters[13].value == True:
            parameters[14].enabled = True
            parameters[15].enabled = True
            parameters[16].enabled = True

        else:
            parameters[14].enabled = False
            parameters[15].enabled = False
            parameters[16].enabled = False

        if not parameters[14].altered:
            parameters[14].value = "Cut_r"

        if not parameters[15].altered:
            parameters[15].value = "Fill_r"

        if not parameters[16].altered:
            parameters[16].value = "CutFill_Statistics_r"

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[5].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[5].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[5].value == "Meter":
                if "Meter" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[5].setErrorMessage("Vertical and horizontal units do not match")
            else:
                parameters[5].clearMessage()
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText
        poa_base = parameters[1].valueAsText
        rowsInput = parameters[2].valueAsText
        row_ID = parameters[3].valueAsText
        pilesInput = parameters[4].valueAsText
        xyzUnit = parameters[5].valueAsText
        minReveal = parameters[6].valueAsText
        maxReveal = parameters[7].valueAsText
        gradeOut = parameters[8].valueAsText
        pilesOutput = parameters[9].valueAsText
        outputRevPOARasters = parameters[10].value
        revOutput = parameters[11].valueAsText
        poaOutput = parameters[12].valueAsText
        cutFillOption = parameters[13].value
        cutOut = parameters[14].valueAsText
        fillOut = parameters[15].valueAsText 
        statsOutput = parameters[16].valueAsText 

        # Set the DEM as the snap raster and reference for grid resolution and spatial reference
        spatialRef = arcpy.Describe(demInput).spatialReference
        gridRes = arcpy.Describe(demInput).meanCellWidth
        arcpy.env.snapRaster = demInput
        mapUnits = spatialRef.linearUnitName

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

        # Find the minimum distance north-south between rows
        rowsNear = arcpy.analysis.GenerateNearTable(rowsInput, rowsInput, r"in_memory\rowsNear", None, "NO_LOCATION","ANGLE", "ALL", 8, "GEODESIC")

        codeblock_nsDist = """
def direction(angle, nearDist):
    if ((angle < -175) or (angle >= 0 and angle < 5)) or (angle > 175 and angle < 185):
        return nearDist
    else:
        return ""
"""
        arcpy.management.CalculateField(rowsNear, "delta_y", "direction(!NEAR_ANGLE!, !NEAR_DIST!)", "PYTHON3", codeblock_nsDist, "DOUBLE")

        near_y_stats = arcpy.analysis.Statistics(rowsNear, r"in_memory\near_y_stats", "NEAR_DIST MIN")
        arcpy.management.AlterField(near_y_stats, "MIN_NEAR_DIST", "minYdist")

        arcpy.management.CalculateField(rowsInput, "joinField", "1", "PYTHON3", "", "LONG")

        arcpy.management.JoinField(rowsInput, "joinField", near_y_stats, "OBJECTID", "minYdist")

        arcpy.management.CalculateField(rowsInput, "gridRes", gridRes, "PYTHON3", "", "DOUBLE")

        # Calculate row expansions
        codeblock_nsDistSep = """
def nsExp(minYdist,gridRes):
    if minYdist > gridRes * 3:
        return 3
    else:
        return minYdist/2
"""

        arcpy.management.CalculateField(rowsInput, "nsExp", "nsExp(!minYdist!,!gridRes!)", "PYTHON3", codeblock_nsDistSep, "DOUBLE")

        rowBoundsExpand = arcpy.analysis.GraphicBuffer(rowsInput, "rowBoundsExpand", "nsExp", "SQUARE", "MITER", 10,"0 Feet")

        arcpy.management.DeleteField(rowsInput, ["nsExp", "gridRes", "joinField"])

        # Calculate spacing above and below plane of array
        delta_poa = (float(maxReveal) - float(minReveal))
        arcpy.AddMessage("Reveal tolerance: " + str(delta_poa) + " " + mapUnits)
        spacing = delta_poa / 2

        # Create the upper bound
        upperLimit = arcpy.sa.Plus(poa_base, spacing)
        upperBound = arcpy.management.MosaicToNewRaster([demInput, upperLimit], "in_memory", "upperBound", spatialRef,"32_BIT_FLOAT", gridRes, 1, "MINIMUM", "FIRST")

        # Create the lower bound
        lowerLimit = arcpy.sa.Minus(poa_base, spacing)
        lowerBound = arcpy.management.MosaicToNewRaster([demInput, lowerLimit], "in_memory", "lowerBound", spatialRef,"32_BIT_FLOAT", gridRes, 1, "MAXIMUM", "FIRST")

        # Create and the final grading DEM
        upperGrade = arcpy.sa.Minus(upperBound, demInput)
        demGrade = arcpy.sa.Plus(lowerBound, upperGrade)
        demGrade.save(gradeOut)
        aprxMap.addDataFromPath(demGrade)

        # Extract ungraded and graded elevation layers, plane of array, and reveals

        # Check if row ID field exists in piles - if so, continue, if not, do a spatial join
        rowIDCheck = arcpy.ListFields(pilesInput)
        for field in rowIDCheck:
            if field.name == row_ID:
                pilesOutName = os.path.basename(pilesOutput)
                pileOutFC = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pilesOutName)
            else:
                arcpy.analysis.SpatialJoin(
                target_features=pilesInput,
                join_features=rowsInput,
                out_feature_class=pilesOutput,
                join_operation="JOIN_ONE_TO_ONE",
                join_type="KEEP_ALL",
                match_option="INTERSECT",
                search_radius="3 Feet"
                )
                pileOutFC = pilesOutput  

        # Calculate reveals
        arcpy.SetProgressor("step", "Calculating reveals...", 0, 1)
        grade_trends = arcpy.sa.Minus(demGrade, poa_base)
        min_rev_grade = arcpy.sa.Plus(float(minReveal), grade_trends)
        max_min_reveal = arcpy.sa.ZonalStatistics(rowBoundsExpand, "OBJECTID", min_rev_grade, "MAXIMUM", "DATA")
        reveals = arcpy.sa.Minus(max_min_reveal, grade_trends)

        arcpy.SetProgressor("step", "Calculating plane of array...", 0, 1)

        # Create plane of array raster
        POA = arcpy.sa.Plus(reveals, demGrade)

        # Extract values to piles
        arcpy.sa.ExtractMultiValuesToPoints(pileOutFC, [[demInput,"demExist"],[demGrade,"demGrade"],[reveals,"reveal"],[POA,"TOP_elv"]],"BILINEAR")
        arcpy.management.CalculateField(pileOutFC, "cutFill","!demGrade! - !demExist!", "PYTHON3","", "DOUBLE")

        aprxMap.addDataFromPath(pileOutFC)

        if outputRevPOARasters == True:

            reveals.save(revOutput)
            aprxMap.addDataFromPath(reveals)

            POA.save(poaOutput)
            aprxMap.addDataFromPath(POA)

        if cutFillOption == True:
            arcpy.SetProgressor("default", "Comparing the graded surface to the existing surface...")

            # Calculate the area of one raster square
            grid_area = str(gridRes ** 2)

            # Create a polygon of the domain of the existing elevation
            TotalCutFill = arcpy.ddd.RasterDomain(demInput, "TotalCutFill", "POLYGON")

            # Create new cut and fill rasters based on the final grade
            cutFillFinal = arcpy.sa.Minus(demGrade, demInput)
            
            # Create individual cut rasters and fill rasters
            cut_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, "VALUE > 0")
            cut_raster.save(cutOut)
            fill_raster = arcpy.sa.SetNull(cutFillFinal, cutFillFinal, "VALUE < 0")
            fill_raster.save(fillOut)

            arcpy.SetProgressorLabel("Calculating total graded area")

            # Reclassify cut-fill raster using a tolerance of +/- 1 inch - NOTE: THIS IS ONLY FOR UNITS OF FEET
            reclass_code = RemapRange([[-300,-.01, 1],[-.01, .01, 0],[.01, 300, 2]])
            cutFill_reclass = arcpy.sa.Reclassify(cutFillFinal, 'VALUE', reclass_code, 'DATA')
            reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, 'cutFill_poly', 'SIMPLIFY', 'Value', 'SINGLE_OUTER_PART', None)
            grade_area = arcpy.analysis.Select(reclass_poly, 'grade_area', 'gridcode <> 0')

            # Sum the graded area and convert to acres from square feet
            if xyzUnit == "Foot":
                total_graded_area = arcpy.analysis.Statistics(grade_area, "total_graded_area", "Shape_Area SUM", None)
                arcpy.management.AddFields(total_graded_area,[["graded_area_acres", "DOUBLE", "Total Graded Area (acres)"]])
                arcpy.management.CalculateField(total_graded_area, "graded_area_acres", "round(!SUM_Shape_Area!/43560,2)","PYTHON3", None)

            if xyzUnit == "Meter":
                total_graded_area = arcpy.analysis.Statistics(grade_area, "total_graded_area", "Shape_Area SUM", None)
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
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    if l.name == cutName:
                        symCut = l.symbology
                        symCut.colorizer.stretchType = "MinimumMaximum"
                        cr = aprx.listColorRamps("Cut")[0]
                        symCut.colorizer.colorRamp = cr

                        if xyzUnit == "Foot":
                            l.label = "Cut (ft)"
                        else:
                            l.label = "Cut (m)"

                        l.symbology = symCut

                    if l.name == fillName:
                        symFill = l.symbology
                        symFill.colorizer.stretchType = "MinimumMaximum"
                        cr = aprx.listColorRamps("Fill")[0]
                        symFill.colorizer.colorRamp = cr

                        if xyzUnit == "Foot":
                            l.label = "Fill (ft)"
                        else:
                            l.label = "Fill (m)"

                        l.symbology = symFill

        return

