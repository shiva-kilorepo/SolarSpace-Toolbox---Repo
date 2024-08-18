########################################################################
"""ADJUST ADJACENT PLANES OF ARRAY NORTH-SOUTH BASED ON A MAXIMUM DELTA

Description: Adjusts adjacent plane of arrays for adacent rows north-south based on a maximum delta between the planes of array
Revision log
0.0.1 - 12/15/2021 - Initial scripting
1.0.0 - 12/05/2023 - Converted to Python toolbox
1.0.1 - 12/06/2023 - Fixed issue with tool not running in ArcPro due to MEAN_TOP_elv_orig field name not being valid

"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = "John Williamson"
__version__     = "1.0.0"
__ArcVersion__  = "ArcPro 3.1.3"
__maintainer__  = "Matthew Gagne"
__status__      = "Deployed"

# Load modules 
import arcpy
from arcpy import env
class maxPOADeltaNS(object):
    def __init__(self):
        self.label = "Adjust Adjacent Planes of Array N-S Based on a Maximum Delta"
        self.description = "Adjusts the plane of array and grading based on the latitude and the planes of array derived from the standard grading process"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"
        
    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
            displayName="Input elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Graded elevation raster dataset",
            name="demGrade",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="Tracker rows input feature class",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param2.name]

        param4 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param4.filter.list = ["Point"]
        
        param5 = arcpy.Parameter(
            displayName="Unique plane of array field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.parameterDependencies = [param4.name]

        param6 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        
        param7 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        
        param8 = arcpy.Parameter(
            displayName="Maximum delta plane of array",
            name="maxDelta_POA",
            datatype="Double",
            parameterType="Required",
            direction="Input")
        
        param9 = arcpy.Parameter(
            displayName="Pile output feature class",
            name="piles_out",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
                
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
    def execute(self, parameters, messages):
        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap
        workspace = arcpy.env.workspace

        demExist = parameters[0].valueAsText
        demGrade = parameters[1].valueAsText
        rowsInput = parameters[2].valueAsText
        row_ID = parameters[3].valueAsText
        pilesInput = parameters[4].valueAsText
        poaField = parameters[5].valueAsText
        minReveal = parameters[6].valueAsText
        maxReveal = parameters[7].valueAsText
        maxDelta_POA = parameters[8].valueAsText
        piles_out = parameters[9].valueAsText

        # Calculate north-south plane of array slope
        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

        # Add xy coordinates - will overwrite if already present
        arcpy.management.AddXY(piles_working)

        # Change poaField to TOP_elv_orig
        arcpy.AddMessage(f'poaField = {poaField}')
        arcpy.management.AlterField(piles_working, poaField, "TOP_elv_orig")
        poaField = "TOP_elv_orig"

        # Summary Statistics by row_ID to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
        coorStatsInput = [[poaField, "MEAN"], ["POINT_Y", "MEAN"]]
        coorStats = arcpy.analysis.Statistics(piles_working, "coorStats", coorStatsInput, row_ID)
        
        # # this will print the field names of coorStats
        # field_names = [f.name for f in arcpy.ListFields(coorStats)]
        # arcpy.AddMessage(f"Fields in coorStats: {field_names}")
        
        # Check if MEAN_{poaField} already exists if not create it
        # field_names = [f.name for f in arcpy.ListFields(piles_working)]
        # arcpy.AddMessage(f"Fields in piles_working: {field_names}")
        # if f'MEAN_{poaField}' not in field_names:
        #     arcpy.management.AddField(piles_working, f'MEAN_{poaField}', "DOUBLE")
        # else:
        #     arcpy.AddMessage(f'MEAN_{poaField} already exists')
        #     arcpy.management.AlterField(piles_working, f'MEAN_{poaField}', 'MEAN_TOP_elv_orig')
        
        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(piles_working, row_ID, coorStats, row_ID, ["MEAN_TOP_elv_orig", "MEAN_POINT_Y"])
        
        # Change the name of the mean of the plane of array to MEAN_TOP_elv_orig
        #arcpy.management.AlterField(piles_working, "MEAN_TOP_elv", "MEAN_TOP_elv_orig")
        
        # # list the fields in piles_working
        # field_names = [f.name for f in arcpy.ListFields(piles_working)]
        # arcpy.AddMessage(f"Fields in piles_working: {field_names}")
        
        # Calculate zy_bar, y_ybar_sq
        arcpy.AddMessage(f'Calculating zy_bar and y_ybar_sq')
        arcpy.management.CalculateField(piles_working, "zy_bar","(!TOP_elv_orig! + !MEAN_TOP_elv_orig!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(piles_working, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStats = arcpy.analysis.Statistics(piles_working, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStats, "nsSlope", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

        # Join slope to piles_working
        arcpy.AddMessage(f'Joining slope to piles_working')
        arcpy.management.JoinField(piles_working, row_ID, sumStats, row_ID, ["nsSlope"])

        # Find the intercept
        arcpy.management.CalculateField(piles_working, "bInit", "!TOP_elv_orig! - !nsSlope! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        endPointStats = arcpy.analysis.Statistics(piles_working, "endPointStats", [["bInit", "MEAN"],["nsSlope", "MEAN"]], row_ID)

        rowEndPoints = arcpy.management.CreateFeatureclass(workspace, "rowEndPoints", "POINT", "#", "DISABLED", "DISABLED", rowsInput)

        arcpy.AddField_management(rowEndPoints, "PolygonOID", "LONG")
        arcpy.AddField_management(rowEndPoints, "Position", "TEXT")

        result = arcpy.GetCount_management(rowsInput)
        count = int(result.getOutput(0))

        insert_cursor = arcpy.da.InsertCursor(rowEndPoints, ["SHAPE@", "PolygonOID", "Position"])
        search_cursor = arcpy.da.SearchCursor(rowsInput, ["SHAPE@", "OID@"])

        arcpy.AddMessage(f'Calculating row end points')
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

            north_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(nw_X, nw_Y), arcpy.Point(ne_X, ne_Y)]))
            south_bound_line = arcpy.Polyline(arcpy.Array([arcpy.Point(sw_X, sw_Y), arcpy.Point(se_X, se_Y)]))

            north_row_end = north_bound_line.positionAlongLine(0.5, True)
            south_row_end = south_bound_line.positionAlongLine(0.5, True)

            insert_cursor.insertRow((north_row_end, polygon_oid, "N"))
            insert_cursor.insertRow((south_row_end, polygon_oid, "S"))

        del insert_cursor
        del search_cursor

        arcpy.management.JoinField(rowEndPoints, "PolygonOID", endPointStats, "OBJECTID", [[row_ID],["MEAN_nsSlope"],["MEAN_bInit"]])

        arcpy.management.AddXY(rowEndPoints)

        arcpy.management.CalculateField(rowEndPoints, "poaPlaneDev", "!MEAN_nsSlope! * !POINT_Y! + !MEAN_bInit!", "PYTHON3", "", "DOUBLE")

        # Extract the existing elevation and graded elevation
        arcpy.sa.ExtractMultiValuesToPoints(rowEndPoints, [[demExist,'demExist'],[demGrade,'demGrade']],'BILINEAR')

        # Find the nearest POA and calculate the delta
        end_points_near = arcpy.analysis.GenerateNearTable(rowEndPoints, rowEndPoints, "end_points_near", "12 Feet", "NO_LOCATION", "NO_ANGLE", "CLOSEST", 0, "PLANAR")

        arcpy.management.JoinField(rowEndPoints, "OBJECTID", end_points_near, "IN_FID", "NEAR_FID; NEAR_DIST")
        join_table = arcpy.conversion.FeatureClassToFeatureClass(rowEndPoints, workspace, "join_table")
        arcpy.management.JoinField(rowEndPoints, "NEAR_FID", join_table, "OBJECTID", "poaPlaneDev")

        arcpy.management.AlterField(rowEndPoints, 'poaPlaneDev_1', 'poaNear', '', '', 8, 'NULLABLE', 'CLEAR_ALIAS')
        arcpy.management.CalculateField(rowEndPoints, "delta_poa", "!poaNear! - !poaPlaneDev!", "PYTHON3", '', "DOUBLE")

        # Adjust the poa at points that are over the delta limit
        poaAdj_code = """
def poaAdj(poa, poaNear, maxDelta):
    if abs(poa - poaNear) > maxDelta:
        if poa>poaNear:
            return poa -  ((poa - poaNear) - maxDelta) / 2
        if poa<poaNear:
            return poa -  ((poa - poaNear) + maxDelta) / 2
                
        else:
            return None
"""
        arcpy.management.CalculateField(rowEndPoints, "poaAdj", "poaAdj(!poaPlaneDev!, !poaNear!, "+maxDelta_POA+")", "PYTHON3", poaAdj_code, "DOUBLE")

        arcpy.AddMessage(f'Selecting rows to be modified')
        modRowEnds = arcpy.analysis.Select(rowEndPoints, "modRowEnds", "poaAdj IS NOT NULL")
        rowsMod = arcpy.management.SelectLayerByLocation(rowsInput, "INTERSECT", modRowEnds, None, "NEW_SELECTION", "NOT_INVERT")
        modRowEndsNS = arcpy.management.SelectLayerByLocation(rowEndPoints, "INTERSECT", rowsMod, None, "NEW_SELECTION", "NOT_INVERT")

        poaNull_code = """
def poaNull(poa, poaAdj):
    if poaAdj == None:
        return poa
    else:
        return poaAdj
"""
        arcpy.AddMessage(f'Calculating plane of array at row ends')
        arcpy.management.CalculateField(modRowEndsNS, "poaAdj","poaNull(!poaPlaneDev!,!poaAdj!)", "PYTHON3", poaNull_code)

        # Calculate the slope and intercept of the new POA using both end points
        endStats = arcpy.analysis.Statistics(modRowEndsNS, "endStats", [["poaAdj", "MEAN"], ["POINT_Y", "MEAN"]], row_ID)

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(modRowEndsNS, row_ID, endStats, row_ID, ["MEAN_poaAdj", "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(modRowEndsNS, "zy_bar","(!poaAdj! + !MEAN_poaAdj!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(modRowEndsNS, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStatsEnd = arcpy.analysis.Statistics(modRowEndsNS, "sumStatsEnd", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStatsEnd, "nsSlopeNew", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

        # Join slope to piles_working
        arcpy.management.JoinField(modRowEndsNS, row_ID, sumStatsEnd, row_ID, ["nsSlopeNew"])

        # Find the intercept
        arcpy.AddMessage(f'Finding intercept')
        arcpy.management.CalculateField(modRowEndsNS, "bInitNew", "!poaAdj! - !nsSlopeNew! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        endPointStatsNew = arcpy.analysis.Statistics(modRowEndsNS, "endPointStatsNew", [["bInitNew", "MEAN"],["nsSlopeNew", "MEAN"]], row_ID)

        pilesMod = arcpy.management.SelectLayerByLocation(piles_working, "INTERSECT", rowsMod, None, "NEW_SELECTION", "NOT_INVERT")

        arcpy.AddMessage(f'Joining slope and intercept to piles')
        # Join the slope and intercept to the piles
        arcpy.management.JoinField(pilesMod, row_ID, endPointStatsNew, row_ID, [["MEAN_nsSlopeNew"], ["MEAN_bInitNew"]])

        arcpy.AddMessage(f'Calculating new plane of array')
        # Calculate the new POA for each pile point
        arcpy.management.CalculateField(pilesMod, "poaAdj", "!MEAN_nsSlopeNew! * !POINT_Y! + !MEAN_bInitNew!", "PYTHON3", "", "DOUBLE")

        # Calculate the new reveal and grading for each pile point
        gradeAdjPiles_code = """
def gradeAdjPiles(demExist, poaAdj, minReveal, maxReveal):
    if (poaAdj - demExist) > maxReveal:
        return poaAdj - maxReveal
    if (poaAdj - demExist) < minReveal:
        return poaAdj - minReveal
    else:
        return demExist
"""

        arcpy.AddMessage(f'Calculating new pile elevations')
        arcpy.management.CalculateField(pilesMod, "gradeAdj", "gradeAdjPiles(!demExist!, !poaAdj!, "+minReveal+", "+maxReveal+")", "PYTHON3", gradeAdjPiles_code, "DOUBLE")

        # Merge with non-modified piles
        arcpy.AddMessage(f'Merging modified and non-modified piles')
        pilesNoMod = arcpy.management.SelectLayerByLocation(piles_working, "INTERSECT", rowsMod, None, "NEW_SELECTION", "INVERT")
        pilesOutput = arcpy.management.Merge([[pilesNoMod],[pilesMod]], piles_out)

        Null_code = """
def NullOut(poa, poaAdj):
    if poaAdj == None:
        return poa
    else:
        return poaAdj
"""
        arcpy.AddMessage(f'Calculating adjusted plane of array')
        arcpy.management.CalculateField(pilesOutput, "poaAdj","NullOut(!TOP_elv_orig!,!poaAdj!)", "PYTHON3", Null_code)

        NullGrade_code = """
def NullGradeOut(demGrade, gradeAdj):
    if gradeAdj == None:
        return demGrade
    else:
        return gradeAdj
"""
        arcpy.AddMessage(f'Calculating adjusted grading')
        arcpy.management.CalculateField(pilesOutput, "gradeAdj","NullGradeOut(!demGrade!,!gradeAdj!)", "PYTHON3", NullGrade_code)

        arcpy.AddMessage(f'Calculating adjusted reveal')
        arcpy.management.CalculateField(pilesOutput, "revAdj", "!poaAdj! - !gradeAdj!", "PYTHON3", "", "DOUBLE")
        
        arcpy.AddMessage(f'Calculating adjusted cut/fill')
        arcpy.management.CalculateField(pilesOutput, "cutFillAdj", "!gradeAdj! - !demExist!", "PYTHON3", "", "DOUBLE")
        
        return

        

