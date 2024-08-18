########################################################################################################
"""DIRECTIONAL SLOPE EXCLUSION ANALYSIS 

Description: Creates exclusion areas based on directional slope limitations

Revision log
0.0.1 - 9/29/2021 - Rebuilt, updated to match KN coding standards
0.0.2 - 2/11/2022 - Updated algorithm, added capability for degrees and percent, feet and meters
0.0.3 - 4/1/2022 - Updated parameters for specific outputs to be more clear
1.0.0 - 8/5/2022 - Added automatic symbology
1.0.1 - 8/31/2022 - Added validation, separated out east/west and south limits, updated units for meters
2.0.0 - 12/15/2023 - 2.0 version created by MG; hard & soft exclusion zones added
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2024, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "2.0.0"
__license__     = "Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import math
from arcpy.sa import *
import os.path
import sys

class SlopeExclusion_v2(object):
    def __init__(self):
        self.label = "Directional Slope Exclusion Analysis"
        self.description = "Analyzes the slope of a surface in terms of mechanical & production exclusion zones"
        self.canRunInBackground = False
        self.category = "Site Suitability\Terrain Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input elevation raster",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Foot", "Meter"]

        param2 = arcpy.Parameter(
            displayName="Solar array configuration",
            name="array_config",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Single axis tracker", "Fixed tilt", "Custom dimensions"]

        param3 = arcpy.Parameter(
            displayName="Custom row dimension north-south",
            name="rowNS",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Slope output measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["Percent", "Degrees"]

        param5 = arcpy.Parameter(
            displayName="Production (North-facing) soft slope limit",
            name="prodLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Production (North-facing) hard slope limit",
            name="prodLimitHard",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="East/west slope structural/mechanical/civil limit",
            name="mechEWLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="North/south slope structural/mechanical/civil limit",
            name="mechNSLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Structural/mechanical/civil limit hard slope limit",
            name="mechLimit_hard",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param10 = arcpy.Parameter(
            displayName="Production soft exclusion output feature class",
            name="prodSoftOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param11 = arcpy.Parameter(
            displayName="Production hard exclusion output feature class",
            name="prodHardOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param12 = arcpy.Parameter(
            displayName="Mechanical soft exclusion output feature class",
            name="mechSoftOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param13 = arcpy.Parameter(
            displayName="Mechanical hard exclusion output feature class",
            name="mechHardOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[1].altered:
            parameters[1].value = "Foot"

        if parameters[2].value == "Single axis tracker" or parameters[2].value == "Fixed tilt":
            parameters[3].enabled = False
        if parameters[2].value == "Custom dimensions":
            parameters[3].enabled = True
        else:
            parameters[3].enabled = False

        if not parameters[3].altered:
            parameters[3].value = "300"

        if not parameters[4].altered:
            parameters[4].value = "Percent"

        if not parameters[5].altered:
            parameters[5].value = "5"

        if not parameters[6].altered:
            parameters[6].value = "8"

        if not parameters[7].altered:
            parameters[7].value = "15"

        if not parameters[8].altered:
            parameters[8].value = "15"

        if not parameters[9].altered:
            parameters[9].value = "20"

        if not parameters[10].altered:
            parameters[10].value = "prod_soft_exclusion"

        if not parameters[11].altered:
            parameters[11].value = "prod_hard_exclusion"

        if not parameters[12].altered:
            parameters[12].value = "mech_soft_exclusion"

        if not parameters[13].altered:
            parameters[13].value = "mech_hard_exclusion"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            if parameters[1].value == "Foot":
                if "Foot" not in arcpy.Describe(parameters[0].value).spatialReference.linearUnitName:
                    parameters[1].setErrorMessage("Vertical and horizontal units do not match")
            if parameters[1].value == "Meter":
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
        demInput        = parameters[0].valueAsText  
        xyzUnit         = parameters[1].valueAsText  
        array_config    = parameters[2].valueAsText
        rowNScustom     = parameters[3].valueAsText  
        slopeUnits      = parameters[4].valueAsText  
        prodLimit       = parameters[5].valueAsText  
        prodLimitHard   = parameters[6].valueAsText  
        mechEWLimit     = parameters[7].valueAsText  
        mechNSLimit     = parameters[8].valueAsText  
        mechLimit_hard  = parameters[9].valueAsText  
        prodSoftOutput  = parameters[10].valueAsText  
        prodHardOutput  = parameters[11].valueAsText  
        mechSoftOutput  = parameters[12].valueAsText  
        mechHardOutput  = parameters[13].valueAsText  
        
        # Set snap to demInput raster
        arcpy.env.snapRaster = demInput

        arcpy.SetProgressor("default", "Analyzing the directional slope...")

        if array_config == "Single axis tracker":
            if xyzUnit == "Foot":
                rowNS = 300
                rowEW = 10
            else:
                rowNS = 125
                rowEW = 3

        if array_config == "Fixed tilt":
            if xyzUnit == "Foot":
                rowNS = 14
                rowEW = 200
            else:
                rowNS = 4
                rowEW = 60
        if array_config == "Custom dimensions":
            rowNS = float(rowNScustom)
            if xyzUnit == "Foot":
                rowEW = 10
            else:
                rowEW = 3

        # Run focal statistics to get rid of small areas
        # Cut the row length in half and multiply the row width by 2
        if rowNS > rowEW:
            lengthResRow = str(round(rowNS, 0)/2)
            lengthResHigh = rowEW * 1.5
            widthRes = rowEW * 1.5
        else:
            widthRes = str(round(rowEW/2, 0))
            lengthResRow = rowNS * 1.5
            lengthResHigh = rowNS * 1.5

        focalInputRow = ("Rectangle " + str(widthRes) + " " + str(lengthResRow) + " MAP")
        demFocalRow = arcpy.sa.FocalStatistics(demInput, focalInputRow, "MEAN", "DATA", 90)

        focalInputHigh = ("Rectangle " + str(widthRes) + " " + str(lengthResHigh) + " MAP")
        demFocalHigh = arcpy.sa.FocalStatistics(demInput, focalInputHigh, "MEAN", "DATA", 90)

        arcpy.SetProgressor("default", "Analyzing the terrain based on the row length...")

        AspectRow = arcpy.sa.SurfaceParameters(
            in_raster=demFocalRow,
            parameter_type="ASPECT",
            local_surface_type="QUADRATIC",
            use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
            z_unit=xyzUnit,
        )

        AspectRad_row = AspectRow * math.pi / 180

        # Process slope in radians
        SlopeRow = arcpy.sa.SurfaceParameters(
            in_raster=demFocalRow,
            parameter_type="SLOPE",
            local_surface_type="QUADRATIC",
            use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
            z_unit=xyzUnit,
            output_slope_measurement="DEGREE",
        )
        
        SlopeRad_row = SlopeRow * math.pi / 180

        AspectHigh = arcpy.sa.SurfaceParameters(
            in_raster=demFocalHigh,
            parameter_type="ASPECT",
            local_surface_type="QUADRATIC",
            use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
            z_unit=xyzUnit,
        )

        AspectRad_high = AspectHigh * math.pi / 180

        # Process slope in radians
        SlopeHigh = arcpy.sa.SurfaceParameters(
            in_raster=demFocalHigh,
            parameter_type="SLOPE",
            local_surface_type="QUADRATIC",
            use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
            z_unit=xyzUnit,
            output_slope_measurement="DEGREE",
        )
        
        SlopeRad_high = SlopeHigh * math.pi / 180

        if slopeUnits == "Percent":
            ewSlope_row = Tan(Sin(AspectRad_row) * SlopeRad_row) * 100
            nsSlope_row = Tan(Cos(AspectRad_row) * SlopeRad_row) * 100
            ewSlope_high = Tan(Sin(AspectRad_high) * SlopeRad_high) * 100
            nsSlope_high = Tan(Cos(AspectRad_high) * SlopeRad_high) * 100
        if slopeUnits == "Degrees":
            ewSlope_row = Sin(AspectRad_row) * SlopeRad_row * 180 / math.pi
            nsSlope_row = Cos(AspectRad_row) * SlopeRad_row * 180 / math.pi
            ewSlope_high = Sin(AspectRad_high) * SlopeRad_high * 180 / math.pi
            nsSlope_high = Cos(AspectRad_high) * SlopeRad_high * 180 / math.pi


        arcpy.SetProgressor("default", "Determining slopes that exceed the specified tolerances...")

        # Set null values outside the limits
        prod_row_where = "VALUE < " + prodLimit
        prod_high_where = "VALUE < " + prodLimitHard
        mechEW_row_where = "VALUE > -" + mechEWLimit + " And VALUE < " + mechEWLimit
        mechNS_row_where = "VALUE > -" + mechNSLimit + " And VALUE < " + mechNSLimit
        mech_high_where = "VALUE > -" + mechLimit_hard + " And VALUE < " + mechLimit_hard

        nsSlope_prod_row_pre = arcpy.sa.SetNull(
            in_conditional_raster=nsSlope_row,
            in_false_raster_or_constant=1,
            where_clause=prod_row_where
        )

        nsSlope_prod_high_pre = arcpy.sa.SetNull(
            in_conditional_raster=nsSlope_high,
            in_false_raster_or_constant=2,
            where_clause=prod_high_where
        )
        
        ewSlope_mech_row_pre = arcpy.sa.SetNull(
            in_conditional_raster=ewSlope_row,
            in_false_raster_or_constant=1,
            where_clause=mechEW_row_where
        )
        
        nsSlope_mech_row_pre = arcpy.sa.SetNull(
            in_conditional_raster=nsSlope_row,
            in_false_raster_or_constant=1,
            where_clause=mechNS_row_where
        )
        
        ewSlope_mech_high_pre = arcpy.sa.SetNull(
            in_conditional_raster=ewSlope_high,
            in_false_raster_or_constant=2,
            where_clause=mech_high_where
        )
        
        nsSlope_mech_high_pre = arcpy.sa.SetNull(
            in_conditional_raster=nsSlope_high,
            in_false_raster_or_constant=2,
            where_clause=mech_high_where
        )
        
        arcpy.SetProgressor("default", "Refining the exclusion areas...")

        # Convert to polygons
        prodNS_row_poly = arcpy.conversion.RasterToPolygon(nsSlope_prod_row_pre, r"in_memory\prodNS_row_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        prodNS_high_poly = arcpy.conversion.RasterToPolygon(nsSlope_prod_high_pre, r"in_memory\prodNS_high_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        mechEW_row_poly = arcpy.conversion.RasterToPolygon(ewSlope_mech_row_pre, r"in_memory\mechEW_row_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        mechNS_row_poly = arcpy.conversion.RasterToPolygon(nsSlope_mech_row_pre, r"in_memory\mechNS_row_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        mechEW_high_poly = arcpy.conversion.RasterToPolygon(ewSlope_mech_high_pre, r"in_memory\mechEW_high_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)
        mechNS_high_poly = arcpy.conversion.RasterToPolygon(nsSlope_mech_high_pre, r"in_memory\mechNS_high_poly", "SIMPLIFY", "Value","SINGLE_OUTER_PART", None)

        mech_row_poly = arcpy.management.Merge([[mechEW_row_poly], [mechNS_row_poly]], r"in_memory\mech_row_poly")
        mech_high_poly = arcpy.management.Merge([[mechEW_high_poly], [mechNS_high_poly]], r"in_memory\mech_high_poly")

        # Aggregate within 25 feet and minimum areas and holes of 5000 sq ft
        prod_row_agg = arcpy.cartography.AggregatePolygons(prodNS_row_poly, r"in_memory\prod_row_agg", "25 Feet", "5000 SquareFeet","5000 SquareFeet")
        prod_high_agg = arcpy.cartography.AggregatePolygons(prodNS_high_poly, r"in_memory\prod_high_agg", "25 Feet", "5000 SquareFeet","5000 SquareFeet")
        mech_row_agg = arcpy.cartography.AggregatePolygons(mech_row_poly, r"in_memory\mech_row_agg", "25 Feet", "5000 SquareFeet","5000 SquareFeet")
        mech_high_agg = arcpy.cartography.AggregatePolygons(mech_high_poly, r"in_memory\mech_high_agg", "25 Feet", "5000 SquareFeet","5000 SquareFeet")

        # Buffer out by 35 ft to merge close areas
        bufferOut = str(25) + " " + xyzUnit
        prodRow_BufferOut = arcpy.analysis.PairwiseBuffer(prod_row_agg, r"in_memory\prodRow_BufferOut", bufferOut, "ALL")
        prodHigh_BufferOut = arcpy.analysis.PairwiseBuffer(prod_high_agg, r"in_memory\prodHigh_BufferOut", bufferOut, "ALL")
        mechRow_BufferOut = arcpy.analysis.PairwiseBuffer(mech_row_agg, r"in_memory\mechRow_BufferOut", bufferOut, "ALL")
        mechHigh_BufferOut = arcpy.analysis.PairwiseBuffer(mech_high_agg, r"in_memory\mechHigh_BufferOut", bufferOut, "ALL")

        # Buffer to get rid of small areas
        bufferIn = str(-35) + " " + xyzUnit
        prodRow_BufferIn = arcpy.analysis.PairwiseBuffer(prodRow_BufferOut, r"in_memory\prodRow_BufferIn", bufferIn, "ALL")
        prodHigh_BufferIn = arcpy.analysis.PairwiseBuffer(prodHigh_BufferOut, r"in_memory\prodHigh_BufferIn", bufferIn, "ALL")
        mechRow_BufferIn = arcpy.analysis.PairwiseBuffer(mechRow_BufferOut, r"in_memory\mechRow_BufferIn", bufferIn, "ALL")
        mechHigh_BufferIn = arcpy.analysis.PairwiseBuffer(mechHigh_BufferOut, r"in_memory\mechHigh_BufferIn", bufferIn, "ALL")

        # Buffer out high slope case to get to original bounds, row case to get to 5 ft before original bounds
        bufferRow = str(5) + " " + xyzUnit
        bufferHigh = str(10) + " " + xyzUnit
        prodRow_PreFinal = arcpy.analysis.PairwiseBuffer(prodRow_BufferIn, r"in_memory\prodRow_PreFinal", bufferRow, "ALL")
        prodHigh_Final = arcpy.analysis.PairwiseBuffer(prodHigh_BufferIn, prodHardOutput, bufferHigh, "ALL")
        mechRow_PreFinal = arcpy.analysis.PairwiseBuffer(mechRow_BufferIn, r"in_memory\mechRow_PreFinal", bufferRow, "ALL")
        mechHigh_Final = arcpy.analysis.PairwiseBuffer(mechHigh_BufferIn, mechHardOutput, bufferHigh, "ALL")

        # Merge and dissolve the row and high cases
        prodRow_merge = arcpy.management.Merge([[prodRow_PreFinal], [prodHigh_Final]], r"in_memory\prodRow_merge")
        mechRow_merge = arcpy.management.Merge([[mechRow_PreFinal], [mechHigh_Final]], r"in_memory\mechRow_merge")

        prodRow_merge_dis = arcpy.analysis.PairwiseDissolve(prodRow_merge,r"in_memory\prodRow_merge_dis")
        mechRow_merge_dis = arcpy.analysis.PairwiseDissolve(mechRow_merge,r"in_memory\mechRow_merge_dis")

        # Buffer out by 5 feet to get final bounds
        prodRow_Final_prescreen = arcpy.analysis.PairwiseBuffer(prodRow_merge_dis, r"in_memory\prodRow_Final_prescreen", bufferRow, "ALL")
        mechRow_Final_prescreen = arcpy.analysis.PairwiseBuffer(mechRow_merge_dis, r"in_memory\mechRow_Final_prescreen", bufferRow, "ALL")

        # Split up areas that may have been combined
        prodPreFinal_split = arcpy.management.MultipartToSinglepart(prodRow_Final_prescreen, "prodPreFinal_split")
        mechPreFinal_split = arcpy.management.MultipartToSinglepart(mechRow_Final_prescreen, "mechPreFinal_split")

        # Get rid of areas smaller than 5000 square feet or 465 meters
        if xyzUnit == "Foot":
            areaMax = "Shape_Area > 5000"
        if xyzUnit == "Meter":
            areaMax = "Shape_Area > 465"
        prodRow_Final = arcpy.analysis.Select(prodPreFinal_split, prodSoftOutput, areaMax)
        mechRow_Final = arcpy.analysis.Select(mechPreFinal_split, mechSoftOutput, areaMax)

        # Create fields designating hard or soft boundaries
        arcpy.management.CalculateField(prodRow_Final, "exclusionType", "'soft'", "PYTHON3", None, "TEXT")
        arcpy.management.CalculateField(prodRow_Final, "north_slopeLimit", ""+prodLimit+" ", "PYTHON3", None, "FLOAT")

        arcpy.management.CalculateField(prodHigh_Final, "exclusionType", "'hard'", "PYTHON3", None, "TEXT")
        arcpy.management.CalculateField(prodHigh_Final, "north_slopeLimit", ""+prodLimitHard+" ", "PYTHON3", None, "FLOAT")
        
        arcpy.management.CalculateField(mechRow_Final, "exclusionType", "'soft'", "PYTHON3", None, "TEXT")
        arcpy.management.CalculateField(mechRow_Final, "eastWest_slopeLimit", ""+mechEWLimit+" ", "PYTHON3", None, "FLOAT")
        arcpy.management.CalculateField(mechRow_Final, "northSouth_slopeLimit", ""+mechNSLimit+" ", "PYTHON3", None, "FLOAT")

        arcpy.management.CalculateField(mechHigh_Final, "exclusionType", "'hard'", "PYTHON3", None, "TEXT")
        arcpy.management.CalculateField(mechHigh_Final, "northEastSouthWest_slopeLimit", ""+mechLimit_hard+" ", "PYTHON3", None, "FLOAT")

        if slopeUnits == "Percent":
            arcpy.management.CalculateField(prodRow_Final, "slopeUnits", "'Percent'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(prodHigh_Final, "slopeUnits", "'Percent'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(mechRow_Final, "slopeUnits", "'Percent'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(mechHigh_Final, "slopeUnits", "'Percent'", "PYTHON3", None, "TEXT")
        if slopeUnits == "Degrees":
            arcpy.management.CalculateField(prodRow_Final, "slopeUnits", "'Degrees'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(prodHigh_Final, "slopeUnits", "'Degrees'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(mechRow_Final, "slopeUnits", "'Degrees'", "PYTHON3", None, "TEXT")
            arcpy.management.CalculateField(mechHigh_Final, "slopeUnits", "'Degrees'", "PYTHON3", None, "TEXT")
            
        # Clean up
        arcpy.management.Delete("mechPreFinal_split")
        arcpy.management.Delete("prodPreFinal_split")

        aprxMap.addDataFromPath(mechRow_Final)
        aprxMap.addDataFromPath(mechHigh_Final)
        aprxMap.addDataFromPath(prodRow_Final)
        aprxMap.addDataFromPath(prodHigh_Final)

        prodSoftName = os.path.basename(prodSoftOutput)
        prodHardName = os.path.basename(prodHardOutput)
        mechSoftName = os.path.basename(mechSoftOutput)
        mechHardName = os.path.basename(mechHardOutput)


        # Apply symbology
        prodSoftLyr = aprxMap.listLayers(prodSoftName)[0]
        prodSoftSym = prodSoftLyr.symbology
        prodSoftSym.renderer.symbol.color = {"RGB": [169, 0, 230, 65]}
        prodSoftSym.renderer.label = "Production (North) Slope Soft Exclusions" 
        prodSoftLyr.symbology = prodSoftSym

        prodHardLyr = aprxMap.listLayers(prodHardName)[0]
        prodHardSym = prodHardLyr.symbology
        prodHardSym.renderer.symbol.applySymbolFromGallery("10% Simple hatch")
        prodHardSym.renderer.symbol.angle = 45
        prodHardSym.renderer.symbol.color = {"RGB": [0, 0, 0, 100]}
        prodHardSym.renderer.symbol.outlineColor = {"RGB": [0, 0, 0, 100]}
        prodHardSym.renderer.symbol.outlineWidth = 1
        prodHardSym.renderer.label = "Production (North) Slope Hard Exclusions"
        prodHardLyr.symbology = prodHardSym

        mechSoftLyr = aprxMap.listLayers(mechSoftName)[0]
        mechSoftSym = mechSoftLyr.symbology
        mechSoftSym.renderer.symbol.color = {"RGB": [255, 255, 0, 65]}
        mechSoftSym.renderer.label = "Mechanical Slope Soft Exclusions"
        mechSoftLyr.symbology = mechSoftSym

        mechHardLyr = aprxMap.listLayers(mechHardName)[0]
        mechHardSym = mechHardLyr.symbology
        mechHardSym.renderer.symbol.applySymbolFromGallery("10% Simple hatch")
        mechHardSym.renderer.symbol.angle = 135
        mechHardSym.renderer.symbol.color = {"RGB": [255, 0, 0, 100]}
        mechHardSym.renderer.symbol.outlineColor = {"RGB": [255, 0, 0, 100]}
        mechHardSym.renderer.symbol.outlineWidth = 1
        mechHardSym.renderer.label = "Mechanical Slope Hard Exclusions"
        mechHardLyr.symbology = mechHardSym

        # arcpy.ResetProgressor()

        return