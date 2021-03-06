"""A module for manipulating single material layers of structural parts.

Author: Perry Roth-Johnson
Last updated: October 11, 2013

"""


import os
import numpy as np
from shapely.geometry import asLineString, Point, LineString
from shapely.affinity import translate


class Layer:
    """Define a layer made of a single material for a structural part.

    Parameters:
    -----------
    polygon : shapely.Polygon object, represents the boundary of this layer
    material : Material object, the material properties of this layer
    parent_part : structure.Part object, the part this layer belongs to
    name : str, the name of this layer
    mass : float, the mass per unit length of this layer
    left : np.array, coords for left edge, saved later by get_and_save_edges()
    top : np.array, coords for top edge, saved later by get_and_save_edges()
    right : np.array, coords for right edge, saved later by
        get_and_save_edges()
    bottom : np.array, coords for bottom edge, saved later by
        get_and_save_edges()
    face_color : str, hex color code for plotting this layer face
        (default: red)
    edge_color : str, hex color code for plotting this layer edge
        (default: black)
    corners : list of shapely Point objects, the corners of this polygon
    edges : list of numpy arrays of coords for each edge of this polygon

    """
    def __init__(self, polygon, material, parent_part, name,
        face_color='#FF0000', edge_color='#000000'):
        self.polygon = polygon
        self.material = material
        self.parent_part = parent_part
        self.name = name
        self.mass = self.polygon.area*self.material.rho  # mass per unit length
        self.left = None  # saved later by <part>.get_and_save_edges()
        self.top = None  # saved later by <part>.get_and_save_edges()
        self.right = None  # saved later by <part>.get_and_save_edges()
        self.bottom = None  # saved later by <part>.get_and_save_edges()
        self.face_color = face_color
        self.edge_color = edge_color
        self.corners = []
        self.edges = []

    def area_fraction(self):
        """Calculate the ratio of this part area to the cross-section area."""
        total_area = self.parent_part.parent_structure.area
        return self.polygon.area/total_area

    def mass_fraction(self):
        """Calculate the ratio of this part mass to the cross-section mass."""
        total_mass = self.parent_part.parent_structure.mass
        return self.mass/total_mass

    def plot_edges(self, axes):
        """Plots the polygon edges of this layer."""
        if self.left is None:
            raise ValueError("Layer instance has attribute <layer>.left=None.\n  Try running <station>.structure.<part>.get_and_save_edges() first.")
        axes.plot(self.left[:,0], self.left[:,1], 'bo-')
        axes.plot(self.top[:,0], self.top[:,1], 'g^-')
        axes.plot(self.right[:,0], self.right[:,1], 'rs-')
        axes.plot(self.bottom[:,0], self.bottom[:,1], 'c*-')

    def get_edges(self):
        """Returns 4 arrays of coords for each edge of this layer."""
        p = self.polygon  # get the polygon for this layer
        # store the polygon exterior coords as a numpy array
        a = np.array(p.exterior.coords)
        # get the x- and y-coordinates of the polygon exterior
        x = a[:,0]
        y = a[:,1]
        if self.parent_part.__class__.__name__ == 'RootBuildup':
            # find the indices where the x-coord is equal to zero
            match_x = np.nonzero(x==0.0)[0]
            # find the indices where the y-coord is equal to the right edge
            match_y = np.nonzero(y==0.0)[0]
            # group all the indices together in a sorted array
            match = np.append(match_x, match_y)
        elif self.parent_part.__class__.__name__ == 'LE_Panel':
            # get the coordinates for the right edge of the LE panel
            r = self.parent_part.right
            # find the indices where the x-coordinate is equal to the right
            #   edge of the LE panel (the "corners" of the LE panel)
            match = np.nonzero(x==r)[0]
        elif self.parent_part.__class__.__name__ == 'SparCap':
            # get the coordinates for the left and right edges
            l = self.parent_part.left
            r = self.parent_part.right
            # find the indices where the x-coord is equal to the left edge
            match_l = np.nonzero(x==l)[0]
            # find the indices where the x-coord is equal to the right edge
            match_r = np.nonzero(x==r)[0]
            # group all the indices together in a sorted array
            match = np.append(match_l, match_r)
        elif self.parent_part.__class__.__name__ == 'AftPanel':
            # get the coordinates for the left and right edges
            l = self.parent_part.left
            r = self.parent_part.right
            # find the indices where the x-coord is equal to the left edge
            match_l = np.nonzero(x==l)[0]
            # find the indices where the x-coord is equal to the right edge
            match_r = np.nonzero(x==r)[0]
            # group all the indices together in a sorted array
            match = np.append(match_l, match_r)
        elif self.parent_part.__class__.__name__ == 'TE_Reinforcement':
            if self.name == 'uniax' or self.name == 'foam':
                # get the coordinates for the left edge
                l = self.parent_part.left
                # find the indices where the x-coord is equal to the left edge
                match = np.nonzero(x==l)[0]
            else:
                # this is an alternate layer
                # get the coordinates for the left and right edges
                if self.name.endswith('left'):
                    l = self.parent_part.left_vertex[0]
                    r = self.parent_part.foam_left_vertex[0]
                elif self.name.endswith('middle'):
                    l = self.parent_part.foam_left_vertex[0]
                    r = self.parent_part.uniax_left_vertex[0]
                elif self.name.endswith('right'):
                    l = self.parent_part.uniax_left_vertex[0]
                    r = self.parent_part.uniax_right_vertex[0]
                # find the indices where the x-coord is equal to the left edge
                match_l = np.nonzero(x==l)[0]
                # find the indices where the x-coord is equal to the right edge
                match_r = np.nonzero(x==r)[0]
                # group all the indices together in a sorted array
                match = np.append(match_l, match_r)
        elif self.parent_part.__class__.__name__ == 'ShearWeb':
            # get the coordinates for the left and right edges
            if self.name == 'biax, left':
                l = self.parent_part.left
                r = self.parent_part.left + self.parent_part.base_biax
            elif self.name == 'foam':
                l = self.parent_part.left + self.parent_part.base_biax
                r = self.parent_part.right - self.parent_part.base_biax
            elif self.name == 'biax, right':
                l = self.parent_part.right - self.parent_part.base_biax
                r = self.parent_part.right
            # find the indices where the x-coord is equal to the left edge
            match_l = np.nonzero(x==l)[0]
            # find the indices where the x-coord is equal to the right edge
            match_r = np.nonzero(x==r)[0]
            # group all the indices together in a sorted array
            match = np.append(match_l, match_r)
        elif self.parent_part.__class__.__name__ == 'ExternalSurface':
            stn = self.parent_part.parent_structure.parent_station
            sharp_TE = stn.airfoil.has_sharp_TE
            if not sharp_TE:
                # find the indices where the x-coord is equal to zero
                match_x = np.nonzero(x==0.0)[0]
                # find the indices where the y-coord is equal to the right edge
                match_y = np.nonzero(y==0.0)[0]
                # group all the indices together in a sorted array
                match = np.append(match_x, match_y)
        match.sort()
        # split the polygon up at each of the corners into 4 "edges"
        edge1 = a[match[0]:match[1]+1,:]
        edge2 = a[match[1]:match[2]+1,:]
        edge3 = a[match[2]:match[3]+1,:]
        try:
            edge4 = a[match[3]:match[4]+1,:]
        except IndexError:
            edge4 = np.append(a[match[3]:,:],a[1:match[0]+1,:],axis=0)
        return (edge1, edge2, edge3, edge4)

    def get_edges2(self, tol=1e-08):
        """Saves a list of arrays of coords for each edge of this layer.

        This is an alternate version of the method get_edges().

        Saves:
        self.edges

        """
        def duplicate(e):
            """Check for edges made of duplicate corners."""
            duplicate_flag = False
            if len(e) == 2:
                z = (e[0] - e[1])
                if (abs(z[0]) < tol) and (abs(z[1]) < tol):
                    duplicate_flag = True
            return duplicate_flag
        p = self.polygon  # get the polygon for this layer
        # store the polygon exterior coords as a numpy array
        a = np.array(p.exterior.coords)
        # find the indices of the corners
        match = []
        for corner in self.corners:
            c = np.array((corner.x, corner.y))
            corner_index = np.where((a==c).all(axis=1))[0][0]
            match.append(corner_index)
        match.sort()
        # split the polygon up at each of the corners into "edges"
        for m in range(len(match))[:-1]:
            edge = a[match[m]:match[m+1]+1,:]
            if not duplicate(edge):
                self.edges.append(edge)
        # grab the last edge
        if len(a[:match[0],:]) > 0:
            # if the last edge wraps from the last element of `a`
            #   to the first element of `a`
            last_edge = np.vstack((a[match[-1]:-1,:], a[:match[0]+1,:]))
        else:
            # if the last edge ends at the last element of `a`
            last_edge = a[match[-1]:,:]
        if not duplicate(last_edge):
            self.edges.append(last_edge)

    def get_and_save_edges(self):
        """Identifies and saves the left, top, right, and bottom (LTRB) edges.

        This method saves the LTRB edges as attributes within the layer object.

        self.left : np.array, coords for left edge
        self.top : np.array, coords for top edge
        self.right : np.array, coords for right edge
        self.bottom : np.array, coords for bottom edge

        """
        edges = self.get_edges()
        # get centroids
        centroids = []
        triangular_region = False
        for edge in edges:
            try:
                centroids.append(asLineString(edge).centroid)
            except ValueError:
                # if the region is triangular, one of its "edges" will be a
                #   point, not a line string.
                triangular_region = True
        # determine which edges are top, bottom, left, and right
        if not triangular_region:
            l = range(4)  # list of indices, one for each edge
            c = np.array([[centroids[0].x, centroids[0].y],
                          [centroids[1].x, centroids[1].y],
                          [centroids[2].x, centroids[2].y],
                          [centroids[3].x, centroids[3].y]])
            cx = c[:,0]
            cy = c[:,1]
            x_max_ind = np.nonzero(cx==cx.max())[0][0]
            x_min_ind = np.nonzero(cx==cx.min())[0][0]
            y_max_ind = np.nonzero(cy==cy.max())[0][0]
            y_min_ind = np.nonzero(cy==cy.min())[0][0]
        else:
            l = range(3)
            c = np.array([[centroids[0].x, centroids[0].y],
                          [centroids[1].x, centroids[1].y],
                          [centroids[2].x, centroids[2].y]])
            cx = c[:,0]
            cy = c[:,1]
            x_min_ind = np.nonzero(cx==cx.min())[0][0]
            y_max_ind = np.nonzero(cy==cy.max())[0][0]
            y_min_ind = np.nonzero(cy==cy.min())[0][0]
        if self.parent_part.__class__.__name__ == 'RootBuildup':
            # find centroid at x=0
            ind_x = np.nonzero(cx==0.0)[0][0]
            l.remove(ind_x)  # remove the index for the right edge
            # find centroid at y=0
            ind_y = np.nonzero(cy==0.0)[0][0]
            l.remove(ind_y)  # remove the index for the left edge
            if self.name == 'triax, lower left':
                self.right = edges[ind_x]  # right edge saved!
                self.left = edges[ind_y]  # left edge saved!
            elif self.name == 'triax, lower right':
                self.left = edges[ind_x]  # left edge saved!
                self.right = edges[ind_y]  # right edge saved!
            elif self.name == 'triax, upper right':
                self.left = edges[ind_x]  # left edge saved!
                self.right = edges[ind_y]  # right edge saved!
            elif self.name == 'triax, upper left':
                self.right = edges[ind_x]  # right edge saved!
                self.left = edges[ind_y]  # left edge saved!
            # find top and bottom edges
            if centroids[l[0]].y > centroids[l[1]].y:
                self.top = edges[l[0]]     # top edge saved!
                self.bottom = edges[l[1]]  # bottom edge saved!
            else:
                self.top = edges[l[1]]     # top edge saved!
                self.bottom = edges[l[0]]  # bottom edge saved!
        elif self.parent_part.__class__.__name__ == 'LE_Panel':
            l.remove(x_min_ind)  # remove the index for the left edge
            self.left = edges[x_min_ind]  # left edge saved!
            l.remove(y_max_ind)  # remove the index for the top edge
            self.top = edges[y_max_ind]  # top edge saved!
            l.remove(y_min_ind)  # remove the index for the bottom edge
            self.bottom = edges[y_min_ind]  # bottom edge saved!
            self.right = edges[l[0]]  # right edge saved!
        elif self.parent_part.__class__.__name__ == 'SparCap':
            l.remove(x_min_ind)  # remove the index for the left edge
            self.left = edges[x_min_ind]  # left edge saved!
            l.remove(x_max_ind)  # remove the index for the right edge
            self.right = edges[x_max_ind]  # right edge saved!
            if centroids[l[0]].y > centroids[l[1]].y:
                self.top = edges[l[0]]     # top edge saved!
                self.bottom = edges[l[1]]  # bottom edge saved!
            else:
                self.top = edges[l[1]]     # top edge saved!
                self.bottom = edges[l[0]]  # bottom edge saved!
        elif self.parent_part.__class__.__name__ == 'AftPanel':
            l.remove(x_min_ind)  # remove the index for the left edge
            self.left = edges[x_min_ind]  # left edge saved!
            l.remove(x_max_ind)  # remove the index for the right edge
            self.right = edges[x_max_ind]  # right edge saved!
            if centroids[l[0]].y > centroids[l[1]].y:
                self.top = edges[l[0]]     # top edge saved!
                self.bottom = edges[l[1]]  # bottom edge saved!
            else:
                self.top = edges[l[1]]     # top edge saved!
                self.bottom = edges[l[0]]  # bottom edge saved!
        elif self.parent_part.__class__.__name__ == 'TE_Reinforcement':
            if self.name == 'uniax' or self.name == 'foam':
                l.remove(x_max_ind)  # remove the index for the right edge
                self.right = edges[x_max_ind]  # right edge saved!
                l.remove(y_max_ind)  # remove the index for the top edge
                self.top = edges[y_max_ind]  # top edge saved!
                l.remove(y_min_ind)  # remove the index for the bottom edge
                self.bottom = edges[y_min_ind]  # bottom edge saved!
                self.left = edges[l[0]]  # left edge saved!
            else:
                # this is an alternate layer
                l.remove(x_min_ind)  # remove the index for the left edge
                self.left = edges[x_min_ind]  # left edge saved!
                if not triangular_region:
                    # if this region is rectangular, assign the right edge
                    l.remove(x_max_ind)  # remove the index for the right edge
                    self.right = edges[x_max_ind]  # right edge saved!
                else:
                    self.right = None
                if centroids[l[0]].y > centroids[l[1]].y:
                    self.top = edges[l[0]]     # top edge saved!
                    self.bottom = edges[l[1]]  # bottom edge saved!
                else:
                    self.top = edges[l[1]]     # top edge saved!
                    self.bottom = edges[l[0]]  # bottom edge saved!
        elif self.parent_part.__class__.__name__ == 'ShearWeb':
            l.remove(x_min_ind)  # remove the index for the left edge
            self.left = edges[x_min_ind]  # left edge saved!
            l.remove(x_max_ind)  # remove the index for the right edge
            self.right = edges[x_max_ind]  # right edge saved!
            if centroids[l[0]].y > centroids[l[1]].y:
                self.top = edges[l[0]]     # top edge saved!
                self.bottom = edges[l[1]]  # bottom edge saved!
            else:
                self.top = edges[l[1]]     # top edge saved!
                self.bottom = edges[l[0]]  # bottom edge saved!

    def find_corners(self, bounding_polygon, tol=1.0e-08, print_flag=False):
        """Find the corners of a layer cut by a bounding polygon.

        Saves: self.corners

        """
        list_of_corners = []
        bounding_line = LineString(bounding_polygon.exterior)
        for coord in self.polygon.exterior.coords[:-1]:
            pt = Point(coord[0],coord[1])
            # determine if this point is on the bounding_polygon
            if bounding_line.distance(pt) < tol:
                list_of_corners.append(pt)
                if print_flag:
                    print pt
        self.corners = list_of_corners

    def write_alt_layer_edges(self, f):
        """Writes the edges for this alternate layer in the file f."""
        part_name = self.parent_part.__class__.__name__  # part name
        layer_name = self.name  # layer name
        if part_name in ['ShearWeb', 'AftPanel', 'InternalSurface']:
            part_num = self.parent_part.num
            prefix = '{0}{1}; {2}'.format(part_name, part_num, layer_name)
        else:
            prefix = '{0}; {1}'.format(part_name, layer_name)
        # get the edges
        self.get_edges2()
        for edge in self.edges:
            f.write('curd # lp3\n')
            for cd_pair in edge:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(
                    cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')

    def write_alt_layer_edges2(self, f, start_edge_num, tol=1e-07):
        """Writes the edges for this alternate layer in the file f.

        This is an alternate version of the method write_alt_layer_edges()

        """
        part_name = self.parent_part.__class__.__name__  # part name
        layer_name = self.name  # layer name
        if part_name in ['ShearWeb', 'AftPanel', 'InternalSurface']:
            part_num = self.parent_part.num
            prefix = '{0}{1}; {2}'.format(part_name, part_num, layer_name)
        else:
            prefix = '{0}; {1}'.format(part_name, layer_name)
        # get the edges
        self.get_edges2()
        if len(self.edges) > 4:
            # look for small edges and throw them out
            bad_edge = None
            for i,edge in enumerate(self.edges):
                if len(edge) == 2:
                    b = edge[0]-edge[1]
                    if (b[0] < tol) and (b[1] < tol):
                        bad_edge = i
            if bad_edge is not None:
                self.edges.pop(bad_edge)
                print "*** Warning: In '{0},' a small edge was found and thrown out!".format(prefix)
        for edge in self.edges:
            f.write('curd {0} lp3\n'.format(start_edge_num))
            start_edge_num += 1
            for cd_pair in edge:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(
                    cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')

    def write_layer_edges(self, f, start_edge_num, triangular_region=False):
        """Writes the edges for this layer in the file f.

        Returns a dictionary of ID numbers for each edge.
        d['<part>, <layer>, left'] : start_edge_num
        d['<part>, <layer>, bottom'] : start_edge_num+1
        d['<part>, <layer>, right'] : start_edge_num+2
        d['<part>, <layer>, top'] : start_edge_num+3

        If triangular_region=True, then only 3 items are in the dictionary.
        d['<part>, <layer>, left'] : start_edge_num
        d['<part>, <layer>, bottom'] : start_edge_num+1
        d['<part>, <layer>, top'] : start_edge_num+2

        Parameters
        ----------
        f : file object, the handle for the file being written to
        start_edge_num : int, the ID number for the first edge being written

        """
        part_name = self.parent_part.__class__.__name__  # part name
        layer_name = self.name  # layer name
        if part_name in ['ShearWeb', 'AftPanel', 'InternalSurface']:
            part_num = self.parent_part.num
            prefix = '{0}{1}; {2}'.format(part_name, part_num, layer_name)
        else:
            prefix = '{0}; {1}'.format(part_name, layer_name)
        if triangular_region:
            d = {'{0}; left'.format(prefix) : start_edge_num,
                 '{0}; bottom'.format(prefix) : start_edge_num+1,
                 '{0}; top'.format(prefix) : start_edge_num+2}
        else:
            # this is a quadrilateral region
            d = {'{0}; left'.format(prefix) : start_edge_num,
                 '{0}; bottom'.format(prefix) : start_edge_num+1,
                 '{0}; right'.format(prefix) : start_edge_num+2,
                 '{0}; top'.format(prefix) : start_edge_num+3}
        # left edge
        f.write('curd {0} lp3\n'.format(start_edge_num))
        for cd_pair in self.left:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        # bottom edge
        f.write('curd {0} lp3\n'.format(start_edge_num+1))
        for cd_pair in self.bottom:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        if triangular_region:
            # top edge
            f.write('curd {0} lp3\n'.format(start_edge_num+2))
            for cd_pair in self.top:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')
        else:
            # right edge
            f.write('curd {0} lp3\n'.format(start_edge_num+2))
            for cd_pair in self.right:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')
            # top edge
            f.write('curd {0} lp3\n'.format(start_edge_num+3))
            for cd_pair in self.top:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')
        return d

    def write_layer_edges2(self, f, curve_num_placeholder='#'):
        """Writes the edges for this layer in the file f.

        Parameters
        ----------
        f : file object, the handle for the file being written to

        """
        part_name = self.parent_part.__class__.__name__  # part name
        layer_name = self.name  # layer name
        if part_name in ['ShearWeb', 'AftPanel', 'InternalSurface']:
            part_num = self.parent_part.num
            prefix = '{0}{1}; {2}'.format(part_name, part_num, layer_name)
        else:
            prefix = '{0}; {1}'.format(part_name, layer_name)
        # left edge
        f.write('curd {0} lp3\n'.format(curve_num_placeholder))
        for cd_pair in self.left:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        # bottom edge
        f.write('curd {0} lp3\n'.format(curve_num_placeholder))
        for cd_pair in self.bottom:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        # right edge
        f.write('curd {0} lp3\n'.format(curve_num_placeholder))
        for cd_pair in self.right:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        # top edge
        f.write('curd {0} lp3\n'.format(curve_num_placeholder))
        for cd_pair in self.top:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')

    def write_polygon_edges(self, airfoil=None):
        """Write edges for this layer's polygon to a file in `station_path`."""
        stn = self.parent_part.parent_structure.parent_station
        part_name = self.parent_part.__class__.__name__  # part name
        layer_name = self.name  # layer name
        if part_name in ['ShearWeb', 'AftPanel', 'InternalSurface']:
            part_num = self.parent_part.num
            if airfoil is None:
                prefix = '{0}{1}_{2}'.format(part_name, part_num, layer_name)
            elif airfoil == 'lower':
                prefix = 'lower_{0}{1}_{2}'.format(part_name, part_num, layer_name)
            elif airfoil == 'upper':
                prefix = 'upper_{0}{1}_{2}'.format(part_name, part_num, layer_name)
            else:
                raise ValueError("`airfoil` keyword must be 'lower' or 'upper'")
        else:
            if airfoil is None:
                prefix = '{0}_{1}'.format(part_name, layer_name)
            elif airfoil == 'lower':
                prefix = 'lower_{0}_{1}'.format(part_name, layer_name)
            elif airfoil == 'upper':
                prefix = 'upper_{0}_{1}'.format(part_name, layer_name)
            else:
                raise ValueError("`airfoil` keyword must be 'lower' or 'upper'")
        f = open(os.path.join(stn.station_path,prefix+'.txt'), 'w')
        # exterior
        f.write('# exterior:\n')
        f.write('# ---------\n')
        for cd_pair in self.polygon.exterior.coords:
            f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
        f.write(';;\n\n')
        # interior
        try:
            # pick the first interior sequence
            # (layers should not have multiple interiors)
            interior = self.polygon.interiors[0]
            f.write('# interior:\n')
            f.write('# ---------\n')
            for cd_pair in interior.coords:
                f.write('{0: .8f}  {1: .8f}  0.0\n'.format(cd_pair[0], cd_pair[1]))
            f.write(';;\n\n')
        except IndexError:
            # no interior coords exist
            pass
        f.close()

    def move(self, x3_offset, alt_layer=False):
        """Translate a layer in the vertical (x3) direction."""
        # translate the polygon
        self.polygon = translate(self.polygon, yoff=x3_offset)
        # translate the corners
        for i in range(len(self.corners)):
            new_corner = translate(self.corners[i], yoff=x3_offset)
            self.corners[i] = new_corner
        if not alt_layer:
            # in a regular layer, update the left, right, top, and bottom edges
            #   so they will be translated too
            self.get_and_save_edges()
        else:
            # in an alt layer, translate the edges
            for edge in self.edges:
                edge[:,1] += x3_offset
