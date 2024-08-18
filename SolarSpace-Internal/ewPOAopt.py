#!/usr/bin/env python
"""Description: Optimizes the plane of array using theoretical planes of array from adacent rows
Revision log
0.0.1 - 4/5/2022 - updated to new template
"""

__author__ = "Matthew Gagne"
__copyright__ = "Copyright 2022, KiloNewton, LLC"
__credits__ = ["Matthew Gagne", "John Williamson"]
__version__ = "1.0.0"
__license__= "internal"
__ArcVersion__ = "ArcGIS 2.9.3"
__maintainer__ = "Matthew Gagne"
__status__ = "Deployed internally"

# Load arcpy and Spatial Analyst
import arcpy
from arcpy import env
from arcpy.sa import *
import os
import sys

class ewPOAopt(object):
    def __init__(self):
        self.label = "East-West Plane of Array Optimization"
        self.description = "Optimizes the plane of array using theoretical planes of array from adacent rows"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Optimization"

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
            displayName="Plane of array or top of pile elevation field",
            name="poaField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Reveal field",
            name="revField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param3.parameterDependencies = [param0.name]

        param4 = arcpy.Parameter(
            displayName="Minimum reveal field",
            name="min_reveal",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.parameterDependencies = [param0.name]

        param5 = arcpy.Parameter(
            displayName="Maximum reveal field",
            name="max_reveal",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.parameterDependencies = [param0.name]

        param6 = arcpy.Parameter(
            displayName="Graded elevation field",
            name="gradeField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param6.parameterDependencies = [param0.name]

        param7 = arcpy.Parameter(
            displayName="Optimized piles output feature class",
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
            parameters[7].value = "pilesOpt"

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        scratch = arcpy.env.scratchWorkspace
        arcpy.env.overwriteOutput=True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.listMaps()[0]

        # Define input parameters
        pilesInput    = parameters[0].valueAsText
        rowID           = parameters[1].valueAsText
        poaField        = parameters[2].valueAsText
        revField        = parameters[3].valueAsText
        min_reveal      = parameters[4].valueAsText
        max_reveal      = parameters[5].valueAsText
        demExist        = parameters[6].valueAsText
        pileOutput      = parameters[7].valueAsText

        # Copy piles to preserve original reveal output for a temporary near file, and for output
        pilesWorking = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, "pilesWorking")
        pilesOutName = os.path.basename(pileOutput)
        pileRevealsOpt = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pilesOutName)

        # Find the nearest four piles (max) for each individual pile, and separate out into east and west
        piles_near = arcpy.analysis.GenerateNearTable(pilesWorking, pilesInput, "piles_near","", "NO_LOCATION", "ANGLE", "ALL", 4, "GEODESIC")

        arcpy.management.AlterField(pilesWorking,poaField, "poa_near", "", "", "", "", "CLEAR_ALIAS")
        arcpy.management.JoinField(piles_near, "NEAR_FID", pilesWorking, "OBJECTID", "poa_near")

        near_east = arcpy.TableSelect_analysis(piles_near, "near_east", "NEAR_ANGLE > 87 And NEAR_ANGLE < 92") # Note: this assumes that there are no short rows, or staggered piles 

        arcpy.management.AlterField(near_east,"poa_near", "poa_east", "", "", "", "", "CLEAR_ALIAS")

        near_west = arcpy.TableSelect_analysis(piles_near, "near_west", "NEAR_ANGLE > -92 And NEAR_ANGLE < -87") # Note: this assumes that there are no short rows, or staggered piles 
        arcpy.management.AlterField(near_west, "poa_near", "poa_west", "", "", "", "", "CLEAR_ALIAS")

        # Join east and west back to the piles
        arcpy.management.JoinField(pilesWorking, "OBJECTID", near_east, "IN_FID", "poa_east")
        arcpy.management.JoinField(pilesWorking, "OBJECTID", near_west, "IN_FID", "poa_west")

        # Calculate theoretical plane of array
        codeblock_poaTH = """
def poaTH(east,west, poa):
    if east == None or west == None:
        return poa
    else:
        return (east+west)/2
"""

        arcpy.management.CalculateField(pilesWorking, "poa_opt_pre", "poaTH(!poa_east!,!poa_west!,!poa_near!)", "PYTHON3", codeblock_poaTH,"FLOAT")
        arcpy.management.CalculateField(pilesWorking, "poa_delta", "!poa_opt_pre!-!poa_near!", "PYTHON3", "","FLOAT")
        arcpy.management.CalculateField(pilesWorking, "poa_opt", "!poa_delta!/2 + !poa_near!", "PYTHON3", "","FLOAT")

        pilesOutName = os.path.basename(pileOutput)
        pileRevealsOpt = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pilesOutName)
        arcpy.management.JoinField(pileRevealsOpt, "OBJECTID", pilesWorking, "OBJECTID", "poa_opt")

        arcpy.management.CalculateField(pileRevealsOpt, "poa_delta", "!poa_opt!-!"+poaField+"!", "PYTHON3", "","FLOAT")

        # Calculate the adjusted reveal
        codeblock_revAdj = """
def revAdj(EG, minRev, maxRev, poaTH):
        if (poaTH - EG) > maxRev:
            return maxRev
        if (poaTH - EG) < minRev:
            return minRev
        else:
            return poaTH - EG
    """

        arcpy.management.CalculateField(pileRevealsOpt, "reveal_opt", "revAdj(!"+demExist+"!,!"+min_reveal+"!,!"+max_reveal+"!,!poa_opt!)", "PYTHON3", codeblock_revAdj,"FLOAT")
        
        aprxMap.addDataFromPath(pileRevealsOpt) 
        aprxMap.addDataFromPath(pilesWorking) 

        # Clean up
        
        return