from logger import Logger
import numpy as np
from shapely.geos import TopologicalError
from shapely.geometry import *
import math

def calcXSMetrics(xs, rivershapeWithDonuts, dem, fStationInterval):
    """
    Calculate metrics for a list of cross sections
    :param xs: The cross section to generate metrics from
    :param rivershapeWithDonuts: The original rivershape file with donuts
    :param dem: Raster object
    :param fStationInterval: some interval (float)
    :return:
    """
    regularPoints = interpolateRasterAlongLine(xs.geometry, fStationInterval)
    # Augment these points with values from the raster
    ptsdict = lookupRasterValues(regularPoints, dem)

    # Get the reference Elevation from the edges
    refElev = getRefElev(ptsdict['values'])

    xsmXSLength = xs.geometry.length
    xsmWetWidth = dryWidth(xs.geometry, rivershapeWithDonuts)
    xsmDryWidth = xsmXSLength - xsmWetWidth

    if refElev == 0:
        xs.isValid = False
        xsmMaxDepth = 0
        xsmMeanDepth = 0
        xsmW2MxDepth = 0
        xsmW2AvDepth = 0
    else:
        # The depth array must be calculated
        deptharr = refElev - ptsdict['values']

        xsmMaxDepth = maxDepth(deptharr)
        xsmMeanDepth = meanDepth(deptharr)

        xsmW2MxDepth = xsmWetWidth / xsmMaxDepth if not xsmMaxDepth == 0.0 else 0.0
        xsmW2AvDepth = xsmWetWidth / xsmMeanDepth if not xsmMeanDepth == 0.0 else 0.0

    # Make sure that everything has a value
    xs.metrics = {
        "XSLength": metricSanitize(xsmXSLength),
        "WetWidth": metricSanitize(xsmWetWidth),
        "DryWidth": metricSanitize(xsmDryWidth),
        "MaxDepth": metricSanitize(xsmMaxDepth),
        "MeanDepth": metricSanitize(xsmMeanDepth),
        "W2MxDepth": metricSanitize(xsmW2MxDepth),
        "W2AvDepth": metricSanitize(xsmW2AvDepth),
        "BFElev": metricSanitize(refElev),
        "BFArea": 0,
        "HRadius": 0,
        "NumStat":0
    }
    return ptsdict

def metricSanitize(metric):
    """
    This function does nothing more than prevent bad numbers
    :param metric:
    :return:
    """
    if metric is None or np.isnan(metric):
        metric = 0.0
    # We explicitly cast this to np.float (NOT np.float32 or np.float64 etc.) to keep ogr from breaking
    return np.float(metric)

def getRefElev(arr):
    """
    Take a masked array and return a reference depth
    :param arr: Masked array
    :return:
    """
    if isinstance(arr, np.ma.MaskedArray) and (arr.mask[0] or arr.mask[-1]):
        fValue = 0
    else:
        fValue = np.average(arr[0] + arr[-1]) / 2

    return fValue

def maxDepth(arr):
    """
    Calculate the maximum   depth from a list of values
    :param arr:
    :return:
    """
    # Note we don't need to worry about negative depths because we're using max
    # Also don't worry about np.nan because the metricSanitize catches things
    return np.nanmax(arr)


def meanDepth(deptharr):
    """
    Calculate the mean depth from a list of depths
    :param deptharr:
    :return:
    """
    fValue = np.average([x for x in deptharr if x > 0])
    if np.isnan(fValue):
        fValue = 0

    return fValue

def dryWidth(xs, rivershapeWithDonuts):
    """

    :param xs: shapely cross section object
    :param rivershapeWithDonuts: Polygon with non-qualifying donuts retained
    :return:
    """
    log = Logger('dryWidth')
    # Get all intersects of this crosssection with the rivershape
    try:
        intersects = xs.intersection(rivershapeWithDonuts)
    except TopologicalError as e:
        log.error("Could not perform intersection on `rivershapeWithDonuts`. Look for small, invalid islands as a possible cause", e)
        raise e

    # The intersect may be one object (LineString) or many. We have to handle both cases
    if intersects.type == "LineString":
        intersects = MultiLineString([intersects])

    return sum([intersect.length for intersect in intersects])

def interpolateRasterAlongLine(xs, fStationInterval):
    """
    Given a cross section (Linestring) and a spacing point return regularly spaced points
    along that line
    :param xs:
    :param fStationInterval:
    :return:
    """
    points = [xs.interpolate(currDist) for currDist in np.arange(0, xs.length, fStationInterval)]
    # Add the endpoint if it doesn't already exist
    if points[-1] != xs.coords[-1]:
        points.append(Point(xs.coords[-1]))
    return points

def lookupRasterValues(points, raster):
    """
    Given an array of points with real-world coordinates, lookup values in raster
    then mask out any nan/nodata values
    :param points:
    :param raster:
    :return:
    """
    pointsdict = { "points": points, "values": [] }

    for pt in pointsdict['points']:
        pointsdict['values'].append(raster.getPixelVal(pt.coords[0]))

    # Mask out the np.nan values
    pointsdict['values'] = np.ma.masked_invalid(pointsdict['values'])

    return pointsdict