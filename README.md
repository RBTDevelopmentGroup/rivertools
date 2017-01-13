# RiverTools

## Centerline

```sh
usage: centerline.py [-h] [--smoothing SMOOTHING] [--noviz]
                     river thalweg islands centerline

positional arguments:
  river                 Path to the river shape file. Donuts will be ignored.
  thalweg               Path to the thalweg shapefile
  islands               Path to the islands shapefile.
  centerline            Path to the desired output centerline shapefile

optional arguments:
  -h, --help            show this help message and exit
  --smoothing SMOOTHING
                        smoothing "s" factor for the curve. (default=0/None)
  --noviz               Disable result visualization (faster)

```


## CrossSections

```sh
usage: crosssections.py [-h] [--noviz]
                        river islands centerline dem crosssections

positional arguments:
  river          Path to the river shape file. Donuts will be ignored.
  islands        Path to the islands shapefile.
  centerline     Path to the centerline shapefile
  dem            Path to the DEM Raster (used for metric calculation)
  crosssections  Path to the desired output crosssections

optional arguments:
  -h, --help     show this help message and exit
  --noviz        Disable result visualization (faster)

```