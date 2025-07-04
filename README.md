# System overviev

All python files located in .\ and described within this README.md are called directly by the class and functions present within EIS_experiment_main.py. All the files located in .\dependencies\ are called indirectly as helpers for the classes located in .\ and described here.

## EIS_main.py

Contains and runs a class that, on init, maintains the necessary functions and info to run and process the data of specified EIS experiments.

### Member Variables

- num_picoscopes
- channels
- gui

>Num_picoscopes is an int representing the number of active picoscopes.
>
>Channels is an array representing all the possible channels and whether they are active.
>
>The gui varable is a class of the type EIS_GUI as described in the section EIS_GUI.py.

### Member Functions

- start_and_process_measurements(self)
- do_experiment(num_picoscopes, channels, range_of_freqs, bias, amplitude, constants, parameters, time_path) (as a static method)
- process_data(self, resistor_value, num_freqs, save_path, parameters)
- open_fitting(self)

>Start_and_process_measurements collects parameters from the GUI. Then it spawns a multiprocessing Pool running do_experiment. If the "Immediately process data" checkbox is ticked, it will then call the process_data function.
>
>Do_experiment is run as a seperate multiprocess, alowing measurements to be taken at the same time as previous are processed. The function sets up a QApplication and a qasync loop before creating an EIS_experiment and calling it to run. See the description for EIS_experiment.py for further details.
>
>Process_data collects the active indexes for current and voltage measurements and creates a data_processer object before calling it to start processing all files at a specified path. See the section on data_processer.py for further details.
>
>Open_fitting creates a dashboard_for_plotting_and_fitting interface object as specified in the section dashboard_for_plotting_and_fitting interface.py.

## EIS_GUI.py

Contains a class that, on init, creates a GUI that allows one to run custom EIS experiments. It contains fields for writing parameters for EIS experiments, in addition to buttons to call the start_and_process_measurements() and open_fitting() functions of the EIS_main class.

## EIS_experiment.py

Contains a class that will run and perform measurements on experiment specified with its given parameters.

## data_processor.py

## dashboard_for_plotting_and_fitting.py

## Extra notes

There is additional documentation located in .\further_documentation\ Do note, however, that some of the documentation may be partially outdated, such as refering to control_main which no longer exists.
