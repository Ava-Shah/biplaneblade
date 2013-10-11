"""A module for organizing geometrical data for a blade station.

Author: Perry Roth-Johnson
Last updated: October 11, 2013

"""


import os
import numpy as np
import matplotlib.pyplot as plt
import transformation as tf
# reload(tf)
import coordinates as cd
# reload(cd)
import airfoil as airf
reload(airf)
import structure as struc
reload(struc)
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
from descartes import PolygonPatch
# the descartes module translates shapely objects into matplotlib objects
from operator import attrgetter
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
        .create_polygons() : find the polygon representations of each
            structural part
        .get_interior_loop() : get the interior loop for the desired internal
            surface
        .write_all_part_polygons() : write the coordinates of all structural
            parts to `station_path`
        .find_SW_cs_coords() : find the corners of the cross-sections for
            each structural part (NOTE: only shear webs implemented so far)
        .find_part_edges() : find the edges of each structural part
        .plot_part_edges() : plot color block for each structural part region
        .plot_polygon() : plot a polygon in a matplotlib figure
        .get_profile() : returns a polygon for the desired profile
        .erode_part_thickness() : returns a polygon of the outer profile,
            eroded by the part height
        .cut_out_part_interior() : returns a polygon of `inner_profile` cut out
            of `outer_profile`
        .part_bounding_box() : returns a polygon of the bounding box that
            contains the part
        .SW_bounding_boxes() : returns three polygons of bounding boxes that
            contain the biax and foam regions of the shear web
        .extract_external_surface() : extract the external surface from the
            blade definition
        .get_gelcoat_and_triax_regions_of_ext_surf() : returns dict of gelcoat
            and triax regions of external surface
        .extract_SW() : extract the shear web from the blade definition
        .extract_TE_reinforcement() : extract the TE reinforcement from the
            blade definition
        .get_foam_and_uniax_regions_of_TE_reinf() : returns dict of foam and
            uniax regions of the TE reinforcement
        .cut_out_part() : returns a dict of polygons after cutting out the
            desired part. (NOTE: this is different from the other method,
            `.cut_out_part_interior()`.)
        .get_outer_profile_name() : determine the name of the outer profile
        .extract_part() : extract the polygon for a part from the blade
            definition
        .merge_all_parts() : merges all the structural parts in this station
            into one polygon
        .plot_parts() : plots the structural parts in this blade station
        .cross_section_area() : calculate the total cross-section area for this
            station
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


class MonoplaneStation(_Station):
    """Define a monoplane station for a wind turbine blade."""
    def __init__(self, stn_series, blade_path):
        """Create a new biplane station for a biplane blade."""
        _Station.__init__(self, stn_series, blade_path)
        self.type = 'monoplane'
        self.airfoil = airf.MonoplaneAirfoil(
            name=stn_series['airfoil'],
            filename=stn_series['airfoil']+'.txt',
            chord=stn_series['chord'],
            pitch_axis=stn_series['pitch axis'],
            twist=stn_series['twist'])
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
            h_ext_surf_gelcoat=stn_series['external surface height gelcoat'])
        self.logf.write("****** LAMINATE SCHEDULE ******\n")
        self.logf.write(str(self.structure) + '\n')
        self.logf.flush()
        self.logf.close()

    def create_polygons(self):
        """Find the polygon representations of each structural part."""
        st = self.structure
        af = self.airfoil
        af.create_polygon()
        if st.external_surface.exists():
            # # gelcoat region
            # op_gelcoat = af.polygon  # outer profile is the airfoil profile
            # ip_gelcoat = op_gelcoat.buffer(-st.external_surface.height_gelcoat)
            # st.external_surface.polygon_gelcoat = op_gelcoat.difference(ip_gelcoat)
            # assert st.external_surface.polygon_gelcoat.geom_type == 'Polygon'
            # # triax region
            # op_triax = ip_gelcoat
            # ip_triax = op_triax.buffer(-st.external_surface.height_triax)
            # st.external_surface.polygon_triax = op_triax.difference(ip_triax)
            # assert st.external_surface.polygon_triax.geom_type == 'Polygon'
            d = self.extract_part('external surface')
            st.external_surface.polygon_gelcoat = d['gelcoat region']
            st.external_surface.polygon_triax = d['triax region']
        if st.root_buildup.exists():
            d = self.extract_part('root buildup')
            st.root_buildup.polygon = d['single part']
        if st.spar_cap.exists():
            d = self.extract_part('spar cap')
            st.spar_cap.polygon_lower = d['lower part']
            st.spar_cap.polygon_upper = d['upper part']
        if st.aft_panel_1.exists():
            d = self.extract_part('aft panel 1')
            st.aft_panel_1.polygon_lower = d['lower part']
            st.aft_panel_1.polygon_upper = d['upper part']
        if st.aft_panel_2.exists():
            d = self.extract_part('aft panel 2')
            st.aft_panel_2.polygon_lower = d['lower part']
            st.aft_panel_2.polygon_upper = d['upper part']
        if st.LE_panel.exists():
            d = self.extract_part('LE panel')
            st.LE_panel.polygon = d['single part']
        if st.shear_web_1.exists():
            d = self.extract_part('shear web 1')
            st.shear_web_1.polygon_left_biax = d['left biax region']
            st.shear_web_1.polygon_foam = d['foam region']
            st.shear_web_1.polygon_right_biax = d['right biax region']
        if st.shear_web_2.exists():
            d = self.extract_part('shear web 2')
            st.shear_web_2.polygon_left_biax = d['left biax region']
            st.shear_web_2.polygon_foam = d['foam region']
            st.shear_web_2.polygon_right_biax = d['right biax region']
        if st.shear_web_3.exists():
            d = self.extract_part('shear web 3')
            st.shear_web_3.polygon_left_biax = d['left biax region']
            st.shear_web_3.polygon_foam = d['foam region']
            st.shear_web_3.polygon_right_biax = d['right biax region']
        if st.TE_reinforcement.exists():
            d = self.extract_part('TE reinforcement')
            st.TE_reinforcement.polygon_uniax = d['uniax region']
            st.TE_reinforcement.polygon_foam = d['foam region']
        if st.internal_surface_1.exists():
            # triax region
            op_triax = self.get_interior_loop(1)
            ip_triax = op_triax.buffer(-st.internal_surface_1.height_triax)
            st.internal_surface_1.polygon_triax = op_triax.difference(ip_triax)
            assert st.internal_surface_1.polygon_triax.geom_type == 'Polygon'
            # resin region
            op_resin = ip_triax
            ip_resin = op_resin.buffer(-st.internal_surface_1.height_resin)
            st.internal_surface_1.polygon_resin = op_resin.difference(ip_resin)
            assert st.internal_surface_1.polygon_resin.geom_type == 'Polygon'
        if st.internal_surface_2.exists():
            op_triax = self.get_interior_loop(2)
            ip_triax = op_triax.buffer(-st.internal_surface_2.height_triax)
            st.internal_surface_2.polygon_triax = op_triax.difference(ip_triax)
            assert st.internal_surface_2.polygon_triax.geom_type == 'Polygon'
            # resin region
            op_resin = ip_triax
            ip_resin = op_resin.buffer(-st.internal_surface_2.height_resin)
            st.internal_surface_2.polygon_resin = op_resin.difference(ip_resin)
            assert st.internal_surface_2.polygon_resin.geom_type == 'Polygon'
        if st.internal_surface_3.exists():
            op_triax = self.get_interior_loop(3)
            ip_triax = op_triax.buffer(-st.internal_surface_3.height_triax)
            st.internal_surface_3.polygon_triax = op_triax.difference(ip_triax)
            assert st.internal_surface_3.polygon_triax.geom_type == 'Polygon'
            # resin region
            op_resin = ip_triax
            ip_resin = op_resin.buffer(-st.internal_surface_3.height_resin)
            st.internal_surface_3.polygon_resin = op_resin.difference(ip_resin)
            assert st.internal_surface_3.polygon_resin.geom_type == 'Polygon'
        if st.internal_surface_4.exists():
            op_triax = self.get_interior_loop(4)
            ip_triax = op_triax.buffer(-st.internal_surface_4.height_triax)
            st.internal_surface_4.polygon_triax = op_triax.difference(ip_triax)
            assert st.internal_surface_4.polygon_triax.geom_type == 'Polygon'
            op_resin = ip_triax
            ip_resin = op_resin.buffer(-st.internal_surface_4.height_resin)
            st.internal_surface_4.polygon_resin = op_resin.difference(ip_resin)
            assert st.internal_surface_4.polygon_resin.geom_type == 'Polygon'

    def extract_part(self, part_name):
        """Extract the polygon for a part from the blade definition.

        Parameters
        ----------
        part_name : str, the name of the structural part. Options include:
            'spar cap', 'shear web 1', 'shear web 2', 'shear web 3',
            'aft panel 1', 'aft panel 2', 'TE reinforcement', 'LE panel',
            'root buildup', or 'external surface'

        """
        st = self.structure
        # 1. determine the name of the outer profile (op_name)
        op_name = self.get_outer_profile_name(part_name)
        # 2. access the desired structural part
        SW_flag = False  # shear web flag
        TE_flag = False  # trailing edge reinforcement flag
        ES_flag = False  # external surface flag
        if part_name == 'root buildup':
            p = st.root_buildup
        elif part_name == 'spar cap':
            p = st.spar_cap
        elif part_name == 'aft panel 1':
            p = st.aft_panel_1
        elif part_name == 'aft panel 2':
            p = st.aft_panel_2
        elif part_name == 'LE panel':
            p = st.LE_panel
        elif part_name == 'shear web 1':
            p = st.shear_web_1
            SW_flag = True
        elif part_name == 'shear web 2':
            p = st.shear_web_2
            SW_flag = True
        elif part_name == 'shear web 3':
            p = st.shear_web_3
            SW_flag = True
        elif part_name == 'TE reinforcement':
            p = st.TE_reinforcement
            TE_flag = True
        elif part_name == 'internal surface':
            raise NotImplementedError("Use the function `extract_internal_surface` instead.")
        elif part_name == 'external surface':
            p = st.external_surface
            ES_flag = True
        else:
            raise ValueError("""The value for `part_name` was not recognized. Options include:
    'spar cap'
    'shear web 1', 'shear web 2', 'shear web 3',
    'aft panel 1', 'aft panel 2',
    'TE reinforcement',
    'LE panel',
    'root buildup',
    'internal surface',
    'external surface'""")
        # 3. get outer profile
        op = self.get_profile(profile_name=op_name)
        if SW_flag:
            # use a special extraction algorithm for shear webs
            dict_of_parts = self.extract_SW(op, p)
        elif TE_flag:
            # use a special extraction algorithm for the TE reinforcement
            dict_of_parts = self.extract_TE_reinforcement(op, p)
        elif ES_flag:
            # use a special extraction algorithm for the external surface
            dict_of_parts = self.extract_external_surface(op, p)
        else:
            # use the normal extraction algorithm for all other parts
            # 4. erode the outer profile by the part thickness
            ip = self.erode_part_thickness(part=p, outer_profile=op)
            # 5. cut out the part interior from the outer profile
            ac = self.cut_out_part_interior(inner_profile=ip, outer_profile=op)
            # 6. draw a bounding box at the part edges
            bb = self.part_bounding_box(part=p)
            # 7. cut out the structural part
            dict_of_parts = self.cut_out_part(ac, bb)
        return dict_of_parts

    def get_outer_profile_name(self, part_name):
        """Determine the name of the outer profile."""
        st = self.structure
        # does external surface exist?
        if st.external_surface.exists():
            # yes, external surface exists
            # are we plotting external surface?
            if part_name == 'external surface':
                # yes, we're plotting external surface
                op_name = 'airfoil'
            else:
                # no, we're not plotting external surface
                # does root buildup exist?
                if st.root_buildup.exists():
                    # yes, root buildup exists
                    # are we plotting root buildup?
                    if part_name == 'root buildup':
                        # yes, we're plotting root buildup
                        op_name = '(airfoil) - (external surface)'
                    else:
                        # no, we're not plotting root buildup
                        op_name = '(airfoil) - (external surface) - (root buildup)'
                else:
                    # no, root buildup doesn't exist
                    op_name = '(airfoil) - (external surface)'
        else:
            # no, external surface doesn't exist
            # does root buildup exist?
            if st.root_buildup.exists():
                # yes, root buildup exists
                # are we plotting root buildup?
                if part_name == 'root buildup':
                    # yes, we're plotting root buildup
                    op_name = 'airfoil'
                else:
                    # no, we're not plotting root buildup
                    op_name = '(airfoil) - (root buildup)'
            else:
                # no, root buildup doesn't exist
                op_name = 'airfoil'
        return op_name

    def get_profile(self, profile_name, res=16):
        """Returns a polygon for the desired profile.

        Parameters:
        -----------
        profile_name : str, the name of the desired profile. Choose between:
            'airfoil'
              --> airfoil profile
            '(airfoil) - (root buildup)'
              --> airfoil profile - root buildup thickness
            '(airfoil) - (external surface)'
              --> airfoil profile - external surface thickness
            '(airfoil) - (external surface) - (root buildup)'
              --> airfoil profile - (external surface + root buildup) thickness
        res : int (default: 16), a resolution that determines the number of
            segments used to approximate a quarter circle around a point

        """
        st = self.structure
        af = self.airfoil
        if profile_name == 'airfoil':
            p = af.polygon
        elif profile_name == '(airfoil) - (root buildup)':
            p = af.polygon.buffer(-st.root_buildup.height,
                resolution=res)
        elif profile_name == '(airfoil) - (external surface)':
            p = af.polygon.buffer(-st.external_surface.height,
                resolution=res)
        elif profile_name == '(airfoil) - (external surface) - (root buildup)':
            p = af.polygon.buffer(-(st.external_surface.height + 
                st.root_buildup.height), resolution=res)
        else:
            raise NotImplementedError("That `profile_name` is not supported.")
        return p

    def extract_SW(self, op, p):
        """Extract the shear web from the blade definition.

        ***
        NOTE: this function should NOT be used directly, it should only be 
        called by <station>.extract_part(...)
        ***

        The shear web is split into three regions:
        (1) left biax region
        (2) foam region
        (3) right biax region

        Parameters
        ----------
        op : shapely.Polygon, the polygon representation of the desired outer
            profile
        p : <station>.structure.<part>, the structural part, where <part> = 
            'shear web 1', 'shear web 2', or 'shear web 3'
        
        """
        # 6. get bounding boxes for the biax and foam regions of the shear web
        (L_biax_bb, foam_bb, R_biax_bb) = self.SW_bounding_boxes(SW_part=p)
        # 7. cut out the structural part
        # we are extracting a shear web; just cut out the intersection
        # of the outer profile and the three bounding boxes
        left_biax = self.cut_out_part(op, L_biax_bb)['single part']
        foam = self.cut_out_part(op, foam_bb)['single part']
        right_biax = self.cut_out_part(op, R_biax_bb)['single part']
        dict_of_parts = {'left biax region' : left_biax,
            'foam region' : foam, 'right biax region' : right_biax}
        return dict_of_parts

    def SW_bounding_boxes(self, SW_part, y_boundary_buffer=1.2):
        """Returns three polygons of bounding boxes that contain the biax and foam regions of the shear web.

        The points of each bounding box are labeled from 1 to 4 as:

        4---3
        |   |
        1---2

        """
        (minx, miny, maxx, maxy) = self.airfoil.polygon.bounds
        # left biax bounding box
        pt1 = (SW_part.left, miny*y_boundary_buffer)
        pt2 = (SW_part.left+SW_part.base_biax, miny*y_boundary_buffer)
        pt3 = (SW_part.left+SW_part.base_biax, maxy*y_boundary_buffer)
        pt4 = (SW_part.left, maxy*y_boundary_buffer)
        left_biax_bb = Polygon([pt1, pt2, pt3, pt4])
        # foam bounding box
        pt1 = (SW_part.left+SW_part.base_biax, miny*y_boundary_buffer)
        pt2 = (SW_part.right-SW_part.base_biax, miny*y_boundary_buffer)
        pt3 = (SW_part.right-SW_part.base_biax, maxy*y_boundary_buffer)
        pt4 = (SW_part.left+SW_part.base_biax, maxy*y_boundary_buffer)
        foam_bb = Polygon([pt1, pt2, pt3, pt4])
        # right biax bounding box
        pt1 = (SW_part.right-SW_part.base_biax, miny*y_boundary_buffer)
        pt2 = (SW_part.right, miny*y_boundary_buffer)
        pt3 = (SW_part.right, maxy*y_boundary_buffer)
        pt4 = (SW_part.right-SW_part.base_biax, maxy*y_boundary_buffer)
        right_biax_bb = Polygon([pt1, pt2, pt3, pt4])
        return (left_biax_bb, foam_bb, right_biax_bb)

    def cut_out_part(self, airfoil_cutout, bounding_box):
        """Returns a dict of polygons after cutting out the desired part.

        The dict of polygons may contain either two items (e.g. an upper spar
        cap and a lower spar cap) or one item (e.g. a leading edge panel).

        Parts are obtained by finding the intersection of two polygons:
        `airfoil_cutout` and `bounding_box`.

        Parameters
        ----------
        airfoil_cutout : shapely.Polygon, the airfoil profile with the inner
            boundary of the structural part cut out
        bounding_box : shapely.Polygon, a bounding box that stretches from the
            left to right edge of the desired structural part

        """
        p4 = airfoil_cutout.intersection(bounding_box)
        # p4 may be a `MultiPolygon` that contains more than one polygon
        # (e.g. p4 contains the upper and lower spar caps)
        # if so, extract each polygon and convert them to separate patches
        # (otherwise, PolygonPatch will throw an error)
        dict_of_parts = {}
        try:
            if len(p4.geoms) == 2:
                dict_of_parts['lower part'] = p4.geoms[0]
                dict_of_parts['upper part'] = p4.geoms[1]
            else:
                raise NotImplementedError("After cutting out parts, more than 2 polygons were found.")
        except AttributeError:
            # p4 is just a `Polygon`, not a `MultiPolygon`, and p4 does not
            # have the attribute `geoms`.
            # (e.g. p4 is the LE panel)
            dict_of_parts['single part'] = p4
        return dict_of_parts

    def extract_TE_reinforcement(self, op, p):
        """Extract the TE reinforcement from the blade definition.

        ***
        NOTE: this function should NOT be used directly, it should only be 
        called by <station>.extract_part(...)
        ***

        The TE reinforcement is split into one or two regions:
        (1) uniax region
        (2) foam region (optional)

        Parameters
        ----------
        op : shapely.Polygon, the polygon representation of the desired outer
            profile
        p : <station>.structure.TE_reinforcement, the structural part for the
            TE reinforcement
        
        """
        # 4. erode the outer profile by the part thickness
        ip = self.erode_part_thickness(part=p, outer_profile=op)
        # 5. cut out the part interior from the outer profile
        ac = self.cut_out_part_interior(inner_profile=ip, outer_profile=op)
        # 6. draw a bounding box at the TE reinforcement edges
        bb = self.part_bounding_box(part=p)
        # 7. cut out the entire TE reinforcement
        e = self.cut_out_part(ac, bb)['single part']  # entire TE reinforcement
        # 8. extract the foam and uniax regions from the TE reinforcement
        dict_of_parts = self.get_foam_and_uniax_regions_of_TE_reinf(e)
        return dict_of_parts

    def erode_part_thickness(self, part, outer_profile, res=16):
        """Returns a polygon of the outer profile, eroded by the part height

        Parameters
        ----------
        part : <station>.structure.<part>, the object that represents a
            structural part at this station
        outer_profile : shapely.Polygon, the polygon that represents the
            desired outer profile
        res : int (default: 16), a resolution that determines the number of
            segments used to approximate a quarter circle around a point

        """
        return outer_profile.buffer(-part.height, resolution=res)

    def cut_out_part_interior(self, inner_profile, outer_profile):
        """Returns a polygon of `inner_profile` cut out of `outer_profile`."""
        return outer_profile.difference(inner_profile)

    def part_bounding_box(self, part, x_boundary_buffer=1.2, 
        y_boundary_buffer=1.2):
        """Returns a polygon of the bounding box that contains the part.

        The points of the bounding box are labeled from 1 to 4 as:

        4---3
        |   |
        1---2

        Parameters
        ----------
        part : <station>.structure.<part>, the object that represents a
            structural part at this station
        x_boundary_buffer : float (default: 1.2), factor to multiply with the
            minx and maxx bound of the airfoil polygon, to stretch the bounding
            box past the left and right edges of the airfoil polygon
        y_boundary_buffer : float (default: 1.2), factor to multiply with the
            miny and maxy bound of the airfoil polygon, to stretch the bounding
            box above and below the top and bottom edges of the airfoil polygon

        """
        (minx, miny, maxx, maxy) = self.airfoil.polygon.bounds
        if part.left is not None and part.right is not None:
            # if the part has values for the attributes `left` and `right`
            pt1 = (part.left, miny*y_boundary_buffer)
            pt2 = (part.right, miny*y_boundary_buffer)
            pt3 = (part.right, maxy*y_boundary_buffer)
            pt4 = (part.left, maxy*y_boundary_buffer)
        else:
            # if part.left=None and part.right=None, then just use
            # the airfoil bounds to form the bounding box
            # (e.g. the root buildup doesnt have left and right edges)
            pt1 = (minx*x_boundary_buffer, miny*y_boundary_buffer)
            pt2 = (maxx*x_boundary_buffer, miny*y_boundary_buffer)
            pt3 = (maxx*x_boundary_buffer, maxy*y_boundary_buffer)
            pt4 = (minx*x_boundary_buffer, maxy*y_boundary_buffer)
        bounding_box = Polygon([pt1, pt2, pt3, pt4])
        return bounding_box

    def get_foam_and_uniax_regions_of_TE_reinf(self, entire_region, axes=None,
        debug_plots=False, res=16):
        """Returns dict of foam and uniax regions of the TE reinforcement.

        Parameters
        ----------
        entire_region : ?
        axes : ?
        debug_plots : ?
        res : int (default: 16), a resolution that determines the number of
            segments used to approximate a quarter circle around a point

        """
        TE = self.structure.TE_reinforcement
        if isnan(TE.height_foam) and isnan(TE.height_uniax):
            uniax_region = None
            foam_region = None
        else:
            if isnan(TE.height_foam):
                uniax_region = entire_region
                foam_region = None
            elif isnan(TE.height_uniax):
                foam_region = entire_region
                uniax_region = None
            else:
                # split entire_region up into foam_region and uniax_region
                # 1. get polygons for outer profile (entire_region) and inner
                #    profile (external surface or root buildup, minus the uniax
                #    thickness)
                op = entire_region
                if self.structure.external_surface.exists():
                    if self.structure.root_buildup.exists():
                        ip = self.get_profile('(airfoil) - (external surface) - (root buildup)')
                        ip = ip.buffer(-TE.height_uniax, resolution=res)
                    else:
                        ip = self.get_profile('(airfoil) - (external surface)')
                        ip = ip.buffer(-TE.height_uniax, resolution=res)
                else:
                    if self.structure.root_buildup.exists():
                        ip = self.get_profile('(airfoil) - (root buildup)')
                        ip = ip.buffer(-TE.height_uniax, resolution=res)
                    else:
                        ip = self.get_profile('airfoil')
                        ip = ip.buffer(-TE.height_uniax, resolution=res)
                if debug_plots:
                    # plot the boundary of the outer_profile (entire TE)
                    self.plot_polygon(op, axes, face_color='#6699cc',
                        edge_color='#6699cc')
                    # plot the boundary of the inner profile (~foam region)
                    self.plot_polygon(ip, axes, face_color=(0,1,0),
                        edge_color=(0,1,0))
                # 2. intersection of op and ip is the foam region
                foam_region = op.intersection(ip)
                # 3. difference of ip from op is the uniax region
                uniax_region = op.difference(ip)
        d = {'uniax region': uniax_region, 'foam region': foam_region}
        return d

    def extract_external_surface(self, op, p):
        """Extract the external surface from the blade definition.

        ***
        NOTE: this function should NOT be used directly, it should only be
        called by <station>.extract_part(...)
        ***

        """
        # 4. erode the outer profile by the part thickness
        ip = self.erode_part_thickness(part=p, outer_profile=op)
        # 5. cut out the part interior from the outer profile
        e = self.cut_out_part_interior(inner_profile=ip, outer_profile=op)  # entire external surface
        dict_of_parts = self.get_gelcoat_and_triax_regions_of_ext_surf(e)
        return dict_of_parts

    def get_gelcoat_and_triax_regions_of_ext_surf(self, entire_region, res=16):
        """Returns dict of gelcoat and triax regions of external surface.

        Parameters
        ----------
        entire_region : object, polygon for the entire external surface?
        res : int (default: 16), a resolution that determines the number of
            segments used to approximate a quarter circle around a point

        """
        ES = self.structure.external_surface
        if isnan(ES.height_gelcoat) and isnan(ES.height_triax):
            triax_region = None
            gelcoat_region = None
        else:
            if isnan(ES.height_gelcoat):
                triax_region = entire_region
                gelcoat_region = None
            elif isnan(ES.height_triax):
                gelcoat_region = entire_region
                triax_region = None
            else:
                # split entire_region up into gelcoat_region and triax_region
                # 1. get polygons for outer profile (entire_region) and inner
                #    profile (airfoil, minus the gelcoat thickness)
                op = entire_region
                ip = self.get_profile('airfoil')
                ip = ip.buffer(-ES.height_gelcoat, resolution=res)
                # 2. intersection of op and ip is the triax region
                triax_region = op.intersection(ip)
                # 3. difference of ip from op is the gelcoat region
                gelcoat_region = op.difference(ip)
        d = {'triax region': triax_region, 'gelcoat region': gelcoat_region}
        return d

    def get_interior_loop(self, internal_surface_num, area_threshold=10e-06,
        debug_flag=False):
        """Get the interior loop for the desired internal surface.

        Returns a polygon object of the requested interior loop.

        Parameters
        ----------
        internal_surface_num : int, desired internal surface (1, 2, 3, or 4)
        area_threshold : float (default: 10e-06), threshold value to decide if
            an interior loop is valid (when the loop area > area_threshold)

        """
        p = self.merge_all_parts()
        # find interior loops that have a 'big' area (> area_threshold)
        good_loops = []
        for interior in p.interiors:
            a = Polygon(interior).area
            if a > area_threshold:
                good_loops.append(interior)
        if debug_flag:
            print "Station #{0} has {1} good interior loops.".format(
                self.station_num, len(good_loops))
        # sort loops by x-coordinate of their centroids, smallest to largest
        if len(good_loops) > 1:
            good_loops.sort(key=attrgetter('centroid.x'))
        # get the interior loop for the desired internal surface
        #   internal_surface_1 ==> internal_surface_num=1 ==> good_loops[0]
        #   internal_surface_2 ==> internal_surface_num=2 ==> good_loops[1]
        #   internal_surface_3 ==> internal_surface_num=3 ==> good_loops[2]
        #   internal_surface_4 ==> internal_surface_num=4 ==> good_loops[3]
        loop = Polygon(good_loops[internal_surface_num-1])
        return loop

    def merge_all_parts(self, plot_flag=False, merge_internal_surface=False):
        """Merges all the structural parts in this station into one polygon."""
        st = self.structure
        if plot_flag:
            fig, ax = plt.subplots()
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
        # gather all the parts
        list_of_parts = []
        if st.external_surface.exists():
            ES = st.external_surface.polygon_triax
            ES = ES.union(st.external_surface.polygon_gelcoat)
            list_of_parts.append(ES)
        if st.root_buildup.exists():
            RB = st.root_buildup.polygon
            list_of_parts.append(RB)
        if st.LE_panel.exists():
            LE = st.LE_panel.polygon
            list_of_parts.append(LE)
        if st.spar_cap.exists():
            sc_u = st.spar_cap.polygon_upper
            sc_l = st.spar_cap.polygon_lower
            list_of_parts.append(sc_u)
            list_of_parts.append(sc_l)
        if st.aft_panel_1.exists():
            aft1_u = st.aft_panel_1.polygon_upper
            aft1_l = st.aft_panel_1.polygon_lower
            list_of_parts.append(aft1_u)
            list_of_parts.append(aft1_l)
        if st.aft_panel_2.exists():
            aft2_u = st.aft_panel_2.polygon_upper
            aft2_l = st.aft_panel_2.polygon_lower
            list_of_parts.append(aft2_u)
            list_of_parts.append(aft2_l)
        if st.TE_reinforcement.exists():
            TE_uniax = st.TE_reinforcement.polygon_uniax
            try:
                TE_foam = st.TE_reinforcement.polygon_foam
                TE = TE_uniax.union(TE_foam)
            except ValueError:
                TE = TE_uniax
            list_of_parts.append(TE)
        if st.shear_web_1.exists():
            sw1 = st.shear_web_1.polygon_left_biax.union(st.shear_web_1.polygon_foam)
            sw1 = sw1.union(st.shear_web_1.polygon_right_biax)
            list_of_parts.append(sw1)
        if st.shear_web_2.exists():
            sw2 = st.shear_web_2.polygon_left_biax.union(st.shear_web_2.polygon_foam)
            sw2 = sw2.union(st.shear_web_2.polygon_right_biax)
            list_of_parts.append(sw2)
        if st.shear_web_3.exists():
            sw3 = st.shear_web_3.polygon_left_biax.union(st.shear_web_3.polygon_foam)
            sw3 = sw3.union(st.shear_web_3.polygon_right_biax)
            list_of_parts.append(sw3)
        if merge_internal_surface:
            # also merge the internal surface with the other structural parts
            if st.internal_surface_1.exists():
                IS1 = st.internal_surface_1.polygon_triax
                IS1 = IS1.union(st.internal_surface_1.polygon_resin)
                list_of_parts.append(IS1)
            if st.internal_surface_2.exists():
                IS2 = st.internal_surface_2.polygon_triax
                IS2 = IS2.union(st.internal_surface_2.polygon_resin)
                list_of_parts.append(IS2)
            if st.internal_surface_3.exists():
                IS3 = st.internal_surface_3.polygon_triax
                IS3 = IS3.union(st.internal_surface_3.polygon_resin)
                list_of_parts.append(IS3)
            if st.internal_surface_4.exists():
                IS4 = st.internal_surface_4.polygon_triax
                IS4 = IS4.union(st.internal_surface_4.polygon_resin)
                list_of_parts.append(IS4)
        # merge everything
        p = cascaded_union(list_of_parts)
        if plot_flag:
            # plot the merged polygon
            self.plot_polygon(p, ax, face_color='#4000FF', edge_color='#000000',
                alpha=0.8)  # face color is purple
            plt.show()
        return p

    def plot_polygon(self, polygon, axes, face_color=(1,0,0),
        edge_color=(1,0,0), alpha=0.5):
        """Plot a polygon in a matplotlib figure."""
        patch = PolygonPatch(polygon, fc=face_color, ec=edge_color, alpha=alpha)
        axes.add_patch(patch)

    def write_all_part_polygons(self):
        """Write the coordinates of all structural parts to `station_path`s."""
        st = self.structure
        if st.external_surface.exists():
            f = open(os.path.join(self.station_path,'external_surface.txt'), 'w')
            f.write("# triax region\n")
            f.write("# ------------\n")
            f.write(str(st.external_surface.polygon_triax.__geo_interface__))
            f.write("\n\n")
            f.write("# gelcoat region\n")
            f.write("# --------------\n")
            f.write(str(st.external_surface.polygon_gelcoat.__geo_interface__))
            f.close()
        if st.root_buildup.exists():
            f = open(os.path.join(self.station_path,'root_buildup.txt'), 'w')
            f.write(str(st.root_buildup.polygon.__geo_interface__))
            f.close()
        if st.spar_cap.exists():
            f = open(os.path.join(self.station_path,'spar_cap.txt'), 'w')
            f.write("# lower spar cap\n")
            f.write("# --------------\n")
            f.write(str(st.spar_cap.polygon_lower.__geo_interface__))
            f.write("\n\n")
            f.write("# upper spar cap\n")
            f.write("# --------------\n")
            f.write(str(st.spar_cap.polygon_upper.__geo_interface__))
            f.close()
        if st.aft_panel_1.exists():
            f = open(os.path.join(self.station_path,'aft_panel_1.txt'), 'w')
            f.write("# lower aft panel #1\n")
            f.write("# ------------------\n")
            f.write(str(st.aft_panel_1.polygon_lower.__geo_interface__))
            f.write("\n\n")
            f.write("# upper aft panel #1\n")
            f.write("# ------------------\n")
            f.write(str(st.aft_panel_1.polygon_upper.__geo_interface__))
            f.close()
        if st.aft_panel_2.exists():
            f = open(os.path.join(self.station_path,'aft_panel_2.txt'), 'w')
            f.write("# lower aft panel #2\n")
            f.write("# ------------------\n")
            f.write(str(st.aft_panel_2.polygon_lower.__geo_interface__))
            f.write("\n\n")
            f.write("# upper aft panel #2\n")
            f.write("# ------------------\n")
            f.write(str(st.aft_panel_2.polygon_upper.__geo_interface__))
            f.close()
        if st.LE_panel.exists():
            f = open(os.path.join(self.station_path,'LE_panel.txt'), 'w')
            f.write(str(st.LE_panel.polygon.__geo_interface__))
            f.close()
        if st.shear_web_1.exists():
            f = open(os.path.join(self.station_path,'shear_web_1.txt'), 'w')
            f.write("# left biax region\n")
            f.write("# ----------------\n")
            f.write(str(st.shear_web_1.polygon_left_biax.__geo_interface__))
            f.write("\n\n")
            f.write("# foam region\n")
            f.write("# -----------\n")
            f.write(str(st.shear_web_1.polygon_foam.__geo_interface__))
            f.write("\n\n")
            f.write("# right biax region\n")
            f.write("# -----------------\n")
            f.write(str(st.shear_web_1.polygon_right_biax.__geo_interface__))
            f.close()
        if st.shear_web_2.exists():
            f = open(os.path.join(self.station_path,'shear_web_2.txt'), 'w')
            f.write("# left biax region\n")
            f.write("# ----------------\n")
            f.write(str(st.shear_web_2.polygon_left_biax.__geo_interface__))
            f.write("\n\n")
            f.write("# foam region\n")
            f.write("# -----------\n")
            f.write(str(st.shear_web_2.polygon_foam.__geo_interface__))
            f.write("\n\n")
            f.write("# right biax region\n")
            f.write("# -----------------\n")
            f.write(str(st.shear_web_2.polygon_right_biax.__geo_interface__))
            f.close()
        if st.shear_web_3.exists():
            f = open(os.path.join(self.station_path,'shear_web_3.txt'), 'w')
            f.write("# left biax region\n")
            f.write("# ----------------\n")
            f.write(str(st.shear_web_3.polygon_left_biax.__geo_interface__))
            f.write("\n\n")
            f.write("# foam region\n")
            f.write("# -----------\n")
            f.write(str(st.shear_web_3.polygon_foam.__geo_interface__))
            f.write("\n\n")
            f.write("# right biax region\n")
            f.write("# -----------------\n")
            f.write(str(st.shear_web_3.polygon_right_biax.__geo_interface__))
            f.close()
        if st.TE_reinforcement.exists():
            f = open(os.path.join(self.station_path,'TE_reinforcement.txt'), 'w')
            f.write("# uniax region\n")
            f.write("# ------------\n")
            f.write(str(st.TE_reinforcement.polygon_uniax.__geo_interface__))
            f.write("\n\n")
            f.write("# foam region\n")
            f.write("# -----------\n")
            try:
                f.write(str(st.TE_reinforcement.polygon_foam.__geo_interface__))
            except:
                f.write("# ...the foam region doesn't exist!")
            f.close()
        if st.internal_surface_1.exists():
            f = open(os.path.join(self.station_path,'internal_surface_1.txt'), 'w')
            f.write("# triax region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_1.polygon_triax.__geo_interface__))
            f.write("\n\n")
            f.write("# resin region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_1.polygon_resin.__geo_interface__))
            f.close()
        if st.internal_surface_2.exists():
            f = open(os.path.join(self.station_path,'internal_surface_2.txt'), 'w')
            f.write("# triax region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_2.polygon_triax.__geo_interface__))
            f.write("\n\n")
            f.write("# resin region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_2.polygon_resin.__geo_interface__))
            f.close()
        if st.internal_surface_3.exists():
            f = open(os.path.join(self.station_path,'internal_surface_3.txt'), 'w')
            f.write("# triax region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_3.polygon_triax.__geo_interface__))
            f.write("\n\n")
            f.write("# resin region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_3.polygon_resin.__geo_interface__))
            f.close()
        if st.internal_surface_4.exists():
            f = open(os.path.join(self.station_path,'internal_surface_4.txt'), 'w')
            f.write("# triax region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_4.polygon_triax.__geo_interface__))
            f.write("\n\n")
            f.write("# resin region\n")
            f.write("--------------\n")
            f.write(str(st.internal_surface_4.polygon_resin.__geo_interface__))
            f.close()

    def find_SW_cs_coords(self):
        """Find the corners of the cross-sections for each shear web.

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

    def plot_part_edges(self, axes):
        """Plot color block for each structural part region.

        Each color block spans the plot from top to bottom.

        Uses coordinates saved as attributes within each Part instance
        (OOP style) by <Station>.find_part_edges().

        Must run <Station>.find_part_edges() first.

        KNOWN BUG: this doesn't work after rotating the airfoil coordinates.
        (This feature will not be implemented.)

        """
        st = self.structure
        try:
            if st.spar_cap.exists():
                axes.axvspan(st.spar_cap.left, st.spar_cap.right, facecolor='cyan', edgecolor='cyan', alpha=0.7)
            if st.TE_reinforcement.exists():
                axes.axvspan(st.TE_reinforcement.left, st.TE_reinforcement.right, facecolor='pink', edgecolor='pink', alpha=0.7)
            if st.LE_panel.exists():
                axes.axvspan(st.LE_panel.left, st.LE_panel.right, facecolor='magenta', edgecolor='magenta', alpha=0.7)
            if st.aft_panel_1.exists():
                axes.axvspan(st.aft_panel_1.left, st.aft_panel_1.right, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.aft_panel_2.exists():
                axes.axvspan(st.aft_panel_2.left, st.aft_panel_2.right, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.shear_web_1.exists():
                axes.axvspan(st.shear_web_1.left, st.shear_web_1.right, facecolor='green', edgecolor='green')
            if st.shear_web_2.exists():
                axes.axvspan(st.shear_web_2.left, st.shear_web_2.right, facecolor='green', edgecolor='green')
            if st.shear_web_3.exists():
                axes.axvspan(st.shear_web_3.left, st.shear_web_3.right, facecolor='green', edgecolor='green')
        except AttributeError:
            raise AttributeError("Part edges (.left and .right) have not been defined yet!\n  Try running <Station>.find_part_edges() first.")

    def plot_parts(self):
        """Plots the structural parts in this blade station."""
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
                self.plot_polygon(st.external_surface.polygon_gelcoat,
                    ax, face_color='#4000FF', edge_color='#000000',
                    alpha=0.8)  # face color is purple
                self.plot_polygon(st.external_surface.polygon_triax,
                    ax, face_color='#4000FF', edge_color='#000000',
                    alpha=0.8)  # face color is purple
            if st.root_buildup.exists():
                self.plot_polygon(st.root_buildup.polygon, ax,
                    face_color='#BE925A', edge_color='#000000',
                    alpha=0.8)  # face color is brown
            if st.spar_cap.exists():
                self.plot_polygon(st.spar_cap.polygon_lower, ax,
                    face_color='#00ACEF', edge_color='#000000',
                    alpha=0.8)  # face color is blue
                self.plot_polygon(st.spar_cap.polygon_upper, ax,
                    face_color='#00ACEF', edge_color='#000000',
                    alpha=0.8)  # face color is blue
            if st.aft_panel_1.exists():
                self.plot_polygon(st.aft_panel_1.polygon_lower, ax,
                    face_color='#F58612', edge_color='#000000',
                    alpha=0.8)  # face color is orange
                self.plot_polygon(st.aft_panel_1.polygon_upper, ax,
                    face_color='#F58612', edge_color='#000000',
                    alpha=0.8)  # face color is orange
            if st.aft_panel_2.exists():
                self.plot_polygon(st.aft_panel_2.polygon_lower, ax,
                    face_color='#F58612', edge_color='#000000',
                    alpha=0.8)  # face color is orange
                self.plot_polygon(st.aft_panel_2.polygon_upper, ax,
                    face_color='#F58612', edge_color='#000000',
                    alpha=0.8)  # face color is orange
            if st.LE_panel.exists():
                self.plot_polygon(st.LE_panel.polygon, ax,
                    face_color='#00A64F', edge_color='#000000',
                    alpha=0.8)  # face color is green
            if st.shear_web_1.exists():
                self.plot_polygon(st.shear_web_1.polygon_left_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_1.polygon_foam, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_1.polygon_right_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
            if st.shear_web_2.exists():
                self.plot_polygon(st.shear_web_2.polygon_left_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_2.polygon_foam, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_2.polygon_right_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
            if st.shear_web_3.exists():
                self.plot_polygon(st.shear_web_3.polygon_left_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_3.polygon_foam, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
                self.plot_polygon(st.shear_web_3.polygon_right_biax, ax,
                    face_color='#FFF100', edge_color='#000000',
                    alpha=0.8)  # face color is yellow
            if st.TE_reinforcement.exists():
                self.plot_polygon(st.TE_reinforcement.polygon_uniax, ax,
                    face_color='#F366BA', edge_color='#000000',
                    alpha=0.8)  # face color is pink
                try:
                    self.plot_polygon(st.TE_reinforcement.polygon_foam, ax,
                        face_color='#F366BA', edge_color='#000000',
                        alpha=0.8)  # face color is pink
                except TypeError:  # foam region doesn't exist
                    pass
            if st.internal_surface_1.exists():
                self.plot_polygon(st.internal_surface_1.polygon_triax, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
                self.plot_polygon(st.internal_surface_1.polygon_resin, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
            if st.internal_surface_2.exists():
                self.plot_polygon(st.internal_surface_2.polygon_triax, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
                self.plot_polygon(st.internal_surface_2.polygon_resin, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
            if st.internal_surface_3.exists():
                self.plot_polygon(st.internal_surface_3.polygon_triax, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
                self.plot_polygon(st.internal_surface_3.polygon_resin, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
            if st.internal_surface_4.exists():
                self.plot_polygon(st.internal_surface_4.polygon_triax, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
                self.plot_polygon(st.internal_surface_4.polygon_resin, ax,
                    face_color='#999999', edge_color='#000000',
                    alpha=0.8)  # face color is gray
        except AttributeError:
            raise AttributeError("Part instance has no attribute 'polygon'.\n  Try running <station>.find_all_part_polygons() first.")
        plt.show()
        return (fig, ax)

    # def cross_section_area(self):
    #     """Calculate the total cross-section area for this station."""
    #     p = self.merge_all_parts(merge_internal_surface=False)
    #     return p.area


class BiplaneStation(_Station):
    """Define a biplane station for a biplane wind turbine blade."""
    def __init__(self, stn_series, blade_path):
        """Create a new biplane station for a biplane blade."""
        _Station.__init__(self, stn_series, blade_path)
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
            stagger_to_chord_ratio=stn_series['stagger-to-chord ratio'])
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
            h_int_surf_triax=stn_series['internal surface height triax'],
            h_int_surf_resin=stn_series['internal surface height resin'],
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
            h_int_surf_triax_u=stn_series['internal surface height triax upper'],
            h_int_surf_resin_u=stn_series['internal surface height resin upper'],
            h_ext_surf_triax_u=stn_series['external surface height triax upper'],
            h_ext_surf_gelcoat_u=stn_series['external surface height gelcoat upper'])
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

    def plot_part_edges(self, axes):
        """Plot color block for each structural part region.

        Each color block spans the plot from top to bottom.

        Uses coordinates saved as attributes within each Part instance
        (OOP style) by <Station>.find_part_edges().

        Must run <Station>.find_part_edges() first.

        KNOWN BUG: this doesn't work after rotating the airfoil coordinates.
        (This feature will not be implemented.)

        """
        st = self.structure
        # upper airfoil
        try:
            if st.upper_spar_cap.exists():
                axes.axvspan(st.upper_spar_cap.left, st.upper_spar_cap.right, ymin=0.5, facecolor='cyan', edgecolor='cyan', alpha=0.7)
            if st.upper_TE_reinforcement.exists():
                axes.axvspan(st.upper_TE_reinforcement.left, st.upper_TE_reinforcement.right, ymin=0.5, facecolor='pink', edgecolor='pink', alpha=0.7)
            if st.upper_LE_panel.exists():
                axes.axvspan(st.upper_LE_panel.left, st.upper_LE_panel.right, ymin=0.5, facecolor='magenta', edgecolor='magenta', alpha=0.7)
            if st.upper_aft_panel_1.exists():
                axes.axvspan(st.upper_aft_panel_1.left, st.upper_aft_panel_1.right, ymin=0.5, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.upper_aft_panel_2.exists():
                axes.axvspan(st.upper_aft_panel_2.left, st.upper_aft_panel_2.right, ymin=0.5, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.upper_shear_web_1.exists():
                axes.axvspan(st.upper_shear_web_1.left, st.upper_shear_web_1.right, ymin=0.5, facecolor='green', edgecolor='green')
            if st.upper_shear_web_2.exists():
                axes.axvspan(st.upper_shear_web_2.left, st.upper_shear_web_2.right, ymin=0.5, facecolor='green', edgecolor='green')
            if st.upper_shear_web_3.exists():
                axes.axvspan(st.upper_shear_web_3.left, st.upper_shear_web_3.right, ymin=0.5, facecolor='green', edgecolor='green')
        except AttributeError:
            raise AttributeError("Part edges (.left and .right) have not been defined yet!\n  Try running <Station>.find_part_edges() first.")
        # lower airfoil
        try:
            if st.lower_spar_cap.exists():
                axes.axvspan(st.lower_spar_cap.left, st.lower_spar_cap.right, ymax=0.5, facecolor='cyan', edgecolor='cyan', alpha=0.7)
            if st.lower_TE_reinforcement.exists():
                axes.axvspan(st.lower_TE_reinforcement.left, st.lower_TE_reinforcement.right, ymax=0.5, facecolor='pink', edgecolor='pink', alpha=0.7)
            if st.lower_LE_panel.exists():
                axes.axvspan(st.lower_LE_panel.left, st.lower_LE_panel.right, ymax=0.5, facecolor='magenta', edgecolor='magenta', alpha=0.7)
            if st.lower_aft_panel_1.exists():
                axes.axvspan(st.lower_aft_panel_1.left, st.lower_aft_panel_1.right, ymax=0.5, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.lower_aft_panel_2.exists():
                axes.axvspan(st.lower_aft_panel_2.left, st.lower_aft_panel_2.right, ymax=0.5, facecolor='orange', edgecolor='orange', alpha=0.7)
            if st.lower_shear_web_1.exists():
                axes.axvspan(st.lower_shear_web_1.left, st.lower_shear_web_1.right, ymax=0.5, facecolor='green', edgecolor='green')
            if st.lower_shear_web_2.exists():
                axes.axvspan(st.lower_shear_web_2.left, st.lower_shear_web_2.right, ymax=0.5, facecolor='green', edgecolor='green')
            if st.lower_shear_web_3.exists():
                axes.axvspan(st.lower_shear_web_3.left, st.lower_shear_web_3.right, ymax=0.5, facecolor='green', edgecolor='green')
        except AttributeError:
            raise AttributeError("Part edges (.left and .right) have not been defined yet!\n  Try running <Station>.find_part_edges() first.")

    def find_SW_cs_coords(self):
        """Find the corners of the cross-sections for each shear web.

        Saves cross-section coordinates (in meters) as the '.cs_coords' 
        attribute (a numpy array) within each ShearWeb instance.

        """
        st = self.structure
        af = self.airfoil
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
