############################################################
"""EXPORT PILES AND GRADE BOUNDS TO TO LANDXML 

Revision log
1.0.0 - 01/06/2023 - Adopted from expor raster to landxml script
"""



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

class LXMLExportPilesBounds(object):
    def __init__(self):
        self.label = "Export Piles and Grade Bounds to LandXML"
        self.description = "Exports a piles and grading boundaries to a LandXML"
        self.canRunInBackground = False
        self.category = "Civil Analysis\Civil Utilities"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input existing surface raster dataset",
            name="demExist",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input pile feature class",
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
            displayName="Grading boundaries",
            name="gradeBounds",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ["Polygon"]

        param4 = arcpy.Parameter(
            displayName="Output LandXML file",
            name="out_xml",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[4].altered:
            (dirnm, basenm) = os.path.split(parameters[4].valueAsText)
            if not basenm.endswith(".xml"):
                parameters[4].value = os.path.join(dirnm, "{}.xml".format(basenm))

        if not parameters[4].altered:
            parameters[4].value = 'demGrade_LXML.xml'

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
        demExist = parameters[0].valueAsText
        pilesInput = parameters[1].valueAsText
        gradeField = parameters[2].valueAsText
        gradeBounds = parameters[3].valueAsText
        out_xml = parameters[4].valueAsText

        outputPath = os.path.dirname(workspace)
        tempDir = arcpy.management.CreateFolder(outputPath, "lxml_temp")
        tempDirOut = outputPath + "/lxml_temp"

        gridRes = arcpy.Describe(demExist).meanCellWidth
        spatialRef = arcpy.Describe(demExist).spatialReference
        mapUnits = spatialRef.linearUnitName

        arcpy.SetProgressor('default', "Analyzing the inputs...")

        gradeBoundsInput = arcpy.conversion.FeatureClassToFeatureClass(gradeBounds, workspace,"gradeBoundsInput")

        # Convert the bounds to a line and interpolate the existing surface 
        gradeBoundsLine = arcpy.management.FeatureToLine(gradeBoundsInput, "gradeBoundsLine", None, "ATTRIBUTES")

        if gridRes < 2:
            sampleDist = 1
        else:
            sampleDist = gridRes/2

        gradeBounds_3D = arcpy.sa.InterpolateShape(demExist, gradeBoundsLine, "gradeBounds_3D", sampleDist, 1, "BILINEAR", "DENSIFY", 0, "EXCLUDE")

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

        arcpy.AddMessage("LandXML Exported Successfully")

        arcpy.ResetProgressor()

        return


