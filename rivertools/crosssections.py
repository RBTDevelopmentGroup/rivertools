from shapely.geometry import *
import argparse
import sys
import numpy as np
from lib.shapes import *
from lib.plotting import Plotter
from lib.logger import Logger
from lib.metrics import *

def crosssections(args):
    """
    A Note about debugging:

    You can use the following paths in this repo:

    "../sampledata/Visit_2425/WettedExtent.shp" "../sampledata/Visit_2425/Islands.shp" "../sampledata/outputs/centerline.shp" "../sampledata/Visit_2425/DEM.tif" "../sampledata/outputs/crosssections.shp"

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
    islandsshp = Shapefile(args.islands.name)

    # Pull the geometry objects out and disregard the fields
    polyRiverShape = rivershp.featuresToShapely()[0]['geometry']
    centerlines = centerline.featuresToShapely()

    # Load in the island shapes then filter them to qualifying only
    islList = islandsshp.featuresToShapely()
    multipolIslands = MultiPolygon([isl['geometry'] for isl in islList if isl['fields']['Qualifying'] == 1])

    # Make a new rivershape using the exterior and only qualifying islands from that shapefile
    log.info("Combining exterior and qualifying islands...")
    rivershape = Polygon(polyRiverShape.exterior).difference(multipolIslands)

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
        for currDist in np.arange(0, linegeo.length, 0.5):
            # Now create the cross sections with length = 2 * diag
            xsgeos, junk = createTangentialLine(currDist, linegeo, rivershape)
            throwaway += junk
            for xs in xsgeos:
                keep = True
                xsObj = XSObj(channelID, xs, mainChannel)

                # If this is not the main channel and our cross section touches the exterior wall in
                # more than one place then lose it
                if not mainChannel:
                    dista = Point(xs.coords[0]).distance(rivershape.exterior)
                    distb = Point(xs.coords[1]).distance(rivershape.exterior)
                    if dista < 0.001 and distb < 0.001:
                        keep = False

                if keep:
                    linexs.append(xsObj)
                else:
                    throwaway.append(xs)

        allxslines.append(linexs)

    # --------------------------------------------------------
    # Valid/invalid line testing
    # --------------------------------------------------------
    log.info("Testin XSs for Validity...")

    for linexs in allxslines:

        lengths = [xs.geometry.length for xs in linexs]
        stdev = np.std(lengths)
        mean = np.mean(lengths)

        # Test each cross section for validity.
        # TODO: Right now it's just stddev test. There should probably be others
        for idx, xsobj in enumerate(linexs):
            isValid = not xsobj.geometry.length > (mean + 4 * stdev)
            xsobj.isValid = isValid

    # --------------------------------------------------------
    # Metric Calculation
    # --------------------------------------------------------
    # Flatten the list
    flatxsls = [xs for xslist in allxslines for xs in xslist]
    calcMetrics(flatxsls, polyRiverShape, args.dem.name)

    # --------------------------------------------------------
    # Write the output Shapefile
    # --------------------------------------------------------
    # TODO: I'd love to abstract all this away but it's a pain to do this in a generic way
    log.info("Writing Shapefiles...")
    outShape = Shapefile()
    outShape.create(args.crosssections, rivershp.spatialRef, geoType=ogr.wkbLineString)

    outShape.createField("ID", ogr.OFTInteger)
    outShape.createField("isValid", ogr.OFTInteger)

    for metricName, metricValue in flatxsls[0].metrics.iteritems():
        outShape.createField(metricName, ogr.OFTReal)

    for idx, xs in enumerate(flatxsls):
        featureDefn = outShape.layer.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        ogrLine = ogr.CreateGeometryFromJson(json.dumps(mapping(xs.geometry)))
        outFeature.SetGeometry(ogrLine)

        # Set some metadata fields
        outFeature.SetField("ID", int(idx))
        outFeature.SetField("isValid", int(xs.isValid))

        # Now write all the metrics to a file
        for metricName, metricValue in xs.metrics.iteritems():
            try:
                # print "{0} ==> {1}".format(metricName, metricValue)
                outFeature.SetField(metricName, metricValue)
            except NotImplementedError as e:
                log.error("OGR SetField Error", e)

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
        plt.plotShape(MultiLineString, '#000000', 0.5, 20, "Centerlines")

        # The valid crosssections are blue
        plt.plotShape(MultiLineString([g.geometry for g in flatxsls if g.isValid]), '#0000FF', 0.7, 25, "Valid Cross Sections")

        # Invalid crosssections are orange
        plt.plotShape(MultiLineString([g.geometry for g in flatxsls if not g.isValid]), '#00FF00', 0.7, 25, "Invalid Cross Sections")

        # Throwaway lines (the ones that are too whack to even test for validity) are faded red
        plt.plotShape(MultiLineString(throwaway), '#FF0000', 0.3, 20, "Throwaway Lines (not stored)")

        plt.showPlot(getBufferedBounds(rivershape, 10).bounds)


def main():

    log = Logger("Initializing")

    # parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument('river',
                        help='Path to the river shape file. Donuts will be ignored.',
                        type=argparse.FileType('r'))
    parser.add_argument('islands',
                        help='Path to the islands shapefile.',
                        type=argparse.FileType('r'))
    parser.add_argument('centerline',
                        help='Path to the centerline shapefile',
                        type=argparse.FileType('r'))
    parser.add_argument('dem',
                        help='Path to the DEM Raster (used for metric calculation)',
                        type=argparse.FileType('r'))
    parser.add_argument('crosssections',
                        help='Path to the desired output crosssections')
    parser.add_argument('--noviz',
                        help = 'Disable result visualization',
                        action='store_true',
                        default=False)
    args = parser.parse_args()

    if not args.river or not args.centerline or not args.islands or not args.crosssections or not args.dem:
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

