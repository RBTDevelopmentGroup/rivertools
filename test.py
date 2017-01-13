# Utility functions we need
import unittest
import numpy as np
from shapely.geometry import *

class TestRasterClass(unittest.TestCase):
    """
    Before we do anything we need to test the underlying core class
    There is only one method we wrote for this:
    """
    def test_getPixelVal(self):
        from rivertools.raster import Raster
        self.assertTrue(False)

    def test_isClose(self):
        """
        Oh, also this little helper method:
        I didn't write it so we'd better test it well
        """
        from rivertools.raster import isclose
        self.assertTrue(False)

class TestShapeHelpers(unittest.TestCase):

    def test_getBufferedBounds(self):
        from rivertools.shapes import getBufferedBounds
        self.assertTrue(False)

    def test_getDiag(self):
        from rivertools.shapes import getDiag
        self.assertTrue(False)

    def test_rectIntersect(self):
        from rivertools.shapes import rectIntersect
        self.assertTrue(False)

    def test_getExtrapoledLine(self):
        from rivertools.shapes import getExtrapoledLine
        self.assertTrue(False)

    def test_reconnectLine(self):
        from rivertools.shapes import reconnectLine
        self.assertTrue(False)

    def test_splitClockwise(self):
        """
        This is the big one. Needs more careful testing than the rest
        :return:
        """
        from rivertools.shapes import splitClockwise
        self.assertTrue(False)

class TestMetricClass(unittest.TestCase):

    def test_interpolateRasterAlongLine(self):
        from rivertools.metrics import interpolateRasterAlongLine
        self.assertTrue(False)

    def test_dryWidth(self):
        from rivertools.metrics import dryWidth

        # Create a polygon (with no donut)
        aPoly = Polygon([(1, 1), (5, 1), (5, 5), (1, 5), (1, 1)])

        # Create a line
        aLine = LineString([(0, 2.5), (6, 2.5)])

        fValue = dryWidth(aLine, aPoly)
        self.assertEqual(fValue, 4)

        aDonut = Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)])
        aPolyWithDonut = aPoly.difference(aDonut)

        from rivertools.plotting import Plotter
        plt = Plotter()

        # The shape of the river is grey (this is the one with only qualifying islands
        plt.plotShape(aPolyWithDonut, '#AACCCC', 0.5, 5)
        plt.plotShape(aLine, '#CCCCAA', 0.5, 10)
        plt.showPlot((0, 0, 10, 10))

        fValue = dryWidth(aLine, aPolyWithDonut)
        self.assertEqual(fValue, 3)

        self.assertTrue(False)

    def test_meanDepth(self):
        from rivertools.metrics import meanDepth

        depthValues = [1, 2, 3, 4, 5]

        fValue = meanDepth(depthValues)
        self.assertEqual(fValue, 3)

        depthValues = [np.nan, 2, 3, 4, 5]
        depthValuesma = np.ma.masked_invalid(depthValues)
        fValue = meanDepth(depthValuesma)
        self.assertEqual(fValue, 3.5)

        depthValues = [np.nan, np.nan, np.nan, np.nan, np.nan]
        depthValuesma = np.ma.masked_invalid(depthValues)
        fValue = meanDepth(depthValuesma)
        self.assertEqual(fValue, 0)

    def test_maxDepth(self):
        from rivertools.metrics import maxDepth

        # The pass case
        self.assertEqual(maxDepth([1, 2, 3, 4, 5]), 5)

        # The double case
        self.assertEqual(maxDepth([1, 2, 3, 5, 5]), 5)

        # All values nan
        self.assertTrue(np.isnan(maxDepth([np.nan, np.nan, np.nan, np.nan, np.nan])))

        # One value nan
        self.assertEqual(maxDepth([np.nan, 2, 3, 4, 5]), 5)


    def test_getRefElev(self):
        from rivertools.metrics import getRefElev
        self.assertTrue(False)


    # end point on XS when XS is not precise multiple of station distance
    # An idea for this test is get the original line length and compare with
    # the array size multiplied by the station interval

    # Figure out how to handle cross sections with no data parts

    # Which width to use for ratios... is it wetted width or total length

    # Write the attributes to the shapefile



class TestVoronoiClass(unittest.TestCase):

    def test_collectCenterLines(self):
        from rivertools.vor import NARVoronoi
        self.assertTrue(False)

    def test_createshapes(self):
        from rivertools.vor import NARVoronoi
        self.assertTrue(False)

class TestGeoSmoothingClass(unittest.TestCase):
    """
    This is going to be a hard one to test but it came from someone else's implementation so
    I think we should try since testing will help us understand what we are using.
    """

    def test_smooth(self):
        from geosmoothing import *
        self.assertTrue(False)