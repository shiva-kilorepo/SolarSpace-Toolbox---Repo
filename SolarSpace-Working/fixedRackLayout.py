########################################################################
""" FIXED RACK LAYOUT TOOL

Revision log
0.0.1 - 05/05/2022 - Initial scripting
1.0.0 - 02/08/2023 - Updated to PYT format
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Commercial"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules`
import arcpy
from arcpy import env
import sys
import math

class fixedRackLayout(object):
    def __init__(self):
        self.label = "Fixed Rack Layout Tool"
        self.description = "Creates a preliminary fixed rack layout based on a buildable area and technology specifications"
        self.canRunInBackground = False
        self.category = "Site Design\Layout Creation"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Buildable area feature class",
            name="buildable_area",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Measurement units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Foot", "Meter"]

        param2 = arcpy.Parameter(
            displayName="Module name",
            name="moduleType",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Module power (Watts)",
            name="modPower",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Module length",
            name="modLength",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Module width",
            name="modWidth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Module gap",
            name="modGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="East-west gap between rows (non-road)",
            name="rowGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Array tilt (degrees)",
            name="arrayAngle",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Inverter name",
            name="inverterType",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param10 = arcpy.Parameter(
            displayName="Inverter size (MWac)",
            name="inverterSize",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param11 = arcpy.Parameter(
            displayName="DC/AC ratio",
            name="dcacRatio",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param12 = arcpy.Parameter(
            displayName="Aspect ratio",
            name="aspectRatio",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param12.filter.type = "ValueList"
        param12.filter.list = ["1P", "2P", "1L", "2L", "3L"]

        param13 = arcpy.Parameter(
            displayName="Modules per string",
            name="modString",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        param14 = arcpy.Parameter(
            displayName="Strings per full row",
            name="stringsRow",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        param15 = arcpy.Parameter(
            displayName="GCR (%)",
            name="GCR",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param16 = arcpy.Parameter(
            displayName="Road width",
            name="roadWidth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param17 = arcpy.Parameter(
            displayName="Output strings or full rows?",
            name="stringsRowsOption",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param17.filter.type = "ValueList"
        param17.filter.list = ["Strings", "Full rows"]

        param18 = arcpy.Parameter(
            displayName="Layout output feature class",
            name="layoutOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param19 = arcpy.Parameter(
            displayName="Layout summary table",
            name="summaryOutput",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14, param15, param16, param17, param18, param19]

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

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        buildable_area = parameters[0].valueAsText
        xyzUnit = parameters[1].valueAsText
        moduleType = parameters[2].valueAsText
        modPower = parameters[3].valueAsText
        modLength = parameters[4].valueAsText
        modWidth = parameters[5].valueAsText
        modGap = parameters[6].valueAsText
        rowGap = parameters[7].valueAsText
        arrayAngle = parameters[8].valueAsText
        inverterType = parameters[9].valueAsText
        inverterSize = parameters[10].valueAsText
        dcacRatio = parameters[11].valueAsText
        aspectRatio = parameters[12].valueAsText
        modString = parameters[13].valueAsText
        stringsRow = parameters[14].valueAsText
        GCR = parameters[15].valueAsText
        roadWidth = parameters[16].valueAsText
        stringsRowsOption = parameters[17].valueAsText
        layoutOutput = parameters[18].valueAsText
        summaryOutput = parameters[19].valueAsText

        # Calculate variables
        panelsRow = float( modString) * float( stringsRow) # Number of panels per row
        powerRow = float( modPower) * panelsRow / 1000
        rowsInverter = math.ceil( float( inverterSize) * float( dcacRatio) * 1000 / powerRow)

        # Calculate row width and length
        if aspectRatio == "1P":
            aspectFactor = 1
            rowWidthFlat = float( modLength)
            rowWidth = math.cos(math.radians(float(arrayAngle)))*rowWidthFlat
            rowLength =  panelsRow * ( float( modWidth) + float( modGap)) / aspectFactor
        if aspectRatio == "2P":
            aspectFactor = 2
            rowWidthFlat = ( float( modGap) + float( modLength) * aspectFactor) 
            rowWidth = math.cos(math.radians(float(arrayAngle)))*rowWidthFlat
            rowLength =  panelsRow * ( float( modWidth) + float( modGap)) / aspectFactor
        if aspectRatio == "1L":
            aspectFactor = 1
            rowWidthFlat = float( modWidth)
            rowWidth = math.cos(math.radians(float(arrayAngle)))*rowWidthFlat
            rowLength =  panelsRow * ( float( modLength) + float( modGap)) / aspectFactor
        if aspectRatio == "2L":
            aspectFactor = 2
            rowWidthFlat = ( float( modGap) + float( modWidth) * aspectFactor) 
            rowWidth = math.cos(math.radians(float(arrayAngle)))*rowWidthFlat
            rowLength =  panelsRow * ( float( modLength) + float( modGap)) / aspectFactor
        if aspectRatio == "3L":
            aspectFactor = 2
            rowWidthFlat = ( float( modGap) + float( modWidth) * aspectFactor) 
            rowWidth = math.cos(math.radians(float(arrayAngle)))*rowWidthFlat
            rowLength =  panelsRow * ( float( modLength) + float( modGap)) / aspectFactor

        # Calculate spacing variables
        center_center = ( rowWidth / ( float( GCR)/100)) 
        gap_NS = ( center_center - rowWidth)

        # Calculate rows per block NS and EW
        EWrowsBlock = math.floor ( math.sqrt( rowsInverter))
        NSrowsBlock = math.ceil ( rowsInverter / EWrowsBlock)

        # Calculate block size
        EWblock = (rowLength + float(rowGap)) * EWrowsBlock
        NSblock = NSrowsBlock*( rowWidth + gap_NS)

        # Calculate Fishnet Size
        EWfishnet = (EWblock + float( roadWidth) + float(rowGap ))
        NSfishnet = (NSblock + float( roadWidth) - gap_NS)

        # Define extents of buildable area
        desc = arcpy.Describe(buildable_area)

        # Define spatial reference
        spatialRef = desc.spatialReference

        xMin = str(desc.extent.XMin) 
        yMin = str(desc.extent.YMin)

        originXY = xMin + " " + yMin
        yAxisCoor = xMin + " " + str(desc.extent.YMin + 10)

        # Create a fishnet of inverter block
        inverterBlocks = arcpy.management.CreateFishnet(r"in_memory\inverterBlocks", originXY, yAxisCoor, EWfishnet, NSfishnet, None, None, None, "NO_LABELS", buildable_area, "POLYGON")

        # Calculate x and y adjustments to polygon extents
        x_adj = str((EWfishnet - EWblock)/2 - float(rowGap))
        y_adj = str((NSfishnet - NSblock)/2)

        # Create points of zone corners
        corner_points = arcpy.management.FeatureVerticesToPoints(inverterBlocks, r"in_memory\corner_points", "ALL")
        arcpy.management.AddXY(corner_points)
        arcpy.management.AddFields(corner_points, [["xNew", "DOUBLE"], ["yNew", "DOUBLE"]])
        points_stats = arcpy.analysis.Statistics(corner_points, r"in_memory\points_stats", "POINT_X MAX;POINT_X MIN;POINT_Y MAX;POINT_Y MIN", "ORIG_FID")
        arcpy.management.JoinField(corner_points, "ORIG_FID", points_stats, "ORIG_FID", "MAX_POINT_X; MAX_POINT_Y")

        # Calculate new x coordinates
        codeblock_newX = """
def xNew(x,xMAX, xDist):
    if x == xMAX:
        return x - xDist
    else:
        return x + xDist
"""

        arcpy.management.CalculateField(corner_points, "xNew", "xNew(!POINT_X!,!MAX_POINT_X!,"+x_adj+")", "PYTHON3", codeblock_newX)

        # Calculate new y coordinates
        codeblock_newY = """
def yNew(y,yMAX, yDist):
    if y == yMAX:
        return y - yDist
    else:
        return y + yDist
"""

        arcpy.management.CalculateField(corner_points, "yNew", "yNew(!POINT_Y!,!MAX_POINT_Y!,"+y_adj+")", "PYTHON3", codeblock_newY)

        new_points = arcpy.management.XYTableToPoint(corner_points, r"in_memory\new_points", "xNew", "yNew", None, spatialRef)

        inverterBlocks_adj = arcpy.management.MinimumBoundingGeometry(new_points, r"in_memory\inverterBlocks_adj", "RECTANGLE_BY_AREA", "LIST", "ORIG_FID", "NO_MBG_FIELDS")

        # Subdivide into two sections
        if NSrowsBlock == 1:
            rowBlocks_pre = inverterBlocks_adj
        else: 
            rowBlocks_pre = arcpy.management.SubdividePolygon(inverterBlocks_adj, r"in_memory\rowBlocks_pre", "NUMBER_OF_EQUAL_PARTS", NSrowsBlock, None, None, 0, "STRIPS")

        del y_adj
        del x_adj
        del corner_points
        del points_stats
        del new_points

        # Subdivide polygon to make individual rows then graphic buffer the rowGap/2
        rowsBlocksDivide = arcpy.management.SubdividePolygon(rowBlocks_pre, r"in_memory\rowsBlocksDivide", "NUMBER_OF_EQUAL_PARTS", EWrowsBlock, None, None, 0, "STACKED_BLOCKS")

        y_adj = str(gap_NS/2)
        x_adj = str(float(rowGap )/2)

        # Create points of zone corners
        corner_points = arcpy.management.FeatureVerticesToPoints(rowsBlocksDivide, r"in_memory\corner_points", "ALL")
        arcpy.management.AddXY(corner_points)
        arcpy.management.AddFields(corner_points, [["xNew", "DOUBLE"], ["yNew", "DOUBLE"]])
        points_stats = arcpy.analysis.Statistics(corner_points, r"in_memory\points_stats", "POINT_X MAX;POINT_X MIN;POINT_Y MAX;POINT_Y MIN", "ORIG_FID")
        arcpy.management.JoinField(corner_points, "ORIG_FID", points_stats, "ORIG_FID", "MAX_POINT_X; MAX_POINT_Y")

        # Calculate new x coordinates
        codeblock_newX = """
def xNew(x,xMAX, xDist):
    if x == xMAX:
        return x - xDist
    else:
        return x + xDist
"""

        arcpy.management.CalculateField(corner_points, "xNew", "xNew(!POINT_X!,!MAX_POINT_X!,"+x_adj+")", "PYTHON3", codeblock_newX)

        # Calculate new y coordinates
        codeblock_newY = """
def yNew(y,yMAX, yDist):
    if y == yMAX:
        return y - yDist
    else:
        return y + yDist
"""

        arcpy.management.CalculateField(corner_points, "yNew", "yNew(!POINT_Y!,!MAX_POINT_Y!,"+y_adj+")", "PYTHON3", codeblock_newY)

        new_points = arcpy.management.XYTableToPoint(corner_points, r"in_memory\new_points", "xNew", "yNew", None, spatialRef)

        rowBlocks = arcpy.management.MinimumBoundingGeometry(new_points, r"in_memory\rowBlocks", "RECTANGLE_BY_AREA", "LIST", "ORIG_FID", "NO_MBG_FIELDS")

        if aspectFactor == 1:
            stringsFinal = rowBlocks
        else:
            if aspectRatio == "2P":
                    stringsFinal = arcpy.management.SubdividePolygon(rowBlocks, layoutOutput, "NUMBER_OF_EQUAL_PARTS", aspectFactor, None, None, 0, "STRIPS")
            stringsFinal = arcpy.management.SubdividePolygon(rowBlocks, layoutOutput, "NUMBER_OF_EQUAL_PARTS", aspectFactor, None, None, 0, "STACKED_BLOCKS")

        aprxMap.addDataFromPath(stringsFinal) 
        
        return

