"""Determine the layer plane angle of all the elements in a grid.

Author: Perry Roth-Johnson
Last modified: March 17, 2014

References:
http://stackoverflow.com/questions/3365171/calculating-the-angle-between-two-lines-without-having-to-calculate-the-slope/3366569#3366569
http://stackoverflow.com/questions/19295725/angle-less-than-180-between-two-segments-lines

"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import lib.grid as gr
reload(gr)
import lib.abaqus_utils2 as au
reload(au)
import lib.vabs_utils as vu
reload(vu)
from shapely.geometry import Polygon, LineString
from descartes import PolygonPatch


# -----------------------------------------------
# update these parameters!
station_num = 2
# -----------------------------------------------

stn_str = 'stn{0:02d}'.format(station_num)
plt.close('all')
# create a figure
plt.figure(num='Station #{0:02d}'.format(station_num))
ax = plt.gcf().gca()

# outer_edge_node_nums=[1,4], inner_edge_node_nums=[2,3]
list_of_unflipped_elementsets = [
    'rbtrile',
    'rbtriscl',
    'esgelle',
    'esgelscl',
    'estrile',
    'estriscl',
    'isresle',
    'isresscl',
    'istrile',
    'istriscl'
    ]

# outer_edge_node_nums=[3,2], inner_edge_node_nums=[4,1]
list_of_flipped_elementsets = [
    'rbtrite',
    'rbtrilr',
    'rbtriur',
    'rbtriscu',
    'esgelte',
    'esgellr',
    'esgelur',
    'esgelscu',
    'estrite',
    'estrilr',
    'estriur',
    'estriscu',
    'isreste',
    'isreslr',
    'isresur',
    'isresscu',
    'istrite',
    'istrilr',
    'istriur',
    'istriscu'
    ]

# outer_edge_node_nums=[2,1], inner_edge_node_nums=[3,4]
list_of_weird_elementsets = [
    'scupper',
    'teuniax'
]

# outer_edge_node_nums=[4,3], inner_edge_node_nums=[1,2]
list_of_weird_elementsets2 = [
    'sclower'
]

# import the initial grid object
fmt_grid = 'sandia_blade/' + stn_str + '/mesh_' + stn_str + '.abq'
g = au.AbaqusGrid(fmt_grid, debug_flag=True)
# check that all elements have counter-clockwise orientation
# print "  Checking that all elements have counter-clockwise orientation..."
# for elem in g.list_of_elements:
#     if not elem.is_ccw():
#         fmt = "    Element #{:d} is bad! Its nodes are not oriented CCW."
#         print fmt.format(elem.elem_num)
# update the grid object with all the layer plane angles
for elem in g.list_of_elements:
    if elem.element_set in list_of_unflipped_elementsets:
        elem.calculate_layer_plane_angle(outer_edge_node_nums=[1,4],
            inner_edge_node_nums=[2,3])
    elif elem.element_set in list_of_flipped_elementsets:
        elem.calculate_layer_plane_angle(outer_edge_node_nums=[3,2],
            inner_edge_node_nums=[4,1])
    elif elem.element_set in list_of_weird_elementsets:
        elem.calculate_layer_plane_angle(outer_edge_node_nums=[2,1], 
            inner_edge_node_nums=[3,4])
    elif elem.element_set in list_of_weird_elementsets2:
        elem.calculate_layer_plane_angle(outer_edge_node_nums=[4,3], 
            inner_edge_node_nums=[1,2])
    else:
        raise Warning("Element #{0} has no element set!".format(elem.elem_num))
# plot a small selection of elements to check the results
for elem in g.list_of_elements[::25]:
# for elem in g.list_of_elements[:150:5]:
    elem.plot(label_nodes=False)
    print elem.elem_num, elem.element_set, elem.theta1
# show the plot
plt.xlim([-3,3])
plt.ylim([-3,3])
ax.set_aspect('equal')

plt.figure(num='Station #{0:02d}, theta1 vs. elem_num'.format(
    station_num))
enum=np.arange(g.number_of_elements)+1
theta=np.zeros(g.number_of_elements)
elemset=[]
for i,elem in enumerate(g.list_of_elements):
    theta[i] = elem.theta1
    elemset.append(elem.element_set)
plt.plot(enum,theta)
plt.xlabel('element number [#]')
plt.ylabel('theta1 [deg]')
plt.grid('on')

plt.show()
# -----------------------------------------------------------------------------
# read layers.csv to determine the number of layers
layer_file = pd.read_csv('sandia_blade/layers.csv', index_col=0)
number_of_layers = len(layer_file)
# write the updated grid object to a VABS input file
fmt_vabs = 'sandia_blade/' + stn_str + '/mesh_' + stn_str + '.vabs'
f = vu.VabsInputFile(
    vabs_filename=fmt_vabs,
    grid=g,
    material_filename='sandia_blade/materials.csv',
    layer_filename='sandia_blade/layers.csv',
    debug_flag=True,
    flags={
        'format'           : 1,
        'Timoshenko'       : 1,
        'recover'          : 0,
        'thermal'          : 0,
        'curve'            : 0,
        'oblique'          : 0,
        'trapeze'          : 0,
        'Vlasov'           : 0
    })
