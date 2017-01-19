# These are for graphic only
import matplotlib.pyplot as plt
from shapely.geometry import *
from matplotlib.collections import PolyCollection
from descartes import PolygonPatch
import os

class Plotter:

    def __init__(self):
        self.fig = plt.figure(1, figsize=(10, 10))
        self.ax = self.fig.gca()

    def plotShape(self, mp, color, alpha, zord, label=None):
        """
        Nothing fancy here. Just a plotting function to help us visualize
        :param ax:
        :param mp:
        :param color:
        :param alpha:
        :param zord:
        :return:
        """
        # We're using Descartes here for polygonpathc
        if mp.type == 'Polygon':
            self.ax.add_patch(PolygonPatch(mp, fc=color, ec='#000000', lw=0.2, alpha=alpha, zorder=zord, label=label))

        elif mp.type == 'LineString':
            x, y = mp.xy
            self.ax.plot(x, y, color=color, alpha=alpha, linewidth=1, solid_capstyle='round', zorder=zord, label=label)

        elif mp.type == 'MultiPoint':
            for idx, p in enumerate(mp):
                x, y = p.xy
                label = label if idx == 0 else None
                self.ax.plot(x, y, color=color, alpha=alpha, markersize=2, marker="o", zorder=zord, label=label)


        elif mp.type == 'MultiLineString':
            for idx, p in enumerate(mp):
                x, y = p.xy
                label = label if idx==0 else None
                self.ax.plot(x, y, color=color, alpha=alpha, linewidth=1, solid_capstyle='round', zorder=zord, label=label)

        elif mp.type == 'MultiPolygon':
            coll = PolyCollection(list([tuple(p.exterior.coords) for p in mp]), facecolors=color, edgecolors='#000000', linewidths=0.5, label=label)
            coll.set_alpha(alpha)
            coll.set_zorder(0.2)
            self.ax.add_collection(coll)

    @staticmethod
    def savePlot(path, bounds=None):
        if bounds is not None:
            plt.ylim(bounds[1], bounds[3])
            plt.xlim(bounds[0], bounds[2])
        plt.autoscale(enable=False)
        plt.title(" ".join(os.path.basename(path).split("-")))
        plt.legend(loc='best', prop={'size':6})
        plt.savefig(path, dpi=(300))
        plt.close()

    @staticmethod
    def showPlot(bounds=None):
        if bounds is not None:
            plt.ylim(bounds[1], bounds[3])
            plt.xlim(bounds[0], bounds[2])
        plt.autoscale(enable=False)
        plt.legend(loc='best')
        plt.show()
        plt.close()
        return
