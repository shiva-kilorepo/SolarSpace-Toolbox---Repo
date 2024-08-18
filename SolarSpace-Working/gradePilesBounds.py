########################################################################
"""NEW GRADE FROM BOUNDS AND PILES

Revision log
0.1.0 - 02/03/2023 - Intial coding.
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *

class gradePilesBounds(object):
    def __init__(self):
        self.label = "New graded raster from piles and bounds"
        self.description = " "
        self.canRunInBackground = False
        self.category = "Civil Analysis\SAT Grading Adjustments"
        
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Existing elevation raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Pile input feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Point"]

        param2 = arcpy.Parameter(
            displayName="Graded elevation field",
            name="gradeField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param2.parameterDependencies = [param1.name]

        param3 = arcpy.Parameter(
            displayName="Grading boundary",
            name="gradeBound",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ["Polygon"]

        param4 = arcpy.Parameter(
            displayName="Smoothed grading output raster dataset",
            name="gradeOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        # param5 = arcpy.Parameter(
            # displayName="Output grading volume statistics?",
            # name="cutFillOption",
            # datatype="GPBoolean",
            # parameterType="Optional",
            # direction="Input")
        # param5value = False

        # param6 = arcpy.Parameter(
            # displayName="Cut output raster dataset",
            # name="cutOut",
            # datatype="DERasterDataset",
            # parameterType="Optional",
            # direction="Derived")

        # param7 = arcpy.Parameter(
            # displayName="Fill output raster dataset",
            # name="fillOut",
            # datatype="DERasterDataset",
            # parameterType="Optional",
            # direction="Derived")

        # param8 = arcpy.Parameter(
            # displayName="Volume summary table",
            # name="statsOutput",
            # datatype="DETable",
            # parameterType="Optional",
            # direction="Output")

        params = [param0, param1, param2, param3, param4]#, param5, param6, param7, param8]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # if parameters[5].value == True:
            # parameters[6].enabled = True
            # parameters[7].enabled = True
            # parameters[8].enabled = True

        # else:
            # parameters[6].enabled = False
            # parameters[7].enabled = False
            # parameters[8].enabled = False

        # if not parameters[6].altered:
            # parameters[6].value = 'Cut'

        # if not parameters[7].altered:
            # parameters[7].value = 'Fill'

        # if not parameters[8].altered:
            # parameters[8].value = 'CutFill_Statistics'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):

        # Set workspace environment
        workspace = arcpy.env.workspace
        arcpy.env.overwriteOutput=True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demExist = parameters[0].valueAsText # Existing elevation in raster format
        pilesInput = parameters[1].valueAsText # pile layer
        gradeField = parameters[2].valueAsText
        gradeBounds = parameters[3].valueAsText
        gradeOut = parameters[4].valueAsText # Graded raster output dataset
        # cutFillOption = parameters[5].value
        # cutOut = parameters[6].valueAsText
        # fillOut = parameters[7].valueAsText
        # statsOutput = parameters[8].valueAsText

        outputPath = os.path.dirname(workspace)

        spatialRef = arcpy.Describe(demExist).spatialReference
        gridRes = arcpy.Describe(demExist).meanCellWidth
        arcpy.env.snapRaster = demExist

        # Select the sample points and the piles within graded areas
        piles_intersect = arcpy.management.SelectLayerByLocation(pilesInput, "INTERSECT", gradeBounds)
        piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, "piles_graded")

        # Convert the buffered layer to polylines and interpolate the existing elevation
        grade_area_line = arcpy.management.FeatureToLine(gradeBounds, "grade_area_line")
        grade_bound_3D = arcpy.sa.InterpolateShape(demExist, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR","DENSIFY", 0, "EXCLUDE")

        # Create TIN between graded piles and refine to graded area, and extract the 3D edges
        tin_name_piles = str(outputPath + "\piles_TIN")
        pileTIN_input = "piles_graded " + gradeField + " Mass_Points"
        piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, pileTIN_input)
        tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
        tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line,None, "NEW_SELECTION", "INVERT")
        tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace,"tinEdge_final")

        # Create a TIN from the bound and piles layer
        tin_name = str(outputPath + "\grade_TIN")
        grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef,"grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
        gradeBoundsName = os.path.basename(gradeBounds)
        editTinInput = gradeBoundsName + " <None> <None> Hard_Clip false"
        arcpy.ddd.EditTin(grade_TIN, editTinInput, "DELAUNAY")

        gradeRasterName = os.path.basename(gradeOut)

        output_grade = arcpy.ddd.TinRaster(grade_TIN, gradeRasterName, "FLOAT", "LINEAR", "CELLSIZE", 1,gridRes)

        aprxMap.addDataFromPath(output_grade)

