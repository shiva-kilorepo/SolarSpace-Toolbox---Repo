
# Set workspace environment
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
aprx = arcpy.mp.ArcGISProject("CURRENT")
aprxMap = aprx.activeMap

# Set parameters
wrk = 
demInput            = parameters[0].valueAsText  
projectBoundary     = parameters[1].valueAsText
rowsInput           = parameters[2].valueAsText
row_ID              = parameters[3].valueAsText
pilesInput          = parameters[4].valueAsText 
xyzUnit             = parameters[5].valueAsText
minReveal           = parameters[6].valueAsText
maxReveal           = parameters[7].valueAsText
#GCR                 = parameters[8].valueAsText
maxMean             = parameters[9].valueAsText
tracker_length      = parameters[10].valueAsText
tracker_width       = parameters[11].valueAsText
maxPileSpan         = parameters[12].valueAsText
maxHalfRow          = parameters[13].valueAsText
pilesRow            = parameters[14].valueAsText 
pilesHalfRow        = parameters[15].valueAsText
maxAngleSpan        = parameters[16].valueAsText
maxAngleHalfRow     = parameters[17].valueAsText
deflectionTolerance = parameters[18].valueAsText
safetyFactor        = parameters[19].valueAsText 
gradeMin            = parameters[20].valueAsText
gradeOut            = parameters[21].valueAsText
pileOutput          = parameters[22].valueAsText
gradeBoundsOut      = parameters[23].valueAsText


# Set grid resolution to the DEM raster and snap to raster
arcpy.env.snapRaster = demInput
rasRef = arcpy.Raster(demInput)
gridRes = arcpy.env.cellSize = rasRef.meanCellWidth
spatialRef = arcpy.Describe(demInput).spatialReference
outputPath = os.path.dirname(workspace)
mapUnits = spatialRef.linearUnitName

t1_length = float(tracker_length)
t2_length = float(tracker_length) * .75
t3_length = float(maxHalfRow) 
t4_length = float(maxHalfRow) * 0.5   
t5_length = float(maxPileSpan)

revWindow = (float(maxReveal) - float(minReveal))
arcpy.AddMessage("Reveal tolerance: " + str(revWindow) + " " + mapUnits)
spacing = revWindow / 2

# Calculate thetas
if ((int(pilesRow) - 1) * float(maxAngleSpan)) > (t1_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_1 = (float(maxAngleHalfRow) * t1_length / t3_length) * float(deflectionTolerance)/2
if ((int(pilesRow) - 1) * float(maxAngleSpan)) < (t1_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_1 = (float(maxAngleSpan) * (int(pilesRow) - 1)) * float(deflectionTolerance)/2

if ((int(pilesRow) - 1) * float(maxAngleSpan)) > (t2_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_2 = (float(maxAngleHalfRow) * t2_length / t3_length) * float(deflectionTolerance)/2
if ((int(pilesRow) - 1) * float(maxAngleSpan)) < (t2_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_2 = (float(maxAngleSpan) * (int(pilesRow) - 1)) * float(deflectionTolerance)/2

if ((int(pilesRow) - 1) * float(maxAngleSpan)) > (t3_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_3 = (float(maxAngleHalfRow) * t3_length / t3_length) * float(deflectionTolerance)/2
if ((int(pilesRow) - 1) * float(maxAngleSpan)) < (t3_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_3 = (float(maxAngleSpan) * (int(pilesRow) - 1)) * float(deflectionTolerance)/2

if ((int(pilesRow) - 1) * float(maxAngleSpan)) > (t4_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_4 = (float(maxAngleHalfRow) * t4_length / t3_length) * float(deflectionTolerance)/2
if ((int(pilesRow) - 1) * float(maxAngleSpan)) < (t4_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_4 = (float(maxAngleSpan) * (int(pilesRow) - 1)) * float(deflectionTolerance)/2

if ((int(pilesRow) - 1) * float(maxAngleSpan)) > (t5_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_5 = (float(maxAngleHalfRow) * t5_length / t3_length) * float(deflectionTolerance)/2
if ((int(pilesRow) - 1) * float(maxAngleSpan)) < (t5_length/float(maxHalfRow) * float(maxAngleHalfRow)):
    theta_5 = (float(maxAngleSpan) * (int(pilesRow) - 1)) * float(deflectionTolerance)/2

r_1 =  t1_length / (2 * math.sin(theta_1 * math.pi / 180))
d_1 = math.sqrt(r_1**2 - t1_length**2 / 4)
h_1 = r_1 - d_1 + revWindow
t1_range = h_1 * float(safetyFactor)

r_2 =  t2_length / (2 * math.sin(theta_2 * math.pi / 180))
d_2 = math.sqrt(r_2**2 - t2_length**2 / 4)
h_2 = r_2 - d_2 + revWindow
t2_range = h_2 * float(safetyFactor)

r_3 =  t3_length / (2 * math.sin(theta_3 * math.pi / 180))
d_3 = math.sqrt(r_3**2 - t3_length**2 / 4)
h_3 = r_3 - d_3 + revWindow
t3_range = h_3 * float(safetyFactor)

r_4 =  t4_length / (2 * math.sin(theta_4 * math.pi / 180))
d_4 = math.sqrt(r_4**2 - t4_length**2 / 4)
h_4 = r_4 - d_4 + revWindow
t4_range = h_4 * float(safetyFactor)

r_5 =  t5_length / (2 * math.sin(theta_5 * math.pi / 180))
d_5 = math.sqrt(r_5**2 - t5_length**2 / 4)
h_5 = r_5 - d_5 + revWindow
t5_range = h_5 * float(safetyFactor)

arcpy.SetProgressor("default", "Defining the project array boundary...")

pileName = os.path.basename(pileOutput)
piles_working = arcpy.conversion.FeatureClassToFeatureClass(pilesInput, workspace, pileName)
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[demInput, "demExist"]], "BILINEAR")

# Define analysis width as the center-to-center distance divided by 2
analysis_width = (float(tracker_width) / (float(GCR) / 100)) / 2
rowDomainExpand = analysis_width / -1.5

# Create the row domain
if xyzUnit == "Foot":
    boundExpandInput = str(float(tracker_length)/2) + " Feet"
if xyzUnit == "Meter":
    boundExpandInput = str(float(tracker_length)/2) + " Meters"

boundsExpand = arcpy.analysis.GraphicBuffer(projectBoundary, "boundsExpand", boundExpandInput, "SQUARE", "MITER", 10,"0 Feet")

# Make a grid of the site at the analysis width
grid_project = arcpy.cartography.GridIndexFeatures("grid_project", boundsExpand, "INTERSECTFEATURE", "NO_USEPAGEUNIT", None, analysis_width, analysis_width)

# Convert to point
grid_project_point = arcpy.management.FeatureToPoint(grid_project, "grid_project_point")

# Add XY to label points
arcpy.management.AddXY(grid_project_point)

# Create a raster of the northings
northing_raster = arcpy.conversion.PointToRaster(grid_project_point, "POINT_Y", "northing_raster", "MOST_FREQUENT", "NONE", analysis_width, "BUILD")

# Resample the northings to the existing elevation
reSampDist = str(str(gridRes) + " " + str(gridRes))
with arcpy.EnvManager(snapRaster=demInput):
    northResamplePre = arcpy.management.Resample(northing_raster, "northResamplePre", reSampDist, "NEAREST")

northResample = arcpy.management.Clip(northResamplePre, "", "northResample", boundsExpand, "3.4e+38","ClippingGeometry", "NO_MAINTAIN_EXTENT")

demInputClip = arcpy.management.Clip(demInput, "", "demInputClip", boundsExpand, "3.4e+38","ClippingGeometry", "NO_MAINTAIN_EXTENT")

arcpy.SetProgressor("default", "Analyzing the terrain...")

# Get the directional NS slope of the DEM
# Process aspect
AspectDeg_t1 = arcpy.sa.SurfaceParameters(
    in_raster=demInputClip,
    parameter_type="ASPECT",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

AspectRad_t1 = AspectDeg_t1 * math.pi / 180

# Run focal statistics (mean) on the input elevation based on the t1 inputs
focal_input_t1 = str("Rectangle " + str(analysis_width) + " " + str(t1_length) + " MAP")
demFocal_t1 = arcpy.sa.FocalStatistics(
    in_raster=demInputClip,
    neighborhood=focal_input_t1,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Process slope
SlopeDeg_t1 = arcpy.sa.SurfaceParameters(
    in_raster=demInputClip,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

SlopeRad_t1 = SlopeDeg_t1 * math.pi / 180

# Process north-south slope in radians
CosAspRad_t1 = Cos(AspectRad_t1)
nsRad_t1 = CosAspRad_t1 * SlopeRad_t1

# Process north-south slope in percent if option chosen
nsPerc_t1 = Tan(nsRad_t1)

# Run focal statistics (mean) on the NS slope
nsFocal_t1 = arcpy.sa.FocalStatistics(
    in_raster=nsPerc_t1,
    neighborhood=focal_input_t1,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Focal statistics on the northings
yFocal_t1 = arcpy.sa.FocalStatistics(
    in_raster=northResample,
    neighborhood=focal_input_t1,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Calculate the "intercept" b
intB_t1 = demFocal_t1 - nsFocal_t1 * yFocal_t1

# Calculate a "trend"
tPrelim_t1 = nsFocal_t1 * northResample + intB_t1

# Subtract the existing elevation from the trend
trend_dem_t1 = arcpy.sa.Minus(tPrelim_t1, demInputClip)

# Run focal statistics on trend_dem based on the row width
focal_trend_dem_input = str("Rectangle " + str(analysis_width) + " " + str(analysis_width) + " MAP")

# Potentially change to maximum
initGrade_t1 = arcpy.sa.FocalStatistics(
    in_raster=trend_dem_t1,
    neighborhood=focal_trend_dem_input,
    statistics_type=maxMean,
    ignore_nodata="DATA",
    percentile_value=90
)

initSurface_t1 = arcpy.management.MosaicToNewRaster(
    input_rasters=[demInputClip, initGrade_t1],
    output_location = workspace,
    raster_dataset_name_with_extension="initSurface_t1",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="SUM",
    mosaic_colormap_mode="FIRST"
)

# Create the upper bound
revToleranceHalf_t1 = float(t1_range)/2
upperLimit_t1 = arcpy.sa.Plus(initSurface_t1, revToleranceHalf_t1)

upperBound_t1 = arcpy.management.MosaicToNewRaster(
    input_rasters=[demInputClip, upperLimit_t1],
    output_location = workspace,
    raster_dataset_name_with_extension="upperBound_t1",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MINIMUM",
    mosaic_colormap_mode="FIRST"
)


lowerLimit_t1 = arcpy.sa.Minus(initSurface_t1, revToleranceHalf_t1)

lowerBound_t1 = arcpy.management.MosaicToNewRaster(
    input_rasters=[demInputClip, lowerLimit_t1],
    output_location = workspace,
    raster_dataset_name_with_extension="lowerBound_t1",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MAXIMUM",
    mosaic_colormap_mode="FIRST"
)

# Create the t1 surface
upperGrade_t1 = arcpy.sa.Minus(upperBound_t1, demInputClip)
t1_surface = arcpy.sa.Plus(lowerBound_t1, upperGrade_t1)
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[t1_surface, "t1_surface"]], "BILINEAR")

############################
# Start the second iteration

# Get the directional NS slope of the DEM
# Process aspect
AspectDeg_t2 = arcpy.sa.SurfaceParameters(
    in_raster=t1_surface,
    parameter_type="ASPECT",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

AspectRad_t2 = AspectDeg_t2 * math.pi / 180

# Run focal statistics (mean) on the input elevation based on the t2 inputs
focal_input_t2 = str("Rectangle " + str(analysis_width) + " " + str(t2_length) + " MAP")
demFocal_t2 = arcpy.sa.FocalStatistics(
    in_raster=t1_surface,
    neighborhood=focal_input_t2,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Process slope
SlopeDeg_t2 = arcpy.sa.SurfaceParameters(
    in_raster=t1_surface,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

SlopeRad_t2 = SlopeDeg_t2 * math.pi / 180

# Process north-south slope in radians
CosAspRad_t2 = Cos(AspectRad_t2)
nsRad_t2 = CosAspRad_t2 * SlopeRad_t2

# Process north-south slope in percent if option chosen
nsPerc_t2 = Tan(nsRad_t2)

# Run focal statistics (mean) on the NS slope
nsFocal_t2 = arcpy.sa.FocalStatistics(
    in_raster=nsPerc_t2,
    neighborhood=focal_input_t2,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Focal statistics on the northings
yFocal_t2 = arcpy.sa.FocalStatistics(
    in_raster=northResample,
    neighborhood=focal_input_t2,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Calculate the "intercept" b
intB_t2 = demFocal_t2 - nsFocal_t2 * yFocal_t2

# Calculate a "trend"
tPrelim_t2 = nsFocal_t2 * northResample + intB_t2

# Subtract the existing elevation from the trend
trend_dem_t2 = arcpy.sa.Minus(tPrelim_t2, t1_surface)

initGrade_t2 = arcpy.sa.FocalStatistics(
    in_raster=trend_dem_t2,
    neighborhood=focal_trend_dem_input,
    statistics_type=maxMean,
    ignore_nodata="DATA",
    percentile_value=90
)
    
initSurface_t2 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t1_surface, initGrade_t2],
    output_location = workspace,
    raster_dataset_name_with_extension="initSurface_t2",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="SUM",
    mosaic_colormap_mode="FIRST"
)

# Create the upper bound
revToleranceHalf_t2 = float(t2_range)/2
upperLimit_t2 = arcpy.sa.Plus(initSurface_t2, revToleranceHalf_t2)

upperBound_t2 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t1_surface, upperLimit_t2],
    output_location = workspace,
    raster_dataset_name_with_extension="upperBound_t2",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MINIMUM",
    mosaic_colormap_mode="FIRST"
)

lowerLimit_t2 = arcpy.sa.Minus(initSurface_t2, revToleranceHalf_t2)

lowerBound_t2 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t1_surface, lowerLimit_t2],
    output_location = workspace,
    raster_dataset_name_with_extension="lowerBound_t2",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MAXIMUM",
    mosaic_colormap_mode="FIRST"
)

# Create the t2 surface
upperGrade_t2 = arcpy.sa.Minus(upperBound_t2, t1_surface)
t2_surface = arcpy.sa.Plus(lowerBound_t2, upperGrade_t2)
t2_surface.save("t2_surface")
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[t2_surface, "t2_surface"]], "BILINEAR")

############################
# Start the third iteration

# Get the directional NS slope of the DEM
# Process aspect
AspectDeg_t3 = arcpy.sa.SurfaceParameters(
    in_raster=t2_surface,
    parameter_type="ASPECT",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

AspectRad_t3 = AspectDeg_t3 * math.pi / 180

# Run focal statistics (mean) on the input elevation based on the t3 inputs
focal_input_t3 = str("Rectangle " + str(analysis_width) + " " + str(t3_length) + " MAP")
demFocal_t3 = arcpy.sa.FocalStatistics(
    in_raster=t2_surface,
    neighborhood=focal_input_t3,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Process slope
SlopeDeg_t3 = arcpy.sa.SurfaceParameters(
    in_raster=t2_surface,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

SlopeRad_t3 = SlopeDeg_t3 * math.pi / 180

# Process north-south slope in radians
CosAspRad_t3 = Cos(AspectRad_t3)
nsRad_t3 = CosAspRad_t3 * SlopeRad_t3

# Process north-south slope in percent if option chosen
nsPerc_t3 = Tan(nsRad_t3)

# Run focal statistics (mean) on the NS slope 
nsFocal_t3 = arcpy.sa.FocalStatistics(
    in_raster=nsPerc_t3,
    neighborhood=focal_input_t3,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Focal statistics on the northings
yFocal_t3 = arcpy.sa.FocalStatistics(
    in_raster=northResample,
    neighborhood=focal_input_t3,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Calculate the "intercept" b
intB_t3 = demFocal_t3 - nsFocal_t3 * yFocal_t3

# Calculate a "trend"
tPrelim_t3 = nsFocal_t3 * northResample + intB_t3

# Subtract the existing elevation from the trend
trend_dem_t3 = arcpy.sa.Minus(tPrelim_t3, t2_surface)

initGrade_t3 = arcpy.sa.FocalStatistics(
    in_raster=trend_dem_t3,
    neighborhood=focal_trend_dem_input,
    statistics_type=maxMean,
    ignore_nodata="DATA",
    percentile_value=90
)
    
initSurface_t3 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t2_surface, initGrade_t3],
    output_location = workspace,
    raster_dataset_name_with_extension="initSurface_t3",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="SUM",
    mosaic_colormap_mode="FIRST"
)

# Create the upper bound
revToleranceHalf_t3 = float(t3_range)/2
upperLimit_t3 = arcpy.sa.Plus(initSurface_t3, revToleranceHalf_t3)

upperBound_t3 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t2_surface, upperLimit_t3],
    output_location = workspace,
    raster_dataset_name_with_extension="upperBound_t3",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MINIMUM",
    mosaic_colormap_mode="FIRST"
)

lowerLimit_t3 = arcpy.sa.Minus(initSurface_t3, revToleranceHalf_t3)

lowerBound_t3 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t2_surface, lowerLimit_t2],
    output_location = workspace,
    raster_dataset_name_with_extension="lowerBound_t3",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MAXIMUM",
    mosaic_colormap_mode="FIRST"
)

# Create the t3 surface
upperGrade_t3 = arcpy.sa.Minus(upperBound_t3, t2_surface)
t3_surface = arcpy.sa.Plus(lowerBound_t3, upperGrade_t3)
t3_surface.save("t3_surface")
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[t3_surface, "t3_surface"]], "BILINEAR")

############################
# Start the fourth iteration

# Get the directional NS slope of the DEM
# Process aspect
AspectDeg_t4 = arcpy.sa.SurfaceParameters(
    in_raster=t3_surface,
    parameter_type="ASPECT",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

AspectRad_t4 = AspectDeg_t4 * math.pi / 180

# Run focal statistics (mean) on the input elevation based on the t1 inputs
focal_input_t4 = str("Rectangle " + str(analysis_width) + " " + str(t4_length) + " MAP")
demFocal_t4 = arcpy.sa.FocalStatistics(
    in_raster=t3_surface,
    neighborhood=focal_input_t4,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Process slope
SlopeDeg_t4 = arcpy.sa.SurfaceParameters(
    in_raster=t3_surface,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

SlopeRad_t4 = SlopeDeg_t4 * math.pi / 180

# Process north-south slope in radians
CosAspRad_t4 = Cos(AspectRad_t4)
nsRad_t4 = CosAspRad_t4 * SlopeRad_t4

# Process north-south slope in percent
nsPerc_t4 = Tan(nsRad_t4)

# Run focal statistics (mean) on the NS slope 
nsFocal_t4 = arcpy.sa.FocalStatistics(
    in_raster=nsPerc_t4,
    neighborhood=focal_input_t4,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Focal statistics on the northings
yFocal_t4 = arcpy.sa.FocalStatistics(
    in_raster=northResample,
    neighborhood=focal_input_t4,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Calculate the "intercept" b
intB_t4 = demFocal_t4 - nsFocal_t4 * yFocal_t4

# Calculate a "trend"
tPrelim_t4 = nsFocal_t4 * northResample + intB_t4

# Subtract the existing elevation from the trend
trend_dem_t4 = arcpy.sa.Minus(tPrelim_t4, t3_surface)

initGrade_t4 = arcpy.sa.FocalStatistics(
    in_raster=trend_dem_t4,
    neighborhood=focal_trend_dem_input,
    statistics_type=maxMean,
    ignore_nodata="DATA",
    percentile_value=90
)
    
initSurface_t4 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t3_surface, initGrade_t4],
    output_location = workspace,
    raster_dataset_name_with_extension="initSurface_t4",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="SUM",
    mosaic_colormap_mode="FIRST"
)

# Create the upper bound
revToleranceHalf_t4 = float(t4_range)/2
upperLimit_t4 = arcpy.sa.Plus(initSurface_t4, revToleranceHalf_t4)

upperBound_t4 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t3_surface, upperLimit_t4],
    output_location = workspace,
    raster_dataset_name_with_extension="upperBound_t4",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MINIMUM",
    mosaic_colormap_mode="FIRST"
)

lowerLimit_t4 = arcpy.sa.Minus(initSurface_t4, revToleranceHalf_t4)

lowerBound_t4 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t3_surface, lowerLimit_t4],
    output_location = workspace,
    raster_dataset_name_with_extension="lowerBound_t4",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MAXIMUM",
    mosaic_colormap_mode="FIRST"
)

# Create the t4 surface
upperGrade_t4 = arcpy.sa.Minus(upperBound_t4, t3_surface)
t4_surface = arcpy.sa.Plus(lowerBound_t4, upperGrade_t4)
t4_surface.save("t4_surface")
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[t4_surface, "t4_surface"]], "BILINEAR")

############################
# Start the fifth iteration

# Get the directional NS slope of the DEM
# Process aspect
AspectDeg_t5 = arcpy.sa.SurfaceParameters(
    in_raster=t4_surface,
    parameter_type="ASPECT",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

AspectRad_t5 = AspectDeg_t5 * math.pi / 180

# Run focal statistics (mean) on the input elevation based on the t1 inputs
focal_input_t5 = str("Rectangle " + str(analysis_width) + " " + str(t5_length) + " MAP")
demFocal_t5 = arcpy.sa.FocalStatistics(
    in_raster=t4_surface,
    neighborhood=focal_input_t5,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Process slope
SlopeDeg_t5 = arcpy.sa.SurfaceParameters(
    in_raster=t4_surface,
    parameter_type="SLOPE",
    local_surface_type="QUADRATIC",
    use_adaptive_neighborhood="FIXED_NEIGHBORHOOD",
    z_unit=xyzUnit,
    output_slope_measurement="DEGREE",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    use_equatorial_aspect="NORTH_POLE_ASPECT",
    in_analysis_mask=None
)

SlopeRad_t5 = SlopeDeg_t5 * math.pi / 180

# Process north-south slope in radians
CosAspRad_t5 = Cos(AspectRad_t5)
nsRad_t5 = CosAspRad_t5 * SlopeRad_t5

# Process north-south slope in percent if option chosen
nsPerc_t5 = Tan(nsRad_t5)

# Run focal statistics (mean) on the NS slope
nsFocal_t5 = arcpy.sa.FocalStatistics(
    in_raster=nsPerc_t5,
    neighborhood=focal_input_t5,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Focal statistics on the northings
yFocal_t5 = arcpy.sa.FocalStatistics(
    in_raster=northResample,
    neighborhood=focal_input_t5,
    statistics_type="MEAN",
    ignore_nodata="DATA",
    percentile_value=90
)

# Calculate the "intercept" b
intB_t5 = demFocal_t5 - nsFocal_t5 * yFocal_t5

# Calculate a "trend"
tPrelim_t5 = nsFocal_t5 * northResample + intB_t5

# Subtract the existing elevation from the trend
trend_dem_t5 = arcpy.sa.Minus(tPrelim_t5, t4_surface)

# Potentially change to maximum
initGrade_t5 = arcpy.sa.FocalStatistics(
    in_raster=trend_dem_t5,
    neighborhood=focal_trend_dem_input,
    statistics_type=maxMean,
    ignore_nodata="DATA",
    percentile_value=90
)
    
initSurface_t5 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t4_surface, initGrade_t5],
    output_location = workspace,
    raster_dataset_name_with_extension="initSurface_t5",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="SUM",
    mosaic_colormap_mode="FIRST"
)

# Create the upper bound
revToleranceHalf_t5 = float(t5_range)/2
upperLimit_t5 = arcpy.sa.Plus(initSurface_t5, revToleranceHalf_t5)

upperBound_t5 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t4_surface, upperLimit_t5],
    output_location = workspace,
    raster_dataset_name_with_extension="upperBound_t5",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MINIMUM",
    mosaic_colormap_mode="FIRST"
)

lowerLimit_t5 = arcpy.sa.Minus(initSurface_t5, revToleranceHalf_t5)

lowerBound_t5 = arcpy.management.MosaicToNewRaster(
    input_rasters=[t4_surface, lowerLimit_t5],
    output_location = workspace,
    raster_dataset_name_with_extension="lowerBound_t5",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="MAXIMUM",
    mosaic_colormap_mode="FIRST"
)

# Create the t5 surface
upperGrade_t5 = arcpy.sa.Minus(upperBound_t5, t4_surface)
t5_surface = arcpy.sa.Plus(lowerBound_t5, upperGrade_t5)
t5_surface.save("t5_surface")
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[t5_surface, "t5_surface"]], "BILINEAR")

# Screen the surface
deltaFG_EG = arcpy.sa.Minus(t5_surface, demInputClip)

minGradeScreen_input = "VALUE > -" + gradeMin + " And VALUE < " + gradeMin

FG_pre = arcpy.sa.SetNull(deltaFG_EG, t5_surface, minGradeScreen_input)

FG_EG_pre = arcpy.management.MosaicToNewRaster(
    input_rasters=[demInputClip, FG_pre],
    output_location = workspace,
    raster_dataset_name_with_extension="FG_EG_pre",
    coordinate_system_for_the_raster=spatialRef,
    pixel_type="32_BIT_FLOAT",
    cellsize=gridRes,
    number_of_bands=1,
    mosaic_method="LAST",
    mosaic_colormap_mode="FIRST"
)

# Extract ungraded and graded elevation layers

arcpy.management.AddXY(piles_working)
arcpy.sa.ExtractMultiValuesToPoints(piles_working,[[FG_EG_pre, "basePlane"]], "BILINEAR")

gradeClip = arcpy.management.Clip(FG_EG_pre, "", gradeOut, projectBoundary, "3.4e+38","ClippingGeometry", "NO_MAINTAIN_EXTENT")

arcpy.management.CalculateField(piles_working, "grade_trends", "!demGrade!-!basePlane!", "PYTHON3", None, "DOUBLE")
arcpy.management.CalculateField(piles_working, "min_rev_grade", ""+minReveal+" + !grade_trends!", "PYTHON3", None, "DOUBLE")
maxMinRevStats = arcpy.analysis.Statistics(piles_working, "maxMinRevStats", ["min_rev_grade", "MAX"], row_ID)
arcpy.management.JoinField(piles_working, row_ID, maxMinRevStats, row_ID, "MAX_min_rev_grade")

arcpy.management.CalculateField(piles_working, "reveal", "!MAX_min_rev_grade! - !grade_trends!", "PYTHON3", None, "DOUBLE")
arcpy.management.CalculateField(piles_working, "TOP_elv", "!reveal! + !demGrade!", "PYTHON3", None, "DOUBLE")

# Calculate reveals 

arcpy.management.CalculateField(piles_working, "cutFill", "!demGrade!-!demExist!", "PYTHON3", None, "DOUBLE")

aprxMap.addDataFromPath(piles_working)
aprxMap.addDataFromPath(gradeClip)

# Subtract the existing elevation from the graded elevation
cutFill = arcpy.sa.Minus(gradeClip, demInput)
cutFillScreen = arcpy.sa.SetNull(cutFill, cutFill, minGradeScreen_input)

cutFillMAXResult = arcpy.GetRasterProperties_management(cutFillScreen, "MAXIMUM")
cutFillMINResult = arcpy.GetRasterProperties_management(cutFillScreen, "MINIMUM")
cutFillMAX = cutFillMAXResult.getOutput(0)
cutFillMIN = cutFillMINResult.getOutput(0)

arcpy.AddMessage("Fill Max: " + str(cutFillMAX))
arcpy.AddMessage("Cut Max: " + str(cutFillMIN))
