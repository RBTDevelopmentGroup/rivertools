import argparse
import sys
from shapely.geometry import *
import geojson
from functools import partial
import pyproj
from shapely.ops import transform
from rivertools.logger import Logger
from shapes import Shapefile

def export(args):
    """
    Reproject a ShapeFile to WGS84 and export to GeoJSON

    :param args:
    :return: None
    """

    log = Logger("Reach Export")

    # Load the Shapefile and obtain the Spatial Reference as Proj4
    log.info("Opening Shapefiles...")
    originalShp = Shapefile(args.river.name)
    originalSRS = originalShp.spatialRef.ExportToProj4()
    originalProj4 = pyproj.Proj(originalSRS)

    # Pull the geometry objects out and disregard the fields
    raw_geometry = originalShp.featuresToShapely()[0]['geometry']

    # Optional simplication of the geometry using Shapely simplify
    simple_poly = raw_geometry
    if args.tolerance:
        simple_poly = raw_geometry.simplify(args.tolerance)

    # Re-project the geometry to WGS84
    reproject = partial(pyproj.transform, originalProj4, pyproj.Proj(init='epsg:4326'))
    trans_poly = transform(reproject, simple_poly)

    # Convert the geometry to GeoJSON and write to file
    geom_in_geojson = geojson.Feature(geometry=trans_poly, properties={})
    with open(args.json, 'w+') as outfile:
        geojson.dump(geom_in_geojson, outfile)

def main():
    
    log = Logger("Initializing")

    # parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument('river',
                        help='Path to the river shape file. Donuts will be ignored.',
                        type=argparse.FileType('r'))
    parser.add_argument('json',
                        help='Path to the output GeoJSON file',
                        type=str)
    parser.add_argument('--tolerance',
                        help='Simplification tolerance in the linear units of the river ShapeFile.',
                        type=float,
                        default=5.0)
    args = parser.parse_args()

    if not args.river or not args.json:
        log.error("ERROR: Missing arguments")
        parser.print_help()
        exit(0)

    log = Logger("Program")

    try:
        export(args)
        log.info("Completed Successfully")
    except AssertionError as ex:
        log.error("Assertion Error", ex)
        sys.exit(0)
    except Exception as ex:
        log.error('Unexpected error: {0}'.format(sys.exc_info()[0]), ex)
        raise
        sys.exit(0)
        
if __name__ == "__main__":
    main()