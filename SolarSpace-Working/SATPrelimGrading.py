########################################################################
""" SAT PRELIMINARY GRADING ASSESSMENT 

Revision log
0.0.1 - 08/30/2021 - Updated the header to the new KiloNewton tamplate.
0.0.2 - 2/9/2022 - Updated to include a range of potential tracker 
lengths and cut/fill output statistics
0.0.3 - 4/2/2022 - Updated parameters for specific outputs to be more 
clear
0.0.4 - 5/17/2022 - Updated to correct for meters
1.0.0 - 8/5/2022 - Added automatic symbology
2.0.0 - 8/30/2022 - Completely redesigned and updated efficiency, added 
vertical unit validation
2.1.0 - 12/12/2022 - Added buffer and clipping to get rid of grading 
along boundary, added ability to make exclusions based on grading depth,
added ability for volume estimate outputs
2.2.0 - Added ability to specify tracker width
2.3.0 - 1/19/2024 - Added symbology exit protocol to prevent errors & ability to ouput a preliminary graded surface
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "2.3.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.1.3"
__maintainer__  = ["Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import math
import arcpy
from arcpy import env
from arcpy.sa import *
import os
import sys

class PreliminaryGrading(object):
    def __init__(self):
        self.label = "Single Axis Tracker Preliminary Grading Assessment"
        self.description = "Analyzes a surface and calculates potential grading using theoretical solar tracker rows"
        self.canRunInBackground = False
        self.category = "Site Suitability\Civil Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input elevation raster",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Area of interest",
            name="aoi_boundary",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Polygon"]

        param2 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Tracker full row length",
            name="tracker_length",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Tracker row width",
            name="tracker_width",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Pile reveal tolerance",
            name="revTolerance",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Cut raster output dataset",
            name="cutOutput",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param7 = arcpy.Parameter(
            displayName="Fill raster output dataset",
            name="fillOutput",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param8 = arcpy.Parameter(
            displayName="Output grading volume statistics?",
            name="cutFillOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param8.value = False

        param9 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
            parameterType="Optional",
            direction="Output")

        param10 = arcpy.Parameter(
            displayName="Create exclusion areas based on maximum cut and fill depth?",
            name="exclusionOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param10.value = False

        param11 = arcpy.Parameter(
            displayName="Exclude cut or fill more than...",
            name="cutFillLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param12 = arcpy.Parameter(
            displayName="Output exclusion feature class",
            name="exclusionOut",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Derived")

        param13 = arcpy.Parameter(
            displayName="Output preliminary graded surface?",
            name="demPrelimgradeOutput",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        #param13.value = False
        
        param14 = arcpy.Parameter(
            displayName="Output preliminary graded surface name",
            name="demPrelimgradeName",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14]

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
            parameters[3].value = "300"

        if not parameters[4].altered:
            parameters[4].value = "7.5"

        if not parameters[5].altered:
            parameters[5].value = "2"

        if not parameters[6].altered:
            parameters[6].value = "prelimCut"

        if not parameters[7].altered:
            parameters[7].value = "prelimFill"

        if parameters[8].value == True:
            parameters[9].enabled = True
        else:
            parameters[9].enabled = False

        if not parameters[9].altered:
            parameters[9].value = "CutFillPrelim_Statistics"

        if parameters[10].value == True:
            parameters[11].enabled = True
            parameters[12].enabled = True
        else:
            parameters[11].enabled = False
            parameters[12].enabled = False

        if not parameters[11].altered:
            parameters[11].value = "5"

        if not parameters[12].altered:
            parameters[12].value = "cutFillExclusion"
        
        if parameters[13].value == True:
            parameters[14].enabled = True
        else:
            parameters[14].enabled = False
            
        if not parameters[14].altered:
            parameters[14].value = "demPrelimgrade"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[2].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[1].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[2].value == "Meter":
                if "Meter" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[1].setErrorMessage("Vertical and horizontal units do not match")
            else:
                parameters[1].clearMessage()

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText  # Input elevation model
        aoi_boundary = parameters[1].valueAsText  # Project boundary
        xyzUnit = parameters[2].valueAsText  # Foot or Meter
        tracker_length = parameters[3].valueAsText  # Length of tracker
        tracker_width = parameters[4].valueAsText  # Length of tracker
        revTolerance = parameters[5].valueAsText  # Reveal tolerance
        cutOutput = parameters[6].valueAsText  # Cut output raster
        fillOutput = parameters[7].valueAsText  # Fill output raster
        cutFillOption = parameters[8].value
        statsOutput = parameters[9].valueAsText
        exclusionOption = parameters[10].value # Option to create exclusion areas based on max cut or fill
        cutFillLimit = parameters[11].valueAsText # Maximum depth of cut or fill
        exclusionOut = parameters[12].valueAsText # Output exclusion feature class
        demPrelimgradeOutput = parameters[13].value # Output preliminary graded surface
        demPrelimgradeName = parameters[14].valueAsText # Output preliminary graded surface name
        
        # Set grid resolution to the DEM raster and snap to raster
        arcpy.env.snapRaster = demInput
        rasRef = arcpy.Raster(demInput)
        gridRes = arcpy.env.cellSize = rasRef.meanCellWidth
        spatialRef = arcpy.Describe(demInput).spatialReference

        # Define layout width as a factor of the tracker width
        layout_width = float(tracker_width) * 3

        arcpy.SetProgressor("default", "Creating theoretical rows across the site...")

        # Buffer the boundary out by half row length
        bufferOut = str(float(tracker_length)/2)
        boundaryBuffer = arcpy.analysis.PairwiseBuffer(aoi_boundary,  r"in_memory\boundaryBuffer", bufferOut, "ALL")

        # Clip the raster to the boundaryBuffer
        demInputClip = arcpy.management.Clip(demInput, "", "demInputClip", boundaryBuffer, "", "ClippingGeometry","NO_MAINTAIN_EXTENT")

        # Make a grid of the site at 30x30 ft or 10 x 10 m
        grid_project = arcpy.cartography.GridIndexFeatures("grid_project", boundaryBuffer, "INTERSECTFEATURE", "NO_USEPAGEUNIT", None, layout_width, layout_width)

        # Convert to point
        grid_project_point = arcpy.management.FeatureToPoint(grid_project, "grid_project_point")

        # Add XY to label points
        arcpy.management.AddXY(grid_project_point)

        # Create a raster of the northings
        northing_raster = arcpy.conversion.PointToRaster(grid_project_point, "POINT_Y", "northing_raster", "MOST_FREQUENT", "NONE", layout_width, "BUILD")

        # Resample the northings to the existing elevation
        reSampDist = str(str(gridRes) + " " + str(gridRes))
        northResample = arcpy.management.Resample(northing_raster, "northResample", reSampDist, "BILINEAR")

        arcpy.SetProgressor("default", "Calculating theoretical grading...")

        # Get the directional NS slope of the DEM
        # Process aspect
        AspectDeg = arcpy.sa.Aspect(demInputClip, "PLANAR", xyzUnit)

        AspectRad = AspectDeg * math.pi / 180

        # Run focal statistics (mean) on the input elevation based on the row length and default x distance of 30 ft or 10 m
        focal_input = str("Rectangle " + str(layout_width) + " " + str(tracker_length) + " MAP")
        demFocal = arcpy.sa.FocalStatistics(demInputClip, focal_input, "MEAN", "DATA", 90)

        # Process slope
        SlopeDeg = arcpy.sa.Slope(demFocal, "DEGREE", "1", "PLANAR", xyzUnit)
        SlopeRad = SlopeDeg * math.pi / 180

        # Process north-south slope in radians
        CosAspRad = Cos(AspectRad)
        nsRad = CosAspRad * SlopeRad

        # Process north-south slope in percent if option chosen
        nsPerc = Tan(nsRad)

        # Run focal statistics (mean) on the NS slope based on the row length and default x distance of 30 ft or 10 m
        nsFocal = arcpy.sa.FocalStatistics(nsPerc, focal_input, "MEAN", "DATA", 90)

        # Focal statistics on the northings
        yFocal = arcpy.sa.FocalStatistics(northResample, focal_input, "MEAN", "DATA", 90)

        # Calculate the "intercept" b
        intB = demFocal - nsFocal * yFocal

        # Calculate a "trend"
        tPrelim = nsFocal * northResample + intB

        # Subtract the existing elevation from the trend
        trend_dem = arcpy.sa.Minus(tPrelim, demInputClip)

        # Run focal statistics on trend_dem based on the row width - THIS MAY NEED TO BE ADJUSTED - MAYBE HALF?
        focal_trend_dem_input = str("Rectangle " + str(layout_width) + " " + str(layout_width) + " MAP")
        initGrade = arcpy.sa.FocalStatistics(trend_dem, focal_trend_dem_input, "MEAN", "DATA", 90)

        # Create the upper and lower bounds - reveal tolerance is intentionally shurnk to be conservative
        revToleranceHalf = float(revTolerance) / 2.05
        upperBound = arcpy.sa.Plus(initGrade, revToleranceHalf)
        lowerBound = arcpy.sa.Minus(initGrade, revToleranceHalf)

        arcpy.SetProgressor("default", "Creating cut and fill rasters...")

        # Screen based on the tolerance
        cutName = os.path.basename(cutOutput)
        fillName = os.path.basename(fillOutput)

        cutPrelim = arcpy.sa.SetNull(upperBound, upperBound, "VALUE > 0")
        cutRaster = arcpy.management.Clip(cutPrelim, "", cutOutput, aoi_boundary, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")

        fillPrelim = arcpy.sa.SetNull(lowerBound, lowerBound, "VALUE < 0")
        fillRaster = arcpy.management.Clip(fillPrelim, "", fillOutput, aoi_boundary, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")

        aprxMap.addDataFromPath(cutRaster)
        aprxMap.addDataFromPath(fillRaster)

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
            # report error but continue
            arcpy.AddWarning("Unable to apply Cut/Fill symbology correctly")
            pass

        # Calculate the cut-fill statistics
        if cutFillOption == True:
            
            cutFill = arcpy.management.MosaicToNewRaster([[cutRaster],[fillRaster]], workspace, "cutFill",spatialRef,"32_BIT_FLOAT",gridRes,1,"LAST","FIRST")

            arcpy.SetProgressor("default", "Calculating preliminary grading statistics...")

            # Calculate the area of one raster square
            grid_area = str(gridRes ** 2)
        
            # Create a polygon of the domain of the existing elevation
            TotalCutFill = arcpy.ddd.RasterDomain(demInput, "TotalCutFill", "POLYGON")

            # Reclassify cut-fill raster using a tolerance of +/- 1 inch - NOTE: THIS IS ONLY FOR UNITS OF FEET
            reclass_code = RemapRange([[-300, -.083, 1], [-.083, .083, 0], [.083, 300, 2]])
            cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
            reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
            grade_area = arcpy.analysis.Select(reclass_poly, "grade_area", "gridcode <> 0")

            # Sum the graded area and convert to acres from square feet
            if xyzUnit == "Foot":
                total_graded_area = arcpy.analysis.Statistics(grade_area, "total_graded_area", "Shape_Area SUM", None)
                arcpy.management.AddFields(total_graded_area, [["graded_area_acres", "DOUBLE", "Total Graded Area (acres)"]])
                arcpy.management.CalculateField(total_graded_area, "graded_area_acres", "round(!SUM_Shape_Area!/43560,2)", "PYTHON3")

            if xyzUnit == "Meter":
                total_graded_area = arcpy.analysis.Statistics(grade_area, "total_graded_area", "Shape_Area SUM", None)
                arcpy.management.AddFields(total_graded_area, [["graded_area_m2", "DOUBLE", "Total Graded Area (m^2)"]])
                arcpy.management.CalculateField(total_graded_area, "graded_area_m2", "round(!SUM_Shape_Area!,2)", "PYTHON3")

            arcpy.SetProgressorLabel("Calculating cut and fill statistics")

            # Calculate the cut-fill statistics
            Cut_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, "OID", cutRaster, "Cut_Total", "DATA", "ALL")
            Fill_Total = arcpy.sa.ZonalStatisticsAsTable(TotalCutFill, "OID", fillRaster, "Fill_Total", "DATA", "ALL")

            # Add fields to convert to cubic yards, multiply the sum by the grid resolution and convert to cubic yards or meters
            if xyzUnit == "Foot":
                arcpy.management.AddFields(Cut_Total, [["cut_y3", "DOUBLE"]])
                arcpy.management.CalculateField(Cut_Total, "cut_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3",
                                                None)
                arcpy.management.AddFields(Fill_Total, [["fill_y3", "DOUBLE"]])
                arcpy.management.CalculateField(Fill_Total, "fill_y3", "round((!SUM!*" + grid_area + ")/27,2)", "PYTHON3")
                arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_y3"])
                arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_y3"])

                # Calculate net, gross, and ratio statistics for cubic yards
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_y3 SUM; fill_y3 SUM", None)
                arcpy.management.AddFields(CutFill_Total,[["net_y3", "DOUBLE"], ["gross_y3", "DOUBLE"], ["cut_fill_ratio", "DOUBLE"]])
                arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_y3! + !SUM_fill_y3!,2)","PYTHON3")
                arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_y3! - !SUM_cut_y3!,2)","PYTHON3")
                arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_y3!) / !SUM_fill_y3!,2)", "PYTHON3")

                # Merge area and volume tables and transpose table for final output
                arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_acres")
                output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_y3", "Cut Volume (y^3)"],
                                                                                ["SUM_fill_y3", "Fill Volume (y^3)"],
                                                                                ["Net_Volume", "Net Volume (y^3)"],
                                                                                ["Total_Volume", "Total Volume (y^3)"],
                                                                                ["cut_fill_ratio", "Cut/Fill Ratio"],
                                                                                ["graded_area_acres",
                                                                                 "Graded Area (acres)"]], statsOutput,
                                                                                "Grading", "Summary", None)

            if xyzUnit == "Meter":
                arcpy.management.AddFields(Cut_Total, [["cut_m3", "DOUBLE"]])
                arcpy.management.CalculateField(Cut_Total, "cut_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3", None)
                arcpy.management.AddFields(Fill_Total, [["fill_m3", "DOUBLE"]])
                arcpy.management.CalculateField(Fill_Total, "fill_m3", "round((!SUM!*" + grid_area + "),2)", "PYTHON3")
                arcpy.management.JoinField(TotalCutFill, "OID", Cut_Total, "OID", ["cut_m3"])
                arcpy.management.JoinField(TotalCutFill, "OID", Fill_Total, "OID", ["fill_m3"])

                # Calculate net, gross, and ratio statistics for cubic meters
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, "Cut_Fill_Totals", "cut_m3 SUM; fill_m3 SUM", None)
                arcpy.management.AddFields(CutFill_Total, [["net_m3", "DOUBLE"], ["gross_m3", "DOUBLE"], ["cut_fill_ratio", "DOUBLE"]])
                arcpy.management.CalculateField(CutFill_Total, "Net_Volume", "round(!SUM_cut_m3! + !SUM_fill_m3!,2)", "PYTHON3")
                arcpy.management.CalculateField(CutFill_Total, "Total_Volume", "round(!SUM_fill_m3! - !SUM_cut_m3!,2)","PYTHON3")
                arcpy.management.CalculateField(CutFill_Total, "cut_fill_ratio","round(abs(!SUM_cut_m3!) / !SUM_fill_m3!,2)", "PYTHON3")

                # Merge area and volume tables and transpose table for final output for metric NEED TO CHANGE ACRES
                arcpy.management.JoinField(CutFill_Total, "OBJECTID", total_graded_area, "OBJECTID", "graded_area_m2")
                output_table = arcpy.management.TransposeFields(CutFill_Total, [["SUM_cut_m3", "Cut Volume (m^3)"],
                                                                                ["SUM_fill_m3", "Fill Volume (m^3)"],
                                                                                ["Net_Volume", "Net Volume (m^3)"],
                                                                                ["Total_Volume", "Total Volume (m^3)"],
                                                                                ["cut_fill_ratio", "Cut/Fill Ratio"],
                                                                                ["graded_area_m2", "Graded Area (m^2)"]],
                                                                                statsOutput, "Grading", "Summary", None)

        # Create exclusion areas based on maximum cut or fill depth
        if exclusionOption == True:

            arcpy.SetProgressor("default", "Calculating preliminary grading statistics...")

            # Reclassify the input raster
            fillMaxResult = arcpy.management.GetRasterProperties(cutFill, "MAXIMUM")
            fillMax = round(float(fillMaxResult.getOutput(0)),2)
            cutMaxResult = arcpy.management.GetRasterProperties(cutFill, "MINIMUM")
            cutMax = round(float(cutMaxResult.getOutput(0)),2)
            
            limitDef = str(cutMax) + " -" + cutFillLimit + " 1; -" +cutFillLimit + " " + cutFillLimit + " NODATA; " + cutFillLimit + " " + str(fillMax) + " 2"

            rasterReclass = arcpy.sa.Reclassify(cutFill, "VALUE", limitDef, "DATA")

            arcpy.SetProgressor("default", "Creating the exclusion areas...")

            # Convert to polygon
            exclusionFC = arcpy.conversion.RasterToPolygon(rasterReclass, exclusionOut, "SIMPLIFY", "Value", "MULTIPLE_OUTER_PART")

            aprxMap.addDataFromPath(exclusionFC)

            exclusionName = os.path.basename(exclusionOut)
        
            try:
                #Apply symbology
                exclusionLyr = aprxMap.listLayers(exclusionName)[0]
                exclusionSym = exclusionLyr.symbology
                exclusionSym.renderer.symbol.color = {"RGB": [255, 255, 0, 0]}
                exclusionSym.renderer.symbol.applySymbolFromGallery("10% Simple hatch")
                if xyzUnit == "Foot":
                    exclusionSym.renderer.label = "Grading > " + cutFillLimit + " ft"
                if xyzUnit == "Meter":
                    exclusionSym.renderer.label = "Grading > " + cutFillLimit + " m"
                exclusionLyr.symbology = exclusionSym
            except:
                # report error but continue
                arcpy.AddWarning("Unable to apply exclusion symbology correctly")
                pass
    
        # Create the preliminary graded surface 
        #arcpy.AddMessage(f'preliminary graded surface output is {demPrelimgradeName} option is {demPrelimgradeOutput}')
        if demPrelimgradeOutput == True:
            arcpy.AddMessage("Preliminary graded surface option is selected. This may take a few minutes.")
            arcpy.SetProgressor("default", "Creating preliminary graded surface from Cut/Fill rasters...")

            # Strip the path from the output name to get the name of the raster
            demPrelimgradeName = os.path.basename(demPrelimgradeName)   
            
            # Mosaic the cut and fill rasters together with the demExist to get the preliminary graded surface
            demPrelimgrade = arcpy.management.MosaicToNewRaster([[demInputClip],[cutRaster],[fillRaster]], workspace, demPrelimgradeName, spatialRef, "32_BIT_FLOAT", gridRes, 1, "SUM", "FIRST")
            
            # Add the preliminary graded surface to the map
            aprxMap.addDataFromPath(demPrelimgrade)
        else:
            arcpy.AddMessage("Preliminary graded surface option is not selected. This may not take a few minutes.")
        
        # Clean up
        arcpy.management.Delete("Cut_Fill_Totals")
        arcpy.management.Delete("Cut_Total")
        arcpy.management.Delete("cutFill_poly")
        arcpy.management.Delete("Fill_Total")
        arcpy.management.Delete("grade_area")
        arcpy.management.Delete("grid_project")
        arcpy.management.Delete("grid_project_point")
        arcpy.management.Delete("northing_raster")
        arcpy.management.Delete("total_graded_area")
        arcpy.management.Delete("TotalCutFill")
        arcpy.management.Delete("cutFill")
        arcpy.management.Delete(demInputClip)
        arcpy.management.Delete("northResample")

        arcpy.ResetProgressor()

        return