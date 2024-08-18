########################################################################
"""MASS GRADING ASSESSMENT 

Revision log
0.0.1 - 09/01/2022 - Initial build
1.0.0 - 09/12/2022 - Fixed calculation errors
1.1.0 - 12/20/2022 - Updated to calculate using directional rasters
1.2.0 - 01/29/2024 - Updated syntx of focal stat. ln 175
"""

__author__      = ["Liza Flowers", "Matthew Gagne", "Zane Nordquist", "John Williamson"]
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.2.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Liza Flowers", "Zane Nordquist"]
__status__      = "Demployed"

# Load modules
import math
import arcpy
from arcpy.sa import *
import os
import sys

class MassGradev2(object):

    def __init__(self):
        self.label = "Mass Grading Assessment"
        self.description = "Creates a heat map of the volume and cost of grading based on the directional slope of a surface"
        self.alias = "MassGrade_v2"
        self.canRunInBackground = False
        self.category = "Site Suitability\Civil Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input elevation raster",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Foot", "Meter"]

        param2 = arcpy.Parameter(
            displayName="Slope output units",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Percent", "Degrees"]

        param3 = arcpy.Parameter(
            displayName="Slope limit",
            name="maxSlope",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Output grading volume raster",
            name="outputVolume",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param5 = arcpy.Parameter(
            displayName="Output grading cost layer?",
            name="costOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param5.value = False

        param6 = arcpy.Parameter(
            displayName="Cost of grading per cubic yard or cubic meter (optional)",
            name="gradePrice",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Output grading cost raster (optional)",
            name="outputCost",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[1].altered:
            parameters[1].value = 'Foot'

        if not parameters[4].altered:
            parameters[4].value = 'gradeVolume'

        if parameters[5].value == True:
            parameters[6].enabled = True
            parameters[7].enabled = True
        else:
            parameters[6].enabled = False
            parameters[7].enabled = False

        if not parameters[6].altered:
            parameters[6].value = '10'

        if not parameters[7].altered:
            parameters[7].value = 'gradeCost'

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
        workspace = arcpy.env.workspace

        # Set parameters
        demInput = parameters[0].valueAsText  # Input elevation model - raster
        xyzUnit = parameters[1].valueAsText  # Foot or Meter
        slopeUnits = parameters[2].valueAsText  # Maximum slope target
        maxSlope = parameters[3].valueAsText  # Maximum slope target
        outputVolume = parameters[4].valueAsText  # Output cost of grading raster
        costOption = parameters[5].value  # Cost of grading per cubic yard or cubic meter (optional)
        gradePrice = parameters[6].valueAsText  # Cost of grading per cubic yard or cubic meter (optional)
        outputCost = parameters[7].valueAsText  # Output cost of grading raster (optional)
        
        # Set raster environments
        arcpy.env.snapRaster = demInput
        gridRes = arcpy.Describe(demInput).meanCellWidth
        gridResSQ = gridRes ** 2
        spatialRef = arcpy.Describe(demInput).spatialReference

        # Run focal statistics of a 100 ft circle using range to determine the height range directionally
        if xyzUnit == "Foot":
            focalNSInput = NbrRectangle(30, 100, "MAP")
            focalEWInput = NbrRectangle(100, 30, "MAP")
            cubicConversion = (1 / 27)
            areaConversion = 43560
        else:
            focalNSInput = NbrRectangle(10, 30, "MAP")
            focalEWInput = NbrRectangle(30, 10, "MAP")
            cubicConversion = 1
            areaConversion = 10000

        arcpy.SetProgressor('default', 'Determining slopes over the limit...')

        demFocalNS = arcpy.sa.FocalStatistics(demInput, focalNSInput, "RANGE", "DATA", 90)
        demFocalEW = arcpy.sa.FocalStatistics(demInput, focalEWInput, "RANGE", "DATA", 90)
        heightRangeNS = demFocalNS / 2
        heightRangeEW = demFocalEW / 2

        # Calculate the directional slopes of the surface
        if slopeUnits == "Degrees":
            target_slope = tan(math.pi * float(maxSlope) / 180)
        else:
            target_slope = float(maxSlope)

        AspectDeg = arcpy.sa.Aspect(demInput, "PLANAR", xyzUnit)
        AspectRad = AspectDeg * math.pi / 180

        SlopeDeg = arcpy.sa.Slope(demInput, "DEGREE", "1", "PLANAR", xyzUnit)
        SlopeRad = SlopeDeg * math.pi / 180

        CosAspRad = arcpy.sa.Cos(AspectRad)
        nsRad = CosAspRad * SlopeRad
        if slopeUnits == "Degrees":
            nsSlope = nsRad * 180 / math.pi
        if slopeUnits == "Percent":
            nsSlope = arcpy.sa.Tan(nsRad) * 100

        SinAspRad = arcpy.sa.Sin(AspectRad)
        ewRad = SinAspRad * SlopeRad
        if slopeUnits == "Degrees":
            ewSlope = abs(ewRad * 180 / math.pi)
        if slopeUnits == "Percent":
            ewSlope = abs(arcpy.sa.Tan(ewRad) * 100)

        arcpy.SetProgressor('default', 'Calculating the estimated volume...')

        # Find the volume directionally
        volCellPreNS = areaConversion * (heightRangeNS * gridResSQ) * (abs(nsSlope) / target_slope - 1) * cubicConversion
        volCellPreEW = areaConversion * (heightRangeEW * gridResSQ) * (abs(ewSlope) / target_slope - 1) * cubicConversion

        volCellPosNS = arcpy.sa.SetNull(volCellPreNS, volCellPreNS, "VALUE < 0")
        volCellPosEW = arcpy.sa.SetNull(volCellPreEW, volCellPreEW, "VALUE < 0")

        volNSsquare = arcpy.sa.Square(volCellPosNS)
        volEWsquare = arcpy.sa.Square(volCellPosEW)
        volSum = arcpy.sa.Plus(volNSsquare,volEWsquare)
        volCombined = arcpy.sa.SquareRoot(volSum)

        volCellPre = arcpy.management.MosaicToNewRaster([[volCellPosNS],[volCellPosEW],[volCombined]], workspace, "volCellPre",spatialRef,"32_BIT_FLOAT",gridRes,1,"LAST","FIRST")

        volCell = arcpy.sa.Divide(volCellPre, gridResSQ)

        volCell.save(outputVolume)
        aprxMap.addDataFromPath(outputVolume)

        # Apply symbology
        volName = os.path.basename(outputVolume)
        for l in aprxMap.listLayers():
            if l.isRasterLayer:
                if l.name == volName:
                    symVol = l.symbology
                    symVol.colorizer.stretchType = "StandardDeviation"
                    cr = aprx.listColorRamps("Heat Map 1")[0]
                    symVol.colorizer.colorRamp = cr

                    if xyzUnit == "Foot":
                        symVol.colorizer.minLabel = symVol.colorizer.minLabel + " y^3/acre"
                        symVol.colorizer.maxLabel = symVol.colorizer.maxLabel + " y^3/acre"
                    else:
                        symVol.colorizer.minLabel = symVol.colorizer.minLabel + " m^3/hectare"
                        symVol.colorizer.maxLabel = symVol.colorizer.maxLabel + " m^3/hectare"
                        
                    l.symbology = symVol

        if costOption == True:
            arcpy.SetProgressor('default', 'Calculating the estimated grading cost...')

            costArea = float(gradePrice) * volCell
            costArea.save(outputCost)
            aprxMap.addDataFromPath(outputCost)

            # Apply symbology
            costName = os.path.basename(outputCost)
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    if l.name == costName:
                        symCost = l.symbology
                        symCost.colorizer.stretchType = "StandardDeviation"
                        cr = aprx.listColorRamps("Precipitation")[0]
                        symCost.colorizer.colorRamp = cr
                        symCost.colorizer.invertColorRamp = True

                        if xyzUnit == "Foot":
                            symCost.colorizer.minLabel = symCost.colorizer.minLabel + " $/acre"
                            symCost.colorizer.maxLabel = symCost.colorizer.maxLabel + " $/acre"
                        else:
                            symCost.colorizer.minLabel = symCost.colorizer.minLabel + " $/hectare"
                            symCost.colorizer.maxLabel = symCost.colorizer.maxLabel + " $/hectare"
                            
                        l.symbology = symCost

        arcpy.management.Delete("volCellPre")

        arcpy.ResetProgressor()

        return
