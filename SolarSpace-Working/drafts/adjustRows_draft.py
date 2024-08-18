#########################################################################
""" Adjust Row by tilt percent or height

Revision log
0.0.1 - 11/14/2023 - Drafting  
"""

__author__      = "Zane Nordquist"
__copyright__   = "Copyright 2024, KiloNewton, LLC"
__credits__     = ["Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
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

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject("CURRENT")
aprxMap = aprx.activeMap

# Set input data
gdb = r'C:\Users\znordquist\Documents\ArcGIS\Projects\SolarSpace - Testing Env\SolarSpace - Testing Env.gdb'
input_rows = rf'{gdb}\rowsInput_focus_Ex'
input_piles = rf'{gdb}\pilesGraded_v1_2ft_focus_Ex'
row_IDs = [str(263),str(264)]
northing = 'POINT_Y'
easting = 'POINT_X'
method = 'Percent'
tilt_pin = 'South'
oldPOA = 'TOP_elv'
fullInputOption = 'Yes'

# Set input parameters
heightAdj = 2
tilt_adj = 5

# set input variable
input = input_piles

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
df_master = pd.DataFrame(data, columns = fields)

# Create a pandas dataframe & list outisde the list to store the data for each row
df_adj = pd.DataFrame()
df_list = []  

# Filter to only rows with the row_ID
#df = df[df_master['row_ID'] == row_ID]

for row in row_IDs:
    df = df_master[df_master['row_ID'] == row]

    # add column to determin if the row is north or south tilt_pin ('Y' or 'N')
    # if tilt_pin is north then find the row with the highest northing and set that as the tilt pin row
    if tilt_pin == 'North':
        df['tilt_pin'] = np.where(df[northing] == df[northing].max(), 'Y', 'N')
    elif tilt_pin == 'South':
        df['tilt_pin'] = np.where(df[northing] == df[northing].min(), 'Y', 'N')
    else:
        'Error: tilt_pin must be North or South'
        sys.exit()

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
if fullInputOption == 'Yes':
    # create newPOA column in the df_master and set it equal to the TOP_elv
    df_master['newPOA'] = df_master['TOP_elv']
    df_fullInput = df_master[df_master['row_ID'].isin(row_IDs) == False]
    df_adj = pd.concat([df_adj, df_fullInput], ignore_index=True)

#  remove the shape and OBJECTID columns
df_adj = df_adj.drop(columns=['Shape','OBJECTID'])

# Fillna with some appropriate defaults. Strings are filled with ""
df_cleaned = df_adj.fillna(value={"pile_ID": 0, "row_ID": "", "POINT_X": 0.0, "POINT_Y": 0.0, "demExist": 0.0, "demGrade": 0.0, "reveal": 0.0, "TOP_elv": 0.0, "cutFill": 0.0, "nsSlopePercPOA": 0.0, "trackerType": "", "pileType": "", "holePattern": "", "newPOA": 0.0})

# Convert pandas DataFrame to a numpy structured array
numpy_array = np.array(np.rec.fromrecords(df_cleaned.values))
numpy_array.dtype.names = tuple(df_cleaned.columns)

# Convert the numpy array to an ArcGIS Table
arcpy.da.NumPyArrayToTable(numpy_array, os.path.join(workspace, "temp_table"))

# Now 'temp_table' can be used as input in the XYTableToPoint function
## Use the df to update the input shapefile - using arcpy xy table to point
arcpy.management.XYTableToPoint(os.path.join(workspace, "temp_table"), f'{input}_rowAdj', easting, northing, None, input_sr)

# Delete the temp_table
arcpy.management.Delete(os.path.join(workspace, "temp_table"))
