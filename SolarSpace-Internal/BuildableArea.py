####################################################################################################
"""DERIVE BUILDABLE AREA 

Derives the buildable area based on inputs

Revision log
0.0.1 - 08/8/2022 - Initial build and testing
1.0.0 - 8/15/2022 - Deployed
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

import arcpy
import os.path
import sys

class BuildableArea(object):
    def __init__(self):
        self.label = "Derive buildable area"
        self.description = "Derives the buildable area based on inputs"
        self.canRunInBackground = False
        self.category = "Site Design"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Project area",
            name="project_area",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Measurement units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["Feet", "Meters"]

        param2 = arcpy.Parameter(
            displayName="Project boundary setback",
            name="project_bound_setback",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Setbacks",
            name="setback_input",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        param3.columns = [["GPFeatureLayer", "Setback Feature"], ["String", "Feature Category"], ["Double", "Setback"]]
        param3.filters[1].type = "ValueList"
        param3.filters[1].list = ["Environment - Critical Habitat",
                                  "Environment - Forestry",
                                  "Environment - Riparian Area",
                                  "Environment - Other",
                                  "Hydro - Ditch/Drainage",
                                  "Hydro - Flood Zone",
                                  "Hydro - Pond/Lake",
                                  "Hydro - River/Stream",
                                  "Hydro - Wetland",
                                  "Hydro - Other",
                                  "Project - Easement",
                                  "Project - Substation",
                                  "Project - Other",
                                  "Slope Exclusion",
                                  "Structures - Primary",
                                  "Structures - Secondary",
                                  "Structures - Other",
                                  "Transportation - Highway",
                                  "Transportation - Improved Road",
                                  "Transportation - Rail",
                                  "Transportation - Unimproved Road",
                                  "Transportation - Other",
                                  "Utility - Oil/Gas Pipeline",
                                  "Utility - Oil/as Well",
                                  "Utility - Transmission Line",
                                  "Utility - Distribution Line",
                                  "Utility - Other",
                                  "Other",
                                  ]

        param4 = arcpy.Parameter(
            displayName="Buildable area output feature class",
            name="buildable_output",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        param5 = arcpy.Parameter(
            displayName="Setback output feature class",
            name="setback_output",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Derived")

        params = [param0, param1, param2, param3, param4, param5]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            parameters[2].value = 25

        if not parameters[4].altered:
            parameters[4].value = 'buildable_area'

        if not parameters[5].altered:
            parameters[5].value = 'setbacks_all'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        parameters[2].clearMessage()

        if parameters[2].value > 0:
            parameters[2].setErrorMessage("Use a negative number to define the setback within the project boundary.")

        return

    def execute(self, parameters, messages):

        # Load modules
        import arcpy
        from arcpy import env

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput = True
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Set parameters
        project_area = parameters[0].valueAsText  # Project area
        xyzUnit = parameters[1].valueAsText  # Feet or Meters
        project_bound_setback = parameters[2].valueAsText  # Setback from outer boundary
        setback_input = parameters[3].value  # Setback input layers with setbacks and category
        buildable_output = parameters[4].valueAsText  # Output buildable area
        setback_output = parameters[5].valueAsText  # Output setback feature class

        outputPath = os.path.dirname(workspace)

        # Initially do the setback from the project boundary
        bSetback = project_bound_setback + " " + xyzUnit
        bound_setback = arcpy.analysis.PairwiseBuffer(project_area, "bound_setback", bSetback)

        # Create scratch geodatabase for the setback layers
        setbackScratchGDB = arcpy.management.CreateFileGDB(outputPath, "setbacks.gdb", "CURRENT")

        # List feature classes
        scratchWS = arcpy.env.workspace = (outputPath + "/setbacks.gdb")

        arcpy.SetProgressor('default', 'Creating setbacks from input features...')

        # Loop through the setback feature inputs and apply setbacks and the categroy
        for i in setback_input:
            feature = i[0]
            type = i[1]
            dist = i[2]

            unique_name = arcpy.CreateUniqueName("setback")

            feature_setback = arcpy.analysis.PairwiseBuffer(feature, unique_name, dist, "ALL")

            # Add a field for the category
            type_input = "'" + str(type) + "'"
            arcpy.management.CalculateField(feature_setback, "feature_category", type_input, "PYTHON3", '', "TEXT",
                                            "NO_ENFORCE_DOMAINS")

            # Add a field for the setback
            setback_value = "'" + str(dist) + " " + xyzUnit + "'"
            arcpy.management.CalculateField(feature_setback, "setback_distance", setback_value, "PYTHON3", '', "TEXT",
                                            "NO_ENFORCE_DOMAINS")

        setbacksList = arcpy.ListFeatureClasses()

        setbacksAll = arcpy.management.Merge(setbacksList, setback_output)

        # Change default environment back to workspace
        arcpy.env.workspace = workspace

        arcpy.SetProgressor('default', 'Creating buildable area...')

        # Erase the setbacks from the bound_setback
        buildableArea = arcpy.analysis.Erase(bound_setback, setbacksAll, buildable_output)

        aprxMap.addDataFromPath(setbacksAll)
        aprxMap.addDataFromPath(buildableArea)

        buildableName = os.path.basename(buildable_output)
        setbackName = os.path.basename(setback_output)

        # Apply symbology
        buildableLyr = aprxMap.listLayers(buildableName)[0]
        buildableSym = buildableLyr.symbology
        buildableSym.renderer.symbol.color = {'RGB': [85, 255, 0, 50]}
        buildableSym.renderer.label = "Buildable Area"
        buildableLyr.symbology = buildableSym

        setbackLyr = aprxMap.listLayers(setbackName)[0]
        setbackSym = setbackLyr.symbology
        setbackSym.updateRenderer('UniqueValueRenderer')
        setbackSym.renderer.fields = ['feature_category']
        for grp in setbackSym.renderer.groups:
            for itm in grp.items:
                lyrValue = itm.values[0][0]
                if lyrValue == "Environment - Critical Habitat":
                    itm.symbol.color = {'RGB': [255, 0, 0, 50]}
                    itm.symbol.outlineColor = {'RGB': [115, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Environment - Forestry":
                    itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    itm.symbol.color = {'RGB': [112, 168, 0, 75]}
                    itm.symbol.outlineColor = {'RGB': [115, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Environment - Riparian Area":
                    itm.symbol.color = {'RGB': [0, 168, 132, 50]}
                    itm.symbol.outlineColor = {'RGB': [0, 115, 76, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Environment - Other":
                    itm.symbol.applySymbolFromGallery("10% Crosshatch")
                    itm.symbol.color = {'RGB': [85, 255, 0, 75]}
                    itm.symbol.outlineColor = {'RGB': [38, 115, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - Ditch/Drainage":
                    itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    itm.symbol.angle = 135
                    itm.symbol.color = {'RGB': [0, 112, 255, 75]}
                    itm.symbol.outlineColor = {'RGB': [0, 38, 115, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - Flood Zone":
                    itm.symbol.color = {'RGB': [0, 255, 197, 50]}
                    itm.symbol.outlineColor = {'RGB': [0, 168, 132, 50]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - Pond/Lake":
                    itm.symbol.color = {'RGB': [115, 223, 255, 50]}
                    itm.symbol.outlineColor = {'RGB': [0, 132, 168, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - River/Stream":
                    itm.symbol.color = {'RGB': [0, 77, 168, 50]}
                    itm.symbol.outlineColor = {'RGB': [115, 255, 223, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - Wetland":
                    itm.symbol.color = {'RGB': [0, 132, 168, 50]}
                    itm.symbol.outlineColor = {'RGB': [130, 130, 130, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Hydro - Other":
                    itm.symbol.applySymbolFromGallery("10% Crosshatch")
                    itm.symbol.color = {'RGB': [0, 76, 115, 75]}
                    itm.symbol.outlineColor = {'RGB': [0, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Project - Easement":
                    itm.symbol.color = {'RGB': [255, 170, 0, 50]}
                    itm.symbol.outlineColor = {'RGB': [255, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Project - Substation":
                    itm.symbol.color = {'RGB': [0, 76, 115, 75]}
                    itm.symbol.outlineColor = {'RGB': [0, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Project - Other":
                    itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    itm.symbol.angle = 90
                    itm.symbol.color = {'RGB': [104, 104, 104, 75]}
                    itm.symbol.outlineColor = {'RGB': [0, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Slope Exclusion":
                    itm.symbol.color = {"RGB": [255, 255, 0, 65]}
                    itm.symbol.outlineColor = {'RGB': [168, 168, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Structures - Primary":
                    itm.symbol.color = {'RGB': [233, 115, 255, 50]}
                    itm.symbol.outlineColor = {'RGB': [132, 0, 168, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Structures - Secondary":
                    itm.symbol.color = {'RGB': [168, 0, 132, 50]}
                    itm.symbol.outlineColor = {'RGB': [255, 115, 223, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Structures - Other":
                    itm.symbol.color = {'RGB': [132, 0, 168, 50]}
                    itm.symbol.outlineColor = {'RGB': [232, 190, 255, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Transportation - Highway":
                    itm.symbol.color = {'RGB': [255, 150, 127, 50]}
                    itm.symbol.outlineColor = {'RGB': [230, 230, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Transportation - Improved Road":
                    itm.symbol.color = {'RGB': [68, 101, 137, 50]}
                    itm.symbol.outlineColor = {'RGB': [255, 85, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Transportation - Rail":
                    itm.symbol.applySymbolFromGallery("10% Crosshatch")
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Transportation - Unimproved Road":
                    itm.symbol.color = {'RGB': [115, 115, 0, 50]}
                    itm.symbol.outlineColor = {'RGB': [255, 255, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Transportation - Other":
                    itm.symbol.color = {'RGB': [110, 110, 0, 50]}
                    itm.symbol.outlineColor = {'RGB': [0, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Utility - Oil/Gas Pipeline":
                    itm.symbol.color = {'RGB': [68, 79, 137, 50]}
                    itm.symbol.outlineColor = {'RGB': [169, 0, 230, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Utility - Oil/as Well":
                    itm.symbol.applySymbolFromGallery("10% Crosshatch")
                    itm.symbol.color = {'RGB': [68, 79, 137, 75]}
                    itm.symbol.outlineColor = {'RGB': [169, 0, 230, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Utility - Transmission Line":
                    itm.symbol.color = {'RGB': [255, 85, 0, 50]}
                    itm.symbol.outlineColor = {'RGB': [204, 204, 204, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Utility - Distribution Line":
                    itm.symbol.color = {'RGB': [255, 167, 127, 50]}
                    itm.symbol.outlineColor = {'RGB': [168, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Utility - Other":
                    itm.symbol.color = {'RGB': [205, 102, 102, 50]}
                    itm.symbol.outlineColor = {'RGB': [0, 0, 0, 75]}
                    itm.symbol.outlineWidth = 1
                if lyrValue == "Other":
                    itm.symbol.applySymbolFromGallery("10% Simple hatch")
                    itm.symbol.outlineWidth = 1
        setbackLyr.symbology = setbackSym

        # Clean up
        arcpy.management.Delete(setbackScratchGDB)
        arcpy.management.Delete(bound_setback)

        arcpy.ResetProgressor()

        return