############################################################
"""EXTRAPOLATE 3D PLANE OF ARRAY FROM PILES

Description: Extrapolates the plane of array from a pile layer

While this script can be used independently, it will be a foundation for many of the adjustment scripts upcoming

Revision log
0.0.1 - 11/07/2022 - Initial scripting
"""
__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2022, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
__license__     = "Testing"
__ArcVersion__  = "ArcPro 3.0.2"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Testing"

import arcpy

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

# Set parameters
rowsInput = r"C:\Users\MGagne\Documents\Clients\Luminace\GIS\Illinois 2.gdb\rowsInput_v3b"
row_ID = "row_ID"
pilesInput = r"C:\Users\MGagne\Documents\Clients\Luminace\GIS\Illinois 2.gdb\revised_piles_XYTableToPoint"
poaField = "TOP_elv"
endofRowPt_out = "eor_POA"

# Calculate north-south plane of array slope
piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

# Add xy coordinates - will overwrite if already present
arcpy.management.AddXY(piles_working)

# Change poaField to TOP_elv_orig
arcpy.management.AlterField(piles_working, poaField, "TOP_elv_orig")

# Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
coorStatsInput = [["TOP_elv_orig", "MEAN"], ["POINT_Y", "MEAN"]]
coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)

# Join the mean of the plane of array and MEAN_POINT_Y back to the piles
arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, ["MEAN_TOP_elv_orig", "MEAN_POINT_Y"])

# Calculate zy_bar, y_ybar_sq
arcpy.management.CalculateField(piles_working, "zy_bar","(!TOP_elv_orig! + !MEAN_TOP_elv_orig!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

# Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

# Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
arcpy.management.CalculateField(sumStats, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

# Join slope to piles_working
arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope"])

# Find the intercept
arcpy.management.CalculateField(piles_working, "bInit", "!TOP_elv_orig! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

endPointStats = arcpy.analysis.Statistics(piles_working, "endPointStats", [["bInit", "MEAN"],["nsSlope", "MEAN"]], row_ID)

rowCornerPoints = arcpy.management.CreateFeatureclass(workspace, "rowCornerPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)

arcpy.AddField_management(rowCornerPoints, "PolygonOID", "LONG")
arcpy.AddField_management(rowCornerPoints, "Position", "TEXT")

result = arcpy.GetCount_management(rowsInput)
count = int(result.getOutput(0))

insert_cursor = arcpy.da.InsertCursor(rowCornerPoints, ["SHAPE@", "PolygonOID", "Position"])
search_cursor = arcpy.da.SearchCursor(rowsInput, ["SHAPE@", "OID@"])

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


del insert_cursor
del search_cursor

arcpy.management.JoinField(rowCornerPoints, "PolygonOID", endPointStats, "OBJECTID", [[row_ID],["MEAN_nsSlope"],["MEAN_bInit"]])

arcpy.management.AddXY(rowCornerPoints)

arcpy.management.CalculateField(rowCornerPoints, "poaPlaneDev", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

# Add order field
codeblock_order = """
def ordPoint(pos):
    if pos == "NW":
        return 1
    if pos == "NE":
        return 2
    if pos == "SE":
        return 3
    else:
        return 4
"""

arcpy.management.CalculateField(rowCornerPoints, "ptOrder", "ordPoint(!Position!)", "PYTHON3", codeblock_order, "LONG")

bound3Dpoints = arcpy.ddd.FeatureTo3DByAttribute(rowCornerPoints, "bound3Dpoints", "poaPlaneDev")

lines3D = arcpy.management.PointsToLine(bound3Dpoints, "lines3D", row_ID, "ptOrder", "CLOSE")

poaOut = arcpy.management.FeatureToPolygon(lines3D, "poaOut")

