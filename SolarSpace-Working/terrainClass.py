########################################################################
"""TERRAIN CLASSIFICATION 

Revision log
0.0.1 - 04/19/2024 - Initial scripting
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
__license__     = "Internal"
__ArcVersion__  = "ArcPro 3.1.0"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist", "Liza Flowers"]
__status__      = "Testing"

import arcpy
import math
from arcpy.sa import *
import os
import sys

class terrainClass(object):
    def __init__(self):
        self.label = "Terrain Classification"
        self.description = "Classifies the complexity of the terrain based on slope and elevation variation"
        self.canRunInBackground = False
        self.category = "Site Suitability\Terrain Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input elevation raster",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Area of interest",
            name="aoi",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Polygon"]

        param2 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Terrain classification summary table",
            name="terClassOutput",
            datatype="DETable",
            parameterType="Optional",
            direction="Output")

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
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        demInput        = parameters[0].valueAsText
        aoi             = parameters[1].valueAsText
        xyzUnit         = parameters[2].valueAsText
        terClassOutput  = parameters[3].valueAsText

        # Set the DEM as the snap raster and reference for grid resolution and spatial reference
        arcpy.env.snapRaster = demInput

        # Clip the raster to the project area
        aoi_buffer = arcpy.analysis.PairwiseBuffer(aoi, "grade_bounds_pre", "100 Feet", "ALL")
        demClip = arcpy.management.Clip(demInput, "", 'in_memory\demClip', aoi_buffer, "", "ClippingGeometry")

        # Take the focal statistics mean and standard deviation of the raster with a rectangale of 30 ft
        elv_STD = arcpy.sa.FocalStatistics(demClip, "Rectangle 30 30 MAP", "STD", "DATA")
        elv_mean = arcpy.sa.FocalStatistics(demClip, "Rectangle 30 30 MAP", "MEAN", "DATA")

        # Subtract the elevation from the mean
        dem_mean = arcpy.sa.Minus(demClip, elv_mean)

        # Divide by the standard deviation to get the z score
        z_score = arcpy.sa.Divide(dem_mean, elv_STD)

        # Clip to area of interest
        z_score_aoi = arcpy.management.Clip(z_score, "", 'in_memory\z_score_aoi', aoi, "", "ClippingGeometry")

        # Reclassify as 0, 1, 2, 3, 4
        z_score_classify = arcpy.sa.Reclassify(z_score_aoi, "VALUE", "-100 -4 4;-4 -3 3;-3 -2 2;-2 -1 1;-1 1 0;1 2 1;2 3 2;3 4 3;4 100 4", "DATA")
        
        # Find the percentage of the site that is 1 STD, 2, STD, 3, STD, 4 STD from the mean and calculate the terrain score
        max_area = arcpy.analysis.Statistics(z_score_classify, "max_area", "Count SUM")
        arcpy.management.CalculateField(z_score_classify, "joinField", "1", "PYTHON3", "", "LONG")
        arcpy.management.JoinField(z_score_classify, "joinField", max_area, "OBJECTID", "SUM_Count")
        arcpy.management.CalculateField(z_score_classify, "terrain_score", "!Count!/!SUM_Count! * !Value! * 100", "PYTHON3", "", "FLOAT")
        terrain_var_score = arcpy.analysis.Statistics(z_score_classify, terClassOutput, "terrain_score SUM")

        # FIND PERCENTAGE OF SITE THAT IS > 20%, 15%, 10%, 5% SLOPE
        slope_site = arcpy.sa.SurfaceParameters(elv_mean,"SLOPE","QUADRATIC","","FIXED_NEIGHBORHOOD",xyzUnit,"PERCENT_RISE","","",aoi)

        # Reclassify as 0, 1, 2, 3, 4
        slope_classify = arcpy.sa.Reclassify(slope_site, "VALUE", "0 5 0;5 10 1; 10 15 2 ;15 20 3 ;20 4000 4", "DATA")

        # Find the percentage of the site that is 1 STD, 2, STD, 3, STD, 4 STD from the mean and calculate the terrain score
        arcpy.management.CalculateField(slope_classify, "joinField", "1", "PYTHON3", "", "LONG")
        arcpy.management.JoinField(slope_classify, "joinField", max_area, "OBJECTID", "SUM_Count")
        arcpy.management.CalculateField(slope_classify, "slope_score", "!Count!/!SUM_Count! * !Value! * 100", "PYTHON3", "", "FLOAT")
        slope_score = arcpy.analysis.Statistics(slope_classify, "slope_score", "slope_score SUM")

        arcpy.management.JoinField(terClassOutput, "OBJECTID", slope_score, "OBJECTID", "SUM_slope_score")

        aprxMap.addDataFromPath(terClassOutput)

        return
