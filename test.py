# Utility functions we need
import unittest
import numpy as np
import math

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

        # Regular number test abs tolerance
        self.assertTrue(isclose( 1.12, 1.11, rel_tol=1e-09, abs_tol=0.1))
        self.assertFalse(isclose(1.12, 1.11, rel_tol=1e-09, abs_tol=0.01))

        # Regular number test rel tolerance
        self.assertTrue(isclose( 1.12, 1.11, rel_tol=1e-02, abs_tol=0))
        self.assertFalse(isclose(1.12, 1.11, rel_tol=1e-03, abs_tol=0))

        # Scientific notation test rel tolerance
        self.assertTrue(isclose( 1.11112e-09, 1.11111e-09, rel_tol=1e-05, abs_tol=0))
        self.assertFalse(isclose(1.11112e-09, 1.11111e-09, rel_tol=1e-06, abs_tol=0))

        # Scientific notation test abs tolerance
        self.assertTrue(isclose( 1.11112e-09, 1.11111e-09, rel_tol=1e-06, abs_tol=1e-13))
        self.assertFalse(isclose(1.11112e-09, 1.11111e-09, rel_tol=1e-06, abs_tol=1e-14))

class TestShapeHelpers(unittest.TestCase):

    def test_getBufferedBounds(self):
        from rivertools.shapes import getBufferedBounds

        testShape = getBufferedBounds(Polygon([(0,0), (0,1), (1,1), (1,0), (0,0)]), 10)
        expectedBounds = (-10.0, -10.0, 11.0, 11.0)

        self.assertEqual(testShape.bounds, expectedBounds)

    def test_getDiag(self):
        from rivertools.shapes import getDiag
        diag = getDiag(Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]))
        self.assertEqual(diag, math.sqrt(2))

    def test_rectIntersect(self):
        from rivertools.shapes import rectIntersect

        poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
        line = LineString([(0.3,0.3), (0.7, 0.7)])

        self.assertTrue(False)

    def test_getExtrapoledLine(self):
        from rivertools.shapes import getExtrapoledLine

        # Vertical line
        line = LineString([(0, 0), (0, 1)])
        newline = getExtrapoledLine(line, 0.5)
        self.assertAlmostEqual(newline.length, 0.5, 10)
        self.assertEqual(newline.coords[0], line.coords[1], 3)

        # Horizontal line
        line = LineString([(0,0), (1, 0)])
        newline = getExtrapoledLine(line, 1)
        self.assertAlmostEqual(newline.length, 1, 10)

        # Diag NW
        line = LineString([(0,0), (1, 1)])
        newline = getExtrapoledLine(line, 1)
        self.assertAlmostEqual(newline.length, 1, 10)

        # Diag NE
        line = LineString([(0,0), (-1, 1)])
        newline = getExtrapoledLine(line, 1)
        self.assertAlmostEqual(newline.length, 1, 10)

        # Diag SE
        line = LineString([(0,0), (-1, -1)])
        newline = getExtrapoledLine(line, 1)
        self.assertAlmostEqual(newline.length, 1, 10)

        # Diag Sw
        line = LineString([(0,0), (1, -1)])
        newline = getExtrapoledLine(line, 1)
        self.assertAlmostEqual(newline.length, 1, 10)

    def test_createTangentialLine(self):
        from rivertools.shapes import createTangentialLine
        length = 2
        line = LineString([(0, 0), (1, 1)])
        tanline, tanpoint = createTangentialLine(math.sqrt(2)/2, line, length)

        self.assertEqual(tanpoint.coords[0], (0.5, 0.5))
        self.assertEqual(tanline.length, length*2)

    def test_createTangentialIntersect(self):
        from rivertools.shapes import createTangentialIntersect
        line = LineString([(0, 0), (1, 1)])
        shape = Polygon([(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)])

        tanline, tanpoint = createTangentialIntersect(math.sqrt(2)/2, line, shape)

        # Does our shape contain the tangent line?
        self.assertTrue(shape.contains(tanline))

        # Does the tangent line have exactly two points?
        coords = list(shape.intersection(tanline).coords)
        self.assertEqual(len(coords), 2)

        # Do those two points lie on the polygon edge?
        self.assertEqual(shape.distance(Point(coords[0])), 0)
        self.assertEqual(shape.distance(Point(coords[1])), 0)

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

    def plotit(self, line, newline):
        from rivertools.plotting import Plotter
        plt = Plotter()
        # The shape of the river is grey (this is the one with only qualifying islands
        plt.plotShape(newline, '#FF0000', 0.5, 5)
        plt.plotShape(line, '#0000FF', 0.5, 10)
        plt.showPlot((-3, -3, 3, 3))

class TestMetricClass(unittest.TestCase):

    def test_interpolateRasterAlongLine(self):
        from rivertools.metrics import interpolateRasterAlongLine
        xs = LineString([(0,0),(1,0)])

        # Even test
        points = interpolateRasterAlongLine(xs, 0.2)
        self.assertEqual(len(points), 6)

        # Uneven Test
        points = interpolateRasterAlongLine(xs, 0.2001)
        self.assertEqual(len(points), 6)

        # Uneven Test 2
        points = interpolateRasterAlongLine(xs, 0.19999)
        self.assertEqual(len(points), 7)

    def test_lookupRasterValues(self):
        from rivertools.metrics import lookupRasterValues
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

        # Unmasked array
        depthValues = [1, 2, 3, 4, 5]
        self.assertEqual(getRefElev(depthValues), 3.0)

        # Masked Array
        depthValues = np.ma.array([1, 2, 3, 4, 5], mask=[False, False, False, False, False])
        self.assertEqual(getRefElev(depthValues), 3.0)

        # Masked Array with valid mask
        depthValues = np.ma.array([1, 2, np.nan, 4, 5], mask=[False, False, True, False, False])
        self.assertEqual(getRefElev(depthValues), 3.0)

        # Masked Array with invalid mask
        depthValues = np.ma.array([np.nan, 2, 3, 4, 5], mask=[True, False, True, False, False])
        self.assertEqual(getRefElev(depthValues), 0)
        depthValues = np.ma.array([np.nan, 2, 3, 4, np.nan], mask=[False, False, True, False, True])
        self.assertEqual(getRefElev(depthValues), 0)
        depthValues = np.ma.array([np.nan, 2, 3, 4, np.nan], mask=[True, False, True, False, True])
        self.assertEqual(getRefElev(depthValues), 0)

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