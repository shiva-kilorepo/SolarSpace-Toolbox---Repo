########################################################################
"""CREATE POINTS ON POLYGONS

Revision log
v0.0.1 - 12/15/2021 - Adapted from script by Ian Broad
1.0.0 - 08/24/2023 - Converted to PYT format (internal use)
"""
# __author__      = "Matthew Gagne"
# __copyright__   = "Copyright 2023, KiloNewton, LLC"
# __credits__     = ["Matthew Gagne", "Zane Nordquist", "Liza Flowers", "Ian Broad"]
# __version__     = "1.0.0"
# __license__     = "Internal"
# __ArcVersion__  = "ArcGIS 3.1.2"
# __maintainer__  = ["Matthew Gagne", "Zane Nordquist", "Liza Flowers"]
# __status__      = "Testing"

#Load modules
import arcpy
import os.path
import sys

class PtsOnPolygon(object):
    def __init__(self):
        self.label = "Create Points On Polygons"
        self.description = "Creates points on a polygon"
        self.canRunInBackground = False
        self.category = "kNz Utilities"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input polygon layer",
            name="polygon",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName=" Output mid point layer?",
            name="midpoints",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param1.value = False

        param2 = arcpy.Parameter(
            displayName="Output points on polygon",
            name="output",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")
        

        params = [param0, param1, param2]
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
        
    def execute(self, parameters, messages):
        
        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        polygon = parameters[0].valueAsText #polygon input
        midpoints = parameters [1].value  #True or False statement for midpoints
        output = parameters[2].valueAsText #output points?

        outputName = os.path.basename(output)

        pointsOut = arcpy.management.CreateFeatureclass(workspace, outputName, "POINT", "#", "DISABLED", "DISABLED", polygon)
        arcpy.AddField_management(pointsOut, "PolygonOID", "LONG")
        arcpy.AddField_management(pointsOut, "Position", "TEXT")

        insert_cursor = arcpy.da.InsertCursor(pointsOut, ["SHAPE@", "PolygonOID", "Position"])
        search_cursor = arcpy.da.SearchCursor(polygon, ["SHAPE@", "OID@"])

        for row in search_cursor:
            polygon_oid = str(row[1])

            coordinateList = []
            sw_dist = {}
            se_dist = {}
            nw_dist = {}
            ne_dist = {}

            for part in row[0]:
                for pnt in part:
                    if pnt:
                        coordinateList.append((pnt.X, pnt.Y))

            # Find the extent of each row
            rowExtent = row[0].extent

            sw_coordinate = rowExtent.lowerLeft
            se_coordinate = rowExtent.lowerRight
            nw_coordinate = rowExtent.upperLeft
            ne_coordinate = rowExtent.upperRight

            sw_point = arcpy.PointGeometry(sw_coordinate)
            se_point = arcpy.PointGeometry(se_coordinate)
            nw_point = arcpy.PointGeometry(nw_coordinate)
            ne_point = arcpy.PointGeometry(ne_coordinate)

            # Find the vertex closest to each corner of the row extent
            for vertex in coordinateList:
                vertex_coordinates = arcpy.Point(vertex[0], vertex[1])
                vertex_point = arcpy.PointGeometry(vertex_coordinates)
                sw_dist[float(sw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                se_dist[float(se_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                nw_dist[float(nw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
                ne_dist[float(ne_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

            #Calculates where quarter quarter sections would intersect polygon
            swMinDist = min(sw_dist)
            seMinDist = min(se_dist)
            nwMinDist = min(nw_dist)
            neMinDist = min(ne_dist)

            sw_X = float(sw_dist[swMinDist][0])
            sw_Y = float(sw_dist[swMinDist][1])
            se_X = float(se_dist[seMinDist][0])
            se_Y = float(se_dist[seMinDist][1])

            nw_X = float(nw_dist[nwMinDist][0])
            nw_Y = float(nw_dist[nwMinDist][1])
            ne_X = float(ne_dist[neMinDist][0])
            ne_Y = float(ne_dist[neMinDist][1])

            sw_point = arcpy.PointGeometry(sw_coordinate)
            se_point = arcpy.PointGeometry(se_coordinate)
            nw_point = arcpy.PointGeometry(nw_coordinate)
            ne_point = arcpy.PointGeometry(ne_coordinate)

            insert_cursor.insertRow((nw_point, polygon_oid, "NW"))
            insert_cursor.insertRow((ne_point, polygon_oid, "NE"))
            insert_cursor.insertRow((sw_point, polygon_oid, "SW"))
            insert_cursor.insertRow((se_point, polygon_oid, "SE"))

            if midpoints == True:
                west_line = arcpy.Polyline(arcpy.Array([arcpy.Point(nw_X, nw_Y), arcpy.Point(sw_X, sw_Y)]))
                east_line = arcpy.Polyline(arcpy.Array([arcpy.Point(ne_X, ne_Y), arcpy.Point(se_X, se_Y)]))
                north_line = arcpy.Polyline(arcpy.Array([arcpy.Point(nw_X, nw_Y), arcpy.Point(ne_X, ne_Y)]))
                south_line = arcpy.Polyline(arcpy.Array([arcpy.Point(sw_X, sw_Y), arcpy.Point(se_X, se_Y)]))

                west_point = west_line.positionAlongLine(0.5, True)
                east_point = east_line.positionAlongLine(0.5, True)
                north_point = north_line.positionAlongLine(0.5, True)
                south_point = south_line.positionAlongLine(0.5, True)

                insert_cursor.insertRow((west_point, polygon_oid, "W"))
                insert_cursor.insertRow((east_point, polygon_oid, "E"))
                insert_cursor.insertRow((north_point, polygon_oid, "N"))
                insert_cursor.insertRow((south_point, polygon_oid, "S"))

        del insert_cursor
        del search_cursor

        aprxMap.addDataFromPath(pointsOut)
            
        return


