########################################################################
"""POLYGON DIRECTIONAL GRAPHIC BUFFER

Revision log
0.0.1 - 12/14/2022 - Initial scripting based on base plane of array zones script
1.0.0 - 5/17/2022 - Tested and deployed internally
1.0.1 - 1/5/2023 - Converter to PYT format
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.1"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import os.path
import sys

class DirectionalBuffer(object):
    def __init__(self):
        self.label = "Polygon Directional Graphic Buffer"
        self.description = "Graphically buffers a polygon feature class  east-west and north-south by prescribed distances"
        self.canRunInBackground = False
        self.category = "kNz Utilities"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input polygon feature class",
            name="polygonInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Polygon shape",
            name="polygonType",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Rectangles", "Irregular"]

        param2 = arcpy.Parameter(
            displayName="Measurement units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Distance to buffer to the east",
            name="xEast",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Distance to buffer to the west",
            name="xWest",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Distance to buffer to the north",
            name="yNorth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Distance to buffer to the south",
            name="ySouth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Accuracy resolution",
            name="fnVar",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Output feature class",
            name="polygonOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
        
        return params

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[1].altered:
            parameters[1].value = "Rectangles"

        if not parameters[2].altered:
            parameters[2].value = "Foot"

        if parameters[1].value == "Irregular":
            parameters[7].enabled = True
        else:
            parameters[7].enabled = False
            
        if not parameters[7].altered:
            parameters[7].value = .5

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # if parameters[1].value == "Irregular":
            # if parameters[3].altered:
                # if parameters[3].value < 0:
                    # parameters[3].setErrorMessage("Value must be greater than or equal to 0")
        # if parameters[1].value == "Irregular":
            # if parameters[4].altered:
                # if parameters[4].value < 0:
                    # parameters[4].setErrorMessage("Value must be greater than or equal to 0")
        # if parameters[1].value == "Irregular"
            # if parameters[5].altered:
                # if parameters[5].value < 0:
                    # parameters[5].setErrorMessage("Value must be greater than or equal to 0")
        # if parameters[1].value == "Irregular":
            # if parameters[6].altered:
                # if parameters[6].value < 0:
                    # parameters[6].setErrorMessage("Value must be greater than or equal to 0")
        # if parameters[1].value == "Irregular":
            # if parameters[7].altered:
                # if parameters[7].value <= 0 or parameters[7].value > 2:
                    # parameters[7].setErrorMessage(
                        # "Value must be greater than 0 and less than 2")

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        polygonInput = parameters[0].valueAsText
        polygonType = parameters[1].valueAsText
        xyzUnit = parameters[2].valueAsText
        xEast = parameters[3].valueAsText
        xWest = parameters[4].valueAsText
        yNorth = parameters[5].valueAsText
        ySouth = parameters[6].valueAsText
        fnVar = parameters[7].valueAsText
        polygonOutput = parameters[8].valueAsText

        # Set the spatial reference
        spatialRef = arcpy.Describe(polygonInput).spatialReference

        # Create a 1x1 fishnet of the input polygon

        arcpy.SetProgressor("default", "Determining polygon extents...")

        if polygonType == "Rectangles":
        
            # Create corner points of the rows - this only works for rows oriented north-south - if angled, this will not work
            polygonCornerPoints = arcpy.CreateFeatureclass_management("in_memory", "polygonCornerPoints", "POINT", "#", "DISABLED", "DISABLED", polygonInput)
            arcpy.AddField_management(polygonCornerPoints, "PolygonOID", "LONG")
            arcpy.AddField_management(polygonCornerPoints, "Position", "TEXT")

            insert_cursor = arcpy.da.InsertCursor(polygonCornerPoints, ["SHAPE@", "PolygonOID", "Position"])
            search_cursor = arcpy.da.SearchCursor(polygonInput, ["SHAPE@", "OID@"])

            for row in search_cursor:
                try:
                    polygon_oid = str(row[1])

                    coordinateList = []

                    for part in row[0]:
                        for pnt in part:
                            if pnt:
                                coordinateList.append((pnt.X, pnt.Y))
                    
                    #Determine the extent of each row
                    rowExtent = row[0].extent

                    sw_coordinate = rowExtent.lowerLeft
                    se_coordinate = rowExtent.lowerRight
                    nw_coordinate = rowExtent.upperLeft
                    ne_coordinate = rowExtent.upperRight
                    
                    sw_point = arcpy.PointGeometry(sw_coordinate)
                    se_point = arcpy.PointGeometry(se_coordinate)
                    nw_point = arcpy.PointGeometry(nw_coordinate)
                    ne_point = arcpy.PointGeometry(ne_coordinate)
                    
                    insert_cursor.insertRow((nw_point, polygon_oid, "NW"))
                    insert_cursor.insertRow((ne_point, polygon_oid, "NE"))
                    insert_cursor.insertRow((sw_point, polygon_oid, "SW"))
                    insert_cursor.insertRow((se_point, polygon_oid, "SE"))

                except Exception as err:
                    arcpy.AddMessage(str(err.message))

            del insert_cursor
            del search_cursor

            arcpy.management.AddXY(polygonCornerPoints)

            # Calculate new point coordinates
            codeblock_newX = """
def xNew(pos,x,xEast, xWest):
    if pos == "NW" or pos == "SW":
        return (x - xWest) 
    if pos == "NE" or pos == "SE":
        return (x + xEast)
"""

            arcpy.management.CalculateField(polygonCornerPoints, "xNew", "xNew(!Position!,!POINT_X!,"+xEast+", "+xWest+")", "PYTHON3", codeblock_newX, "DOUBLE")

            codeblock_newY = """
def yNew(pos,y,yNorth, ySouth):
    if pos == "NW" or pos == "NE":
        return (y + yNorth)
    if pos == "SW" or pos == "SE":
        return (y - ySouth)
"""

            arcpy.management.CalculateField(polygonCornerPoints, "yNew", "yNew(!Position!,!POINT_Y!,"+yNorth+", "+ySouth+")", "PYTHON3", codeblock_newY, "DOUBLE")
            new_points_table = arcpy.conversion.TableToTable(polygonCornerPoints, workspace, "new_points_table")
            new_points = arcpy.management.XYTableToPoint(new_points_table, r"in_memory\new_points", "xNew", "yNew", None, spatialRef)

            direcBuffOut = arcpy.management.MinimumBoundingGeometry(new_points, polygonOutput, "RECTANGLE_BY_AREA", "LIST", "PolygonOID", "NO_MBG_FIELDS")

            # Clean up
            arcpy.management.Delete(new_points_table)
            arcpy.management.Delete(polygonCornerPoints)

        else:
            desc = arcpy.Describe(polygonInput)

            xMin = str(desc.extent.XMin)
            yMin = str(desc.extent.YMin)

            originXY = xMin + " " + yMin
            yAxisCoor = xMin + " " + str(desc.extent.YMin + 10)

            fishnetPre = arcpy.management.CreateFishnet(r"in_memory\fishnetPre", originXY, yAxisCoor, fnVar,fnVar, None, None, None, "NO_LABELS", polygonInput,"POLYGON")

            # Create a line of the polygon boundary
            input_line = arcpy.management.FeatureToLine(polygonInput, "in_memory\input_line", None, "ATTRIBUTES")

            arcpy.SetProgressor("default", "Interpreting the polygon boundaries...")

            # Select the fishnet that intersects the boundary line
            fishnetScreen = arcpy.management.SelectLayerByLocation(fishnetPre, "Intersect", input_line, "", "NEW_SELECTION", "NOT_INVERT")

            # Create corner points of the fishnet squares
            fishnetCornerPoints = arcpy.management.CreateFeatureclass("in_memory", "fishnetCornerPoints", "POINT", "#", "DISABLED", "DISABLED", fishnetScreen)
            arcpy.management.AddField(fishnetCornerPoints, "PolygonOID", "LONG")
            arcpy.management.AddField(fishnetCornerPoints, "Position", "TEXT")

            insert_cursor = arcpy.da.InsertCursor(fishnetCornerPoints, ["SHAPE@", "PolygonOID", "Position"])
            search_cursor = arcpy.da.SearchCursor(fishnetScreen, ["SHAPE@", "OID@"])

            for row in search_cursor:
                try:
                    polygon_oid = str(row[1])

                    coordinateList = []

                    for part in row[0]:
                        for pnt in part:
                            if pnt:
                                coordinateList.append((pnt.X, pnt.Y))
                    
                    #Determine the extent of each row
                    rowExtent = row[0].extent

                    sw_coordinate = rowExtent.lowerLeft
                    se_coordinate = rowExtent.lowerRight
                    nw_coordinate = rowExtent.upperLeft
                    ne_coordinate = rowExtent.upperRight
                    
                    sw_point = arcpy.PointGeometry(sw_coordinate)
                    se_point = arcpy.PointGeometry(se_coordinate)
                    nw_point = arcpy.PointGeometry(nw_coordinate)
                    ne_point = arcpy.PointGeometry(ne_coordinate)
                    
                    insert_cursor.insertRow((nw_point, polygon_oid, "NW"))
                    insert_cursor.insertRow((ne_point, polygon_oid, "NE"))
                    insert_cursor.insertRow((sw_point, polygon_oid, "SW"))
                    insert_cursor.insertRow((se_point, polygon_oid, "SE"))

                except Exception as err:
                    arcpy.AddMessage(str(err.message))

            del insert_cursor
            del search_cursor

            arcpy.management.AddXY(fishnetCornerPoints)

            arcpy.SetProgressor("default", "Expanding the boundaries directionally...")

            # Calculate new point coordinates
            codeblock_newX = """
def xNew(pos,x,xEast, xWest):
    if pos == "NW" or pos == "SW":
        return (x - xWest) 
    if pos == "NE" or pos == "SE":
        return (x + xEast)
"""

            arcpy.management.CalculateField(fishnetCornerPoints, "xNew", "xNew(!Position!,!POINT_X!,"+xEast+", "+xWest+")", "PYTHON3", codeblock_newX, "DOUBLE")

            codeblock_newY = """
def yNew(pos,y,yNorth, ySouth):
    if pos == "NW" or pos == "NE":
        return (y + yNorth)
    if pos == "SW" or pos == "SE":
        return (y - ySouth)
"""

            arcpy.management.CalculateField(fishnetCornerPoints, "yNew", "yNew(!Position!,!POINT_Y!,"+yNorth+","+ySouth+")", "PYTHON3", codeblock_newY, "DOUBLE")
            new_points_table = arcpy.conversion.TableToTable(fishnetCornerPoints, workspace, "new_points_table")
            new_points = arcpy.management.XYTableToPoint(new_points_table, r"in_memory\new_points", "xNew", "yNew", None, spatialRef)

            arcpy.SetProgressor("default", "Creating the expanded polygon...")

            fishnet_exp = arcpy.management.MinimumBoundingGeometry(new_points, "fishnet_exp", "RECTANGLE_BY_AREA", "LIST", "PolygonOID", "NO_MBG_FIELDS")

            # Merge the original polygon with the expanded fishnet and dissolve
            polygonExp_merge = arcpy.management.Merge([[fishnet_exp],[polygonInput]], "in_memory\polygonExp_merge")
            polygonExp_dislv = arcpy.analysis.PairwiseDissolve(polygonExp_merge, "in_memory\polygonExp_dislv")

            # Simplify the boundary by twice the resolution of the fishnet
            if xyzUnit == "Foot":
                simpDist = str(float(fnVar)*2) + " Feet"
            else:
                simpDist = str(float(fnVar)*2) + " Meter"

            direcBuffOutName = os.path.basename(polygonOutput)
            direcBuffOut = arcpy.cartography.SimplifyPolygon(polygonExp_dislv, direcBuffOutName, "POINT_REMOVE", simpDist, "", "", "NO_KEEP", None)

            arcpy.management.Delete(fishnet_exp)
            arcpy.management.Delete(new_points_table)

        aprxMap.addDataFromPath(direcBuffOut)

        arcpy.ResetProgressor()

        return


