########################################################################
"""ADJUST PILE NORTHING TO PLANE OF ARRAY

0.0.1 - 10/20/2021 - adapted from raster version of the script
1.0.0 - 5/17/2022 - Tested and deployed internally
1.1.0 - 1/9/2023 - Converted to PYT format, added extrapolation of graded surface and reveal check
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.1.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *

class NorthingAdjPOA(object):
    def __init__(self):
        self.label = "Adjust Pile Northing to Plane of Array"
        self.description = "Adjusts the northing of piles based on the slope of the plane of array"
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
            displayName="Motor or gearbox pile designation",
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
            displayName="Existing elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Graded elevation raster dataset",
            name="demGrade",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Adjusted pile output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6]
        
        return params
        
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[6].altered:
            parameters[6].value = "pileAdj"

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
        pilesInput = parameters[0].valueAsText 
        row_ID = parameters[1].valueAsText # Unique row ID field in pilesInput and gearboxPiles
        gearboxSQL = parameters[2].valueAsText # Field that contains gearbox/motor designation
        poaField = parameters[3].valueAsText # Field designating the plane of array value
        demExist = parameters[4].valueAsText
        demGrade = parameters[5].valueAsText
        pileOutput = parameters[6].valueAsText 

        # Define spatial reference
        spatialRef = arcpy.Describe(pilesInput).spatialReference

        # Create a working piles
        pilesOriginal = arcpy.conversion.FeatureClassToFeatureClass(pilesInput,workspace,"pilesOriginal")
        gearboxPiles = arcpy.analysis.Select(pilesInput, "gearboxPiles", gearboxSQL)

        # Populate coordinates of pilesInput and gearboxPiles
        arcpy.management.AddXY(pilesOriginal)
        arcpy.management.AddXY(gearboxPiles)

        # Alter fieldname for POINT_Y for gearboxPiles
        arcpy.management.AlterField(gearboxPiles, "POINT_Y", "northing_gear", "northing_gear")

        # Calculate the means of the northing and the base planes by row
        nMeanInput = str("POINT_Y MEAN;" + poaField + " MEAN")
        piles_northing_plane_mean = arcpy.analysis.Statistics(pilesOriginal, "piles_northing_plane_mean", nMeanInput, row_ID)

        # Join back to the pile table
        meanPOAField = "MEAN_" + poaField
        nMeanResult = "MEAN_POINT_Y; " + meanPOAField
        arcpy.management.JoinField(pilesOriginal, row_ID, piles_northing_plane_mean, row_ID, nMeanResult)

        # Calculate the delta between the northing and northing mean, and the deltat between the plane and plane mean
        arcpy.management.CalculateField(pilesOriginal, "n_nbar", "!POINT_Y!-!MEAN_POINT_Y!", "PYTHON3", "", "DOUBLE")
        poa_poaBarCalc = str("!" + poaField + "! -!MEAN_" + poaField +"!")
        arcpy.management.CalculateField(pilesOriginal, "poa_poaBar", poa_poaBarCalc, "PYTHON3", "", "DOUBLE")

        # Calculate the delta plane squared, and the product of the delta plane and the delta northing
        arcpy.management.CalculateField(pilesOriginal, "dNorthXdpoa", "!n_nbar! * !poa_poaBar!", "PYTHON3","","DOUBLE")
        arcpy.management.CalculateField(pilesOriginal, "dNorth_sq", "!n_nbar!*!n_nbar!", "PYTHON3","","DOUBLE")

        # Do summary statistics to get row sums of the delta plane squared and the product of the delta plane and the delta northing
        piles_delta_sum = arcpy.analysis.Statistics(pilesOriginal, "piles_delta_sum", "dNorthXdpoa SUM;dNorth_sq SUM", row_ID)

        # Calculate the slope
        arcpy.management.CalculateField(piles_delta_sum, "slope", "-100*!SUM_dNorthXdpoa!/!SUM_dNorth_sq!", "PYTHON3","","DOUBLE")

        # Join the slope back to the piles
        arcpy.management.JoinField(pilesOriginal, row_ID, piles_delta_sum, row_ID, "slope")

        # Calculate the new northing based on the distance to the gearbox pile northing
        arcpy.management.JoinField(pilesOriginal, row_ID, gearboxPiles, row_ID, "northing_gear")
        arcpy.management.CalculateField(pilesOriginal, "northing_adj", "!northing_gear! + (!POINT_Y!-!northing_gear!) / math.sqrt(1 + math.pow(!slope!/100,2))", "PYTHON3", "","DOUBLE")

        # Add a checking field for the distance adjusted
        arcpy.management.CalculateField(pilesOriginal, "nAdj_check", "!northing_adj! - !POINT_Y!", "PYTHON3", "","DOUBLE")

        # Preserve the original northing
        arcpy.management.CalculateField(pilesOriginal, "northing_orig", "!POINT_Y!", "PYTHON3", "","DOUBLE")

        # XY table to point
        # pilesOutName = os.path.basename(pileOutput)
        pilesOutName = os.path.join(workspace, pileOutput)

        pilesAdj = arcpy.management.XYTableToPoint(pilesOriginal, pilesOutName, "POINT_X", "northing_adj", None, spatialRef)

        arcpy.sa.ExtractMultiValuesToPoints(pilesAdj,[[demExist, 'demExist_temp'],[demGrade, 'demGrade_adj']], 'BILINEAR')

        # Calculate new point coordinates
        codeblock_grade = """
def dGrade(demE,demG):
    if demG == None:
        return demE
    else:
        return demG
    """

        arcpy.management.CalculateField(pilesAdj, "demGrade_adj", "dGrade(!demExist_temp!, !demGrade_adj!)", "PYTHON3", codeblock_grade,"DOUBLE")

        arcpy.management.CalculateField(pilesAdj, "reveal_adj","!"+poaField+"! - !demGrade_adj!", "PYTHON3", "","DOUBLE")

        # Update POINT_Y
        arcpy.management.AddXY(pilesAdj)

        # Delete unecessary fields
        arcpy.management.DeleteField(pilesAdj, "dNorth_sq;dNorthXdpoa;MEAN_poa;MEAN_POINT_Y;n_nbar;northing_gear;poa_poaBar;POINT_Z;slope;demExist_temp")

        arcpy.management.Delete(piles_delta_sum)
        arcpy.management.Delete(piles_northing_plane_mean)
        arcpy.management.Delete(pilesOriginal)
        arcpy.management.Delete(gearboxPiles)

        # Add output to map
        aprxMap.addDataFromPath(pilesAdj)

        return