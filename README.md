bladedesign
===========

tool to set up structural models of [biplane] wind turbine blades

Current workflow (as of April 10, 2014)
---------------------------------------
1. `create_stnXX_mesh.py` - write initial TrueGrid input file with boundary curves: `mesh_stnXX_start.tg`
2. manually edit `mesh_stnXX_start.tg` to create block meshes fitted to boundary curves; save as `mesh_stnXX_finish.tg`
3. run TrueGrid on `mesh_stnXX_finish.tg` to write ABAQUS output file: `mesh_stnXX.abq`
4. run `layer_plane_angles_stnXX.py` - write updated grid object to VABS input file: `mesh_stnXX.vabs`
5. run `run_vabs.py` - use VABS to calculate mass and stiffness matrices
6. `mesh_stnXX.vabs.K` - mass and stiffness matrices are in this file!
7. run `plot_MK.py` - plot VABS data vs. Sandia published data
8. run `write_DYMORE_input_file.py` - write VABS output for a DYMORE input file to `sandia_blade_OD.dat` and `sandia_blade_MK.dat`
9. manually copy contents of `sandia_blade_OD.dat` and `sandia_blade_MK.dat` into `sandia_blade.dat`.
10. run `rundymore.bat` to load the structural model
11. run `plot_DYMORE_results.py` to postprocess results in `FIGURES` directory
12. run `clean.bat` to erase all DYMORE results

Usage: `create_blades.py`
-------------------------
start an IPython (qt)console with the pylab flag:  
`$ ipython qtconsole --pylab`  
Then, from the prompt, run this script:  
`|> %run create_blades`  
Once you are finished looking at the blades, you can clean up extra files:  
`|> %run clean`  

Usage: `create_meshes.py`
-------------------------
start an IPython (qt)console with the pylab flag:  
`$ ipython qtconsole --pylab`  
Then, from the prompt, run this script:  
`|> %run create_meshes`  

Usage: `create_stnXX_mesh.py`
-------------------------
start an IPython (qt)console with the pylab flag:  
`$ ipython qtconsole --pylab`  
Then, from the prompt, run this script:  
`|> %run create_stnXX_mesh`  

Usage: `layer_plane_angles_stnXX.py`
-------------------------
start an IPython (qt)console with the pylab flag:  
`$ ipython qtconsole --pylab`  
Then, from the prompt, run this script:  
`|> %run layer_plane_angles_stnXX`  

List of top-level scripts
-------------------------
* `create_blades.py` - Create the Sandia blade and 4 biplane blades
* `create_meshes.py` - Write initial TrueGrid files for Sandia blade stations
* `create_stnXX_mesh.py` - Write initial TrueGrid file for Sandia station #XX
* `layer_plane_angles_stnXX.py` - Write updated grid object to VABS input file for station #XX

List of cleanup scripts
-----------------------
* `clean.py` - Delete leftover files and paths in each `blade_path`
* `clear_logs.py` - Delete the contents of all the log files

Plan forward (as of March 13, 2014)
----------------------------------
Instead of automatically generating meshes with Python, let's only use Python to automatically generate boundary curves for each part in a blade station. (I think I already have this functionality.) Then, manually mesh each station in TrueGrid. (Start with Station #1 and work your way out to Station #34.) Save the final `*.tg` file in an archive of all the blade input files. Export the grid in ABAQUS format and use Python to tranlate it to VABS format. Use VABS to generate the mass and stiffness matrix. This will be tedious, but straightforward. In the end, you should have an archive of all the blade input files that looks like:

* `sandia_blade/`  
  * `blade_definition.csv`  
  * `materials.csv`  
  * `airfoils/`  
    * `Cylinder.txt`
    * ...
    * `NACA_64-618.txt`
  * `stn01/`
    * `mesh_stn01_start.tg` (initial TrueGrid input file with part boundary curves)
    * `mesh_stn01_final.tg` (final TrueGrid input file with grids inside curves)
    * `mesh_stn01.abq` (exported grid file in ABAQUS format)
    * `mesh_stn01.vabs` (VABS input file of geometry and materials)
    * `mesh_stn01.vabs.K` (VABS output of mass and stiffness matrices)
  * `stn02/`
  * ...
  * `stn34/`
