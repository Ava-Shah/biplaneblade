"""A module for organizing geometrical data for a blade station.

Note: to generate html documentation of this module, open a Windows cmd prompt:
> cd path/to/lib
> python -m pydoc -w station
Then, open path/to/lib/station.html in a browser.
Refs:
https://docs.python.org/2.7/library/pydoc.html
http://bytes.com/topic/python/answers/436285-how-use-pydoc

Author: Perry Roth-Johnson
Last updated: April 14, 2014

"""


import os
import numpy as np
import matplotlib.pyplot as plt
import transformation as tf
import coordinates as cd
import airfoil as airf
reload(airf)
import structure as struc
reload(struc)
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
from shapely.affinity import translate
from descartes import PolygonPatch
# the descartes module translates shapely objects into matplotlib objects
# from operator import attrgetter
# helps to sort lists of objects by their attributes
# ref: https://wiki.python.org/moin/HowTo/Sorting#Operator_Module_Functions
from math import isnan


class _Station:
    """Define a station for a wind turbine blade.

    The _Station base class is not intended for use.
    Use MonoplaneStation or BiplaneStation instead.

    This class also contains methods to split the airfoil curve into separate
    segments for each structural part: spar caps, shear webs, etc.

    Usage
    -----
    import pandas as pd
    import station as stn
    df = pd.read_csv('Sandia_blade.csv', index_col=0)
    s5 = stn._Station(df.ix[5])  # import station 5

    """
    logfile_name = 'station.log'
    number_of_stations = 0
    def __init__(self, stn_series, blade_path):
        """Create a new blade station.

        Parameters
        ---------
        stn_series : pandas.Series, properties for this station
        blade_path: string, the local target directory for storing blade data

        Attributes
        ----------
        .station_num : int, the blade station number
        .station_path : str, local directory for storing this station's data
        .logf : file handle, log file for all Station operations
        .coords
            .x1 : float, spanwise coordinate (meters)
            .x2 : float, edgewise coordinate (meters)
            .x3 : float, flapwise coordinate (meters)
        .airfoil
            .name : str, the airfoil name
            .filename : str, the airfoil filename
            .path : str, the airfoil path
            .pitch_axis : float, the chord fraction distance between the
                leading edge and the pitch axis (unitless)
            .chord : float, the chord length (meters)
            .twist : float, the twist about the x1 axis (degrees)
            .coords : numpy array, the airfoil coordinates (scaled by the
                .chord and .pitch_axis dimensions)
                [note: created by .read_coords()]
            .LE_index : int, the index of .coords for the leading edge of this
                airfoil
            .suction : numpy array, the (scaled) airfoil coordinates of the
                suction surface
            .pressure : numpy array, the (scaled) airfoil coordinates of the
                pressure surface
            .polygon : shapely.Polygon, a closed polygon representation of the
                entire airfoil surface
        .structure
            .root_buildup
                .base=np.nan
                .height : float, the root buildup height (meters)
                .polygon : Shapely Polygon obj
                    .exterior.coords : Shapely coords obj, exterior coords
                    .interiors[0].coords : Shapely coords obj, interior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                        ['coordinates'][1] : tuple of tuples, interior coords
            .spar_cap
                .base : float, the spar cap base (meters)
                .height : float, the spar cap height (meters)
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .polygon_lower : Shapely Polygon obj, lower spar cap
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_upper : Shapely Polygon obj, upper spar cap
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .shear_web_1
                .base : float, the shear web #1 total base (meters)
                .base_biax : float, the shear web #1 base for biax (meters)
                .base_foam : float, the shear web #1 base for foam (meters)
                .x2 : float, dist from pitch axis to edge of SW #1 (meters)
                .height=np.nan
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .cs_coords : numpy array, the 4 coordinates for the corners of
                    the cross-section of the shear web at this station, ordered
                    as [lower left, lower right, upper right, upper left]
                .polygon_left_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_foam : Shapely Polygon obj, foam region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_right_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .shear_web_2
                .base : float, the shear web #2 total base (meters)
                .base_biax : float, the shear web #2 base for biax (meters)
                .base_foam : float, the shear web #2 base for foam (meters)
                .x2 : float, dist from pitch axis to edge of SW #2 (meters)
                .height=np.nan
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .cs_coords : numpy array, the 4 coordinates for the corners of
                    the cross-section of the shear web at this station, ordered
                    as [lower left, lower right, upper right, upper left]
                .polygon_left_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_foam : Shapely Polygon obj, foam region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_right_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .shear_web_3
                .base : float, the shear web #3 total base (meters)
                .base_biax : float, the shear web #3 base for biax (meters)
                .base_foam : float, the shear web #3 base for foam (meters)
                .x2 : float, dist from pitch axis to edge of SW #3 (meters)
                .height=np.nan
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .cs_coords : numpy array, the 4 coordinates for the corners of
                    the cross-section of the shear web at this station, ordered
                    as [lower left, lower right, upper right, upper left]
                .polygon_left_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_foam : Shapely Polygon obj, foam region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_right_biax : Shapely Polygon obj, left biax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .TE_reinforcement
                .base : float, the trailing edge reinforcement base (meters)
                .height_uniax : float, the TE reinf height for uniax (meters)
                .height_foam : float, the TE reinf height for foam (meters)
                .height : float, the TE reinf total height (meters)
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .polygon_uniax : Shapely Polygon obj, uniax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_foam : Shapely Polygon obj, foam region
                    (if foam region doesn't exist, .polygon_foam=None)
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .LE_panel
                .base=np.nan
                .height : the leading edge panel height (meters)
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .polygon : Shapely Polygon obj
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .aft_panel_1
                .base=np.nan
                .height : the aft panel (fwd of SW#3) height (meters)
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .polygon_lower : Shapely Polygon obj, lower aft panel #1
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_upper : Shapely Polygon obj, upper aft panel #1
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .aft_panel_2
                .base=np.nan
                .height : the aft panel (aft of SW#3) height (meters)
                .left : float, the left edge -- chordwise coord (meters)
                .right : float, the right edge -- chordwise coord (meters)
                .polygon_lower : Shapely Polygon obj, lower aft panel #2
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                .polygon_upper : Shapely Polygon obj, upper aft panel #2
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
            .internal_surface
                .base=np.nan
                .height_triax : float, the internal surface height for triax (meters)
                .height_resin : float, the internal surface height for resin (meters)
                .height : float, the internal surface total height (meters)
            .external_surface
                .base=np.nan
                .height_triax : float, the external surface height for triax (meters)
                .height_gelcoat : float, the external surface height for gelcoat (meters)
                .height : float, the external surface total height (meters)
                .polygon_triax : Shapely Polygon obj, triax region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                        ['coordinates'][1] : tuple of tuples, interior coords
                .polygon_gelcoat : Shapely Polygon obj, gelcoat region
                    .exterior.coords : Shapely coords obj, exterior coords
                    .__geo_interface__ : dict of coordinates and type
                        ['coordinates'][0] : tuple of tuples, exterior coords
                        ['coordinates'][1] : tuple of tuples, interior coords

        Methods
        -------
        .__del__() : delete this station
        .create_plot() : create a plot for this station
        .show_plot() : show the plot
        .save_plot() : save the plot in the station path as a PNG file
        .write_all_part_polygons() : write the coordinates of all structural
            parts to `station_path`
        .find_SW_cs_coords() : find the corners of the each shear web
            cross-section
        .find_part_edges() : find the edges of each structural part
        .plot_polygon() : plot a polygon in a matplotlib figure
        .plot_parts() : plots the structural parts in this blade station
        .structure
            .<Part>
                .exists() : bool, check if a Part exists at this station
        .airfoil
            .read_coords() : Read the airfoil coordinates and scale wrt the
                airfoil dims. Create a new attribute, <Station>.airfoil.coords,
                a numpy array of airfoil coordinates.
            .scale_coords()
            .rotate_coords()
            .split_at_LE_and_TE() : Split the airfoil curve into suction and
                pressure segments. Create new attributes: 
                <Station>.airfoil.LE_index, <Station>.airfoil.suction, and 
                <Station>.airfoil.pressure
            .plot_coords() : plot the airfoil coordinates of this station

        Usage
        -----    
        _Station(b._df.ix[5], 'sandia_blade')
        # this creates station #5 of the Sandia blade
        # _df is a pandas DataFrame containing properties of all blade stations
        # _df.ix[5] gets the Series object for station #5 from DataFrame _df
        # Note: _Stations are usually not created directly. New _Stations are
        # usually created by the _Blade class.

        """
        _Station.number_of_stations += 1
        self.station_num = _Station.number_of_stations
        self.station_path = os.path.join(blade_path, 'stn{0:02d}'.format(self.station_num))
        try:
            os.mkdir(self.station_path)
        except WindowsError:
            print "[WindowsError] The station path '{0}' already exists!".format(os.path.split(self.station_path)[-1])
        self.logf = open(_Station.logfile_name, "a")
        self.logf.write("............(Created blade station #{0})............\n".format(self.station_num))
        print " Created blade station #{0}".format(self.station_num)
        self.coords = cd.Coordinates(stn_series['x1'], 
                                  stn_series['x2'], 
                                  stn_series['x3'])
        self.logf.write("****** COORDINATES ******\n")
        self.logf.write(str(self.coords) + '\n')
        self.logf.flush()
        self.logf.close()

    def __del__(self):
        _Station.number_of_stations = _Station.number_of_stations - 1
        print " Station deleted, and now _Station.number_of_stations = {0}".format(_Station.number_of_stations)

    def create_plot(self, legend_flag=False):
        """Create a plot for this station.

        Returns handles to the figure and its axes: (fig, axes)

        Several settings are applied ---------
        Title : Station #[num], [airfoil name], [num]% span
        Aspect ratio : equal
        Grid : on
        x-label : x2 [meters]
        y-label : x3 [meters]

        """
        af = self.airfoil
        fig, axes = plt.subplots()
        axes.set_title("Station #{0}, {1}, {2}% span".format(self.station_num, af.name, self.coords.x1))
        axes.set_aspect('equal')
        axes.grid('on')
        axes.set_xlabel('x2 [meters]')
        axes.set_ylabel('x3 [meters]')
        if legend_flag:
            axes.legend(loc='center')
        return (fig, axes)

    def show_plot(self):
        """Show the plot."""
        plt.show()

    def save_plot(self, fig):
        """Save the plot in the station path as a PNG file: stnXX.png"""
        fname = os.path.join(self.station_path, 'stn{0:02d}.png'.format(self.station_num))
        fig.savefig(fname)

    def plot_polygon(self, polygon, axes, face_color=(1,0,0),
        edge_color=(1,0,0), alpha=0.5):
        """Plot a polygon in a matplotlib figure."""
        patch = PolygonPatch(polygon, fc=face_color, ec=edge_color, alpha=alpha)
        axes.add_patch(patch)


class MonoplaneStation(_Station):
    """Define a monoplane station for a wind turbine blade."""
    def __init__(self, stn_series, blade_path, parent_blade):
        """Create a new biplane station for a biplane blade."""
        _Station.__init__(self, stn_series, blade_path)
        self.parent_blade = parent_blade
        self.type = 'monoplane'
        self.airfoil = airf.MonoplaneAirfoil(
            name=stn_series['airfoil'],
            filename=stn_series['airfoil']+'.txt',
            chord=stn_series['chord'],
            pitch_axis=stn_series['pitch axis'],
            twist=stn_series['twist'],
            has_sharp_TE=stn_series['has sharp TE'],
            parent_station=self)
        self.logf = open(_Station.logfile_name, "a")
        self.logf.write("****** AIRFOIL AND CHORD PROPERTIES ******\n")
        self.logf.write(str(self.airfoil) + '\n')
        self.structure = struc.MonoplaneStructure(
            h_RB=stn_series['root buildup height'],
            b_SC=stn_series['spar cap base'],
            h_SC=stn_series['spar cap height'],
            b_SW1_biax=stn_series['shear web 1 base biax'],
            b_SW1_foam=stn_series['shear web 1 base foam'],
            x2_SW1=stn_series['shear web 1 x2'],
            b_SW2_biax=stn_series['shear web 2 base biax'],
            b_SW2_foam=stn_series['shear web 2 base foam'],
            x2_SW2=stn_series['shear web 2 x2'],
            b_SW3_biax=stn_series['shear web 3 base biax'],
            b_SW3_foam=stn_series['shear web 3 base foam'],
            x2_SW3=stn_series['shear web 3 x2'],
            b_TE_reinf=stn_series['TE reinf base'],
            h_TE_reinf_uniax=stn_series['TE reinf height uniax'],
            h_TE_reinf_foam=stn_series['TE reinf height foam'],
            h_LE_panel=stn_series['LE panel height'],
            h_aft_panel_1=stn_series['aft panel 1 height'],
            h_aft_panel_2=stn_series['aft panel 2 height'],
            h_int_surf_1_triax=stn_series['internal surface 1 height triax'],
            h_int_surf_1_resin=stn_series['internal surface 1 height resin'],
            h_int_surf_2_triax=stn_series['internal surface 2 height triax'],
            h_int_surf_2_resin=stn_series['internal surface 2 height resin'],
            h_int_surf_3_triax=stn_series['internal surface 3 height triax'],
            h_int_surf_3_resin=stn_series['internal surface 3 height resin'],
            h_int_surf_4_triax=stn_series['internal surface 4 height triax'],
            h_int_surf_4_resin=stn_series['internal surface 4 height resin'],
            h_ext_surf_triax=stn_series['external surface height triax'],
            h_ext_surf_gelcoat=stn_series['external surface height gelcoat'],
            parent_station=self)
        self.logf.write("****** LAMINATE SCHEDULE ******\n")
        self.logf.write(str(self.structure) + '\n')
        self.logf.flush()
        self.logf.close()

    def find_SW_cs_coords(self):
        """Find the corners of each shear web cross-section.

        Saves cross-section coordinates (in meters) as the '.cs_coords' 
        attribute (a numpy array) within each ShearWeb instance.

        """
        st = self.structure
        af = self.airfoil
        if st.shear_web_1.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.shear_web_1.left)
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.shear_web_1.right)
            st.shear_web_1.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.shear_web_2.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.shear_web_2.left)
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.shear_web_2.right)
            st.shear_web_2.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.shear_web_3.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.shear_web_3.left)
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.shear_web_3.right)
            st.shear_web_3.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)

    def find_part_edges(self):
        """Find the edges of each structural part in this monoplane station.

        Saves coordinates (in meters) as '.left' and '.right' attributes
        (floats) within each Part instance (OOP style).

        """
        st = self.structure
        af = self.airfoil
        if st.spar_cap.exists():
            st.spar_cap.left = -st.spar_cap.base/2.0
            st.spar_cap.right = st.spar_cap.base/2.0
        if st.TE_reinforcement.exists():
            st.TE_reinforcement.left = -af.pitch_axis*af.chord+af.chord-st.TE_reinforcement.base
            st.TE_reinforcement.right = -af.pitch_axis*af.chord+af.chord
        if st.shear_web_1.exists():
            st.shear_web_1.right = st.shear_web_1.x2
            st.shear_web_1.left = st.shear_web_1.x2-st.shear_web_1.base
        if st.shear_web_2.exists():
            st.shear_web_2.left = st.shear_web_2.x2
            st.shear_web_2.right = st.shear_web_2.x2+st.shear_web_2.base
        if st.shear_web_3.exists():
            st.shear_web_3.left = st.shear_web_3.x2
            st.shear_web_3.right = st.shear_web_3.x2+st.shear_web_3.base
        if st.LE_panel.exists():
            st.LE_panel.left = -af.pitch_axis*af.chord
            if st.shear_web_1.exists():
                st.LE_panel.right = st.shear_web_1.left
            elif st.spar_cap.exists():
                st.LE_panel.right = st.spar_cap.left
            else:
                st.LE_panel.right = np.nan
                raise Warning("'LE panel, right' is undefined for station #{0}".format(self.station_num))
        if st.aft_panel_1.exists():
            if st.shear_web_2.exists():
                st.aft_panel_1.left = st.shear_web_2.right
            elif st.spar_cap.exists():
                st.aft_panel_1.left = st.spar_cap.right
            else:
                st.aft_panel_1.left = np.nan
                raise Warning("'aft panel 1, left' is undefined for station #{0}".format(self.station_num))
            if st.shear_web_3.exists():
                st.aft_panel_1.right = st.shear_web_3.left
            elif st.TE_reinforcement.exists():
                st.aft_panel_1.right = st.TE_reinforcement.left
            else:
                st.aft_panel_1.right = np.nan
                raise Warning("'aft panel 1, right' is undefined for station #{0}".format(self.station_num))
        if st.aft_panel_2.exists():
            if st.shear_web_3.exists():
                st.aft_panel_2.left = st.shear_web_3.right
            else:
                st.aft_panel_2.left = np.nan
                raise Warning("'aft panel 2, left' is undefined for station #{0}".format(self.station_num))
            if st.TE_reinforcement.exists():
                st.aft_panel_2.right = st.TE_reinforcement.left
            else:
                st.aft_panel_2.right = np.nan
                raise Warning("'aft panel 2, right' is undefined for station #{0}".format(self.station_num))

    def plot_parts(self, ax=None):
        """Plots the structural parts in this blade station."""
        if ax is None:
            fig, ax = plt.subplots()
        st = self.structure
        ax.set_title("Station #{0}, {1}, {2}% span".format(self.station_num, self.airfoil.name, self.coords.x1))
        ax.set_aspect('equal')
        ax.grid('on')
        ax.set_xlabel('x2 [meters]')
        ax.set_ylabel('x3 [meters]')
        self.plot_polygon(self.airfoil.polygon, ax,
            face_color='None', edge_color='#999999', alpha=0.8)
        (minx, miny, maxx, maxy) = self.airfoil.polygon.bounds
        ax.set_xlim([minx*1.2,maxx*1.2])
        ax.set_ylim([miny*1.2,maxy*1.2])
        try:
            if st.external_surface.exists():
                self.plot_polygon(
                    st.external_surface.layer['gelcoat'].polygon, ax,
                    st.external_surface.layer['gelcoat'].face_color,
                    st.external_surface.layer['gelcoat'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.external_surface.layer['triax'].polygon, ax,
                    st.external_surface.layer['triax'].face_color,
                    st.external_surface.layer['triax'].edge_color,
                    alpha=0.8)
            if st.root_buildup.exists():
                self.plot_polygon(
                    st.root_buildup.layer['triax'].polygon, ax,
                    st.root_buildup.layer['triax'].face_color,
                    st.root_buildup.layer['triax'].edge_color,
                    alpha=0.8)
            if st.spar_cap.exists():
                self.plot_polygon(
                    st.spar_cap.layer['lower'].polygon, ax,
                    st.spar_cap.layer['lower'].face_color,
                    st.spar_cap.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.spar_cap.layer['upper'].polygon, ax,
                    st.spar_cap.layer['upper'].face_color,
                    st.spar_cap.layer['upper'].edge_color,
                    alpha=0.8)
            if st.aft_panel_1.exists():
                self.plot_polygon(
                    st.aft_panel_1.layer['lower'].polygon, ax,
                    st.aft_panel_1.layer['lower'].face_color,
                    st.aft_panel_1.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.aft_panel_1.layer['upper'].polygon, ax,
                    st.aft_panel_1.layer['upper'].face_color,
                    st.aft_panel_1.layer['upper'].edge_color,
                    alpha=0.8)
            if st.aft_panel_2.exists():
                self.plot_polygon(
                    st.aft_panel_2.layer['lower'].polygon, ax,
                    st.aft_panel_2.layer['lower'].face_color,
                    st.aft_panel_2.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.aft_panel_2.layer['upper'].polygon, ax,
                    st.aft_panel_2.layer['upper'].face_color,
                    st.aft_panel_2.layer['upper'].edge_color,
                    alpha=0.8)
            if st.LE_panel.exists():
                self.plot_polygon(
                    st.LE_panel.layer['foam'].polygon, ax,
                    st.LE_panel.layer['foam'].face_color,
                    st.LE_panel.layer['foam'].edge_color,
                    alpha=0.8)
            if st.shear_web_1.exists():
                self.plot_polygon(
                    st.shear_web_1.layer['biax, left'].polygon, ax,
                    st.shear_web_1.layer['biax, left'].face_color,
                    st.shear_web_1.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_1.layer['foam'].polygon, ax,
                    st.shear_web_1.layer['foam'].face_color,
                    st.shear_web_1.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_1.layer['biax, right'].polygon, ax,
                    st.shear_web_1.layer['biax, right'].face_color,
                    st.shear_web_1.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.shear_web_2.exists():
                self.plot_polygon(
                    st.shear_web_2.layer['biax, left'].polygon, ax,
                    st.shear_web_2.layer['biax, left'].face_color,
                    st.shear_web_2.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_2.layer['foam'].polygon, ax,
                    st.shear_web_2.layer['foam'].face_color,
                    st.shear_web_2.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_2.layer['biax, right'].polygon, ax,
                    st.shear_web_2.layer['biax, right'].face_color,
                    st.shear_web_2.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.shear_web_3.exists():
                self.plot_polygon(
                    st.shear_web_3.layer['biax, left'].polygon, ax,
                    st.shear_web_3.layer['biax, left'].face_color,
                    st.shear_web_3.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_3.layer['foam'].polygon, ax,
                    st.shear_web_3.layer['foam'].face_color,
                    st.shear_web_3.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.shear_web_3.layer['biax, right'].polygon, ax,
                    st.shear_web_3.layer['biax, right'].face_color,
                    st.shear_web_3.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.TE_reinforcement.exists():
                self.plot_polygon(
                    st.TE_reinforcement.layer['uniax'].polygon, ax,
                    st.TE_reinforcement.layer['uniax'].face_color,
                    st.TE_reinforcement.layer['uniax'].edge_color,
                    alpha=0.8)
                try:
                    self.plot_polygon(
                        st.TE_reinforcement.layer['foam'].polygon, ax,
                        st.TE_reinforcement.layer['foam'].face_color,
                        st.TE_reinforcement.layer['foam'].edge_color,
                        alpha=0.8)
                except KeyError:  # foam region doesn't exist
                    pass
            if st.internal_surface_1.exists():
                self.plot_polygon(
                    st.internal_surface_1.layer['triax'].polygon, ax,
                    st.internal_surface_1.layer['triax'].face_color,
                    st.internal_surface_1.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.internal_surface_1.layer['resin'].polygon, ax,
                    st.internal_surface_1.layer['resin'].face_color,
                    st.internal_surface_1.layer['resin'].edge_color,
                    alpha=0.8)
            if st.internal_surface_2.exists():
                self.plot_polygon(
                    st.internal_surface_2.layer['triax'].polygon, ax,
                    st.internal_surface_2.layer['triax'].face_color,
                    st.internal_surface_2.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.internal_surface_2.layer['resin'].polygon, ax,
                    st.internal_surface_2.layer['resin'].face_color,
                    st.internal_surface_2.layer['resin'].edge_color,
                    alpha=0.8)
            if st.internal_surface_3.exists():
                self.plot_polygon(
                    st.internal_surface_3.layer['triax'].polygon, ax,
                    st.internal_surface_3.layer['triax'].face_color,
                    st.internal_surface_3.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.internal_surface_3.layer['resin'].polygon, ax,
                    st.internal_surface_3.layer['resin'].face_color,
                    st.internal_surface_3.layer['resin'].edge_color,
                    alpha=0.8)
            if st.internal_surface_4.exists():
                self.plot_polygon(
                    st.internal_surface_4.layer['triax'].polygon, ax,
                    st.internal_surface_4.layer['triax'].face_color,
                    st.internal_surface_4.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.internal_surface_4.layer['resin'].polygon, ax,
                    st.internal_surface_4.layer['resin'].face_color,
                    st.internal_surface_4.layer['resin'].edge_color,
                    alpha=0.8)
        except AttributeError:
            raise AttributeError("Part instance has no attribute 'polygon'.\n  Try running <station>.structure.create_all_layers() first.")
        plt.show()


class BiplaneStation(_Station):
    """Define a biplane station for a biplane wind turbine blade."""
    def __init__(self, stn_series, blade_path, parent_blade):
        """Create a new biplane station for a biplane blade."""
        _Station.__init__(self, stn_series, blade_path)
        self.parent_blade = parent_blade
        self.type = 'biplane'
        self.airfoil = airf.BiplaneAirfoil(
            name=stn_series['airfoil']+'_biplane',
            name_L=stn_series['airfoil'],
            filename_L=stn_series['airfoil']+'.txt',
            chord_L=stn_series['chord'],
            SW_ref_pt_L=stn_series['lower SW ref pt fraction'],
            name_U=stn_series['airfoil upper'],
            filename_U=stn_series['airfoil upper']+'.txt',
            chord_U=stn_series['chord'],
            SW_ref_pt_U=stn_series['upper SW ref pt fraction'],
            pitch_axis=stn_series['pitch axis'],
            twist=stn_series['twist'],
            gap_to_chord_ratio=stn_series['gap-to-chord ratio'],
            gap_fraction=stn_series['gap fraction'],
            stagger_to_chord_ratio=stn_series['stagger-to-chord ratio'],
            parent_station=self)
        self.logf = open(_Station.logfile_name, "a")
        self.logf.write("****** AIRFOIL AND CHORD PROPERTIES ******\n")
        self.logf.write(str(self.airfoil) + '\n')
        self.structure = struc.BiplaneStructure(
            h_RB=stn_series['root buildup height'],
            b_SC=stn_series['spar cap base'],
            h_SC=stn_series['spar cap height'],
            b_SW1_biax=stn_series['shear web 1 base biax'],
            b_SW1_foam=stn_series['shear web 1 base foam'],
            x2_SW1=stn_series['shear web 1 x2'],
            b_SW2_biax=stn_series['shear web 2 base biax'],
            b_SW2_foam=stn_series['shear web 2 base foam'],
            x2_SW2=stn_series['shear web 2 x2'],
            b_SW3_biax=stn_series['shear web 3 base biax'],
            b_SW3_foam=stn_series['shear web 3 base foam'],
            x2_SW3=stn_series['shear web 3 x2'],
            b_TE_reinf=stn_series['TE reinf base'],
            h_TE_reinf_uniax=stn_series['TE reinf height uniax'],
            h_TE_reinf_foam=stn_series['TE reinf height foam'],
            h_LE_panel=stn_series['LE panel height'],
            h_aft_panel_1=stn_series['aft panel 1 height'],
            h_aft_panel_2=stn_series['aft panel 2 height'],
            h_int_surf_1_triax=stn_series['internal surface 1 height triax'],
            h_int_surf_1_resin=stn_series['internal surface 1 height resin'],
            h_int_surf_2_triax=stn_series['internal surface 2 height triax'],
            h_int_surf_2_resin=stn_series['internal surface 2 height resin'],
            h_int_surf_3_triax=stn_series['internal surface 3 height triax'],
            h_int_surf_3_resin=stn_series['internal surface 3 height resin'],
            h_int_surf_4_triax=stn_series['internal surface 4 height triax'],
            h_int_surf_4_resin=stn_series['internal surface 4 height resin'],
            h_ext_surf_triax=stn_series['external surface height triax'],
            h_ext_surf_gelcoat=stn_series['external surface height gelcoat'],
            h_RB_u=stn_series['root buildup height upper'],
            b_SC_u=stn_series['spar cap base upper'],
            h_SC_u=stn_series['spar cap height upper'],
            b_SW1_biax_u=stn_series['shear web 1 base biax upper'],
            b_SW1_foam_u=stn_series['shear web 1 base foam upper'],
            x2_SW1_u=stn_series['shear web 1 x2 upper'],
            b_SW2_biax_u=stn_series['shear web 2 base biax upper'],
            b_SW2_foam_u=stn_series['shear web 2 base foam upper'],
            x2_SW2_u=stn_series['shear web 2 x2 upper'],
            b_SW3_biax_u=stn_series['shear web 3 base biax upper'],
            b_SW3_foam_u=stn_series['shear web 3 base foam upper'],
            x2_SW3_u=stn_series['shear web 3 x2 upper'],
            b_TE_reinf_u=stn_series['TE reinf base upper'],
            h_TE_reinf_uniax_u=stn_series['TE reinf height uniax upper'],
            h_TE_reinf_foam_u=stn_series['TE reinf height foam upper'],
            h_LE_panel_u=stn_series['LE panel height upper'],
            h_aft_panel_1_u=stn_series['aft panel 1 height upper'],
            h_aft_panel_2_u=stn_series['aft panel 2 height upper'],
            h_int_surf_1_triax_u=stn_series['internal surface 1 height triax upper'],
            h_int_surf_1_resin_u=stn_series['internal surface 1 height resin upper'],
            h_int_surf_2_triax_u=stn_series['internal surface 2 height triax upper'],
            h_int_surf_2_resin_u=stn_series['internal surface 2 height resin upper'],
            h_int_surf_3_triax_u=stn_series['internal surface 3 height triax upper'],
            h_int_surf_3_resin_u=stn_series['internal surface 3 height resin upper'],
            h_int_surf_4_triax_u=stn_series['internal surface 4 height triax upper'],
            h_int_surf_4_resin_u=stn_series['internal surface 4 height resin upper'],
            h_ext_surf_triax_u=stn_series['external surface height triax upper'],
            h_ext_surf_gelcoat_u=stn_series['external surface height gelcoat upper'],
            parent_station=self)
        self.logf.write("****** LAMINATE SCHEDULE ******\n")
        self.logf.write(str(self.structure) + '\n')
        self.logf.flush()
        self.logf.close()

    def find_part_edges(self):
        """Find the edges of each structural part in this biplane station.

        Saves coordinates (in meters) as '.left' and '.right' attributes
        (floats) within each Part instance (OOP style).

        """
        st = self.structure
        af = self.airfoil
        # upper airfoil
        upper_refpt = -(af.pitch_axis*af.total_chord)+(af.upper_SW_ref_pt_fraction*af.upper_chord)
        if st.upper_spar_cap.exists():
            st.upper_spar_cap.left = upper_refpt - st.upper_spar_cap.base/2.0
            st.upper_spar_cap.right = upper_refpt + st.upper_spar_cap.base/2.0
        if st.upper_TE_reinforcement.exists():
            st.upper_TE_reinforcement.left = upper_refpt - af.upper_SW_ref_pt_fraction*af.upper_chord+af.upper_chord-st.upper_TE_reinforcement.base
            st.upper_TE_reinforcement.right = upper_refpt - af.upper_SW_ref_pt_fraction*af.upper_chord+af.upper_chord
        if st.upper_shear_web_1.exists():
            st.upper_shear_web_1.right = upper_refpt + st.upper_shear_web_1.x2
            st.upper_shear_web_1.left = upper_refpt + st.upper_shear_web_1.x2-st.upper_shear_web_1.base
        if st.upper_shear_web_2.exists():
            st.upper_shear_web_2.left = upper_refpt + st.upper_shear_web_2.x2
            st.upper_shear_web_2.right = upper_refpt + st.upper_shear_web_2.x2+st.upper_shear_web_2.base
        if st.upper_shear_web_3.exists():
            st.upper_shear_web_3.left = upper_refpt + st.upper_shear_web_3.x2
            st.upper_shear_web_3.right = upper_refpt + st.upper_shear_web_3.x2+st.upper_shear_web_3.base
        if st.upper_LE_panel.exists():
            st.upper_LE_panel.left = upper_refpt - af.upper_SW_ref_pt_fraction*af.upper_chord
            if st.upper_shear_web_1.exists():
                st.upper_LE_panel.right = st.upper_shear_web_1.left
            elif st.upper_spar_cap.exists():
                st.upper_LE_panel.right = st.upper_spar_cap.left
            else:
                st.upper_LE_panel.right = np.nan
                raise Warning("'LE panel, right' is undefined for station #{0}".format(self.station_num))
        if st.upper_aft_panel_1.exists():
            if st.upper_shear_web_2.exists():
                st.upper_aft_panel_1.left = st.upper_shear_web_2.right
            elif st.upper_spar_cap.exists():
                st.upper_aft_panel_1.left = st.upper_spar_cap.right
            else:
                st.upper_aft_panel_1.left = np.nan
                raise Warning("'aft panel 1, left' is undefined for station #{0}".format(self.station_num))
            if st.upper_shear_web_3.exists():
                st.upper_aft_panel_1.right = st.upper_shear_web_3.left
            elif st.upper_TE_reinforcement.exists():
                st.upper_aft_panel_1.right = st.upper_TE_reinforcement.left
            else:
                st.upper_aft_panel_1.right = np.nan
                raise Warning("'aft panel 1, right' is undefined for station #{0}".format(self.station_num))
        if st.upper_aft_panel_2.exists():
            if st.upper_shear_web_3.exists():
                st.upper_aft_panel_2.left = st.upper_shear_web_3.right
            else:
                st.upper_aft_panel_2.left = np.nan
                raise Warning("'aft panel 2, left' is undefined for station #{0}".format(self.station_num))
            if st.upper_TE_reinforcement.exists():
                st.upper_aft_panel_2.right = st.upper_TE_reinforcement.left
            else:
                st.upper_aft_panel_2.right = np.nan
                raise Warning("'aft panel 2, right' is undefined for station #{0}".format(self.station_num))
        # lower airfoil
        lower_refpt = -(af.pitch_axis*af.total_chord)+(af.stagger)+(af.lower_SW_ref_pt_fraction*af.lower_chord)
        if st.lower_spar_cap.exists():
            st.lower_spar_cap.left = lower_refpt - st.lower_spar_cap.base/2.0
            st.lower_spar_cap.right = lower_refpt + st.lower_spar_cap.base/2.0
        if st.lower_TE_reinforcement.exists():
            st.lower_TE_reinforcement.left = lower_refpt - af.lower_SW_ref_pt_fraction*af.lower_chord+af.lower_chord-st.lower_TE_reinforcement.base
            st.lower_TE_reinforcement.right = lower_refpt - af.lower_SW_ref_pt_fraction*af.lower_chord+af.lower_chord
        if st.lower_shear_web_1.exists():
            st.lower_shear_web_1.right = lower_refpt + st.lower_shear_web_1.x2
            st.lower_shear_web_1.left = lower_refpt + st.lower_shear_web_1.x2-st.lower_shear_web_1.base
        if st.lower_shear_web_2.exists():
            st.lower_shear_web_2.left = lower_refpt + st.lower_shear_web_2.x2
            st.lower_shear_web_2.right = lower_refpt + st.lower_shear_web_2.x2+st.lower_shear_web_2.base
        if st.lower_shear_web_3.exists():
            st.lower_shear_web_3.left = lower_refpt + st.lower_shear_web_3.x2
            st.lower_shear_web_3.right = lower_refpt + st.lower_shear_web_3.x2+st.lower_shear_web_3.base
        if st.lower_LE_panel.exists():
            st.lower_LE_panel.left = lower_refpt - af.lower_SW_ref_pt_fraction*af.lower_chord
            if st.lower_shear_web_1.exists():
                st.lower_LE_panel.right = st.lower_shear_web_1.left
            elif st.lower_spar_cap.exists():
                st.lower_LE_panel.right = st.lower_spar_cap.left
            else:
                st.lower_LE_panel.right = np.nan
                raise Warning("'LE panel, right' is undefined for station #{0}".format(self.station_num))
        if st.lower_aft_panel_1.exists():
            if st.lower_shear_web_2.exists():
                st.lower_aft_panel_1.left = st.lower_shear_web_2.right
            elif st.lower_spar_cap.exists():
                st.lower_aft_panel_1.left = st.lower_spar_cap.right
            else:
                st.lower_aft_panel_1.left = np.nan
                raise Warning("'aft panel 1, left' is undefined for station #{0}".format(self.station_num))
            if st.lower_shear_web_3.exists():
                st.lower_aft_panel_1.right = st.lower_shear_web_3.left
            elif st.lower_TE_reinforcement.exists():
                st.lower_aft_panel_1.right = st.lower_TE_reinforcement.left
            else:
                st.lower_aft_panel_1.right = np.nan
                raise Warning("'aft panel 1, right' is undefined for station #{0}".format(self.station_num))
        if st.lower_aft_panel_2.exists():
            if st.lower_shear_web_3.exists():
                st.lower_aft_panel_2.left = st.lower_shear_web_3.right
            else:
                st.lower_aft_panel_2.left = np.nan
                raise Warning("'aft panel 2, left' is undefined for station #{0}".format(self.station_num))
            if st.lower_TE_reinforcement.exists():
                st.lower_aft_panel_2.right = st.lower_TE_reinforcement.left
            else:
                st.lower_aft_panel_2.right = np.nan
                raise Warning("'aft panel 2, right' is undefined for station #{0}".format(self.station_num))

    def find_SW_cs_coords(self):
        """Find the corners of each shear web cross-section.

        Saves cross-section coordinates (in meters) as the '.cs_coords' 
        attribute (a numpy array) within each ShearWeb instance.

        """
        st = self.structure
        af = self.airfoil
        # lower airfoil
        if st.lower_shear_web_1.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.lower_shear_web_1.left, airfoil='lower')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.lower_shear_web_1.right, airfoil='lower')
            st.lower_shear_web_1.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.lower_shear_web_2.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.lower_shear_web_2.left, airfoil='lower')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.lower_shear_web_2.right, airfoil='lower')
            st.lower_shear_web_2.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.lower_shear_web_3.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.lower_shear_web_3.left, airfoil='lower')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.lower_shear_web_3.right, airfoil='lower')
            st.lower_shear_web_3.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        # upper airfoil
        if st.upper_shear_web_1.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.upper_shear_web_1.left, airfoil='upper')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.upper_shear_web_1.right, airfoil='upper')
            st.upper_shear_web_1.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.upper_shear_web_2.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.upper_shear_web_2.left, airfoil='upper')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.upper_shear_web_2.right, airfoil='upper')
            st.upper_shear_web_2.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)
        if st.upper_shear_web_3.exists():
            ((x1,y1),(x4,y4)) = af.find_part_edge_coords(st.upper_shear_web_3.left, airfoil='upper')
            ((x2,y2),(x3,y3)) = af.find_part_edge_coords(st.upper_shear_web_3.right, airfoil='upper')
            st.upper_shear_web_3.cs_coords = np.array([[x1,y1],  # 1 (lower left)
                                                 [x2,y2],  # 2 (lower right)
                                                 [x3,y3],  # 3 (upper right)
                                                 [x4,y4]]) # 4 (upper left)

    def plot_parts(self, ax=None):
        """Plots the structural parts in this blade station."""
        if ax is None:
            fig, ax = plt.subplots()
        st = self.structure
        ax.set_title("Station #{0}, {1}, {2}% span".format(self.station_num, self.airfoil.name, self.coords.x1))
        ax.set_aspect('equal')
        ax.grid('on')
        ax.set_xlabel('x2 [meters]')
        ax.set_ylabel('x3 [meters]')
        if self.type == 'monoplane':
            self.plot_polygon(self.airfoil.polygon, ax,
                face_color='None', edge_color='#999999', alpha=0.8)
            (minx, miny, maxx, maxy) = self.airfoil.polygon.bounds
        elif self.type == 'biplane':
            self.plot_polygon(self.airfoil.lower_polygon, ax,
                face_color='None', edge_color='#999999', alpha=0.8)
            self.plot_polygon(self.airfoil.upper_polygon, ax,
                face_color='None', edge_color='#999999', alpha=0.8)
            (lminx, lminy, lmaxx, lmaxy) = self.airfoil.lower_polygon.bounds
            (uminx, uminy, umaxx, umaxy) = self.airfoil.upper_polygon.bounds
            (minx, miny, maxx, maxy) = (
                min(lminx,uminx),
                min(lminy,uminy),
                max(lmaxx,umaxx),
                max(lmaxy,umaxy)
                )
        else:
            raise ValueError("<station>.type must be 'monoplane' or 'biplane'")
        ax.set_xlim([minx*1.2,maxx*1.2])
        ax.set_ylim([miny*1.2,maxy*1.2])
        try:
            # lower airfoil ---------------------------------------------------
            if st.lower_external_surface.exists():
                self.plot_polygon(
                    st.lower_external_surface.layer['gelcoat'].polygon, ax,
                    st.lower_external_surface.layer['gelcoat'].face_color,
                    st.lower_external_surface.layer['gelcoat'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_external_surface.layer['triax'].polygon, ax,
                    st.lower_external_surface.layer['triax'].face_color,
                    st.lower_external_surface.layer['triax'].edge_color,
                    alpha=0.8)
            if st.lower_root_buildup.exists():
                self.plot_polygon(
                    st.lower_root_buildup.layer['triax'].polygon, ax,
                    st.lower_root_buildup.layer['triax'].face_color,
                    st.lower_root_buildup.layer['triax'].edge_color,
                    alpha=0.8)
            if st.lower_spar_cap.exists():
                self.plot_polygon(
                    st.lower_spar_cap.layer['lower'].polygon, ax,
                    st.lower_spar_cap.layer['lower'].face_color,
                    st.lower_spar_cap.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_spar_cap.layer['upper'].polygon, ax,
                    st.lower_spar_cap.layer['upper'].face_color,
                    st.lower_spar_cap.layer['upper'].edge_color,
                    alpha=0.8)
            if st.lower_aft_panel_1.exists():
                self.plot_polygon(
                    st.lower_aft_panel_1.layer['lower'].polygon, ax,
                    st.lower_aft_panel_1.layer['lower'].face_color,
                    st.lower_aft_panel_1.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_aft_panel_1.layer['upper'].polygon, ax,
                    st.lower_aft_panel_1.layer['upper'].face_color,
                    st.lower_aft_panel_1.layer['upper'].edge_color,
                    alpha=0.8)
            if st.lower_aft_panel_2.exists():
                self.plot_polygon(
                    st.lower_aft_panel_2.layer['lower'].polygon, ax,
                    st.lower_aft_panel_2.layer['lower'].face_color,
                    st.lower_aft_panel_2.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_aft_panel_2.layer['upper'].polygon, ax,
                    st.lower_aft_panel_2.layer['upper'].face_color,
                    st.lower_aft_panel_2.layer['upper'].edge_color,
                    alpha=0.8)
            if st.lower_LE_panel.exists():
                self.plot_polygon(
                    st.lower_LE_panel.layer['foam'].polygon, ax,
                    st.lower_LE_panel.layer['foam'].face_color,
                    st.lower_LE_panel.layer['foam'].edge_color,
                    alpha=0.8)
            if st.lower_shear_web_1.exists():
                self.plot_polygon(
                    st.lower_shear_web_1.layer['biax, left'].polygon, ax,
                    st.lower_shear_web_1.layer['biax, left'].face_color,
                    st.lower_shear_web_1.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_1.layer['foam'].polygon, ax,
                    st.lower_shear_web_1.layer['foam'].face_color,
                    st.lower_shear_web_1.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_1.layer['biax, right'].polygon, ax,
                    st.lower_shear_web_1.layer['biax, right'].face_color,
                    st.lower_shear_web_1.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.lower_shear_web_2.exists():
                self.plot_polygon(
                    st.lower_shear_web_2.layer['biax, left'].polygon, ax,
                    st.lower_shear_web_2.layer['biax, left'].face_color,
                    st.lower_shear_web_2.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_2.layer['foam'].polygon, ax,
                    st.lower_shear_web_2.layer['foam'].face_color,
                    st.lower_shear_web_2.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_2.layer['biax, right'].polygon, ax,
                    st.lower_shear_web_2.layer['biax, right'].face_color,
                    st.lower_shear_web_2.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.lower_shear_web_3.exists():
                self.plot_polygon(
                    st.lower_shear_web_3.layer['biax, left'].polygon, ax,
                    st.lower_shear_web_3.layer['biax, left'].face_color,
                    st.lower_shear_web_3.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_3.layer['foam'].polygon, ax,
                    st.lower_shear_web_3.layer['foam'].face_color,
                    st.lower_shear_web_3.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_shear_web_3.layer['biax, right'].polygon, ax,
                    st.lower_shear_web_3.layer['biax, right'].face_color,
                    st.lower_shear_web_3.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.lower_TE_reinforcement.exists():
                self.plot_polygon(
                    st.lower_TE_reinforcement.layer['uniax'].polygon, ax,
                    st.lower_TE_reinforcement.layer['uniax'].face_color,
                    st.lower_TE_reinforcement.layer['uniax'].edge_color,
                    alpha=0.8)
                try:
                    self.plot_polygon(
                        st.lower_TE_reinforcement.layer['foam'].polygon, ax,
                        st.lower_TE_reinforcement.layer['foam'].face_color,
                        st.lower_TE_reinforcement.layer['foam'].edge_color,
                        alpha=0.8)
                except KeyError:  # foam region doesn't exist
                    pass
            if st.lower_internal_surface_1.exists():
                self.plot_polygon(
                    st.lower_internal_surface_1.layer['triax'].polygon, ax,
                    st.lower_internal_surface_1.layer['triax'].face_color,
                    st.lower_internal_surface_1.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_internal_surface_1.layer['resin'].polygon, ax,
                    st.lower_internal_surface_1.layer['resin'].face_color,
                    st.lower_internal_surface_1.layer['resin'].edge_color,
                    alpha=0.8)
            if st.lower_internal_surface_2.exists():
                self.plot_polygon(
                    st.lower_internal_surface_2.layer['triax'].polygon, ax,
                    st.lower_internal_surface_2.layer['triax'].face_color,
                    st.lower_internal_surface_2.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_internal_surface_2.layer['resin'].polygon, ax,
                    st.lower_internal_surface_2.layer['resin'].face_color,
                    st.lower_internal_surface_2.layer['resin'].edge_color,
                    alpha=0.8)
            if st.lower_internal_surface_3.exists():
                self.plot_polygon(
                    st.lower_internal_surface_3.layer['triax'].polygon, ax,
                    st.lower_internal_surface_3.layer['triax'].face_color,
                    st.lower_internal_surface_3.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_internal_surface_3.layer['resin'].polygon, ax,
                    st.lower_internal_surface_3.layer['resin'].face_color,
                    st.lower_internal_surface_3.layer['resin'].edge_color,
                    alpha=0.8)
            if st.lower_internal_surface_4.exists():
                self.plot_polygon(
                    st.lower_internal_surface_4.layer['triax'].polygon, ax,
                    st.lower_internal_surface_4.layer['triax'].face_color,
                    st.lower_internal_surface_4.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.lower_internal_surface_4.layer['resin'].polygon, ax,
                    st.lower_internal_surface_4.layer['resin'].face_color,
                    st.lower_internal_surface_4.layer['resin'].edge_color,
                    alpha=0.8)
            # upper airfoil ---------------------------------------------------
            if st.upper_external_surface.exists():
                self.plot_polygon(
                    st.upper_external_surface.layer['gelcoat'].polygon, ax,
                    st.upper_external_surface.layer['gelcoat'].face_color,
                    st.upper_external_surface.layer['gelcoat'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_external_surface.layer['triax'].polygon, ax,
                    st.upper_external_surface.layer['triax'].face_color,
                    st.upper_external_surface.layer['triax'].edge_color,
                    alpha=0.8)
            if st.upper_root_buildup.exists():
                self.plot_polygon(
                    st.upper_root_buildup.layer['triax'].polygon, ax,
                    st.upper_root_buildup.layer['triax'].face_color,
                    st.upper_root_buildup.layer['triax'].edge_color,
                    alpha=0.8)
            if st.upper_spar_cap.exists():
                self.plot_polygon(
                    st.upper_spar_cap.layer['lower'].polygon, ax,
                    st.upper_spar_cap.layer['lower'].face_color,
                    st.upper_spar_cap.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_spar_cap.layer['upper'].polygon, ax,
                    st.upper_spar_cap.layer['upper'].face_color,
                    st.upper_spar_cap.layer['upper'].edge_color,
                    alpha=0.8)
            if st.upper_aft_panel_1.exists():
                self.plot_polygon(
                    st.upper_aft_panel_1.layer['lower'].polygon, ax,
                    st.upper_aft_panel_1.layer['lower'].face_color,
                    st.upper_aft_panel_1.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_aft_panel_1.layer['upper'].polygon, ax,
                    st.upper_aft_panel_1.layer['upper'].face_color,
                    st.upper_aft_panel_1.layer['upper'].edge_color,
                    alpha=0.8)
            if st.upper_aft_panel_2.exists():
                self.plot_polygon(
                    st.upper_aft_panel_2.layer['lower'].polygon, ax,
                    st.upper_aft_panel_2.layer['lower'].face_color,
                    st.upper_aft_panel_2.layer['lower'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_aft_panel_2.layer['upper'].polygon, ax,
                    st.upper_aft_panel_2.layer['upper'].face_color,
                    st.upper_aft_panel_2.layer['upper'].edge_color,
                    alpha=0.8)
            if st.upper_LE_panel.exists():
                self.plot_polygon(
                    st.upper_LE_panel.layer['foam'].polygon, ax,
                    st.upper_LE_panel.layer['foam'].face_color,
                    st.upper_LE_panel.layer['foam'].edge_color,
                    alpha=0.8)
            if st.upper_shear_web_1.exists():
                self.plot_polygon(
                    st.upper_shear_web_1.layer['biax, left'].polygon, ax,
                    st.upper_shear_web_1.layer['biax, left'].face_color,
                    st.upper_shear_web_1.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_1.layer['foam'].polygon, ax,
                    st.upper_shear_web_1.layer['foam'].face_color,
                    st.upper_shear_web_1.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_1.layer['biax, right'].polygon, ax,
                    st.upper_shear_web_1.layer['biax, right'].face_color,
                    st.upper_shear_web_1.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.upper_shear_web_2.exists():
                self.plot_polygon(
                    st.upper_shear_web_2.layer['biax, left'].polygon, ax,
                    st.upper_shear_web_2.layer['biax, left'].face_color,
                    st.upper_shear_web_2.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_2.layer['foam'].polygon, ax,
                    st.upper_shear_web_2.layer['foam'].face_color,
                    st.upper_shear_web_2.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_2.layer['biax, right'].polygon, ax,
                    st.upper_shear_web_2.layer['biax, right'].face_color,
                    st.upper_shear_web_2.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.upper_shear_web_3.exists():
                self.plot_polygon(
                    st.upper_shear_web_3.layer['biax, left'].polygon, ax,
                    st.upper_shear_web_3.layer['biax, left'].face_color,
                    st.upper_shear_web_3.layer['biax, left'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_3.layer['foam'].polygon, ax,
                    st.upper_shear_web_3.layer['foam'].face_color,
                    st.upper_shear_web_3.layer['foam'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_shear_web_3.layer['biax, right'].polygon, ax,
                    st.upper_shear_web_3.layer['biax, right'].face_color,
                    st.upper_shear_web_3.layer['biax, right'].edge_color,
                    alpha=0.8)
            if st.upper_TE_reinforcement.exists():
                self.plot_polygon(
                    st.upper_TE_reinforcement.layer['uniax'].polygon, ax,
                    st.upper_TE_reinforcement.layer['uniax'].face_color,
                    st.upper_TE_reinforcement.layer['uniax'].edge_color,
                    alpha=0.8)
                try:
                    self.plot_polygon(
                        st.upper_TE_reinforcement.layer['foam'].polygon, ax,
                        st.upper_TE_reinforcement.layer['foam'].face_color,
                        st.upper_TE_reinforcement.layer['foam'].edge_color,
                        alpha=0.8)
                except KeyError:  # foam region doesn't exist
                    pass
            if st.upper_internal_surface_1.exists():
                self.plot_polygon(
                    st.upper_internal_surface_1.layer['triax'].polygon, ax,
                    st.upper_internal_surface_1.layer['triax'].face_color,
                    st.upper_internal_surface_1.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_internal_surface_1.layer['resin'].polygon, ax,
                    st.upper_internal_surface_1.layer['resin'].face_color,
                    st.upper_internal_surface_1.layer['resin'].edge_color,
                    alpha=0.8)
            if st.upper_internal_surface_2.exists():
                self.plot_polygon(
                    st.upper_internal_surface_2.layer['triax'].polygon, ax,
                    st.upper_internal_surface_2.layer['triax'].face_color,
                    st.upper_internal_surface_2.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_internal_surface_2.layer['resin'].polygon, ax,
                    st.upper_internal_surface_2.layer['resin'].face_color,
                    st.upper_internal_surface_2.layer['resin'].edge_color,
                    alpha=0.8)
            if st.upper_internal_surface_3.exists():
                self.plot_polygon(
                    st.upper_internal_surface_3.layer['triax'].polygon, ax,
                    st.upper_internal_surface_3.layer['triax'].face_color,
                    st.upper_internal_surface_3.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_internal_surface_3.layer['resin'].polygon, ax,
                    st.upper_internal_surface_3.layer['resin'].face_color,
                    st.upper_internal_surface_3.layer['resin'].edge_color,
                    alpha=0.8)
            if st.upper_internal_surface_4.exists():
                self.plot_polygon(
                    st.upper_internal_surface_4.layer['triax'].polygon, ax,
                    st.upper_internal_surface_4.layer['triax'].face_color,
                    st.upper_internal_surface_4.layer['triax'].edge_color,
                    alpha=0.8)
                self.plot_polygon(
                    st.upper_internal_surface_4.layer['resin'].polygon, ax,
                    st.upper_internal_surface_4.layer['resin'].face_color,
                    st.upper_internal_surface_4.layer['resin'].edge_color,
                    alpha=0.8)
        except AttributeError:
            raise AttributeError("Part instance has no attribute 'polygon'.\n  Try running <station>.structure.create_all_layers() first.")
        plt.show()

    def plot_parts_offset(self, airfoil_to_plot='lower', x3_offset=None, 
        ax=None):
        """Plots the structural parts in one airfoil of this station.

        Parts are shifted by the x3_offset distance.

        """
        if ax is None:
            fig, ax = plt.subplots()
        st = self.structure
        fmt1 = "Station #{0}, {1}, {2}% span\n"
        fmt2 = "lower airfoil in local beam coordinate system (x3-offset = {3:+.4f})"
        fmt = fmt1 + fmt2
        ax.set_title(fmt.format(self.station_num, self.airfoil.name, 
            self.coords.x1, x3_offset))
        ax.set_aspect('equal')
        ax.grid('on')
        ax.set_xlabel('x2 [meters]')
        ax.set_ylabel('x3 [meters]')
        if self.type == 'monoplane':
            raise Warning("This method is only meant for biplane stations.")
        elif self.type == 'biplane':
            if airfoil_to_plot == 'lower':
                lp2 = translate(self.airfoil.lower_polygon, yoff=x3_offset)
                (minx, miny, maxx, maxy) = lp2.bounds
            elif airfoil_to_plot == 'upper':
                raise NotImplementedError("`airfoil_to_plot`='upper' is not implemented! Try `airfoil_to_plot`='lower' instead.")
            else:
                raise ValueError("`airfoil_to_plot` keyword must be 'lower'")
        else:
            raise ValueError("<station>.type must be 'monoplane' or 'biplane'")
        ax.set_xlim([minx*1.2,maxx*1.2])
        ax.set_ylim([miny*1.2,maxy*1.2])
        if airfoil_to_plot == 'lower':
            for layer in self.structure._list_of_lower_layers:
                new_polygon = translate(layer.polygon, yoff=x3_offset)
                self.plot_polygon(new_polygon, ax, layer.face_color, 
                    layer.edge_color, alpha=0.8)
        elif airfoil_to_plot == 'upper':
            raise NotImplementedError("`airfoil_to_plot`='upper' is not implemented! Try `airfoil_to_plot`='lower' instead.")
        else:
            raise ValueError("`airfoil_to_plot` keyword must be 'lower'")
