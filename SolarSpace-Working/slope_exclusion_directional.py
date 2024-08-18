########################################################################
"""CREATES EXCLUSION AREAS BASED ON SLOPE LIMITATIONS
Revision log
0.0.1 - 9/29/2021 - Rebuilt, updated to match KN coding standards
0.0.2 - 2/11/2022 - Updated algorithm, added capability for degrees and percent, feet and meters
0.0.3 - 2/11/2022 - Updated inputs to have individual inputs by direction, as well as outputs
0.0.4 - 5/23/2023 - Transformed to pyt
"""

__author__ = "Matthew Gagne"
__copyright__ = "Copyright 2022, KiloNewton, LLC"
__credits__ = ["Matthew Gagne", "John Williamson"]
__version__ = "0.0.3"
__license__= "internal"
__ArcVersion__ = "ArcPro 2.9.3"
__maintainer__ = ["Matthew Gagne", "Zane Nordquist"]
__status__ = "Deployed internally"

# Load modules
import math
import arcpy
from arcpy import env

# Import spatial  & 3D analyst
from arcpy.sa import *
from arcpy.ddd import *

class SlopeExclusionDirectional(object):
    def __init__(self):
        self.label = "Creates directional slope limitations"
        self.description = "Creates exclusion areas based on directional slope limitations"
        self.canRunInBackground = False
        self.category = "kNz Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input digital elevation model dataset",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Maximum Length of Row",
            name="rowLength",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Slope output measurement units",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Percent", "Degrees"]

        param3 = arcpy.Parameter(
            displayName="North Limit",
            name="northLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="South Limit",
            name="southLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="East limit",
            name="eastLimit",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="West limit",
            name="westLimit",
            datatype="Double",
            parameterType="Required",
            direction="Derived")

        param7 = arcpy.Parameter(
            displayName="Vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param7.filter.type = "ValueList"
        param7.filter.list = ["Foot", "Meter"]

        param8 = arcpy.Parameter(
            displayName="Output exclusion feature class",
            name="version",
            datatype="String",
            parameterType="Required",
            direction="Derived")

        
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

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
        import math
        
        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demInput = parameters[0].valueAsText # Input elevation model - raster
        rowLength = parameters[1].valueAsText # row length in units defined
        slopeUnits = parameters[2].valueAsText # Units of slope - percent or degree
        northLimit = parameters[3].valueAsText
        southLimit = parameters[4].valueAsText
        eastLimit = parameters[5].valueAsText
        westLimit = parameters[6].valueAsText
        xyzUnit = parameters[7].valueAsText # Foot or Meter
        version = parameters[8].valueAsText # Version control

        arcpy.SetProgressor("default", "Determining Directional Slopes...")

        # Set grid resolution to the DEM raster and snap to raster
        spatialRef = arcpy.Describe(demInput).spatialReference
        arcpy.env.snapRaster = demInput
        gridRes = arcpy.Describe(demInput).meanCellWidth

        # Run focal statistics to get rid of small areas
        lengthRes = str(round(float(rowLength)/4,0))
        if xyzUnit == "Foot":
            widthRes = "30"
        if xyzUnit == "Meter": 
            widthRes = "10"

        focalInput = ("Rectangle " + lengthRes + " " + widthRes + " MAP")
        demFocal = arcpy.sa.FocalStatistics(demInput, focalInput, "MEAN", "DATA", 90)

        AspectRad = arcpy.sa.Aspect(demFocal,"PLANAR",xyzUnit) * math.pi / 180

        # Process slope in radians
        SlopeRad = arcpy.sa.Slope(demFocal,"DEGREE","1","PLANAR",xyzUnit) * math.pi / 180

        if slopeUnits == "Percent":
            ewSlope = Tan( Sin( AspectRad) * SlopeRad) * 100
            nsSlope = Tan( Cos( AspectRad) * SlopeRad) * 100
        if slopeUnits == "Degrees":
            ewSlope = Sin( AspectRad) * SlopeRad * 180 / math.pi
            nsSlope = Cos( AspectRad) * SlopeRad * 180 / math.pi

        # Reclassify
        northClass = '-2000 '+northLimit+' NODATA; '+northLimit+' 2000 1'
        northReclass = arcpy.sa.Reclassify(nsSlope, "VALUE", northClass, "DATA")

        southClass = '-2000 -'+southLimit+' 1; -'+southLimit+' 2000 NODATA'
        southReclass = arcpy.sa.Reclassify(nsSlope, "VALUE", southClass, "DATA")

        eastClass = '-2000 '+eastLimit+' NODATA; '+eastLimit+' 2000 1'
        eastReclass = arcpy.sa.Reclassify(ewSlope, "VALUE", eastClass, "DATA")

        westClass = '-2000 -'+westLimit+' 1; -'+westLimit+' 2000 NODATA'
        westReclass = arcpy.sa.Reclassify(ewSlope, "VALUE", westClass, "DATA")

        arcpy.SetProgressor("default", "Creating Exclusions...")

        # Convert to polygon
        northPoly = arcpy.conversion.RasterToPolygon(northReclass, "northPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
        southPoly = arcpy.conversion.RasterToPolygon(southReclass, "southPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
        eastPoly = arcpy.conversion.RasterToPolygon(eastReclass, "eastPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
        westPoly = arcpy.conversion.RasterToPolygon(westReclass, "westPoly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)

        # Aggregate within 25 feet and minimum areas and holes of 5000 sq ft
        north_agg = arcpy.cartography.AggregatePolygons(northPoly, "north_agg", "25 Feet", "5000 SquareFeet", "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)
        south_agg = arcpy.cartography.AggregatePolygons(southPoly, "south_agg", "25 Feet", "5000 SquareFeet", "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)
        east_agg = arcpy.cartography.AggregatePolygons(eastPoly, "east_agg", "25 Feet", "5000 SquareFeet", "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)
        west_agg = arcpy.cartography.AggregatePolygons(westPoly, "west_agg", "25 Feet", "5000 SquareFeet", "5000 SquareFeet", "NON_ORTHOGONAL", None, None, None)

        # Buffer out by 1/16 of the row length to merge close areas
        bufferOut = str(float( rowLength) / 16) + " " + xyzUnit
        northBufferOut = arcpy.analysis.Buffer(north_agg, "northBufferOut", bufferOut, "FULL", "ROUND", "NONE", None, "PLANAR")
        southBufferOut = arcpy.analysis.Buffer(south_agg, "southBufferOut", bufferOut, "FULL", "ROUND", "NONE", None, "PLANAR")
        eastBufferOut = arcpy.analysis.Buffer(east_agg, "eastBufferOut", bufferOut, "FULL", "ROUND", "NONE", None, "PLANAR")
        westBufferOut = arcpy.analysis.Buffer(west_agg, "westBufferOut", bufferOut, "FULL", "ROUND", "NONE", None, "PLANAR")

        # Buffer in by 1/8 of the row area to get rid of small areas
        bufferIn = str(float( rowLength) / -8) + " " + xyzUnit
        northBufferIn = arcpy.analysis.Buffer(northBufferOut, "northBufferIn", bufferIn, "FULL", "ROUND", "NONE", None, "PLANAR")
        southBufferIn = arcpy.analysis.Buffer(southBufferOut, "southBufferIn", bufferIn, "FULL", "ROUND", "NONE", None, "PLANAR")
        eastBufferIn = arcpy.analysis.Buffer(eastBufferOut, "eastBufferIn", bufferIn, "FULL", "ROUND", "NONE", None, "PLANAR")
        westBufferIn = arcpy.analysis.Buffer(westBufferOut, "westBufferIn", bufferIn, "FULL", "ROUND", "NONE", None, "PLANAR")

        # Buffer out by 1/32 of the row length
        bufferFinal = str(float( rowLength) / 32) + " " + xyzUnit
        northPreFinal = arcpy.analysis.Buffer(northBufferIn, "northPreFinal", bufferFinal, "FULL", "ROUND", "NONE", None, "PLANAR")
        southPreFinal = arcpy.analysis.Buffer(southBufferIn, "southPreFinal", bufferFinal, "FULL", "ROUND", "NONE", None, "PLANAR")
        eastPreFinal = arcpy.analysis.Buffer(eastBufferIn, "eastPreFinal", bufferFinal, "FULL", "ROUND", "NONE", None, "PLANAR")
        westPreFinal = arcpy.analysis.Buffer(westBufferIn, "westPreFinal", bufferFinal, "FULL", "ROUND", "NONE", None, "PLANAR")

        # Get rid of areas smaller than 5000 square feet - need an if statement here for meters
        lengthRes = str(round(float(rowLength)/8,0))
        if xyzUnit == "Foot":
            areaMax = "Shape_Area > 5000"
        if xyzUnit == "Meter": 
            areaMax = "Shape_Area > 465"
        northFinal = arcpy.analysis.Select(northPreFinal,"northExclusion" + version, areaMax)
        southFinal = arcpy.analysis.Select(southPreFinal,"southExclusion" + version, areaMax)
        eastFinal = arcpy.analysis.Select(eastPreFinal,"eastExclusion" + version, areaMax)
        westFinal = arcpy.analysis.Select(westPreFinal,"westExclusion" + version, areaMax)

        # Add results to map
        aprxMap.addDataFromPath(northFinal)
        aprxMap.addDataFromPath(southFinal)
        aprxMap.addDataFromPath(eastFinal)
        aprxMap.addDataFromPath(westFinal)


        arcpy.ResetProgressor()

        return

