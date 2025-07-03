# mypy: ignore-errors
'''
Short description:
    The main code that needs to be run to open the Tkinter-window and the Bokeh-plots.
    Its interface-class is the fundamental structure that makes the program run as intended.

Why:
    A class that combines functions and classes from the different files in order to accieve the wanted functionality.

Depends on:
    circuit_handler2.py
    generate_bokeh2.py
    DRT_fitting.py
    tkinter_window.py
    fitting_algorithms.py

@author: Elling Svee (elling.svee@gmail.com)
'''
import os
import tkinter as tk
from bokeh.io import show
from bokeh.models import CustomJS
import pandas as pd         # For sorting file structure
from bokeh.plotting import output_file, save
import dependencies.generate_bokeh as gb
import dependencies.circuit_handler as ch  
from dependencies.tkinter_window import tkinter_class
from dependencies.fitting_algorithms import retrieve_data, fit_with_circuit, fit_with_DRT, predict_impedances

import time
from tkinter import ttk
from tkinter import filedialog
from shutil import rmtree
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dependencies.eis_sample import EIS_Sample
from bokeh.io import show, curdoc
from datetime import date
from bokeh.models import Button, CustomJS, CheckboxButtonGroup, CheckboxGroup, ColorPicker, ColumnDataSource, DataTable, TabPanel
from bokeh.models import CDSView, GroupFilter, CustomJSFilter
from bokeh.models import DateFormatter, TableColumn, DatePicker, DateRangeSlider, text, Dropdown, MultiChoice, MultiSelect, Div
from bokeh.models import PasswordInput, RadioButtonGroup, RadioGroup, RangeSlider, Select, Slider, Span, Tabs, GridPlot, Plot, HoverTool
from bokeh.models import LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.layouts import column, row, layout
from bokeh.palettes import Cividis, Spectral, Turbo256, Plasma256, Viridis256    # Color palettes
import numpy as np
import math
import copy # For doing deeper copies

from datetime import datetime # For sorting dates
from io import StringIO
from impedance.models.circuits.circuits import CustomCircuit


class interface():
    def __init__(self, opened_from_controlmain_bool = False) -> None:
        """
        Set up the interface and its widgets. Calls the root.mainloop starting
        the programs wait and idle behavior.
        """
        # Auto-run variable
        self.auto_run_state = False
        self.auto_run_min = 10 # Min
        self.auto_run_plot = False # Plot aswell

        # Variables related to the processing and fitting
        self.df                         = pd.DataFrame(data={})
        self.circuit_df                 = pd.DataFrame(data={})
        self.impedance_from_fitting_df  = pd.DataFrame(data={})
        self.DRT_df                     = pd.DataFrame(data={})
        self.Z_pred_df                  = pd.DataFrame(data={})
        self.model_df                   = pd.DataFrame(data={})
        self.circuit_base_variables = []
        self.all_base_variables = ["Re", "R1", "R2", "R3", "R4", "C1", "C2", "C3", "L1", "std_Re", "std_R1", "std_R2", "std_R3", "std_R4", "std_C1", "std_C2", "std_C3", "std_L1", r"$\tau$ 1", r"$\tau$ 2", r"$\tau$ 3", "TotR", "TotC", "Chivalue"]
        
        self.DRT_maxiter = 400
        self.DRT_range_pred = 101
        self.DRT_repeat_criterion = 100
        

        self.DRT_sigma_n_start     = 0
        self.DRT_sigma_n_end       = 0.001
        self.DRT_sigma_f_start     = 0
        self.DRT_sigma_f_end       = 0.1
        self.DRT_ell_start         = 0
        self.DRT_ell_end           = 3  

        self.current = "some string with current cell and folder"
        self.log_hyperparameters = False

        self.axes_roundoff_decimals = 3
        self.normalizing_areas = {
            'cm^2' : 1 
        }
        self.display_res_in_milli = True
        self.display_cap_in_milli = True
        
        self.Z_pred_min_factor = 0.5
        self.Z_pred_max_factor = 2
        self.Z_pred_num = 100
        self.Z_pred_maxiter = 10
        self.Z_pred_tolerance =  1e-5

        self.bokeh_output_file_name = 'dashboard_for_plotting_and_fitting'

        # Variables used in normalization
        self.area_size = -1
        self.area_str = 'cm^2'
        
        # Default values
        self.parent_path = os.getcwd()
        self.directory = "Total_mm"
        self.default_path = os.path.join(self.parent_path, self.directory)
        
        
        # Need to create different_tkinter_windows based on if if is opened from this file or from the button in control_main
        self.opened_from_controlmain_bool = opened_from_controlmain_bool
        if not self.opened_from_controlmain_bool:
            self.open_window()

    def open_window(self):
        try:
            #### Window setup ####
            self.tw = tkinter_class(self) # initialize tkinter-window class, see own file
            # Starts the windows mainloop, which activates a idle og wait behavior
            self.tw.root.mainloop()
        except:
            print('interface -> init: Unable to start tkinter window.')

    def find_circuit_type(self, in_file_path, out_file_path) -> ch.BaseCircuitHandler:
        """
        When
        ----------
        Called when a Circuit should be made, from the process and load existing
        functions.

        Does
        ----------
        Creates a circuit handler with the circuit string taken from the stored
        vale of circuit_string.get(). If normalize is true the circuit handler
        vil be created with normalized data and units. Also pass the log function
        to the circuit handler. The file paths are also passed and used when it
        should load/save data.

        Note
        ----------
        Errors are raised if the circuit string or the paths
        are invalid.
        """
        # With normalization
        if self.tw.normalize_checkbox_var.get() == 1 or self.tw.normalize_checkbox_var.get() == 1.0 or self.tw.normalize_checkbox_var.get() == "1" or self.tw.normalize_checkbox_var.get() == '1.0':
            circuit_handler = ch.get_circuit_handler(self.tw.circuit_string.get())(
                in_file_path,
                out_file_path,
                self.tw.log,
                area_str=self.area_str, # Normalization input
                area_size=float(self.area_size)  # Normalization input
            )
        # Without normalization
        else:
            # print(' Without normalization')
            circuit_handler = ch.get_circuit_handler(self.tw.circuit_string.get())(
                in_file_path, '', self.tw.log, area_str = 'cm^2', area_size=float(-1)
            )
        # Checks if the retured circuit is valid instance
        if circuit_handler is None:
            raise IndexError(
                f"The circuit you are using ({self.tw.circuit_string.get()}) have not been implemented."
            )
        # Return the created circuit handler
        return circuit_handler
    
    def update_normalize_params(self):
        '''
        If data is normalized, this function makes sure that the self.area_size-variable gets updated with the correct value.        
        '''
        if (True in self.df['normalized'].tolist()) or ('True' in self.df['normalized'].tolist()):
            self.area_size = self.df.iloc[0]['area'][:-4] # Slice away the ' cm^2' at the end of the value
        else:
            self.area_size = float(-1)
        self.area_str = 'cm^2'

    def process(self):
        '''
        Function that calls other functions (most of them located in fitting_algorithm.py) in order to perform the full retrieval and fitting of the data.

        '''
        self.tw.start['state'] = tk.DISABLED
        self.tw.start['bg']    = self.tw.text_disabled_color
        self.tw.bokeh_output_file_name_button['bg'] = self.tw.browse_button_color

        self.all_data_files         = []
        self.all_data               = {}
        self.df                     = pd.DataFrame(data={})
        self.circuit_df             = pd.DataFrame(data={})
        self.circuit_base_variables = []
        try:
            self.df= retrieve_data(self)        #
            print(f"self.df: {self.df}")
        except Exception as error:
            e = Exception(f"Unable to retrieve data from directory due to {error}. Make sure you select a valid folder.")
            self.tw.log(e)
            raise e

        if len(self.df) == 0:
            e = Exception("The chosen dir yielded a empty dataframe. Make sure you select a valid folder.")
            self.tw.log(e)
            raise e
        
        try:
            self.update_normalize_params()
        except:
            self.tw.log("process -> update_normalize_params: Unable to update the area_size-parameter.")

        if self.tw.circuit_fit_checkbox_var.get()  == 1:
            try:
                self.circuit_df, self.impedance_from_fitting_df, self.circuit_base_variables = fit_with_circuit(self, self.df)
            except: 
                self.tw.log("process -> fit_with_circuit: Unable to perform circuit-fitting.")
        if self.tw.DRT_fit_checkbox_var.get() == 1:
            try:
                self.DRT_df = fit_with_DRT(self, self.df)
            except Exception as e:
                print(f"Unexpected {e=}, {type(e)=}")
                self.tw.log("process -> fit_with_DRT: Unable to perform DRT-fitting.")


        if self.tw.Z_pred_checkbox_var.get() == 1:
            self.Z_pred_df = predict_impedances(self, self.df)

        self.tw.use_prev_data_alert.grid_remove()
        self.tw.save_data.configure(bg=self.tw.red_button, text="SAVE")
        self.tw.start['state'] = tk.NORMAL
        self.tw.start['bg']    = self.tw.generate_interface_color
        self.tw.save_file_folder_label['state'] = tk.NORMAL
        self.tw.save_file_folder['state'] = tk.NORMAL
        self.tw.save_data['state'] = tk.NORMAL
        self.tw.save_file_folder_button['state'] = tk.NORMAL

    def auto_run(self):
        '''
        When run it coninously watches the chosen data-folder. After the spesified waiting time, it will re-process the data.
        Note
        ----------
        Could be massively improved by ONLY processing the new files that have not been previously processed. This is currently not implemented. 
        '''
        if self.auto_run_state: # It might be a problemt that the program freezes when performing calculations. Such that it is "impossible" to uncheck the auto-run-button.
            self.tw.auto_run_update_button['state'] = tk.DISABLED
            self.tw.auto_run_update_button['bg']    = self.tw.red_button

            self.process() # Run the func
            
            # If chosen in settings, also create new bokeh-plot
            if self.auto_run_plot: 
                ...
            
            # Change color of update-button
            self.tw.auto_run_update_button['state'] = tk.NORMAL
            self.tw.auto_run_update_button['bg']    = self.tw.generate_interface_color

            # Wait desired amt of time. Make sure it is enouch waiting time compared to the time it takes to run the DRT-fitting.
            auto_run_min = 10
            if int(self.tw.auto_run_min_var.get()) > 0:
                auto_run_min = int(self.tw.auto_run_min_var.get())
            # time.sleep(self.auto_run_min*60)
            self.tw.root.after(auto_run_min*60*1000, self.auto_run) # Wait spesified amount of time

    def create_bokeh(self):
        """
        When
        ----------
        Called when the Generate Interface-button is pressed

        Does
        ----------
        Using the calulated (or loaded) data in the self.df-dataframe to generate a Bokeh-interface as a HTML-file that will be opened in a brower
        
        Note
        ----------
        Utilizes functions and classed defined in the generate_bokeh file.
        """

        self.tw.bokeh_output_file_name_button['bg'] = self.tw.browse_button_color # Resetting the color of the button that selects the filename

        #### Initializing the classes and relevant varianbles ####
        currentplot = gb.CurrentPlot(self)
        currentplot.update()
        self.update_normalize_params()
        currentplot.normalized_bool = (self.area_size != float(-1))

        #### Widget setup ####
        gb.create_widgets(currentplot)

        #### Plots ####
        p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist = gb.create_figures()

        # # Filter
        # filt = gb.create_filter(currentplot)

        # Adding glyphs to plot
        currentplot.instert_glyphs(p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist)

        # Settings for the two plots
        gb.plot_settings(currentplot, p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist)


        # Callback for cell selection
        code_str = '''src.change.emit(); for (let i = 0; i < imp_srcs.length; i++) {imp_srcs[i].change.emit();}; for (let i = 0; i < Z_pred_srcs.length; i++) {Z_pred_srcs[i].change.emit();}'''
        # Cells
        currentplot.cell_selector_callback = gb.create_callback(currentplot)
        currentplot.cell_selector.js_on_change('active', currentplot.cell_selector_callback) 
        currentplot.temperature_selector.js_on_change('active' ,CustomJS(args=dict(src=currentplot.cell_source, imp_srcs=currentplot.filtered_impedance_sources, Z_pred_srcs=currentplot.filtered_Z_pred_sources), code=code_str))
        currentplot.pressure_selector.js_on_change('active' ,CustomJS(args=dict(src=currentplot.cell_source, imp_srcs=currentplot.filtered_impedance_sources, Z_pred_srcs=currentplot.filtered_Z_pred_sources),code=code_str))
        currentplot.dc_current_selector.js_on_change('active' ,CustomJS(args=dict(src=currentplot.cell_source, imp_srcs=currentplot.filtered_impedance_sources, Z_pred_srcs=currentplot.filtered_Z_pred_sources),code=code_str))
        currentplot.ac_current_selector.js_on_change('active' ,CustomJS(args=dict(src=currentplot.cell_source, imp_srcs=currentplot.filtered_impedance_sources, Z_pred_srcs=currentplot.filtered_Z_pred_sources),code=code_str))
        currentplot.hide_fitted_impedance.js_on_change('active', currentplot.cell_selector_callback) 
        currentplot.hide_prediction_error.js_on_change('active', currentplot.cell_selector_callback) 

        currentplot.date_selector.js_on_change('value', currentplot.cell_selector_callback)
        # Resistance-plot
        currentplot.resistance_callback = gb.create_callback(currentplot)
        currentplot.resistance_selector.js_on_change('active', currentplot.resistance_callback) 
        # Capacitance-plot
        currentplot.capacitance_callback = gb.create_callback(currentplot)
        currentplot.capacitance_selector.js_on_change('active', currentplot.capacitance_callback)
        # Time-plot
        currentplot.time_callback = gb.create_callback(currentplot)
        currentplot.time_selector.js_on_change('active', currentplot.time_callback)

        #### Layout ####
        lay_out = gb.create_layout(currentplot, p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist ,self.area_size, self.area_str)

        output_file(filename=self.bokeh_output_file_name + ".html", title="Bokeh Plot")
        save(lay_out)
        show(lay_out) # Opening the interface
        

if __name__ == "__main__":
    interface()