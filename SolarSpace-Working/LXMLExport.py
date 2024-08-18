########################################################################
"""EXPORT GRADED RASTER SURFACE TO LANDXML 

Revision log
0.1.0 - 06/30/2022 - Intial coding.
1.0.0 - 09/14/2022 - Updated & fixed code.
2.0.0 - 12/8/2022 - Modified to allow for grading boundaries
"""

'''MIT License

Copyright (c) 2018 David Hostetler

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

''' Modified by Matthew Gagne - KiloNewton LLC'''

__author__      = ["Matthew Gagne", "Zane Nordquist"]
__copyright__   = "Copyright 2023, KiloNewton, LLC"
__credits__     = ["Matthew Gagne", "Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal/Commercial"
__ArcVersion__  = "ArcPro 3.0.3"
__maintainer__  = ["Matthew Gagne", "Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import sys
import os
import shapefile
import lxml.etree as ET
from arcpy.sa import *
from arcpy.ddd import *

class LXMLExport(object):
    def __init__(self):
        self.label = "Export Graded Raster Surface to LandXML"
        self.description = "Exports a raster surface to a LandXML"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Civil Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input graded surface raster dataset",
            name="demInput",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input existing surface raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Use pile elevations as reference points?",
            name="pileOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param2.value = False

        param3 = arcpy.Parameter(
            displayName="Input pile feature class",
            name="pilesInput",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param3.filter.list = ["Point"]

        param4 = arcpy.Parameter(
            displayName="Graded elevation field",
            name="gradeField",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param4.parameterDependencies = [param3.name]

        param5 = arcpy.Parameter(
            displayName="Use grading boundary polygon?",
            name="boundOption",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param5.value = False

        param6 = arcpy.Parameter(
            displayName="Grading boundaries",
            name="gradeBounds",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        param6.filter.list = ["Polygon"]

        param7 = arcpy.Parameter(
            displayName="Output LandXML file",
            name="out_xml",
            datatype="DEFile",
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

        if parameters[2].value == True:
            parameters[3].enabled = True
            parameters[4].enabled = True
        else:
            parameters[3].enabled = False
            parameters[4].enabled = False

        if parameters[5].value == True:
            parameters[6].enabled = True
        else:
            parameters[6].enabled = False

        if parameters[7].altered:
            (dirnm, basenm) = os.path.split(parameters[7].valueAsText)
            if not basenm.endswith(".xml"):
                parameters[7].value = os.path.join(dirnm, "{}.xml".format(basenm))

        if not parameters[7].altered:
            parameters[7].value = 'demGrade_LXML.xml'

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
        demInput = parameters[0].valueAsText
        demExist = parameters[1].valueAsText
        pileOption = parameters[2].value
        pilesInput = parameters[3].valueAsText
        gradeField = parameters[4].valueAsText
        boundOption = parameters[5].value
        gradeBounds = parameters[6].valueAsText
        out_xml = parameters[7].valueAsText

        outputPath = os.path.dirname(workspace)
        tempDir = arcpy.management.CreateFolder(outputPath, "lxml_temp")
        tempDirOut = outputPath + "/lxml_temp"

        gridRes = arcpy.Describe(demExist).meanCellWidth
        spatialRef = arcpy.Describe(demExist).spatialReference
        mapUnits = spatialRef.linearUnitName

        arcpy.SetProgressor('default', "Analyzing the raster...")

        if boundOption == False:
            arcpy.SetProgressor('default', "Creating the grading boundaries...")

            if "Foot" in mapUnits:
                buffDist = str(gridRes) + " Feet"
            else: 
                buffDist = str(gridRes) + " Meter"
            preBound = arcpy.ddd.RasterDomain(demInput, "preBound", "POLYGON")
            preBoundBuffer = arcpy.analysis.PairwiseBuffer(preBound, "preBoundBuffer", "4 Feet")
            preBoundBuffSimp = arcpy.cartography.SimplifyPolygon(preBoundBuffer,"preBoundBuffSimp", "POINT_REMOVE", buffDist, "", "", "NO_KEEP")
            gradBounds_buff_in = arcpy.analysis.PairwiseBuffer(preBoundBuffSimp, "gradBounds_buff_in", "-4 Feet")
            gradeBoundsInput = arcpy.analysis.PairwiseBuffer(gradBounds_buff_in, "gradeBoundsInput", buffDist)

            # Clean up
            arcpy.management.Delete(gradBounds_buff_in)
            arcpy.management.Delete(preBoundBuffSimp)
            arcpy.management.Delete(preBoundBuffer)
            arcpy.management.Delete(preBound)

        else: 
            gradeBoundsInput = arcpy.conversion.FeatureClassToFeatureClass(gradeBounds, workspace,"gradeBoundsInput")

        # Convert the bounds to a line and interpolate the existing surface 
        gradeBoundsLine = arcpy.management.FeatureToLine(gradeBoundsInput, "gradeBoundsLine", None, "ATTRIBUTES")

        if gridRes < 2:
            sampleDist = 1
        else:
            sampleDist = gridRes/2

        gradeBounds_3D = arcpy.sa.InterpolateShape(demExist, gradeBoundsLine, "gradeBounds_3D", sampleDist, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

        if pileOption == False:
            arcpy.SetProgressor('default', "Generating internal reference points...")
            if "Foot" in mapUnits:
                ptDist = str(sampleDist*2) + " Feet"
            else: 
                ptDist = str(sampleDist*2) + " Meter"
            halfFtContour = arcpy.sa.Contour(demInput, "halfFtContour", .5)
            halfFtContourPT = arcpy.management.GeneratePointsAlongLines(halfFtContour, "halfFtContourPT", "DISTANCE", ptDist, None, "END_POINTS")

            # Create a TIN of the surface and clip to the grade bounds
            arcpy.SetProgressor('default', "Creating a TIN surface...")
            tinGradeName = str(outputPath + "\demGrade")
            tinInput = "gradeBounds_3D Shape.Z Hard_Line <None>; halfFtContourPT Contour Mass_Points <None>"
            gradeTIN = arcpy.ddd.CreateTin(tinGradeName, spatialRef,  tinInput, "DELAUNAY")
            arcpy.ddd.EditTin(gradeTIN, "gradeBoundsInput <None> <None> Hard_Clip false", "DELAUNAY")

            # Clean up
            arcpy.management.Delete(halfFtContour)
            arcpy.management.Delete(halfFtContourPT)


        if pileOption == True:
            arcpy.SetProgressor('default', "Selecting piles within grading boundaries...")
            arcpy.management.CalculateField(pilesInput, "gradeTemp", '(!'+gradeField+'!)', 'PYTHON3',"", "DOUBLE")
            # Select piles within graded boundaries
            gradedPilesSelect = arcpy.management.SelectLayerByLocation(pilesInput, "INTERSECT", gradeBoundsInput, None, "NEW_SELECTION", "NOT_INVERT")
            gradedPiles = arcpy.conversion.FeatureClassToFeatureClass(gradedPilesSelect,workspace,"gradedPiles")

            # Create a TIN of the surface and clip to the grade bounds
            arcpy.SetProgressor('default', "Creating a TIN surface...")
            tin_name_piles = str(outputPath + "\piles_TIN")
            piles_TIN = arcpy.ddd.CreateTin(tin_name_piles, spatialRef, "gradedPiles gradeTemp Mass_Points")
            tinEdge_piles = arcpy.ddd.TinEdge(piles_TIN, r"in_memory\tinEdge_piles", "REGULAR")
            tinEdge_piles_select = arcpy.management.SelectLayerByLocation(tinEdge_piles, "INTERSECT", gradeBoundsLine,None, "NEW_SELECTION", "INVERT")
            tinEdge_final = arcpy.conversion.FeatureClassToFeatureClass(tinEdge_piles_select, workspace,"tinEdge_final")

            tinGradeName = str(outputPath + "\demGrade")
            tinInput = "gradeBounds_3D Shape.Z Hard_Line <None>; tinEdge_final Shape.Z Hard_Line <None>"
            gradeTIN = arcpy.ddd.CreateTin(tinGradeName, spatialRef,  tinInput, "DELAUNAY")
            arcpy.ddd.EditTin(gradeTIN, "gradeBoundsInput <None> <None> Hard_Clip false", "DELAUNAY")

            arcpy.management.DeleteField(pilesInput, ["gradeTemp"])

            # Clean up
            arcpy.management.Delete(piles_TIN)
            arcpy.management.Delete(tinEdge_piles)
            arcpy.management.Delete(tinEdge_final)
            arcpy.management.Delete(gradedPiles)
            arcpy.management.Delete(gradedPiles)

        arcpy.SetProgressor('default', "Converting TIN to LandXML...")

        # Convert to TIN Triangles
        tinTriangle = arcpy.ddd.TinTriangle(gradeTIN, "tinTriangle", "PERCENT", 1, '', '')

        # Convert tinTriangle to shapefile
        tinShapefile = arcpy.conversion.FeatureClassToShapefile(tinTriangle, tempDir)

        tin_shp = str(tempDirOut + "/tinTriangle")

        # Reading input TIN shapefile using PyShp
        in_shp = shapefile.Reader(tin_shp)
        shapeRecs = in_shp.shapeRecords()

        # Initializing landxml surface items
        namespace = {'xsi' : "http://www.w3.org/2001/XMLSchema"}
        landxml = ET.Element('LandXML',
                             nsmap=namespace,
                             xmlns="http://www.landxml.org/schema/LandXML-1.2",
                             language = 'English',
                             readOnly = 'false',
                             time = '08:00:00',
                             date = '2019-01-01',
                             version="1.2")
        units = ET.SubElement(landxml, 'Units')
        surfaces = ET.SubElement(landxml, 'Surfaces')
        surface = ET.SubElement(surfaces, 'Surface', name="demGrade")
        definition = ET.SubElement(surface, 'Definition',
                                   surfType="TIN")
        pnts = ET.SubElement(definition, 'Pnts')
        faces = ET.SubElement(definition, 'Faces')

        # Dictionary to define correct units based on input
        unit_opt = {'ft':('Imperial', 'squareFoot', 'USSurveyFoot',
                          'cubicFeet', 'fahrenheit', 'inHG'),
                    'm': ('Metric', 'squareMeter', 'meter',
                          'cubicMeter', 'celsius', 'mmHG'),
                    'ft-int': ('Imperial', 'squareFoot', 'foot',
                               'cubicFeet', 'fahrenheit', 'inHG')}

        unit_len = "ft"

        # Define units here. Has not been tested with metric.
        unit = ET.SubElement(units,
                             unit_opt[unit_len][0],
                             areaUnit=unit_opt[unit_len][1],
                             linearUnit=unit_opt[unit_len][2],
                             volumeUnit=unit_opt[unit_len][3],
                             temperatureUnit=unit_opt[unit_len][4],
                             pressureUnit=unit_opt[unit_len][5])

        # Initializing output variables
        pnt_dict = {}
        face_list = []
        cnt = 0

        # Creating reference point dictionary/id for each coordinate
        # As well as LandXML points, and list of faces
        for sr in shapeRecs:
            shape_pnt_ids = []   # id of each shape point

            # Each shape should only have 3 points
            for pnt in range(3):   
                # Coordinate with y, x, z format
                coord = (sr.shape.points[pnt][1],
                         sr.shape.points[pnt][0],
                         sr.shape.z[pnt])

                # If element is new, add to dictionary and
                # write xml point element
                if coord not in pnt_dict:
                    cnt+=1
                    pnt_dict[coord] = cnt

                    shape_pnt_ids.append(cnt)  # Add point id to list 

                    # Individual point landxml features
                    pnt_text = f'{coord[0]:.5f} {coord[1]:.5f} {coord[2]:.3f}'
                    pnt = ET.SubElement(pnts, 'P', id=str(cnt)).text = pnt_text

                # If point is already in the point dictionary, append existing point id
                else:
                    shape_pnt_ids.append(pnt_dict[coord])

            # Check if too many or too few points created
            if len(shape_pnt_ids) != 3:
                print('Error - check input shapefile. '\
                      'Must be a polygon with only three nodes for each shape.')
                sys.exit(0)

            # Reference face list for each shape
            face_list.append(shape_pnt_ids)

        # Writing faces to landxml
        for face in face_list:
            ET.SubElement(faces, 'F').text = f'{face[0]} {face[1]} {face[2]}'

        arcpy.SetProgressor('default', "Writing output file...")

        # Writing output
        tree = ET.ElementTree(landxml)
        tree.write(out_xml, pretty_print=True, xml_declaration=True, encoding="iso-8859-1")

        del tinShapefile
        del in_shp
        del shapeRecs

        arcpy.management.Delete(tempDir)
        arcpy.management.Delete(tinTriangle)
        arcpy.management.Delete(gradeBoundsLine)
        arcpy.management.Delete(gradeBoundsInput)
        arcpy.management.Delete(gradeBounds_3D)
        arcpy.management.Delete(gradeTIN)

        arcpy.AddMessage("LandXML Exported Successfully")

        arcpy.ResetProgressor()

        return


