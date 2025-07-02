'''
Short description:
    The code that handles the reaction and main functionality of the Bokeh-plots. 
    Creates an html-file that can be run and shared seperately with out the rest of the python-files.

Why:
    Seperate the bokeh-realted stuff to make the rest of the code cleaner

@author: Elling Svee (elling.svee@gmail.com)
'''


import os
from datetime import date
from bokeh.models import CustomJS, CheckboxGroup, ColumnDataSource, TabPanel, Whisker
from bokeh.models import CDSView, GroupFilter, CustomJSFilter
from bokeh.models import DateRangeSlider, Dropdown, Div, CustomJSTickFormatter
from bokeh.models import RadioButtonGroup, RangeSlider, Span, Tabs, HoverTool
from bokeh.models import LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.layouts import column, row, layout
from bokeh.palettes import Turbo256, Plasma256, Viridis256    # Color palettes
import numpy as np
from datetime import datetime, timedelta # For sorting dates

from typing import Iterable
import EIS_GUI
import tkinter as tk
from tkinter import filedialog
from shutil import rmtree
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dependencies.eis_sample import EIS_Sample
import time
from bokeh.io import show, curdoc

from bokeh.models.annotations.labels import Label
from bokeh.models import Button, CustomJS, CheckboxButtonGroup, CheckboxGroup, ColorPicker, ColumnDataSource, DataTable, TabPanel, Whisker, ArrowHead, Arrow, OpenHead, TeeHead

from bokeh.models import DateFormatter, TableColumn, DatePicker, DateRangeSlider, text, Dropdown, MultiChoice, MultiSelect, Div, CustomJSTickFormatter, Checkbox
from bokeh.models import PasswordInput, RadioButtonGroup, RadioGroup, RangeSlider, Select, Slider, Span, Tabs, GridPlot, Plot, HoverTool, RangeTool
from bokeh.models import LinearAxis, Range1d, VArea

import math
import copy # For doing deeper copies
import pandas as pd         # For sorting file structure

class CurrentPlot:
    '''
    Class for better control of the variables related to the data imported into the dashboard. Should maybe eventually be combined with the CurrentPlot-class.
    '''
    def __init__(self, interface):
        self.cell_source                    = ColumnDataSource(data = {})
        self.circuit_source                 = ColumnDataSource(data = {})
        self.impedance_from_fitting_source  = ColumnDataSource(data = {})
        self.filtered_impedance_sources     = []
        self.filtered_Z_pred_sources        = []
        self.DRT_source                     = ColumnDataSource(data = {})
        self.Z_pred_source                  = ColumnDataSource(data = {})


        self.df                             = interface.df
        self.circuit_df                     = interface.circuit_df
        self.impedance_from_fitting_df      = interface.impedance_from_fitting_df
        self.DRT_df                         = interface.DRT_df
        self.Z_pred_df                      = interface.Z_pred_df
        self.interface                      = interface
        
        # Two dicts including elements for the earliest and latest date in the dataset. See the update-function for how these are created
        self.start_date_list = {}
        self.end_date_list = {}
        
        # Labels used when creating the widgets
        self.CELL_SELECTOR_LABEL            = None
        self.TEMPERATURE_SELECTOR_LABEL     = None 
        self.PRESSURE_SELECTOR_LABEL        = None 
        self.DC_CURRENT_SELECTOR_LABEL      = None 
        self.AC_CURRENT_SELECTOR_LABEL      = None
        self.RESISTANCE_SELECTOR_LABEL      = None
        self.capacitance_selector_LABEL     = None
        self.TIME_SELECTOR_LABEL            = None

        # Variables from the fitting
        self.circuit_base_variables     = interface.circuit_base_variables
        self.resistance_base_variables  = ["Re", "R1", "R2", "R3", "R4", "TotR"]
        self.resistance_std_deviations  = ["std_Re", "std_R1", "std_R2", "std_R3", "std_R4"]
        self.capacitance_base_variables = ["C1", "C2", "C3", "TotC"]
        self.capacitance_std_deviations = ["std_C1", "std_C2", "std_C3"]
        self.time_base_variables        = [r"$\tau$ 1", r"$\tau$ 2", r"$\tau$ 3"]
    
        self.area_str_value             = interface.normalizing_areas[interface.area_str]
        self.axes_roundoff_decimals     = interface.axes_roundoff_decimals

        # Boolean to check if normalized
        self.normalized_bool            = False

        # Contains the glyphs for the different cells.
        self.cell_plots                     = {}
        # Contains the glyphs for the different data from circuit-fitting. Is "organized" as self.circuit_plots[name of cell] -> Dict (key=name of base variable, value = [Gllyph related to the cell and base variable, error-bar])
        self.circuit_plots                  = {}
        self.impedance_from_fitting_plots   = {}
         # Contains the glyphs for the different cells. Is "organized" as self.DRT_plots[cell_name] ->  Dict (key=name of dictionary, value = [Plot of fitting, Plot of fitting-error])
        self.DRT_plots                      = {}
        self.modeval_plots                  = {}
        self.modnyq_plots                   = {}

        self.Z_pred_imag_plots              = {}
        self.Z_pred_plots                   = {}

        # Widgets
        self.cell_selector              = None
        self.temperature_selector       = None
        self.date_selector              = None
        self.pressure_selector          = None
        self.dc_current_selector        = None
        self.ac_current_selector        = None
        self.resistance_selector        = None
        self.capacitance_selector       = None
        self.time_selector              = None
        self.hide_fitted_impedance      = None
        self.hide_prediction_error      = None

        # Callbacks 
        self.cell_selector_callback     = None
        self.resistance_callback        = None
        self.capacitance_callback       = None
        self.time_callback              = None

    def update(self):
        '''
        Large function that updates all the labels, and the sources used in the various plots 
        '''
        self.CELL_SELECTOR_LABEL        = []
        self.TEMPERATURE_SELECTOR_LABEL = []
        self.PRESSURE_SELECTOR_LABEL    = []
        self.DC_CURRENT_SELECTOR_LABEL  = []
        self.AC_CURRENT_SELECTOR_LABEL  = []
        self.RESISTANCE_SELECTOR_LABEL  = []
        self.capacitance_selector_LABEL = []
        self.TIME_SELECTOR_LABEL        = []
        self.CELL_SELECTOR_LABEL        = self.df['cell_name'].unique().tolist()
        self.TEMPERATURE_SELECTOR_LABEL = self.df['temp'].unique().tolist()
        self.PRESSURE_SELECTOR_LABEL    = self.df['pressure'].unique().tolist()
        self.DC_CURRENT_SELECTOR_LABEL  = self.df['dc'].unique().tolist()
        self.AC_CURRENT_SELECTOR_LABEL  = self.df['ac'].unique().tolist()

        for base_variable in self.circuit_base_variables:
            if base_variable in self.resistance_base_variables:
                self.RESISTANCE_SELECTOR_LABEL.append(base_variable)
            elif base_variable in self.capacitance_base_variables:
                self.capacitance_selector_LABEL.append(base_variable)
            elif base_variable in self.time_base_variables:
                self.TIME_SELECTOR_LABEL.append(base_variable)

        self.cell_source.data                   = {col_name : self.df[col_name].tolist() for col_name in self.df.columns}
        self.circuit_source.data                = {col_name : self.circuit_df[col_name].tolist() for col_name in self.circuit_df.columns}
        self.impedance_from_fitting_source.data = {col_name : self.impedance_from_fitting_df[col_name].tolist() for col_name in self.impedance_from_fitting_df.columns}
        self.DRT_source.data                    = {col_name : self.DRT_df[col_name].tolist() for col_name in self.DRT_df.columns}
        self.Z_pred_source.data                 = {col_name : self.Z_pred_df[col_name].tolist() for col_name in self.Z_pred_df.columns}


        # Update the dits with the info about the earliest and latest dates inthe dataset
        self.dates_list                      = self.df['dir_name'].unique().tolist() # The name of the dirs are also the dates of the data
        # Convert date strings to datetime objects (make note of the "weird" date-format...this is how the raw-data is generated)
        date_objects                    = [datetime.strptime(date_str, "%Y-%m-%d-%H%M-%S") for date_str in self.dates_list]

        # Find the earliest and latest date in the list
        earliest_date                   = min(date_objects)
        latest_date                     = max(date_objects)
        # Update the start_date_list and end_date_list dicts
        self.start_date_dict = {
            'full_string'   : earliest_date.strftime("%Y-%m-%d-%H%M-%S"),
            'year'          : earliest_date.year, 
            'month'         : earliest_date.month, 
            'day'           : earliest_date.day, 
            'hour'          : earliest_date.hour,
            'min'           : earliest_date.minute,
            'sec'           : earliest_date.second
        }
        self.end_date_dict = {
            'full_string'   : latest_date.strftime("%Y-%m-%d-%H%M-%S"),
            'year'          : latest_date.year, 
            'month'         : latest_date.month, 
            'day'           : latest_date.day, 
            'hour'          : latest_date.hour,
            'min'           : latest_date.minute,
            'sec'           : latest_date.second
        }


    def instert_glyphs(self, p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist):
        '''
        Inserting the glyphs into the plots, and organizing them in thir relevant dicts. This is where you whange what data gets plotted and its appearance.
        '''
        # Creating color-schemes
        resistance_colors   = {}
        capacitance_colors  = {}
        time_colors         = {}
        for i, base_variable in enumerate(self.RESISTANCE_SELECTOR_LABEL):
            resistance_colors[base_variable] = Turbo256[1 + i*int(256/len(self.RESISTANCE_SELECTOR_LABEL))]
        for i, base_variable in enumerate(self.capacitance_selector_LABEL):
            capacitance_colors[base_variable] = Turbo256[1 + i*int(256/len(self.capacitance_selector_LABEL))]
        for i, base_variable in enumerate(self.TIME_SELECTOR_LABEL):
            time_colors[base_variable] = Turbo256[1 + i*int(256/len(self.TIME_SELECTOR_LABEL))]
        
        renderers_lines_list = []
        renderers_varea_list = []
        modeval_renderers_scatter_list = []
        modeval_renderers_lines_list = []
        modnyq_renderers_lines_list = []
        modnyq_renderers_scatter_list = []
        Z_pred_renderers_points_list = []
        Z_pred_renderers_lines_list = []
        Z_pred_renderers_varea_list = []
        
        # Iterating though all the cells
        for cell_color_counter, cell_name in enumerate(self.CELL_SELECTOR_LABEL):
            cell_color          = Plasma256[1 + cell_color_counter*int(256/len(self.CELL_SELECTOR_LABEL))]
            
            self.cell_plots[cell_name]          = {}
            self.Z_pred_imag_plots[cell_name]   = {}
            self.Z_pred_plots[cell_name]        = {}

            dir_names = self.df['dir_name'].unique().tolist()

            # Creating a color-scheme
            dir_colors = {}
            for i, dir_name in enumerate(dir_names):
                dir_colors[dir_name] = Viridis256[1 + i*int(256/len(dir_names))]


            for dir_name in dir_names:
            
                # Filter
                filt = create_filter(self)
                view                = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name) 
                                              & GroupFilter(column_name="dir_name", group=dir_name)
                                              & filt) # Filter for the glyphs in the Nyquist- and Bode-plots 
                self.cell_plots[cell_name][dir_name] = [
                    p_nyquist.scatter(x='realvalues', y='imaginaryvalues', source=self.cell_source, view=view, size=7, color=dir_colors[dir_name], legend_label=dir_name),       
                    [
                        # p_bode.scatter(x='frequencies', y='magnitude', source=self.cell_source, view=view, size=7, color=dir_colors[dir_name], legend_label=dir_name + ": Magnitude"), 
                        p_bode.scatter(x='frequencies', y='magnitude', source=self.cell_source, view=view, size=7, color=dir_colors[dir_name], legend_label=dir_name), 
                        # p_bode.line(x='frequencies', y='magnitude', source=self.cell_source, view=view, color=dir_colors[dir_name], legend_label=dir_name), 
                        # p_bode.triangle(x='frequencies', y='phase_angle', source=self.cell_source, view=view, size=7, y_range_name="phase", color=dir_colors[dir_name], legend_label=dir_name + ": Phase angle")
                        p_bode.scatter(x='frequencies', y='phase_angle', source=self.cell_source, view=view, size=7, y_range_name="phase", line_color=dir_colors[dir_name], fill_color='black', fill_alpha = 0)
                        # p_bode.line(x='frequencies', y='phase_angle', source=self.cell_source, view=view, line_dash='dashed', y_range_name="phase", color=dir_colors[dir_name], legend_label=dir_name)
                    ],
                    p_Z_pred.scatter(x='frequencies', y='imaginaryvalues', source=self.cell_source, view=view, size=7, color=dir_colors[dir_name], legend_label=dir_name),
                    p_Z_pred_nyquist.scatter(x='realvalues', y='imaginaryvalues', source=self.cell_source, view=view, size=7, color=dir_colors[dir_name], legend_label=dir_name)
                ]


                if not self.Z_pred_df.empty:
                    # In order to only plot the impedances related to this spesific cell
                    filtered_df              = self.Z_pred_df[(self.Z_pred_df['cell_name'] == cell_name) & (self.Z_pred_df['dir_name'] == dir_name)]
                    filtered_Z_pred_source      = ColumnDataSource(data = {})
                    filtered_Z_pred_source.data = {col_name : filtered_df[col_name].tolist() for col_name in filtered_df.columns}

                    Z_pred_filt, temp_filt_within_range, temp_filt_outside_range                 = create_Z_pred_filter(self, filtered_Z_pred_source, cell_name, dir_name)
                    view_Z_pred                 = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name) 
                                                        & GroupFilter(column_name="dir_name", group=dir_name)
                                                        & Z_pred_filt)
                    view_Z_pred_within                 = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name) 
                                                        & GroupFilter(column_name="dir_name", group=dir_name)
                                                        & Z_pred_filt
                                                        & temp_filt_within_range)
                    view_Z_pred_outside                 = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name) 
                                                        & GroupFilter(column_name="dir_name", group=dir_name)
                                                        & Z_pred_filt
                                                        & temp_filt_outside_range)
                    
                    
                    # Varea for plotting error                    
                    varea_x = filtered_df['freq_vec_star'].tolist()
                    varea_y_lower = filtered_df['error_lower'].tolist()
                    varea_y_upper = filtered_df['error_upper'].tolist()


                    self.Z_pred_imag_plots[cell_name][dir_name] = [
                        p_Z_pred.line(x='freq_vec_star', y='Z_im_vec_star', source=filtered_Z_pred_source, view=view_Z_pred, line_width=2, color=dir_colors[dir_name], line_dash='dashed'),
                        p_Z_pred.varea(x=varea_x, y1=varea_y_lower, y2=varea_y_upper, fill_color="gray", fill_alpha = 0.3)
                    ]
                    
                    # To make the elements show up in the correct order 
                    Z_pred_renderers_points_list.append(self.cell_plots[cell_name][dir_name][2])
                    Z_pred_renderers_lines_list.append(self.Z_pred_imag_plots[cell_name][dir_name][0])
                    Z_pred_renderers_varea_list.append(self.Z_pred_imag_plots[cell_name][dir_name][1])

                    self.Z_pred_plots[cell_name][dir_name] = [
                        p_Z_pred_nyquist.scatter(x='Z_re_vec_star', y='Z_im_vec_star', source=filtered_Z_pred_source, view=view_Z_pred_within, size=7, line_color='darkgrey', fill_color='black', fill_alpha = 0),
                        p_Z_pred_nyquist.scatter(x='Z_re_vec_star', y='Z_im_vec_star', source=filtered_Z_pred_source, view=view_Z_pred_outside, size=7, line_color=dir_colors[dir_name], fill_color='black', fill_alpha = 0)
                    ]

                    self.filtered_Z_pred_sources.append(filtered_Z_pred_source)
            if not self.circuit_df.empty:
                # # Add the fitted impedance to the nyquist- and bode-plots
                self.circuit_plots[cell_name] = {}
                self.impedance_from_fitting_plots[cell_name] = {}
                
                # Iterate trhough dirs aswell
                dir_names = self.circuit_df['dir_name'].unique().tolist()
                for dir_name in dir_names:

                    # In order to only plot the impedances related to this spesific cell
                    filtered_df             = self.impedance_from_fitting_df[(self.impedance_from_fitting_df['cell_name'] == cell_name) & (self.impedance_from_fitting_df['dir_name'] == dir_name)]
                    filtered_imp_source         = ColumnDataSource(data = {})
                    filtered_imp_source.data = {col_name : filtered_df[col_name].tolist() for col_name in filtered_df.columns}

                    impedance_filt = filter_fitted_impedance(self, filtered_imp_source)
                    impedance_view =  CDSView(filter=impedance_filt) # Filter for the glyphs in the Nyquist- and Bode-plots 
                    # Adding the impedances from the circuit-fitting       
                    self.impedance_from_fitting_plots[cell_name][dir_name] = [
                        p_nyquist.line(x='impedance_real', y='impedance_imag', source=filtered_imp_source, view = impedance_view, color=dir_colors[dir_name], line_width=2, line_dash='dashed'),
                        [
                        # p_bode.scatter(x='frequencies', y='magnitude', source=filtered_imp_source, view=impedance_view, size=7, color=dir_colors[dir_name], legend_label=cell_name), 
                        p_bode.line(x='frequencies', y='magnitude', source=filtered_imp_source, view=impedance_view, color=dir_colors[dir_name]), 
                        # p_bode.triangle(x='frequencies', y='phase_angle', source=filtered_imp_source, view=impedance_view, size=7, y_range_name="phase", color=dir_colors[dir_name], legend_label=cell_name), 
                        p_bode.line(x='frequencies', y='phase_angle', source=filtered_imp_source, view=impedance_view, line_dash='dashed', y_range_name="phase", color=dir_colors[dir_name])
                        ]
                    ]
                    self.filtered_impedance_sources.append(filtered_imp_source) # To be able to show and hide the glyph. See the js_on_change callback in dashboard_for_plotting_and_fitting

                    resistance_plots    = {}
                    capacitance_plots   = {}
                    time_plots          = {} 

                    # Filters for the other plots
                    resistance_view         = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name)
                                                        & GroupFilter(column_name='dir_name', group=dir_name)) # Add additional filter here?
                    capacitance_view        = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name)
                                                        & GroupFilter(column_name='dir_name', group=dir_name)) # Add additional filter here?
                    time_view               = CDSView(filter=GroupFilter(column_name="cell_name", group=cell_name)
                                                        & GroupFilter(column_name='dir_name', group=dir_name)) # Add additional filter here?

                    # In order to only plot the whiskers related to this spesific cell
                    filtered_df             = self.circuit_df[(self.circuit_df['cell_name'] == cell_name) & (self.circuit_df['dir_name'] == dir_name)]
                    filtered_source         = ColumnDataSource(data={})
                    filtered_source.data    = {col_name : filtered_df[col_name].tolist() for col_name in filtered_df.columns}

                    for base_variable in self.circuit_base_variables:
                        # If base variable is related to resistance -> append to resistance-plot
                        if base_variable in self.RESISTANCE_SELECTOR_LABEL:
                            error = None
                            # Error bars
                            for std_dev_var in self.resistance_std_deviations:
                                if std_dev_var[4:] == base_variable:
                                    error = Whisker(base='hours_since_first_date', upper=std_dev_var + '_upper', lower=std_dev_var + '_lower', 
                                                    source=filtered_source,
                                                    level="annotation", line_width=1,
                                                    line_color=resistance_colors[base_variable])  

                                    error.upper_head.line_color=resistance_colors[base_variable]
                                    error.lower_head.line_color=resistance_colors[base_variable]
                                    error.upper_head.size=10
                                    error.lower_head.size=10
                                    # error.visible = False
                                    p_resistance.add_layout(error)
                                    # error = error

                            if base_variable == 'TotR':
                                error = Whisker(base='hours_since_first_date', upper=base_variable + '_upper', lower=base_variable + '_lower', 
                                                source=filtered_source,
                                                level="annotation", line_width=1,
                                                line_color=resistance_colors[base_variable])  
                                error.upper_head.line_color=resistance_colors[base_variable]
                                error.lower_head.line_color=resistance_colors[base_variable]
                                error.upper_head.size=10
                                error.lower_head.size=10
                                p_resistance.add_layout(error)

                            # Glyph with the resistance-value
                            resistance_plots[base_variable] = [
                                p_resistance.scatter(x='hours_since_first_date', y=base_variable, source=self.circuit_source, view=resistance_view, size=7, color=resistance_colors[base_variable], legend_label=base_variable), 
                                error
                            ]

                        # If base variable is related to capacitance -> append to capacitance-plot
                        elif base_variable in self.capacitance_selector_LABEL:
                            error = None
                            # Error bars
                            for std_dev_var in self.capacitance_std_deviations:
                                if std_dev_var[4:] == base_variable:
                                    error = Whisker(base='hours_since_first_date', upper=std_dev_var + '_upper', lower=std_dev_var + '_lower', source=filtered_source,
                                                    line_width=1, 
                                                    line_color=capacitance_colors[base_variable]) 
                                    error.upper_head.line_color=capacitance_colors[base_variable]
                                    error.lower_head.line_color=capacitance_colors[base_variable]
                                    error.upper_head.size=10
                                    error.lower_head.size=10
                                    p_capacitance.add_layout(error)
                                    # error = error
                            if base_variable == 'TotC': 
                                error = Whisker(base='hours_since_first_date', upper=base_variable + '_upper', lower=base_variable + '_lower', source=filtered_source,
                                                level="annotation", line_width=1, 
                                                line_color=capacitance_colors[base_variable]) 
                                error.upper_head.line_color=capacitance_colors[base_variable]
                                error.lower_head.line_color=capacitance_colors[base_variable]
                                error.upper_head.size=10
                                error.lower_head.size=10
                                p_capacitance.add_layout(error)

                            # Glyph with the capasitance-value
                            capacitance_plots[base_variable] = [
                                p_capacitance.scatter(x='hours_since_first_date', y=base_variable, source=self.circuit_source, view=capacitance_view, size=7, color=capacitance_colors[base_variable], legend_label=base_variable),
                                error
                            ]

                        # If base variable is related to time -> append to time-plot
                        elif base_variable in self.TIME_SELECTOR_LABEL:
                            time_plots[base_variable] = []
                            time_plots[base_variable] = p_time.scatter(x='hours_since_first_date', y='char_freq' + base_variable[-1], source=self.circuit_source, view=time_view, size=7, color=time_colors[base_variable], legend_label="f_char " + base_variable[-1])
                    self.circuit_plots[cell_name][dir_name] = []
                    self.circuit_plots[cell_name][dir_name].append(resistance_plots)
                    self.circuit_plots[cell_name][dir_name].append(capacitance_plots)
                    self.circuit_plots[cell_name][dir_name].append(time_plots)

                    
            #Here we make both the DRT plot and the Im(Z) plot for evaluating the reliabaility of the model
            if not self.DRT_df.empty:
                DRT_time_plots = {}
                DRT_model_eval_plots = {}
                DRT_nyquist_plots = {}
                dir_names = self.DRT_df['dir_name'].unique().tolist()
                
                # # Creating a color-scheme
                # DRT_colors = {}
                # for i, dir_name in enumerate(dir_names):
                #     DRT_colors[dir_name] = Viridis256[1 + i*int(256/len(dir_names))]

                for dir_name in dir_names:
                    filtered_df             = self.DRT_df[(self.DRT_df['cell_name'] == cell_name) & (self.DRT_df['dir_name'] == dir_name)]
                    filtered_source         = ColumnDataSource(data={})
                    filtered_source.data    = {col_name : filtered_df[col_name].tolist() for col_name in filtered_df.columns}

                    # Varea for plotting error                    
                    varea_x = filtered_df['freq_vec_star'].tolist()
                    sigma_gamma = np.asarray(filtered_df["Sigma_gamma_vec_star"].tolist())
                    gamma_vec = np.asarray(filtered_df["gamma_vec_star"].tolist())
                    varea_y_lower = gamma_vec - 3*np.sqrt(abs(sigma_gamma))
                    varea_y_upper = gamma_vec + 3*np.sqrt(abs(sigma_gamma))
                    DRT_time_plots[dir_name] = [
                        p_DRT.varea(x=varea_x, y1=varea_y_lower, y2=varea_y_upper, fill_color="gray", fill_alpha = 0.3),
                        # p_DRT.line('freq_vec_star','gamma_vec_star', source=filtered_source, line_width=4, color=cell_color, legend_label=dir_name)
                        p_DRT.line('freq_vec_star','gamma_vec_star', source=filtered_source, line_width=4, color=dir_colors[dir_name], legend_label=dir_name)
                    ]
                    freq_vec = self.df.loc[(self.df["dir_name"] == dir_name) & (self.df['cell_name'] == cell_name), 'frequencies'].tolist()
                    exp_data = self.df.loc[(self.df["dir_name"] == dir_name) & (self.df["cell_name"] == cell_name) ,"imaginaryvalues"].tolist()
                    DRT_model_eval_plots[dir_name] = [
                        p_model_eval.line('freq_vec_star', 'Z_imag_star', source=filtered_source, line_width=4, color=dir_colors[dir_name], legend_label=dir_name),
                        p_model_eval.scatter(x=freq_vec, y=exp_data, color=dir_colors[dir_name], size=7, legend_label=dir_name)
                    ]
                    Z_real = self.df.loc[(self.df["dir_name"] == dir_name) & (self.df['cell_name'] == cell_name), 'realvalues'].tolist()
                    DRT_nyquist_plots[dir_name] = [
                        p_model_nyquist.line('Z_real_star', 'Z_imag_star', source=filtered_source, line_width=4, color=dir_colors[dir_name], legend_label=dir_name),
                        p_model_nyquist.scatter(x=Z_real, y=exp_data, size=7, color=dir_colors[dir_name], legend_label=dir_name)
                    ]

                    renderers_lines_list.append(DRT_time_plots[dir_name][1])
                    renderers_varea_list.append(DRT_time_plots[dir_name][0])

                    modeval_renderers_scatter_list.append(DRT_model_eval_plots[dir_name][1])
                    modeval_renderers_lines_list.append(DRT_model_eval_plots[dir_name][0])
                    
                    modnyq_renderers_lines_list.append(DRT_nyquist_plots[dir_name][0])
                    modnyq_renderers_scatter_list.append(DRT_nyquist_plots[dir_name][1])


                self.DRT_plots[cell_name] = DRT_time_plots
                self.modeval_plots[cell_name] = DRT_model_eval_plots
                self.modnyq_plots[cell_name] = DRT_nyquist_plots
        
        

        # Adding an empty element to the nyquist-plot that will be the legend item for all the Impedances calculated from the circuit-fit
        # Not the data that is plotted is not of importance, since it always will be hidden


        if not self.circuit_df.empty:
            label_elem = p_nyquist.line(x='impedance_real', y='impedance_imag', source=self.impedance_from_fitting_source, color='darkgrey', line_width=2, line_dash='dashed', legend_label="Circuit fit")
            label_elem.visible = False
            label_elem2 = p_bode.line(x='frequencies', y='magnitude', source=self.impedance_from_fitting_source, color='darkgrey', line_width=2, legend_label="Circuit fit: Magnitude")
            label_elem2.visible = False
            label_elem3 = p_bode.line(x='frequencies', y='phase_angle', source=self.impedance_from_fitting_source, line_dash='dashed', color='darkgrey', line_width=2, legend_label="Circuit fit: Phase angle")
            label_elem3.visible = False
        label_elem4 = p_bode.scatter(x='frequencies', y='magnitude', source=self.cell_source, view=view, size=7, color='darkgrey', legend_label='Magnitude')
        label_elem4.visible = False
        label_elem5 = p_bode.scatter(x='frequencies', y='phase_angle', source=self.cell_source, view=view, size=7, y_range_name="phase", line_color='darkgrey', fill_color='black', fill_alpha = 0, legend_label='Phase angle')
        label_elem5.visible = False
        if not self.Z_pred_df.empty:
            label_elem6 = p_Z_pred_nyquist.scatter(x='Z_re_vec_star', y='Z_im_vec_star', source=filtered_Z_pred_source, size=7, line_color='darkgrey', fill_color='black', fill_alpha = 0, legend_label='Predicted Z')
            label_elem6.visible = False
            label_elem7 = p_Z_pred.line(x='freq_vec_star', y='Z_im_vec_star', source=filtered_Z_pred_source, line_width=2, color='darkgrey', line_dash='dashed', legend_label='Predicted Z')
            label_elem7.visible = False

        # Set the stacking order so that the varea is moved behind the (more important) line plots
        renderers_list = renderers_varea_list + renderers_lines_list
        p_DRT.renderers = renderers_list
        modeval_renderers_list = modeval_renderers_scatter_list + modeval_renderers_lines_list
        p_model_eval.renderers = modeval_renderers_list
        modnyq_renderers_list = modnyq_renderers_scatter_list + modnyq_renderers_lines_list
        p_model_nyquist.renderers = modnyq_renderers_list
        Z_pred_renderers_list = Z_pred_renderers_varea_list + Z_pred_renderers_lines_list + Z_pred_renderers_points_list
        p_Z_pred.renderers = Z_pred_renderers_list

                                                          
def plot_settings(currentplot, p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist):
    '''
    Settings for the appearance of the plots, and also where the axes of the plots gets the correct scaling.
    '''
    ### The Nyquist-plot ###
    p_nyquist.xaxis.axis_label_text_font_size           = "20pt"
    p_nyquist.xaxis.major_label_text_font_size          = "14pt"
    p_nyquist.yaxis.axis_label_text_font_size           = "20pt"
    p_nyquist.yaxis.major_label_text_font_size          = "14pt"
    p_nyquist.legend.location                           = "top_right"
    # Vertical line
    vline                                               = Span(location=0, dimension='height', line_color='black', line_width=1.5)
    # Horizontal line
    hline                                               = Span(location=0, dimension='width', line_color='black', line_width=1.5)
    p_nyquist.renderers.extend([vline,hline])
    # Add a HoverTool that makes it possible to see the values
    p_nyquist.add_tools(HoverTool(tooltips = [("(Re(Z), -Im(Z))","($x,$y)")]))


    # Scaling axes based on area_str used when normalizing
    p_nyquist.xaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 
    p_nyquist.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 


    # Impedance-fitting plot
    p_Z_pred.xaxis.axis_label_text_font_size           = "20pt"
    p_Z_pred.xaxis.major_label_text_font_size          = "14pt"
    p_Z_pred.yaxis.axis_label_text_font_size           = "20pt"
    p_Z_pred.yaxis.major_label_text_font_size          = "14pt"
    p_Z_pred.legend.location                           = "top_right"
    p_Z_pred.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 
    # Vertical line
    vline                                               = Span(location=0, dimension='height', line_color='black', line_width=1.5)
    # Horizontal line
    hline                                               = Span(location=0, dimension='width', line_color='black', line_width=1.5)
    p_Z_pred.renderers.extend([vline,hline])
    # Add a HoverTool that makes it possible to see the values
    p_Z_pred.add_tools(HoverTool(tooltips = [("(freq, -Im(Z))","($x,$y)")]))
    p_Z_pred.y_range                                      = Range1d(currentplot.df['imaginaryvalues'].min() * 0.9, currentplot.df['imaginaryvalues'].max()* 1.1)


    ### Impedance-fitting Nyquist plot ###
    p_Z_pred_nyquist.xaxis.axis_label_text_font_size           = "20pt"
    p_Z_pred_nyquist.xaxis.major_label_text_font_size          = "14pt"
    p_Z_pred_nyquist.yaxis.axis_label_text_font_size           = "20pt"
    p_Z_pred_nyquist.yaxis.major_label_text_font_size          = "14pt"
    p_Z_pred_nyquist.legend.location                           = "top_right"
    # Vertical line
    vline                                               = Span(location=0, dimension='height', line_color='black', line_width=1.5)
    # Horizontal line
    hline                                               = Span(location=0, dimension='width', line_color='black', line_width=1.5)
    p_Z_pred_nyquist.renderers.extend([vline,hline])
    # Add a HoverTool that makes it possible to see the values
    p_Z_pred_nyquist.add_tools(HoverTool(tooltips = [("(Re(Z), -Im(Z))","($x,$y)")]))


    ### The Bode-plot ###
    p_bode.y_range                                      = Range1d(currentplot.df['magnitude'].min() * 0.9, currentplot.df['magnitude'].max()* 1.1)
    
    if currentplot.normalized_bool == True:
        # Add correct axis-labels
        p_nyquist.xaxis.axis_label                          = f"Re(Z / \u03A9 {currentplot.interface.area_str[:-2]}\u00b2)"
        p_nyquist.yaxis.axis_label                          = f"-Im(Z / \u03A9 {currentplot.interface.area_str[:-2]}\u00b2)"
        p_bode.yaxis.axis_label                             = f"|Z| / \u03A9 {currentplot.interface.area_str[:-2]}\u00b2"
    
    # Extra axis on bode-plot
    p_bode.extra_y_ranges                               = {"phase": Range1d(start=currentplot.df['phase_angle'].min() * 0.9, end=currentplot.df['phase_angle'].max() * 1.1)}
    p_bode.add_layout(LinearAxis(y_range_name="phase",  axis_label="\u03C6 / \u00b0"), 'right')

    p_bode.xaxis.axis_label_text_font_size              = "20pt"
    p_bode.xaxis.major_label_text_font_size             = "14pt"
    p_bode.yaxis.axis_label_text_font_size              = "20pt"
    p_bode.yaxis.major_label_text_font_size             = "14pt"
    p_bode.legend.location                              = "top_right"
    p_bode.add_tools(HoverTool(tooltips = [("(freq, |Z| or \u03C6)","($x,$y)")]))

    p_bode.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 
    

    if not currentplot.circuit_df.empty:
        ### p_resistance-settings ###
        p_resistance.xaxis.axis_label_text_font_size    = "20pt"
        p_resistance.xaxis.major_label_text_font_size   = "14pt"
        p_resistance.yaxis.axis_label_text_font_size    = "20pt"
        p_resistance.yaxis.major_label_text_font_size   = "14pt"
        p_resistance.legend.location                    = "top_right"

        axis_scale_multiplier = 1
        if currentplot.interface.display_res_in_milli == True:
            p_resistance.add_tools(HoverTool(tooltips = [("(Hrs, m\u03A9cm\u00b2)","($x,$y)")]))
            axis_scale_multiplier = 1000
        else:
            p_resistance.add_tools(HoverTool(tooltips = [("(Hrs, \u03A9cm\u00b2)","($x,$y)")]))

        # For plotting in milliOhms
        # p_resistance.yaxis.formatter = CustomJSTickFormatter(code="return Math.round(tick * 1000 * 1000) / 1000") # Change to f.ex. 100 / 100 if you want to round to 2 decimal places
        p_resistance.yaxis.formatter                    = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals, axis_scale_multiplier = axis_scale_multiplier),
            # Multiply by 1000 to convert to milliohm, multiply by area_str_value*area_str_value to convert from m^2
            # The last multiplication and division is to get the correct roundoff for the tics
            code="return ((tick * axis_scale_multiplier) * (area_str_value*area_str_value)).toFixed(decimals)") 


        ### p_capacitance-settings ###
        p_capacitance.xaxis.axis_label_text_font_size   = "20pt"
        p_capacitance.xaxis.major_label_text_font_size  = "14pt"
        p_capacitance.yaxis.axis_label_text_font_size   = "20pt"
        p_capacitance.yaxis.major_label_text_font_size  = "14pt"
        p_capacitance.legend.location                   = "top_right"

        axis_scale_multiplier = 1
        if currentplot.interface.display_cap_in_milli == True:
            p_capacitance.add_tools(HoverTool(tooltips = [("(Hrs, mF/cm\u00b2)","($x,$y)")]))
            axis_scale_multiplier = 1000
        else:
            p_capacitance.add_tools(HoverTool(tooltips = [("(Hrs, F/cm\u00b2)","($x,$y)")]))
        

        # For plotting in milliFarad
        # p_capacitance.yaxis.formatter = CustomJSTickFormatter(code="return Math.round(tick * 1000 * 1000) / 1000") # Change to f.ex. 100 / 100 if you want to round to 2 decimal places
        p_capacitance.yaxis.formatter                   = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals, axis_scale_multiplier = axis_scale_multiplier),
            # Multiply by 1000 to convert to milliohm, divide by area_str_value*area_str_value to convert from  m^-2
            # The last multiplication and division is to get the correct roundoff for the tics
            code="return ((tick * axis_scale_multiplier) / (area_str_value*area_str_value)).toFixed(decimals)") 
        ### p_time-settings ###
        p_time.xaxis.axis_label_text_font_size          = "20pt"
        p_time.xaxis.major_label_text_font_size         = "14pt"
        p_time.yaxis.axis_label_text_font_size          = "20pt"
        p_time.yaxis.major_label_text_font_size         = "14pt"
        p_time.legend.location                          = "top_right"
        p_capacitance.add_tools(HoverTool(tooltips = [("(Hrs, f_char)","($x,$y)")]))

        if currentplot.normalized_bool == True:
            # Add correct axis-labels
            if currentplot.interface.display_res_in_milli == True:
                p_resistance.yaxis.axis_label                   = f"m\u03A9 {currentplot.interface.area_str[:-2]}\u00b2"
            else: 
                p_resistance.yaxis.axis_label                   = f"\u03A9 {currentplot.interface.area_str[:-2]}\u00b2"
            if currentplot.interface.display_cap_in_milli == True:
                p_capacitance.yaxis.axis_label                  = f"mF / {currentplot.interface.area_str[:-2]}\u00b2"
            else:
                p_capacitance.yaxis.axis_label                  = f"F / {currentplot.interface.area_str[:-2]}\u00b2"
        else: 
            if currentplot.interface.display_res_in_milli == True:
                p_resistance.yaxis.axis_label                   = f"m\u03A9"
            if currentplot.interface.display_cap_in_milli == True:
                p_capacitance.yaxis.axis_label                  = f"mF"


    if not currentplot.DRT_df.empty:
        ### The DRT-plot ###
        p_DRT.xaxis.axis_label_text_font_size           = "20pt"
        p_DRT.xaxis.major_label_text_font_size          = "14pt"
        p_DRT.yaxis.axis_label_text_font_size           = "20pt"        
        p_DRT.yaxis.major_label_text_font_size          = "14pt"
        p_DRT.legend.location                           = "top_right"

        p_DRT.y_range.start                             = currentplot.DRT_df['gamma_vec_star'].min()*1.3
        p_DRT.y_range.end                               = currentplot.DRT_df['gamma_vec_star'].max()*1.4

        # For plotting in milliOhms
        p_DRT.yaxis.formatter                           = CustomJSTickFormatter(code="return tick") 
        
        p_DRT.add_tools(HoverTool(tooltips = [(f"(f, \u03B3","($x,$y)")]))
        
        p_DRT.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 

        if currentplot.normalized_bool == True: #so far normalizing does not work for DRT
            # Add correct axis-labels
            p_DRT.yaxis.axis_label                          = f"\u03B3/\u03A9 {currentplot.interface.area_str[:-2]}\u00b2"

        ### The Z.imag prediction for evaluation ###
        p_model_eval.xaxis.axis_label_text_font_size           = "20pt"
        p_model_eval.xaxis.major_label_text_font_size          = "14pt"
        p_model_eval.yaxis.axis_label_text_font_size           = "20pt"        
        p_model_eval.yaxis.major_label_text_font_size          = "14pt"
        p_model_eval.legend.location                           = "top_right"

        p_model_eval.y_range.start                             = currentplot.DRT_df['Z_imag_star'].min()*1.1
        p_model_eval.y_range.end                               = currentplot.DRT_df['Z_imag_star'].max()*1.3

        # For plotting in milliOhms
        p_model_eval.yaxis.formatter                           = CustomJSTickFormatter(code="return tick") 
        
        p_model_eval.add_tools(HoverTool(tooltips = [(f"(f, Im(Z)","($x,$y)")]))
        
        p_model_eval.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 

        p_model_nyquist
        p_model_nyquist.xaxis.axis_label_text_font_size           = "20pt"
        p_model_nyquist.xaxis.major_label_text_font_size          = "14pt"
        p_model_nyquist.yaxis.axis_label_text_font_size           = "20pt"        
        p_model_nyquist.yaxis.major_label_text_font_size          = "14pt"
        p_model_nyquist.legend.location                           = "top_right"

        p_model_nyquist.y_range.start                             = currentplot.DRT_df['Z_imag_star'].min()*0.9
        p_model_nyquist.y_range.end                               = currentplot.DRT_df['Z_imag_star'].max()*1.3

        # For plotting in milliOhms
        # p_model_nyquist.yaxis.formatter                           = CustomJSTickFormatter(code="return tick") 
        
        p_model_nyquist.add_tools(HoverTool(tooltips = [(f"(Re(Z), Im(Z)","($x,$y)")]))
        
        p_model_nyquist.yaxis.formatter = CustomJSTickFormatter(args=dict(area_str_value = currentplot.area_str_value, decimals = currentplot.axes_roundoff_decimals),
            code="return ((tick) / (area_str_value*area_str_value)).toFixed(decimals)") 

def create_layout(
        currentplot, p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist, area_size, area_string
    ):
    '''
    Creating the layout of the interface, and making sure to only display the relevant tabs.
    '''


    # Tabs for switching between the Nyquist- and the Bode-plot
    tab_nyquist                 = TabPanel(child=p_nyquist,title="Nyquist plot")
    tab_bode                    = TabPanel(child=p_bode,title="Bode plot")
    tab_p_resistance            = TabPanel(child=p_resistance,title="Resistance")
    tab_p_capacitance           = TabPanel(child=p_capacitance,title="Capacitance")
    tab_p_time                  = TabPanel(child=p_time,title="Characteristic frequency")
    tab_p_DRT                   = TabPanel(child=p_DRT,title="DRT")
    tab_p_modeval               = TabPanel(child=p_model_eval,title="Z.imag of model")
    tab_p_model_nyquist         = TabPanel(child=p_model_nyquist,title="Nyquist of model")
    tab_p_Z_pred                = TabPanel(child=p_Z_pred,title="Predicted Z.imag")
    tab_p_Z_pred_nyquist        = TabPanel(child=p_Z_pred_nyquist,title="Predicted Nyquist")

    header                      = Div(text="""EIS: Plot and fit data""", styles={'font-size': '36pt'}, width=1400, height=60)
    if currentplot.normalized_bool == True:
        normalization_text      = "Normalization settings: Area size = " + str(area_size) +". Area string = " + str(area_string[:-2]) + "\u00b2."
    else: 
        normalization_text      = 'No normalization'
    normalization_info_label    = Div(text=normalization_text, styles={'font-size': '16pt'}, width=1400, height=30)
    date_selector_label         = Div(text="""Date-range:""", styles={'font-size': '16pt'}, width=300, height=30)
    if (currentplot.date_selector.visible == False): # Hide the date-selector-label is the slider also is hidden
        date_selector_label.visible = False

    temperature_selector_label  = Div(text="""Temperature:""", styles={'font-size': '16pt'}, width=300, height=30)
    pressure_selector_label     = Div(text="""Pressure:""", styles={'font-size': '16pt'}, width=300, height=30)
    dc_current_selector_label   = Div(text="""DC current selector:""", styles={'font-size': '16pt'}, width=300, height=30)
    ac_current_selector_label   = Div(text="""AC current selector:""", styles={'font-size': '16pt'}, width=300, height=30)
    resistance_selector_label   = Div(text="""Resistance selector:""", styles={'font-size': '16pt'}, width=300, height=30)
    capacitance_selector_label  = Div(text="""Capacitance selector:""", styles={'font-size': '16pt'}, width=300, height=30)
    time_selector_label         = Div(text="""Char freq selector:""", styles={'font-size': '16pt'}, width=300, height=30)        
    hide_fitted_impedance_label = Div(text="""Impedances from fitted circuit:""", styles={'font-size': '16pt'}, width=300, height=30) 
    hide_prediction_error_label = Div(text="""Prediction errors:""", styles={'font-size': '16pt'}, width=300, height=30) 


    tabs_list = [tab_nyquist, tab_bode]
    if not currentplot.Z_pred_df.empty:       
        tabs_list.append(tab_p_Z_pred)
        tabs_list.append(tab_p_Z_pred_nyquist)

    if not currentplot.circuit_df.empty:       
        tabs_list.append(tab_p_resistance)
        tabs_list.append(tab_p_capacitance)
        tabs_list.append(tab_p_time)
    if not currentplot.DRT_df.empty:       
        tabs_list.append(tab_p_DRT)
        tabs_list.append(tab_p_modeval)
        tabs_list.append(tab_p_model_nyquist)
    tabs = Tabs(tabs=tabs_list)
    
    if not currentplot.circuit_df.empty:
        if not currentplot.Z_pred_df.empty:
            columns = column(
                            normalization_info_label,
                            date_selector_label,
                            currentplot.date_selector,
                            temperature_selector_label,
                            currentplot.temperature_selector,
                            pressure_selector_label,
                            currentplot.pressure_selector,
                            dc_current_selector_label,
                            currentplot.dc_current_selector,
                            ac_current_selector_label,
                            currentplot.ac_current_selector,
                            resistance_selector_label,
                            currentplot.resistance_selector,
                            capacitance_selector_label,
                            currentplot.capacitance_selector,
                            time_selector_label,
                            currentplot.time_selector,
                            hide_fitted_impedance_label,
                            currentplot.hide_fitted_impedance,
                            row(hide_prediction_error_label,currentplot.hide_prediction_error)
                        )
        else:
            columns = column(
                            normalization_info_label,
                            date_selector_label,
                            currentplot.date_selector,
                            temperature_selector_label,
                            currentplot.temperature_selector,
                            pressure_selector_label,
                            currentplot.pressure_selector,
                            dc_current_selector_label,
                            currentplot.dc_current_selector,
                            ac_current_selector_label,
                            currentplot.ac_current_selector,
                            resistance_selector_label,
                            currentplot.resistance_selector,
                            capacitance_selector_label,
                            currentplot.capacitance_selector,
                            time_selector_label,
                            currentplot.time_selector,
                            hide_fitted_impedance_label,
                            currentplot.hide_fitted_impedance
                        )

        
    else:
        if not currentplot.Z_pred_df.empty:
            columns = column(
                            normalization_info_label,
                            date_selector_label,
                            currentplot.date_selector,
                            temperature_selector_label,
                            currentplot.temperature_selector,
                            pressure_selector_label,
                            currentplot.pressure_selector,
                            dc_current_selector_label,
                            currentplot.dc_current_selector,
                            ac_current_selector_label,
                            currentplot.ac_current_selector,
                            row(hide_prediction_error_label,currentplot.hide_prediction_error)
                        )
        else:
            columns = column(
                            normalization_info_label,
                            date_selector_label,
                            currentplot.date_selector,
                            temperature_selector_label,
                            currentplot.temperature_selector,
                            pressure_selector_label,
                            currentplot.pressure_selector,
                            dc_current_selector_label,
                            currentplot.dc_current_selector,
                            ac_current_selector_label,
                            currentplot.ac_current_selector
                        )

    lay_out = layout(
            column(
                header, 
                # currentplot.rescan_button, 
                currentplot.cell_selector,
                row(
                    tabs,
                    columns
                )
            )
        )
    return lay_out


def create_filter(currentplot):
    '''
    Filter for hiding some of the glyphs based on selections. Could maybe have been integrated as a callback instead, but works fine.
    '''
    filt = CustomJSFilter(args=dict(
        src                     = currentplot.cell_source,
        temperature_selector    = currentplot.temperature_selector,
        pressure_selector       = currentplot.pressure_selector,
        dc_selector             = currentplot.dc_current_selector,
        ac_selector             = currentplot.ac_current_selector
        ), 
        code = '''    
        var temperature_selector_dict = {};
        var tempArray = src.data['temp'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            temperature_selector_dict[i] = x;
        }
        var pressure_selector_dict = {};
        var tempArray = src.data['pressure'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            pressure_selector_dict[i] = x;
        }
        var dc_selector_dict = {};
        var tempArray = src.data['dc'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            dc_selector_dict[i] = x;
        }
        var ac_selector_dict = {};
        var tempArray = src.data['ac'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            ac_selector_dict[i] = x;
        }
        const temperature_selector_active = temperature_selector.active.map(x=>temperature_selector_dict[x]);
        const pressure_selector_active = pressure_selector.active.map(x=>pressure_selector_dict[x]);
        const dc_selector_active = dc_selector.active.map(x=>dc_selector_dict[x]);
        const ac_selector_active = ac_selector.active.map(x=>ac_selector_dict[x]);
        const sel_indices = [];
        for (let i = 0; i < src.get_length(); i++){
            if (
                temperature_selector_active.includes(src.data['temp'][i]) 
                && pressure_selector_active.includes(src.data['pressure'][i])
                && dc_selector_active.includes(src.data['dc'][i])
                && ac_selector_active.includes(src.data['ac'][i])
            ) {
                sel_indices.push(true);
            } else {
                sel_indices.push(false);
            }
        }
        return sel_indices;
        '''                  
    )    
    return filt


def create_Z_pred_filter(currentplot, temp_source, temp_cell_name, temp_dir_name):
    '''
    Filters for hiding some of the predicted impedances based on selections.
    Multiple filters gets created to acchieve different appearances for the interpolated and exerpolated impedances.
    '''
    filt = CustomJSFilter(args=dict(
        src                     = temp_source,
        temperature_selector    = currentplot.temperature_selector,
        pressure_selector       = currentplot.pressure_selector,
        dc_selector             = currentplot.dc_current_selector,
        ac_selector             = currentplot.ac_current_selector
        ), 
        code = '''    
        var temperature_selector_dict = {};
        var tempArray = src.data['temp'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            temperature_selector_dict[i] = x;
        }
        var pressure_selector_dict = {};
        var tempArray = src.data['pressure'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            pressure_selector_dict[i] = x;
        }
        var dc_selector_dict = {};
        var tempArray = src.data['dc'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            dc_selector_dict[i] = x;
        }
        var ac_selector_dict = {};
        var tempArray = src.data['ac'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            ac_selector_dict[i] = x;
        }
        const temperature_selector_active = temperature_selector.active.map(x=>temperature_selector_dict[x]);
        const pressure_selector_active = pressure_selector.active.map(x=>pressure_selector_dict[x]);
        const dc_selector_active = dc_selector.active.map(x=>dc_selector_dict[x]);
        const ac_selector_active = ac_selector.active.map(x=>ac_selector_dict[x]);
        const sel_indices = [];
        for (let i = 0; i < src.get_length(); i++){
            if (
                temperature_selector_active.includes(src.data['temp'][i]) 
                && pressure_selector_active.includes(src.data['pressure'][i])
                && dc_selector_active.includes(src.data['dc'][i])
                && ac_selector_active.includes(src.data['ac'][i])
            ) {
                sel_indices.push(true);
            } else {
                sel_indices.push(false);
            }
        }
        return sel_indices;
        '''                  
    )    

    temp_freqs_list = currentplot.df.loc[(currentplot.df["dir_name"] == temp_dir_name) & (currentplot.df['cell_name'] == temp_cell_name), 'frequencies'].values
    temp_freq_max = np.max(temp_freqs_list)
    temp_freq_min = np.min(temp_freqs_list)
    
    filt_within_freq_range = CustomJSFilter(args=dict(
        src                     = temp_source,
        freq_max                = temp_freq_max,
        freq_min                = temp_freq_min
        ), 
        code = '''    
        const sel_indices = [];
        for (let i = 0; i < src.length; i++) {
            const temp_freq = src.data['freq_vec_star'][i];
            if (temp_freq <= freq_max && temp_freq >= freq_min) {
                sel_indices.push(true);
            } else {
                sel_indices.push(false);
            }
        }
        return sel_indices;
        '''                  
    )

    filt_outside_freq_range = CustomJSFilter(args=dict(
        src                     = temp_source,
        freq_max                = temp_freq_max,
        freq_min                = temp_freq_min
        ), 
        code = '''    
        const sel_indices = [];
        for (let i = 0; i < src.length; i++) {
            const temp_freq = src.data['freq_vec_star'][i];
           if (temp_freq > freq_max || temp_freq < freq_min) {
                sel_indices.push(true);
            } else {
                sel_indices.push(false);
            }
        }
        return sel_indices;
        '''                  
    )

    return filt, filt_within_freq_range, filt_outside_freq_range


def filter_fitted_impedance(currentplot, filtered_source):
    '''
    Filter for hiding some of the circuit-fitted impedances based on selections. Could maybe have been integrated as a callback instead, but works fine.
    '''
    filt = CustomJSFilter(args=dict(
        imp_src                 = filtered_source,
        temperature_selector    = currentplot.temperature_selector,
        pressure_selector       = currentplot.pressure_selector,
        dc_selector             = currentplot.dc_current_selector,
        ac_selector             = currentplot.ac_current_selector
        ), 
        code = '''    
        var temperature_selector_dict = {};
        var tempArray = imp_src.data['temp'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            temperature_selector_dict[i] = x;
        }
        var pressure_selector_dict = {};
        var tempArray = imp_src.data['pressure'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            pressure_selector_dict[i] = x;
        }
        var dc_selector_dict = {};
        var tempArray = imp_src.data['dc'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            dc_selector_dict[i] = x;
        }
        var ac_selector_dict = {};
        var tempArray = imp_src.data['ac'];
        var uniqueTempArray = Array.from(new Set(tempArray)); // Get unique values of tempArray
        for (var i = 0; i < uniqueTempArray.length; i++) {
            var x = uniqueTempArray[i];
            ac_selector_dict[i] = x;
        }
        const temperature_selector_active = temperature_selector.active.map(x=>temperature_selector_dict[x]);
        const pressure_selector_active = pressure_selector.active.map(x=>pressure_selector_dict[x]);
        const dc_selector_active = dc_selector.active.map(x=>dc_selector_dict[x]);
        const ac_selector_active = ac_selector.active.map(x=>ac_selector_dict[x]);
        const sel_indices = [];
        for (let i = 0; i < imp_src.get_length(); i++){
            if (
                temperature_selector_active.includes(imp_src.data['temp'][i]) 
                && pressure_selector_active.includes(imp_src.data['pressure'][i])
                && dc_selector_active.includes(imp_src.data['dc'][i])
                && ac_selector_active.includes(imp_src.data['ac'][i])
            ) {
                sel_indices.push(true);
            } else {
                sel_indices.push(false);
            }
        }
        return sel_indices;
        '''                  
    )    
    return filt


def create_figures():
    '''
    Creating the plots/figures
    '''
    p_nyquist = figure(height = 800, width = 1200, x_axis_label=f"Re(Z / \u03A9)",
                y_axis_label=f"-Im(Z / \u03A9)", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000')
    # The Bode-plot
    p_bode = figure(height = 800, width = 1300, x_axis_label="f / Hz",
            y_axis_label=f"|Z| / \u03A9", outline_line_width = 1, outline_line_color = '#000000', x_axis_type="log")
    
    p_resistance = figure(height = 800, width = 1300, x_axis_label="Hours",
            y_axis_label=f"\u03A9", outline_line_width = 1, outline_line_color = '#000000', y_axis_type="log")
    p_capacitance = figure(height = 800, width = 1300, x_axis_label="Hours",
            y_axis_label=f"F", outline_line_width = 1, outline_line_color = '#000000', y_axis_type="log")
    p_time  = figure(height = 800, width = 1300, x_axis_label="Hours",
            y_axis_label=r"\[f_{char}\]", outline_line_width = 1, outline_line_color = '#000000', y_axis_type="log")
    
    p_DRT   = figure(height = 800, width = 1200, x_axis_label=f"f/Hz",
            y_axis_label=f"\u03B3/\u03A9", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000',
            x_axis_type="log")
    
    p_model_eval = figure(height = 800, width = 1200, x_axis_label=f"f/Hz",
                       y_axis_label=f"Im(Z)/\u03A9", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000',
            x_axis_type="log")
    
    p_model_nyquist = figure(height = 800, width = 1200, x_axis_label=f"Re(Z)/\u03A9",
                       y_axis_label=f"Im(Z)/\u03A9", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000')
    
    p_Z_pred = figure(height = 800, width = 1200, x_axis_label=f"f / Hz",
                y_axis_label=f"-Im(Z / \u03A9)", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000', x_axis_type="log")
    
    p_Z_pred_nyquist = figure(height = 800, width = 1200, x_axis_label=f"Re(Z / \u03A9)",
                y_axis_label=f"-Im(Z / \u03A9)", match_aspect = True, aspect_scale = 1, outline_line_width = 1, outline_line_color = '#000000')

    return p_nyquist, p_bode, p_resistance, p_capacitance, p_time, p_DRT, p_Z_pred, p_Z_pred_nyquist, p_model_eval, p_model_nyquist

def create_widgets(currentplot):
    '''
    Creating the variuos wirgets for making selections of which glyphs to view. 
    '''
    # Cells 
    currentplot.cell_selector           = RadioButtonGroup(labels=['All'] + currentplot.CELL_SELECTOR_LABEL, active=0) # Eventually change to a multselect?
    # Dates

    # dir_names = currentplot.df['dir_name'].unique().tolist() # The name of the dirs are also the dates of the data

    start_date = datetime( # Change to lowest in dataset
        currentplot.start_date_dict['year'],
        currentplot.start_date_dict['month'],
        currentplot.start_date_dict['day'],
        currentplot.start_date_dict['hour'],
        currentplot.start_date_dict['min']
    )
    end_date = datetime( # Change to lowest in dataset
        currentplot.end_date_dict['year'],
        currentplot.end_date_dict['month'],
        currentplot.end_date_dict['day'],
        currentplot.end_date_dict['hour'],
        currentplot.end_date_dict['min']
    )
    start_date_short = datetime( # Change to lowest in dataset
        currentplot.start_date_dict['year'],
        currentplot.start_date_dict['month'],
        currentplot.start_date_dict['day']
    )
    end_date_short = datetime( # Change to lowest in dataset
        currentplot.end_date_dict['year'],
        currentplot.end_date_dict['month'],
        currentplot.end_date_dict['day'],
    )
    print("Start date is: " + str(start_date))
    print("End data is: " + str(end_date))

    if start_date_short == end_date_short: # Dont "properly" create the date selector if only one date in the data
        #temp_end_date = start_date + timedelta(days=1)
        currentplot.date_selector           = RangeSlider(value=(1, int(len(currentplot.dates_list))), start=1, end=int(len(currentplot.dates_list)), step=1)
        #currentplot.date_selector.visible = False
    else:
        currentplot.date_selector           = DateRangeSlider(value=(start_date, end_date), start=start_date, end=end_date)

    # Temperatures
    currentplot.temperature_selector    = CheckboxGroup(labels=currentplot.TEMPERATURE_SELECTOR_LABEL, active=list(range(len(currentplot.df['temp'].unique()))))
    # Pressures
    currentplot.pressure_selector       = CheckboxGroup(labels=currentplot.PRESSURE_SELECTOR_LABEL, active=list(range(len(currentplot.df['pressure'].unique()))))
    # DC Current
    currentplot.dc_current_selector     = CheckboxGroup(labels=currentplot.DC_CURRENT_SELECTOR_LABEL, active=list(range(len(currentplot.df['dc'].unique()))))
    # AC Current
    currentplot.ac_current_selector     = CheckboxGroup(labels=currentplot.AC_CURRENT_SELECTOR_LABEL, active=list(range(len(currentplot.df['ac'].unique()))))
    
    # Resistance
    currentplot.resistance_selector     = CheckboxGroup(labels=currentplot.RESISTANCE_SELECTOR_LABEL, active=list(range(len(currentplot.RESISTANCE_SELECTOR_LABEL))))
    # Capatitance
    currentplot.capacitance_selector    = CheckboxGroup(labels=currentplot.capacitance_selector_LABEL, active=list(range(len(currentplot.capacitance_selector_LABEL))))    
    # Time

    CHAR_FREQ_LABELS = ["f_char " + str(time_label[-1]) for time_label in currentplot.TIME_SELECTOR_LABEL]
    # currentplot.time_selector           = CheckboxGroup(labels=currentplot.TIME_SELECTOR_LABEL, active=list(range(len(currentplot.TIME_SELECTOR_LABEL))))
    currentplot.time_selector           = CheckboxGroup(labels=CHAR_FREQ_LABELS, active=list(range(len(currentplot.TIME_SELECTOR_LABEL))))

    # Hide or show fitted impedance
    currentplot.hide_fitted_impedance = CheckboxGroup(labels=["Show/Hide"], active=[0])
    # Hide or show error fron prediction
    currentplot.hide_prediction_error = CheckboxGroup(labels=["Show/Hide"], active=[0])

    # Selecting what range to view on the x-axis of the fitting plots
    if currentplot.circuit_df.empty:
        max_hours       = 1
    else:
        max_hours = currentplot.circuit_df['hours_since_first_date'].max()
        if max_hours == 0: # In case the cells at one timepoint is processed
            max_hours   = 1

    currentplot.select_hours_slider = RangeSlider(start=0, end=max_hours, value=(0, max_hours), step=10)

def create_callback(currentplot):
    '''
    Callback for only viewing the glyphs related to the cell selected in the cell_selector-, resistance_selector-, capacitance_selector-, time_selector and date_selector-widgets. 
    '''



    # adding on to have option if the date is similar
    start_date_short = datetime( # Change to lowest in dataset
        currentplot.start_date_dict['year'],
        currentplot.start_date_dict['month'],
        currentplot.start_date_dict['day']
    )
    end_date_short = datetime( # Change to lowest in dataset
        currentplot.end_date_dict['year'],
        currentplot.end_date_dict['month'],
        currentplot.end_date_dict['day'],
    )

    if start_date_short == end_date_short:
        selector_callback = CustomJS(args=dict(
                cell_plots=currentplot.cell_plots, 
                circuit_plots=currentplot.circuit_plots, 
                impedance_from_fitting_plots = currentplot.impedance_from_fitting_plots,
                DRT_plots=currentplot.DRT_plots, 
                modeval_plots=currentplot.modeval_plots,
                modnyq_plots=currentplot.modnyq_plots,
                Z_pred_imag_plots=currentplot.Z_pred_imag_plots, 
                Z_pred_plots=currentplot.Z_pred_plots, 

                circuit_bool=(currentplot.circuit_df.empty == False),
                DRT_bool=(currentplot.DRT_df.empty == False),
                Z_pred_bool=(currentplot.Z_pred_df.empty == False),
                
                cell_selector=currentplot.cell_selector, 
                CELL_SELECTOR_LABEL=currentplot.CELL_SELECTOR_LABEL, 
                
                resistance_selector=currentplot.resistance_selector, 
                RESISTANCE_SELECTOR_LABEL= currentplot.RESISTANCE_SELECTOR_LABEL, 

                capacitance_selector=currentplot.capacitance_selector, 
                capacitance_selector_LABEL= currentplot.capacitance_selector_LABEL, 

                time_selector=currentplot.time_selector, 
                TIME_SELECTOR_LABEL= currentplot.TIME_SELECTOR_LABEL, 

                hide_fitted_impedance = currentplot.hide_fitted_impedance,
                hide_prediction_error = currentplot.hide_prediction_error,

                date_selector = currentplot.date_selector), 
                code="""
                const selectedCellIndices = cell_selector.active;
                const selectedResIndices = resistance_selector.active;
                const selectedCapIndices = capacitance_selector.active;
                const selectedTimeIndices = time_selector.active;
                const hide_fitted_impedance_bool = hide_fitted_impedance.active.includes(0);
                const hide_prediction_error_bool = hide_prediction_error.active.includes(0);

                const start = new Date(date_selector.value[0]);
                const end = new Date(date_selector.value[1]);

                var selectedResNames = [];
                for (let i = 0; i < selectedResIndices.length; i++) {
                    selectedResNames.push(RESISTANCE_SELECTOR_LABEL[selectedResIndices[i]]);
                }
                var selectedCapNames = [];
                for (let i = 0; i < selectedCapIndices.length; i++) {
                    selectedCapNames.push(capacitance_selector_LABEL[selectedCapIndices[i]]);
                }
                var selectedTimeNames = [];
                for (let i = 0; i < selectedTimeIndices.length; i++) {
                    selectedTimeNames.push(TIME_SELECTOR_LABEL[selectedTimeIndices[i]]);
                }

                if (selectedCellIndices === 0) {
                    for (var i = 0; i < CELL_SELECTOR_LABEL.length; i++) {
                        const cell_name = CELL_SELECTOR_LABEL[i];
                        
                        for (let dir_key in cell_plots[cell_name]) {
                            const counter = 0;
                            if (cell_plots[cell_name].hasOwnProperty(dir_key)) {
                                const counter = counter + 1;
                                const date = counter;
                                const date_bool = (date >= start && date <= end);
                                
                                cell_plots[cell_name][dir_key][0].visible = date_bool;
                                cell_plots[cell_name][dir_key][1][0].visible = date_bool;
                                cell_plots[cell_name][dir_key][1][1].visible = date_bool;
                                cell_plots[cell_name][dir_key][2].visible = date_bool;
                                cell_plots[cell_name][dir_key][3].visible = date_bool;
                            
                                if (Z_pred_bool) {
                                    Z_pred_imag_plots[cell_name][dir_key][0].visible = date_bool;
                                    Z_pred_imag_plots[cell_name][dir_key][1].visible = (date_bool && hide_prediction_error_bool);
                                    Z_pred_plots[cell_name][dir_key][0].visible = date_bool;
                                    Z_pred_plots[cell_name][dir_key][1].visible = date_bool;
                                }
                            }
                        }

                        if (circuit_bool) {
                            for (let dir_key in circuit_plots[cell_name]) {
                                const counter = 0;
                                if (circuit_plots[cell_name].hasOwnProperty(dir_key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    const date_bool = (date >= start && date <= end);

                                    // Hide or show the grey dots from the circuit-fit
                                    if (date_bool) {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = hide_fitted_impedance_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = hide_fitted_impedance_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = hide_fitted_impedance_bool;
                                    } else {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = false;
                                    }
                                

                                    for (let key in circuit_plots[cell_name][dir_key][0]) {
                                        if (circuit_plots[cell_name][dir_key][0].hasOwnProperty(key)) {
                                            
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][0][key].length; j++) {
                                            
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = (selectedResNames.includes(key));
                                                } else {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }                  
                                    for (let key in circuit_plots[cell_name][dir_key][1]) {
                                        if (circuit_plots[cell_name][dir_key][1].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][1][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = (selectedCapNames.includes(key));
                                                } else {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }                  
                                    for (let key in circuit_plots[cell_name][dir_key][2]) {
                                        if (circuit_plots[cell_name][dir_key][2].hasOwnProperty(key)) {
                                            if (date_bool) {
                                                circuit_plots[cell_name][dir_key][2][key].visible = (selectedTimeNames.includes(key));
                                            } else {
                                                circuit_plots[cell_name][dir_key][2][key].visible = false;
                                            }
                                        }
                                    }                  
                                }
                            }
                        }
                        if (DRT_bool) {
                            for (let key in DRT_plots[cell_name]) {
                                const counter = 0;
                                if (DRT_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end) {
                                        DRT_plots[cell_name][key][0].visible = true;
                                        DRT_plots[cell_name][key][1].visible = true;
                                    } else {
                                        DRT_plots[cell_name][key][0].visible = false;
                                        DRT_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modeval_plots[cell_name]) {
                                const counter = 0;
                                if (modeval_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end) {
                                        modeval_plots[cell_name][key][0].visible = true;
                                        modeval_plots[cell_name][key][1].visible = true;
                                    } else {
                                        modeval_plots[cell_name][key][0].visible = false;
                                        modeval_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modnyq_plots[cell_name]) {
                                const counter = 0;
                                if (modnyq_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end) {
                                        modnyq_plots[cell_name][key][0].visible = true;
                                        modnyq_plots[cell_name][key][1].visible = true;
                                    } else {
                                        modnyq_plots[cell_name][key][0].visible = false;
                                        modnyq_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }
                        }
                    }
                } else {
                    for (let i = 0; i < CELL_SELECTOR_LABEL.length; i++) {
                        const cell_name = CELL_SELECTOR_LABEL[i];
                        
                        for (let dir_key in cell_plots[cell_name]) {
                            const counter = 0;
                            if (cell_plots[cell_name].hasOwnProperty(dir_key)) {
                                const counter = counter + 1;
                                const date = counter;                                  
                                const date_bool = (date >= start && date <= end);
                                
                                cell_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][1][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][1][1].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][2].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][3].visible = ((i + 1 === selectedCellIndices) && date_bool);
                            
                                if (Z_pred_bool) {
                                    Z_pred_imag_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                    Z_pred_imag_plots[cell_name][dir_key][1].visible = ((i + 1 === selectedCellIndices) && date_bool && hide_prediction_error_bool);
                                    Z_pred_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                    Z_pred_plots[cell_name][dir_key][1].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                }
                            
                            }

                        }
                        
                        if (circuit_bool) {
                            for (let dir_key in circuit_plots[cell_name]) {
                                const counter = 0;
                                if (circuit_plots[cell_name].hasOwnProperty(dir_key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    const date_bool = (date >= start && date <= end);

                                    // Hide or show the grey dots from the circuit-fit
                                    if (date_bool) {
                                        const check_bool = (
                                            CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                            hide_fitted_impedance_bool
                                        );
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = check_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = check_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = check_bool;
                                    } else {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = false;
                                    }
                                    
                                    for (let key in circuit_plots[cell_name][dir_key][0]) {
                                        if (circuit_plots[cell_name][dir_key][0].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][0][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = (
                                                    CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                    selectedResNames.includes(key)
                                                    );
                                                } else {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }
                                    for (let key in circuit_plots[cell_name][dir_key][1]) {
                                        if (circuit_plots[cell_name][dir_key][1].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][1][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = (
                                                    CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                    selectedCapNames.includes(key)
                                                    );
                                                } else {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }
                                    for (let key in circuit_plots[cell_name][dir_key][2]) {
                                        if (circuit_plots[cell_name][dir_key][2].hasOwnProperty(key)) {
                                            if (date_bool) {
                                                circuit_plots[cell_name][dir_key][2][key].visible = (
                                                CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                selectedTimeNames.includes(key)
                                                );
                                            } else {
                                                circuit_plots[cell_name][dir_key][2][key].visible = false;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        if (DRT_bool) {
                            for (let key in DRT_plots[cell_name]) {
                                const counter = 0;
                                if (DRT_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end
                                    ) {
                                        DRT_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        DRT_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        DRT_plots[cell_name][key][0].visible = false;
                                        DRT_plots[cell_name][key][1].visible = false;
                                    }
                                }   
                            }

                            for (let key in modeval_plots[cell_name]) {
                                const counter = 0;
                                if (modeval_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end
                                    ) {
                                        modeval_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        modeval_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        modeval_plots[cell_name][key][0].visible = false;
                                        modeval_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            

                            for (let key in modnyq_plots[cell_name]) {
                                const counter = 0;
                                if (modnyq_plots[cell_name].hasOwnProperty(key)) {
                                    const counter = counter + 1;
                                    const date = counter;
                                    if (date >= start && date <= end
                                    ) {
                                        modnyq_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        modnyq_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        modnyq_plots[cell_name][key][0].visible = false;
                                        modnyq_plots[cell_name][key][1].visible = false;
                                    }
                                }   
                            }
                        }
                    }
                }
          """
        )



    else:
        selector_callback = CustomJS(args=dict(
                cell_plots=currentplot.cell_plots, 
                circuit_plots=currentplot.circuit_plots, 
                impedance_from_fitting_plots = currentplot.impedance_from_fitting_plots,
                DRT_plots=currentplot.DRT_plots, 
                modeval_plots=currentplot.modeval_plots, 
                modnyq_plots=currentplot.modnyq_plots,
                Z_pred_imag_plots=currentplot.Z_pred_imag_plots, 
                Z_pred_plots=currentplot.Z_pred_plots, 

                circuit_bool=(currentplot.circuit_df.empty == False),
                DRT_bool=(currentplot.DRT_df.empty == False),
                Z_pred_bool=(currentplot.Z_pred_df.empty == False),
                
                cell_selector=currentplot.cell_selector, 
                CELL_SELECTOR_LABEL=currentplot.CELL_SELECTOR_LABEL, 
                
                resistance_selector=currentplot.resistance_selector, 
                RESISTANCE_SELECTOR_LABEL= currentplot.RESISTANCE_SELECTOR_LABEL, 

                capacitance_selector=currentplot.capacitance_selector, 
                capacitance_selector_LABEL= currentplot.capacitance_selector_LABEL, 

                time_selector=currentplot.time_selector, 
                TIME_SELECTOR_LABEL= currentplot.TIME_SELECTOR_LABEL, 

                hide_fitted_impedance = currentplot.hide_fitted_impedance,
                hide_prediction_error = currentplot.hide_prediction_error,

                date_selector = currentplot.date_selector), 
                code="""
                const selectedCellIndices = cell_selector.active;
                const selectedResIndices = resistance_selector.active;
                const selectedCapIndices = capacitance_selector.active;
                const selectedTimeIndices = time_selector.active;
                const hide_fitted_impedance_bool = hide_fitted_impedance.active.includes(0);
                const hide_prediction_error_bool = hide_prediction_error.active.includes(0);

                const start = new Date(date_selector.value[0]);
                const end = new Date(date_selector.value[1]);

                var selectedResNames = [];
                for (let i = 0; i < selectedResIndices.length; i++) {
                    selectedResNames.push(RESISTANCE_SELECTOR_LABEL[selectedResIndices[i]]);
                }
                var selectedCapNames = [];
                for (let i = 0; i < selectedCapIndices.length; i++) {
                    selectedCapNames.push(capacitance_selector_LABEL[selectedCapIndices[i]]);
                }
                var selectedTimeNames = [];
                for (let i = 0; i < selectedTimeIndices.length; i++) {
                    selectedTimeNames.push(TIME_SELECTOR_LABEL[selectedTimeIndices[i]]);
                }

                if (selectedCellIndices === 0) {
                    for (var i = 0; i < CELL_SELECTOR_LABEL.length; i++) {
                        const cell_name = CELL_SELECTOR_LABEL[i];
                        
                        for (let dir_key in cell_plots[cell_name]) {
                            if (cell_plots[cell_name].hasOwnProperty(dir_key)) {
                                const date = new Date(dir_key.slice(0, 10));
                                const date_bool = (date >= start && date <= end);
                                
                                cell_plots[cell_name][dir_key][0].visible = date_bool;
                                cell_plots[cell_name][dir_key][1][0].visible = date_bool;
                                cell_plots[cell_name][dir_key][1][1].visible = date_bool;
                                cell_plots[cell_name][dir_key][2].visible = date_bool;
                                cell_plots[cell_name][dir_key][3].visible = date_bool;
                            
                                if (Z_pred_bool) {
                                    Z_pred_imag_plots[cell_name][dir_key][0].visible = date_bool;
                                    Z_pred_imag_plots[cell_name][dir_key][1].visible = (date_bool && hide_prediction_error_bool);
                                    Z_pred_plots[cell_name][dir_key][0].visible = date_bool;
                                    Z_pred_plots[cell_name][dir_key][1].visible = date_bool;
                                }
                            }
                        }

                        if (circuit_bool) {
                            for (let dir_key in circuit_plots[cell_name]) {
                                if (circuit_plots[cell_name].hasOwnProperty(dir_key)) {
                                    const date = new Date(dir_key.slice(0, 10));
                                    const date_bool = (date >= start && date <= end);

                                    // Hide or show the grey dots from the circuit-fit
                                    if (date_bool) {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = hide_fitted_impedance_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = hide_fitted_impedance_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = hide_fitted_impedance_bool;
                                    } else {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = false;
                                    }
                                

                                    for (let key in circuit_plots[cell_name][dir_key][0]) {
                                        if (circuit_plots[cell_name][dir_key][0].hasOwnProperty(key)) {
                                            
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][0][key].length; j++) {
                                            
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = (selectedResNames.includes(key));
                                                } else {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }                  
                                    for (let key in circuit_plots[cell_name][dir_key][1]) {
                                        if (circuit_plots[cell_name][dir_key][1].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][1][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = (selectedCapNames.includes(key));
                                                } else {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }                  
                                    for (let key in circuit_plots[cell_name][dir_key][2]) {
                                        if (circuit_plots[cell_name][dir_key][2].hasOwnProperty(key)) {
                                            if (date_bool) {
                                                circuit_plots[cell_name][dir_key][2][key].visible = (selectedTimeNames.includes(key));
                                            } else {
                                                circuit_plots[cell_name][dir_key][2][key].visible = false;
                                            }
                                        }
                                    }                  
                                }
                            }
                        }
                        if (DRT_bool) {
                            for (let key in DRT_plots[cell_name]) {
                                if (DRT_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end) {
                                        DRT_plots[cell_name][key][0].visible = true;
                                        DRT_plots[cell_name][key][1].visible = true;
                                    } else {
                                        DRT_plots[cell_name][key][0].visible = false;
                                        DRT_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modeval_plots[cell_name]) {
                                if (modeval_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end) {
                                        modeval_plots[cell_name][key][0].visible = true;
                                        modeval_plots[cell_name][key][1].visible = true;
                                    } else {
                                        modeval_plots[cell_name][key][0].visible = false;
                                        modeval_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modnyq_plots[cell_name]) {
                                if (modnyq_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end) {
                                        modnyq_plots[cell_name][key][0].visible = true;
                                        modnyq_plots[cell_name][key][1].visible = true;
                                    } else {
                                        modnyq_plots[cell_name][key][0].visible = false;
                                        modnyq_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }
                            
                        }
                    }
                } else {
                    for (let i = 0; i < CELL_SELECTOR_LABEL.length; i++) {
                        const cell_name = CELL_SELECTOR_LABEL[i];
                        
                        for (let dir_key in cell_plots[cell_name]) {
                            if (cell_plots[cell_name].hasOwnProperty(dir_key)) {
                                const date = new Date(dir_key.slice(0, 10));
                                const date_bool = (date >= start && date <= end);
                                
                                cell_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][1][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][1][1].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][2].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                cell_plots[cell_name][dir_key][3].visible = ((i + 1 === selectedCellIndices) && date_bool);
                            
                                if (Z_pred_bool) {
                                    Z_pred_imag_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                    Z_pred_imag_plots[cell_name][dir_key][1].visible = ((i + 1 === selectedCellIndices) && date_bool && hide_prediction_error_bool);
                                    Z_pred_plots[cell_name][dir_key][0].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                    Z_pred_plots[cell_name][dir_key][1].visible = ((i + 1 === selectedCellIndices) && date_bool);
                                }
                            
                            }

                        }
                        
                        if (circuit_bool) {
                            for (let dir_key in circuit_plots[cell_name]) {
                                if (circuit_plots[cell_name].hasOwnProperty(dir_key)) {
                                    const date = new Date(dir_key.slice(0, 10));
                                    const date_bool = (date >= start && date <= end);

                                    // Hide or show the grey dots from the circuit-fit
                                    if (date_bool) {
                                        const check_bool = (
                                            CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                            hide_fitted_impedance_bool
                                        );
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = check_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = check_bool;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = check_bool;
                                    } else {
                                        impedance_from_fitting_plots[cell_name][dir_key][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][0].visible = false;
                                        impedance_from_fitting_plots[cell_name][dir_key][1][1].visible = false;
                                    }
                                    
                                    for (let key in circuit_plots[cell_name][dir_key][0]) {
                                        if (circuit_plots[cell_name][dir_key][0].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][0][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = (
                                                    CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                    selectedResNames.includes(key)
                                                    );
                                                } else {
                                                    circuit_plots[cell_name][dir_key][0][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }
                                    for (let key in circuit_plots[cell_name][dir_key][1]) {
                                        if (circuit_plots[cell_name][dir_key][1].hasOwnProperty(key)) {
                                            for (let j = 0; j < circuit_plots[cell_name][dir_key][1][key].length; j++) {
                                                if (date_bool) {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = (
                                                    CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                    selectedCapNames.includes(key)
                                                    );
                                                } else {
                                                    circuit_plots[cell_name][dir_key][1][key][j].visible = false;
                                                }
                                            }
                                        }
                                    }
                                    for (let key in circuit_plots[cell_name][dir_key][2]) {
                                        if (circuit_plots[cell_name][dir_key][2].hasOwnProperty(key)) {
                                            if (date_bool) {
                                                circuit_plots[cell_name][dir_key][2][key].visible = (
                                                CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name &&
                                                selectedTimeNames.includes(key)
                                                );
                                            } else {
                                                circuit_plots[cell_name][dir_key][2][key].visible = false;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        if (DRT_bool) {
                            for (let key in DRT_plots[cell_name]) {
                                if (DRT_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end
                                    ) {
                                        DRT_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        DRT_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        DRT_plots[cell_name][key][0].visible = false;
                                        DRT_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modeval_plots[cell_name]) {
                                if (modeval_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end
                                    ) {
                                        modeval_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        modeval_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        modeval_plots[cell_name][key][0].visible = false;
                                        modeval_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }

                            for (let key in modnyq_plots[cell_name]) {
                                if (modnyq_plots[cell_name].hasOwnProperty(key)) {
                                    const date = new Date(key.slice(0, 10));
                                    if (date >= start && date <= end
                                    ) {
                                        modnyq_plots[cell_name][key][0].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                        modnyq_plots[cell_name][key][1].visible = (CELL_SELECTOR_LABEL[selectedCellIndices - 1] === cell_name);
                                    } else {
                                        modnyq_plots[cell_name][key][0].visible = false;
                                        modnyq_plots[cell_name][key][1].visible = false;
                                    }
                                }
                            }
                        }
                    }
                }
            """
            )
    return selector_callback
