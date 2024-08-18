########################################################################
"""SINGLE AXIS TRACKER LAYOUT TOOL

Revision log
0.0.1 - 8/27/2021 - Input into new script template
0.0.2 - 6/7/2022 - Added summary table
1.0.0 - 12/9/2022 - Created python toolbox version of tool
1.1.0 - 12/29/2022 - Made default configurations and optional inputs, 
corrected spacing calculations, added option for strings or full rows 
output
2.0.0 - 2/20/2024 - Added optimization options added ability to use exclusions

NEXT UPDATE - Add option for not deleting strings for inverters (for trends)
Make it so strings are appropriately sized
Allow for soft boundaries? Make stand-alone tool first
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "John Williamson"]
__version__     = "2.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcGIS Pro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import math
import os
import sys

class SATLayoutPrelim(object):
    def __init__(self):
        self.label = "Create Single Axis Tracker Preliminary Layout"
        self.description = "Creates a preliminary tracker layout based on a buildable area and technology specifications"
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
            displayName="Tracker configuration",
            name="tracker_config",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param6.filter.type = "ValueList"
        param6.filter.list = ["Include bearing gaps", "No bearing gaps"]

        param7 = arcpy.Parameter(
            displayName="Bearing gap",
            name="bearingGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Motor/gearbox gap",
            name="gearboxGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Module gap",
            name="modGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param10 = arcpy.Parameter(
            displayName="North-south gap between rows (non-road)",
            name="rowGap",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param11 = arcpy.Parameter(
            displayName="Inverter name",
            name="inverterType",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param12 = arcpy.Parameter(
            displayName="Inverter size (MWac)",
            name="inverterSize",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param13 = arcpy.Parameter(
            displayName="Inverter width",
            name="inverterWidth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param14 = arcpy.Parameter(
            displayName="Inverter length",
            name="inverterLength",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param15 = arcpy.Parameter(
            displayName="DC/AC ratio",
            name="dcacRatio",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param16 = arcpy.Parameter(
            displayName="Aspect ratio",
            name="aspectRatio",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = ["1P", "2P"]

        param17 = arcpy.Parameter(
            displayName="Modules per string",
            name="modString",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        param18 = arcpy.Parameter(
            displayName="Strings per full row",
            name="stringsRow",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        param19 = arcpy.Parameter(
            displayName="GCR (%)",
            name="GCR",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param20 = arcpy.Parameter(
            displayName="Road width",
            name="roadWidth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param21 = arcpy.Parameter(
            displayName="Output strings or full rows?",
            name="stringsRowsOption",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Strings", "Full rows"]

        param22 = arcpy.Parameter(
            displayName="Layout output feature class",
            name="layoutOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param23 = arcpy.Parameter(
            displayName="Inverter output feature class",
            name="inverterOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param24 = arcpy.Parameter(
            displayName="Layout summary table",
            name="summaryOutput",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        
        # Updated Parameters for optimization
        param25 = arcpy.Parameter(
            displayName="Output Inverters?",
            name="invertersOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param26 = arcpy.Parameter(
            displayName="Utilize Exclusions in Analysis?",
            name="slopeExclusionOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param27 = arcpy.Parameter(
            displayName="Input Exclusion Feature Class?",
            name="exclusionFeatureClass",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param27.filter.list = ["Polygon"]
        
        param28 = arcpy.Parameter(
            displayName="Percent threshold to a remove a row that intersects an exclusion?",
            name="exclusionRemovePercent",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        
        param29 = arcpy.Parameter(
            displayName="Optimize Layout?",
            name="optimizeOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param30 = arcpy.Parameter(
            displayName="Remove Single Strings?",
            name="singleStringOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param31 = arcpy.Parameter(
            displayName="Remove blocks of rows under limit?",
            name="removeBlockOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param32 = arcpy.Parameter(
            displayName="Input limit to utilize?",
            name="inputBlockLimit",
            datatype="Long",
            parameterType="Required",
            direction="Input")
        

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10,
                  param11, param12, param13, param14, param15, param16, param17, param18, param19, param20,
                  param21, param22, param23, param24, param25, param26, param27, param28, param29, param30,
                  param31, param32]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            parameters[2].value = "Generic 550 W Panel"

        if not parameters[3].altered:
            parameters[3].value = "550"

        if parameters[1].value == "Foot":
            if not parameters[4].altered:
                parameters[4].value = "7.4"
            if not parameters[5].altered:
                parameters[5].value = "3.5"
            if not parameters[8].altered:
                parameters[8].value = "6"
            if not parameters[9].altered:
                parameters[9].value = "0.021"
            if not parameters[10].altered:
                parameters[10].value = "10"
            if not parameters[13].altered:
                parameters[13].value = "8.0"
            if not parameters[14].altered:
                parameters[14].value = "16.0"
            if not parameters[20].value:
                parameters[20].value = "25"
        if parameters[1].value == "Meter":
            if not parameters[4].altered:
                parameters[4].value = "2.25"
            if not parameters[5].altered:
                parameters[5].value = "1.15"
            if not parameters[8].altered:
                parameters[8].value = "1.8"
            if not parameters[9].altered:
                parameters[9].value = "0.00635"
            if not parameters[10].altered:
                parameters[10].value = "3"
            if not parameters[13].altered:
                parameters[13].value = "2.5"
            if not parameters[14].altered:
                parameters[14].value = "5"
            if not parameters[20].value:
                parameters[20].value = "7.5"
            
        if parameters[6].value == "Include bearing gaps":
            parameters[7].enabled = True
            if parameters[1].value == "Foot": 
                if not parameters[7].altered:
                    parameters[7].value = "0.541"
            if parameters[1].value == "Meter": 
                if not parameters[7].altered:
                    parameters[7].value = "0.165"

        if parameters[6].value == "No bearing gaps":
            parameters[7].enabled = False
            if not parameters[7].altered:
                parameters[7].value = "0"

        if not parameters[11].altered:
            parameters[11].value = "Generic 4.0 MWac inverter"

        if not parameters[12].altered:
            parameters[12].value = "4"

        if not parameters[15].altered:
            parameters[15].value = "1.25"

        if not parameters[16].value:
            parameters[16].value = "1P"

        if not parameters[17].value:
            parameters[17].value = "26"

        if not parameters[18].value:
            parameters[18].value = "3"

        if not parameters[19].value:
            parameters[19].value = "33"

        if not parameters[21].value:
            parameters[21].value = "Full rows"

        if not parameters[22].value:
            parameters[22].value = "prelimLayout"

        if not parameters[23].value:
            parameters[23].value = "prelimInverters"

        if not parameters[24].value:
            parameters[24].value = "prelimLayoutSummary"
        
        if not parameters[25].altered:
            parameters[25].value = True
            
        if parameters[26].value == True:
            parameters[27].enabled = True
            parameters[28].enabled = True
        else:
            parameters[27].enabled = False
            parameters[28].enabled = False
        
        if parameters[29].value == True:
            parameters[30].enabled = True
            if not parameters[30].altered:
                parameters[30].value = True
            parameters[31].enabled = True
            if not parameters[31].altered:
                parameters[31].value = True
        else:
            parameters[30].enabled = False
            parameters[31].enabled = False

        
        if parameters[31].value == True:
            parameters[32].enabled = True
        else:
            parameters[32].enabled = False
        
        if not parameters[26].value:
            parameters[28].value = 50
        
        if not parameters[32].value:
            parameters[32].value = 10

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
        buildable_area = parameters[0].valueAsText  # Polygon feature class of buildable area
        xyzUnit = parameters[1].valueAsText  # Horizontal and vertical units
        moduleType = parameters[2].valueAsText  # Module type for documentation only - future enhancement(does nothing now, put as optional)
        modPower = parameters[3].valueAsText  # module power in Watts
        modLength = parameters[4].valueAsText  # Module length - in map units (feet or meters)
        modWidth = parameters[5].valueAsText  # Module width - in map units (feet or meters)
        tracker_config = parameters[6].valueAsText
        bearingGap = parameters[7].valueAsText  # Bearing gap - in map units (feet or meters)
        gearboxGap = parameters[8].valueAsText  # Gearbox gap - in map units (feet or meters)
        modGap = parameters[9].valueAsText  # Gap between modules - in map units (feet or meters)
        rowGap = parameters[10].valueAsText  # Gap between rows north-south - in map units (feet or meters)
        inverterType = parameters[11].valueAsText  # Inverter type/name - future enhancement(does nothing now, put as optional)
        inverterSize = parameters[12].valueAsText  # Inverter size in MW
        inverterWidth = parameters[13].valueAsText  # Inverter width - in map units (feet or meters)
        inverterLength = parameters[14].valueAsText  # Inverter length - in map units (feet or meters)
        dcacRatio = parameters[15].valueAsText  # DC/AC Ratio
        aspectRatio = parameters[16].valueAsText  # Aspect ratio, either 1P or 2P
        modString = parameters[17].valueAsText  # Modules per string
        stringsRow = parameters[18].valueAsText  # Strings per row
        GCR = parameters[19].valueAsText  # Ground cover ratio as a %
        roadWidth = parameters[20].valueAsText  # Width left for site roads between blocks - in map units (feet or meters)
        stringsRowsOption = parameters[21].valueAsText  # Layout output feature class
        layoutOutput = parameters[22].valueAsText  # Layout output feature class
        inverterOutput = parameters[23].valueAsText  # Inverter output feature class
        summaryOutput = parameters[24].valueAsText  # Summary output table
        invertersOption = parameters[25].value  # Inverter output feature class
        slopeExclusionOption = parameters[26].value  # Utilize Exclusions in Analysis?
        exclusionFeatureClass = parameters[27].valueAsText  # Input Exclusion Feature Class
        exclusionRemovePercent = parameters[28].value  # Threshold to remove a row overlapping a slope exclusion
        optimizeOption = parameters[29].value  # Optimize Layout?
        singleStringOption = parameters[30].value  # Remove Single Strings?
        removeBlockOption = parameters[31].value  # Remove blocks of rows under limit?
        inputBlockLimit = parameters[32].value  # Input limit to utilize?
        
        # Define spatial reference and map units
        spatialRef = arcpy.Describe(buildable_area).spatialReference
        mapUnits = spatialRef.linearUnitName

        # Calculate variables
        panelsRow = float(modString) * float(stringsRow)  # Number of panels per row
        powerRow = float(modPower) * panelsRow / 1000
        numBearingGaps = math.ceil(float(panelsRow) / 8) - 1 + 3
        rowsInverter = math.ceil(float(inverterSize) * float(dcacRatio) * 1000 / powerRow)

        arcpy.SetProgressor('default', 'Determining row dimensions...')

        # Calculate row width and length
        if aspectRatio == "1P":
            rowWidth = float(modLength)
        if aspectRatio == "2P":
            rowWidth = (float(modGap) + float(modLength) * 2)

        rowLength = panelsRow * (float(modWidth) + float(modGap)) + float(bearingGap) * numBearingGaps + float(gearboxGap)

        arcpy.SetProgressor('default', 'Calculating row spacing...')

        # Calculate spacing variables
        center_center = (rowWidth / (float(GCR) / 100))
        gap_EW = (center_center - rowWidth)

        arcpy.AddMessage('Pitch east-west (center-center): ' + str(center_center) + ' ' + mapUnits)

        arcpy.SetProgressor('default', 'Calculating number of rows per inverter...')

        arcpy.AddMessage('Number of rows per inverter: ' + str(rowsInverter))

        # Calculate rows per block NS and EW
        NSrowsBlock = math.floor(math.sqrt(rowsInverter * center_center / rowLength))
        EWrowsBlock = math.ceil(rowsInverter / NSrowsBlock)

        # Calculate block size
        NSblock = (NSrowsBlock * rowLength + (NSrowsBlock - 1) * float(rowGap))
        EWblock = (EWrowsBlock * center_center - gap_EW)

        # Calculate Fishnet Size
        NSfishnet = NSblock + float(roadWidth) 
        EWfishnet = (EWblock + float(roadWidth))

        # Define extents of buildable area
        desc = arcpy.Describe(buildable_area)

        xMin = str(desc.extent.XMin)
        yMin = str(desc.extent.YMin)

        originXY = xMin + " " + yMin
        yAxisCoor = xMin + " " + str(desc.extent.YMin + 10)

        arcpy.SetProgressor('default', 'Creating initial inverter blocks...')

        # Create a fishnet of inverter block
        inverterBlocks = arcpy.management.CreateFishnet(r"in_memory\inverterBlocks", originXY, yAxisCoor, EWfishnet,NSfishnet, None, None, None, "NO_LABELS", buildable_area,"POLYGON")

        # Calculate x and y adjustments to polygon extents
        y_adj = str(float(roadWidth) - float(rowGap))
        x_adj = str(EWfishnet - center_center * EWrowsBlock)

        # Make this a called script
        # sys.path.append(util_path)

        # Create points of zone corners
        corner_points_blocks = arcpy.management.FeatureVerticesToPoints(inverterBlocks, r"in_memory\corner_points_blocks", "ALL")
        arcpy.management.AddXY(corner_points_blocks)
        points_stats_blocks = arcpy.analysis.Statistics(corner_points_blocks, r"in_memory\points_stats_blocks", "POINT_X MAX;POINT_X MIN;POINT_Y MAX;POINT_Y MIN; POINT_Y MEAN", "ORIG_FID")
        arcpy.management.JoinField(corner_points_blocks, "ORIG_FID", points_stats_blocks, "ORIG_FID", "MAX_POINT_X; MAX_POINT_Y; MIN_POINT_Y; MEAN_POINT_Y")

        # save corner points to a feature class for debugging
        #arcpy.management.CopyFeatures(corner_points_blocks, f'{workspace}/corner_points_blocks')
        
        # Calculate new x coordinates
        codeblock_newX = """
def xNew(x,xMAX, xDist):
    if x == xMAX:
        return x - xDist/2
    else:
        return x + xDist/2
"""

        arcpy.management.CalculateField(corner_points_blocks, "xNew", "xNew(!POINT_X!,!MAX_POINT_X!," + x_adj + ")", "PYTHON3",codeblock_newX, "DOUBLE")

        # Calculate new y coordinates
        codeblock_newY = """
def yNew(y,yMAX, yDist):
    if y == yMAX:
        return y - yDist/2
    else:
        return y + yDist/2
"""

        arcpy.management.CalculateField(corner_points_blocks, "yNew", "yNew(!POINT_Y!,!MAX_POINT_Y!," + y_adj + ")", "PYTHON3",codeblock_newY, "DOUBLE")

        new_points_blocks_adj = arcpy.management.XYTableToPoint(corner_points_blocks, r"in_memory\new_points_blocks_adj", "xNew", "yNew", None,spatialRef)

        inverterBlocks_adj = arcpy.management.MinimumBoundingGeometry(new_points_blocks_adj, r"in_memory\inverterBlocks_adj","RECTANGLE_BY_AREA", "LIST", "ORIG_FID", "NO_MBG_FIELDS")

        # Subdivide into two sections
        if NSrowsBlock == 1:
            rowBlocks_pre = inverterBlocks_adj
        else:
            rowBlocks_pre = arcpy.management.SubdividePolygon(inverterBlocks_adj, r"in_memory\rowBlocks_pre", "NUMBER_OF_EQUAL_PARTS", NSrowsBlock,None, None, 0, "STRIPS")
        
        # save rowBlocks_pre to a feature class for debugging
        #arcpy.management.CopyFeatures(rowBlocks_pre, f'{workspace}/rowBlocks_pre')

        # Adjust to subdivide size
        y_adj = str(float(rowGap) / 2)
        x_adj = str(0)

        # Make this a called script
        # sys.path.append(util_path)

        # Get the max, min of x and y and the mean of y for the adjusted inverter blocks

        # Create points of the adjusted inverter blocks corners
        corner_points_block_adj = arcpy.management.FeatureVerticesToPoints(rowBlocks_pre, r"in_memory\corner_points_block_adj", "ALL")

        arcpy.management.AddXY(corner_points_block_adj)

        points_stats = arcpy.analysis.Statistics(corner_points_block_adj, r"in_memory\points_stats","POINT_X MAX; POINT_Y MAX", "ORIG_FID")

        arcpy.management.JoinField(corner_points_block_adj, "ORIG_FID", points_stats, "ORIG_FID", "MAX_POINT_X; MAX_POINT_Y")

        # Calculate new x coordinates
        codeblock_newX = """
def xNew(x,xMAX, xDist):
    if x == xMAX:
        return x - xDist
    else:
        return x
"""

        arcpy.management.CalculateField(corner_points_block_adj, "xNew", "xNew(!POINT_X!,!MAX_POINT_X!," + x_adj + ")", "PYTHON3",codeblock_newX, "DOUBLE")

        # Calculate new y coordinates
        codeblock_newY = """
def yNew(y,yMAX, yDist):
    if y == yMAX:
        return y - yDist
    else:
        return y + yDist

"""

        arcpy.management.CalculateField(corner_points_block_adj, "yNew", "yNew(!POINT_Y!,!MAX_POINT_Y!," + y_adj + ")", "PYTHON3",codeblock_newY, "DOUBLE")

        new_points = arcpy.management.XYTableToPoint(corner_points_block_adj, r"in_memory\new_points", "xNew", "yNew", None,spatialRef)

        rowBlocks = arcpy.management.MinimumBoundingGeometry(new_points, r"in_memory\rowBlocks", "RECTANGLE_BY_AREA","LIST", "ORIG_FID", "NO_MBG_FIELDS")

        # Subdivide into expanded row bounds
        rows_pre = arcpy.management.SubdividePolygon(rowBlocks, r"in_memory\rows_pre", "NUMBER_OF_EQUAL_PARTS",EWrowsBlock, None, None, 90, "STRIPS")

        # Adjust to row size
        # Adjust to subdivide size
        x_adj = str(gap_EW / 2)

        # Make this a called script
        # sys.path.append(util_path)

        # Create points of zone corners
        corner_points_rows_pre = arcpy.management.FeatureVerticesToPoints(rows_pre, r"in_memory\corner_points_rows_pre", "ALL")
        arcpy.management.AddXY(corner_points_rows_pre)
        points_stats = arcpy.analysis.Statistics(corner_points_rows_pre, r"in_memory\points_stats","POINT_X MAX;POINT_X MIN", "ORIG_FID")
        arcpy.management.JoinField(corner_points_rows_pre, "ORIG_FID", points_stats, "ORIG_FID", "MAX_POINT_X")

        # Calculate new x coordinates
        codeblock_newX = """
def xNew(x,xMAX, xDist):
    if x == xMAX:
        return x - xDist
    else:
        return x + xDist
"""

        arcpy.management.CalculateField(corner_points_rows_pre, "xNew", "xNew(!POINT_X!,!MAX_POINT_X!," + x_adj + ")", "PYTHON3",codeblock_newX, "DOUBLE")

        new_points = arcpy.management.XYTableToPoint(corner_points_rows_pre, r"in_memory\new_points", "xNew", "POINT_Y", None,spatialRef)

        arcpy.SetProgressor('default', 'Creating full rows...')

        rowsFull = arcpy.management.MinimumBoundingGeometry(new_points, r"in_memory\rowsFull", "RECTANGLE_BY_AREA","LIST", "ORIG_FID", "NO_MBG_FIELDS")

        del x_adj

        arcpy.SetProgressor('default', 'Creating strings...')
         # Subdivide into strings
        rowsStrings = arcpy.management.SubdividePolygon(rowsFull, r"rowsStrings", "NUMBER_OF_EQUAL_PARTS", stringsRow,None, None, 0, "STRIPS")
        
        # Create Inverter Blocks
        if invertersOption == True:
            
            arcpy.SetProgressor('default', 'Creating full inverters...')

            # Create inverters point locations from inverter block center points
            inverterBlock_centerPoint = arcpy.management.FeatureToPoint(inverterBlocks,r"in_memory\inverterBlock_centerPoint", "CENTROID")
            arcpy.management.AddXY(arcpy.management.AddXY(inverterBlock_centerPoint))

            y_adj = str((NSfishnet - (NSrowsBlock - 1) * float(rowGap) - float(roadWidth) / 2 - rowLength / float(stringsRow)) / 2)
            x_adj = str((center_center * (EWrowsBlock - 1) / 2) - center_center / 2)

            arcpy.management.CalculateField(inverterBlock_centerPoint, "yNew", "!POINT_Y! + " + y_adj + "", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(inverterBlock_centerPoint, "xNew", "!POINT_X! + " + x_adj + "", "PYTHON3", "", "DOUBLE")

            inverter_points = arcpy.management.XYTableToPoint(inverterBlock_centerPoint, r"in_memory\inverter_points",
                                                            "xNew", "yNew", None, spatialRef)

            del y_adj
            del x_adj

            # Create inverter polygon from dimensions
            y_adj = str(float(inverterLength) / 2 + 1)
            x_adj = str(float(inverterWidth) / 2 + 1)


            arcpy.management.CalculateField(inverter_points, "xW", "!xNew! - " + x_adj + "", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(inverter_points, "xE", "!xNew! + " + x_adj + "", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(inverter_points, "yN", "!yNew! - " + y_adj + "", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(inverter_points, "yS", "!yNew! + " + y_adj + "", "PYTHON3", "", "DOUBLE")

            # Create new points
            inNW = arcpy.management.XYTableToPoint(inverter_points, r"in_memory\inNW", "xW", "yN", None, spatialRef)
            inNE = arcpy.management.XYTableToPoint(inverter_points, r"in_memory\inNE", "xE", "yN", None, spatialRef)
            inSW = arcpy.management.XYTableToPoint(inverter_points, r"in_memory\inSW", "xW", "yS", None, spatialRef)
            inSE = arcpy.management.XYTableToPoint(inverter_points, r"in_memory\inSE", "xE", "yS", None, spatialRef)

            # merge
            inverter_bound_points = arcpy.Merge_management([inNW, inNE, inSW, inSE], r"in_memory\inverter_bound_points")
            inverters_pre = arcpy.management.MinimumBoundingGeometry(inverter_bound_points, r"in_memory\inverters_pre",
                                                                    "RECTANGLE_BY_AREA", "LIST", "ORIG_FID",
                                                                    "NO_MBG_FIELDS")

            stringsInverters = arcpy.management.SelectLayerByLocation(rowsStrings, "WITHIN_A_DISTANCE", inverters_pre,
                                                                    gap_EW, "NEW_SELECTION", "INVERT")
            strings_pre = arcpy.conversion.FeatureClassToFeatureClass(stringsInverters, workspace, "strings_pre")
        
        else:
            strings_pre = arcpy.conversion.FeatureClassToFeatureClass(rowsStrings, workspace, "strings_pre")

        # Calculate initial layout statistics
        arcpy.SetProgressor('default', 'Calculating initial layout statistics..')

        # Select within buildable area
        strings_buildable = arcpy.management.SelectLayerByLocation(strings_pre, "COMPLETELY_WITHIN", buildable_area, None, "NEW_SELECTION", "NOT_INVERT")

        stringsOutput_pre = arcpy.conversion.FeatureClassToFeatureClass(strings_buildable, workspace, "stringsOutput_pre")

        arcpy.management.CalculateField(stringsOutput_pre, "row_ID","!ORIG_FID!", "PYTHON3", None, "LONG")

        arcpy.management.DeleteField(stringsOutput_pre, "ORIG_FID", "DELETE_FIELDS")

        ### OPTIMIZATION OPTIONS
        # if optimization options are selected run them now
        
        # run slope exclusion option if selected
        if slopeExclusionOption == True:
            arcpy.SetProgressor('default', 'Removing rows based on exclusions...')
            
            stringsOutput_pre_modified = SATLayoutPrelim.removeExclusionRows(stringsOutput_pre, xyzUnit, workspace, exclusionFeatureClass, exclusionRemovePercent)
            
            # save the output to a new feature class with stringsOutput_pre as the name
            stringsOutput_pre = arcpy.conversion.FeatureClassToFeatureClass(stringsOutput_pre_modified, workspace, "stringsOutput_pre")
            
        # run single string option if selected
        if singleStringOption == True:
            arcpy.SetProgressor('default', 'Removing single strings...')
            
            stringsOutput_pre_modified = SATLayoutPrelim.removeSingleStrings(rowWidth, rowLength, stringsRow, stringsOutput_pre, xyzUnit, workspace)
            
            # save the output to a new feature class with stringsOutput_pre as the name
            stringsOutput_pre = arcpy.conversion.FeatureClassToFeatureClass(stringsOutput_pre_modified, workspace, "stringsOutput_pre")
        
        # run block limit option if selected
        if removeBlockOption == True:
            arcpy.SetProgressor('default', 'Removing blocks of rows under specified limits...')
            
            stringsOutput_pre_modified = SATLayoutPrelim.removeBlockRows(stringsOutput_pre, inputBlockLimit, center_center, rowWidth, rowLength, stringsRow, rowBlocks_pre, xyzUnit, workspace)
            
            # save the output to a new feature class with stringsOutput_pre as the name
            stringsOutput_pre = arcpy.conversion.FeatureClassToFeatureClass(stringsOutput_pre_modified, workspace, "stringsOutput_pre")
        
        # generate layout name
        layoutName = os.path.basename(layoutOutput)

        # Dissolve strings into full rows if stringsRowsOption is "Full rows"
        if stringsRowsOption == "Full rows":
            outputLayout = arcpy.management.Dissolve(stringsOutput_pre, layoutOutput, "row_ID")
        else:
            outputLayout = arcpy.conversion.FeatureClassToFeatureClass(stringsOutput_pre, workspace, layoutName)

        # Create inverters if invertersOption is True
        if invertersOption == True:
            inverters_buildable = arcpy.management.SelectLayerByLocation(inverters_pre, "COMPLETELY_WITHIN", buildable_area, None, "NEW_SELECTION", "NOT_INVERT")
            inverterName = os.path.basename(inverterOutput)
            outputInverters = arcpy.conversion.FeatureClassToFeatureClass(inverters_buildable, workspace, inverterName)
            
            inverterResult = arcpy.GetCount_management(outputInverters)
            # The result is a Result object. To get the count as an integer, use the getOutput method
            inverterNum = int(inverterResult.getOutput(0))
        else:
            inverterNum = int(0)
            pass

        layoutSummary = arcpy.analysis.Statistics(strings_buildable, summaryOutput, "OBJECTID COUNT", None)
        arcpy.management.AlterField(layoutSummary, 'FREQUENCY', 'count_strings', 'Number of strings', 'LONG', 4,'NULLABLE', 'DO_NOT_CLEAR')
        arcpy.management.AddFields(layoutSummary, [["DC_MW", "DOUBLE", "DC Capacity (MWdc)"]])
        arcpy.management.CalculateField(layoutSummary, "DC_MW","!count_strings! * " + modString + " * " + modPower + "/1000/1000", "PYTHON3")
                
        # Add inverter count to layout summary
        arcpy.SetProgressor('default', 'Adding inverter count to layout summary...')
        #arcpy.AddMessage('Inverter Count: ' + str(inverterNum))
        if invertersOption == True or inverterNum > 0:
            inverterCount = arcpy.analysis.Statistics(outputInverters, "inverterCount", "OBJECTID COUNT", None)
            arcpy.management.AlterField(inverterCount, 'FREQUENCY', 'count_inverters', 'Number of Inverters', 'LONG', 4,'NULLABLE', 'DO_NOT_CLEAR')
            arcpy.management.JoinField(layoutSummary, "OBJECTID", inverterCount, "OBJECTID", "count_inverters")
        else:
            # create a blank table to join to layout summary
            inverterCount = arcpy.management.CreateTable(workspace, "inverterCount")
            # populate the table with a single row and a count of 0
            arcpy.management.AddField("inverterCount", "count_inverters", "LONG", field_alias="Number of Inverters")
            # set the count to 0
            arcpy.management.CalculateField("inverterCount", "count_inverters", "0", "PYTHON3")
            #arcpy.management.AlterField(inverterCount, 'FREQUENCY', 'count_inverters', 'Number of Inverters', 'LONG', 4,'NULLABLE', 'DO_NOT_CLEAR')

        # Add fields to layout summary
        arcpy.management.AddFields(layoutSummary,
                                   [["AC_MW", "DOUBLE", "AC Capacity (MWac)"], 
                                    ["DC_AC_RATIO", "DOUBLE", "DC/AC Ratio"],
                                    ["panelType", "TEXT", "Module Name"], 
                                    ["modRating", "DOUBLE", "Module Rating (W)"],
                                    ["modString", "LONG", "Modules per String"],
                                    ["inverterType", "TEXT", "Inverter Name"],
                                    ["inverterSize", "DOUBLE", "Inverter Size (MWac)"]])
        arcpy.management.CalculateField(layoutSummary, "modString", modString, "PYTHON3", None)
        arcpy.management.CalculateField(layoutSummary, "inverterSize", inverterSize, "PYTHON3", None)
        arcpy.management.CalculateField(layoutSummary, "panelType", "'" + moduleType + "'", "PYTHON3", None)
        arcpy.management.CalculateField(layoutSummary, "modRating", modPower, "PYTHON3", None)
        arcpy.management.CalculateField(layoutSummary, "inverterType", "'" + inverterType + "'", "PYTHON3", None)
        
        if invertersOption == True or inverterNum > 0:
            if inverterNum > 0:
                arcpy.management.CalculateField(layoutSummary, "AC_MW", "!count_inverters!*!inverterSize!", "PYTHON3", None)
                arcpy.management.CalculateField(layoutSummary, "DC_AC_RATIO", "!DC_MW!/!AC_MW!", "PYTHON3", None)
            else:
                # population AC_MW and DC_AC_RATIO with Null values
                arcpy.management.CalculateField(layoutSummary, "AC_MW", "0", "PYTHON3", None)
                arcpy.management.CalculateField(layoutSummary, "DC_AC_RATIO", "'<Null>'", "PYTHON3", None)
        else:
            # population AC_NW and DC_AC_RATIO with Null values
            arcpy.management.CalculateField(layoutSummary, "AC_MW", "0", "PYTHON3", None)
            arcpy.management.CalculateField(layoutSummary, "DC_AC_RATIO", "'<Null>'", "PYTHON3", None)

        arcpy.management.DeleteField(layoutSummary, "COUNT_OBJECTID", "DELETE_FIELDS")

        # Add layout and inverter outputs to map
        aprxMap.addDataFromPath(outputLayout)
        aprxMap.addDataFromPath(layoutSummary)
        
        try:
            if invertersOption == True:
                aprxMap.addDataFromPath(outputInverters)
                arcpy.management.Delete(inverterCount)
                arcpy.management.Delete(inverters_buildable)
                arcpy.management.Delete(inverters_pre)
                arcpy.management.Delete(stringsInverters)
                
            arcpy.management.Delete(stringsOutput_pre_modified)
            
            # Clean up
            arcpy.management.Delete(strings_buildable)
            arcpy.management.Delete(strings_pre)
            arcpy.management.Delete(points_stats)
            arcpy.management.Delete(new_points)
            arcpy.management.Delete(stringsOutput_pre)
            arcpy.management.Delete(rowsStrings)
        except:
            arcpy.AddMessage("Cleaning up was not successful")
            pass

        arcpy.ResetProgressor()

        return
    
    def removeSingleStrings(rowWidth, rowLength, stringsRow, stringsOutput_pre, xyzUnit, workspace):
        # copy rowsFull to a new feature class in memory
        #rowsWorking = arcpy.management.CopyFeatures(stringsOutput_pre, r"in_memory\rowsWorking")
        
        ### V1
        rowsWorking = arcpy.management.Dissolve(stringsOutput_pre, r"in_memory\rowsWorking", "row_ID")
        
        # generate Shape_Area and Shape_Length fields for rows
        if xyzUnit == "Foot":
            arcpy.management.CalculateGeometryAttributes(rowsWorking, [["Shape_Area", "AREA_GEODESIC"]], "FEET_US", "SQUARE_FEET_US")
        else:
            arcpy.management.CalculateGeometryAttributes(rowsWorking, [["Shape_Area", "AREA_GEODESIC"]], "METERS", "SQUARE_METERS")
        
        # Remove single strings from the layout
        
        # convert input strings to double
        rowWidth = float(rowWidth)
        rowLength = float(rowLength)
        stringsRow = int(stringsRow)

        # calculating area of single string rows
        single_area = (rowWidth*(rowLength/stringsRow))
        
        # Area modification
        single_area_mod = single_area + (single_area * 0.1)
        
        # Convert single_area_mod to an integer
        #single_area_mod = int(single_area_mod)
        
        arcpy.AddMessage(f'Selecting rows above area size: {str(single_area_mod)}')
        
        # select rows greater than the single area
        single_area_select = str(single_area_mod)
        layout_not_single = arcpy.management.SelectLayerByAttribute(rowsWorking, "NEW_SELECTION", "Shape_Area > " + single_area_select , None)
        
        #list number of rows selected
        rowsSelected = arcpy.GetCount_management(layout_not_single)
        arcpy.AddMessage(f'Number of rows selected: {str(rowsSelected)}')
        
        # copy the selected rows to a new feature class
        layout_not_single_fc = arcpy.management.CopyFeatures(layout_not_single, r"in_memory\layout_not_single_fc")
        #arcpy.management.CopyFeatures(layout_not_single, os.path.join(workspace, "layout_not_single_fc_testing"))
        
        # Select by location strings that intersect with the selected rows
        #layout_not_single_select = arcpy.management.SelectLayerByLocation(layout_not_single_fc, "INTERSECT", stringsOutput_pre, None, "NEW_SELECTION", "NOT_INVERT")
        
        arcpy.AddMessage(f'number of features in layout_not_single_fc: {str(arcpy.GetCount_management(layout_not_single_fc))}')
        arcpy.AddMessage(f'number of features in stringsOutput_pre: {str(arcpy.GetCount_management(stringsOutput_pre))}')
        
        layout_not_single_select = arcpy.management.SelectLayerByLocation(
            in_layer=stringsOutput_pre,
            overlap_type="INTERSECT",
            select_features=layout_not_single_fc,
            search_distance=None,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="NOT_INVERT"
        )
        
        arcpy.AddMessage(f'number of features in layout_not_single_select: {str(arcpy.GetCount_management(layout_not_single_select))}')
        
        # Copy the selected features to a new feature class with a different name
        stringsOutput_pre_modified = arcpy.conversion.FeatureClassToFeatureClass(layout_not_single_select, workspace, "stringsOutput_pre_modified")

        return stringsOutput_pre_modified

    def removeBlockRows(stringsOutput_pre, inputBlockLimit, center_center, rowWidth, rowLength, stringsRow, rowBlocks_pre, xyzUnit, workspace):
        # Remove block rows from the layout
        
        # copy strings to a new feature class in memory
        #stringsWorking = arcpy.management.CopyFeatures(stringsOutput_pre, r"in_memory\stringsWorking")
        
        # convert input strings to double
        inputBlockLimit = float(inputBlockLimit)
        center_center = float(center_center)
        rowWidth = float(rowWidth)
        rowLength = float(rowLength)
        stringsRow = int(stringsRow)
        
        # calculate minimum area for a block row
        block_area_width = (center_center * inputBlockLimit) + rowWidth
        block_area_length = (rowLength/stringsRow) * 2
        
        # calculate the area of a block row
        block_area = block_area_width * block_area_length
        
        #create a blockID field in the rowBlocks_pre feature class
        arcpy.management.AddField(rowBlocks_pre, "blockID", "LONG")
        
        # create a list of fields in the rowBlocks_pre feature class
        # fields = arcpy.ListFields(rowBlocks_pre)
        # Get the field names
        #fields = [f.name for f in fields]
        # arcpy.AddMessage(f'Fields in rowBlocks_pre: {fields}')

        #calculate the blockID field equal to the OBJECTID
        arcpy.management.CalculateField(rowBlocks_pre, "blockID", "!OID!", "PYTHON3", None)
        
        # Spatially join the block area blockID field to the stringsOutput_pre feature class
        stringsBlockID = arcpy.analysis.SpatialJoin(stringsOutput_pre, rowBlocks_pre, r"in_memory\stringsBlockID", "JOIN_ONE_TO_ONE", "KEEP_ALL", None, "INTERSECT", None, None)
        
        # aggregate strings into blocks
        layout_blocks = arcpy.cartography.AggregatePolygons(stringsBlockID, r"in_memory\layout_blocks", center_center, block_area, aggregate_field = "blockID")
        
        # Select strings by location that intersect with the blocks
        layout_blocks_select = arcpy.management.SelectLayerByLocation(stringsOutput_pre, "INTERSECT", layout_blocks, None, "NEW_SELECTION", "NOT_INVERT")
        
        # copy the selected strings to a new feature class        
        stringsOutput_pre_modified = arcpy.conversion.FeatureClassToFeatureClass(layout_blocks_select, workspace, "stringsOutput_pre_modified")

        return stringsOutput_pre_modified
    
    def removeExclusionRows(stringsOutput_pre, xyzUnit, workspace, exclusionFeatureClass, exclusionRemovePercent):
        # Remove rows that intersect with slope exclusions
        
        # copy strings to a new feature class in memory
        stringsWorking = arcpy.management.CopyFeatures(stringsOutput_pre, r"in_memory\stringsWorking")
        
        # calculate the area of each feature
        if xyzUnit == "Foot":
            arcpy.management.CalculateGeometryAttributes(stringsWorking, [["Shape_Area_orig", "AREA_GEODESIC"]], "FEET_US", "SQUARE_FEET_US")
        else:
            arcpy.management.CalculateGeometryAttributes(stringsWorking, [["Shape_Area_orig", "AREA_GEODESIC"]], "METERS", "SQUARE_METERS")
        
        # erase the exclusion feature class from the strings
        layout_exclusion_not_select = arcpy.analysis.Erase(stringsWorking, exclusionFeatureClass, r"in_memory\layout_exclusion_not_select")
        
        # calculate the area of each feature after the erase
        if xyzUnit == "Foot":
            arcpy.management.CalculateGeometryAttributes(layout_exclusion_not_select, [["Shape_Area_mod", "AREA_GEODESIC"]], "FEET_US", "SQUARE_FEET_US")
        else:
            arcpy.management.CalculateGeometryAttributes(layout_exclusion_not_select, [["Shape_Area_mod", "AREA_GEODESIC"]], "METERS", "SQUARE_METERS")
            
        calcExpression = "(!Shape_Area_mod! / !Shape_Area_orig!) * 100"
        
        # calculate the percent of the original area that remains after the erase
        arcpy.management.CalculateField(layout_exclusion_not_select, "percentRemaining", calcExpression, "PYTHON3", "", "DOUBLE")
        
        # select all strings that have a percent remaining greater than the exclusionRemovePercent
        exclusionRemovePercent = str(exclusionRemovePercent)
        where_clause = f"percentRemaining > {exclusionRemovePercent} Or percentRemaining = 100"
        layout_exclusion_erase = arcpy.management.SelectLayerByAttribute(layout_exclusion_not_select, "NEW_SELECTION", where_clause)
        
        # Select by location strings of stringsWorking that intersect with the selected strings of layout_exclusion_not_select
        layout_exclusion_not_select_final = arcpy.management.SelectLayerByLocation(stringsWorking, "CONTAINS", layout_exclusion_erase, None, "NEW_SELECTION", "NOT_INVERT")

        # copy the selected strings to a new feature class        
        stringsOutput_pre_modified = arcpy.conversion.FeatureClassToFeatureClass(layout_exclusion_not_select_final, workspace, "stringsOutput_pre_modified")

        return stringsOutput_pre_modified
        