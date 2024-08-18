############################################################
""" ACCOUNT FOR FLOOD DEPTHS IN REVEALS, POA, AND GRADING

Revision log
0.0.1 - 03/15/2023 - Initial scripting
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "0.0.1"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Testing"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *

class floodAdj(object):
    def __init__(self):
        self.label = "Adjust Grading at Piles to Account for Flood Depths"
        self.description = "Revises grading, reveals, and planes of array at piles to account for flood depths"
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"

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
            displayName="Top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Reveal field",
            name="revealField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param0.name]

        param4 = arcpy.Parameter(
            displayName="Existing elevation field",
            name="demExistField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.parameterDependencies = [param0.name]

        param5 = arcpy.Parameter(
            displayName="Graded elevation field",
            name="demGradeField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.parameterDependencies = [param0.name]

        param6 = arcpy.Parameter(
            displayName="Flood depth field",
            name="floodDepth",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param6.parameterDependencies = [param0.name]

        param7 = arcpy.Parameter(
            displayName="Minimum pile reveal",
            name="minReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="Maximum pile reveal",
            name="maxReveal",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Flood depth critical level",
            name="floodCritical",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param10 = arcpy.Parameter(
            displayName="Pile detail output feature class",
            name="pileOutput",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9, param10]

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
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        pilesInput = parameters[0].valueAsText
        row_ID = parameters[1].valueAsText
        poaField = parameters[2].valueAsText
        revealField = parameters[3].valueAsText
        demExistField = parameters[4].valueAsText
        demGradeField = parameters[5].valueAsText
        floodDepth = parameters[6].valueAsText
        # xyzUnit = "Foot"
        minReveal = parameters[7].valueAsText
        maxReveal = parameters[8].valueAsText
        floodCritical = parameters[9].valueAsText
        pilesOutput = parameters[10].valueAsText

        pilesOutName = os.path.basename(pilesOutput)

        piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pilesOutName)

        arcpy.management.CalculateField(piles_working, "clearance","!"+revealField+"! - "+minReveal+"", "PYTHON3", "","DOUBLE")

        floodRevCode = """
def floodRev(floodDepth, floodCritical, demGrade, demExist, clearance):
    if floodDepth > floodCritical:
        return max(floodDepth - demGrade + demExist - clearance,0) 
    else: 
        return max(floodDepth - clearance,0) 
"""
        arcpy.management.CalculateField(piles_working, "floodRevised","floodRev(!"+floodDepth+"!,"+floodCritical+", !"+demGradeField+"!, !"+demExistField+"!, !clearance!)", "PYTHON3", floodRevCode, "DOUBLE")

        floodStats = arcpy.analysis.Statistics(
            in_table=piles_working,
            out_table="floodStats",
            statistics_fields="floodRevised MAX",
            case_field=row_ID,
        )

        arcpy.management.JoinField(piles_working, row_ID, floodStats, row_ID, "MAX_floodRevised")

        arcpy.management.CalculateField(piles_working, "flood_adj", "max(!MAX_floodRevised! - "+floodCritical+", 0)","PYTHON3", "","DOUBLE")

        arcpy.management.CalculateField(piles_working, "TOP_elv_floodAdj", "!"+poaField+"! + !flood_adj! ", "PYTHON3", "","DOUBLE")

        revealCode = """
def revCode(topEl, dE, minR, maxR):
    if (topEl - dE) > maxR:
        return maxR
    if (topEl - dE) < minR:
        return minR
    else: 
        return topEl - dE
"""

        arcpy.management.CalculateField(piles_working, "reveal_floodAdj","revCode(!TOP_elv_floodAdj!, !"+demExistField+"!, "+minReveal+", "+maxReveal+")", "PYTHON3", revealCode, "DOUBLE")

        arcpy.management.CalculateField(piles_working, "demGrade_floodAdj", "!TOP_elv_floodAdj! - !reveal_floodAdj!", "PYTHON3", "","DOUBLE")

        arcpy.management.CalculateField(piles_working, "cutFill_floodAdj", "!demGrade_floodAdj! - !"+demExistField+"!", "PYTHON3", "","DOUBLE")

        aprxMap.addDataFromPath(piles_working)
