########################################################################################################
"""DIRECTIONAL SLOPE EXCLUSION ANALYSIS 

Description: Creates exclusion areas based on directional slope limitations

Revision log
0.0.1 - 9/29/2021 - Rebuilt, updated to match KN coding standards
0.0.2 - 2/11/2022 - Updated algorithm, added capability for degrees and percent, feet and meters
0.0.3 - 4/1/2022 - Updated parameters for specific outputs to be more clear
1.0.0 - 8/5/2022 - Added automatic symbology
1.0.1 - 8/31/2022 - Added validation, separated out east/west and south limits, updated units for meters
"""
__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2022, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import math
from arcpy.sa import *
import os.path
import sys

class SlopeExclusion(object):
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
            displayName="Custom row dimension east-west",
            name="rowEW",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Slope output measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["Percent", "Degrees"]

        param6 = arcpy.Parameter(
            displayName="Production (North-facing) slope limit",
            name="prodLimit",
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
            displayName="Production exclusion output feature class",
            name="prodOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param10 = arcpy.Parameter(
            displayName="Mechanical exclusion output feature class",
            name="mechOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10]
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
            parameters[4].enabled = False
        if parameters[2].value == "Custom dimensions":
            parameters[3].enabled = True
            parameters[4].enabled = True
        else:
            parameters[3].enabled = False
            parameters[4].enabled = False

        if not parameters[3].altered:
            parameters[3].value = "300"

        if not parameters[4].altered:
            parameters[4].value = "7"

        if not parameters[5].altered:
            parameters[5].value = "Percent"

        if not parameters[6].altered:
            parameters[6].value = "5"

        if not parameters[7].altered:
            parameters[7].value = "15"

        if not parameters[8].altered:
            parameters[8].value = "15"

        if not parameters[9].altered:
            parameters[9].value = "prodLossExclusion"

        if not parameters[10].altered:
            parameters[10].value = "mechExclusion"

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
        demInput = parameters[0].valueAsText  # Input elevation model - raster
        xyzUnit = parameters[1].valueAsText  # Foot or Meter
        array_config = parameters[2].valueAsText
        rowNScustom = parameters[3].valueAsText  # row length or width north-south
        rowEWcustom = parameters[4].valueAsText  # row length or width east-west
        slopeUnits = parameters[5].valueAsText  # Units of slope - percent or degree
        prodLimit = parameters[6].valueAsText  # North slope production loss limit
        mechEWLimit = parameters[7].valueAsText  # East/West slope mechanical limit
        mechNSLimit = parameters[8].valueAsText  # South slope mechanical limit
        prodOutput = parameters[9].valueAsText  # Production output feature class
        mechOutput = parameters[10].valueAsText  # Mechanical output feature class

        # Set snap to demInput raster
        arcpy.env.snapRaster = demInput

        arcpy.SetProgressor("default", "Analyzing the directional slope...")

        if array_config == "Single axis tracker":
            if xyzUnit == "Foot":
                rowNS = 300
                rowEW = 7
            else:
                rowNS = 125
                rowEW = 2

        if array_config == "Fixed tilt":
            if xyzUnit == "Foot":
                rowNS = 14
                rowEW = 200
            else:
                rowNS = 4
                rowEW = 60
        if array_config == "Custom dimensions":
            rowNS = float(rowNScustom)
            rowEW = float(rowEWcustom)

        # Run focal statistics to get rid of small areas
        # Cut the row length in half and multiply the row width by 2
        if rowNS > rowEW:
            lengthRes = str(round(rowNS/2, 0))
            widthRes = rowEW * 2
            rowLength = rowNS
        else:
            widthRes = str(round(rowEW/2, 0))
            lengthRes = rowNS * 2
            rowLength = rowEW

        focalInput = ("Rectangle " + str(lengthRes) + " " + str(widthRes) + " MAP")
        demFocal = arcpy.sa.FocalStatistics(demInput, focalInput, "MEAN", "DATA", 90)

        arcpy.SetProgressor("default", "Analyzing the terrain based on the row size...")

        AspectRad = arcpy.sa.Aspect(demFocal, "PLANAR", xyzUnit) * math.pi / 180

        # Process slope in radians
        SlopeRad = arcpy.sa.Slope(demFocal, "DEGREE", "1", "PLANAR", xyzUnit) * math.pi / 180

        if slopeUnits == "Percent":
            ewSlope = Tan(Sin(AspectRad) * SlopeRad) * 100
            nsSlope = Tan(Cos(AspectRad) * SlopeRad) * 100
        if slopeUnits == "Degrees":
            ewSlope = Sin(AspectRad) * SlopeRad * 180 / math.pi
            nsSlope = Cos(AspectRad) * SlopeRad * 180 / math.pi

        arcpy.SetProgressor("default", "Determining slopes that exceed the production tolerance...")

        # Reclassify
        prodClass = "-2000 " + prodLimit + " NODATA; " + prodLimit + " 2000 1"
        prodReclass = arcpy.sa.Reclassify(nsSlope, "VALUE", prodClass, "DATA")

        arcpy.SetProgressor("default", "Determining slopes that exceed the structural/mechanical/civil tolerance...")

        mechClassEW = "-2000 -" + mechEWLimit + " 1; -" + mechEWLimit + " " + mechEWLimit + " NODATA; " + mechEWLimit + " 2000 1"
        mechReclassEW = arcpy.sa.Reclassify(ewSlope, "VALUE", mechClassEW, "DATA")

        mechClassNS = "-2000 -" + mechNSLimit + " 1; -" + mechNSLimit + " " + mechNSLimit + " NODATA; " + mechNSLimit + " 2000 1"
        mechReclassNS = arcpy.sa.Reclassify(nsSlope, "VALUE", mechClassNS, "DATA")

        arcpy.SetProgressor("default", "Refining the exclusion areas...")

        # Convert to polygon
        prodPoly = arcpy.conversion.RasterToPolygon(prodReclass, r"in_memory\prodPoly", "SIMPLIFY", "Value",
                                                    "SINGLE_OUTER_PART", None)
        nsMechPoly = arcpy.conversion.RasterToPolygon(mechReclassNS, r"in_memory\nsMechPoly", "SIMPLIFY", "Value",
                                                      "SINGLE_OUTER_PART", None)
        ewMechPoly = arcpy.conversion.RasterToPolygon(mechReclassEW, r"in_memory\ewMechPoly", "SIMPLIFY", "Value",
                                                      "SINGLE_OUTER_PART", None)
        mechPoly = arcpy.management.Merge([[ewMechPoly], [nsMechPoly]], r"in_memory\mechPoly")

        # Aggregate within 25 feet and minimum areas and holes of 5000 sq ft
        mechAgg = arcpy.cartography.AggregatePolygons(mechPoly, r"in_memory\mechAgg", "25 Feet", "5000 SquareFeet",
                                                      "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)
        prodAgg = arcpy.cartography.AggregatePolygons(prodPoly, r"in_memory\prodAgg", "25 Feet", "5000 SquareFeet",
                                                      "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)

        # Buffer out by 1/16 of the row length to merge close areas
        bufferOut = str(float(rowLength) / 16) + " " + xyzUnit
        mechBufferOut = arcpy.analysis.Buffer(mechAgg, r"in_memory\mechBufferOut", bufferOut, "FULL", "ROUND", "NONE",
                                              None, "PLANAR")
        prodBufferOut = arcpy.analysis.Buffer(prodAgg, r"in_memory\prodBufferOut", bufferOut, "FULL", "ROUND", "NONE",
                                              None, "PLANAR")

        # Buffer in by 1/8 of the row area to get rid of small areas
        bufferIn = str(float(rowLength) / -8) + " " + xyzUnit
        mechBufferIn = arcpy.analysis.Buffer(mechBufferOut, r"in_memory\mechBufferIn", bufferIn, "FULL", "ROUND",
                                             "NONE", None, "PLANAR")
        prodBufferIn = arcpy.analysis.Buffer(prodBufferOut, r"in_memory\prodBufferIn", bufferIn, "FULL", "ROUND",
                                             "NONE", None, "PLANAR")

        # Buffer out by 1/32 of the row length
        bufferFinal = str(float(rowLength) / 32) + " " + xyzUnit
        mechPreFinal = arcpy.analysis.Buffer(mechBufferIn, r"in_memory\mechPreFinal", bufferFinal, "FULL", "ROUND",
                                             "NONE", None, "PLANAR")
        prodPreFinal = arcpy.analysis.Buffer(prodBufferIn, r"in_memory\prodPreFinal", bufferFinal, "FULL", "ROUND",
                                             "NONE", None, "PLANAR")

        # Split up areas that may have been combined
        mechPreFinal_split = arcpy.management.MultipartToSinglepart(mechPreFinal, "mechPreFinal_split")
        prodPreFinal_split = arcpy.management.MultipartToSinglepart(prodPreFinal, "prodPreFinal_split")

        # Get rid of areas smaller than 5000 square feet or 465 meters
        if xyzUnit == "Foot":
            areaMax = "Shape_Area > 5000"
        if xyzUnit == "Meter":
            areaMax = "Shape_Area > 465"
        mechFinal = arcpy.analysis.Select(mechPreFinal_split, mechOutput, areaMax)
        prodFinal = arcpy.analysis.Select(prodPreFinal_split, prodOutput, areaMax)

        # Clean up
        arcpy.management.Delete("mechPreFinal_split")
        arcpy.management.Delete("prodPreFinal_split")

        aprxMap.addDataFromPath(mechFinal)
        aprxMap.addDataFromPath(prodFinal)

        mechName = os.path.basename(mechOutput)
        prodName = os.path.basename(prodOutput)

        # Apply symbology
        mechLyr = aprxMap.listLayers(mechName)[0]
        mechSym = mechLyr.symbology
        mechSym.renderer.symbol.color = {"RGB": [255, 255, 0, 65]}
        mechSym.renderer.label = "Mechanical Slope Exclusions"
        mechLyr.symbology = mechSym

        prodLyr = aprxMap.listLayers(prodName)[0]
        prodSym = prodLyr.symbology
        prodSym.renderer.symbol.color = {"RGB": [169, 0, 230, 65]}
        prodSym.renderer.label = "Production (North) Slope Exclusions"
        prodLyr.symbology = prodSym

        arcpy.ResetProgressor()

        return