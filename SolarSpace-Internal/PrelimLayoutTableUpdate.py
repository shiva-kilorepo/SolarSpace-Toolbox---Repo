""" Adjusts POA & Grading based on Latitude
Description: Adjusts the plane of array and grading based on the latitude and the planes of array derived from the standard grading process
Revision log
1.0.0 - 6/10/2022 - Adapted from SAT layout tool
1.0.1 - 8/24/2023 - Converted to PYT format and interal toolbox
"""

__author__      = "Zane Nordquist"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "John Williamson"]
__version__     = "1.0.0"
__license__     = "internal"
__ArcVersion__  = "ArcPro 3.1.3"
__maintainer__  = "Matthew Gagne"
__status__      = "Deployed"


# Load modules 
import arcpy
from arcpy import env

class PrelimLayoutTableUpdate(object):
    def __init__(self):
        self.label = "Prelim Layout Summary Table Update"
        self.description = "Updates Preliminary Layout table to revised and editted layout (strings and inverters)"
        self.canRunInBackground = False
        self.category = "Site Design/Layout Creation"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input revised string row layer",
            name="stringsInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input revised inverter layer",
            name="inverterInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Input Preliminary Layout Summary Table",
            name="layout_summary_input",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Input version number of the layout",
            name="version",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
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
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        stringsInput =  parameters[0].valueAsText # Polygon layer with individual strings
        inverterInput = parameters[1].valueAsText # Polygon layer with individual inverters
        layout_summary_input = parameters[2].valueAsText # Polygon layer with individual inverters
        version =  parameters[3].valueAsText #version of layout
               
        # Get the latitude of the project
        summary_update = arcpy.conversion.TableToTable(layout_summary_input, workspace, f"layout_summary_{version}")

        # Get count of strings and inverters
        stringCount = arcpy.management.GetCount(stringsInput)
        inverterCount = arcpy.management.GetCount(inverterInput)

        # get value of count_string field from layout_summary
        with arcpy.da.SearchCursor(summary_update, ["count_strings"]) as cursor:
            for row in cursor:
                stringCount_orig = row[0]
                
        # Caculate summary updates DC
        if stringCount != stringCount_orig:
            stringCount = str(stringCount)
            arcpy.management.CalculateField(summary_update,"DC_MW",f"{stringCount} * !modString! * !modRating!/1000/1000","PYTHON3",None,)
            
        # Calculate summary updates AC
        arcpy.management.CalculateField(summary_update,"AC_MW",f"{inverterCount} * !inverterSize!","PYTHON3",None,)
        
        arcpy.management.CalculateField(summary_update, "DC_AC_RATIO", "!DC_MW!/!AC_MW!", "PYTHON3", None)
        
        #Add summary updates to map
        aprxMap.addDataFromPath(summary_update)
        
