rowMidPoints = arcpy.management.CreateFeatureclass("in_memory", "rowMidPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)
arcpy.AddField_management(rowMidPoints, "PolygonOID", "LONG")
arcpy.AddField_management(rowMidPoints, "Position", "TEXT")

result = arcpy.GetCount_management(rowsInput)
count = int(result.getOutput(0))

insert_cursor = arcpy.da.InsertCursor(rowMidPoints, ["SHAPE@", "PolygonOID", "Position"])
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
        lowerLeft_distances[float(sw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
        lowerRight_distances[float(se_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
        upperLeft_distances[float(nw_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])
        upperRight_distances[float(ne_point.distanceTo(vertex_point))] = (vertex[0], vertex[1])

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

    sw_point = arcpy.PointGeometry(arcpy.Point(sw_X, sw_Y))
    se_point = arcpy.PointGeometry(arcpy.Point(se_X, se_Y))
    nw_point = arcpy.PointGeometry(arcpy.Point(nw_X, nw_Y))
    ne_point = arcpy.PointGeometry(arcpy.Point(ne_X, ne_Y))

    insert_cursor.insertRow((sw_point, polygon_oid, "SW"))
    insert_cursor.insertRow((se_point, polygon_oid, "SE"))
    insert_cursor.insertRow((nw_point, polygon_oid, "NW"))
    insert_cursor.insertRow((ne_point, polygon_oid, "NE"))

    north_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(nw_X, nw_Y), arcpy.Point(ne_X, ne_Y)]))
    south_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(sw_X, sw_Y), arcpy.Point(se_X, se_Y)]))

    north_row_end = north_bound_line.positionAlongLine(0.5, True)
    south_row_end = south_bound_line.positionAlongLine(0.5, True)

    insert_cursor.insertRow((north_point, polygon_oid, "N"))
    insert_cursor.insertRow((south_point, polygon_oid, "S"))

del insert_cursor
del search_cursor
