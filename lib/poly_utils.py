"""Preprocessing tools to cut polygons and write their new coordinates.

Author: Perry Roth-Johnson
Last modified: March 14, 2014

"""


import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString
from descartes import PolygonPatch


# cut up the layer polygons to prepare for grid generation
def cut_polygon(original, bounding, ext_label, area_threshold=1.0e-08):
    """Cut the original layer polygon with the bounding polygon."""
    try:
        p_new = original.intersection(bounding)
    except:
        raise Warning("The original polygon does not intersect the bounding polygon!")
    # check if extra negligibly small polygons were created
    if p_new.geom_type != 'Polygon':
        fmt = " In '{0}' region, found a non-Polygon made of {1} polygons. "
        print fmt.format(ext_label,len(p_new.geoms))
        print ' -> area threshold set to', area_threshold
        good_poly_index = None
        num_good_polys_found = 0
        for i,p in enumerate(p_new.geoms):
            fmt2 = '   polygon[{0}]: area={1:5.3e}, centroid=({2:.4},{3:.4})'
            print fmt2.format(i,p.area,p.centroid.xy[0][0],p.centroid.xy[1][0])
            if p.area > area_threshold:
                # only keep polygons with significant area
                good_poly_index = i
                num_good_polys_found += 1
                print '   ...keep polygon[{0}]!'.format(i)
            else:
                # throw out any polygon with insignificant area
                print '   ...throw out polygon[{0}]'.format(i)
        # overwrite p_new with the good polygon
        if num_good_polys_found > 1:
            raise Warning("More than 1 good polygon found. Check bounding polygon coords!")
        try:
            p_new = p_new.geoms[good_poly_index]
        except TypeError:
            raise Warning("The original polygon does not intersect the bounding polygon!")
    return p_new

def plot_polygon(p, face_color, edge_color='r'):
    """Plot a polygon on the current axes."""
    # get the current axes, so we can add polygons to the plot
    ax = plt.gcf().gca()
    patch = PolygonPatch(p, fc=face_color, ec=edge_color, alpha=0.8)
    ax.add_patch(patch)

def cut_plot_and_write_alt_layer(part, material, ext_label, b_polygon,
    area_threshold=1.0e-08, airfoil=None):
    """Cut, plot, and write a polygon for an alternate layer.

    Parameters
    ----------
    part : object, the structural part containing the material layer to be cut
    material : str, the name of the material layer to be cut
    ext_label : str, extension label to name the new layer created from the cut
    b_polygon : shapely.polygon object, the bounding polygon
    area_threshold : float, polygons with areas smaller than this threshold
        will be thrown out
    airfoil : str, set to either 'lower' or 'upper', to designate which airfoil
        should be cut in a biplane station (default=None for monoplane
        stations)

    """
    l = part.layer[material]
    # cut polygon
    p_new = cut_polygon(l.polygon, b_polygon, ext_label, area_threshold)
    # plot polygon
    plot_polygon(p_new, l.face_color)
    # save alt layer as an attribute of this part
    new_layer_name = material + ', ' + ext_label
    l.parent_part.add_new_layer(new_layer_name, p_new, material)
    new_layer = part.alt_layer[new_layer_name]
    # write polygon exterior to text file in `station_path`
    new_layer.write_polygon_edges(airfoil=airfoil)
    # find and plot the corners of the new layer
    new_layer.find_corners(b_polygon)
    plot_corners(new_layer.corners)

def plot_corners(list_of_corners):
    ax = plt.gca()
    for corner in list_of_corners:
        ax.scatter(corner.x, corner.y, s=40, alpha=0.8, zorder=100)
