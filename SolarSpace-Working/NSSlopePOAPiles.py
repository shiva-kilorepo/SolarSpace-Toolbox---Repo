########################################################################
"""DERIVE NORTH-SOUTH SLOPE OF THE PLANE OF ARRAY FROM TOP OF PILE ELEVATIONS

Revision log
v0.0.1 - 9/3/2021 - Initial build
1.0.0 - 5/17/2022 - Tested and deployed

FUTURE UPDATES: APPEND TO ROWS AND SYMBOLIZE WITH LIMITS?
"""

__author__ =        "Matthew Gagne"
__copyright__ =     "Copyright 2023, KiloNewton, LLC"
__credits__ =       ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__ =       "1.0.0"
__license__ =       "Internal/Commercial"
__ArcVersion__ =    "ArcPro 3.0.3"
__maintainer__ =    ["Matthew Gagne", "Zane Nordquist"]
__status__ =        "Deployed"

import arcpy
import os.path
import sys
from arcpy.ddd import *

class NSSlopePiles(object):
    def __init__(self):
        self.label = "Derive North-South Plane of Array Slope from Piles"
        self.description = "Derives the north-south plane of array slope from piles with a top of pile elevation of array field"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Civil Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input pile layer",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Point"]

        param1 = arcpy.Parameter(
            displayName="Unique row ID field",
            name="row_ID",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param1.parameterDependencies = [param0.name]

        param2 = arcpy.Parameter(
            displayName="Top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Slope output measurement",
            name="slopeUnits",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["Percent", "Degrees"]

        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[3].altered:
            parameters[3].value = 'Percent'

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

        # Set parameters
        pilesInput = parameters[0].valueAsText  # Point locations for piles
        row_ID = parameters[1].valueAsText  # Array row unique ID, must be the same in rowsInput and pilesInput
        poaField = parameters[2].valueAsText  # Field that designates the plane of array
        slopeUnits = parameters[3].valueAsText

        arcpy.SetProgressor('default', 'Calculating the plane of array slope from the piles...')

        # Add xy coordinates - will overwrite if already present
        arcpy.management.AddXY(pilesInput)

        # Delete POINT_Z field - not needed
        arcpy.management.DeleteField(pilesInput, "POINT_Z")

        # Summary Statistics by row_ID to to get the mean of the plane of array and the mean of POINT_Y for each row and the count of piles for each row
        coorStatsInput = [[poaField, "MEAN"], ["POINT_Y", "MEAN"]]
        coorStats = arcpy.analysis.Statistics(pilesInput, "coorStats", coorStatsInput, row_ID)

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        coorStatsOutput = ["MEAN_" + poaField, "MEAN_POINT_Y"]
        arcpy.management.JoinField(pilesInput, row_ID, coorStats, row_ID, coorStatsOutput)

        # Calculate zy_bar, y_ybar_sq
        zy_bar_equation = "(!" + poaField + "! - !" + "MEAN_" + poaField + "!)" + "*" + "(!POINT_Y! - !MEAN_POINT_Y!)"
        arcpy.management.CalculateField(pilesInput, "zy_bar", zy_bar_equation, "PYTHON3", "", "DOUBLE")
        arcpy.management.CalculateField(pilesInput, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStats = arcpy.analysis.Statistics(pilesInput, "sumStats", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]], row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStats, "NS_slope_percent", "-100*!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3","", "DOUBLE")

        if slopeUnits == "Percent":
            # Join slope to pilesInput
            arcpy.management.JoinField(pilesInput, row_ID, sumStats, row_ID, ["NS_slope_percent"])
        else:
            arcpy.management.CalculateField(sumStats, "NS_slope_degrees", "math.degrees(math.atan(!NS_slope_percent!/100))", "PYTHON3", "", "DOUBLE")
            arcpy.management.JoinField(pilesInput, row_ID, sumStats, row_ID, ["NS_slope_degrees"])

        # Clean up
        arcpy.management.DeleteField(pilesInput, ["MEAN_POINT_Y", "MEAN_POINT_X", "MEAN_TOP_elv", "zy_bar", "y_ybar_sq"])

        arcpy.management.Delete("coorStats")
        arcpy.management.Delete("sumStats")

        return