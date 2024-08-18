############################################################
"""REPROJECT AND RESAMPLE ELEVATION RASTER

Description: Tool that does the proper reprojection, unit conversion, and resampling of 3DEP (or other) elevation rasters

Revision log
0.0.1 - 11/04/2021 - Initial scripting
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
from arcpy.sa import *
from arcpy.ddd import *
import os.path
import sys

# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject('CURRENT')
aprxMap = aprx.activeMap

# Set parameters
demInput = 
outCS = 
inUnits = # Feet or Meters
outUnits = # Feet or Meters
resampleRaster = # Boolean option for resampling the raster
outGridRes = # Optional resampling
snapToRaster = # Boolean option for snapping to a raster in the workbook, only valid for resampling
snapRaster = 
demOutput = 

demCSconv = arcpy.management.ProjectRaster(demInput, "demCSconv", outCS, "BILINEAR")

if inUnits == "Feet" and outUnits == "Feet":
    demCSconv_out = demCSconv
if inUnits == "Meters" and outUnits == "Meters":
    demCSconv_out = demCSconv
if inUnits == "Meters" and outUnits == "Feet"
    demCSconv_out = out_raster = arcpy.sa.Times(demCSconv, 3.28084)
if inUnits == "Feet" and outUnits == "Meters"
    demCSconv_out = out_raster = arcpy.sa.Divide(demCSconv, 3.28084)

if resampleRaster == True:
    if snapToRaster == True:
        arcpy.env.snapRaster = snapRaster
        gridRes = outGridRes + " " + outGridRes
        demResample = arcpy.management.Resample(demCSconv_out, demOutput, "2 2", "BILINEAR")
    else:
        gridRes = outGridRes + " " + outGridRes
        demResample = arcpy.management.Resample(demCSconv_out, demOutput, "2 2", "BILINEAR")
if resampleRaster == False:
    demFinal = COPY?
    
# Clean up