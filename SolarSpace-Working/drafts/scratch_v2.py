import pandas as pd
import numpy as np
import os
import openpyxl

# PURPOSE: direct 1 to 1 conversion of xlsx to csv

# set input and output paths
input_xlsx = r"M:\Clients\KWRE\Shallow Basket\2 Execution\6 Draft Deliverables\20240216 Shallow Basket Pile Table for BOM 90% w PCS block w client facing table V4.3 recheck.xlsx"
output_csv = r"M:\Clients\KWRE\Shallow Basket\2 Execution\3 GIS\Shallow Basket 2024 - 100% r2 Pile Maps\Shallow Basket - Pile Table for Maps 240223.csv"

# read xlsx
df = pd.read_excel(input_xlsx)

# on POINT_Y Adjusted column if value contains str ' remove it and convert to float
#df['POINT_Y Adjusted'] = df['POINT_Y Adjusted'].str.replace("'", "")

# change column data type to float
#df['POINT_Y Adjusted'] = df['POINT_Y Adjusted'].astype(float)

# write csv
df.to_csv(output_csv, index=False)
print(f"Conversion complete: {output_csv}")


#######
import arcpy
import os
from arcpy.sa import *


# PURPOSE: to generate grading bounds from two input rasters

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput=True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

gdb = r'M:\Clients\Affordable Solar aka GridWorks\NM Community Solar\Projects\ASG-4\2 Execution\3 GIS\ASG-4 Solar.gdb'
demExist = os.path.join(gdb, "demExist_1130")
demGrade = os.path.join(gdb, "demGrade_r_2ft_0226")
pilesInput = os.path.join(gdb, "pilesGrade_2ft_0226")

gradeBoundsOut = os.path.join(gdb, "gradeBounds_r_2ft_0226")

#cutRaster = os.path.join(gdb, "Cut_demGrade_1ft")
#fillRaster = os.path.join(gdb, "Fill_demGrade_1ft")

spatialRef = arcpy.Describe(demExist).spatialReference
gridRes = arcpy.Describe(demExist).meanCellWidth
arcpy.env.snapRaster = demExist
mapUnits = spatialRef.linearUnitName

# create pilesWorking
piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "piles_working")

# Subtract the existing elevation from the graded elevation
cutFill = arcpy.sa.Minus(demGrade,demExist)

arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[demGrade,"demGrade_temp"],[cutFill, 'cutFill_temp']], 'BILINEAR')

piles_graded_pre = arcpy.analysis.Select(piles_working, 'piles_graded_pre', 'cutFill_temp < -0.083 OR cutFill_temp > 0.083' )

# Reclassify cut-fill raster using tolerance
reclass_code = RemapRange([[-300,-1*float(.083), 1],[-1*float(.083), float(.083), 0],[float(.083), 300, 2]])
cutFill_reclass = arcpy.sa.Reclassify(cutFill, "VALUE", reclass_code, "DATA")
reclass_poly = arcpy.conversion.RasterToPolygon(cutFill_reclass, "cutFill_poly", "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None)
grade_area = arcpy.analysis.Select(reclass_poly, "grade_area", "gridcode <> 0")

# Select areas that intersect piles that are graded
grade_intersect = arcpy.management.SelectLayerByLocation(grade_area, 'INTERSECT', piles_graded_pre)
grade_area_rows = arcpy.conversion.FeatureClassToFeatureClass(grade_intersect, workspace, 'grade_area_rows')

# Buffer the graded areas by 5 feet close small holes and merge areas within 10 feet of each other
hole_close_buffer = "10 Feet"
grade_area_rows_buff = arcpy.analysis.PairwiseBuffer(grade_area_rows, 'grade_area_rows_buff', hole_close_buffer, "ALL")

# Invert the buffer to just inside the graded area to eliminate small areas
buffer_in = "-9 Feet"
bounds_invert = arcpy.analysis.PairwiseBuffer(grade_area_rows_buff, 'bounds_invert', buffer_in, "ALL")

# Extend the graded areas to 2 the raster resolution outside of the graded areas to join close areas  
bounds_extend = "3 Feet"

grade_bounds_pre = arcpy.analysis.PairwiseBuffer(bounds_invert, "grade_bounds_pre", bounds_extend, "ALL")

if gridRes > 2:
    simplifyFactor = 1
else:
    simplifyFactor = gridRes/2

#        if xyzUnit == "Foot":
simpInput = str(simplifyFactor) + " Feet"
#        else:
#            simpInput = str(simplifyFactor) + " Meter"

gradeBoundsName = os.path.basename(gradeBoundsOut)

grade_bounds = arcpy.cartography.SimplifyPolygon(grade_bounds_pre, gradeBoundsName, "WEIGHTED_AREA", simpInput, "0 SquareFeet", "RESOLVE_ERRORS", "KEEP_COLLAPSED_POINTS", None)

# Clean up
arcpy.management.Delete(grade_area)
arcpy.management.Delete(grade_area_rows)
arcpy.management.Delete(grade_area_rows_buff)
arcpy.management.Delete(bounds_invert)
arcpy.management.Delete(grade_bounds_pre)
arcpy.management.Delete(piles_working)
arcpy.management.Delete(piles_graded_pre)
arcpy.management.Delete('demGrade_temp')
arcpy.management.Delete('cutFill_temp')
arcpy.management.Delete('cutFill_poly')
arcpy.management.Delete('cutFill')
arcpy.management.Delete('cutFill_reclass')


print("Grading bounds complete")

#-----
# PURPOSE: to generate a raster from a feature class

import os
import requests
import arcpy

# Function to construct the OpenTopography API endpoint with parameters
def get_opentopography_dem(bbox):
    base_url = "https://portal.opentopography.org/API/globaldem"
    params = {
        'demtype': 'SRTMGL1',  # Specify the DEM type, e.g., SRTMGL1
        'south': bbox[1],      # Minimum latitude
        'north': bbox[3],      # Maximum latitude
        'west': bbox[0],       # Minimum longitude
        'east': bbox[2],       # Maximum longitude
        'outputFormat': 'gtiff'  # Output format, here GeoTIFF
    }
    
    # Send the request to OpenTopography
    response = requests.get(base_url, params=params)
    if response.ok:
        return response.content
    else:
        response.raise_for_status()
        print("Failed to retrieve DEM from OpenTopography")

# Example usage in an arcpy script
def retrieve_and_process_dem(project_area_feature_class):
    try:
        # Get the bounding box from the feature class
        desc = arcpy.Describe(project_area_feature_class)
        extent = desc.extent
        bbox = (extent.XMin, extent.YMin, extent.XMax, extent.YMax)
        
        # Request the DEM data from OpenTopography
        print("Requesting DEM from OpenTopography...")
        dem_data = get_opentopography_dem(bbox)
        
        # Save the DEM data to a file
        output_path = r"C:\Users\znordquist\Desktop\Testing\dem.tif"  # Provide a path to save the DEM
        with open(output_path, 'wb') as f:
            f.write(dem_data)
        
        print(f"DEM saved to {output_path}")
        
    except Exception as e:
        arcpy.AddError(f"Failed to retrieve DEM from OpenTopography: {e}")

# Call the function with the path to your input feature class
gdb = r'C:\Users\znordquist\Documents\ArcGIS\Projects\SolarSpace - Testing Env\SolarSpace - Testing Env.gdb'
input_project_area = os.path.join(gdb,'Tester')  
retrieve_and_process_dem(input_project_area)

#------------------------------------------------------------------------------------------------------------

# Test 3
# PURPOSE: to select features from a feature class based on a field value

import arcpy
import os

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput=True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

gdb = r'C:\Users\znordquist\Documents\ArcGIS\Projects\SolarSpace - Testing Env\SolarSpace - Testing Env.gdb'
input_fc = os.path.join(gdb, "prelimLayout")
output_fc = os.path.join(gdb, "output_rows")
