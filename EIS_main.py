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
import time
from math import log10

import EIS_GUI
import EIS_experiment
import data_processor
import dashboard_for_plotting_and_fitting as fitting_dash

class EIS_main:
    def __init__(self):
        scopes = tk.simpledialog.askstring(title="Picoscopes",prompt="How many picoscopes?")
        self.num_picoscopes = int(float(scopes))

        self.channels = np.zeros((self.num_picoscopes,4))
        for picoscope_index in range(self.num_picoscopes):
            chn_diag = tk.simpledialog.askstring(title=f"Picoscope {picoscope_index+1}",
                                                    prompt=f"Write answer with 1 for yes, 0 for no, in one number. Ex: 1100 for chA and chB.\nChannels in picoscope {picoscope_index+1}:")
            for channel_index in range(4):
                self.channels[picoscope_index,channel_index] = int(float(chn_diag[channel_index]))

        self.gui = EIS_GUI.EIS_GUI(self.num_picoscopes, self.channels, self.start_and_process_measurements, self.open_fitting, self.open_processing)
        self.gui.root.mainloop()
        
    def start_and_process_measurements(self):
        self.gui.log("Starting measurements")

        parameters, constants = self.gui.collect_parameters()

        num_channels = 0
        for picoscop_index in range(self.num_picoscopes):
            for channel_index in range(4):
                num_channels += self.channels[picoscop_index, channel_index]

        if len(parameters["cell_numbers"].split(",")) != num_channels - self.num_picoscopes:
            self.gui.log("Error: must have the same number of cells as voltage channels")
            return

        if self.gui.manual_freq_check.get():
            selected_frequencies = parameters["selected_frequencies"].split(",")
            range_of_freqs = []
            for frequency in selected_frequencies:
                range_of_freqs.append(float(frequency))
            num_freqs = len(range_of_freqs)
        else:
            max_freq = float(parameters["max_frequency"])
            min_freq = float(parameters["min_frequency"])
            steps_per_decade = int(parameters["steps_per_decade"])
            
            num_decades = log10(max_freq) - log10(min_freq)
            num_freqs = int(num_decades) * steps_per_decade
            range_of_freqs = np.logspace(log10(max_freq), log10(min_freq), num=num_freqs, endpoint=True, base=10)

            selected_frequencies = ""
            for frequency in range_of_freqs:
                selected_frequencies = selected_frequencies + str(frequency) + ","
            selected_frequencies = selected_frequencies[:-1]
            parameters["selected_frequencies"] = selected_frequencies
                
        bias = float(parameters["DC_current"])
        amplitude = bias * float(parameters["AC_current"])
        low_freq_periods = float(parameters["low_freq_periods"])

        sleep_time = float(parameters["sleep_time"])

        date_today = datetime.today().strftime("%Y-%m-%d-")
        time_now = datetime.now().strftime("%H%M-%S")
        time_path = date_today + time_now
        
        save_path = f"Raw_data\\{time_path}"
    
        do_experiment = tk.messagebox.askyesnocancel("Query to continue", "Do you wish to proceed with experiment?")
        
        if do_experiment:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            pool = Pool(processes=1)
            pool.apply_async(self.do_experiment, [self.num_picoscopes, self.channels, range_of_freqs, bias, amplitude, low_freq_periods, sleep_time, constants, parameters, time_path])

            if self.gui.process_data_check.get():
                processed_path = f"Save_folder\\{time_path}"
                if not os.path.exists(processed_path):
                    os.makedirs(processed_path)

                resistor_value = parameters["resistor_value"]

                self.process_data(resistor_value, num_freqs, time_path, parameters)

    @staticmethod
    def do_experiment(num_picoscopes, channels, range_of_freqs, bias, amplitude, low_freq_periods, sleep_time, constants, parameters, time_path):

        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        experiment = EIS_experiment.EIS_experiment(num_picoscopes, channels, range_of_freqs, bias, amplitude, low_freq_periods, sleep_time, constants, parameters, time_path)

        with loop:
            loop.run_until_complete(experiment.perform_experiment())
        app.quit()

        experiment.plot()

    def process_data(self, resistor_value, num_freqs, save_path, parameters):
        counter = 1
        current_channels_watch_imp = ""
        voltage_channels_watch_imp = ""
        for picoscope_index in range(self.num_picoscopes):
            current_channels_watch_imp += "," +str(counter)
            counter += 1
            for channel_index in range(1,4):
                if self.channels[picoscope_index,channel_index]:
                    voltage_channels_watch_imp += ","+str(counter)
                    counter += 1
        current_channels_watch_imp = current_channels_watch_imp[1:]
        voltage_channels_watch_imp = voltage_channels_watch_imp[1:]
        print("Current channels used: " + current_channels_watch_imp)
        print("Voltage channels used: "+ voltage_channels_watch_imp)

        processor = data_processor.Data_processor(current_channels_watch_imp,
                                                voltage_channels_watch_imp,
                                                resistor_value,
                                                num_freqs,
                                                save_path,
                                                self.num_picoscopes,
                                                self.channels,
                                                parameters)
        time.sleep(1)
        processor.start_processing()

    def open_processing(self):
        parameters, _ = self.gui.collect_parameters()
        resistor_value = parameters["resistor_value"]
        num_freqs =  len(parameters["selected_frequencies"].split(","))
        date_today = datetime.today().strftime("%Y-%m-%d-")
        time_now = datetime.now().strftime("%H%M-%S")
        save_path = date_today + time_now

        counter = 1
        current_channels_watch_imp = ""
        voltage_channels_watch_imp = ""
        for picoscope_index in range(self.num_picoscopes):
            current_channels_watch_imp += "," +str(counter)
            counter += 1
            for channel_index in range(1,4):
                if self.channels[picoscope_index,channel_index]:
                    voltage_channels_watch_imp += ","+str(counter)
                    counter += 1
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
                                                parameters)

    def open_fitting(self):
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