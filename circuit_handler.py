"""
Circuit handler

Short description:
----------
This is a helper file to the impedance fitter function "folder_fitting.py". It uses the 
impedance modlue, which in turn calles the scipy module to do the actual fitting. The file
contains a abstract base class called BaseCircuitHandler and many subclasses (inhereted 
classes) of this base class for each of the implemented circuits. 
(the abstract part means that this class cannot be instantiated)
The are named "Circuit_circuitstring" mening that a
parrallell coupling of resistor and capasitor is "Circuit_p(R1,C1)". The main mathods are
process, plot and load exsisting. The file also contains a dictionary of the implemented 
circuit called "IMPLEMENTED_CIRCUITS" where the keys are the circuit_string and the values
are the Class initialiser. Then there is a get_circuit_handler that takes a circuit string
and returns the class initaliser, but if the circuit string does not exsist it returns None.

Edits by Elling:
Made the files functionality more fitting to be used in the dashboard run by the file dashboard_for_plotting_and_fitting2.py.
Added functions that will calculate the impedance for the different circuits based on the estimated parameters.

@author: Christoffer Askvik Faugstad (christoffer.askvik.faugstad@hotmail.com)
@co-author: Elling Svee (elling.svee@gmail.com)
"""
import time
from impedance.models.circuits.circuits import CustomCircuit
import numpy as np
import os
import matplotlib.pyplot as plt
import math 

# Base class for all circuit handlers
class BaseCircuitHandler:
    """
    Short description:
    ----------
    A Virtual class that all the other Circuit hanlder classes inherit from.
    The virtual part means that this class cannot be instantiated directly
    but need a subclass that has implemented the functions:
    get_bounds,
    get_initial_guess,
    get_new_indicies,
    update_output_data,
    plot_output_data,
    as these are only declared and not implemented in this class.

    Main methods:
    ----------
    process :
        Loops thorgh the files in file_dir and fit the impedance data
        to the circuit in the class
    load_exsisting:
        Loads output data from a file into the class.
    plot :
        Plot the resulting output data from either process or load_exsisting
    """
    def __init__(
        self, file_dir, save_file_path, log, area_str='', area_size=-1
    ) -> None:
        """
        Create a instance, called by subclasses

        Parameters:
        ----------
        - file_dir: The directory where the class should get the impedance specters from.
        - save_file_path: The full filepath to where the resulting fit should be stored.
        - log: The function that log the messages, i.e. log(message) results in a message being shown
        - area_str: The string representation of the normalization unit, e.g. "cm^2". None if nothing
            is provided as input.
        - are_size: The are that should be normalized over, then in the units coresponding to the
            string provided in area_str.
        """
        # Checking that the save_file_path is valid
        if save_file_path != "":
            # Assert it is a text fiel
            if save_file_path[-4:] != ".txt":
                raise FileNotFoundError(
                    f"Could not use the following as a save file {save_file_path}"
                )
            # Check that a input folder has been selected
            if file_dir == "":
                raise FileNotFoundError(f"No input folder is selected.")
            # Check that the input folder path exsists
            if not os.path.exists(file_dir):
                raise FileNotFoundError(
                    f"The input folder path\n{file_dir}\nis not valid."
                )
            # Check that the directory to the save_file_path exists
            if not os.path.exists(os.path.dirname(save_file_path)):
                raise FileNotFoundError(
                    f"The output file path\n{save_file_path}\nis not valid."
                )
        # Check that a save_file_path has been selected
        # if save_file_path == "" and file_dir != "":
        #     raise FileNotFoundError(f"No save file is selected.")
        # Check that files should be found
        if file_dir != "":
            #  Search for valid input files
            self.files_in_watch = [
                os.path.join(file_dir, file)  # The full file path
                for file in os.listdir(file_dir)  # Loops through the things in file_dir
                # Check if it is a file and has the right ending
                if os.path.isfile(os.path.join(file_dir, file))
                and file[-7:] == ".mmfile"
            ]
            # Check that the folder contained some mmfiles
            if len(self.files_in_watch) == 0:
                raise FileNotFoundError(f"No files found in the folder {file_dir}")
            else:
                # Sort the files on the integer interpetation of the string behind the last "_"
                self.files_in_watch.sort(key=lambda f: int(f.split("_")[-1][:-7]))

        # print(f"self.files_in_watch = {self.files_in_watch}")
        
        # Storing the inputvaues in the object
        self.file_dir = file_dir
        self.save_file_path = save_file_path
        self.log = log
        self.output_data = None
        self.area_str = area_str
        self.area_size = float(area_size)
        
        # if save_file_path != "":
        #     # Assert it is a text fiel
        #     if save_file_path[-4:] != ".txt":
        #         raise FileNotFoundError(
        #             f"Could not use the following as a save file {save_file_path}"
        #         )
        #     # Check that a input folder has been selected
        #     if file_dir == "":
        #         raise FileNotFoundError(f"No input folder is selected.")
        #     # Check that the input folder path exsists
        #     if not os.path.exists(file_dir):
        #         raise FileNotFoundError(
        #             f"The input folder path\n{file_dir}\nis not valid."
        #         )
        #     # Check that the directory to the save_file_path exists
        #     if not os.path.exists(os.path.dirname(save_file_path)):
        #         raise FileNotFoundError(
        #             f"The output file path\n{save_file_path}\nis not valid."
        #         )
        # # Check that a save_file_path has been selected
        # if save_file_path == "" and file_dir != "":
        #     raise FileNotFoundError(f"No save file is selected.")
        # # Check that files should be found
        # if file_dir != "":
        #     #  Search for valid input files
        #     self.files_in_watch = [
        #         os.path.join(file_dir, file)  # The full file path
        #         for file in os.listdir(file_dir)  # Loops through the things in file_dir
        #         # Check if it is a file and has the right ending
        #         if os.path.isfile(os.path.join(file_dir, file))
        #         and file[-7:] == ".mmfile"
        #     ]
        #     # Check that the folder contained some mmfiles
        #     if len(self.files_in_watch) == 0:
        #         raise FileNotFoundError(f"No files found in the folder {file_dir}")
        #     else:
        #         # Sort the files on the integer interpetation of the string behind the last "_"
        #         self.files_in_watch.sort(key=lambda f: int(f.split("_")[-1][:-7]))
        # # Storing the inputvaues in the object
        # self.file_dir = file_dir
        # self.save_file_path = save_file_path
        # self.log = log
        # self.output_data = None
        # self.area_str = area_str
        # self.area_size = area_size

    # Default units of the different components
    R_unit = "Ohm"
    C_unit = "F"
    t_unit = "s"
    L_unit = "H"
    CPE_Q_unit = "S s^alpha"
    CPE_alpha_unit = "1"

    #### Process part ####
    # The empty methods the subclasses need to implement
    def get_bounds(self):
        ...

    def get_initial_guess(self):
        ...

    def get_new_indicies(self):
        ...


    def update_output_data(self, parameters, deviations, chiN):
        ...

    def get_header(self):
        # Template to make each label be as long as the floats displayed
        template = "{0:25}"
        return "".join(
            template.format(f"{variable}[{unit}]")
            for variable, unit in zip(self.variables, self.units)
        )

    def do_initial_step(self):
        """
        The function that does the initial fitting of the parameters.

        Note: Are redifine for some subclasses that need different
        parameters for the fit call.
        """
        # Create the CustomCircuit from impedance module
        self.circuit = CustomCircuit(
            self.circuit_string, initial_guess=self.get_initial_guess()
        )
        # Get the data to fit to
        f, Z = BaseCircuitHandler.load_MMFILE(self.files_in_watch[0])


        # For timing the process
        start_time = time.time()
        # Fitting data, global_opt=True, means that the basinhopping algorith of
        # scipy is used, meaning that it searches for a golbal minimum.
        self.circuit.fit(f, Z, bounds=self.get_bounds())  # ,global_opt=True)
        # Log the time used
        # self.log(f"Time spent on first fit: {time.time()-start_time}")
        # Set the parameter values as the inital_guess for the next fitting
        initial_guess = list(self.circuit.parameters_)
        self.circuit.initial_guess = initial_guess
        # Create the output_data array
        self.output_data = np.zeros(
            (
                len(self.files_in_watch),
                2 * self.num_parameters
                + self.num_taus
                + self.num_tot
                + 1,  # +1 from chi/n
            )
        )
        # Creates a new index list so that one can sort the values on some criteria
        self.new_indicies = self.get_new_indicies()

    def do_steps(self):
        """
        Loops through all the files in files_in_watch and fits the impedance data
        to the circuit.
        """
        # Looping through files
        self.Z_fits = {}
        for i, file_path in enumerate(self.files_in_watch):


            # Loading the data that should be fitted

            
            f, Z = BaseCircuitHandler.load_MMFILE(file_path)


            # Fitting data with bounds
            self.circuit.fit(f, Z, bounds=self.get_bounds())

            # print( self.circuit.fit(f, Z, bounds=self.get_bounds())) # Testing

            # Getting the predicted values to calculate the chi/N value for the fit
            self.Z_fits[file_path] = self.circuit.predict(f)
            chiN = (
                np.sqrt(
                    np.sum(
                        (Z.real - self.Z_fits[file_path].real) * (Z.real - self.Z_fits[file_path].real)
                        + (Z.imag - self.Z_fits[file_path].imag) * (Z.imag - self.Z_fits[file_path].imag)
                    )
                    / Z.size
                )
                / f.size
            )


            # Storing the data in output_data
            self.update_output_data(
                i, self.circuit.parameters_, self.circuit.conf_, chiN
            )
            # Loging how far the process has come
            # self.log(f"Done with {i+1} of {len(self.files_in_watch)}")
            # Setting the previous parameters as the new initial_guess
            self.circuit.initial_guess = list(self.circuit.parameters_)

    def normalize(self):
        """
        Called to normalize data, does this if self.area_str is somthing
        different than None. If it is None nothing happens.
        """
        print(f"self.area_size = {self.area_size}")
        if self.area_size != float(-1):

            print(f'Inside the normalization-part of the circuit_handler')
            for i, variable in enumerate(self.variables): 
                if "R" in variable:
                    # self.units[i] += f"{self.area_str}"
                    self.output_data[:, i] *= self.area_size
                elif "C" in variable and not "alpha" in variable:
                    # self.units[i] += f"/{self.area_str}"
                    self.output_data[:, i] /= self.area_size
                elif "L" in variable:
                    # self.units[i] += f"{self.area_str}"
                    self.output_data[:, i] *= self.area_size
        #                elif variable == "Chivalue":
        #                    self.units[i] += f"/{self.area_str}"
        #                    self.output_data[:, i] *= self.area_size
        else:
            pass

    def process(self):
        """
        Does the hole process of fitting a folder of files to the circuit
        and stores the values in the save_file_path.
        Also logs how long time the function takes.
        """
        total_start_time = time.time()
        self.do_initial_step()
        self.do_steps()

        return self.output_data, self.variables, self.files_in_watch, self.Z_fits

        # Unsure if this works
        # if self.save_file_path != '':
        #     np.savetxt(
        #         self.save_file_path, self.output_data, header=self.get_header(), comments=""
        #     )
        #     self.log(
        #         f"Finshed processing and stored the values to:\n{self.save_file_path}\nUsed {np.round(time.time()-total_start_time,2)} s."
        #     )


    @staticmethod
    def load_MMFILE(file_path):
        """
        Method that does not require and instanse of the class to be called,
        i.e. used as 'BaseCircuitHandler.load_MMFILE(filepath)'. Returns the
        frequencies and impedance (complex number) as np.arrays
        """
        data = np.loadtxt(file_path, skiprows=1)
        frequencies = data[:, 0]
        imp = data[:, 1] + data[:, 2] * 1j
        return frequencies, imp

    #### Plot part ####
    def plot_output_data(self):
        ...

    def plot(self,save=False):
        """Creates a matplotlib figure and plots the output_data to this."""
        # Create figure and axis
        self.figure, self.axis = plt.subplots()
        # Seting the tilte to be the name of the save_file_path filename
        # self.figure.canvas.set_window_title(os.path.basename(self.save_file_path)) # This causes an error

        # Ploting to the axis
        self.plot_output_data()
        # Showing the plot, block = False to not freez the rest of the program
        plt.show(block=False)
        # if save:
        #     plt.savefig("EISmodules\\Folder_fit\\folder_fit_plot.pdf")

    def normalize_units(self):
        """
        Called to get the right units on the plot if a normalization is used.
        Does only update the units is the are_str is not None
        """
        # if not self.area_str is None:
        if self.area_str != '':
            for i, variable in enumerate(self.variables):
                if "R" in variable:
                    self.units[i] += f"/{self.area_str}"
                elif "C" in variable and not "alpha" in variable:
                    self.units[i] += f"{self.area_str}"
                elif "L" in variable:
                    self.units[i] += f"/{self.area_str}"
                elif variable == "Chivalue":
                    self.units[i] += f"/{self.area_str}"
        else:
            pass

    def load_existing(self, exsisting_file_path):
        """
        Loads exsisting data into the circuit handler and calls the normalize_units
        to update the units if a normalization has been done
        """
        # Load the data, skiprows = 1 to skip the header
        self.output_data = np.loadtxt(exsisting_file_path, skiprows=1)
        # Updating units is normalized
        self.normalize_units()
        # Checking that the data shape matches the circuit type
        if self.output_data.shape[1] != len(self.variables):
            expected_num = len(self.variables)
            raise ValueError(
                f"The file does not contain the correct circuit data. Found ({self.output_data.shape[1]}) columns but expected {expected_num} ,in the file: \n{exsisting_file_path}"
            )


"""
Now the implementation of subclasses of BaseCircuitHandler follow,
the format is:

####    circuit_string  ####

class Circuit_circuitstring(BaseCircuitHandler):
    circuit_string: str, the string describing the circuit
    
    num_parameters: int, the number of parameters that are in the circuit
    
    num_taus: int, the number of time constants in the circuit
    
    num_tot: int, number of totals in the circuit
    
    base_variables: tuple (str,str,...) A tuple of all the different names of
        the variables in the circuit, used to the labels, is made a tuple so 
        it is inmutable(cannot be changed). 
    
    base_units: tuple (str,str,...) A tuple of the units of the different
        variables. Used the variables form BaseCircuitHandles.X_unit commonly.

    Init function, calles the base init function and creates variables and unit list
    for this spesific instanse so that the can be modified if normalized.
    def __init__(self, file_dir, save_file_path, log,area_str = None,area_size = 1):
        BaseCircuitHandler.__init__(self, file_dir, save_file_path, log,area_str=area_str,area_size=area_size)
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return array of same size as num_parameters

    def get_bounds(self):
        return array of size (2,num_parameters) with bounds


    def get_new_indicies(self):
        return list of indicies to be used in update_output_data

    def update_output_data(self, i, parameters, deviations, chiN):
        store the correct parameters and deviations to the correct
        indicies in the output array

    def plot_output_data(self):
        with self.figure and self.axis plots the fit values as a function of the order
    
    Can also here redefine the do_initial_step or do_steps if needed
        
"""


####    "R0-p(R1,C1)-p(R2,C2)-p(R3,C3)" ####


class Circuit_R0pR1C1pR2C2pR3C3(BaseCircuitHandler):
    circuit_string = "R0-p(R1,C1)-p(R2,C2)-p(R3,C3)"
    num_parameters = 7
    num_taus = 3
    num_tot = 2
    base_variables = (
        "Re",
        "R1",
        "R2",
        "R3",
        "C1",
        "C2",
        "C3",
        "std_Re",
        "std_R1",
        "std_R2",
        "std_R3",
        "std_C1",
        "std_C2",
        "std_C3",
        r"$\tau$ 1",
        r"$\tau$ 2",
        r"$\tau$ 3",
        "TotR",
        "TotC",
        "Chivalue",
    )
    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.ones(self.num_parameters) * 0.01

    def get_bounds(self):
        return np.array([[0, np.inf] for i in range(self.num_parameters)]).T

    def get_new_indicies(self):
        indicies = [1, 3, 5]
        time_constants = [
            self.circuit.initial_guess[1] * self.circuit.initial_guess[2],
            self.circuit.initial_guess[3] * self.circuit.initial_guess[4],
            self.circuit.initial_guess[5] * self.circuit.initial_guess[6],
        ]
        return [index for _, index in sorted(zip(time_constants, indicies))]

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[self.new_indicies[0]]  # R1
        self.output_data[i, 2] = parameters[self.new_indicies[1]]  # R2
        self.output_data[i, 3] = parameters[self.new_indicies[2]]  # R3
        self.output_data[i, 4] = parameters[self.new_indicies[0] + 1]  # C1
        self.output_data[i, 5] = parameters[self.new_indicies[1] + 1]  # C2
        self.output_data[i, 6] = parameters[self.new_indicies[2] + 1]  # C3
        self.output_data[i, 7] = deviations[0]  # std_R0
        self.output_data[i, 8] = deviations[self.new_indicies[0]]  # std_R1
        self.output_data[i, 9] = deviations[self.new_indicies[1]]  # std_R2
        self.output_data[i, 10] = deviations[self.new_indicies[2]]  # std_R3
        self.output_data[i, 11] = deviations[self.new_indicies[0] + 1]  # std_C1
        self.output_data[i, 12] = deviations[self.new_indicies[1] + 1]  # std_C2
        self.output_data[i, 13] = deviations[self.new_indicies[2] + 1]  # std_C3
        self.output_data[i, 14] = (
            self.output_data[i, 1] * self.output_data[i, 4]
        )  # tau1
        self.output_data[i, 15] = (
            self.output_data[i, 2] * self.output_data[i, 5]
        )  # tau2
        self.output_data[i, 16] = (
            self.output_data[i, 3] * self.output_data[i, 6]
        )  # tau3
        self.output_data[i, 17] = (
            parameters[0] + parameters[1] + parameters[3] + parameters[5]
        )  # TotR
        self.output_data[i, 18] = 1 / (
            1 / parameters[2] + 1 / parameters[4] + 1 / parameters[6]
        )  # TotC
        self.output_data[i, 19] = chiN  # Chi/N

    def plot_output_data(self):
        variables = self.variables

        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []

        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=resistance_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 3],
                label=variables[3],
                color=resistance_color,
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 17],
                label=variables[17],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 5],
                label=variables[5],
                color=capacitanse_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 6],
                label=variables[6],
                color=capacitanse_color,
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, -2],
                label=variables[-2],
                color=capacitanse_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 14],
                label=variables[14],
                color=time_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 15],
                label=variables[15],
                color=time_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 16],
                label=variables[16],
                color=time_color,
                linestyle="dashdot",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(fr"Resistance [{self.units[17]}]")
        self.axis.set_yscale("log")
        ax1.set_ylabel(fr"Capacitance [{self.units[-2]}]")
        ax1.set_yscale("log")
        ax2.set_ylabel(fr"Setteling time [{self.units[16]}]")
        ax2.set_yscale("log")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)

        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)


####    "R0-p(R1,C1)-p(R2,C2)" ####


class Circuit_R0pR1C1pR2C2(BaseCircuitHandler):
    circuit_string = "R0-p(R1,C1)-p(R2,C2)"
    num_parameters = 5
    num_taus = 2
    num_tot = 2
    base_variables = (
        "Re",
        "R1",
        "R2",
        "C1",
        "C2",
        "std_Re",
        "std_R1",
        "std_R2",
        "std_C1",
        "std_C2",
        r"$\tau$ 1",
        r"$\tau$ 2",
        "TotR",
        "TotC",
        "Chivalue",
    )

    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.ones(self.num_parameters) * 0.01

    def get_bounds(self):
        return np.array([[0, np.inf] for i in range(self.num_parameters)]).T

    def get_new_indicies(self):
        indicies = [1, 3]
        time_constants = [
            self.circuit.initial_guess[1] * self.circuit.initial_guess[2],
            self.circuit.initial_guess[3] * self.circuit.initial_guess[4],
        ]
        return [index for _, index in sorted(zip(time_constants, indicies))]

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[self.new_indicies[0]]  # R1
        self.output_data[i, 2] = parameters[self.new_indicies[1]]  # R2
        self.output_data[i, 3] = parameters[self.new_indicies[0] + 1]  # C1
        self.output_data[i, 4] = parameters[self.new_indicies[1] + 1]  # C2
        self.output_data[i, 5] = deviations[0]  # std_R0
        self.output_data[i, 6] = deviations[self.new_indicies[0]]  # std_R1
        self.output_data[i, 7] = deviations[self.new_indicies[1]]  # std_R2
        self.output_data[i, 8] = deviations[self.new_indicies[0] + 1]  # std_C1
        self.output_data[i, 9] = deviations[self.new_indicies[1] + 1]  # std_C2
        self.output_data[i, 10] = (
            self.output_data[i, 1] * self.output_data[i, 3]
        )  # tau1
        self.output_data[i, 11] = (
            self.output_data[i, 2] * self.output_data[i, 4]
        )  # tau2
        self.output_data[i, 12] = parameters[0] + parameters[1] + parameters[3]  # TotR
        self.output_data[i, 13] = 1 / (1 / parameters[2] + 1 / parameters[4])  # TotC
        self.output_data[i, 14] = chiN  # Chi/N

    def plot_output_data(self):
        variables = self.variables

        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )

        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []

        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=resistance_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, -3],
                label=variables[-3],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 3],
                label=variables[3],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color=capacitanse_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, -2],
                label=variables[-2],
                color=capacitanse_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 10],
                label=variables[10],
                color=time_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 11],
                label=variables[11],
                color=time_color,
                linestyle="dashed",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        ax1.set_ylabel("Capacitance [F]")
        ax1.set_yscale("log")
        ax2.set_ylabel("Setteling time [s]")
        ax2.set_yscale("log")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)
        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)


####    "R0-p(R1,C1)" ####


class Circuit_R0pR1C1(BaseCircuitHandler):
    circuit_string = "R0-p(R1,C1)"
    num_parameters = 3
    num_taus = 1
    num_tot = 1

    base_variables = (
        "Re",
        "R1",
        "C1",
        "std_Re",
        "std_R1",
        "std_C1",
        r"$\tau$ 1",
        "TotR",
        "Chivalue",
    )
    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.ones(self.num_parameters) * 0.01

    def get_bounds(self):
        return np.array([[0, np.inf] for i in range(self.num_parameters)]).T

    def get_new_indicies(self):
        return [1]

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[1]  # R1
        self.output_data[i, 2] = parameters[2]  # C1
        self.output_data[i, 3] = deviations[0]  # std_R0
        self.output_data[i, 4] = deviations[1]  # std_R1
        self.output_data[i, 5] = deviations[2]  # std_C1
        self.output_data[i, 6] = self.output_data[i, 1] * self.output_data[i, 2]  # tau1
        self.output_data[i, 7] = parameters[0] + parameters[1]  # TotR
        self.output_data[i, 8] = chiN

    def plot_output_data(self):
        variables = self.variables
        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()

        # Offset the right spine of twin2.  The ticks and label have already been
        # placed on the right by twinx above.
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []

        lines = []
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 7],
                label=variables[7],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 6],
                label=variables[6],
                color=time_color,
                linestyle="dotted",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        ax1.set_ylabel("Capacitance [F]")
        ax1.set_yscale("log")
        ax2.set_ylabel("Setteling time [s]")
        ax2.set_yscale("log")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)
        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)


####    "p(R1,C1)" ####


class Circuit_pR1C1(BaseCircuitHandler):
    circuit_string = "p(R1,C1)"
    num_parameters = 2
    num_taus = 1
    num_tot = 0
    base_variables = ("R1", "C1", "std_R1", "std_C1", r"$\tau$ 1", "Chivalue")

    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.ones(self.num_parameters) * 0.01

    def get_bounds(self):
        return np.array([[0, np.inf] for i in range(self.num_parameters)]).T

    def get_new_indicies(self):
        return [0]

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # R1
        self.output_data[i, 1] = parameters[1]  # C1
        self.output_data[i, 2] = deviations[0]  # std_R1
        self.output_data[i, 3] = deviations[1]  # std_C1
        self.output_data[i, 4] = self.output_data[i, 0] * self.output_data[i, 1]  # tau1
        self.output_data[i, 5] = chiN  # Chi/N
        

    def plot_output_data(self):
        variables = self.variables
        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()

        # Offset the right spine of twin2.  The ticks and label have already been
        # placed on the right by twinx above.
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color=time_color,
                linestyle="dotted",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        ax1.set_ylabel("Capacitance [F]")
        ax1.set_yscale("log")
        ax2.set_ylabel("Setteling time [s]")
        ax2.set_yscale("log")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)
        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)
    

        

#### "R0-p(R1,CPE1)-p(R2,CPE2)-p(R3,CPE3)" ####
class Circuit_R0pR1CPE1pR2CPE2pR3CPE3(BaseCircuitHandler):
    circuit_string = "R0-p(R1,CPE1)-p(R2,CPE2)-p(R3,CPE3)"
    num_parameters = 10
    num_taus = 0
    num_tot = 1
    base_variables = (
        "Re",
        "R1",
        "R2",
        "R3",
        "CPE1_Q",
        "CPE1_alpha",
        "CPE2_Q",
        "CPE2_alpha",
        "CPE3_Q",
        "CPE3_alpha",
        "std_Re",
        "std_R1",
        "std_R2",
        "std_R3",
        "std_CPE1_Q",
        "std_CPE1_alpha",
        "std_CPE2_Q",
        "std_CPE2_alpha",
        "std_CPE3_Q",
        "std_CPE3_alpha",
        "TotR",
        "Chivalue",
    )
    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.array([1, 1, 1, 0.9, 1, 1, 0.9, 1, 1, 0.9])

    def get_bounds(self):
        low_lim = 1e-14
        return np.array(
            [
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, 1],
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, 1],
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, 1],
            ]
        ).T

    def get_new_indicies(self):
        indicies = [1, 4, 7]
        resistances = [
            self.circuit.initial_guess[1] * self.circuit.initial_guess[2],
            self.circuit.initial_guess[4] * self.circuit.initial_guess[5],
            self.circuit.initial_guess[7] * self.circuit.initial_guess[8],
        ]
        return [index for _, index in sorted(zip(resistances, indicies))]

    def do_initial_step(self):
        self.circuit = CustomCircuit(
            self.circuit_string, initial_guess=self.get_initial_guess()
        )
        f, Z = BaseCircuitHandler.load_MMFILE(self.files_in_watch[0])
        start_time = time.time()
        self.circuit.fit(f, Z, bounds=self.get_bounds(), method="trf")
        # self.log(
        #     # f"Time spent on first fit, with global optinon true: {time.time()-start_time}"
        # )
        initial_guess = list(self.circuit.parameters_)
        self.circuit.initial_guess = initial_guess
        self.output_data = np.zeros(
            (
                len(self.files_in_watch),
                2 * self.num_parameters + self.num_taus + self.num_tot + 1,
            )
        )  # +1 from chi/n

        self.new_indicies = self.get_new_indicies()

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[self.new_indicies[0]]  # R1
        self.output_data[i, 2] = parameters[self.new_indicies[1]]  # R2
        self.output_data[i, 3] = parameters[self.new_indicies[2]]  # R3
        self.output_data[i, 4] = parameters[self.new_indicies[0] + 1]  # CPE1_Q
        self.output_data[i, 5] = parameters[self.new_indicies[0] + 2]  # CPE1_alpha
        self.output_data[i, 6] = parameters[self.new_indicies[1] + 1]  # CPE2_Q
        self.output_data[i, 7] = parameters[self.new_indicies[1] + 2]  # CPE2_alpha
        self.output_data[i, 8] = parameters[self.new_indicies[2] + 1]  # CPE3_Q
        self.output_data[i, 9] = parameters[self.new_indicies[2] + 2]  # CPE3_alpha
        self.output_data[i, 10] = deviations[0]  # std_R0
        self.output_data[i, 11] = deviations[self.new_indicies[0]]  # std_R1
        self.output_data[i, 12] = deviations[self.new_indicies[1]]  # std_R2
        self.output_data[i, 13] = deviations[self.new_indicies[2]]  # std_R3
        self.output_data[i, 14] = deviations[self.new_indicies[0] + 1]  # std_CPE1_Q
        self.output_data[i, 15] = deviations[self.new_indicies[0] + 2]  # std_CPE1_alpha
        self.output_data[i, 16] = deviations[self.new_indicies[1] + 1]  # std_CPE2_Q
        self.output_data[i, 17] = deviations[self.new_indicies[1] + 2]  # std_CPE2_alpha
        self.output_data[i, 18] = deviations[self.new_indicies[2] + 1]  # std_CPE3_Q
        self.output_data[i, 19] = deviations[self.new_indicies[2] + 2]  # std_CPE3_alpha
        self.output_data[i, 20] = (
            parameters[0] + parameters[1] + parameters[3] + parameters[5]
        )  # TotR
        self.output_data[i, 21] = chiN

    def plot_output_data(self):
        variables = self.variables
        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []

        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=resistance_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 3],
                label=variables[3],
                color=resistance_color,
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 20],
                label=variables[20],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 6],
                label=variables[6],
                color=capacitanse_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 8],
                label=variables[8],
                color=capacitanse_color,
                linestyle="dashdot",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 5],
                label=variables[5],
                color=time_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 7],
                label=variables[7],
                color=time_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 9],
                label=variables[9],
                color=time_color,
                linestyle="dashdot",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        ax1.set_ylabel(r"Q [s$^\alpha\Omega^{-1}$]")
        ax1.set_yscale("log")
        ax2.set_ylabel(r"Phase $\alpha$ [1]")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)

        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)


#### "R0-p(R1,CPE1)-p(R2,CPE2)" ####
class Circuit_R0pR1CPE1pR2CPE2(BaseCircuitHandler):
    circuit_string = "R0-p(R1,CPE1)-p(R2,CPE2)"
    num_parameters = 7
    num_taus = 0
    num_tot = 1
    base_variables = (
        "Re",
        "R1",
        "R2",
        "CPE1_Q",
        "CPE1_alpha",
        "CPE2_Q",
        "CPE2_alpha",
        "std_Re",
        "std_R1",
        "std_R2",
        "std_CPE1_Q",
        "std_CPE1_alpha",
        "std_CPE2_Q",
        "std_CPE2_alpha",
        "TotR",
        "Chivalue",
    )
    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.CPE_Q_unit,
        BaseCircuitHandler.CPE_alpha_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.array([1, 1, 1, 0.9, 1, 1, 0.9])

    def get_bounds(self):
        low_lim = 1e-14
        return np.array(
            [
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, 1],
                [low_lim, np.inf],
                [low_lim, np.inf],
                [low_lim, 1],
            ]
        ).T

    def get_new_indicies(self):
        indicies = [1, 4]
        resistances = [
            self.circuit.initial_guess[1] * self.circuit.initial_guess[2],
            self.circuit.initial_guess[4] * self.circuit.initial_guess[5],
        ]
        return [index for _, index in sorted(zip(resistances, indicies))]

    def do_initial_step(self):
        self.circuit = CustomCircuit(
            self.circuit_string, initial_guess=self.get_initial_guess()
        )
        f, Z = BaseCircuitHandler.load_MMFILE(self.files_in_watch[0])
        start_time = time.time()
        self.circuit.fit(f, Z, bounds=self.get_bounds(), method="trf")
        # self.log(
        #     # f"Time spent on first fit, with global optinon true: {time.time()-start_time}"
        # )
        initial_guess = list(self.circuit.parameters_)
        self.circuit.initial_guess = initial_guess
        self.output_data = np.zeros(
            (
                len(self.files_in_watch),
                2 * self.num_parameters + self.num_taus + self.num_tot + 1,
            )
        )  # +1 from chi/n
        self.new_indicies = self.get_new_indicies()

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[self.new_indicies[0]]  # R1
        self.output_data[i, 2] = parameters[self.new_indicies[1]]  # R2
        self.output_data[i, 3] = parameters[self.new_indicies[0] + 1]  # CPE1_Q
        self.output_data[i, 4] = parameters[self.new_indicies[0] + 2]  # CPE1_alpha
        self.output_data[i, 5] = parameters[self.new_indicies[1] + 1]  # CPE2_Q
        self.output_data[i, 6] = parameters[self.new_indicies[1] + 2]  # CPE2_alpha
        self.output_data[i, 7] = deviations[0]  # std_R0
        self.output_data[i, 8] = deviations[self.new_indicies[0]]  # std_R1
        self.output_data[i, 9] = deviations[self.new_indicies[1]]  # std_R2
        self.output_data[i, 10] = deviations[self.new_indicies[0] + 1]  # std_CPE1_Q
        self.output_data[i, 11] = deviations[self.new_indicies[0] + 2]  # std_CPE1_alpha
        self.output_data[i, 12] = deviations[self.new_indicies[1] + 1]  # std_CPE2_Q
        self.output_data[i, 13] = deviations[self.new_indicies[1] + 2]  # std_CPE2_alpha
        self.output_data[i, 14] = parameters[0] + parameters[1] + parameters[4]  # TotR
        self.output_data[i, 15] = chiN

    def plot_output_data(self):
        variables = self.variables
        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()
        ax2.spines["right"].set_position(("axes", 1.15))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        lines = []

        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=resistance_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 14],
                label=variables[14],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 3],
                label=variables[3],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 5],
                label=variables[5],
                color=capacitanse_color,
                linestyle="dashed",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color=time_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 6],
                label=variables[6],
                color=time_color,
                linestyle="dashed",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        ax1.set_ylabel(r"Q [s$^\alpha\Omega^{-1}$]")
        ax1.set_yscale("log")
        ax2.set_ylabel(r"Phase $\alpha$ [1]")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)

        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)


####    "R0-p(R1,C1)-p(R2,C2)-p(R3,C3,R4-L1)" ####


class Circuit_R0pR1C1pR2C2pR3C3R4L1(BaseCircuitHandler):
    circuit_string = "R0-p(R1,C1)-p(R2,C2)-p(R3,C3,R4-L1)"
    num_parameters = 9
    num_taus = 3
    num_tot = 2
    base_variables = (
        "Re",
        "R1",
        "R2",
        "R3",
        "R4",
        "C1",
        "C2",
        "C3",
        "L1",
        "std_Re",
        "std_R1",
        "std_R2",
        "std_R3",
        "std_R4",
        "std_C1",
        "std_C2",
        "std_C3",
        "std_L1",
        r"$\tau$ 1",
        r"$\tau$ 2",
        r"$\tau$ 3",
        "TotR",
        "TotC",
        "Chivalue",
    )
    base_units = (
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.L_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.L_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.t_unit,
        BaseCircuitHandler.R_unit,
        BaseCircuitHandler.C_unit,
        BaseCircuitHandler.R_unit,
    )

    def __init__(self, file_dir, save_file_path, log, area_str='', area_size=1):
        BaseCircuitHandler.__init__(
            self, file_dir, save_file_path, log, area_str=area_str, area_size=area_size
        )
        self.variables = list(self.base_variables)
        self.units = list(self.base_units)

    def get_initial_guess(self):
        return np.ones(self.num_parameters) * 0.01

    def get_bounds(self):
        return np.array([[0, np.inf] for i in range(self.num_parameters)]).T

    def get_new_indicies(self):
        indicies = [1, 3]
        time_constants = [
            self.circuit.initial_guess[1] * self.circuit.initial_guess[2],
            self.circuit.initial_guess[3] * self.circuit.initial_guess[4],
        ]
        new_indicies = [index for _, index in sorted(zip(time_constants, indicies))]
        new_indicies.append(5)
        return new_indicies

    def update_output_data(self, i, parameters, deviations, chiN):
        self.output_data[i, 0] = parameters[0]  # Re
        self.output_data[i, 1] = parameters[self.new_indicies[0]]  # R1
        self.output_data[i, 2] = parameters[self.new_indicies[1]]  # R2
        self.output_data[i, 3] = parameters[self.new_indicies[2]]  # R3
        self.output_data[i, 4] = parameters[self.new_indicies[2] + 2]  # R4
        self.output_data[i, 5] = parameters[self.new_indicies[0] + 1]  # C1
        self.output_data[i, 6] = parameters[self.new_indicies[1] + 1]  # C2
        self.output_data[i, 7] = parameters[self.new_indicies[2] + 1]  # C3
        self.output_data[i, 8] = parameters[8]  # L1
        self.output_data[i, 9] = deviations[0]  # std_R0
        self.output_data[i, 10] = deviations[self.new_indicies[0]]  # std_R1
        self.output_data[i, 11] = deviations[self.new_indicies[1]]  # std_R2
        self.output_data[i, 12] = deviations[self.new_indicies[2]]  # std_R3
        self.output_data[i, 13] = deviations[self.new_indicies[2] + 2]  # std_R4
        self.output_data[i, 14] = deviations[self.new_indicies[0] + 1]  # std_C1
        self.output_data[i, 15] = deviations[self.new_indicies[1] + 1]  # std_C2
        self.output_data[i, 16] = deviations[self.new_indicies[2] + 1]  # std_C3
        self.output_data[i, 17] = deviations[8]  # std_L1
        self.output_data[i, 18] = (
            self.output_data[i, 1] * self.output_data[i, 4]
        )  # tau1
        self.output_data[i, 19] = (
            self.output_data[i, 2] * self.output_data[i, 5]
        )  # tau2
        self.output_data[i, 20] = (
            self.output_data[i, 3] * self.output_data[i, 6]
        )  # tau3
        self.output_data[i, 21] = (
            parameters[0]
            + parameters[1]
            + parameters[3]
            + 1 / (1 / parameters[5] + 1 / parameters[7])
        )  # TotR
        self.output_data[i, 22] = 1 / (
            1 / parameters[2] + 1 / parameters[4] + 1 / parameters[6]
        )  # TotC
        self.output_data[i, 23] = chiN

    def plot_output_data(self):
        variables = self.variables

        n = np.arange(self.output_data.shape[0])
        if self.output_data.shape[1] != len(variables):
            raise ValueError(
                f"The format of the file is not correct, detected ({self.output_data.shape[1]}) variables, but expected ({len(variables)})"
            )
        self.figure.subplots_adjust(right=0.75)
        ax1 = self.axis.twinx()
        ax2 = self.axis.twinx()
        ax3 = self.axis.twinx()
        ax2.spines["right"].set_position(("axes", 1.14))
        ax3.spines["right"].set_position(("axes", 1.28))

        resistance_color = "g"
        capacitanse_color = "r"
        time_color = "b"
        inductance_color = "magenta"
        lines = []
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 0],
                label=variables[0],
                color=resistance_color,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 1],
                label=variables[1],
                color=resistance_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 2],
                label=variables[2],
                color=resistance_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 3],
                label=variables[3],
                color=resistance_color,
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 4],
                label=variables[4],
                color="lime",
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            self.axis.plot(
                n,
                self.output_data[:, 21],
                label=variables[21],
                color=resistance_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 5],
                label=variables[5],
                color=capacitanse_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 6],
                label=variables[6],
                color=capacitanse_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 7],
                label=variables[7],
                color=capacitanse_color,
                linestyle="dashdot",
            )[0]
        )
        lines.append(
            ax1.plot(
                n,
                self.output_data[:, 22],
                label=variables[22],
                color=capacitanse_color,
                linestyle="solid",
            )[0]
        )

        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 18],
                label=variables[18],
                color=time_color,
                linestyle="dotted",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 19],
                label=variables[19],
                color=time_color,
                linestyle="dashed",
            )[0]
        )
        lines.append(
            ax2.plot(
                n,
                self.output_data[:, 20],
                label=variables[20],
                color=time_color,
                linestyle="dashdot",
            )[0]
        )

        lines.append(
            ax3.plot(
                n,
                self.output_data[:, 8],
                label=variables[8],
                color=inductance_color,
                linestyle="dashdot",
            )[0]
        )

        self.axis.set_xlabel("Time [A.U.]")
        self.axis.set_ylabel(r"Resistance [$\Omega$]")
        self.axis.set_yscale("log")
        self.axis.grid()
        ax1.set_ylabel("Capacitance [F]")
        ax1.set_yscale("log")
        ax2.set_ylabel("Setteling time [s]")
        ax2.set_yscale("log")
        ax3.set_ylabel("Inductance [H]")
        ax3.set_yscale("log")

        self.axis.yaxis.label.set_color(resistance_color)
        ax1.yaxis.label.set_color(capacitanse_color)
        ax2.yaxis.label.set_color(time_color)
        ax3.yaxis.label.set_color(inductance_color)

        tkw = dict(size=4, width=1.5)
        self.axis.tick_params(axis="y", colors=resistance_color, **tkw)
        ax1.tick_params(axis="y", colors=capacitanse_color, **tkw)
        ax2.tick_params(axis="y", colors=time_color, **tkw)
        ax3.tick_params(axis="y", colors=inductance_color, **tkw)
        self.axis.tick_params(axis="x", **tkw)

        labels = [line.get_label() for line in lines]
        self.axis.legend(lines, labels)
    

""" 
A dictionary with the circuit strings as keys and the
circuit initialiser functions as values.
"""
IMPLEMENTED_CIRCUITS = {
    "R0-p(R1,C1)-p(R2,C2)-p(R3,C3)": Circuit_R0pR1C1pR2C2pR3C3,
    "R0-p(R1,C1)-p(R2,C2)": Circuit_R0pR1C1pR2C2, # Disse er de viktige
    "R0-p(R1,C1)": Circuit_R0pR1C1, # Disse er de viktige
    "p(R1,C1)": Circuit_pR1C1,
    "R0-p(R1,CPE1)-p(R2,CPE2)-p(R3,CPE3)": Circuit_R0pR1CPE1pR2CPE2pR3CPE3,
    "R0-p(R1,CPE1)-p(R2,CPE2)": Circuit_R0pR1CPE1pR2CPE2,
    "R0-p(R1,C1)-p(R2,C2)-p(R3,C3,R4-L1)": Circuit_R0pR1C1pR2C2pR3C3R4L1,
}


def get_circuit_handler(circuit_string):
    """
    Get the circuir_string from the IMPLEMENTED_CIRCUITS, returns None if not implemented.
    """
    return IMPLEMENTED_CIRCUITS.get(circuit_string)
