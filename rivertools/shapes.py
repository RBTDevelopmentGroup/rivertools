import math
import json
import os
import ogr
import numpy as np
from logger import Logger
from shapely.geometry import *
from shapely.ops import nearest_points
from bisect import bisect_left

ogr.UseExceptions()
# --------------------------------------------------------
# Load the Shapefiles we need
# --------------------------------------------------------

class Shapefile:

    def __init__(self, sFilename=None):
        self.driver = ogr.GetDriverByName("ESRI Shapefile")
        self.log = Logger('Shapefile')
        self.datasource = None
        if sFilename:
            self.load(sFilename)

    def load(self, sFilename):
        dataSource = self.driver.Open(sFilename, 0)
        self.layer = dataSource.GetLayer()
        self.spatialRef = self.layer.GetSpatialRef()

        self.getFieldDef()
        self.getFeatures()

    def create(self, sFilename, spatialRef=None, geoType=ogr.wkbMultiLineString):
        if os.path.exists(sFilename):
            self.driver.DeleteDataSource(sFilename)
        self.driver = None
        self.driver = ogr.GetDriverByName("ESRI Shapefile")
        self.datasource = self.driver.CreateDataSource(sFilename)
        self.layer = self.datasource.CreateLayer(sFilename, spatialRef, geom_type=geoType)

    def createField(self, fieldName, ogrOFT):
        """
        Create a field on the layer
        :param fieldName:
        :param ogrOFT:
        :return:
        """
        self.log.info("Creating field: {0}".format(fieldName))
        aField = ogr.FieldDefn(fieldName, ogrOFT)
        self.layer.CreateField(aField)

    def featuresToShapely(self):
        if len(self.features) == 0:
            return

        feats = []
        for feat in self.features:
            featobj = json.loads(feat.ExportToJson())

            fields = {}
            for f in self.fields:
                fields[f] = feat.GetField(f)

            feats.append({
                'geometry': shape(featobj['geometry']),
                'fields': fields
            })
        return feats

    def getFieldDef(self):
        self.fields = {}
        lyrDefn = self.layer.GetLayerDefn()
        for i in range(lyrDefn.GetFieldCount()):
            fieldName = lyrDefn.GetFieldDefn(i).GetName()
            fieldTypeCode = lyrDefn.GetFieldDefn(i).GetType()
            fieldType = lyrDefn.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
            fieldWidth = lyrDefn.GetFieldDefn(i).GetWidth()
            GetPrecision = lyrDefn.GetFieldDefn(i).GetPrecision()

            self.fields[fieldName] = {
                'fieldName': fieldName,
                'fieldTypeCode': fieldTypeCode,
                'fieldType': fieldType,
                'fieldWidth': fieldWidth,
                'GetPrecision': GetPrecision
            }

    def getFeatures(self):

        self.features = []
        for feat in self.layer:
            self.features.append(feat)

            # def __del__(self):
            #     if self.datasource.Destroy:
            #         self.datasource.Destroy()

class RiverPoint:

    def __init__(self, pt, interior=False, side=None, island=None):
        self.point = pt
        self.side = side
        self.interior = interior
        self.island = island

def createTangentialIntersect(dist, centerline, rivershape):
    diag = getDiag(rivershape)
    xsLong, point = createTangentialLine(dist, centerline, diag)

    # intersect the long crossection with the rivershape and see what falls out.
    intersections = rivershape.intersection(xsLong)

    # The result may be a linestring or a multilinestring.
    inlist = []
    if not intersections.is_empty:
        if intersections.type == "LineString":
            inlist = [intersections]
        elif intersections.type == "MultiLineString":
            inlist = list(intersections)

    # Now we have to choose what stays and what goes
    keepXs = None
    throwaway = []
    for xs in inlist:
        keep = True
        # Add only lines that contain the centerpoint
        if xs.interpolate(xs.project(point)).distance(point) > 0.01:
            keep = False
        if keep:
            keepXs = xs
        else:
            throwaway.append(xs)

    # One point can only ever have one line segment
    return keepXs, throwaway

def createTangentialLine(dist, centerline, length):
    """
    Create a tangential line at distance
    :param dist:
    :param point:
    :param centerline:
    :return:
    """

    point = centerline.interpolate(dist)
    pt = point.coords[0]

    coords = list(centerline.coords)

    segind = bisectLineSearch(dist, centerline)
    seg = LineString([coords[segind], coords[segind+1]])

    # The slope is rise over run of this segment
    rise = seg.coords[1][1] - seg.coords[0][1]
    run = seg.coords[1][0] - seg.coords[0][0]

    theta = math.atan2(rise, run)
    perptheta = theta + math.pi/2

    return LineString([(
        pt[0] + length * math.cos(perptheta),
        pt[1] + length * math.sin(perptheta)),
        (pt[0] - length * math.cos(perptheta),
         pt[1] - length * math.sin(perptheta))]), point


def bisectLineSearch(dist, line):
    """
    Use a bisect approach to get the index of the start of the line segment that contains
    the distance specified.

    for example:
        line = [ (0,0), (0,4), (0,7), (0,10)
        for dist = 0 returns 0
        for dust = 3.5 returns 0
        for dist = 4.2 returns 2
        for dist = 7.5 returns 3
        for dist = 10 returns 9 (endpoint condition)
    :param dist: The distance along the line
    :param line: The line in question
    :return: index along the line just before we encounter 'dist' length
    """
    arr = list(line.coords)

    def _recurse(idx, ss, count=1):
        # These are the expensive calls. We want to do them as little as possible.
        pt = Point(arr[idx])
        # Past a certain point we start decrementing instead of halving
        newss = ss / 2 if ss > 3 else ss - 1
        proj = line.project(pt)
        dir = 1 if proj < dist else -1

        # Return if we've run out of steps or we've found the culprit
        if proj == dist:
            return idx
        elif ss <= 0:
            return idx if dir > 0 else idx - 1
        else:
            return _recurse(int(idx + newss * dir), newss, count+1)

    maxind = len(arr)-1
    lineind = _recurse(maxind, maxind)
    # Note: we've got an endpoint condition here. If we're at the end of the line
    # just return the last point so we can make a valid line segment out of it.
    return lineind if lineind < maxind else lineind -1


def getBufferedBounds(shape, buffer):
    """
    Get the bounds of a shape and extend them by some arbitrary buffer
    :param shape:
    :param buffer:
    :return:
    """
    newExtent = (shape.bounds[0] - buffer, shape.bounds[1] - buffer, shape.bounds[2] + buffer, shape.bounds[3] + buffer)

    return Polygon([
        (newExtent[0], newExtent[1]),
        (newExtent[2], newExtent[1]),
        (newExtent[2], newExtent[3]),
        (newExtent[0], newExtent[3]),
        (newExtent[0], newExtent[1])
    ])

def getDiag(rect):
    """
    return the biggest possible distance inside a rectangle (the diagonal)
    :param rect: rectangle polygon
    :return:
    """
    return math.sqrt(
        math.pow((rect.bounds[3] - rect.bounds[1]), 2) +
        math.pow((rect.bounds[2] - rect.bounds[0]), 2))

def rectIntersect(line, poly):
    """
    Return the intersection point between a line segment and a polygon
    :param line: Note, the direction is important so we use a list of tuples
    :param poly:
    :return:
    """
    diag = getDiag(poly)
    longLine = getExtrapoledLine(line, diag)
    return poly.intersection(longLine)


def getExtrapoledLine(line, length):
    """
    Creates a line extrapoled in p1->p2 direction' (starting at p2)
    by an arbitrary length
    :param line:
    :param length:
    :return:
    """
    p1 = line.coords[0]
    p2 = line.coords[1]

    rise = (p2[1] - p1[1])
    run = (p2[0] - p1[0])

    theta = math.atan2(rise, run)

    newX = p2[0] + length * math.cos(theta)
    newY = p2[1] + length * math.sin(theta)

    return LineString([p2, (newX, newY)])

def reconnectLine(baseline, separateLine):
    """
    Smoothing can separate the centerline from its alternates. This function
    reconnects them using nearest point projection. Do this before smoothing the
    alternate line
    :param baseline: The main line that does not change
    :param separateLine: The line we want to reconnect
    :return:
    """
    # First find the start and end point
    sepLineStart = Point(separateLine.coords[0])
    sepLineEnd = Point(separateLine.coords[-1])

    # Now find their nearest points on the centerline
    newStart = baseline.interpolate(baseline.project(sepLineStart))
    newEnd = baseline.interpolate(baseline.project(sepLineEnd))

    line = list(separateLine.coords)
    line.insert(0, tuple(newStart.coords[0]))
    line.append(tuple(newEnd.coords[0]))

    return LineString(line)

def splitClockwise(rect, thalweg):
    """
    Work clockwise around a rectangle and create two shapes that represent left and right bank
    We do this by adding 4 corners of the rectangle and 2 endpoints of thalweg to a list and then
    sorting it clockwise using the rectangle centroid.

    Then we traverse the clockwise list and switch between shape1 and shape2 when we hit thalweg start/end points

    finally we inject the entire thalweg line into both shape1 and shape2 between where the start and end points
    of the thalweg intersect the rectangle and instantiate the whole mess as two polygons inside a multipolygon
    which we then return
    :param rect:
    :param thalweg: a thalweg with start and end points that intersects the rectangle
    :return:
    """

    # TODO: This might break if the thalweg is reversed or if the thalweg us weird. Lots of testing necessary
    # The thalweg has two points we care about: the first and last points that should intersect the rectangle
    thalwegStart = thalweg.coords[0]
    thalwegEnd = thalweg.coords[-1]

    coordsorter = list(rect.exterior.coords)
    coordsorter.append(thalwegStart)
    coordsorter.append(thalwegEnd)

    # Sort the points clockwise using the centroid as a center point
    def algo(pt):
        return math.atan2(pt[0] - rect.centroid.coords[0][0], pt[1] - rect.centroid.coords[0][1]);
    coordsorter.sort(key=algo)

    # Create shape1 and shape2 which will fill up with points shape#idx is the place where the thalweg
    # Should be injected
    shape1 = []
    shape2 = []
    shape1idx = 0
    shape2idx = 0

    # Our boolean switchers
    firstshape = True
    foundfirst = False
    reverseThalweg = False

    # Calculate shape 1 and shape 2 by traversal
    for idx, pt in enumerate(coordsorter):

        # If we hit the thalweg start note it using the idx vars and floop the firstshape.
        if pt == thalwegStart:
            shape1idx = len(shape1)
            shape2idx = len(shape2)
            firstshape = not firstshape
            foundfirst = True

        # At the endpoint we just floop the firstshape.
        elif pt == thalwegEnd:
            firstshape = not firstshape
            # We found the tail before we found the head. Make a note that it's ass-backwards
            if not foundfirst:
                reverseThalweg = True

        # If this is a rectangle corner we add it to the appropriate shape
        elif firstshape:
            shape1.append(pt)
        elif not firstshape:
            shape2.append(pt)

    # Now inject the entire thalweg into the appropriate area (reversed if necessary)
    if reverseThalweg:
        shape1[shape1idx:shape1idx] = reversed(list(thalweg.coords))
        shape2[shape2idx:shape2idx] = list(thalweg.coords)
    else:
        shape1[shape1idx:shape1idx] = list(thalweg.coords)
        shape2[shape2idx:shape2idx] = reversed(list(thalweg.coords))

    return MultiPolygon([Polygon(shape1), Polygon(shape2)])