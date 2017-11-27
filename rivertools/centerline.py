import sys
from shapely.geometry import *
import argparse
from logger import Logger

# We wrote two little files with helper methods:
from vor import NARVoronoi
from shapes import *
from geosmoothing import *

########################################################
# Here are some factors you can play with
# The factor to throw into shapely.simplify (http://toblerity.org/shapely/manual.html)
SHAPELY_SIMPLIFY = 0.01
########################################################


# These are just for graphing
def centerline(args):
    """
    A Note about debugging:

    You can use the following paths in this repo:

    "../sampledata/Visit_2425/WettedExtent.shp" "../sampledata/Visit_2425/Islands.shp" "../sampledata/outputs/centerline.shp" "../sampledata/Visit_2425/DEM.tif" "../sampledata/outputs/crosssections.shp" 0.5 0.5

    :param args:
    :return:
    """

    log = Logger("Centerline")

    # --------------------------------------------------------
    # Load the Shapefiles we need
    # --------------------------------------------------------
    log.info("Opening Shapefiles...")
    rivershp = Shapefile(args.river.name)
    thalwegshp = Shapefile(args.thalweg.name)

    islList = []
    if 'islands' in args and args.islands is not None:
        islandsshp = Shapefile(args.islands.name)
        islList = islandsshp.featuresToShapely()

    # Pull the geometry objects out and disregard the fields
    polyRiverShape = rivershp.featuresToShapely()[0]['geometry']
    lineThalweg = thalwegshp.featuresToShapely()[0]['geometry']

    # Load in the island shapes then filter them to qualifying only

    multipolIslands = MultiPolygon([isl['geometry'] for isl in islList if isl['fields']['Qualifying'] == 1])

    # Make a new rivershape using the exterior and only qualifying islands from that shapefile
    log.info("Combining exterior and qualifying islands...")
    rivershape = Polygon(polyRiverShape.exterior).difference(multipolIslands)

    if 'density' in args and args.density > 0:
        # The Spline smooth gives us round curves.
        log.info("Densifying Polygon...")
        smoothRiver = densifyShape(rivershape, args.density)
    else:
        smoothRiver = rivershape

    # --------------------------------------------------------
    # Find the Centerline
    # --------------------------------------------------------

    # First and last line segment we need to extend
    thalwegStart = LineString([lineThalweg.coords[1], lineThalweg.coords[0]])
    thalwegEnd = LineString([lineThalweg.coords[-2], lineThalweg.coords[-1]])

    # Get the bounds of the river with a little extra buffer (10)
    rivershapeBounds = getBufferedBounds(rivershape, 10)

    # Now see where the lines intersect the bounding rectangle
    thalwegStartExt = projToShape(thalwegStart, rivershapeBounds)
    thalwegEndExt = projToShape(thalwegEnd, rivershapeBounds)

    # Now make a NEW thalweg by adding the extension points to the start
    # and end points of the original
    thalweglist = list(lineThalweg.coords)
    thalweglist.insert(0, thalwegStartExt.coords[1])
    thalweglist.append(thalwegEndExt.coords[1])

    newThalweg = LineString(thalweglist)

    # splitClockwise gives us our left and right bank polygons
    bankshapes = splitClockwise(rivershapeBounds, newThalweg)

    # Add all the points (including islands) to the list
    points = []

    # Exterior is the shell and there is only ever 1
    for pt in list(smoothRiver.exterior.coords):
        side = 1 if bankshapes[0].contains(Point(pt)) else -1
        points.append(RiverPoint(pt, interior=False, side=side))

    # Now we consider interiors. NB: Interiors are only qualifying islands in this case
    for idx, island in enumerate(smoothRiver.interiors):
        for pt in list(island.coords):
            side = 1 if bankshapes[0].contains(Point(pt)) else -1
            points.append(RiverPoint(pt, interior=True, side=side, island=idx))

    # Here's where the Voronoi polygons come into play
    log.info("Calculating Voronoi Polygons...")
    myVorL = NARVoronoi(points)

    centerline = myVorL.collectCenterLines(Polygon(rivershape.exterior))

    if (args.smoothing > 0):
        # This is the function that does the actual work of creating the centerline
        log.info("Spline Smoothing Main Line...")
        linespliner = GeoSmoothing(spl_smpar=args.smoothing)
        centerlineSmooth = linespliner.smooth(centerline)
    else:
        centerlineSmooth = centerline

    # Now we've got the main centerline let's flip the islands one by one
    # and get alternate lines
    alternateLines = []
    for idx, island in enumerate(smoothRiver.interiors):
        altLine = myVorL.collectCenterLines(Polygon(rivershape.exterior), flipIsland=idx)
        log.info("  Spline Smoothing Alternate line...")
        if altLine.type == "LineString":
            # We difference the alternate lines with the main line
            # to get just the bit that is different
            diffaltline = altLine.difference(centerlineSmooth)

            if (args.smoothing > 0):
                # Now smooth this line to be roughly the consistency of skippy peanut butter
                smoothAlt = linespliner.smooth(diffaltline)

                # Now we reconnect the bit that is different with the smoothed
                # Segment since smoothing can mess up the intersection
                reconLine = reconnectLine(centerlineSmooth, smoothAlt)
                chopped = chopCenterlineEnds(reconLine, Polygon(rivershape.exterior))
            else:
                chopped = diffaltline

            alternateLines.append(chopped)

    # Chop the centerline at the ends where it intersects the rivershape
    centerlineChopped = chopCenterlineEnds(centerlineSmooth, Polygon(rivershape.exterior))

    # --------------------------------------------------------
    # Write the output Shapefile
    # --------------------------------------------------------
    log.info("Writing Shapefiles...")
    outShape = Shapefile()
    outShape.create(args.centerline, rivershp.spatialRef, geoType=ogr.wkbMultiLineString)

    outShape.createField("ID", ogr.OFTInteger)
    outShape.createField("Channel", ogr.OFTString)

    # The main centerline gets written first
    featureDefn = outShape.layer.GetLayerDefn()
    outFeature = ogr.Feature(featureDefn)
    ogrmultiline = ogr.CreateGeometryFromJson(json.dumps(mapping(centerlineChopped)))
    outFeature.SetGeometry(ogrmultiline)
    featureID = 1
    outFeature.SetField('ID', featureID)
    outFeature.SetField('Channel', 'Main')
    outShape.layer.CreateFeature(outFeature)

    # We do all this again for each alternate line
    for altline in alternateLines:
        newfeat = ogr.Feature(featureDefn)
        linething = ogr.CreateGeometryFromJson(json.dumps(mapping(altline)))
        newfeat.SetGeometry(linething)
        featureID += 1
        newfeat.SetField('ID', featureID)
        newfeat.SetField('Channel', 'Side')
        outShape.layer.CreateFeature(newfeat)

    # --------------------------------------------------------
    # Do a little show and tell with plotting and whatnot
    # --------------------------------------------------------
    if not args.noviz:
        from plotting import Plotter
        log.info("Plotting Results...")

        plt = Plotter()

        # (OPTIONAL). Makes the polygons we will use to visualize
        myVorL.createshapes()

        # The Voronoi shapes are light grey (really slow for some reason)
        plt.plotShape(myVorL.polys, '#AAAAAA', 0.3, 0, 'Voronoi Polygon')

        # Left and right banks are light red and blue
        plt.plotShape(bankshapes[0], '#FFAAAA', 0.5, 5)
        plt.plotShape(bankshapes[1], '#AAAAFF', 0.5, 5)

        # The rivershape is slightly green
        plt.plotShape(rivershape, '#AACCAA', 0.5, 8, 'River')
        plt.plotShape(smoothRiver, '#AAAACC', 0.5, 10, 'SmoothRiver')

        # Thalweg is green and where it extends to the bounding rectangle is orange
        plt.plotShape(newThalweg, '#FFA500', 1, 15, 'Thalweg Extension')
        plt.plotShape(lineThalweg, '#00FF00', 1, 20, 'Thalweg')

        # The centerline we choose is bright red
        plt.plotShape(centerlineChopped, '#FF0000', 0.8, 30, 'Centerline')

        # The alternate lines are in yellow
        plt.plotShape(MultiLineString(alternateLines), '#FFFF00', 0.8, 25, 'Side-Channel Line')

        bounds = getBufferedBounds(rivershapeBounds, 10).bounds
        if 'savepng' in args and args.savepng is not None:
            plt.savePlot(args.savepng, bounds)
        else:
            plt.showPlot(bounds)


def main():

    log = Logger("Initializing")

    # parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument('river',
                        help='Path to the river shape file. Donuts will be ignored.',
                        type=argparse.FileType('r'))
    parser.add_argument('thalweg',
                        help='Path to the thalweg shapefile',
                        type=argparse.FileType('r'))
    parser.add_argument('centerline',
                        type=str,
                        help='Path to the desired output centerline shapefile')
    parser.add_argument('--density',
                        help='The spacing between points (in m) after densification. (default=0.5)',
                        type=float,
                        default=0.5)
    parser.add_argument('--islands',
                        help='Path to the islands shapefile',
                        type=argparse.FileType('r'))
    parser.add_argument('--smoothing',
                        type=float,
                        default=0,
                        help='smoothing "s" factor for the curve. (default=0/None)')
    parser.add_argument('--savepng',
                        type=str,
                        help='Provide a path to save the plot to a png')
    parser.add_argument('--noviz',
                        help = 'Disable result visualization (faster)',
                        action='store_true',
                        default=False)
    args = parser.parse_args()

    if not args.river or not args.thalweg or not args.centerline:
        log.error("ERROR: Missing arguments")
        parser.print_help()
        exit(0)

    log = Logger("Program")

    try:
        centerline(args)
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