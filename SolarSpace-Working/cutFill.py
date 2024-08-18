########################################################################
"""CUT & FILL ASSESSMENT 

Revision log
0.0.1 - 8/27/2021 - New header and indentation of the code
0.0.2 - 4/2/2022 - Updated parameters for specific outputs to be more clear
1.0.0 - 8/5/2022 - Added automatic symbology
2.0.0 - 12/9/2022 - Combined zonal and regular cut fill into one script
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = "Matthew Gagne"
__status__      = "Deployed"

import arcpy
import sys
from arcpy.sa import *
from arcpy.ddd import *
import os.path
import sys

class CutFillAssessment(object):
    def __init__(self):
        self.label = "Cut & Fill Assessment"
        self.description = "Calculates cut & fill rasters and summary volume statistics from graded and existing surfaces. Allows for zonal calculations"
        self.canRunInBackground = False
        self.category = "Civil Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Graded elevation raster dataset",
            name="demGrade",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Cut output raster dataset",
            name="cutOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param4 = arcpy.Parameter(
            displayName="Fill output raster dataset",
            name="fillOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param5 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        param6 = arcpy.Parameter(
            displayName="Calculate volume statistics by zone?",
            name="zoneOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param6.value = False

        param7 = arcpy.Parameter(
            displayName="Zone input feature class",
            name="zonesInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param7.filter.list = ["Polygon"]

        param8 = arcpy.Parameter(
            displayName="Unique zone ID",
            name="zoneID",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param8.parameterDependencies = [param7.name]

        param9 = arcpy.Parameter(
            displayName="Zone output feature class",
            name="zonesOutput",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            parameters[2].value = "Foot"

        if not parameters[3].altered:
            parameters[3].value = "Cut"

        if not parameters[4].altered:
            parameters[4].value = "Fill"

        if not parameters[5].altered:
            parameters[5].value = "CutFill_Stats"

        if parameters[6].value == True:
            parameters[7].enabled = True
            parameters[8].enabled = True
            parameters[9].enabled = True
        else:
            parameters[7].enabled = False
            parameters[8].enabled = False
            parameters[9].enabled = False

        if not parameters[9].altered:
            parameters[9].value = "CutFill_Zones"
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        # Load modules
        import arcpy
        from arcpy import env

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        demExist = parameters[0].valueAsText  # Existing elevation in raster format
        demGrade = parameters[1].valueAsText  # Graded elevation in raster format
        xyzUnit = parameters[2].valueAsText  # Graded elevation in raster format
        cutOutput = parameters[3].valueAsText  # Cut raster output
        fillOutput = parameters[4].valueAsText  # Fill raster output
        statsOutput = parameters[5].valueAsText  # Statistics table output
        zoneOption = parameters[6].value  # Cost of grading per cubic yard or cubic meter (optional)
        zonesInput = parameters[7].valueAsText  # Zone input for cut fill analysis
        zoneID = parameters[8].valueAsText  # Unique zone ID
        zonesOutput = parameters[9].valueAsText  # Statistics feature class output for zones

        # Set spatial reference, grid resolution, and snap raster if needed (examples below)
        spatialRef = arcpy.Describe(demExist).spatialReference
        gridRes = arcpy.Describe(demExist).meanCellWidth
        arcpy.env.snapRaster = demExist
        mapUnits = spatialRef.linearUnitName

        # Calculate the area of one raster square
        grid_area = str(gridRes ** 2)

        arcpy.SetProgressor("default", "Comparing the graded surface to the existing surface...")

        # Create a polygon of the domain of the existing elevation
        TotalCutFill = arcpy.ddd.RasterDomain(demExist, "TotalCutFill", "POLYGON")

        # Create a raster of the delta from the existing DEM to the graded DEM, then isolate the cut (greater than 0) and fill (less than 0)
        cutFill = arcpy.sa.Minus(demGrade, demExist)

        # Create individual cut rasters and fill rasters
        cut_raster = arcpy.sa.SetNull(cutFill, cutFill, "VALUE > 0")
        cut_raster.save(cutOutput)
        fill_raster = arcpy.sa.SetNull(cutFill, cutFill, "VALUE < 0")
        fill_raster.save(fillOutput)

        arcpy.SetProgressorLabel("Calculating total graded area")

        # Reclassify cut-fill raster using a tolerance of +/- 1 inch - NOTE: THIS IS ONLY FOR UNITS OF FEET
        reclass_code = arcpy.sa.RemapRange([[-300, -.0415, 1], [-.0415, .0415, 0], [.0415, 300, 2]])
        cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
        reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        grade_area = arcpy.analysis.Select(reclass_poly, "grade_area", "gridcode <> 0")

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
            arcpy.management.CalculateField(Fill_Total, "fill_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3","", "DOUBLE")
            arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_y3"])
            arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_y3"])

            # Calculate net, gross, and ratio statistics for cubic yards
            CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_y3 SUM; fill_y3 SUM", None)
            arcpy.management.AddFields(CutFill_Total,[["net_y3", "DOUBLE"], ["gross_y3", "DOUBLE"], ["cut_fill_ratio", "DOUBLE"]])
            arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_y3! + !SUM_fill_y3!,2)","PYTHON3", None)
            arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_y3! - !SUM_cut_y3!,2)","PYTHON3", None)
            arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_y3!) / !SUM_fill_y3!,2)", "PYTHON3", None)

            # Merge area and volume tables and transpose table for final output
            arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_acres")
            output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_y3", "Cut Volume (y^3)"],
                                                                            ["SUM_fill_y3", "Fill Volume (y^3)"],
                                                                            ["Net_Volume", "Net Volume (y^3)"],
                                                                            ["Total_Volume", "Total Volume (y^3)"],
                                                                            ["cut_fill_ratio", "Cut/Fill Ratio"],
                                                                            ["graded_area_acres","Graded Area (acres)"]],
                                                                            statsOutput,"Grading", "Summary", None)

        if xyzUnit == "Meter":
            arcpy.management.CalculateField(Cut_Total, "cut_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(Fill_Total, "fill_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3","", "DOUBLE")
            arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_m3"])
            arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_m3"])

            # Calculate net, gross, and ratio statistics for cubic meters
            CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_m3 SUM; fill_m3 SUM", None)
            arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_m3! + !SUM_fill_m3!,2)","PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_m3! - !SUM_cut_m3!,2)","PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_m3!) / !SUM_fill_m3!,2)", "PYTHON3", "", "DOUBLE")
            # Merge area and volume tables and transpose table for final output for metric NEED TO CHANGE ACRES
            arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_m2")
            output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_m3", "Cut Volume (m^3)"],
                                                                            ["SUM_fill_m3", "Fill Volume (m^3)"],
                                                                            ["Net_Volume", "Net Volume (m^3)"],
                                                                            ["Total_Volume", "Total Volume (m^3)"],
                                                                            ["cut_fill_ratio", "Cut/Fill Ratio"],
                                                                            ["graded_area_m2", "Graded Area (m^2)"]],
                                                                            statsOutput, "Grading", "Summary", None)

        # Clean up
        arcpy.management.Delete("Cut_Fill_Totals")
        arcpy.management.Delete("Cut_Total")
        arcpy.management.Delete("cutFill_poly")
        arcpy.management.Delete("Fill_Total")
        arcpy.management.Delete("total_graded_area")
        arcpy.management.Delete("TotalCutFill")

        aprxMap.addDataFromPath(cut_raster)
        aprxMap.addDataFromPath(fill_raster)

        cutName = os.path.basename(cutOutput)
        fillName = os.path.basename(fillOutput)

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

        if zoneOption == True:

            arcpy.SetProgressorLabel("Gathering cut and fill statistics by zone...")

            zoneOutputName = os.path.basename(zonesOutput)

            zonesCutFill = arcpy.conversion.FeatureClassToFeatureClass(zonesInput, workspace, zoneOutputName)

            # Create zonal statistics for the cut and fill rasters
            cut_zonal = arcpy.sa.ZonalStatisticsAsTable(zonesCutFill, zoneID, cut_raster, "cut_zonal", "DATA", "ALL")
            fill_zonal = arcpy.sa.ZonalStatisticsAsTable(zonesCutFill, zoneID, fill_raster, "fill_zonal", "DATA", "ALL")

            # Add fields to convert to cubic yards, multiply the sum by the grid resolution and convert to cubic yards or meters
            if xyzUnit == "Foot":
                arcpy.management.CalculateField(cut_zonal, "cut_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3","", "DOUBLE")
                arcpy.management.CalculateField(fill_zonal, "fill_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3","","DOUBLE")
                arcpy.management.JoinField(zonesCutFill, zoneID, cut_zonal, zoneID, ["cut_y3"])
                arcpy.management.JoinField(zonesCutFill, zoneID, fill_zonal, zoneID, ["fill_y3"])

                nullOutCode = """
def nullOut(input):
    if input == None:
        return 0
    else:
        return input
"""
                arcpy.management.CalculateField(zonesCutFill, "fill_y3", "nullOut(!fill_y3!)", "PYTHON3",nullOutCode,"DOUBLE")
                arcpy.management.CalculateField(zonesCutFill, "cut_y3", "nullOut(!cut_y3!)", "PYTHON3",nullOutCode,"DOUBLE")

                # Calculate net, gross, and ratio statistics for zones
                arcpy.management.AddFields(zonesCutFill, [["net_y3", "DOUBLE", "Net Volume (y^3)"],
                                                          ["gross_y3", "DOUBLE", "Total Volume (y^3)"],
                                                          ["cut_fill_ratio", "DOUBLE", "Cut/Fill Ratio"]])
                arcpy.management.CalculateField(zonesCutFill, "net_y3", "round(!cut_y3! + !fill_y3!,2)", "PYTHON3", None)
                arcpy.management.CalculateField(zonesCutFill, "gross_y3", "round(!fill_y3! - !cut_y3!,2)", "PYTHON3", None)
                arcpy.management.CalculateField(zonesCutFill, "cut_fill_ratio", "round(abs(!cut_y3!) / !fill_y3!,2)","PYTHON3", None)

            if xyzUnit == "Meter":
                arcpy.management.CalculateField(cut_zonal, "cut_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3", "","DOUBLE")
                arcpy.management.CalculateField(fill_zonal, "fill_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3","","DOUBLE")
                arcpy.management.JoinField(zonesCutFill, zoneID, cut_zonal, zoneID, ["cut_m3"])
                arcpy.management.JoinField(zonesCutFill, zoneID, fill_zonal, zoneID, ["fill_m3"])

                nullOutCode = """
def nullOut(input):
    if input == None:
        return 0
    else:
        return input
"""
                arcpy.management.CalculateField(zonesCutFill, "fill_m3", "nullOut(!fill_m3!)", "PYTHON3",nullOutCode,"DOUBLE")
                arcpy.management.CalculateField(zonesCutFill, "cut_m3", "nullOut(!cut_m3!)", "PYTHON3",nullOutCode,"DOUBLE")

                # Calculate net, gross, and ratio statistics for zones
                arcpy.management.AddFields(zonesCutFill, [["net_m3", "DOUBLE", "Net Volume (m^3)"],
                                                          ["gross_m3", "DOUBLE", "Total Volume (m^3)"],
                                                          ["cut_fill_ratio", "DOUBLE", "Cut/Fill Ratio"]])
                arcpy.management.CalculateField(zonesCutFill, "net_m3", "round(!cut_m3! + !fill_m3!,2)", "PYTHON3", None)
                arcpy.management.CalculateField(zonesCutFill, "gross_m3", "round(!fill_m3! - !cut_m3!,2)", "PYTHON3", None)
                arcpy.management.CalculateField(zonesCutFill, "cut_fill_ratio", "round(abs(!cut_m3!) / !fill_m3!,2)","PYTHON3", None)

            aprxMap.addDataFromPath(zonesCutFill)

            arcpy.management.Delete(cut_zonal)
            arcpy.management.Delete(fill_zonal)


        arcpy.ResetProgressor()

        return