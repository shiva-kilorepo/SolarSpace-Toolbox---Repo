########################################################################
"""PILE NORTHING ADJUST TO PLANE OF ARRAY - SPECIFIC TO ARRAY

0.0.1 - 10/20/2021 - adapted from raster version of the script
1.0.0 - 5/17/2022 - Tested and deployed internally
1.1.0 - 1/9/2023 - Converted to PYT format, added extrapolation of graded surface and reveal check
1.2.0 - 1/24/2023 - Added custom calculations for ATI
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.2.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Testing"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import math

class ATINorthingAdjPOA(object):
    def __init__(self):
        self.label = "ATI - Pile Northing Adjust to Plane of Array"
        self.description = "Adjusts the northing of piles based on the slope of the plane of array for ATI trackers"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Civil Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Pile input feature class",
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
            displayName="Gearbox pile designation",
            name="gearboxSQL",
            datatype="GPSQLExpression",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param0.name]

        param4 = arcpy.Parameter(
            displayName="Height differential (bearing - gearbox)",
            name="heightDiff",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Graded elevation raster dataset",
            name="demGrade",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Adjusted pile output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7]
        
        return params
        
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[7].altered:
            parameters[7].value = "pileAdj"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        pilesInput = parameters[0].valueAsText # Original pile locations, point feature class; row_ID and a field designating the pile type (ie, motor/gearbox/other) must also be present
        row_ID = parameters[1].valueAsText # Unique row ID field in pilesInput and gearboxPiles
        gearboxSQL = parameters[2].valueAsText # Field that contains gearbox/motor designation
        poaField = parameters[3].valueAsText # Field designating the plane of array value
        heightDiff = parameters[4].valueAsText
        demExist = parameters[5].valueAsText
        demGrade = parameters[6].valueAsText
        pileOutput = parameters[7].valueAsText 

        # Define spatial reference
        spatialRef = arcpy.Describe(pilesInput).spatialReference

        pilesOptOutName = os.path.basename(pileOutput)

        # Create a working piles
        pilesAdj = arcpy.conversion.FeatureClassToFeatureClass(pilesInput,workspace,pilesOptOutName)
        gearboxPiles = arcpy.analysis.Select(pilesInput, "gearboxPiles", gearboxSQL)

        # Populate coordinates of pilesInput and gearboxPiles
        arcpy.management.AddXY(pilesAdj)
        arcpy.management.AddXY(gearboxPiles)

        # Alter fieldname for POINT_Y for gearboxPiles
        arcpy.management.AlterField(gearboxPiles, "POINT_Y", "northing_gear", "northing_gear")

        # Calculate the means of the northing and the base planes by row
        nMeanInput = str("POINT_Y MEAN;" + poaField + " MEAN")
        piles_northing_plane_mean = arcpy.analysis.Statistics(pilesAdj, "piles_northing_plane_mean", nMeanInput, row_ID)


        # Join back to the pile table
        meanPOAField = "MEAN_" + poaField
        nMeanResult = "MEAN_POINT_Y; " + meanPOAField
        arcpy.management.JoinField(pilesAdj, row_ID, piles_northing_plane_mean, row_ID, nMeanResult)

        # Calculate the delta between the northing and northing mean, and the deltat between the plane and plane mean
        arcpy.management.CalculateField(pilesAdj, "n_nbar", "!POINT_Y!-!MEAN_POINT_Y!", "PYTHON3", "", "DOUBLE")
        poa_poaBarCalc = str("!" + poaField + "! -!MEAN_" + poaField +"!")
        arcpy.management.CalculateField(pilesAdj, "poa_poaBar", poa_poaBarCalc, "PYTHON3", "", "DOUBLE")

        # Calculate the delta plane squared, and the product of the delta plane and the delta northing
        arcpy.management.CalculateField(pilesAdj, "dNorthXdpoa", "!n_nbar! * !poa_poaBar!", "PYTHON3","","DOUBLE")
        arcpy.management.CalculateField(pilesAdj, "dNorth_sq", "!n_nbar!*!n_nbar!", "PYTHON3","","DOUBLE")

        # Do summary statistics to get row sums of the delta plane squared and the product of the delta plane and the delta northing
        piles_delta_sum = arcpy.analysis.Statistics(pilesAdj, "piles_delta_sum", "dNorthXdpoa SUM;dNorth_sq SUM", row_ID)

        # Calculate the slope in radians
        arcpy.management.CalculateField(piles_delta_sum, "slopeRad", "math.atan(-!SUM_dNorthXdpoa!/!SUM_dNorth_sq!)", "PYTHON3","","DOUBLE")

        # Join the slope back to the piles
        arcpy.management.JoinField(pilesAdj, row_ID, piles_delta_sum, row_ID, "slopeRad")

        # Calculate the new northing based on the distance to the gearbox pile northing
        arcpy.management.JoinField(pilesAdj, row_ID, gearboxPiles, row_ID, "northing_gear")
        arcpy.management.CalculateField(pilesAdj, "distGear", "!POINT_Y! - !northing_gear!", "PYTHON3", "","DOUBLE")

        # Calculate the northing adjustment
        arcpy.management.CalculateField(pilesAdj, "deltaG", "math.sin(!slopeRad!) * "+heightDiff+"", "PYTHON3", "","DOUBLE")

        # Calculate d
        dadjCode = """        
def dAdjm(distGear, deltaG, slopeRad):
    if distGear == 0:
        return -deltaG
    else: 
        return distGear * math.cos(slopeRad)
"""
        arcpy.management.CalculateField(pilesAdj, "dadj", "dAdjm(!distGear!, !deltaG!, !slopeRad!)", "PYTHON3", dadjCode,"DOUBLE")

        # Calculate the new northing
        arcpy.management.CalculateField(pilesAdj, "northing_adj_ATI", "!POINT_Y! + !dadj! - !distGear!", "PYTHON3", "","DOUBLE")

        # Calculate the adjustment distance for checking
        arcpy.management.CalculateField(pilesAdj, "adjDist", "!northing_adj_ATI! - !POINT_Y!", "PYTHON3", "","DOUBLE")

        aprxMap.addDataFromPath(pilesAdj)

        # The gearbox adjustment needs to be opposite sign of the slope

        return