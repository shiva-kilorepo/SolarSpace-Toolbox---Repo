########################################################################
"""CREATE SAMPLE PILES 


Description: creates sample piles within tracker rows for use with grading

Revision log
0.0.1 - 2/22/2022 - initial coding
0.0.2 - 3/1/2022 - debugging and putting into KiloNewton coding format
1.0.0 - 4/2/2022 - Updated output parameters
1.0.1 - 8/8/2022 - Fixed issue with random piles due to subdivide
1.1.0 - 2/16/2024 - Added fixWrongPiles function to remove any piles with row ID that does not match the row ID of the row it is in
                    Added the ability to add pile location to output sample piles

FUTURE UPDATES: ALLOW FOR SPECIFIC PILE LOCATIONS - BASED ON MOTOR? CENTER? END?
ADD PILE NUMBER NORTH-SOUTH
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.1.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import os.path
import sys
import math

import os
import pandas as pd
import numpy as np
from arcgis.features import GeoAccessor, GeoSeriesAccessor

class SamplePiles(object):
    def __init__(self):
        self.label = "Create Sample Piles for Tracker Rows"
        self.description = "Creates sample piles for tracker rows"
        self.canRunInBackground = False
        self.category = "Site Design\Layout Creation"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Tracker Rows",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Piles per Row",
            name="pilesPerRow",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Pile Output Name",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        
        param3 = arcpy.Parameter(
            displayName="Output Pile Location Attribute?",
            name="pileLocationOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        params = [param0, param1, param2, param3]
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
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        rowsInput = parameters[0].valueAsText  # Rows as a polygon with a unique row ID
        pilesPerRow = parameters[1].value  # number of piles per row
        pileOutput = parameters[2].valueAsText  # Output pile feature class
        pileLocationOption = parameters[3].value  # Option to add pile location to the output feature class

        arcpy.SetProgressor('default', 'Determining the initial pile positions...')

        # Get the max length of the rows and define a distance to expand them by
        with arcpy.da.SearchCursor(rowsInput, 'Shape_Length') as cursor:
                maxLength = max(cursor)
        maxLength = float('.'.join(str(elem) for elem in maxLength))

        del cursor

        buffer_dist = math.floor(maxLength/2)/pilesPerRow/2 - 1

        buffer_dist = int(buffer_dist)

        # Expand the rows
        rowsExpand = arcpy.analysis.GraphicBuffer(rowsInput, "rowsExpand", buffer_dist, "SQUARE", "MITER", 10, "0 Feet")

        # Get the max area of the rows
        with arcpy.da.SearchCursor(rowsExpand, 'Shape_Area') as cursor:
                maxArea = max(cursor)
        maxArea = float('.'.join(str(elem) for elem in maxArea))

        del cursor

        area = int(maxArea/pilesPerRow)

        #Subdivide the rows
        rowsSubdivide = arcpy.management.SubdividePolygon(rowsExpand, r'in_memory\rowsSubdivide', 'EQUAL_AREAS', "", area, "", 0, 'STRIPS')

        #Turn the blocks into points
        pilesPoints = arcpy.management.FeatureToPoint(rowsSubdivide, r'in_memory\pilesPoints', 'CENTROID')

        # Select all that are within the rows
        piles_select = arcpy.management.SelectLayerByLocation(pilesPoints, "INTERSECT", rowsInput, None, "NEW_SELECTION", "NOT_INVERT")

        pileOutputName = os.path.basename(pileOutput)

        #Join the points to the rows
        pilesFinal = arcpy.conversion.FeatureClassToFeatureClass(piles_select, workspace, pileOutputName)

        # Clean up
        arcpy.management.Delete(rowsExpand)
        arcpy.DeleteField_management(pilesFinal, ['BUFF_DIST','ORIG_FID'])
        
        # run the fixWrongPiles function
        arcpy.SetProgressor('default', 'Fixing any wrong pile positions...')
        SamplePiles.fixWrongPiles(pilesFinal, rowsInput, pileOutputName, workspace)
        
        try:
            arcpy.DeleteField_management(pilesFinal, ['TARGET_FID'])
        except:
            pass

        if pileLocationOption == True:
            # Add the pile location to the output feature class
            arcpy.SetProgressor('default', 'Adding pile location to the output feature class...')
            SamplePiles.addPileLocation(pilesFinal, pileOutputName, workspace)
        else:
            pass
        
        # Add the pile feature class to the map
        aprxMap.addDataFromPath(pilesFinal)

        arcpy.ResetProgressor()

        return
    
    def fixWrongPiles(pilesFinal, rowsInput, pileOutputName, workspace):
        """Removes any piles with row ID that does not match the row ID of the row it is in"""

        # delete piles outside of the rows
        # arcpy.management.SelectLayerByLocation(pilesFinal, "INTERSECT", rowsInput, None, "NEW_SELECTION", "INVERT")
        # arcpy.management.DeleteRows(pilesFinal)
        
        # Select all that are within the rows
        piles_select = arcpy.management.SelectLayerByLocation(pilesFinal, "INTERSECT", rowsInput, None, "NEW_SELECTION", "NOT_INVERT")
                
        # spatial join to get the row ID of the rows the piles are in
        arcpy.analysis.SpatialJoin(piles_select, rowsInput, r'in_memory\pilesJoin', "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
        
        # delete piles with wrong row ID
        piles_select = arcpy.management.SelectLayerByAttribute(r'in_memory\pilesJoin', "NEW_SELECTION", "Row_ID <> Row_ID_1","INVERT")
        #arcpy.management.DeleteRows(piles_select) 
        
        # print the number of featutes to be deleted
        #count = arcpy.management.GetCount(r'in_memory\pilesJoin')
        #arcpy.AddMessage(count)
        
        #arcpy.management.DeleteRows(r'in_memory\pilesJoin')
        
        # remove the join fields
        try:
            arcpy.management.DeleteField(r'in_memory\pilesJoin', ['Row_ID_1','BUFF_DIST','ORIG_FID','Join_Count','TARGET_FID'])
        except:
            pass
        
        # save the final pile feature class asd pilesFinal (not in memory)
        pilesFinal = arcpy.conversion.FeatureClassToFeatureClass(piles_select, workspace, pileOutputName)
        
        return pilesFinal
        
    def addPileLocation(pilesFinal, pileOutputName, workspace):
        """Adds the pile location to the output feature class"""
        input = os.path.join(workspace, 'pilesFocus')
        input = pilesFinal
        
        # get the contains and datatype of input
        desc = arcpy.Describe(input)
        dataType = desc.dataType
        
        arcpy.AddMessage(f'Input is a {dataType}; input is {input}')

        # get count of rows
        #pilesCount = arcpy.GetCount_management(input)
        #print(f'Number of piles: {pilesCount}')
        
        # add  XY coordinates to the input feature class
        arcpy.management.AddXY(input)

        # get the input shapefile's spatial reference
        input_sr = arcpy.Describe(input).spatialReference

        # Create an empty list to store the data
        data = []

        # Get the fields from the shapefile
        fields = [field.name for field in arcpy.ListFields(input)]

        # Create a search cursor
        with arcpy.da.SearchCursor(input, fields) as cursor:
            for row in cursor:
                data.append(list(row))
            
        # Create a pandas DataFrame from the list
        df = pd.DataFrame(data, columns = fields)

        # create new column 'pile_location' that is a unique identifier for each pile; generated sequentially from 1 to the number of piles in the row (by POINT_Y)

        # generate a df_list to store the dataframes for each row
        df_list = []

        # for each unique row ID in the dataframe generate a list of the unique pile locations starting from 1 at the point with the highest POINT_Y value
        # for each row ID in the dataframe
        for row_ID in df['row_ID'].unique():
            # filter the dataframe to only the rows with the row_ID
            df_row = df[df['row_ID'] == row_ID]
            # sort the dataframe by POINT_Y descending
            df_row = df_row.sort_values(by = 'POINT_Y', ascending = False)
            # create a new column that is a sequence from 1 to the number of piles in the row
            df_row['pile_location'] = range(1, len(df_row) + 1)
            # append the dataframe to the list
            df_list.append(df_row)

        # concatenate the list of dataframes into one dataframe
        df = pd.concat(df_list)

        # get wkid of input_sr
        wkid = input_sr.factoryCode
        
        # get the output location (pilesFinal) as a string
        pilesFinal = os.path.join(workspace, pileOutputName)

        # create a spatial dataframe from the pandas dataframe
        sedf = pd.DataFrame.spatial.from_xy(df=df, x_column='POINT_X', y_column='POINT_Y', sr=wkid)
        sedf.spatial.to_featureclass(location = pilesFinal, sanitize_columns = False)
                
        return pilesFinal