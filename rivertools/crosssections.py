from shapely.geometry import *
import argparse
import sys
import numpy as np
from raster import Raster
from shapes import *
from plotting import Plotter
from logger import Logger
from metrics import *
from os import path
from datetime import datetime
import itertools
from time import strftime

def crosssections(args):
    """
    A Note about debugging:

    You can use the following paths in this repo:

    "../sampledata/Visit_2425/WettedExtent.shp" "../sampledata/Visit_2425/Thalweg.shp" "../sampledata/outputs/centerline.shp" --islands "../sampledata/Visit_2425/Islands.shp" --smoothing 0

    :param args:
    :return:
    """

    log = Logger("Cross Sections")

    # --------------------------------------------------------
    # Load the Shapefiles we need
    # --------------------------------------------------------
    log.info("Opening Shapefiles...")
    rivershp = Shapefile(args.river.name)
    centerline = Shapefile(args.centerline.name)

    islList = []
    if 'islands' in args and args.islands is not None:
        islandsshp = Shapefile(args.islands.name)
        islList = islandsshp.featuresToShapely()

    # Pull the geometry objects out and disregard the fields
    polyRiverShape = rivershp.featuresToShapely()[0]['geometry']
    centerlines = centerline.featuresToShapely()

    # Load in the island shapes then filter them to qualifying only

    multipolIslands = MultiPolygon([isl['geometry'] for isl in islList if isl['fields']['Qualifying'] == 1])

    # Make a new rivershape using the exterior and only qualifying islands from that shapefile
    log.info("Combining exterior and qualifying islands...")
    rivershape = Polygon(polyRiverShape.exterior).difference(multipolIslands)

    pointcloud = {
        "stationsep": [],
        "separation": []
    }

    # --------------------------------------------------------
    # Traverse the line(s)
    # --------------------------------------------------------
    log.info("Starting Centerline Traversal...")

    class XSObj:
        def __init__(self, centerlineID, geometry, isMain):
            self.centerlineID = centerlineID
            self.geometry = geometry
            self.metrics = {}
            self.isValid = False
            self.isMain = isMain

    allxslines = []
    throwaway = []
    for line in centerlines:
        linexs = []
        linegeo = line['geometry']
        mainChannel = 'Channel' in line['fields'] and line['fields']['Channel'] == "Main"
        channelID = line['fields']['ID']

        # Get 50cm spaced points
        for currDist in np.arange(0, linegeo.length, args.separation):
            # Now create the cross sections with length = 2 * diag
            newxs, junk, pt = createTangentialIntersect(currDist, linegeo, rivershape)
            throwaway += junk

            # If the points flag is set we add this point to a dictionary for later
            # Writing to the shp file
            if args.points:
                pointcloud['separation'].append(pt)

            keep = True
            xsObj = XSObj(channelID, newxs, mainChannel)

            # If this is not the main channel and our cross section touches the exterior wall in
            # more than one place then lose it
            if not mainChannel:
                dista = Point(newxs.coords[0]).distance(rivershape.exterior)
                distb = Point(newxs.coords[1]).distance(rivershape.exterior)
                if dista < 0.001 and distb < 0.001:
                    keep = False

            if keep:
                linexs.append(xsObj)
            else:
                throwaway.append(newxs)

        allxslines.append(linexs)

    # --------------------------------------------------------
    # Valid/invalid line testing
    # --------------------------------------------------------
    log.info("Testing XSs for Validity...")

    for linexs in allxslines:
        xsValueValidate(linexs)

    xsOverlapValidate(allxslines)


    # --------------------------------------------------------
    # Metric Calculation
    # --------------------------------------------------------
    # Flatten the list
    log.info("Calculating metrics for all crosssections")
    flatxsl = [xs for xslist in allxslines for xs in xslist]
    dem = Raster(args.dem.name)
    for idx, xs in enumerate(flatxsl):
        ptsdict = calcXSMetrics(xs, polyRiverShape, dem, args.stationsep)
        # Add all station points to stationsep for writing to the shapefile
        if args.points:
            ptsdict['xsid'] = idx
            pointcloud['stationsep'].append(ptsdict)


    # --------------------------------------------------------
    # Write the output Shapefile
    # --------------------------------------------------------
    log.info("Writing XSs to Shapefiles...")
    outShape = Shapefile()
    outShape.create(args.crosssections, rivershp.spatialRef, geoType=ogr.wkbLineString)

    outShape.createField("ID", ogr.OFTInteger)
    outShape.createField("isValid", ogr.OFTInteger)

    # Define and add the metadata fields to the ShapeFile.
    # The are not the essential fields (such as ID above) or the metric
    # fields that are defined during XS creation. These are things like file paths etc.
    AddMetaFields(outShape)

    for metricName, metricValue in flatxsl[0].metrics.iteritems():
        outShape.createField(metricName, ogr.OFTReal)

    for idx, xs in enumerate(flatxsl):
        featureDefn = outShape.layer.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        ogrLine = ogr.CreateGeometryFromJson(json.dumps(mapping(xs.geometry)))
        outFeature.SetGeometry(ogrLine)

        # Set some metadata fields
        outFeature.SetField("ID", int(idx))
        outFeature.SetField("isValid", int(xs.isValid))
        outFeature.SetField("Name", "Cross Section {0}".format(idx))
        outFeature.SetField("Date", datetime.now().strftime('%Y-%m-%d'))
        outFeature.SetField("CLine", path.abspath(args.centerline.name))
        outFeature.SetField("DEM", path.abspath(args.dem.name))
        outFeature.SetField("Banks", path.abspath(args.river.name))
        outFeature.SetField("Extension", 0) # lateral extension currently always zero
        outFeature.SetField("StatSep", args.stationsep)

        if xs.isMain:
            outFeature.SetField('Channel', 'Main')
        else:
            outFeature.SetField('Channel', 'Side')

        # Now write all the metrics to a file
        for metricName, metricValue in xs.metrics.iteritems():
            try:
                # print "{0} ==> {1}".format(metricName, metricValue)
                outFeature.SetField(metricName, metricValue)
            except NotImplementedError as e:
                log.error("OGR SetField Error", e)

        outShape.layer.CreateFeature(outFeature)

    if args.points:
        log.info("Writing Points...")
        outShape = Shapefile()
        newname = "{0}_points.shp".format(os.path.splitext(args.crosssections)[0])
        outShape.create(newname, rivershp.spatialRef, geoType=ogr.wkbPoint)

        outShape.createField("ID", ogr.OFTInteger)
        outShape.createField("xsID", ogr.OFTInteger)
        outShape.createField("type", ogr.OFTString)
        outShape.createField("val", ogr.OFTReal)

        featureDefn = outShape.layer.GetLayerDefn()
        for idx, xspts in enumerate(pointcloud['stationsep']):
            for idy, pt in enumerate(xspts['points']):
                outFeature = ogr.Feature(featureDefn)
                ogrPt = ogr.CreateGeometryFromJson(json.dumps(mapping(pt)))
                outFeature.SetGeometry(ogrPt)
                outFeature.SetField("ID", int(idx))
                outFeature.SetField("val", float(xspts['values'][idy]))
                outFeature.SetField("type", "stationsep")
                outFeature.SetField("xsID", int(xspts['xsid']))
                outShape.layer.CreateFeature(outFeature)

        for idx, pt in enumerate(pointcloud['separation']):
            outFeature = ogr.Feature(featureDefn)
            ogrPt = ogr.CreateGeometryFromJson(json.dumps(mapping(pt)))
            outFeature.SetGeometry(ogrPt)
            outFeature.SetField("ID", int(idx))
            outFeature.SetField("type", "separation")
            outFeature.SetField("val", 0)
            outFeature.SetField("xsID", idx)
            outShape.layer.CreateFeature(outFeature)


    # --------------------------------------------------------
    # Do a little show and tell with plotting and whatnot
    # --------------------------------------------------------
    if not args.noviz:
        log.info("Plotting Results...")

        plt = Plotter()

        # The shape of the river is grey (this is the one with only qualifying islands
        plt.plotShape(rivershape, '#CCCCCC', 0.5, 5, 'River Shape')

        # Centerline is black
        plt.plotShape(MultiLineString([g['geometry'] for g in centerlines]), '#000000', 0.5, 20, "Centerlines")

        # Throwaway lines (the ones that are too whack to even test for validity) are faded red
        plt.plotShape(MultiLineString(throwaway), '#FF0000', 0.3, 20, "Throwaway Lines (not stored)")

        # Invalid crosssections are orange
        plt.plotShape(MultiLineString([g.geometry for g in flatxsl if not g.isValid]), '#00FF00', 0.7, 25, "Invalid Cross Sections")

        # The valid crosssections are blue
        plt.plotShape(MultiLineString([g.geometry for g in flatxsl if g.isValid]), '#0000FF', 0.7, 30, "Valid Cross Sections")

        bounds = getBufferedBounds(rivershape, 10).bounds
        if 'savepng' in args and args.savepng is not None:
            plt.savePlot(args.savepng, bounds)
        else:
            plt.showPlot(bounds)


def AddMetaFields(outShape):

    # Field to store the date that the cross sections were generated
    outShape.createField("Date", ogr.OFTString)
    ogr.FieldDefn("Date", ogr.OFTString).SetWidth(10)

    # Field to store the cross section name
    outShape.createField("Name", ogr.OFTString)
    ogr.FieldDefn("Name", ogr.OFTString).SetWidth(255)

    # Field to store the path to the DEM ShapeFile
    outShape.createField("DEM", ogr.OFTString)
    ogr.FieldDefn("DEM", ogr.OFTString).SetWidth(255)

    # Field to store the path to the river banks ShapeFile
    outShape.createField("Banks", ogr.OFTString)
    ogr.FieldDefn("Banks", ogr.OFTString).SetWidth(255)

    # Field to store the path to the centerline ShapeFile
    outShape.createField("CLine", ogr.OFTString)
    ogr.FieldDefn("CLine", ogr.OFTString).SetWidth(255)

    # Lateral extension beyond the river banks polygon.
    outShape.createField("Extension", ogr.OFTInteger)

    # Lateral spacing of stations along a cross section
    outShape.createField("StatSep", ogr.OFTReal)

    # Which channel the cross section is in: 'Main' or 'Side'
    outShape.createField("Channel", ogr.OFTString)
    ogr.FieldDefn("Channel", ogr.OFTString).SetWidth(4)

def xsValueValidate(linexs):
    """
    Validate each XS in a line based on the average stats
    for that line
    :param linexs:
    :return:
    """
    lengths = [xs.geometry.length for xs in linexs]
    stdev = np.std(lengths)
    mean = np.mean(lengths)

    # Test each cross section for validity.
    # TODO: Right now it's just stddev test. There should probably be others
    for idx, xsobj in enumerate(linexs):
        isValid = not xsobj.geometry.length > (mean + 4 * stdev)
        xsobj.isValid = isValid


def xsOverlapValidate(allxslines):
    """
    See if any
    :return: Nothing. This edits in place.
    """
    # Loop over lines
    for linecombo in itertools.combinations(allxslines,2):
        xslist0 = [xs for xs in linecombo[0] if xs.isValid]
        xslist1 = [xs for xs in linecombo[1] if xs.isValid]

        for xs in xslist0:
            for xsTest in xslist1:
                if xs.geometry.intersects(xsTest.geometry):
                    xs.isValid = False
                    xsTest.isValid = False


def main():

    log = Logger("Initializing")

    # parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument('river',
                        help='Path to the river shape file. Donuts will be ignored.',
                        type=argparse.FileType('r'))
    parser.add_argument('centerline',
                        help='Path to the centerline shapefile',
                        type=argparse.FileType('r'))
    parser.add_argument('dem',
                        help='Path to the DEM Raster (used for metric calculation)',
                        type=argparse.FileType('r'))
    parser.add_argument('crosssections',
                        help='Path to the desired output crosssections')
    parser.add_argument('separation',
                        type=float,
                        help='Downstream spacing between cross sections')
    parser.add_argument('stationsep',
                        type=float,
                        help='Lateral spacing between vertical DEM measurements')
    parser.add_argument('--islands',
                        help='Path to the islands shapefile',
                        type=argparse.FileType('r'))
    parser.add_argument('--savepng',
                        type=str,
                        help='Provide a path to save the plot to a png')
    parser.add_argument('--points',
                        help = 'Generate points at separation and stationsep (slower)',
                        action='store_true',
                        default=False)
    parser.add_argument('--noviz',
                        help = 'Disable result visualization (faster)',
                        action='store_true',
                        default=False)
    args = parser.parse_args()

    if not args.river or not args.centerline or not args.crosssections or not args.dem:
        print "ERROR: Missing arguments"
        parser.print_help()
        exit(0)

    log = Logger("Program")

    try:
        crosssections(args)
        log.info("Completed Successfully")
    except AssertionError as e:
        log.error("Assertion Error", e)
        sys.exit(0)
    except Exception as e:
        log.error('Unexpected error: {0}'.format(sys.exc_info()[0]), e)
        raise
        sys.exit(0)


if __name__ == "__main__":
    main()

