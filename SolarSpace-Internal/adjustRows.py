#########################################################################
""" Adjust Row by tilt percent or height

Revision log
0.0.1 - 12/14/2023 - Drafting  
0.1.0 - 1/16/2023 - Convert scrtipt to tool; added functionality
"""

__author__      = "Zane Nordquist"
__copyright__   = "Copyright 2024, KiloNewton, LLC"
__credits__     = ["Zane Nordquist", "John Williamson"]
__version__     = "0.1.0"
__license__     = "Internal"
__ArcVersion__  = "ArcPro 3.2.1"
__maintainer__  = ["Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import shapefile
import lxml.etree as ET
import math
import numpy as np
import pandas as pd

class adjustRows(object):

    def __init__(self):
        self.label = "Adjust Rows"
        self.description = "Tilts or adjusts the poa of input rows"
        self.alias = "adjustRows"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input row dataset",
            name="rowsInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Input pile dataset",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Point"]
        
        param2 = arcpy.Parameter(
            displayName="Vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Slope output units",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["Percent", "Degrees"]

        param4 = arcpy.Parameter(
            displayName="Northing field",
            name="northing",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.parameterDependencies = [param1.name]

        param5 = arcpy.Parameter(
            displayName="Easting field",
            name="easting",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.parameterDependencies = [param1.name]

        param6 = arcpy.Parameter(
            displayName="TOP Elev field to adjust",
            name="oldPOA",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        #param5.value = False
        param6.parameterDependencies = [param1.name]

        param7 = arcpy.Parameter(
            displayName="Direction to tilt rows",
            name="tilt_pin",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param7.filter.type = "ValueList"
        param7.filter.list = ["North", "South"]

        param8 = arcpy.Parameter(
            displayName="Height adjustment",
            name="heightAdj",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        
        param9 = arcpy.Parameter(
            displayName="Tilt adjustment",
            name="tilt_adj",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        
        param10 = arcpy.Parameter(
            displayName="Output full input dataset?",
            name="fullInputOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param10.value = False
        
        param11 = arcpy.Parameter(
            displayName="Output name",
            name="output_name",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Output")


        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            parameters[2].value = 'Foot'

        if not parameters[3].altered:
            parameters[3].value = 'Percent'
        
        if not parameters[4].altered:
            parameters[4].value = 'POINT_Y'
        
        if not parameters[5].altered:
            parameters[5].value = 'POINT_X'
        
        if not parameters[6].altered:
            parameters[6].value = 'TOP_elv'
            
        if not parameters[8].altered:
            parameters[8].value = 0.0
            
        if not parameters[9].altered:
            parameters[9].value = 0.0
        
        if not parameters[11].altered:
            parameters[11].value = 'piles_rowAdj'
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # if parameters[1].altered:
        #     if parameters[2].value == "Foot":
        #         if "Foot" not in arcpy.Describe(parameters[1].value).spatialReference.linearUnitName:
        #             parameters[2].setErrorMessage("Vertical and horizontal units do not match")
        #     if parameters[2].value == "Meter":
        #         if "Meter" not in arcpy.Describe(parameters[1].value).spatialReference.linearUnitName:
        #             parameters[2].setErrorMessage("Vertical and horizontal units do not match")
        #     else:
        #         parameters[2].clearMessage()
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        rowsInput = parameters[0].valueAsText  # Input rows dataset
        pilesInput = parameters[1].valueAsText  # Input piles dataset
        xyzUnit = parameters[2].valueAsText  # Foot or Meter
        slopeUnits = parameters[3].valueAsText  # Percent or Degrees
        northing = parameters[4].valueAsText  # Northing field
        easting = parameters[5].valueAsText  # Easting field
        oldPOA = parameters[6].valueAsText  # Old POA field
        tilt_pin = parameters[7].valueAsText  # North or South
        heightAdj = parameters[8].valueAsText  # Height adjustment
        tilt_adj = parameters[9].valueAsText  # Tilt adjustment
        fullInputOption = parameters[10].value # boolean to determine if the full input dataset is output
        output_name = parameters[11].valueAsText # Output name
        
        ### testing purposes ###
        #arcpy.AddMessage(f'fullInputOption: {fullInputOption}')
        
        # if slopeUnits is degrees, convert to percent
        if slopeUnits == 'Degrees':
            tilt_adj = math.tan(math.radians(tilt_adj)) * 100
            arcpy.AddMessage(f'Tilt percent: {tilt_adj}')
        
        # if there's a selection in the input rows, update the pile selection to match
        if arcpy.Describe(rowsInput).FIDSet:
            arcpy.SelectLayerByLocation_management(pilesInput, "INTERSECT", rowsInput)
            
        # Create list of selected object IDs
        desc = arcpy.Describe(pilesInput)
        selection_ids_string = desc.FIDSet.split(";")
        selection_ids = [int(id) for id in selection_ids_string if id]
        arcpy.AddMessage(f'# of piles to be adjusted: {len(selection_ids)}')
        
        # Clear selection
        arcpy.SelectLayerByAttribute_management(pilesInput, "CLEAR_SELECTION")
        
        # update data type for heightAdj and tilt_adj
        heightAdj = float(heightAdj)
        tilt_adj = float(tilt_adj)
        
        # get the input shapefile's spatial reference
        spatialRef = arcpy.Describe(pilesInput).spatialReference

        # set input variable
        input = pilesInput

        # Create an empty list to store the data
        data = []

        # Get the fields from the shapefile
        fields = [field.name for field in arcpy.ListFields(input)]

        # Create a search cursor
        try:
            with arcpy.da.SearchCursor(input, fields) as cursor:
                for row in cursor:
                    data.append(list(row))
                    
        except Exception as e:
            arcpy.AddError("Error while reading the input file: " + str(e))
            return

        # Create a pandas DataFrame from the list
        df_master = pd.DataFrame(data, columns = fields)
        if len(selection_ids) != 0:
            df_selected = df_master[df_master['OBJECTID'].isin(selection_ids)]
        else:
            arcpy.AddMessage('No piles selected; full input dataset will be output')
            df_selected = pd.DataFrame(data, columns = fields)
            return

        # Create a pandas dataframe & list outisde the list to store the data for each row
        df_adj = pd.DataFrame()
        df_list = []  

        # Filter to only rows with the row_ID
        #df = df[df_master['row_ID'] == row_ID]
        
        # get all the row_IDs from the input rows
        row_IDs = df_selected['row_ID'].unique()
        arcpy.AddMessage(f'Adjusting rows: {row_IDs}')
        
        arcpy.SetProgressor('default', 'Adjusting Rows & Piles...')

        # run main adjustment loop for each row_ID
        for row in row_IDs:
            df = df_selected[df_selected['row_ID'] == row]

            # add column to determine if the row is north or south tilt_pin ('Y' or 'N')
            # if tilt_pin is north then find the row with the highest northing and set that as the tilt pin row
            try:
                if tilt_pin == 'North':
                    df['tilt_pin'] = np.where(df[northing] == df[northing].max(), 'Y', 'N')
                elif tilt_pin == 'South':
                    df['tilt_pin'] = np.where(df[northing] == df[northing].min(), 'Y', 'N')
                else:
                    arcpy.AddError('Error: tilt_pin must be North or South')
            except Exception as e:
                arcpy.AddError("Error while creating tilt_pin column: " + str(e))
                return

            # add a column named findPin that is equal to the tilt_pin == 'Y' row's northing value
            df['findPin'] = df[df['tilt_pin'] == 'Y'][northing].values[0]
            #print (df[df['tilt_pin'] == 'Y'][northing].values[0])

            # calculate the length of the row
            row_length = df[northing].max() - df[northing].min()
            #print(row_length)

            # run row tilt adj % calculation
            rowTilt_adjPerc = 0
            ns_value = 0
            if tilt_pin == 'North':
                ns_value = -1
            else:
                ns_value = 1

            rowTilt_adjPerc = (tilt_adj / 100) * ns_value
            #print(rowTilt_adjPerc)

            # create new poa column
            # newPOA = (oldPOA + heightAdj + rowTilt_adjPerc) * (northering - findPin)
            df['newPOA'] = df[oldPOA] + heightAdj + rowTilt_adjPerc * (df[northing] - df['findPin'])

            # append the df to the df list
            df_list.append(df)

        # Concatenate all dataframes at once
        df_adj = pd.concat(df_list, ignore_index=True)

        #  remove the findPin, tilt_pin, columns
        df_adj = df_adj.drop(columns=['findPin', 'tilt_pin'])

        # if the fullInputOption is 'Yes' then add the add unadjusted rows to the df_adj
        arcpy.AddMessage(f'Full Input Option set to {fullInputOption}')
        if fullInputOption:
            arcpy.SetProgressor('default', 'Re-adding unselected data...')
            df_master['newPOA'] = df_master['TOP_elv']
            df_unadjusted = df_master[~df_master['row_ID'].isin(df_selected['row_ID'])]
            df_final = pd.concat([df_adj, df_unadjusted])
        else:
            df_final = df_adj

        #  remove the shape and OBJECTID columns
        try:
            df_cleaned = df_final.drop(columns=['Shape','OBJECTID'])
        except:
            arcpy.AddMessage('Shape and OBJECTID columns not found; duplicates in schema might occur')
            df_cleaned = df_final
            pass
        
        # Fillna with some appropriate defaults. Strings are filled with ""
        for column in df_cleaned.columns:
            if df_cleaned[column].dtype == np.int64:
                df_cleaned[column].fillna(0, inplace=True)
            elif df_cleaned[column].dtype == np.float64:
                df_cleaned[column].fillna(0.0, inplace=True)
            elif df_cleaned[column].dtype == np.object:  # Assuming the object type is a string
                df_cleaned[column].fillna('', inplace=True)
            # Add similar checks for other data types if needed
        arcpy.SetProgressor('default', 'Converting data to feature...')

        # Convert pandas DataFrame to a numpy structured array
        numpy_array = np.array(np.rec.fromrecords(df_cleaned.values))
        numpy_array.dtype.names = tuple(df_cleaned.columns)
        
        # check if the temp_table already exists and delete it if it does
        if arcpy.Exists(os.path.join(workspace, "temp_table")):
            arcpy.management.Delete(os.path.join(workspace, "temp_table"))

        # Convert the numpy array to an ArcGIS Table
        arcpy.da.NumPyArrayToTable(numpy_array, os.path.join(workspace, "temp_table"))
        
        arcpy.SetProgressor('default', 'Converting data to feature...')
        
        # Now 'temp_table' can be used as input in the XYTableToPoint function
        ## Use the df to update the input shapefile - using arcpy xy table to point
        arcpy.management.XYTableToPoint(os.path.join(workspace, "temp_table"), output_name, easting, northing, None, spatialRef)
        
        # Delete the temp_table
        arcpy.management.Delete(os.path.join(workspace, "temp_table"))
        
        arcpy.ResetProgressor()
        #arcpy.AddMessage("Rows and piles adjusted")
        
        aprxMap.addDataFromPath(output_name)
        
        return
