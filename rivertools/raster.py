import gdal
import numpy as np
from logger import Logger
# this allows GDAL to throw Python Exceptions
gdal.UseExceptions()

class Raster:

    def __init__(self, sfilename):
        self.log = Logger("Raster")
        self.filename = sfilename

        self.errs = ""
        try:
            src_ds = gdal.Open( self.filename )
        except RuntimeError, e:
            self.log.error('Unable to open %s' % self.filename, e)
            raise e
        try:
            # Read Raster Properties
            srcband = src_ds.GetRasterBand(1)
            self.bands = src_ds.RasterCount
            self.driver = src_ds.GetDriver().LongName
            self.gt = src_ds.GetGeoTransform()
            self.nodata = srcband.GetNoDataValue()
            """ Turn a Raster with a single band into a 2D [x,y] = v array """
            self.array = srcband.ReadAsArray()

            # Now mask out any NAN or nodata values (we do both for consistency)
            if self.nodata is not None:
                self.array = np.ma.array(self.array, mask=(np.isnan(self.array) | (self.array == self.nodata)))

            self.dataType = srcband.DataType
            self.min = np.nanmin(self.array)
            self.max = np.nanmax(self.array)
            self.proj = src_ds.GetProjection()

            # Remember:
            # [0]/* top left x */
            # [1]/* w-e pixel resolution */
            # [2]/* rotation, 0 if image is "north up" */
            # [3]/* top left y */
            # [4]/* rotation, 0 if image is "north up" */
            # [5]/* n-s pixel resolution */
            self.left = self.gt[0]
            self.cellWidth = self.gt[1]
            self.top = self.gt[3]
            self.cellHeight = self.gt[5]
            self.cols = src_ds.RasterXSize
            self.rows = src_ds.RasterYSize
            # Important to throw away the srcband
            srcband.FlushCache()
            srcband = None

        except RuntimeError as e:
            self.log.error('Could not retrieve meta Data for %s' % self.filepath, e)
            raise e

    def getPixelVal(self, pt):
        # Convert from map to pixel coordinates.
        # Only works for geotransforms with no rotation.
        px = int((pt[0] - self.left) / self.cellWidth)  # x pixel
        py = int((pt[1] - self.top) / self.cellHeight)  # y pixel
        val = self.array[py, px]
        if isclose(val, self.nodata, rel_tol=1e-07):
            return np.nan

        return val

def isclose(a, b, rel_tol=1e-09, abs_tol=0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)