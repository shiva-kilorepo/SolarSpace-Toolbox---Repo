#############################
# SolarSpace Python Toolbox #
#############################

"""
Release Notes
Version BETA.0.0.1 - 4/7/2022
=> Initial release

Version BETA.0.0.2 - 5/27/2022
=> Fixed issue with preliminary grading assessment with certain projections that were causing gaps
=> Added preliminary layout tool

Version 1.0.0 - 6/15/2022
=> Implemented into ArcGIS Pro Add-in

Version 1.0.1 - 7/21/2022
=> Modified layout tool to include summary of capacity
=> Revised tool groupings
=> Added tool tips

Version 1.1.0 - 8/5/2022
=> Added automatic symbology, minor fixes, added preliminary terrain loss estimate tool

Version 1.2.0 - 8/30/2022
=> Added LandXML export and minor tool fixes

Version 1.3.0 - 1/10/2023
=> Added all working internal tools
=> Revised all grading boundaries
=> Fixed an error in the prelim grading tool to eliminate erroneous values at boundaries
=> Added an option for volume statistics/layers outputs to all grading/prelim grading tools
=> Upgraded LandXMl export tool
=> Added option to export LandXMl from all grading tools
=> Added raster exclusion limits tool
=> Added extract POA at end of rows tool
=> Combined Cut and Fill and Zonal Cut and Fill tools into one tool
=> Upgraded and fixed errors in the prelim terrain loss tool
=> Added ability to have exclusion zones for grading for prelim grading tool
=> Updated mass grading tool do calculate slope directionally

Version 1.4.0 - 4/1/2024
=> Added 2 new tools: Adjust rows & Import surface data
=> Revamped directional slope exclusion tool methodology & added option to output hard/soft exclusions
=> Added additional functionality to layout tool to improve feasibility of output
=> Added ability of Preliminary Grading Assesment to produce output surface raster
=> Added additional checks & use-case fixes to grading estimate tools
=> Fixed persistent bugs with mass grading estimate, terrain loss estimate & pile northing adjust tools
=> Fixed bug with sample pile tool producing un-needed piles; added ability to produce pile location attribute
"""

import arcpy

#from ATINorthingAdjPOACenterFixed import *
from basePlanes import*
from BuildableArea import*
from ConventionalGrading import*
from cutFill import*
from DirectionalBuffer import *
from DirectionalSlope import *
#from DirectionalSlopeExclusion import *
from DirectionalSlopeExclusion_v2 import *
from ewPOAopt import *
from exclusionLimits import *
from fixedRackLayout import *
from floodAdj import floodAdj
#from gradePilesBounds import *
from gradePilesBounds_v2 import *
from gradeRevisePOA import *
from LXMLExport import *
from MassGrading_v2 import *
from MassGrading import *
from maxPOADeltaNS import *
from NorthingAdjPOA import *
from NSPOACheck import *
from NSSlopePOAPiles import *
from poaEWcheck import *
from poaRowEnds import *
#from PrelimLayoutTableUpdate import *
from PrelimTerrainLoss import * 
from revisePilesFromPOAEnds import*
from SamplePiles import*
from SATGradingEst import* # COMMERCIAL ONLY
from SATLayoutPrelim import *
from SATPrelimGrading import *
from SATSiTE_Rough import *
from SmoothRoughGrading import *
from terrainLoss import *
from TINtoLXML import *
#from slope_exclusion_directional import *
from PointsOnPoylgon import *
from terrainFollowingGrading_v4 import *
from adjustRows import *
from retrievePublicDEM import *

class Toolbox(object):
    def __init__(self):
        """SolarSpaceAddIn_Build_v1.4.0.pyt"""
        self.label = "SolarSpace"
        self.alias = "SolarSpace"

        # List of tool classes associated with this toolbox
        self.tools =    [#ATINorthingAdjPOACenterFixed,
                        BasePlanes, 
                        BuildableArea,
                        SATGradeConventional,
                        CutFillAssessment,
                        DirectionalBuffer,
                        #SlopeExclusion,
                        SlopeExclusion_v2,  
                        DirectionalSlope, 
                        ewPOAopt, 
                        ExclusionLimits,
                        fixedRackLayout,
                        floodAdj,
                        #gradePilesBounds,
                        gradePilesBounds_v2,
                        gradeRevisePOA,
                        LXMLExport,
                        MassGradev2,
                        maxPOADeltaNS,
                        NorthingAdjPOA,
                        NSPOACheck,
                        NSSlopePiles,
                        poaEWcheck,
                        poaRowEnds,
                        PreliminaryGrading, 
                        #PrelimLayoutTableUpdate,
                        PrelimTerrainLoss,
                        revisePilesFromPOAEnds,
                        SamplePiles,
                        SATGradingEstimate,
                        SATLayoutPrelim,
                        SATSiTE_Rough,
                        SmoothRoughGrading,
                        terrainLoss,
                        TINtoLXML,
                        #SlopeExclusionDirectional,
                        PtsOnPolygon,
                        terrainFollowingGrading_v4,
                        MassGrade,
                        adjustRows,
                        retrievePublicDEM
                        ]



