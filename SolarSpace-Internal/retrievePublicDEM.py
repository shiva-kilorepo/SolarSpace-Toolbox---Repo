#########################################################################
""" Retrieve Public DEM Raster dataset

Revision log
0.0.1 - 11/31/2023 - Drafting of tool
0.1.0 - 12/1/2023 - Intial conversion to ArcPro/.pyt format
1.0.0 - 4/1/2024 - Initial deployment

"""

__author__      = "Zane Nordquist"
__copyright__   = "Copyright 2024, KiloNewton, LLC"
__credits__     = ["Zane Nordquist", "John Williamson"]
__version__     = "1.0.0"
__license__     = "Internal"
__ArcVersion__  = "ArcPro 3.2.1"
__maintainer__  = ["Zane Nordquist"]
__status__      = "Deployed"

# Load modules
import arcpy
import os.path
import sys
from arcpy.sa import *
from arcpy.ddd import *
import arcpy
from arcpy.sa import *
import os
import requests

class retrievePublicDEM(object):

    def __init__(self):
        self.label = "Retrieve Public DEM Raster dataset"
        self.description = "Find and download a public DEM raster dataset from the USGS National Map or world image server."
        self.alias = "retrievePublicDEM"
        self.canRunInBackground = False
        self.category = "Site Suitability\Data Retrieval"

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input project area",
            name="projectArea",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Output dataset name",
            name="outputName",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")
        
        param2 = arcpy.Parameter(
            displayName="Vertical elevation units",
            name="xyzUnit",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Foot", "Meter"]

        param3 = arcpy.Parameter(
            displayName="Data source to perfer in search", 
            name="dataSource",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["USGS"]
        #param3.filter.list = ["USGS", "World Imagery"]

        param4 = arcpy.Parameter(
            displayName="Size to resample output raster to", 
            name="resample_size",
            datatype="Long",
            parameterType="Required",
            direction="Input")

        params = [param0, param1, param2, param3, param4]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        if not parameters[1].altered:
            parameters[1].value = f'prelim_demExist'

        if not parameters[2].altered:
            parameters[2].value = 'Foot'
        
        if not parameters[3].altered:
            parameters[3].value = 'USGS'
        
        if not parameters[4].altered:
            parameters[4].value = 2
            
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
        projectArea = parameters[0].valueAsText  # Input project area feature class
        outputName = parameters[1].valueAsText  # output raster dataset name
        xyzUnit = parameters[2].valueAsText  # Vertical elevation units
        dataSource = parameters[3].valueAsText # Data source to perfer in search
        resample_size = parameters[4].valueAsText  # Resample size for the raster
        
        # Ensure Spatial Analyst license is checked out
        arcpy.CheckOutExtension("Spatial")
        
        # set desc & extent variables
        desc = arcpy.Describe(projectArea)
        extent = desc.extent
        
        # convert extent to bbox #bbox=<xmin>,<ymin>,<xmax>,<ymax>
        bbox = str(extent.XMin) + ',' + str(extent.YMin) + ',' + str(extent.XMax) + ',' + str(extent.YMax)
        arcpy.AddMessage(f'Bounding Box: {bbox}')

        # get sr of project area
        sr = desc.spatialReference
        arcpy.AddMessage(f'Project area spatial reference: {sr}')

        # Specify the URL of the image service
        if dataSource == 'USGS':
            arcpy.AddMessage('Using USGS data source.')
            image_service_url = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
            sr = str(sr.factoryCode)
        elif dataSource == 'World Imagery':
            arcpy.AddMessage('Using World Imagery data source.')
            image_service_url = "https://elevation.arcgis.com/arcgis/rest/services/WorldElevation/Terrain/ImageServer"
            sr = 3857 # if your input feature class aligns with World Imagery
        else:
            image_service_url = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
            sr = str(sr.factoryCode)
            arcpy.AddWarning('Data source not recognized. Using USGS data source.')
        
        # Edit the url to export the image
        arcpy.SetProgressor('default', 'Sending in html request...')
        image_service_url = f'{image_service_url}/exportImage?f=image&bbox={bbox}&bboxSR={sr}&imageSR={sr}&size=1000,1000&format=tiff&pixelType=F32&noData=0'
        
        arcpy.AddMessage(f'Image service URL: {image_service_url}')

        # send in the request
        try:
            response = requests.get(image_service_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            arcpy.AddError(err)
            return

        # create temp folder to store the image (one step below the workspace)
        temp_folder = os.path.join((os.path.dirname(workspace)), 'temp')
        
        # check if the temp folder exists and create it if it doesn't
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        
        # send in the request
        arcpy.SetProgressor('default', 'Downloading image...')
        response = requests.get(image_service_url)
        
        # write the image to the temp folder if the request is successful
        if response.status_code == 200:
            arcpy.AddMessage('Image successfully retrieved.')
            # Write content to file
            output_temp = f'{temp_folder}/outputName_raw.tif'
        else:
            arcpy.AddError('Failed to retrieve data: Status Code {response.status_code}')
                    
        # Output name raw (no dir)
        output_basename = os.path.basename(outputName)
        
        # Save the output in the geodatabase
        with open(output_temp, 'wb') as f:
            f.write(response.content)

            # save the image
            output_gdb = f'in_memory\{output_basename}_raw'
            arcpy.CopyRaster_management(output_temp, output_gdb, pixel_type='32_BIT_FLOAT', nodata_value=0)

        # clip the raster to the project area
        arcpy.SetProgressor('default', 'Clipping raster to project area...')
        output_gdb_clip = f'in_memory\{output_basename}_clip'
        
        # clip the image to the project area
        arcpy.management.Clip(
            in_raster = output_gdb,
            out_raster = output_gdb_clip,
            in_template_dataset = projectArea,
            nodata_value = "0",
            clipping_geometry = 'ClippingGeometry',
            maintain_clipping_extent = "NO_MAINTAIN_EXTENT")
        
        # resample the raster to resolution
        output_gdb_resample = f'in_memory\{output_basename}_resample'
        arcpy.Resample_management(output_gdb_clip, output_gdb_resample, f'{resample_size} {resample_size}', 'BILINEAR')

        # convert the raster to unit if the user specifies
        # if the user specifies meters, then the raster is already in meters
        arcpy.SetProgressor('default', 'Converting raster to specified units...')
        if xyzUnit == 'Foot':
            # multiple the raster by 3.28084 to convert from meters to feet
            output_gdb_times = f'{workspace}\{output_basename}'
            arcpy.Times_3d(output_gdb_resample, 3.28084, output_gdb_times)
        else:
            output_gdb_times = f'{workspace}\{output_basename}'
            arcpy.CopyRaster_management(output_gdb_resample, output_gdb_times, pixel_type='32_BIT_FLOAT', nodata_value=0)
        arcpy.AddMessage(f'Raster converted to {xyzUnit}')

        # add the raster to the map
        aprxMap.addDataFromPath(output_gdb_times)
        
        # clean up
        arcpy.arcpy.SetProgressor('default', 'Cleaning up...')
        arcpy.ResetProgressor()
        arcpy.management.Delete(output_gdb)
        arcpy.management.Delete(output_gdb_clip)
        arcpy.management.Delete(output_gdb_resample)
        
        # remove the temp folder
        try:
            os.remove(output_temp)
        except:
            pass
        os.rmdir(temp_folder)
        
        ### Templates for error reporting ###
        
        # # Create a search cursor
        # try:
        #     with arcpy.da.SearchCursor(input, fields) as cursor:
        #         for row in cursor:
        #             data.append(list(row))
                    
        # except Exception as e:
        #     arcpy.AddError("Error while reading the input file: " + str(e))
        #     return
        
        # # check if the temp_table already exists and delete it if it does
        # if arcpy.Exists(os.path.join(workspace, "temp_table")):
        #     arcpy.management.Delete(os.path.join(workspace, "temp_table"))
        
        # arcpy.AddMessage(f'Adjusting rows: {row_IDs}')

        # arcpy.SetProgressor('default', 'Converting data to feature...')
        
        # # Delete the temp_table
        # arcpy.management.Delete(os.path.join(workspace, "temp_table"))
        
        # arcpy.ResetProgressor()
        # #arcpy.AddMessage("Rows and piles adjusted")
        
        # aprxMap.addDataFromPath(output_name)
        
        
        
        return
