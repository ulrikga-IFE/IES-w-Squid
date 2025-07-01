'''
Short description:
    Includes functions and that generates the tkinter-interface. 
    Closely related to the interface-class in dashboard_for_plotting_and_fitting.py. Should maybe in the future combine these into one class. 
Why:
    Separate this code into its own file in order to make the init of the interface-class in dashboard_for_plotting_and_fitting.py cleaner.

Depends on:
    circuit_handler.py


@author: Elling Svee (elling.svee@gmail.com)
'''
import os
import tkinter as tk
from tkinter import ttk
import pandas as pd
import dependencies.circuit_handler as ch 


class tkinter_class():
    def __init__(self, interface) -> None:
        """
        Windows that handles the tkinter-windows
        """
        self.interface = interface

        # Need to create different_tkinter_windows based on if if is opened from this file or from the button in control_main
        if interface.opened_from_controlmain_bool == True:
            self.root = tk.Toplevel()                             # Create main window
        else:
            self.root = tk.Tk()                             # Create main window
            self.root.eval('tk::PlaceWindow . center')      # Centering the window(ish) on the screen


        # Menubar is the thing at the top of the window ('Help') 
        self.menubar = tk.Menu(self.root)
        self.menubar.add_command(label="About",command=self.about)
        self.menubar.add_command(label="How To",command=self.how_to)
        self.root.config(menu=self.menubar)



        # Call the center_window function after the window is rendered
        self.root.after(0, self.center_window)

        self.root.title("Control panel")
        self.root.iconbitmap("ife.ico")     # A IFE logo on the top left corner of the window

        # Constants used for the layout of the window
        self.DPI                        = 100
        self.WIDTH                      = 62
        self.TEXTHEIGHT                 = 20
        self.filetypes                  = (("txt", "*.txt"),)
        self.default_extention          = "*.txt"
        self.padx                       = 2
        self.pady                       = 2
        self.font                       = ("Arial", 12)
        self.button_font                = ("Arial", 10)
        self.browse_button_color        = 'sky blue'
        self.generate_interface_color   = "light green"
        self.red_button                 = 'firebrick3'
        self.text_color                 = 'grey1'
        self.text_disabled_color        = 'grey75'


        # Add menu-bar
        self.currentrow = 0
        self.header     = tk.Label(self.root, text="EIS: Plot and fit data")
        self.header.config(fg=self.text_color, font=("Arial", 24))
        self.header.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky='nsew')

        ################ SELECT DATA FOLDER ################
        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        # Select folder from which we will retrieve the data
        self.currentrow += 1
        # Label
        self.data_folder_label = tk.Label(self.root, text="Data folder:")
        self.data_folder_label.config(fg=self.text_color, font=self.font)
        self.data_folder_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        # Text
        self.data_folder = tk.Text(self.root, height = 1, width=20)
        self.data_folder.insert(tk.INSERT, os.path.basename(os.path.basename(self.interface.default_path)))
        self.data_folder.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        # Button
        self.data_folder_button = tk.Button(self.root, text="Browse", command=self.select_data_folder, bg=self.browse_button_color, font=self.button_font) 
        self.data_folder_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew") 

        # Checkbox and settings window for normalizing the data
        self.normalize_bool = tk.IntVar()

        self.currentrow += 1
        # Label
        self.normalize_label = tk.Label(self.root, text="Normalize (Y/N):")
        self.normalize_label.config(fg=self.text_color, font=self.font)
        self.normalize_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        # Checkbox
        self.normalize_checkbox_var = tk.IntVar()
        self.normalize_checkbox_var.set(0)
        self.normalize_checkbox = tk.Checkbutton(self.root, variable=self.normalize_checkbox_var, onvalue=1, offvalue=0)
        self.normalize_checkbox.grid(row=self.currentrow, column=1, padx=self.padx, pady=self.pady, sticky="W")

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        self.currentrow += 1
        
        ################ PREDICT IMPEDANCE ################
        self.Z_pred_checkbox_var = tk.IntVar()
        self.Z_pred_checkbox_var.set(0)
        self.Z_pred_checkbox = tk.Checkbutton(self.root, variable=self.Z_pred_checkbox_var, onvalue=1, offvalue=0)
        self.Z_pred_checkbox.grid(row=self.currentrow, column=1, padx=self.padx, pady=self.pady, sticky="W")
        self.Z_pred_label = tk.Label(self.root, text="Predict impedance (beta version):")
        self.Z_pred_label.config(fg=self.text_color, font=self.font)
        self.Z_pred_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        self.open_Z_pred_setting_button = tk.Button(self.root, text="Open settings", command=self.Z_pred_setting_window)
        self.open_Z_pred_setting_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew")

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ SELECT FITTING ALGORITHM ################
        # Checkbox for choosing which fitting algorithm that will be performed
        self.currentrow += 1
        # Label
        self.fitting_algorithms_label = tk.Label(self.root, text="Fitting algorithms:")
        self.fitting_algorithms_label.config(fg=self.text_color, font=self.font)
        self.fitting_algorithms_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        # Equivalent circuit
        self.circuit_fit_checkbox_var = tk.IntVar()
        self.circuit_fit_checkbox_var.set(0) #Default value
        self.circuit_fit_checkbox = tk.Checkbutton(self.root, variable=self.circuit_fit_checkbox_var, onvalue=1, offvalue=0)
        self.circuit_fit_checkbox.grid(row=self.currentrow, column=1, padx=self.padx, pady=self.pady, sticky="W")
        self.circuit_fit_label = tk.Label(self.root, text="Equivalent circuit")
        self.circuit_fit_label.config(fg=self.text_color, font=self.font)
        self.circuit_fit_label.grid(row=self.currentrow, column=2, padx=self.padx, pady=self.pady, sticky="W")

        # Distribution of relaxation times
        self.currentrow += 1
        self.DRT_fit_checkbox_var = tk.IntVar()
        self.DRT_fit_checkbox_var.set(0) #Default value
        self.DRT_fit_checkbox = tk.Checkbutton(self.root, variable=self.DRT_fit_checkbox_var, onvalue=1, offvalue=0)
        self.DRT_fit_checkbox.grid(row=self.currentrow, column=1, padx=self.padx, pady=self.pady, sticky="W")
        self.DRT_fit_label = tk.Label(self.root, text="Distribution of relaxation times")
        self.DRT_fit_label.config(fg=self.text_color, font=self.font)
        self.DRT_fit_label.grid(row=self.currentrow, column=2, padx=self.padx, pady=self.pady, sticky="W")

        ################ CIRCUIT-FITTING SETTINGS ################
        # Dropdown for choosing circuit for fitting
        self.currentrow += 1
        # Label
        self.select_circuit_label = tk.Label(self.root, text="Select circuit:")
        self.select_circuit_label.config(fg=self.text_color, font=self.font)
        self.select_circuit_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        # Menu
        self.circuit_string = tk.StringVar(self.root)
        self.circuit_string.set(list(ch.IMPLEMENTED_CIRCUITS.keys())[1])
        self.circuit_menu = tk.OptionMenu(self.root, self.circuit_string, *list(ch.IMPLEMENTED_CIRCUITS.keys()), command=self.choose_circuit)
        self.circuit_menu.grid(row=self.currentrow, column=1, columnspan=3, padx=self.padx, pady=self.pady, sticky="ew")


        ################ DRT-FITTING SETTINGS ################
        self.currentrow += 1

        # Labels
        self.DRT_settings_label = tk.Label(self.root, text="DRT-fitting:")
        self.DRT_settings_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        self.open_DRT_advanced_setting_button = tk.Button(self.root, text="Open advanced settings", command=self.DRT_advanced_setting_window)
        self.open_DRT_advanced_setting_button.grid(row=self.currentrow, column=1, columnspan=3, padx=self.padx, pady=self.pady, sticky="ew")

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ PROCESS ################
        # Button for processing/fitting the data
        self.currentrow += 1
        self.process_button = tk.Button(self.root, text="Process", command=self.interface.process, height=5, bg=self.browse_button_color)
        self.process_button.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="ew")

        # Messagebox for user feedback and error logging
        self.messagebox = tk.Text(self.root, height=5)
        self.messagebox.grid(row=self.currentrow, column=1, columnspan=3, padx=self.padx, pady=self.pady, sticky="ew")

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ AUTO-RUN ################
        self.currentrow += 1
        # Labels
        self.auto_run_label = tk.Label(self.root, text="Auto-run:")
        self.auto_run_label.config(fg=self.text_color, font=self.font)
        self.auto_run_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        self.auto_run_checkbox_var = tk.IntVar()
        self.auto_run_checkbox_var.set(0)
        self.auto_run_checkbox = tk.Checkbutton(self.root, variable=self.auto_run_checkbox_var, command=self.auto_run_checkbox_callback, onvalue=1, offvalue=0)
        self.auto_run_checkbox.grid(row=self.currentrow, column=1, padx=self.padx, pady=self.pady, sticky="W")

        self.auto_run_min_label = tk.Label(self.root, text="Wait time (minuites):", state=tk.DISABLED)
        self.auto_run_min_label.config(fg=self.text_color, font=self.font)
        self.auto_run_min_label.grid(row=self.currentrow, column=2, padx=self.padx, pady=self.pady, sticky="E")
        self.auto_run_min_var       = tk.StringVar()
        self.auto_run_min_textbox   = tk.Entry(self.root, width=10, textvariable=self.auto_run_min_var, state=tk.DISABLED)
        self.auto_run_min_textbox.delete(0, tk.END)
        self.auto_run_min_textbox.insert(0, str(10))
        self.auto_run_min_textbox.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew")

        self.currentrow += 1
        # Run-Button
        # Use BooleanVar to manage the state of the button
        self.auto_run_button_state = tk.BooleanVar()
        self.auto_run_button_state.set(False)  # Initialize the state to OFF
        self.auto_run_button = tk.Button(self.root, text="START", command=self.auto_run_toggle, bg=self.browse_button_color, font=self.button_font, state=tk.DISABLED) 
        self.auto_run_button.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew") 
        # Update-button
        self.auto_run_update_button = tk.Button(self.root, text="Update", command=self.update_auto_run, bg=self.red_button, font=self.button_font, state=tk.DISABLED) 
        self.auto_run_update_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew") 

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ SAVE DATA ################
        # Select file to save the data to
        self.currentrow += 1
        # Label
        self.save_file_folder_label = tk.Label(self.root, text="Save to folder:")
        self.save_file_folder_label.config(fg=self.text_color, font=self.font)
        self.save_file_folder_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        self.save_file_folder_label['state'] = tk.DISABLED
        # Text
        self.save_file_folder = tk.Text(self.root, height = 1, width=20)
        # self.save_file_folder.insert(tk.INSERT, os.path.basename(os.path.basename(self.default_path)))
        self.save_file_folder.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        self.save_file_folder['state'] = tk.DISABLED
        # Button
        self.save_file_folder_button = tk.Button(self.root, text="Browse", command=self.select_save_folder, bg=self.browse_button_color, font=self.button_font) 
        self.save_file_folder_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew") 
        self.save_file_folder_button['state'] = tk.DISABLED

        self.currentrow += 1    
        # Alert in case no data is processed before trying to save
        self.save_data_alert = tk.Label(self.root, text='Need to process the data before you can save')
        self.save_data_alert.config(fg=self.red_button, font=self.font)
        self.save_data_alert.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="w")
        self.save_data_alert.grid_remove() # Itialize as hidden

        # Alert in case no file is selected before trying to save
        self.save_data_choose_file_alert = tk.Label(self.root, text='Choose a folder first')
        self.save_data_choose_file_alert.config(fg=self.red_button, font=self.font)
        self.save_data_choose_file_alert.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="w")
        self.save_data_choose_file_alert.grid_remove() # Itialize as hidden

        # Button for saving the data
        self.save_data = tk.Button(
            self.root, text="SAVE", bg=self.red_button, font=self.button_font, command=self.save_data_callback
        )
        self.save_data.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew")
        self.save_data['state'] = tk.DISABLED

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ LOAD DATA ################
        # Open data that has previously been calculated
        self.currentrow += 1
        # Label
        self.previous_data_folder_label = tk.Label(self.root, text="Load previous data:")
        self.previous_data_folder_label.config(fg=self.text_color, font=self.font)
        self.previous_data_folder_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        # Text
        self.previous_data_folder = tk.Text(self.root, height = 1, width=20)
        # self.previous_data_folder.insert(tk.INSERT, os.path.basename(os.path.basename(self.default_path)))
        self.previous_data_folder.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        # Button
        self.previous_data_folder_button = tk.Button(self.root, text="Browse", command=self.select_prev_data_folder, bg=self.browse_button_color, font=self.button_font) 
        self.previous_data_folder_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew") 


        self.currentrow += 1
        # Button for clearing the choice of opening previous file
        self.clear_prev_data = tk.Button(
            self.root, text="CLEAR", bg=self.red_button, font=self.button_font, command=self.clear_prev_data_callback
        )
        self.clear_prev_data.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew")
        # Button for selecting the choice of opening previous file
        self.use_prev_data = tk.Button(
            self.root, text="USE PREV DATA", bg=self.browse_button_color, font=self.button_font, command=self.use_prev_data_callback
        )
        self.use_prev_data.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")

        self.currentrow += 1
        # Alert if trying to use previos data without a folder being selected
        self.use_prev_data_alert = tk.Label(self.root, text='Choose a file first')
        self.use_prev_data_alert.config(fg=self.red_button, font=self.font)
        self.use_prev_data_alert.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="w")
        self.use_prev_data_alert.grid_remove() # Itialize as hidden

        # Add gray line across screen
        self.currentrow += 1
        horizontal_line = ttk.Separator(self.root, orient="horizontal")
        horizontal_line.grid(row=self.currentrow, column=0, columnspan=4, sticky="ew", pady=2)

        ################ GENERATE INTERFACE ################
        self.currentrow += 1
        # Label
        self.bokeh_output_file_name_label = tk.Label(self.root, text="Choose filename:")
        self.bokeh_output_file_name_label.config(fg=self.text_color, font=self.font)
        self.bokeh_output_file_name_label.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")

        # Text
        self.bokeh_output_file_name = tk.Text(self.root, height = 1, width=20)
        self.bokeh_output_file_name.insert(tk.INSERT, self.interface.bokeh_output_file_name)
        self.bokeh_output_file_name.grid(row=self.currentrow, column=1, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        # Button
        self.bokeh_output_file_name_button = tk.Button(self.root, text="Apply", command=self.select_bokeh_output_file_name, bg=self.browse_button_color, font=self.button_font) 
        self.bokeh_output_file_name_button.grid(row=self.currentrow, column=3, padx=self.padx, pady=self.pady, sticky="ew") 

        # Generate bokeh self
        self.currentrow += 1
        self.plot_settings = tk.Button(self.root, text="Plot settings", height=5,command=self.plot_setting_window, font=self.button_font)
        self.plot_settings.grid(row=self.currentrow, column=0, padx=self.padx, pady=self.pady, sticky="ew")
    
        self.start = tk.Button(self.root, text="Generate interface", height=5,command=self.interface.create_bokeh, bg=self.text_disabled_color, font=self.button_font, state=tk.DISABLED)
        self.start.grid(row=self.currentrow, column=1, columnspan=3, padx=self.padx, pady=self.pady, sticky="ew")

    # Function to center the window
    def center_window(self):
        '''
        Makes sure the window gets places in the centre of the screen
        '''
        self.root.update_idletasks()  # Update wiow's dimensions
        window_width    = self.root.winfo_width()
        window_height   = self.root.winfo_height()
        screen_width    = self.root.winfo_screenwidth()
        screen_height   = self.root.winfo_screenheight()
        x               = (screen_width - window_width) // 2
        y               = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def select_bokeh_output_file_name(self):
        chosen_filename = self.bokeh_output_file_name.get("1.0", tk.END)
        # Check is the textbox contains any characters
        if len(chosen_filename.strip()) > 0:
            self.interface.bokeh_output_file_name = chosen_filename.strip() 
            self.bokeh_output_file_name_button['bg'] = self.generate_interface_color
        else:
            print("You need to choose a filename that contains characters")
            self.bokeh_output_file_name_button['bg'] = self.browse_button_color

    def use_prev_data_callback(self):
        '''
        Callback for retrieving already calculated data from chosen file. 
        '''
        folderpath = self.previous_data_folder.get("1.0",tk.END).strip()
        if folderpath == '': # If no file is seleced
            self.use_prev_data_alert.grid() # Alert
        else:
            try:
                files_retrieved = [False, False, False, False, False]
                # Retrieve the DataFrames from the text files in the folder
                for filename in os.listdir(folderpath):
                    file_path = os.path.join(folderpath, filename)
                    if os.path.isfile(file_path):
                        # current_df = pd.read_csv(file_path, sep='\t')
                        if filename == 'cells.txt':
                            self.interface.df = pd.read_csv(file_path, sep='\t')
                            files_retrieved[0] = True
                        elif filename == 'circuit.txt':
                            self.interface.circuit_df = pd.read_csv(file_path, sep='\t')
                            files_retrieved[1] = True
                        elif filename == 'impedance_from_fitting.txt':
                            self.interface.impedance_from_fitting_df = pd.read_csv(file_path, sep='\t')
                            files_retrieved[2] = True
                        elif filename == 'DRT.txt':
                            self.interface.DRT_df = pd.read_csv(file_path, sep='\t')
                            files_retrieved[3] = True
                        elif filename == 'predicted_impedance.txt':
                            self.interface.Z_pred_df = pd.read_csv(file_path, sep='\t')
                            files_retrieved[4] = True

                if files_retrieved[0] == False:
                    self.interface.df = pd.DataFrame(data={})
                elif files_retrieved[1] == False:
                    self.interface.circuit_df = pd.DataFrame(data={})
                elif files_retrieved[2] == False:
                    self.interface.impedance_from_fitting_df = pd.DataFrame(data={})
                elif files_retrieved[3] == False:
                    self.interface.DRT_df = pd.DataFrame(data={})
                elif files_retrieved[4] == False:
                    self.interface.Z_pred_df = pd.DataFrame(data={})

                # For loop that ideally should have been avoided, but needs to run for the plots to be properly generated
                self.interface.circuit_base_variables = []
                for col_name in self.interface.circuit_df.columns:
                    if col_name in self.interface.all_base_variables:
                        self.interface.circuit_base_variables.append(col_name)

                # Update the self.area_size and self.area_str, but need to find a way of retrieving this from the dataframe.
                self.interface.area_size = float(self.interface.df.iloc[0]['area'][:-4])

                self.use_prev_data_alert.grid_remove() # Removing the alert

                # Disabling the elements of the window that should not be possible to click
                self.data_folder_label['state']                 = tk.DISABLED
                self.data_folder['state']                       = tk.DISABLED
                self.data_folder_button['state']                = tk.DISABLED
                self.select_circuit_label['state']              = tk.DISABLED
                self.circuit_menu['state']                      = tk.DISABLED
                self.normalize_label['state']                   = tk.DISABLED
                self.normalize_checkbox['state']                = tk.DISABLED
                self.process_button['state']                    = tk.DISABLED
                self.messagebox['state']                        = tk.DISABLED
                self.save_file_folder_label['state']            = tk.DISABLED
                self.save_file_folder['state']                  = tk.DISABLED
                self.save_file_folder['state']                  = tk.DISABLED
                self.save_data['state']                         = tk.DISABLED
                self.previous_data_folder_label['state']        = tk.DISABLED
                self.save_file_folder['state']                  = tk.DISABLED
                self.save_file_folder_button['state']           = tk.DISABLED
                self.save_file_folder_button['state']           = tk.DISABLED
                self.circuit_fit_checkbox['state']              = tk.DISABLED
                self.circuit_fit_label['state']                 = tk.DISABLED
                self.DRT_fit_checkbox['state']                  = tk.DISABLED
                self.DRT_fit_label['state']                     = tk.DISABLED
                self.previous_data_folder_button['state']       = tk.DISABLED
                self.DRT_settings_label['state']                = tk.DISABLED
                self.open_DRT_advanced_setting_button['state']  = tk.DISABLED
                self.fitting_algorithms_label['state']          = tk.DISABLED


                # Enabling the generate_interface-button
                self.use_prev_data.configure(bg=self.generate_interface_color) 
                self.start['state'] = tk.NORMAL
                self.start['bg'] = self.generate_interface_color
            except Exception as e:
                print('use_prev_data_callback: Unable to use the data from the selected folder. Make sure that the selected folder is valid.')
                raise

    def clear_prev_data_callback(self):
        '''
        Callback for undoing the choice of using previous data. 
        '''
        self.interface.df         = pd.DataFrame(data={})
        self.interface.circuit_df = pd.DataFrame(data={})
        self.interface.DRT_df     = pd.DataFrame(data={})
        
        # Opposite to what was done in the use_prev_data_callback-file
        self.use_prev_data_alert.grid_remove() 
        self.data_folder_label['state']                     = tk.NORMAL
        self.data_folder['state']                           = tk.NORMAL
        self.data_folder_button['state']                    = tk.NORMAL
        self.select_circuit_label['state']                  = tk.NORMAL
        self.circuit_menu['state']                          = tk.NORMAL
        self.normalize_label['state']                       = tk.NORMAL
        self.normalize_checkbox['state']                    = tk.NORMAL
        self.process_button['state']                        = tk.NORMAL
        self.messagebox['state']                            = tk.NORMAL
        # self.save_file_folder_label['state']                = tk.NORMAL
        # self.save_file_folder['state']                      = tk.NORMAL
        # self.save_data['state']                             = tk.NORMAL
        # self.save_file_folder_button['state']               = tk.NORMAL
        self.previous_data_folder_label['state']            = tk.NORMAL
        self.circuit_fit_checkbox['state']                  = tk.NORMAL
        self.circuit_fit_label['state']                     = tk.NORMAL
        self.DRT_fit_checkbox['state']                      = tk.NORMAL
        self.DRT_fit_label['state']                         = tk.NORMAL
        self.previous_data_folder_button['state']           = tk.NORMAL
        self.DRT_settings_label['state']                    = tk.NORMAL
        self.open_DRT_advanced_setting_button['state']      = tk.NORMAL
        self.fitting_algorithms_label['state']              = tk.NORMAL

        
        # Disabling the generate_interface-button
        self.use_prev_data.configure(bg=self.browse_button_color)
        self.start['state'] = tk.DISABLED
        self.start['bg']    = self.text_disabled_color

    def save_data_callback(self):
        '''
        Callback for when saving calulated data to file. 
        '''
        if self.interface.df.empty == True: # If no data has been calculated
            self.save_data_choose_file_alert.grid_remove()
            self.save_data_alert.grid()
        else:
            self.save_data_alert.grid_remove()
            # Save data to chosen path
            folderpath = self.save_file_folder.get("1.0",tk.END).strip()
            if folderpath == '': # If no folderpath has been selected
                self.save_data_choose_file_alert.grid()
            else:
                try:
                    self.save_data_choose_file_alert.grid_remove()
                    os.makedirs(folderpath, exist_ok=True)

                    # Remove the already exisiting files before adding the new ones
                    if os.path.isfile(os.path.join(folderpath, 'cells.txt')):
                        os.remove(os.path.join(folderpath, 'cells.txt'))
                    if os.path.isfile(os.path.join(folderpath, 'circuit.txt')):
                        os.remove(os.path.join(folderpath, 'circuit.txt'))
                    if os.path.isfile(os.path.join(folderpath, 'DRT.txt')):
                        os.remove(os.path.join(folderpath, 'DRT.txt'))
                    if os.path.isfile(os.path.join(folderpath, 'impedance_from_fitting.txt')):
                        os.remove(os.path.join(folderpath, 'impedance_from_fitting.txt'))
                    if os.path.isfile(os.path.join(folderpath, 'predicted_impedance.txt')):
                        os.remove(os.path.join(folderpath, 'predicted_impedance.txt'))

                    if not self.interface.df.empty:
                        self.interface.df.to_csv(os.path.join(folderpath, 'cells.txt'), sep='\t', index=False)
                    if not self.interface.circuit_df.empty:
                        self.interface.circuit_df.to_csv(os.path.join(folderpath, 'circuit.txt'), sep='\t', index=False)
                    if not self.interface.impedance_from_fitting_df.empty:
                        self.interface.impedance_from_fitting_df.to_csv(os.path.join(folderpath, 'impedance_from_fitting.txt'), sep='\t', index=False)
                    if not self.interface.DRT_df.empty:
                        self.interface.DRT_df.to_csv(os.path.join(folderpath, 'DRT.txt'), sep='\t', index=False)
                    if not self.interface.Z_pred_df.empty:
                        self.interface.Z_pred_df.to_csv(os.path.join(folderpath, 'predicted_impedance.txt'), sep='\t', index=False)

                    # self.interface.df.to_csv(filepath, sep='\t', index=False)
                    self.save_data.configure(bg=self.generate_interface_color, text="DATA SAVED")
                except Exception as e:
                    raise e

    def select_data_folder(self):
        '''
        Callback for when choosing the folder for the data that will be fitted. 
        '''
        directory               = tk.filedialog.askdirectory(title="Select folder", initialdir=os.getcwd())
        self.data_folder.delete("1.0", tk.END)
        self.interface.data_folder_path   = os.path.basename(directory)
        self.interface.default_path       = directory
        self.data_folder.insert(tk.INSERT, os.path.basename(os.path.basename(directory)))
    
    def select_save_folder(self):
        '''
        Callback for when choosing the folder for the data that will be fitted. 
        '''
        directory = tk.filedialog.askdirectory(title="Select folder", initialdir=os.getcwd())
        self.save_file_folder.delete("1.0", tk.END)
        # self.save_file_folder.insert(tk.INSERT, directory)
        self.save_file_folder.insert(tk.INSERT, directory)
    def select_prev_data_folder(self):
        '''
        Callback for when choosing the folder for the data that will be fitted. 
        '''
        directory = tk.filedialog.askdirectory(title="Select folder", initialdir=os.getcwd())
        self.previous_data_folder.delete("1.0", tk.END)
        self.previous_data_folder.insert(tk.INSERT, directory)

    def auto_run_toggle(self):
        '''
        Toggles the auto-run feature ON and OFF
        '''
        current_state = self.auto_run_button_state.get()
        self.auto_run_button_state.set(not current_state)
        self.interface.auto_run_state = self.auto_run_button_state.get()

        if self.interface.auto_run_state:
            self.auto_run_button.config(text="STOP", bg=self.red_button)

            self.root.after(1, self.interface.auto_run)

        else:
            self.auto_run_button.config(text="START", bg=self.generate_interface_color)
            self.root.after(1, self.interface.auto_run)
    
    def auto_run_checkbox_callback(self):
        if  self.auto_run_checkbox_var.get() == 1:
            self.process_button['state'] = tk.DISABLED
            self.auto_run_button['state'] = tk.NORMAL
            self.auto_run_update_button['state'] = tk.NORMAL
            self.auto_run_min_label['state'] = tk.NORMAL
            self.auto_run_min_textbox['state'] = tk.NORMAL
            self.auto_run_min_label['state'] = tk.NORMAL
            self.auto_run_min_textbox['state'] = tk.NORMAL

            if self.auto_run_button_state.get() == False:
                self.auto_run_button['bg'] = self.generate_interface_color
            else:
                self.auto_run_button['bg'] = self.red_button

        else:
            self.process_button['state'] = tk.NORMAL
            self.auto_run_button['state'] = tk.DISABLED
            self.auto_run_button['bg'] = self.browse_button_color
            self.auto_run_update_button['state'] = tk.DISABLED
            self.auto_run_min_label['state'] = tk.DISABLED
            self.auto_run_min_textbox['state'] = tk.DISABLED
            self.auto_run_min_label['state'] = tk.DISABLED
            self.auto_run_min_textbox['state'] = tk.DISABLED

    def update_auto_run(self):
        self.interface.create_bokeh()
        self.auto_run_update_button['bg']    = self.red_button # Changing the color of the update-button
        self.auto_run_update_button['state'] = tk.DISABLED

    def destroy(self):
        '''
        Function to destroy all plots and all windows
        '''
        self.root.destroy()

    def log(self, message):
        """Logging function to write messages to screen."""
        # Insert the message
        self.messagebox.insert(tk.END, f"{message}\n")
        # Adjust the view to be at the last inserted text
        self.messagebox.see(tk.END)
        # Update so the change is drawed to screen
        # self.froot.update_idletasks()
        self.root.update_idletasks()

    def how_to(self):
        # self.open_README_md()
        # A description of how to run the software
        tk.messagebox.showinfo(
            title="How to",
            # message="How to use the GUI control panel:\n"+
            #         "-------------------------------------------------------------\n\n"+
            #         "Import and process data:\n"+
            #         "- Pick the folder where the data files are located, this is normally the Total_mm folder\n"+
            #         "- Choose whether or not to normalize the data using the Normalize-checkbox\n"+
            #         "- Select which fitting algorithm you wish to use. No fitting algorithm needs to be chosen to just view Nyquist- and Bode-plots\n"+
            #         "- - If Eq.circuit-fitting is chosen, also choose the circuit.\n"+
            #         "- - If DRT-fitting is chosen, also choose the Resolution, Max Iterations and Tolerance. This can drastically affect the runtime.\n"+
            #         "- Press the process button to perform calculation. The process is logged the the window.\n"+
            #         "- After the processing, you have the options of saving the data to a folder. Browse and find an empty(!) folder, and press SAVE to save the data.\n"+
            #         "- Press Generate interface to open a Bokeh-plot.\n\n"+
            #         "Use previous data:\n"+
            #         "- If previous data has been saved, browse and find the folder where the saved data is located.\n"+
            #         "- Press USE PREV DATA to use the saved data, or press CLEAR to instead perform calculations of RAW-data.\n"+
            #         "- Press Generate interface to open a Bokeh-plot.\n\n",
            message="See README_visualize_and_fit.md",
            parent=self.root)

    def about(self):
        # A little bit about the software
        tk.messagebox.showinfo(
            title = "About",
            message = "Author: Elling Svee\n"+
                    "Co-author: Thomas Holm\n"+
                    "Contact: elling.svee@gmail.com\n\n"+
                    "Made at IFE - Institutt for Energiteknologi.\n\n"+
                    "The program is made for plotting, fitting and analysis of EIS data from the setup at IFE.",
                    parent=self.root)
    def choose_circuit(self, circuit_string):
        """Helper function to set the value of the circuit_string when the circuit_menu is used"""
        # Setting the value from the menu to the variable in the string
        self.circuit_string.set(circuit_string)


    def DRT_advanced_setting_window(self):
        """
        When
        ----------
        Called from the advances-settings-button gets pressed
        Does
        ----------
        Lets you choose the setting for the DRT-fitting
        """
        nw = tk.Toplevel(self.root) # New window

        # Call the center_window function after the window is rendered
        nw.after(0, self.center_window)
        
        nw.title("DRT: Advanced settings")
        nw.iconbitmap("ife.ico")     # A IFE logo on the top left corner of the window

        currentrow = 0
        padx = self.padx + 10
        pady = self.pady + 2

        header = tk.Label(nw, text="Advanced settings")
        header.config(fg=self.text_color, font=("Arial", 16))
        header.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky='nsew')
        
        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)

        currentrow += 1
        self.DRT_settings_range_pred_label  = tk.Label(nw, text="Resolution")
        self.DRT_settings_range_pred_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_range_pred_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_range_pred_var     = tk.StringVar()
        self.DRT_settings_range_pred_textbox = tk.Entry(nw, width=10, textvariable=self.DRT_settings_range_pred_var)
        self.DRT_settings_range_pred_textbox.delete(0, tk.END)
        self.DRT_settings_range_pred_textbox.insert(0, str(self.interface.DRT_range_pred))
        self.DRT_settings_range_pred_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")
        
        currentrow += 1
        self.DRT_settings_maxiter_label     = tk.Label(nw, text="Max iterations")
        self.DRT_settings_maxiter_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_maxiter_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_maxiter_var       = tk.StringVar()
        self.DRT_settings_maxiter_textbox   = tk.Entry(nw, width=10, textvariable=self.DRT_settings_maxiter_var)
        self.DRT_settings_maxiter_textbox.delete(0, tk.END)
        self.DRT_settings_maxiter_textbox.insert(0, str(self.interface.DRT_maxiter))
        self.DRT_settings_maxiter_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")
        
        currentrow += 1
        self.DRT_settings_repeat_label   = tk.Label(nw, text="Repeat criterion")
        self.DRT_settings_repeat_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_repeat_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_repeat_var     = tk.StringVar()
        self.DRT_settings_repeat_textbox = tk.Entry(nw, width=10, textvariable=self.DRT_settings_repeat_var)
        self.DRT_settings_repeat_textbox.delete(0, tk.END)
        self.DRT_settings_repeat_textbox.insert(0, str(self.interface.DRT_repeat_criterion))
        self.DRT_settings_repeat_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)

        currentrow += 1
        self.DRT_settings_sigma_n_start_label     = tk.Label(nw, text="sigma_n start")
        self.DRT_settings_sigma_n_start_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_sigma_n_start_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_sigma_n_start_var       = tk.StringVar()
        self.DRT_settings_sigma_n_start_textbox   = tk.Entry(nw, width=10, textvariable=self.DRT_settings_sigma_n_start_var)
        self.DRT_settings_sigma_n_start_textbox.delete(0, tk.END)
        self.DRT_settings_sigma_n_start_textbox.insert(0, str(self.interface.DRT_sigma_n_start))
        self.DRT_settings_sigma_n_start_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        currentrow += 1
        self.DRT_settings_sigma_n_end_label     = tk.Label(nw, text="sigma_n end")
        self.DRT_settings_sigma_n_end_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_sigma_n_end_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_sigma_n_end_var       = tk.StringVar()
        self.DRT_settings_sigma_n_end_textbox   = tk.Entry(nw, width=10, textvariable=self.DRT_settings_sigma_n_end_var)
        self.DRT_settings_sigma_n_end_textbox.delete(0, tk.END)
        self.DRT_settings_sigma_n_end_textbox.insert(0, str(self.interface.DRT_sigma_n_end))
        self.DRT_settings_sigma_n_end_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")
        
        currentrow += 1
        self.DRT_settings_sigma_f_start_label     = tk.Label(nw, text="sigma_f start")
        self.DRT_settings_sigma_f_start_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_sigma_f_start_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_sigma_f_start_var       = tk.StringVar()
        self.DRT_settings_sigma_f_start_textbox   = tk.Entry(nw, width=10, textvariable=self.DRT_settings_sigma_f_start_var)
        self.DRT_settings_sigma_f_start_textbox.delete(0, tk.END)
        self.DRT_settings_sigma_f_start_textbox.insert(0, str(self.interface.DRT_sigma_f_start))
        self.DRT_settings_sigma_f_start_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        currentrow += 1
        self.DRT_settings_sigma_f_end_label     = tk.Label(nw, text="sigma_f end")
        self.DRT_settings_sigma_f_end_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_sigma_f_end_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_sigma_f_end_var       = tk.StringVar()
        self.DRT_settings_sigma_f_end_textbox   = tk.Entry(nw, width=10, textvariable=self.DRT_settings_sigma_f_end_var)
        self.DRT_settings_sigma_f_end_textbox.delete(0, tk.END)
        self.DRT_settings_sigma_f_end_textbox.insert(0, str(self.interface.DRT_sigma_f_end))
        self.DRT_settings_sigma_f_end_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")
        
        currentrow += 1
        self.DRT_settings_ell_start_label         = tk.Label(nw, text="ell start")
        self.DRT_settings_ell_start_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_ell_start_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_ell_start_var           = tk.StringVar()
        self.DRT_settings_ell_start_textbox       = tk.Entry(nw, width=10, textvariable=self.DRT_settings_ell_start_var)
        self.DRT_settings_ell_start_textbox.delete(0, tk.END)
        self.DRT_settings_ell_start_textbox.insert(0, str(self.interface.DRT_ell_start))
        self.DRT_settings_ell_start_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        currentrow += 1
        self.DRT_settings_ell_end_label         = tk.Label(nw, text="ell end")
        self.DRT_settings_ell_end_label.config(fg=self.text_color, font=self.font)
        self.DRT_settings_ell_end_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="w")

        self.DRT_settings_ell_end_var           = tk.StringVar()
        self.DRT_settings_ell_end_textbox       = tk.Entry(nw, width=10, textvariable=self.DRT_settings_ell_end_var)
        self.DRT_settings_ell_end_textbox.delete(0, tk.END)
        self.DRT_settings_ell_end_textbox.insert(0, str(self.interface.DRT_ell_end))
        self.DRT_settings_ell_end_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        # Add gray line across screen
        currentrow      += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)

        # Make an apply button
        currentrow += 1
        # Button for clearing the choice of opening previous file
        self.apply_advanced_settings = tk.Button(
            nw, text="APPLY", bg=self.red_button, font=self.button_font, command=self.apply_advanced_settings_callback
        )
        self.apply_advanced_settings.grid(row=currentrow, column=0, columnspan=2, pady=pady, sticky="ew")

        currentrow += 1
        # Alert if not all settings have values
        self.choose_all_advanced_settings_alert = tk.Label(nw, text='Enter values for all settings')
        self.choose_all_advanced_settings_alert.config(fg=self.red_button, font=self.font)
        self.choose_all_advanced_settings_alert.grid(row=currentrow, column=0, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        self.choose_all_advanced_settings_alert.grid_remove() # Itialize as hidden

    def apply_advanced_settings_callback(self):
        if (self.DRT_settings_range_pred_var.get() != '' and
        self.DRT_settings_maxiter_var.get() != '' and self.DRT_settings_repeat_var.get() != '' and
        self.DRT_settings_sigma_n_start_var.get() != '' and self.DRT_settings_sigma_n_end_var.get() != '' and
        self.DRT_settings_sigma_f_start_var.get() != '' and self.DRT_settings_sigma_f_end_var.get() != '' and 
        self.DRT_settings_ell_start_var.get() != ''and self.DRT_settings_ell_end_var.get() != ''):
            
            self.choose_all_advanced_settings_alert.grid_remove() # Itialize as hidden
            
            self.interface.DRT_range_pred    = int(self.DRT_settings_range_pred_var.get())
            self.interface.DRT_maxiter    = int(self.DRT_settings_maxiter_var.get())
            self.interface.DRT_repeat_criterion    = int(self.DRT_settings_repeat_var.get())
            self.interface.DRT_sigma_n_start    = float(self.DRT_settings_sigma_n_start_var.get())
            self.interface.DRT_sigma_n_end   = float(self.DRT_settings_sigma_n_end_var.get())
            self.interface.DRT_sigma_f_strat    = float(self.DRT_settings_sigma_f_start_var.get())
            self.interface.DRT_sigma_f_end    = float(self.DRT_settings_sigma_f_end_var.get())
            self.interface.DRT_ell_start    = float(self.DRT_settings_ell_start_var.get())
            self.interface.DRT_ell_end    = float(self.DRT_settings_ell_end_var.get())
            self.apply_advanced_settings.configure(bg=self.generate_interface_color) 
        else: 
            self.choose_all_advanced_settings_alert.grid() # Alert

    def plot_setting_window(self):
        """
        When
        ----------
        Called when the plot-settings-button gets pressed
        Does
        ----------
        Lets you choose the setting for the appearence of the plot
        """
        nw = tk.Toplevel(self.root) # New window

        # Call the center_window function after the window is rendered
        nw.after(0, self.center_window)
        
        nw.title("Plot settings")
        nw.iconbitmap("ife.ico")     # A IFE logo on the top left corner of the window

        currentrow = 0
        padx = self.padx + 10
        pady = self.pady + 2

        header = tk.Label(nw, text="Plot settings")
        header.config(fg=self.text_color, font=("Arial", 16))
        header.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky='nsew')

        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)
        
        currentrow += 1
        self.plot_settings_axes_roundoff_label  = tk.Label(nw, text="Axis roundoff (number of decimals)")
        self.plot_settings_axes_roundoff_label.config(fg=self.text_color, font=self.font)
        self.plot_settings_axes_roundoff_label.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.plot_settings_axes_roundoff_var     = tk.StringVar()
        self.plot_settings_axes_roundoff_textbox = tk.Entry(nw, width=10, textvariable=self.plot_settings_axes_roundoff_var)
        self.plot_settings_axes_roundoff_textbox.delete(0, tk.END)
        self.plot_settings_axes_roundoff_textbox.insert(0, str(self.interface.axes_roundoff_decimals))
        self.plot_settings_axes_roundoff_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")


        currentrow += 1
        # Label
        self.display_res_in_milli_label = tk.Label(nw, text="Resistance in milliOhm (Y/N):")
        self.display_res_in_milli_label.config(fg=self.text_color, font=self.font)
        self.display_res_in_milli_label.grid(row=currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        # Checkbox
        self.display_res_in_milli_checkbox_var = tk.IntVar()
        if self.interface.display_res_in_milli == True:
            self.display_res_in_milli_checkbox_var.set(1)
        else: 
            self.display_res_in_milli_checkbox_var.set(0)
        self.display_res_in_milli_checkbox = tk.Checkbutton(nw, variable=self.display_res_in_milli_checkbox_var, onvalue=1, offvalue=0)
        self.display_res_in_milli_checkbox.grid(row=currentrow, column=1, padx=self.padx, pady=self.pady, sticky="E")
        
        currentrow += 1
        # Label
        self.display_cap_in_milli_label = tk.Label(nw, text="Capcitance in milliFarad (Y/N):")
        self.display_cap_in_milli_label.config(fg=self.text_color, font=self.font)
        self.display_cap_in_milli_label.grid(row=currentrow, column=0, padx=self.padx, pady=self.pady, sticky="W")
        # Checkbox
        self.display_cap_in_milli_checkbox_var = tk.IntVar()
        if self.interface.display_cap_in_milli == True:
            self.display_cap_in_milli_checkbox_var.set(1)
        else:
            self.display_cap_in_milli_checkbox_var.set(0)
        self.display_cap_in_milli_checkbox = tk.Checkbutton(nw, variable=self.display_cap_in_milli_checkbox_var, onvalue=1, offvalue=0)
        self.display_cap_in_milli_checkbox.grid(row=currentrow, column=1, padx=self.padx, pady=self.pady, sticky="E")


        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)

             
        # Make an apply button
        currentrow += 1
        # Button for clearing the choice of opening previous file
        self.apply_plot_settings = tk.Button(
            nw, text="APPLY", bg=self.red_button, font=self.button_font, command=self.apply_plot_settings_callback
        )
        self.apply_plot_settings.grid(row=currentrow, column=0, columnspan=2, pady=pady, sticky="ew")

        currentrow += 1
        # Alert if not all settings have values
        self.choose_all_plot_settings_alert = tk.Label(nw, text='Enter valid values for all settings')
        self.choose_all_plot_settings_alert.config(fg=self.red_button, font=self.font)
        self.choose_all_plot_settings_alert.grid(row=currentrow, column=0, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        self.choose_all_plot_settings_alert.grid_remove() # Itialize as hidden
  
    def apply_plot_settings_callback(self):
        if self.plot_settings_axes_roundoff_var.get() != '' and int(self.plot_settings_axes_roundoff_var.get()) > -1:
            self.interface.axes_roundoff_decimals = int(self.plot_settings_axes_roundoff_var.get())
            
            self.interface.display_res_in_milli = (self.display_res_in_milli_checkbox_var.get() == 1)
            self.interface.display_cap_in_milli = (self.display_cap_in_milli_checkbox_var.get() == 1)


            self.choose_all_plot_settings_alert.grid_remove() # Itialize alert as hidden
            self.apply_plot_settings.configure(bg=self.generate_interface_color) 
        else:
            self.choose_all_plot_settings_alert.grid() # Alert



    def Z_pred_setting_window(self):
        """
        When
        ----------
        Called from the Z_pred-settings-button gets pressed
        Does
        ----------
        Lets you choose the setting for the impedance prediction
        """
        nw = tk.Toplevel(self.root) # New window

        # Call the center_window function after the window is rendered
        nw.after(0, self.center_window)
        
        nw.title("Prediction settings")
        nw.iconbitmap("ife.ico")     # A IFE logo on the top left corner of the window

        currentrow = 0
        padx = self.padx + 10
        pady = self.pady + 2

        header = tk.Label(nw, text="Prediction settings")
        header.config(fg=self.text_color, font=("Arial", 16))
        header.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky='nsew')

        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)
        
        currentrow += 1
        temp_label1  = tk.Label(nw, text="Min factor (Min predicted frequency = Min experimental frequency * Min factor):")
        temp_label1.config(fg=self.text_color, font=self.font)
        temp_label1.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.Z_pred_min_factor_var     = tk.StringVar()
        self.Z_pred_min_factor_textbox = tk.Entry(nw, width=10, textvariable=self.Z_pred_min_factor_var)
        self.Z_pred_min_factor_textbox.delete(0, tk.END)
        self.Z_pred_min_factor_textbox.insert(0, str(self.interface.Z_pred_min_factor))
        self.Z_pred_min_factor_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        currentrow += 1
        temp_label3  = tk.Label(nw, text="Max factor (Max predicted frequency = Max experimental frequency * Max factor)")
        temp_label3.config(fg=self.text_color, font=self.font)
        temp_label3.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.Z_pred_max_factor_var     = tk.StringVar()
        self.Z_pred_max_factor_textbox = tk.Entry(nw, width=10, textvariable=self.Z_pred_max_factor_var)
        self.Z_pred_max_factor_textbox.delete(0, tk.END)
        self.Z_pred_max_factor_textbox.insert(0, str(self.interface.Z_pred_max_factor))
        self.Z_pred_max_factor_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        currentrow += 1
        temp_label3  = tk.Label(nw, text="Number of predictions")
        temp_label3.config(fg=self.text_color, font=self.font)
        temp_label3.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.Z_pred_num_var     = tk.StringVar()
        self.Z_pred_num_textbox = tk.Entry(nw, width=10, textvariable=self.Z_pred_num_var)
        self.Z_pred_num_textbox.delete(0, tk.END)
        self.Z_pred_num_textbox.insert(0, str(self.interface.Z_pred_num))
        self.Z_pred_num_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)

        currentrow += 1
        temp_label4  = tk.Label(nw, text="Max iterations")
        temp_label4.config(fg=self.text_color, font=self.font)
        temp_label4.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.Z_pred_maxiter_var     = tk.StringVar()
        self.Z_pred_maxiter_textbox = tk.Entry(nw, width=10, textvariable=self.Z_pred_maxiter_var)
        self.Z_pred_maxiter_textbox.delete(0, tk.END)
        self.Z_pred_maxiter_textbox.insert(0, str(self.interface.Z_pred_maxiter))
        self.Z_pred_maxiter_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")
        
        currentrow += 1
        temp_label5  = tk.Label(nw, text="Tolerance")
        temp_label5.config(fg=self.text_color, font=self.font)
        temp_label5.grid(row=currentrow, column=0, padx=padx, pady=pady, sticky="W")

        self.Z_pred_tolerance_var     = tk.StringVar()
        self.Z_pred_tolerance_textbox = tk.Entry(nw, width=10, textvariable=self.Z_pred_tolerance_var)
        self.Z_pred_tolerance_textbox.delete(0, tk.END)
        self.Z_pred_tolerance_textbox.insert(0, str(self.interface.Z_pred_tolerance))
        self.Z_pred_tolerance_textbox.grid(row=currentrow, column=1, padx=padx, pady=pady, sticky="ew")

        # Add gray line across screen
        currentrow += 1
        horizontal_line = ttk.Separator(nw, orient="horizontal")
        horizontal_line.grid(row=currentrow, column=0, columnspan=2, sticky="ew", pady=2)
             
        # Make an apply button
        currentrow += 1
        # Button for clearing the choice of opening previous file
        self.apply_Z_pred_settings = tk.Button(
            nw, text="APPLY", bg=self.red_button, font=self.button_font, command=self.apply_Z_pred_settings_callback
        )
        self.apply_Z_pred_settings.grid(row=currentrow, column=0, columnspan=2, pady=pady, sticky="ew")

        currentrow += 1
        # Alert if not all settings have values
        self.choose_all_Z_pred_settings_alert = tk.Label(nw, text='Enter valid values for all settings')
        self.choose_all_Z_pred_settings_alert.config(fg=self.red_button, font=self.font)
        self.choose_all_Z_pred_settings_alert.grid(row=currentrow, column=0, columnspan=2, padx=self.padx, pady=self.pady, sticky="ew")
        self.choose_all_Z_pred_settings_alert.grid_remove() # Itialize as hidden

    def apply_Z_pred_settings_callback(self):
        if True:
            self.interface.Z_pred_min_factor = float(self.Z_pred_min_factor_var.get())
            self.interface.Z_pred_max_factor = float(self.Z_pred_max_factor_var.get())
            self.interface.Z_pred_num = int(self.Z_pred_num_var.get())  
            self.interface.Z_pred_tolerance = float(self.Z_pred_tolerance_var.get())
            self.interface.Z_pred_maxiter = int(self.Z_pred_maxiter_var.get())  
            

            self.choose_all_Z_pred_settings_alert.grid_remove() # Itialize alert as hidden
            self.apply_Z_pred_settings.configure(bg=self.generate_interface_color) 