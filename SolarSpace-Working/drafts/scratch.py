# import modules
import arcpy
import os
import sys
import pandas as pd
import numpy as np
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# find current project
gdb = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

input = os.path.join(gdb, 'pilesFocus')

# get count of rows
pilesCount = arcpy.GetCount_management(input)
print(f'Number of piles: {pilesCount}')

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

# create a spatial dataframe from the pandas dataframe
sedf = pd.DataFrame.spatial.from_xy(df=df, x_column='POINT_X', y_column='POINT_Y', sr=wkid)

sedf.spatial.to_featureclass(location = os.path.join(gdb, 'pilesFocus_pileLoc'), sanitize_columns = False)


# saving
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
        fullInputOption = parameters[10].valueAsText  # Yes or No
        output_name = parameters[11].valueAsText # Output name
        
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

        # Create a pandas dataframe & list outisde the list to store the data for each row
        df_adj = pd.DataFrame()
        df_list = []  

        # Filter to only rows with the row_ID
        #df = df[df_master['row_ID'] == row_ID]
        
        # get all the row_IDs from the input rows
        row_IDs = df_master['row_ID'].unique()
        arcpy.AddMessage(f'Adjusting rows: {row_IDs}')
        
        arcpy.SetProgressor('default', 'Adjusting Rows & Piles...')

        # run main adjustment loop for each row_ID
        for row in row_IDs:
            df = df_master[df_master['row_ID'] == row]

            # add column to determine if the row is north or south tilt_pin ('Y' or 'N')
            # if tilt_pin is north then find the row with the highest northing and set that as the tilt pin row
            if tilt_pin == 'North':
                df['tilt_pin'] = np.where(df[northing] == df[northing].max(), 'Y', 'N')
            elif tilt_pin == 'South':
                df['tilt_pin'] = np.where(df[northing] == df[northing].min(), 'Y', 'N')
            else:
                arcpy.AddError('Error: tilt_pin must be North or South')

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
        if fullInputOption == 'True':
            # clear the pilesInput variable's selection if it has one
            arcpy.SelectLayerByAttribute_management(pilesInput, "CLEAR_SELECTION")
            
            # create a df_fullInput that contains all the rows for the input shapefile post selection clear
            
            # set input variable
            input = pilesInput

            # Create an empty list to store the data
            data = []

            # Get the fields from the shapefile
            fields = [field.name for field in arcpy.ListFields(input)]

            # Create a search cursor
            with arcpy.da.SearchCursor(input, fields) as cursor:
                for row in cursor:
                    data.append(list(row))

            # Create a pandas DataFrame from the list
            df_master_clear = pd.DataFrame(data, columns = fields)
            
            # create newPOA column in the df_master and set it equal to the TOP_elv
            df_master_clear['newPOA'] = df_master_clear['TOP_elv']
            df_fullInput = df_master_clear[df_master_clear['row_ID'].isin(row_IDs) == False]
            df_adj = pd.concat([df_adj, df_fullInput], ignore_index=True)

        #  remove the shape and OBJECTID columns
        df_adj = df_adj.drop(columns=['Shape','OBJECTID'])

        # Fillna with some appropriate defaults. Strings are filled with ""
        df_cleaned = df_adj.fillna(value={"pile_ID": 0, "row_ID": "", "POINT_X": 0.0, "POINT_Y": 0.0, "demExist": 0.0, "demGrade": 0.0, "reveal": 0.0, "TOP_elv": 0.0, "cutFill": 0.0, "nsSlopePercPOA": 0.0, "trackerType": "", "pileType": "", "holePattern": "", "newPOA": 0.0})

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

workspace = r'C:\Users\znordquist\Documents\ArcGIS\Projects\SolarSpace - Testing Env\SolarSpace - Testing Env.gdb'
stringsOutput_pre = os.path.join(workspace, 'prelimLayout')
xyzUnit = 'FEET_US'
exclusionFeatureClass = os.path.join(workspace, 'mechExclusion')
exclusionRemovePercent = 50

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
    
removeExclusionRows(stringsOutput_pre, xyzUnit, workspace, exclusionFeatureClass, exclusionRemovePercent)