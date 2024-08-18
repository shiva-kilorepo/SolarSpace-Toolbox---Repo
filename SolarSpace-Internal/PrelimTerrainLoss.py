########################################################################
"""PRELIMNINARY TERRAIN LOSS ASSESSMENT

Revision log
0.0.1 - 01/05/2022 - adapted from full terrain loss tool
1.0.0 - 8/5/2022 - updated for commercial release, static inputs for coefficients
1.0.1 - 9/12/2022 - Added vertical unit validation
1.1.0 - 12/29/2022 - Changed focal statistics to remove striation, 
changed focal statistics for north-south and east west, added option for
mechanical blocks and unlinked rows and optional east-west and north-south
loss rasters
1.1.1 - 4/1/2024 - Fixed minor focal stats issue
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2024, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.1.1"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import math
import arcpy
from arcpy import env
from arcpy.sa import *
import os
import sys

class PrelimTerrainLoss(object):
    def __init__(self):
        self.label = "Preliminary SAT Terrain Loss Assessment"
        self.description = "Estimates the losses with respect to terrain for single axis trackers without a layout"
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
            displayName="Tracker configuration",
            name="trackerConfig",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["Mechanical blocks", "Unlinked rows"]

        param5 = arcpy.Parameter(
            displayName="Block width",
            name="block_width",
            datatype="Double",
            parameterType="Optional",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Preliminary terrain loss estimate output raster",
            name="prelimLossOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Derived")

        param7 = arcpy.Parameter(
            displayName="Output individual east-west and north-south loss rasters?",
            name="ewnsOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param7.value = False

        param8 = arcpy.Parameter(
            displayName="Preliminary east-west terrain loss estimate output raster",
            name="ewLossOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        param9 = arcpy.Parameter(
            displayName="Preliminary north-south terrain loss estimate output raster",
            name="nsLossOut",
            datatype="DERasterDataset",
            parameterType="Optional",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return params

        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[2].value == "Foot":
            if not parameters[3].altered:
                parameters[3].value = '300'
        if parameters[2].value == "Meter":
            if not parameters[3].altered:
                parameters[3].value = '100'

        if parameters[4].value == "Mechanical blocks":
            parameters[5].enabled = True
        else:
            parameters[5].enabled = False

        if parameters[3].value == "Foot":
            if not parameters[5].altered:
                parameters[5].value = '500'
        if parameters[3].value == "Meter":
            if not parameters[5].altered:
                parameters[5].value = '150'

        if not parameters[6].altered:
            parameters[6].value = 'prelimLoss'

        if parameters[7].value == True:
            parameters[8].enabled = True
            parameters[9].enabled = True
        else:
            parameters[8].enabled = False
            parameters[9].enabled = False

        if not parameters[8].altered:
            parameters[8].value = 'ewLoss'

        if not parameters[9].altered:
            parameters[9].value = 'nsLoss'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        scratchWorkspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText  # Raw or graded digital elevation model
        aoi_boundary = parameters[1].valueAsText  # Area of interest
        xyzUnit = parameters[2].valueAsText  # Horizontal and vertical units
        tracker_length = parameters[3].valueAsText  # Tracker length north-south
        trackerConfig = parameters[4].valueAsText # Mechanical blocks or Unlinked rows 
        block_width = parameters[5].valueAsText  # Output raster dataset
        prelimLossOut = parameters[6].valueAsText  # Output raster dataset
        ewnsOption = parameters[7].value # Output raster dataset
        ewLossOut = parameters[8].valueAsText # Output raster dataset
        nsLossOut = parameters[9].valueAsText # Output raster dataset

        # Make focal inputs based on parameters
        if trackerConfig == "Unlinked rows":
            numSTDs = 2
            if xyzUnit == "Foot":
                focalInputEW = NbrRectangle(30, int(tracker_length), 'MAP')
                focalInputNW = NbrRectangle(30, int(tracker_length), 'MAP')
            if xyzUnit == "Meter":
                focalInputEW = NbrRectangle(9, int(tracker_length), 'MAP')
                focalInputNW = NbrRectangle(9, int(tracker_length), 'MAP')
        if trackerConfig == "Mechanical blocks":
            numSTDs = 3
            focalInputEW = NbrRectangle(int(block_width), int(tracker_length), 'MAP')
            focalInputNW = NbrRectangle(int(block_width), int(tracker_length), 'MAP')

        specProd = "2334"  # Panel specific production, based on terrain loss project
        ewVar = "-12.1"  # East-west variable, based on terrain loss project
        nsVarA = "13.8"  # North-south variable, based on terrain loss project
        nsVarB = "-0.15127"  # North-south variable, based on terrain loss project

        # Set spatial reference and grid resolution as the same as the DEM raster
        spatialRef = arcpy.Describe(demInput).spatialReference
        gridRes = arcpy.Describe(demInput).meanCellWidth

        # Set all raster outputs to snap to the DEM
        arcpy.env.snapRaster = demInput

        arcpy.SetProgressor('default', 'Analyzing terrain slope and variation...')

        # Run focal statistics on the terrain for east west and north south
        focal_DEM_EW = arcpy.sa.FocalStatistics(demInput, focalInputEW, "STD", "DATA")
        focal_DEM_NS = arcpy.sa.FocalStatistics(demInput, focalInputNW, "MEAN", "DATA")

        # Process aspect
        AspectRad = arcpy.sa.Aspect(focal_DEM_NS, "PLANAR", xyzUnit) * math.pi / 180

        # Process slope
        SlopeRad = arcpy.sa.Slope(focal_DEM_NS, "DEGREE", "1", "PLANAR", xyzUnit) * math.pi / 180

        # Process north-south and east-west slope in degrees
        nsDeg = arcpy.sa.Cos(AspectRad) * SlopeRad * 180 / math.pi

        arcpy.SetProgressor('default', 'Calculating the east-west losses...')

        # Calculate east-west production based on variation from east to west
        ewProd = (float(specProd) + float(ewVar) * (.5 * focal_DEM_EW * numSTDs))

        # Calculate east-west losses
        ewLoss = ((1 - ewProd / float(specProd)) * -100)

        arcpy.SetProgressor('default', 'Calculating the north-west losses...')

        # Calculate north-south production based on the mean from north to south
        nsProd = (float(specProd) - float(nsVarA) * nsDeg + float(nsVarB) * Power(nsDeg, 2))

        # Calculate north-south losses
        nsLoss = ((1 - nsProd / float(specProd)) * -100)

        arcpy.SetProgressor('default', 'Calculating the total losses...')

        # Calculate overall production
        allProd = (ewProd + (nsProd - float(specProd)))

        # Calculate losses from both east-west and north-south
        allLossPre = (1 - allProd / float(specProd))
        prelimLoss = arcpy.sa.Times(allLossPre, -100)
        lossName = os.path.basename(prelimLossOut)
        prelimLossClip = arcpy.management.Clip(prelimLoss, "", lossName, aoi_boundary, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")

        aprxMap.addDataFromPath(prelimLossClip)

        # Apply symbology
        for l in aprxMap.listLayers():
            if l.isRasterLayer:
                sym = l.symbology
                if l.name == lossName:
                    sym.colorizer.stretchType = "PercentClip"
                    cr = aprx.listColorRamps('Cyan to Purple')[0]
                    sym.colorizer.colorRamp = cr
                    sym.colorizer.invertColorRamp = True
                    sym.colorizer.minLabel = sym.colorizer.minLabel + " (%)"
                    sym.colorizer.maxLabel = sym.colorizer.maxLabel + " (%)"

                    l.symbology = sym

        if ewnsOption == True:        
            lossEWName = os.path.basename(ewLossOut)
            prelimEWClip = arcpy.management.Clip(ewLoss, "", lossEWName, aoi_boundary, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")        

            lossNSName = os.path.basename(nsLossOut)
            prelimNSClip = arcpy.management.Clip(nsLoss, "", lossNSName, aoi_boundary, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")        

            aprxMap.addDataFromPath(ewLossOut)
            aprxMap.addDataFromPath(nsLossOut)

            # Apply symbology
            for l in aprxMap.listLayers():
                if l.isRasterLayer:
                    sym = l.symbology
                    if l.name == lossEWName:
                        sym.colorizer.stretchType = "PercentClip"
                        cr = aprx.listColorRamps('Cyan to Purple')[0]
                        sym.colorizer.colorRamp = cr
                        sym.colorizer.invertColorRamp = True
                        sym.colorizer.minLabel = sym.colorizer.minLabel + " (%)"
                        sym.colorizer.maxLabel = sym.colorizer.maxLabel + " (%)"

                        l.symbology = sym

                    if l.name == lossNSName:
                        sym.colorizer.stretchType = "PercentClip"
                        cr = aprx.listColorRamps('Cyan to Purple')[0]
                        sym.colorizer.colorRamp = cr
                        sym.colorizer.invertColorRamp = True
                        sym.colorizer.minLabel = sym.colorizer.minLabel + " (%)"
                        sym.colorizer.maxLabel = sym.colorizer.maxLabel + " (%)"

                        l.symbology = sym

        arcpy.ResetProgressor()

        return