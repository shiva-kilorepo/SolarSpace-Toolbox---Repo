########################################################################################################
"""MASS GRADING COST ANALYSIS 

Description: Estimates the cost of grading based on slope and terrain variation for a surface

Revision log
0.0.1 - 09/01/2022 - Initial build
1.0.0 - 09/12/2022 - Fixed calculation errors
"""

__author__      = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__copyright__   = "Copyright 2022, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.2"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import math
import arcpy
from arcpy.sa import *
import os
import sys

class MassGrade(object):

    def __init__(self):
        self.label = "Mass Grading Cost Analysis v1 - Outdated"
        self.description = "Estimates the cost of grading based on slope and terrain variation for a surface"
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
        aprx = arcpy.mp.ArcGISProject('CURRENT')
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

        # Set snap to demInput raster
        arcpy.env.snapRaster = demInput
        gridRes = arcpy.Describe(demInput).meanCellWidth
        gridResSQ = gridRes ** 2

        # Run focal statistics of a 100 ft circle using range
        if xyzUnit == "Foot":
            focalInput = "Circle 100 MAP"
            cubicConversion = (1 / 27)
            areaConversion = 43560
        else:
            focalInput = "Circle 30 MAP"
            cubicConversion = 1
            areaConversion = 10000

        demFocal = arcpy.sa.FocalStatistics(demInput, focalInput, "RANGE", "DATA", 90)
        heightRange = demFocal / 2

        # Calculate the slope of the existing surface
        if slopeUnits == "Degrees":
            target_slope = tan(math.pi * float(maxSlope) / 180)
        else:
            target_slope = float(maxSlope)

        # Take the directional slope of the dem
        demSlope = arcpy.sa.Slope(demInput, "PERCENT_RISE", 1, "PLANAR", xyzUnit)

        volCellPre = areaConversion * (heightRange * gridResSQ) * ((demSlope) / target_slope - 1) * cubicConversion

        volCell = arcpy.sa.SetNull(volCellPre, volCellPre, "VALUE < 0") / gridResSQ

        volCell.save(outputVolume)
        aprxMap.addDataFromPath(outputVolume)

        # Apply symbology
        volName = os.path.basename(outputVolume)
        for l in aprxMap.listLayers():
            if l.isRasterLayer:
                if l.name == volName:
                    symVol = l.symbology
                    symVol.colorizer.stretchType = "StandardDeviation"
                    cr = aprx.listColorRamps('Heat Map 1')[0]
                    symVol.colorizer.colorRamp = cr

                    if xyzUnit == "Foot":
                        l.description = "y^3/acre"
                    else:
                        l.description = "m^3/hectare"

                    l.symbology = symVol

        if costOption == True:
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
                        cr = aprx.listColorRamps('Precipitation')[0]
                        symCost.colorizer.colorRamp = cr
                        symCost.colorizer.invertColorRamp = True

                        if xyzUnit == "Foot":
                            l.description = "$/acre"
                        else:
                            l.description = "$/hectare"

                        l.symbology = symCost

        return
