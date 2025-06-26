'''
Short description:
    Contains functions used retrieve data from filesystem and perform fitting and predictions based on this data.
Why:
    Separate these algorithms into seperate file in order to make interface-class in dashboard_for_plotting_and_fitting.py cleaner.

Depends on:
    circuit_handler.py
@author: Elling Svee (elling.svee@gmail.com) 
Edited by Emma Roverso  (emmaerov@gmail.com)
'''

import os
import math
import pandas as pd         # For sorting file structure
import time
import numpy as np
from datetime import datetime # For sorting dates
from dependencies.RR_GP_DRT import fit_DRT
import dependencies.DRT_fitting
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from dependencies.tkinter_window import tkinter_class




def retrieve_data(interface):
    """
    When
    ----------
    Called from the process-function
    Does
    ----------
    Retrieves the data from the selected directory, and formats it in a way so that it can be used when creating the Bokeh-plots. 
    
    Note
    ----------
    The data is stored in a Pandas Dataframe, and this df will be used at the source for the Bokeh-plot
    """
    # List for collection and combining dataframes from the individual folders
    dfs = []
    # Timing and logging the process
    interface.tw.log(f"Started retrieving data.")
    start_time = time.time()

    checkbool = False

    df = pd.DataFrame(data={})
    # Iterating through the directory
    for root, dirs, files in os.walk(interface.default_path, topdown=True):  
        for dir_name in dirs:
            path_to_params = os.path.join(interface.default_path, dir_name, 'Parameters.txt')

            # Only running the following code if the Parameters.txt file exists
            if os.path.exists(path_to_params):


                # Path has been found and Parameters.txt text file is identified, now we can add all the parameters from the file to the script
                f = open(path_to_params,'r')
                lines = f.readlines()
                date_text           = lines[0].strip('\n').strip().split("\t").pop(1)
                time_text           = lines[1].strip('\n').strip().split("\t").pop(1)
                area_text           = lines[4].strip('\n').strip().split("\t").pop(1)
                temperature_text    = lines[5].strip('\n').strip().split("\t").pop(1)
                pressure_text       = lines[6].strip('\n').strip().split("\t").pop(1)
                dccurrent_text      = lines[7].strip('\n').strip().split("\t").pop(1)
                accurrent_text      = lines[8].strip('\n').strip().split("\t").pop(1)

                params_string       = date_text + "_" + time_text + "_" + area_text + "_" + temperature_text + "_" + pressure_text + "_" + dccurrent_text + "_" + accurrent_text # F.ex 2023-05-28-_1401-38_86_50_1_3.4_40
                cell_name_array     = lines[3].strip('\n').strip().split("\t").pop(1).split(',') # F.ex ['2', '3', '4', '5', '6', '7']

                # Iterate throught the files within the folder, which wave been stored in the temp_files_in_watch-folder
                path_to_files = os.path.join(interface.default_path,dir_name)
                for root, dirs, files in os.walk(path_to_files):
                    sorting_array = []
                    # Interate through the individual files in the subdriectories
                    for filename in files:
                        # print(f"filename = {filename}")
                        # Find files that have mmfile in the text, these are the data files
                        if "mmfile" in filename and "bak" not in filename:
                            # print(f"YES")
                            # temp_files_in_watch.append(filename) # Testing
                            # print(f"filename = {filename}")
                            ending = filename.split('.').pop(0).split('_')[2]
                            # print(f"ending = {ending}")
                            # print(f'Ending: {ending}')  # For testing
                            sorting_array.append(int(ending))
                    sorting_array.sort()
                    for num in range(0,len(sorting_array)):  
                         # Open file
                        filename_here = "total_mmfile_"+str(sorting_array[num])+".mmfile"
                        path_to_file = os.path.join(root,filename_here)
                        f = open(path_to_file,'r')
                        lines = f.readlines()
                        # Arrays that will be filled with values 
                        frequencies = []
                        realvalues = []
                        imaginaryvalues = []                        
                        magnitude = []
                        phase_angle = []


                        for i in range(1,len(lines)):
                            # Check if line has values (ie. not the uppermost line). Does probably not need the if-statement since all files are on the same format
                            if any(chr.isdigit() for chr in lines[i]):
                                # Retrieving the data from the files, and some basic calculations to get the magnitue and phase angle 
                                frequencies.append(lines[i].strip('\n').strip().split("\t")[0])
                                # print(f"area_text = {area_text}")

                                real_norm = float(lines[i].strip('\n').strip().split("\t")[1])
                                imag_norm = -float(lines[i].strip('\n').strip().split("\t")[2])
                                phase_angle_value = np.arctan2(imag_norm,real_norm)*180/math.pi
                                phase_angle.append(phase_angle_value)
                                if interface.tw.normalize_checkbox_var.get() == 1: # Normalizing
                                    real_norm *= float(area_text)
                                    imag_norm *= float(area_text)
                                realvalues.append(real_norm)
                                imaginaryvalues.append(imag_norm)
                                magnitude_norm = np.sqrt(real_norm**2 + imag_norm**2)
                                magnitude.append(magnitude_norm)

                        if checkbool == True: # To be deleted
                            print(f"frequencies = {frequencies}")
                            print(f"realvalues = {realvalues}")
                            print(f"imaginaryvalues = {imaginaryvalues}")
                            checkbool = False

                        params_string_individual_cell = "data_" + params_string + "_" + cell_name_array[num]

                        # Creating a dataframe that includes all the individual values retrieved from the files in the subdirectory
                        temp_df = pd.DataFrame({'frequencies': frequencies, 'realvalues': realvalues, 'imaginaryvalues': imaginaryvalues, 'magnitude': magnitude, 'phase_angle': phase_angle})
                        temp_df = temp_df.astype(float)

                        split_string = params_string_individual_cell.split('_')
                        temp_df['cell_name'] = 'Cell '+ str(split_string[8])
                        temp_df['date'] = str(datetime.strptime(params_string_individual_cell.split('_')[1][:-1], '%Y-%m-%d').date())
                        temp_df['time'] = str(datetime.strptime(params_string_individual_cell.split('_')[2][:], '%H%M-%S').time())
                        temp_df['temp'] = str(split_string[4])+"\u00b0C"
                        temp_df['pressure'] = str(split_string[5]+" bar")
                        temp_df['dc'] = str(split_string[6]+" A")
                        temp_df['ac'] = str(split_string[7]+" %")
                        temp_df['area'] = str(split_string[3]+" cm^2")
                        temp_df['dir_name'] = dir_name
                        temp_df['path_to_file'] = path_to_file

                        # Normalizing, if checkbox is checked
                        if interface.tw.normalize_checkbox_var.get() == 1:
                            # temp_df['realvalues'] *= float(split_string[3])
                            # temp_df['imaginaryvalues'] *= float(split_string[3])
                            # temp_df['magnitude'] *= float(split_string[3])
                            temp_df['normalized'] = 'True'
                        else:
                            temp_df['normalized'] = 'False'

                        dfs.append(temp_df.copy())


    if dfs == []: # In case no dataframes has been created
        df = pd.DataFrame(columns=['frequencies', 'realvalues', 'imaginaryvalues', 'magnitude', 'phase_angle', 'cell_name', 'date', 'time', 'area', 'temp', 'pressure', 'dc', 'ac', 'dir_name', 'normalized'])
    else:
        df = pd.concat(dfs, ignore_index=True) # Combining all smaller dataframe to one big one
    interface.tw.log(f"Finished retrieving. Total time: {round(time.time()-start_time, 2)} sec.")
    return df.drop_duplicates().copy() 
    

def retrieve_process(interface, df, dir_name):
    """
    Does
    ----------
    Logs that it has started to process. Then it initiates a inherited class of the
    BaseCircuitHandles from the circuit_process_and_plot.py. Then the
    BaseCircuitHandler methods process and plot are called.
    Note
    ----------
    If an error occur or input is invalid, this will be logged to the message board
    and the function will terminate.
    """

    dir_path = os.path.join(interface.default_path,dir_name)
    # circuit_handler = interface.find_circuit_type(
    #     dir_name, ''
    # )

    circuit_handler = interface.find_circuit_type(
        dir_path, ''
    )
    temp_output_data, temp_variables, temp_files_in_watch, temp_Z_fits = circuit_handler.process()

    # Adding the predicted impedances to a df
    temp_impedance_df = df.loc[(df['dir_name'] == dir_name), ['frequencies', 'cell_name', 'date', 'path_to_file', 'temp', 'dc', 'ac', 'pressure']]
    for i, file_path in enumerate(circuit_handler.files_in_watch):
        temp_impedance_df.loc[temp_impedance_df['path_to_file'] == file_path, 'impedance'] = temp_Z_fits[file_path]
    temp_impedance_df['dir_name'] = dir_name

    return temp_output_data, temp_variables, temp_files_in_watch, temp_impedance_df
    

def fit_with_circuit(interface, df):
    """
    When
    ----------
    Called from the process-function

    Does
    ----------
    Fits the data using the selected circuit, and also formats this in such a way that it can be plotted. 
    
    Note
    ----------
    The data is stored in a Pandas Dataframe, and this df will be used at the source for the Bokeh-plot
    """
    interface.tw.log('Started circuit-fitting:')
    start_time = time.time()
    current_time = start_time

    # print(df)
    # circuit_df = df[['cell_name', 'date', 'dir_name', 'path_to_file', 'area', 'frequencies']]
    circuit_df = df[['cell_name', 'date', 'dir_name', 'path_to_file', 'area']]
    circuit_df = circuit_df.drop_duplicates()
    # impedance_df = df[['path_to_file',  'frequencies', 'cell_name', 'date', 'dir_name']]
    # impedance_df = impedance_df.drop_duplicates()
    base_variables = []


    impedance_dfs=[]
    dir_names = circuit_df['dir_name'].unique()
    for i in range(len(dir_names)):
        temp_output_data, temp_base_variables, temp_files_in_watch, temp_impedance_df = retrieve_process(interface, df, dir_names[i])
        impedance_dfs.append(temp_impedance_df)

        # Normalizing the fitted variables
        if interface.tw.normalize_checkbox_var.get() == 1:
            for j, variable in enumerate(temp_base_variables): 
                if "R" in variable:
                    # self.units[i] += f"{self.area_str}"
                    temp_output_data[:, j] *= float(interface.area_size)
                elif "C" in variable and not "alpha" in variable:
                    # self.units[i] += f"/{self.area_str}"
                    temp_output_data[:, j] /= float(interface.area_size)
                elif "L" in variable:
                    # self.units[i] += f"{self.area_str}"
                    temp_output_data[:, j] *= float(interface.area_size)
        
        if i == 0:
            for base_variable in temp_base_variables:
                base_variables.append(base_variable)
                circuit_df[base_variable] = None
        for j, filepath in enumerate(temp_files_in_watch):
            for k, base_variable in enumerate(temp_base_variables):
                circuit_df.loc[circuit_df['path_to_file'] == filepath, base_variable] = temp_output_data[j][k]

        interface.tw.log(f"- Circuit-fitting: Done with {i+1} out of {len(dir_names)} folders. Time: {round(time.time()-current_time,2)} sec.")
        current_time = time.time()

    # Add column with the earliest date
    earliest_date = pd.to_datetime(circuit_df['date']).min()
    circuit_df['hours_since_first_date'] = (pd.to_datetime(circuit_df['date']) - earliest_date).dt.total_seconds() / 3600

    # Calculating the upper and lower calues for the standard deivations. The Whisker-errorbar in Bokeh required that the data was given in this way            
    R_std_dev_names = []
    C_std_dev_names = []
    for base_variable in base_variables:
        for std_dev_name in ["std_Re", "std_R1", "std_R2", "std_R3", "std_R4"]:
            if std_dev_name[4:] == base_variable:
                R_std_dev_names.append(std_dev_name)
                circuit_df[std_dev_name + '_lower'] = circuit_df[base_variable] - circuit_df[std_dev_name]
                circuit_df[std_dev_name + '_upper'] = circuit_df[base_variable] + circuit_df[std_dev_name]
        for std_dev_name in ["std_C1", "std_C2", "std_C3"]:
            if std_dev_name[4:] == base_variable:
                C_std_dev_names.append(std_dev_name)
                circuit_df[std_dev_name + '_lower'] = circuit_df[base_variable] - circuit_df[std_dev_name]
                circuit_df[std_dev_name + '_upper'] = circuit_df[base_variable] + circuit_df[std_dev_name]

    # Calculating the standard-deviation for the total Resistance and Capacitance. NB: This calculating assumes that the variables ('std_R1', 'std_R2' etc.) are independent n order to avoid having to esitmate the covariance.
    if 'TotR' in base_variables:
        tot_var_df = 0
        for std_dev_name in R_std_dev_names:                    
            tot_var_df += circuit_df[std_dev_name]**2
        tot_std_dev_df = tot_var_df**(0.5)
        circuit_df['TotR' + '_upper'] = circuit_df['TotR'] + tot_std_dev_df
        circuit_df['TotR' + '_lower'] = circuit_df['TotR'] - tot_std_dev_df

    if 'TotC' in base_variables:
        tot_var_df = 0
        for std_dev_name in C_std_dev_names:                    
            tot_var_df += circuit_df[std_dev_name]**2
        tot_std_dev_df = tot_var_df**(0.5)
        circuit_df['TotC' + '_upper'] = circuit_df['TotC'] + tot_std_dev_df
        circuit_df['TotC' + '_lower'] = circuit_df['TotC'] - tot_std_dev_df
    # Using the tau-values to calculate the characteristic frequenies

    for time_val in [r"$\tau$ 1", r"$\tau$ 2", r"$\tau$ 3"]:
        if time_val in base_variables:
            circuit_df['char_freq' + time_val[-1]] = 1 / circuit_df[time_val]


    impedance_df = pd.concat(impedance_dfs, ignore_index=True).drop_duplicates().copy()
    # Create new columns only including the real- and imag-parts of the impedance in the impedance_df
    impedance_df['impedance_real'] = impedance_df['impedance'].apply(lambda x: x.real)
    impedance_df['impedance_imag'] = impedance_df['impedance'].apply(lambda x: x.imag)
    # Inverting the imaginary part
    impedance_df['impedance_imag'] *= -1 
    # Removing the 'impedance'-column from the dataframe
    impedance_df.drop('impedance', axis=1, inplace=True)

    # # # Normalizing the impedances variables (OBS)
    if interface.tw.normalize_checkbox_var.get() == 1:
        impedance_df['impedance_real'] = impedance_df['impedance_real'] * float(interface.df.iloc[0]['area'][:-4])
        impedance_df['impedance_imag'] = impedance_df['impedance_imag'] * float(interface.df.iloc[0]['area'][:-4])

    # To plot the fitted impedance in the bode-plot aswell
    impedance_df['magnitude'] = np.sqrt(np.square(impedance_df['impedance_real']) + np.square(impedance_df['impedance_imag']))
    impedance_df['phase_angle'] = np.arctan2(impedance_df['impedance_imag'],impedance_df['impedance_real'])*180/math.pi

    interface.tw.log(f"Finished circuit-fitting. Total time: {round(time.time()-start_time,2)} sec.")

    # Fixing issue when applying logarithmic scale to the y-axes
    for col in circuit_df.columns:
        if col in ["Re_lower", "R1_lower", "R2_lower", "R3_lower", "R4_lower", "TotR_lower", "C1_lower", "C2_lower", "C3_lower", "TotC_lower",
                   "Re_upper", "R1_upper", "R2_upper", "R3_upper", "R4_upper", "TotR_upper", "C1_upper", "C2_upper", "C3_upper", "TotC_upper"]:
            circuit_df[col] = np.maximum(circuit_df[col], 1e-6)


    return circuit_df.drop_duplicates().copy(), impedance_df.drop_duplicates().copy(), base_variables



def fit_with_DRT(interface, df):
    """
    This function is called from dashboard_for_plotting_and_fitting by the process method.

    It iterates through data before fitting, and manages the results in a pandas frame. 

    Dependent on RR_GP_DRT.py which depends on GP_DRT.py

    Parameters
    ----------
    interface : object
        Instance of the Interface class defined in dashboard_for_plotting_and_fitting.py

    df : pandas DataFrame
        DataFrame containing experimental data

    Returns
    ---------
    DRT_df : pandas DataFrame
        DataFrame containing data produced by DRT fitting.
    """
    interface.tw.log('Started DRT-fitting:')
    start_time   = time.time()


    dfs = []
    # Iterate through dits
    dir_names           = df['dir_name'].unique()
    cell_names          = df['cell_name'].unique()
    
    if interface.log_hyperparameters:
        log_file = open("hyppar_log.csv", "w")
        log_file.write(f"dataset,sigma_n,sigma_f,ell,loss\n")
        log_file.close()

    for i, dir_name in enumerate(dir_names):
        for cell_name in cell_names:
            interface.current = f"{cell_name} in {dir_name}"

            real_vals = np.array(df.loc[(df["dir_name"] == dir_name) & (df["cell_name"] == cell_name), 'realvalues'].tolist())
            imag_vals = np.array(df.loc[(df["dir_name"] == dir_name) & (df["cell_name"] == cell_name), 'imaginaryvalues'].tolist())
            Z_exp = real_vals - 1j*imag_vals #Imagenary numbers must be inverted

            freq_vec = np.array(df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'frequencies'].tolist())
            #dict with result data to be passed and filled
            data = {
                    'freq_vec_star'         :np.zeros(interface.DRT_range_pred), 
                    'gamma_vec_star'        :np.zeros(interface.DRT_range_pred),
                    'Sigma_gamma_vec_star'  :np.zeros(interface.DRT_range_pred), 
                    'Z_imag_star'           :np.zeros(interface.DRT_range_pred),
                    'Z_real_star'           :np.zeros(interface.DRT_range_pred) 
                    }
            try:
                # Perform DRT
                fit_DRT(Z_exp, freq_vec, data, interface)
                # Insert collected data into dataframe
                temp_df = pd.DataFrame.from_dict(data)
                temp_date = df.loc[df['dir_name'] == dir_name]['date'].values[0]

                temp_df['cell_name']    = cell_name
                temp_df['dir_name']     = dir_name
                temp_df['date']         = temp_date
                dfs.append(temp_df)
            except Exception as e:
                print(f"Unexpected {e=}, {type(e)=}")
                interface.tw.log("fit_with_DRT -> DRT_fitting.fit_data: Unable to retrieve fitted data.")
                raise

        interface.tw.log(f"{dir_name} folder done")
            

    interface.tw.log(f"- DRT-fitting: Done with {i+1} out of {len(dir_names)} folders. Time: {round(time.time()-start_time,2)} sec.")

    DRT_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    return DRT_df
    
def predict_impedances(interface, df):
    """
    When
    ----------
    Called from the process-function
    Does
    ----------
    Interpolates and extrapolated the impedance-data by utilizing the same framework as the DRT-fitting.
    
    Note
    ----------
    The data is stored in a Pandas Dataframe, and this df will be used at the source for the Bokeh-plot.
    The interpolation of the data can be improved, since the DRT-method only fits the imaginary part of the experimental impedances.
    """
    interface.tw.log('Started predicting impedances:')
    start_time   = time.time()
    current_time = start_time

    dfs = []
    # Iterate through dits
    dir_names           = df['dir_name'].unique()
    cell_names          = df['cell_name'].unique()

    # print(f"dir_names = {dir_names}")
    for i, dir_name in enumerate(dir_names):
        # Iterate_through cells
        temp_date = df.loc[df['dir_name'] == dir_name]['date'].values[0]
        for cell_name in cell_names:

            real_vals = np.array(df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'realvalues'].tolist())
            imag_vals = np.array(df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'imaginaryvalues'].tolist())

            try:
                # Perform DRT
                freq_vec_star, Z_re_vec_star, Z_im_vec_star, error_lower, error_upper = dependencies.DRT_fitting.predict_impedance(
                    interface, 
                    df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'frequencies'].tolist(),
                    real_vals,
                    imag_vals
                ) 
            except:
                interface.tw.log("fit_with_DRT -> DRT_fitting.fit_data: Unable to retrieve fitted data.")
                raise

            # Add to DRT_df
            temp_df = pd.DataFrame(data={
                    'freq_vec_star'         :   freq_vec_star, 
                    'Z_re_vec_star'         :   Z_re_vec_star,
                    'Z_im_vec_star'         :   Z_im_vec_star,
                    'error_lower'           :   error_lower, 
                    'error_upper'           :   error_upper
                    })

            temp_df['cell_name']    = cell_name
            temp_df['dir_name']     = dir_name
            temp_df['date']         = temp_date

            temp_df['temp']         = df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'temp'].unique()[0]
            temp_df['pressure']         = df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'pressure'].unique()[0]
            temp_df['dc']         = df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'dc'].unique()[0]
            temp_df['ac']         = df.loc[(df["dir_name"] == dir_name) & (df['cell_name'] == cell_name), 'ac'].unique()[0]


            dfs.append(temp_df)

    Z_pred_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    interface.tw.log(f"Finished predicting impedance. Total time: {round(time.time()-start_time,2)} sec.")
    return Z_pred_df
