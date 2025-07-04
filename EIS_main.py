import os
import tkinter.simpledialog
import tkinter as tk 
import numpy as np
from multiprocessing import Pool
from datetime import datetime
from PySide6.QtWidgets import QApplication
import sys
import asyncio
import qasync
from math import log10


import EIS_GUI
import EIS_experiment
import data_processor
import dashboard_for_plotting_and_fitting as fitting_dash

class EIS_main:
    def __init__(self) -> None:

        scopes = tk.simpledialog.askstring(title="Picoscopes",prompt="How many picoscopes?")
        self.num_picoscopes = int(float(scopes))

        self.channels = np.zeros((self.num_picoscopes,4), dtype = bool)
        for picoscope_index in range(self.num_picoscopes):
            chn_diag = tk.simpledialog.askstring(title=f"Picoscope {picoscope_index+1}",
                                                    prompt=f"Write answer with 1 for yes, 0 for no, in one number. Ex: 1100 for chA and chB.\nChannels in picoscope {picoscope_index+1}:")
            for channel_index in range(4):
                self.channels[picoscope_index,channel_index] = bool(float(chn_diag[channel_index]))

        self.gui = EIS_GUI.EIS_GUI(self.num_picoscopes, self.channels, self.start_and_process_measurements, self.open_fitting, self.open_processing)
        self.gui.root.mainloop()
        
    def start_and_process_measurements(self) -> None:
        """
        Called when
        ---------
        Called by a button press from the GUI.

        Description
        ----
        Collects all parameters from the GUI.

        Then confirms you wish to proceed, before calling do_experiment with collected parameters.

        If the "Immediately process data" checkbox is checked, it will also call process_data.
        """

        self.gui.log("Starting measurements")
        
        # Collecting parameters from the GUI
        experiment_parameters, save_metadata = self.gui.collect_parameters()

        # Acceptance test on cell numbers
        num_channels = sum(sum(self.channels))
        if len(save_metadata["cell_numbers"].split(",")) != num_channels - self.num_picoscopes:
            self.gui.log("Error: must have the same number of cells as voltage channels")
            return

        # Collecting the current and potential ranges
        experiment_ranges = np.array([experiment_parameters["current_range"],
                                        experiment_parameters["stack_potential_range"],
                                        experiment_parameters["cell_potential_range"]])

        # Collecting the correct frequencies depending on inputted settings
        if self.gui.manual_freq_check.get():
            selected_frequencies = experiment_parameters["selected_frequencies"].split(",")
            temporary_frequencies = []
            for frequency in selected_frequencies:
                temporary_frequencies.append(float(frequency))
            range_of_freqs = np.array(temporary_frequencies)
            num_freqs = len(range_of_freqs)
        else:
            max_freq = experiment_parameters["max_frequency"]
            min_freq = experiment_parameters["min_frequency"]
            steps_per_decade = experiment_parameters["steps_per_decade"]
            
            num_decades = log10(max_freq) - log10(min_freq)
            num_freqs = int(num_decades) * steps_per_decade
            range_of_freqs = np.logspace(log10(max_freq), log10(min_freq), num=num_freqs, endpoint=True, base=10)

            selected_frequencies = ""
            for frequency in range_of_freqs:
                selected_frequencies = selected_frequencies + str(frequency) + ","
            selected_frequencies = selected_frequencies[:-1]
            save_metadata["selected_frequencies"] = selected_frequencies
        
        # Collecting the EIS parameters
        bias = experiment_parameters["bias"]
        amplitude = bias * experiment_parameters["amplitude"]
        low_freq_periods = experiment_parameters["low_freq_periods"]
        sleep_time = experiment_parameters["sleep_time"]
        resistor_value = experiment_parameters["resistor_value"]

        # Finding the time and date of experiment start to create the save folders
        date_today = datetime.today().strftime("%Y-%m-%d-")
        time_now = datetime.now().strftime("%H%M-%S")
        time_path = date_today + time_now

    
        do_experiment = tk.messagebox.askyesnocancel("Query to continue", "Do you wish to proceed with experiment?")
        if do_experiment:
            if not os.path.exists(f"Raw_data\\{time_path}"):
                os.makedirs(f"Raw_data\\{time_path}")
            
            # Spawns a multiprocessing pool object to perform the measurements
            pool = Pool(processes=1)
            pool.apply_async(self.do_experiment, [self.num_picoscopes,
                                                    self.channels,
                                                    experiment_ranges,
                                                    range_of_freqs,
                                                    bias, 
                                                    amplitude,
                                                    low_freq_periods,
                                                    sleep_time,
                                                    time_path, 
                                                    save_metadata])


            if self.gui.process_data_check.get():
                processed_path = f"Save_folder\\{time_path}"
                if not os.path.exists(processed_path):
                    os.makedirs(processed_path)

                # Starts to process data immediately as each measurement is completed
                self.process_data(resistor_value,
                                    num_freqs,
                                    time_path,
                                    save_metadata)

    @staticmethod
    def do_experiment(num_picoscopes        : int,
                        channels            : np.ndarray[tuple[int,int], bool],
                        experiment_ranges   : np.ndarray[tuple[int], int],
                        range_of_freqs      : np.ndarray[tuple[int], float],
                        bias                : float,
                        amplitude           : float,
                        low_freq_periods    : float,
                        sleep_time          : float, 
                        time_path           : str,
                        save_metadata       : dict[str, str]
    ) -> bool:
        """
        Parameters
        ----------
        num_picoscopes : int
                Represents the number of picoscopes to take measurement from
        channels : ndarray
                2D array containing data with 'bool' type representing the active picoscope channels
        experiment_ranges : ndarray
                1D array containing the current and potential ranges of the experiment
        range_of_freqs : ndarray
                1D array containing data with 'float' type representing all frequencies to run EIS with
        bias : float
                Represents the applied DC current bias
        amplitude : float
                Represents the amplitude of the applied AC current
        low_freq_periods : float
                Represents the number of periods to run for frequencies < 10 Hz
        sleep_time : float
                Represents the number of seconds of DC current to run before and after the EIS experiment
        time_path : str
                The date and time used to create the folder to save results from the EIS
        save_metadata : dict
                Dictionary containing all required metadata for saving files.

        Called when
        ----------
        Called by start_and_process_measurements as the job of a multiprocessing.pool.Pool worker.

        Description
        ----------
        Creates an EIS_experiment object and waits for it to finish running perform_experiment.        
        """

        # Starts all loops necessary for interfacing with hardware
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        # Creates an experiment object with the inputted parameters
        experiment = EIS_experiment.EIS_experiment(num_picoscopes,
                                                    channels,
                                                    experiment_ranges,
                                                    range_of_freqs,
                                                    bias,
                                                    amplitude,
                                                    low_freq_periods,
                                                    sleep_time, 
                                                    time_path,
                                                    save_metadata)

        # Waits for all measurements to be complete and then closes the loops
        with loop:
            loop.run_until_complete(experiment.perform_experiment())
            #loop.run_until_complete(experiment.pico_setup())
            #experiment.pico_close()
        app.quit()
        return True
        #experiment.plot()

    def process_data(self,
                        resistor_value  : int,
                        num_freqs       : int,
                        save_path       : str,
                        save_metadata   : dict[str, str]
    ) -> None:
        
        # Loops through and gets all the active current and voltage channels
        channel_index_in_file = 1
        current_channels_watch_imp = ""
        voltage_channels_watch_imp = ""
        for picoscope_index in range(self.num_picoscopes):
            current_channels_watch_imp += "," +str(channel_index_in_file)
            channel_index_in_file += 1
            for channel_index in range(1,4):
                if self.channels[picoscope_index,channel_index]:
                    voltage_channels_watch_imp += ","+str(channel_index_in_file)
                    channel_index_in_file += 1
        current_channels_watch_imp = current_channels_watch_imp[1:]
        voltage_channels_watch_imp = voltage_channels_watch_imp[1:]
        print("Current channels used: " + current_channels_watch_imp)
        print("Voltage channels used: "+ voltage_channels_watch_imp)

        # Creates a data processor object and starts processing data
        processor = data_processor.Data_processor(current_channels_watch_imp,
                                                voltage_channels_watch_imp,
                                                resistor_value,
                                                num_freqs,
                                                save_path,
                                                self.num_picoscopes,
                                                self.channels,
                                                save_metadata)
        processor.start_processing()

    def open_processing(self) -> None:
        
        experiment_parameters, save_metadata = self.gui.collect_parameters()

        resistor_value = experiment_parameters["resistor_value"]

        if self.gui.manual_freq_check.get():
                    num_freqs =  len(experiment_parameters["selected_frequencies"].split(","))
        else:
            max_freq = experiment_parameters["max_frequency"]
            min_freq = experiment_parameters["min_frequency"]
            steps_per_decade = experiment_parameters["steps_per_decade"]
            num_decades = log10(max_freq) - log10(min_freq)
            num_freqs = int(num_decades) * steps_per_decade
            range_of_freqs = np.logspace(log10(max_freq), log10(min_freq), num=num_freqs, endpoint=True, base=10)
            
            selected_frequencies = ""
            for frequency in range_of_freqs:
                selected_frequencies = selected_frequencies + str(frequency) + ","
            selected_frequencies = selected_frequencies[:-1]
            save_metadata["selected_frequencies"] = selected_frequencies

        date_today = datetime.today().strftime("%Y-%m-%d-")
        time_now = datetime.now().strftime("%H%M-%S")
        save_path = date_today + time_now
        save_path = "2025-07-03-1519-44"
        channel_index_in_file = 1
        current_channels_watch_imp = ""
        voltage_channels_watch_imp = ""
        for picoscope_index in range(self.num_picoscopes):
            current_channels_watch_imp += "," +str(channel_index_in_file)
            channel_index_in_file += 1
            for channel_index in range(1,4):
                if self.channels[picoscope_index,channel_index]:
                    voltage_channels_watch_imp += ","+str(channel_index_in_file)
                    channel_index_in_file += 1
        current_channels_watch_imp = current_channels_watch_imp[1:]
        voltage_channels_watch_imp = voltage_channels_watch_imp[1:]
        print("Current channels used: " + current_channels_watch_imp)
        print("Voltage channels used: "+ voltage_channels_watch_imp)

        data_processor.Data_processor(current_channels_watch_imp,
                                                voltage_channels_watch_imp,
                                                resistor_value,
                                                num_freqs,
                                                save_path,
                                                self.num_picoscopes,
                                                self.channels,
                                                save_metadata)
        
    def open_fitting(self) -> None:

        self.gui.log("Opening fitting window")
        fitting_dash.interface()

if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.abspath(__file__))
    folder_names = ['Save_folder', 'Total_mm', 'Raw_data']
    for folder_name in folder_names:
        temp_folder_path = os.path.join(current_directory, folder_name)
        if not os.path.exists(temp_folder_path):
            try:
                os.makedirs(temp_folder_path)
                print(f"Folder '{folder_name}' created successfully in {current_directory}.")
            except OSError as e:
                print(f"Error occurred while creating folder '{folder_name}': {e}")
        else:
            print(f"Folder '{folder_name}' already exists in {current_directory}.")
            
    EIS_main()