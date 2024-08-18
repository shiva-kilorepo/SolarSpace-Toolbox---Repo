########################################################################
"""SMOOTHED GRADING FROM ROUGH GRADING

Revision log
v0.0.1 - 3/15/2022 - Adapted from full smooth grading script
v1.0.0 - 1/9/2023 - Upgraded to Python Toolbox format, revised grading 
boundary derivation for simplified boundaries
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

class SmoothRoughGrading(object):
    def __init__(self):
        self.label = "Smoothed Grading from Rough Grading"
        self.description = " Creates smoothed grading from rough grading output"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Rough grading elevation raster dataset",
            name="demGrade",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["Point"]

        param3 = arcpy.Parameter(
            displayName="Smoothed grading output raster dataset",
            name="gradeOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        param4 = arcpy.Parameter(
            displayName="Grading boundary output feature class",
            name="gradeBoundsOut",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        param5 = arcpy.Parameter(
            displayName="Output grading volume statistics?",
            name="cutFillOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param5value = False

        param6 = arcpy.Parameter(
            displayName="Cut output raster dataset",
            name="cutOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param7 = arcpy.Parameter(
            displayName="Fill output raster dataset",
            name="fillOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param8 = arcpy.Parameter(
            displayName="Volume summary table",
            name="statsOutput",
            datatype="DETable",
            parameterType="Optional",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[3].altered:
            parameters[3].value = 'demGrade_s'

        if not parameters[4].altered:
            parameters[4].value = 'gradeBounds'
            
        if parameters[5].value == True:
            parameters[6].enabled = True
            parameters[7].enabled = True
            parameters[8].enabled = True

        else:
            parameters[6].enabled = False
            parameters[7].enabled = False
            parameters[8].enabled = False

        if not parameters[6].altered:
            parameters[6].value = 'Cut'

        if not parameters[7].altered:
            parameters[7].value = 'Fill'

        if not parameters[8].altered:
            parameters[8].value = 'CutFill_Statistics'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput=True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demExist = parameters[0].valueAsText # Existing elevation in raster format
        demGrade = parameters[1].valueAsText # Rough graded elevation in raster format
        pilesInput = parameters[2].valueAsText # pile layer
        gradeOut = parameters[3].valueAsText # Graded raster output dataset
        gradeBoundsOut = parameters[4].valueAsText
        cutFillOption = parameters[5].value
        cutOut = parameters[6].valueAsText
        fillOut = parameters[7].valueAsText
        statsOutput = parameters[8].valueAsText

        outputPath = os.path.dirname(workspace)

        # Set the DEM as the snap raster and reference for grid resolution and spatial reference
        spatialRef = arcpy.Describe(demExist).spatialReference
        gridRes = arcpy.Describe(demExist).meanCellWidth
        arcpy.env.snapRaster = demExist
        mapUnits = spatialRef.linearUnitName

        # Extract ungraded and graded elevation layers
        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

        # Subtract the existing elevation from the graded elevation
        cutFill = arcpy.sa.Minus(demGrade,demExist)

        arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[demGrade,"demGrade_temp"],[cutFill, 'cutFill_temp']], 'BILINEAR')

        piles_graded_pre = arcpy.analysis.Select(piles_working, 'piles_graded_pre', 'cutFill_temp < -0.083 OR cutFill_temp > 0.083' )

        # Reclassify cut-fill raster using tolerance
        reclass_code = RemapRange([[-300,-1*float(.083), 1],[-1*float(.083), float(.083), 0],[float(.083), 300, 2]])
        cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
        reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
        grade_area = arcpy.analysis.Select(reclass_poly, "grade_area", "gridcode <> 0")

        # Select areas that intersect piles that are graded
        grade_intersect = arcpy.management.SelectLayerByLocation(grade_area, 'INTERSECT', piles_graded_pre)
        grade_area_rows = arcpy.conversion.FeatureClassToFeatureClass(grade_intersect, workspace, 'grade_area_rows')

        # Buffer the graded areas by 5 feet close small holes and merge areas within 10 feet of each other
        hole_close_buffer = "10 Feet"
        grade_area_rows_buff = arcpy.analysis.PairwiseBuffer(grade_area_rows, 'grade_area_rows_buff', hole_close_buffer, "ALL")

        # Invert the buffer to just inside the graded area to eliminate small areas
        buffer_in = "-9 Feet"
        bounds_invert = arcpy.analysis.PairwiseBuffer(grade_area_rows_buff, 'bounds_invert', buffer_in, "ALL")

        # Extend the graded areas to 2 the raster resolution outside of the graded areas to join close areas  
        bounds_extend = "3 Feet"

        grade_bounds_pre = arcpy.analysis.PairwiseBuffer(bounds_invert, "grade_bounds_pre", bounds_extend, "ALL")

        if gridRes > 2:
            simplifyFactor = 1
        else:
            simplifyFactor = gridRes/2

#        if xyzUnit == "Foot":
        simpInput = str(simplifyFactor) + " Feet"
#        else:
#            simpInput = str(simplifyFactor) + " Meter"
        
        gradeBoundsName = os.path.basename(gradeBoundsOut)

        grade_bounds = arcpy.cartography.SimplifyPolygon(grade_bounds_pre, gradeBoundsName, "WEIGHTED_AREA", simpInput, "0 SquareFeet", "RESOLVE_ERRORS", "KEEP_COLLAPSED_POINTS", None)

        # Select the sample points and the piles within graded areas
        piles_intersect = arcpy.SelectLayerByLocation_management(piles_working, 'INTERSECT', grade_bounds)
        piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, 'piles_graded')

        # Convert the buffered layer to polylines and interpolate the existing elevation
        grade_area_line = arcpy.management.FeatureToLine(grade_bounds, "grade_area_line")
        grade_bound_3D = arcpy.sa.InterpolateShape(demExist, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

        # Create TIN between graded piles and refine to graded area, and extract the 3D edges
        tin_name_piles = str(outputPath + "\piles_TIN")
        piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, "piles_graded demGrade_temp masspoints")
        tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
        tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line, None, "NEW_SELECTION", "INVERT")
        tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace, "tinEdge_final")

        # Create a TIN from the bound and piles layer
        tin_name = str(outputPath + "\grade_TIN")
        grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef, "grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
        editTinInput = gradeBoundsName + " <None> <None> Hard_Clip false"
        arcpy.ddd.EditTin(grade_TIN, editTinInput, "DELAUNAY")

        gradeRasterName = os.path.basename(gradeOut)

        grade_raster = arcpy.ddd.TinRaster(grade_TIN, gradeRasterName,"FLOAT", "NATURAL_NEIGHBORS", "CELLSIZE", 1, gridRes)

        # Add output to map
        aprxMap.addDataFromPath(grade_bounds)
        aprxMap.addDataFromPath(grade_raster)

        if cutFillOption == True:
            arcpy.SetProgressor('default', 'Comparing the graded surface to the existing surface...')

            # Calculate the area of one raster square
            grid_area = str(gridRes ** 2)

            # Create a polygon of the domain of the existing elevation
            TotalCutFill = arcpy.ddd.RasterDomain(demInput, 'TotalCutFill', 'POLYGON')

            # Create new cut and fill rasters based on the final grade
            cutFillFinal = arcpy.sa.Minus(grade_raster, demInput)
            
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
                arcpy.management.AddFields(Cut_Total, [['cut_y3', 'DOUBLE']])
                arcpy.management.CalculateField(Cut_Total, 'cut_y3', 'round((!SUM!*' + grid_area + ')/27,2)', 'PYTHON3',None)
                arcpy.management.AddFields(Fill_Total, [['fill_y3', 'DOUBLE']])
                arcpy.management.CalculateField(Fill_Total, 'fill_y3', 'round((!SUM!*' + grid_area + ')/27,2)', 'PYTHON3',None)
                arcpy.management.JoinField(TotalCutFill, 'OID', Cut_Total, 'OID', ['cut_y3'])
                arcpy.management.JoinField(TotalCutFill, 'OID', Fill_Total, 'OID', ['fill_y3'])

                # Calculate net, gross, and ratio statistics for cubic yards
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, 'Cut_Fill_Totals', 'cut_y3 SUM; fill_y3 SUM', None)
                arcpy.management.AddFields(CutFill_Total,[['net_y3', 'DOUBLE'], ['gross_y3', 'DOUBLE'], ['cut_fill_ratio', 'DOUBLE']])
                arcpy.management.CalculateField(CutFill_Total, 'Net_Volume', 'round(!SUM_cut_y3! + !SUM_fill_y3!,2)','PYTHON3', None)
                arcpy.management.CalculateField(CutFill_Total, 'Total_Volume', 'round(!SUM_fill_y3! - !SUM_cut_y3!,2)','PYTHON3', None)
                arcpy.management.CalculateField(CutFill_Total, 'cut_fill_ratio','round(abs(!SUM_cut_y3!) / !SUM_fill_y3!,2)', 'PYTHON3', None)

                # Merge area and volume tables and transpose table for final output
                arcpy.management.JoinField(CutFill_Total, 'OBJECTID', total_graded_area, 'OBJECTID', 'graded_area_acres')
                output_table = arcpy.management.TransposeFields(CutFill_Total, [['SUM_cut_y3', 'Cut Volume (y^3)'],['SUM_fill_y3', 'Fill Volume (y^3)'],['Net_Volume', 'Net Volume (y^3)'],['Total_Volume', 'Total Volume (y^3)'],['cut_fill_ratio', 'Cut/Fill Ratio'],['graded_area_acres','Graded Area (acres)']], statsOutput,'Grading', 'Summary', None)

            if xyzUnit == "Meter":
                arcpy.management.AddFields(Cut_Total, [['cut_m3', 'DOUBLE']])
                arcpy.management.CalculateField(Cut_Total, 'cut_m3', 'round((!SUM!*' + grid_area + '),2)', 'PYTHON3', None)
                arcpy.management.AddFields(Fill_Total, [['fill_m3', 'DOUBLE']])
                arcpy.management.CalculateField(Fill_Total, 'fill_m3', 'round((!SUM!*' + grid_area + '),2)', 'PYTHON3',None)
                arcpy.management.JoinField(TotalCutFill, 'OID', Cut_Total, 'OID', ['cut_m3'])
                arcpy.management.JoinField(TotalCutFill, 'OID', Fill_Total, 'OID', ['fill_m3'])

                # Calculate net, gross, and ratio statistics for cubic meters
                CutFill_Total = arcpy.analysis.Statistics(TotalCutFill, 'Cut_Fill_Totals', 'cut_m3 SUM; fill_m3 SUM', None)
                arcpy.management.AddFields(CutFill_Total,[['net_m3', 'DOUBLE'], ['gross_m3', 'DOUBLE'], ['cut_fill_ratio', 'DOUBLE']])
                arcpy.management.CalculateField(CutFill_Total, 'Net_Volume', 'round(!SUM_cut_m3! + !SUM_fill_m3!,2)','PYTHON3', None)
                arcpy.management.CalculateField(CutFill_Total, 'Total_Volume', 'round(!SUM_fill_m3! - !SUM_cut_m3!,2)','PYTHON3', None)
                arcpy.management.CalculateField(CutFill_Total, 'cut_fill_ratio','round(abs(!SUM_cut_m3!) / !SUM_fill_m3!,2)', 'PYTHON3', None)

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
        
        return