########################################################################
"""DIRECTIONAL SLOPE ANALYSIS 

Calculates the east-west and north-south slopes of an elevation model

Revision log
0.0.1 - 08/30/2021 - Updated the header to the new KiloNewton tamplate.
0.0.2 - 9/29/2021 - Added additional drop down options for outputting radians, percent, or degrees, option to output only east-west/north-south or both
0.0.3 - 4/1/2022 - Updated parameters for specific outputs to be more clear, removed option for specific outputs
1.0.0 - 8/4/2022 - Fixed output parameters so custom file names can be added
1.0.1 - 8/5/2022 - added automatic symbology, dynamic labeling and inputs
1.0.2 - 8/31/2022 - added validation of vertical and horizontal units
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.2"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import math
from arcpy.sa import *
import os
import sys

class DirectionalSlope(object):
    def __init__(self):
        self.label = "Directional Slope Analysis"
        self.description = "Analyzes the directional slope of a surface N/S & E/W"
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
            displayName="Vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Foot", "Meter"]

        param2 = arcpy.Parameter(
            displayName="Slope output measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Percent", "Degrees", "Radians"]

        param3 = arcpy.Parameter(
            displayName="Directions to output",
            name="outPut_options",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["East/West", "North/South", "East/West/North/South"]

        param4 = arcpy.Parameter(
            displayName="East/west directional slope raster output dataset",
            name="ewDS",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param5 = arcpy.Parameter(
            displayName="North/south directional slope raster output dataset",
            name="nsDS",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5]
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

        if not parameters[2].altered:
            parameters[2].value = "Percent"

        if parameters[3].value == "East/West" or parameters[3].value == "East/West/North/South":
            parameters[4].enabled = True
        else:
            parameters[4].enabled = False

        if parameters[3].value == "North/South" or parameters[3].value == "East/West/North/South":
            parameters[5].enabled = True
        else:
            parameters[5].enabled = False

        if not parameters[4].altered:
            parameters[4].value = "ewDS"

        if not parameters[5].altered:
            parameters[5].value = "nsDS"

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
        demInput = parameters[0].valueAsText  # Raw or graded digital elevation model
        xyzUnit = parameters[1].valueAsText  # Foot or Meter
        slopeUnits = parameters[2].valueAsText  # Slope units: percent, degrees, or radians
        outPut_options = parameters[3].valueAsText  # Directional slope rasters to output
        ewOutput = parameters[4].valueAsText  # East/West output raster
        nsOutput = parameters[5].valueAsText  # North/South output raster

        # Set grid resolution to the DEM raster and snap to raster
        spatialRef = arcpy.Describe(demInput).spatialReference
        arcpy.env.snapRaster = demInput

        arcpy.SetProgressor('default', 'Analyzing the surface directional slope...')

        # Process aspect
        AspectDeg = arcpy.sa.Aspect(demInput, "PLANAR", xyzUnit)
        AspectRad = AspectDeg * math.pi / 180

        arcpy.SetProgressor('default', 'Analyzing the surface slope...')

        # Process slope
        SlopeDeg = arcpy.sa.Slope(demInput, "DEGREE", "1", "PLANAR", xyzUnit)
        SlopeRad = SlopeDeg * math.pi / 180

        if outPut_options == "North/South" or outPut_options == "East/West/North/South":

            arcpy.SetProgressor('default', 'Processing the north-south slope...')

            # Process north-south slope in slope in radians, degrees, or percent
            CosAspRad = Cos(AspectRad)
            nsRad = CosAspRad * SlopeRad
            if slopeUnits == "Radians":
                nsRad.save(nsOutput)
            if slopeUnits == "Degrees":
                nsDeg = nsRad * 180 / math.pi
                nsDeg.save(nsOutput)
            if slopeUnits == "Percent":
                nsPerc = Tan(nsRad) * 100
                nsPerc.save(nsOutput)

            aprxMap.addDataFromPath(nsOutput)

            nsName = os.path.basename(nsOutput)

            # Apply symbology
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    sym = l.symbology
                    if l.name == nsName:
                        sym.colorizer.stretchType = "StandardDeviation"
                        cr = aprx.listColorRamps('North-South Slope')[0]
                        sym.colorizer.colorRamp = cr
                        if slopeUnits == "Percent":
                            sym.colorizer.minLabel = "South (%)"
                            sym.colorizer.maxLabel = "North (%)"
                        if slopeUnits == "Degrees":
                            sym.colorizer.minLabel = "South (degrees)"
                            sym.colorizer.maxLabel = "North (degrees)"
                        if slopeUnits == "Radians":
                            sym.colorizer.minLabel = "South (radians)"
                            sym.colorizer.maxLabel = "North (radians)"

                        l.symbology = sym

        if outPut_options == "East/West" or outPut_options == "East/West/North/South":

            arcpy.SetProgressor('default', 'Processing the east-west slope...')

            # Process east-west slope in radians, degrees, or percent
            SinAspRad = Sin(AspectRad)
            ewRad = SinAspRad * SlopeRad
            if slopeUnits == "Radians":
                ewRad.save(ewOutput)
            if slopeUnits == "Degrees":
                # Process east-west slope in degrees
                ewDeg = ewRad * 180 / math.pi
                ewDeg.save(ewOutput)
            if slopeUnits == "Percent":
                ewPerc = Tan(ewRad) * 100
                ewPerc.save(ewOutput)

            aprxMap.addDataFromPath(ewOutput)

            ewName = os.path.basename(ewOutput)

            # Apply symbology
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    sym = l.symbology
                    if l.name == ewName:
                        sym.colorizer.stretchType = "StandardDeviation"
                        cr = aprx.listColorRamps('East-West Slope')[0]
                        sym.colorizer.colorRamp = cr
                        if slopeUnits == "Percent":
                            sym.colorizer.minLabel = "West (%)"
                            sym.colorizer.maxLabel = "East (%)"
                        if slopeUnits == "Percent":
                            l.description = "Slope (%)"
                        if slopeUnits == "Degrees":
                            sym.colorizer.minLabel = "West (degrees)"
                            sym.colorizer.maxLabel = "East (degrees)"
                        if slopeUnits == "Radians":
                            sym.colorizer.minLabel = "West (radians)"
                            sym.colorizer.maxLabel = "East (radians)"

                        l.symbology = sym

            arcpy.ResetProgressor()

            return
