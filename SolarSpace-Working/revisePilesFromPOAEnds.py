############################################################
"""REVISE PILE PLANE OF ARRAY FROM ADJUSTED ROW ENDS

Revision log
0.0.1 - 02/09/2023 - Initial scripting
1.0.0 - 02/10/2023 - Tested and released
1.1.0 - 11/14/2023 - Changed script to avoid errors in processing/selecting, added change calculations
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.1.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
import math
from arcpy.sa import *
from arcpy.ddd import *

class revisePilesFromPOAEnds(object):
    def __init__(self):
        self.label = "Calculate New POA Grading and Reveal for Piles from Revised End of Rows"
        self.description = "Calculates the plane of array, grading, and reveal for piles based on adjusted row ends"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Revised end of row points",
            name="eorPOA",
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
            displayName="Original POA field",
            name="poaOrigField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Revised POA field",
            name="poaAdjField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param0.name]

        param4 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param6.filter.list = ["Point"]

        param7 = arcpy.Parameter(
            displayName="Existing elevation field",
            name="demExist_Field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param7.parameterDependencies = [param6.name]

        param8 = arcpy.Parameter(
            displayName="Compare previous grade, reveals and top of pile elevations?",
            name="compareOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param8.value = False

        param9 = arcpy.Parameter(
            displayName="Original top of pile elevation field",
            name="TOP_elv_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param9.parameterDependencies = [param6.name]

        param10 = arcpy.Parameter(
            displayName="Reveal field",
            name="revField",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param10.parameterDependencies = [param6.name]

        param11 = arcpy.Parameter(
            displayName="Graded elevation field",
            name="demGrade_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param11.parameterDependencies = [param6.name]

        param12 = arcpy.Parameter(
            displayName="Pile output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[8].value == True:
            parameters[9].enabled = True
            parameters[10].enabled = True
            parameters[11].enabled = True
        else:
            parameters[9].enabled = False
            parameters[10].enabled = False
            parameters[11].enabled = False

        if not parameters[12].altered:
            parameters[12].value = "pilesAdj"
    
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # if parameters[4].altered:
            # rowIDCheck = arcpy.Describe(parameters[4].valueAsText).fields
            # if parameters[1].valueAsText in [f.name for f in rowIDCheck]:
                # parameters[4].clearMessage()
            # else:
                # parameters[4].setErrorMessage("Row ID field is not present in piles")
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        eorPOA          = parameters[0].valueAsText
        row_ID          = parameters[1].valueAsText
        poaOrigField    = parameters[2].valueAsText
        poaAdjField     = parameters[3].valueAsText
        minReveal       = parameters[4].valueAsText
        maxReveal       = parameters[5].valueAsText        
        pilesInput      = parameters[6].valueAsText
        demExist_Field  = parameters[7].valueAsText
        compareOption   = parameters[8].value
        TOP_elv_field   = parameters[9].valueAsText
        revField        = parameters[10].valueAsText
        demGrade_field  = parameters[11].valueAsText
        pileOutput      = parameters[12].valueAsText

        eorAdj = arcpy.conversion.FeatureClassToFeatureClass(eorPOA,workspace,"eorAdj")

        arcpy.management.AddXY(eorAdj)

        # Calculate the slope and intercept of the new POA using both end points
        endStats = arcpy.analysis.Statistics(eorAdj, "endStats", [[poaAdjField, "MEAN"], ["POINT_Y", "MEAN"]], row_ID)

        meanPOAField = "MEAN_" + poaAdjField

        # Join the mean of the plane of array and MEAN_POINT_Y back to the piles
        arcpy.management.JoinField(eorAdj, row_ID, endStats, row_ID, [meanPOAField, "MEAN_POINT_Y"])

        # Calculate zy_bar, y_ybar_sq
        arcpy.management.CalculateField(eorAdj, "zy_bar","(!"+poaAdjField+"! + !"+meanPOAField+"!) * (!POINT_Y! - !MEAN_POINT_Y!)", "PYTHON3", "","DOUBLE")
        arcpy.management.CalculateField(eorAdj, "y_ybar_sq", "(!POINT_Y! - !MEAN_POINT_Y!)**2", "PYTHON3", "","DOUBLE")

        # Summary Statistics by row_ID to get the sum of zy_bar, y_ybar_sq
        sumStatsEnd = arcpy.analysis.Statistics(eorAdj, "sumStatsEnd", [["zy_bar", "SUM"], ["y_ybar_sq", "SUM"]],row_ID)

        # Calculate the slope (SUM_xy_bar/SUM_x_bar_sq), multiplied by 100 for percent and by -1 to get the convention of north is positive/south is negative
        arcpy.management.CalculateField(sumStatsEnd, "nsSlopeNew", "!SUM_zy_bar!/!SUM_y_ybar_sq!", "PYTHON3", "","DOUBLE")

        # Join slope to piles_working
        arcpy.management.JoinField(eorAdj, row_ID, sumStatsEnd, row_ID, ["nsSlopeNew"])

        # Find the intercept
        arcpy.management.CalculateField(eorAdj, "bInitNew", "!"+poaAdjField+"! - !nsSlopeNew! * !POINT_Y!", "PYTHON3", "", "DOUBLE")

        endPointStatsNew = arcpy.analysis.Statistics(eorAdj, "endPointStatsNew", [["bInitNew", "MEAN"],["nsSlopeNew", "MEAN"]], row_ID)

        pilesOutName = os.path.basename(pileOutput)

        pilesOutFC = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pilesOutName)

        arcpy.management.AddXY(pilesOutFC)

        # Join the slope and intercept to the piles
        arcpy.management.JoinField(pilesOutFC, row_ID, endPointStatsNew, row_ID, [["MEAN_nsSlopeNew"], ["MEAN_bInitNew"]])

        # Calculate the new POA for each pile point
        arcpy.management.CalculateField(pilesOutFC, "TOP_elv_eorRev", "!MEAN_nsSlopeNew! * !POINT_Y! + !MEAN_bInitNew!", "PYTHON3", "", "DOUBLE")

        # Calculate the new reveal and grading for each pile point
        gradeAdjPiles_code = """
def gradeAdjPiles(demExist, poaAdj, minReveal, maxReveal):
    if (poaAdj - demExist) > maxReveal:
        return poaAdj - maxReveal
    if (poaAdj - demExist) < minReveal:
        return poaAdj - minReveal
    else:
        return demExist
"""

        gradeInput = "gradeAdjPiles(!" + demExist_Field + "!, !TOP_elv_eorRev!, " + minReveal + ", " + maxReveal + ")"

        arcpy.management.CalculateField(pilesOutFC, "demGrade_eorRev",gradeInput, "PYTHON3", gradeAdjPiles_code, "DOUBLE")

        arcpy.management.CalculateField(pilesOutFC, "reveal_eorRev", "!TOP_elv_eorRev! - !demGrade_eorRev!", "PYTHON3", "", "DOUBLE")
        arcpy.management.CalculateField(pilesOutFC, "cutFill_eorRev", "!demGrade_eorRev! - !"+demExist_Field+"!", "PYTHON3", "", "DOUBLE")

        if compareOption == True:

            arcpy.management.CalculateField(pilesOutFC, "TOP_elv_change", "!TOP_elv_eorRev! - !"+TOP_elv_field+"!", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(pilesOutFC, "demGrade_change", "!demGrade_eorRev! - !"+demGrade_field+"!", "PYTHON3", "", "DOUBLE")
            arcpy.management.CalculateField(pilesOutFC, "reveal_change", "!reveal_eorRev! - !"+revField+"!", "PYTHON3", "", "DOUBLE")

        arcpy.management.DeleteField(pilesOutFC, [["MEAN_nsSlopeNew"],["MEAN_bInitNew"]])

        arcpy.management.Delete(sumStatsEnd)
        arcpy.management.Delete(endPointStatsNew)
        arcpy.management.Delete(eorAdj)

        aprxMap.addDataFromPath(pilesOutFC)

        return


