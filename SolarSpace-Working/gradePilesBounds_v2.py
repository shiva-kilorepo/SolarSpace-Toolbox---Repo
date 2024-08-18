########################################################################
"""NEW GRADE FROM BOUNDS AND PILES

Revision log
0.1.0 - 02/03/2023 - Intial coding.
1.0.0 - 12/14/2023 - Added screen for TIN creation to eliminate long TIN edges
"""

__author__      = "Matthew Gagne"
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal"
__ArcVersion__  = "ArcGIS 3.2.1"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import math

class gradePilesBounds_v2(object):
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
            name="gradeBounds",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ["Polygon"]

        param4 = arcpy.Parameter(
            displayName="Piles per full row",
            name="pilesPerRow",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Horizontal and vertical units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["Foot", "Meter"]

        param6 = arcpy.Parameter(
            displayName="Full row length",
            name="rowLength",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="Row width",
            name="rowWidth",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param8 = arcpy.Parameter(
            displayName="GCR (%)",
            name="GCR",
            datatype="Double",
            parameterType="Required",
            direction="Input")

        param9 = arcpy.Parameter(
            displayName="Smoothed grading output raster dataset",
            name="gradeOut",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")


        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
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
        arcpy.env.overwriteOutput=True
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap

        # Set parameters
        demInput            = parameters[0].valueAsText  
        pilesInput          = parameters[1].valueAsText
        gradeField          = parameters[2].valueAsText
        gradeBounds          = parameters[3].valueAsText
        pilesPerRow         = parameters[4].valueAsText 
        xyzUnit             = parameters[5].valueAsText
        rowLength           = parameters[6].valueAsText
        rowWidth            = parameters[7].valueAsText
        GCR                 = parameters[8].valueAsText
        gradeOut            = parameters[9].valueAsText

        outputPath = os.path.dirname(workspace)

        spatialRef = arcpy.Describe(demInput).spatialReference
        gridRes = arcpy.Describe(demInput).meanCellWidth
        arcpy.env.snapRaster = demInput

        # Select the sample points and the piles within graded areas
        piles_intersect = arcpy.management.SelectLayerByLocation(pilesInput, "INTERSECT", gradeBounds)
        piles_graded = arcpy.conversion.FeatureClassToFeatureClass(piles_intersect, workspace, "piles_graded")

        # Convert the buffered layer to polylines and interpolate the existing elevation
        grade_area_line = arcpy.management.FeatureToLine(gradeBounds, "grade_area_line")
        grade_bound_3D = arcpy.sa.InterpolateShape(demInput, grade_area_line, "grade_bound_3D", None, 1, "BILINEAR","DENSIFY", 0, "EXCLUDE")

        # Create TIN between graded piles and refine to graded area, and extract the 3D edges
        tin_name_piles = str(outputPath + "\piles_TIN")
        pileTIN_input = "piles_graded " + gradeField + " Mass_Points"
        arcpy.AddMessage(f'Creating tin based on: {pileTIN_input}')
        piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, pileTIN_input)
        tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
        tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", grade_area_line,None, "NEW_SELECTION", "INVERT")
        tinEdge_preScreen = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace,"tinEdge_preScreen")
        
        centerToCenter = float(rowWidth) / (float(GCR) / 100)
        averageSpan = float(rowLength) / float(pilesPerRow) + 10
        rowToRowDiagonal = math.sqrt(centerToCenter**2 + averageSpan **2) + 25
        
        spanWhereClause = "SHAPE_LENGTH < " +  str(rowToRowDiagonal)
        
        tinEdge_final = arcpy.analysis.Select(tinEdge_preScreen, "tinEdge_final", spanWhereClause)

        # Create a TIN from the bound and piles layer
        tin_name = str(outputPath + "\grade_TIN")
        grade_TIN = arcpy.ddd.CreateTin(tin_name, spatialRef,"grade_bound_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>")
        gradeBoundsName = os.path.basename(gradeBounds)
        editTinInput = gradeBoundsName + " <None> <None> Hard_Clip false"
        arcpy.ddd.EditTin(grade_TIN, editTinInput, "DELAUNAY")

        gradeRasterName = os.path.basename(gradeOut)

        output_grade = arcpy.ddd.TinRaster(grade_TIN, gradeRasterName, "FLOAT", "LINEAR", "CELLSIZE", 1,gridRes)

        aprxMap.addDataFromPath(output_grade)

