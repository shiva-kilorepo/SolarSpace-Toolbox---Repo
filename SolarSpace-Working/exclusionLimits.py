########################################################################
"""CREATE EXCLUSIONS FROM RASTERS USING LIMITS

Revision log
0.0.1 - 12/15/2022 - Initial scripting
1.0.0 - 1/2/2023 - Added more robust inputs/options
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

class ExclusionLimits(object):
    def __init__(self):
        self.label = "Create Exclusions from Raster Using Limits"
        self.description = "Creates exclusion areas based on prescribed limits"
        self.canRunInBackground = False
        self.category = "kNz Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input raster dataset",
            name="rasterInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Exclude values...",
            name="valueOption",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Greater than", "Less than", "Greater and less than", "Greater or less than"]

        param2 = arcpy.Parameter(
            displayName="Exclude values greater than:",
            name="greaterThan",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Exclude values less than:",
            name="lessThan",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Upper limit:",
            name="upperLimit",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Lower limit",
            name="lowerLimit",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Output exclusion feature class",
            name="exclusionOut",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[1].value == "Greater than" or parameters[1].value == "Greater and less than":
            parameters[3].value = 0

        if parameters[1].value == "Less than" or parameters[1].value == "Greater and less than":
            parameters[2].value = 0

        if parameters[1].value == "Less than" or parameters[1].value == "Greater than" or parameters[1].value == "Greater or less than":
            parameters[4].value = 0
            parameters[5].value = 0

        if parameters[1].value == "Greater than" or parameters[1].value == "Greater or less than":
            parameters[2].enabled = True
        else:
            parameters[2].enabled = False

        if parameters[1].value == "Less than" or parameters[1].value == "Greater or less than":
            parameters[3].enabled = True
        else:
            parameters[3].enabled = False

        if parameters[1].value == "Greater and less than":
            parameters[4].enabled = True
            parameters[5].enabled = True
        else:
            parameters[4].enabled = False
            parameters[5].enabled = False

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):

        # Load modules
        import arcpy
        import os.path
        import sys
        
        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        rasterInput = parameters[0].valueAsText  # Raster input data
        valueOption = parameters[1].valueAsText  # Option for greater than, less than, or both
        greaterThan = parameters[2].valueAsText  # Exclude values greater than 
        lessThan = parameters[3].valueAsText # Exclude values less than 
        upperLimit = parameters[4].valueAsText # Upper limit for and
        lowerLimit = parameters[5].valueAsText # Lower limit for and
        exclusionOut = parameters[6].valueAsText

        arcpy.SetProgressor("default", "Determining values that exceed the input limits...")

        # Reclassify the input raster
        rasterMax = arcpy.management.GetRasterProperties(rasterInput, "MAXIMUM")
        rasterMin = arcpy.management.GetRasterProperties(rasterInput, "MINIMUM")

        if valueOption == "Less than":
            limitDef = str(rasterMin) + " " + lessThan + " 1; " + lessThan + " " + str(rasterMax) + " NODATA" 
        if valueOption == "Greater than":
            limitDef = str(rasterMin) + " " + greaterThan + " NODATA; " + greaterThan + " " + str(rasterMax) + " 2" 
        if valueOption == "Greater or less than":
            limitDef = str(rasterMin) + " " + lessThan + " 1; " + lessThan + " " + greaterThan + " NODATA; " + greaterThan + " " + str(rasterMax) + " 2" 
        if valueOption == "Greater and less than":
            limitDef = str(rasterMin) + " " + lowerLimit + " NODATA; " + lowerLimit + " " + upperLimit + " 1; " + upperLimit + " " + str(rasterMax) + " NODATA" 

        rasterReclass = arcpy.sa.Reclassify(rasterInput, "VALUE", limitDef, "DATA")

        arcpy.SetProgressor("default", "Creating the exclusion areas...")

        # Convert to polygon
        exclusionFC = arcpy.conversion.RasterToPolygon(rasterReclass, exclusionOut, "SIMPLIFY", "Value", "MULTIPLE_OUTER_PART")

        aprxMap.addDataFromPath(exclusionFC)

        # exclusionName = os.path.basename(exclusionOut)

        # exclusionLyr = aprxMap.listLayers(exclusionName)[0]
        # exclusionSym = exclusionLyr.symbology
        # exclusionSym.updateRenderer('UniqueValueRenderer')
        # exclusionSym.renderer.fields = ['Value']
        # for grp in exclusionSym.renderer.groups:
            # for itm in grp.items:
                # lyrValue = itm.values[0][0]
                # if lyrValue == "1":
                    # itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    # itm.symbol.color = {'RGB': [27, 158, 119, 50]}
                    # itm.symbol.outlineColor = {'RGB': [0, 115, 76, 75]}
                    # itm.symbol.outlineWidth = 1
                # if lyrValue == "2":
                    # itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    # itm.symbol.color = {'RGB': [217, 95, 2, 50]}
                    # itm.symbol.outlineColor = {'RGB': [115, 38, 0, 75]}
                    # itm.symbol.outlineWidth = 1
        # exclusionLyr.symbology = exclusionSym

        arcpy.ResetProgressor()

        return

