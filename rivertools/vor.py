import numpy as np
from scipy.spatial.qhull import QhullError
from scipy.spatial import Voronoi
from shapely.geometry import *
from shapely.ops import unary_union, linemerge
from logger import Logger

class NARVoronoi:
    """
    The purpose of this class is to load a shapefile and calculate the voronoi
    shapes from it.
    """

    def __init__(self, points):
        """
        The init method is where all the Voronoi magic happens.
        :param points:
        """
        # The centroid is what we're going to use to shift all the coords around
        self.points = points
        self.centroid = MultiPoint([x.point for x in points]).centroid.coords[0]
        self.log = Logger('NARVoronoi')

        # Give us a numpy array that is easy to work with then subtract the centroid
        # centering our object around the origin so that the QHull method works properly
        adjpoints = np.array(MultiPoint([x.point for x in points]))
        adjpoints = adjpoints - self.centroid

        try:
            self._vor = Voronoi(adjpoints)
        except QhullError as e:
            self.log.error("Something went wrong with QHull", e)
        except ValueError as e:
            self.log.error("Invalid array specified", e)

        # bake in region adjacency (I have no idea why it's not in by default)
        self.region_neighbour = []

        # Find which regions are next to which other regions
        for idx, reg in enumerate(self._vor.regions):
            adj = []
            for idy, reg2 in enumerate(self._vor.regions):
                # Adjacent if we have two matching vertices (neighbours share a wall)
                if idx != idy and len(set(reg) - (set(reg) - set(reg2))) >= 2:
                    adj.append(idy)
            self.region_neighbour.append(adj)

        # Transform everything back to where it was (with some minor floating point rounding problems)
        # Note that we will use the following and NOT anything from inside _vor (which is shifted to the origin)
        self.vertices = self._vor.vertices + self.centroid
        self.ridge_points = self._vor.ridge_points
        self.ridge_vertices = self._vor.ridge_vertices
        self.regions = self._vor.regions
        self.point_region = self._vor.point_region

    def collectCenterLines(self, flipIsland=None):
        """

        :param flipIsland: The id of the island to reassign to a different side. Useful when calculating alternate
                            centerlines around islands.
        :return: LineString (Valid) or MultiLineString (invalid)
        """

        # The first loop here asigns each polygon to either left or right side of the channel based on the
        # self.point object we passed in earlier.
        regions = []
        for idx, reg in enumerate(self.region_neighbour):
            # obj will have everything we need to know.
            obj = {
                "id": idx,
                "side": 1,
                "adjacents": reg
            }
            lookupregion = np.where(self._vor.point_region == idx)
            if len(lookupregion[0]) > 0:
                ptidx = lookupregion[0][0]
                point = self.points[int(ptidx)]
                if flipIsland is not None and point.island == flipIsland:
                    obj["side"] = point.side * -1
                else:
                    obj["side"] = point.side
            regions.append(obj)

        # The second loop goes over each region's neighbours and if a neighbour has a different side
        # Then we must be on opposite sides of a centerline and so try and find two points representing a wall between
        # These regions that we will add to our centerline
        centerlines = []
        for region in regions:
            for nidx in region['adjacents']:
                neighbour = regions[nidx]
                if neighbour['side'] != region['side']:

                    # Get the two shared points these two regions should have
                    # NOTE: set(A) - (set(A) - set(B)) is a great pattern
                    sharedpts = set(self.regions[region['id']]) - (set(self.regions[region['id']]) - set(self.regions[nidx]))

                    # Add this point to the list if it is unique
                    if -1 not in sharedpts:
                        lineseg = []
                        for e in sharedpts:
                            lineseg.append(self.vertices[e])
                        if len(lineseg) == 2:
                            centerlines.append(LineString(lineseg))

        # linemerge and unary_union are used to turn MultiLineStrings into a single LineString. We might not succeed
        # Though if the lines don't connect
        return linemerge(unary_union(centerlines))

    def createshapes(self):
        """
        Simple helper function to make polygons out of the untransformed (i.e. original) Voronoi vertices.
        We use this mainly for visualization
        :return:
        """
        polys = []
        for region in self.regions:
            if len(region) >= 3:
                regionVerts = [self.vertices[ptidx] for ptidx in region if ptidx >= 0]
                if len(regionVerts) >= 3:
                    polys.append(Polygon(regionVerts))
        self.polys = MultiPolygon(polys)

