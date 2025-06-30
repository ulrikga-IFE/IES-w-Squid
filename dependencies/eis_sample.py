"""
Circuit handler

Short description:
----------
This is a helper file to the Watch impedance. The file consist of a 
class called EIS_Sample that both can load time data compute the
fourier transform of the voltage and current signals and analyse
these to find the frequencies present in the signal and compute
the impedance based on this. The class also has method for storing
the results. For further specification see the class description.

@author: Christoffer Askvik Faugstad (christoffer.askvik.faugstad@hotmail.com)
"""
from dependencies.GUI_helper import PlotCanvas
import numpy as np
from matplotlib.colors import LogNorm
from scipy.fft import rfft, rfftfreq, next_fast_len
from scipy.signal import find_peaks
import os

class EIS_Sample:
    """
    Short description:
    ----------
    A electrocheimcal impedance spectropy template for calculating the impedance
    from time samples of voltage and current.

    Main methods:
    ----------
    - watch_call :
        Instantiates a object from a file and does the fft and saves
        the impedance data to file. The instanse is returned for further use.
    - plot_somthing :
        Either nyquist, bode or fft_spectrum. The functions either take a axis
        and figure or is the method is extended with "_canvas" it takes a
        PlotCanvas object, defined in the GUI file.
    - get_full_save_path:
        Static method that returns what absolute file path to the save file
        would be used. Convinient for checking if the file already exsists.

    Other methods:
    ----------
    - __init__
    - classmethod from_file
    - save_to_MMFILE
    - fft


    """

    def __init__(
        self,
        voltage: np.array,
        current: np.array,
        sample_frequency: int,
        voltage_proportion=0.1,
        current_proportion=0.1,
        filter_apply=True,
        filter_type="Hann",       
        beta_factor=4.2,
        frequency_now = 1,

    ):
        """
        Parameters:
        ----------
        - voltage : np.array
            The voltage time signal as a numpy array in Volts
        - current : np.array
            The current time signal as a numpy array in Ampere
        - sample_frequency: int
            The sample frequency used in Hertz
        - voltage_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the voltage fft
        - current_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the current fft

        Does:
        ----------
        Stores tha values in the object and cheks if the size of the arrays are the
        same, if not raises ValueError.

        Returns:
        ----------
        The instanse.
        """

        if voltage.size != current.size:
            raise ValueError(
                "voltage of size: "
                + str(voltage.size)
                + " does not match current of size: "
                + str(current.size)
            )
        self.voltage = voltage
        self.current = current
        if sample_frequency <= 0:
            raise ValueError(
                f"Sample frequency cannot be {sample_frequency}. \n Must be a positive number."
            )

        self.sample_frequency = sample_frequency
        self.voltage_proportion = voltage_proportion
        self.current_proportion = current_proportion
        self.filter_apply = filter_apply
        self.filter_type = filter_type
        self.beta_factor = beta_factor
        self.frequency_now = frequency_now

    @classmethod
    def from_file(
        cls,
        file_path,
        time_loc=0,
        voltage_loc=1,
        current_loc=2,
        voltage_proportion=0.1,
        current_proportion=0.1,
        correction_factor_current=1,
        filter_apply=True,
        filter_type="Hann",
        beta_factor=4.2,
        frequency_now = 1,
    ):
        """
        Parameters:
        ----------
        - file_path : str
            The relative/absolute filepath to pico text file
        - time_loc : int, default 0
            The column of the time loging in the file (zero indexed)
        - voltage_loc : int, default 1
            The column of the voltage loging in the file (zero indexed)
        - current_loc : int, default 2
            The column of the current loging in the file (zero indexed)
        - voltage_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the voltage fft
        - current_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the current fft
        - current_factor : float, default 0.01
            A factor to multiply the current data with. Relevant if a quasi
            measurment is done or some loging error is done.

        Does:
        ----------
        Reads data for sample from a text file produced by the picoscope.
        The second row (index 1) is taken as the unit row and if any of these
        contain a "m" it is assumed the the coresponding column is in milli-
        so to work in base unit these columns are multiplied by 10^(-3).
        The data is assumed to start in the forth row (index 3) thus the
        3 first rows are skipped when looking for data. The sample frequency
        is found be taking the inverse of the difference between the two
        first measurments of time.

        Returns:
        ----------
        A instance of the class with the parameters that are found in the file
        together with the ones passed in to this function.
        """
        # Getting the header unit names
        header = np.loadtxt(file_path, skiprows=21, max_rows=1, dtype=str)
        # Making a bool array with True if the unit is in milli-
        is_in_m = ["m" in name for name in header]
        # Loading the data after skipping 23 rows
        data = np.loadtxt(file_path, skiprows=23)
        # Getting the different parts as seperate arrays and converting is in milli-
        time_data = data[:, time_loc]
        if is_in_m[time_loc]:
            time_data *= 0.001
        voltage = data[:, voltage_loc]
        if is_in_m[voltage_loc]:
            voltage *= 0.001
        current = data[:, current_loc]
        if is_in_m[current_loc]:
            current *= 0.001
        # Applying the current correction factor
        current /= correction_factor_current
        # Calculating the sample frequency
        sample_frequency = int(np.round(1 / (time_data[1] - time_data[0])))
        # Returning a instanse of the class with the parameters from the file
        return cls(
            voltage,
            current,
            sample_frequency,
            voltage_proportion=voltage_proportion,
            current_proportion=current_proportion,
            filter_apply=filter_apply,
            filter_type=filter_type,
            beta_factor=beta_factor, 
            frequency_now = frequency_now,
        )

    def save_to_MMFILE(self, full_save_path):
        """
        Paramaters:
        ----------
        full_save_path : The absolute file path to where the
            file should be save.

        Does:
        ----------
        Saves the data stored in impedance and fft_frequencies and
        saves it to the full_save_path in the MMFILE format, mening:
        Frequency   Real    Complex
        Number      Number  Number
        ...

        """
        with open(full_save_path, "w") as f:
            f.write("Frequency\tReal\tImaginary")
            for imp, freq in zip(self.impedance, self.fft_frequencies):
                f.write(f"\n{freq}\t{imp.real}\t{imp.imag}")

    def fft(self):
        """
        Does:
        ----------

        Computes the rfft (fft but only with real input) of the voltage and current.
        Then the peaks of the two fft's are found separatly and the intersection
        of these peaks are taken as the found peaks for the impedances. Thus the
        impedance of the peaks are calculated by voltage / current.

        The peaks are calculated by having a proportion the peaks have to be higher than
        to remove the low intensity peaks. This is controlled by the variables
        voltage- and current_proportion, which give the porportion of the max signal
        the peaks have to be above.

        If a window function is applied to filter, this will apply this prior to the fft 
        and a normalization is applied according to the window function to the fft processed data.

        Stored values:
        ----------
        - all_fft_frequencies : All the frequencies that are calculated
        - all_fft_voltage  : All the voltage fourier components
        - all_fft_current : All the current fourier componets
        - voltage_indicies : The indicies of the found peaks in the voltage fft
        - current_indicies : The indicies of the found peaks in the current fft
        - indicies : The intersection of the voltage and current_indicies
        - fft_frequencies : The frequency of the found peaks
        - impedance : The impedance calculated at the peaks
        """
        # Sample size
        N = self.voltage.size
        self.beta_factor = float(self.beta_factor)
        self.voltage_window = []
        self.current_window = []
        
        # Apply filtering to the input data if applicable, this part should: 
        # - check if filter is applied
        # - apply the correct or no filter to the time data
        # - calculate the impedance and save the data for plotting
        # - normalize the data (before or after fft?) it doesn't matter right?
        fft_length = next_fast_len(N, real=True)

        if self.filter_apply == True:
            normalization_factor = 0.0
            if self.filter_type == "Rectangle":
                # Rectangle filter is really no filter
                # Compute ffts, rfft method used since input is real
                fft_voltage = rfft(self.voltage, fft_length) * 1.0 / N
                fft_current = rfft(self.current, fft_length) * 1.0 / N

                fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)

            elif self.filter_type == "Hann":
                # Apply filter function to the input data

                for vol, curr, norm in zip(self.voltage, self.current, np.hanning(N)):
                    self.voltage_window.append(vol*norm)
                    self.current_window.append(curr*norm)

                # Calculate normalization factor
                normalization_factor = sum(np.hanning(N))/N

                # Compute ffts on the filtered data
                fft_voltage = rfft(self.voltage_window, fft_length) * 1.0 / N / normalization_factor
                fft_current = rfft(self.current_window, fft_length) * 1.0 / N / normalization_factor

                fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)

            elif self.filter_type == "Hamming":
                # Apply filter function to the input data

                for vol, curr, norm in zip(self.voltage, self.current, np.hamming(N)):
                    self.voltage_window.append(vol*norm)
                    self.current_window.append(curr*norm)

                # Calculate normalization factor
                normalization_factor = sum(np.hamming(N))/N

                # Compute ffts on the filtered data
                fft_voltage = rfft(self.voltage_window, fft_length) * 1.0 / N / normalization_factor
                fft_current = rfft(self.current_window, fft_length) * 1.0 / N / normalization_factor

                fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)
                
            elif self.filter_type == "Blackman":
                # Apply filter function to the input data

                for vol, curr, norm in zip(self.voltage, self.current, np.blackman(N)):
                    self.voltage_window.append(vol*norm)
                    self.current_window.append(curr*norm)

                # Calculate normalization factor
                normalization_factor = sum(np.blackman(N))/N

                # Compute ffts on the filtered data
                fft_voltage = rfft(self.voltage_window, fft_length) * 1.0 / N / normalization_factor
                fft_current = rfft(self.current_window, fft_length) * 1.0 / N / normalization_factor

                fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)
                

            elif self.filter_type == "Kaiser":
                # Apply filter function to the input data
                for vol, curr, norm in zip(self.voltage, self.current, np.kaiser(N,self.beta_factor)):
                    self.voltage_window.append(vol*norm)
                    self.current_window.append(curr*norm)

                # Calculate normalization factor
                normalization_factor = sum(np.kaiser(N,self.beta_factor))/N

                # Compute ffts on the filtered data
                fft_voltage = rfft(self.voltage_window, fft_length) * 1.0 / N / normalization_factor
                fft_current = rfft(self.current_window, fft_length) * 1.0 / N / normalization_factor

                fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)
        else:
            # Compute ffts, fft method used since input is real
            fft_voltage = rfft(self.voltage) * 1.0 / N
            fft_current = rfft(self.current) * 1.0 / N

            fft_frequencies = rfftfreq(fft_length, 1 / self.sample_frequency)
        

        """
        # Removing the data at frequency lower than twice the lowest frequency resolution
        remove_indicies = np.array([0, 1, 2, 3, 4, 5, 6])            # ORIGINAL STATEMENT IS [0,1,2,3]
        fft_voltage[remove_indicies] = np.zeros(len(list(remove_indicies)))        
        fft_current[remove_indicies] = np.zeros(len(list(remove_indicies)))
        """
        
        # Calculating indicies of max
        # We want to force it at the desired frequency. The way to do this is simply get the resolution and the frequency, 
        # and thus find the indice that is relevant. We also tweak this so this is indeed a peak in the fft data.
        # height = max(np.abs(fft_voltage)) * self.voltage_proportion
        #voltage_indicies = find_peaks(np.abs(fft_voltage), height=height)[0]
        #height = max(np.abs(fft_current)) * self.current_proportions

        def find_closest_frequency_index(fft_frequencies, target_frequency):
            closest_index = min(range(len(fft_frequencies)), key=lambda i: abs(fft_frequencies[i] - target_frequency))
            return closest_index
        
        #indice = find_closest_frequency_index(fft_frequencies, self.frequency_now)

        #current_indicies = find_peaks(np.abs(fft_current), height=height)

        def find_nearest_maximum(fft_current, fft_frequencies, frequency):
            """
            Finds the local maximum closest to the desired point.
            """
            # Get the local maxima
            maxima = find_peaks(np.abs(fft_current))
            #print(f"This is the maximas: {maxima[0]}")
            #print(f"the type of maxima is: {type(maxima[0])}")
            # Get the index of the desired point
            desired_point = find_closest_frequency_index(fft_frequencies, frequency)
            #print(f"This is the desired point: {desired_point}")
            #print(f"the type of desired point is: {type(desired_point)}")

            # If there are no local maxima, return None
            if not maxima:
                return None

            # Find the nearest local maximum
            nearest_maxima = min(maxima[0], key=lambda x: abs(x - desired_point))
            #print(f'This is the nearest maxima: {nearest_maxima}')

            return nearest_maxima


        current_indicies = find_nearest_maximum(fft_current, fft_frequencies, self.frequency_now)
            
        #current_indicies = current_indicies[-1]
        voltage_indicies = current_indicies             # Just a fix so that it's the same
        #voltage_indicies = find_nearest_maximum(fft_voltage, fft_frequencies, self.frequency_now)
        # Taking the indicies that are shared by both voltage and current
        indicies = np.intersect1d(voltage_indicies, current_indicies)

        # Storing all relevant variables
        self.all_fft_frequencies = fft_frequencies
        self.all_fft_voltage = fft_voltage
        self.all_fft_current = fft_current
        self.voltage_indicies = voltage_indicies
        self.current_indicies = current_indicies
        self.indicies = indicies
        self.fft_frequencies = fft_frequencies[indicies]
        self.impedance = fft_voltage[indicies] / fft_current[indicies]  # Corrected by THolm  
       

        # We now make an additional sequence to try to correct the phase angle values for the plot
        # First find the voltage amplitude
        ##voltage_amplitude = np.abs(fft_voltage[indices[0]])

        # Normalize input signal by known amplitude and dc current (0)
        ##current_normalized = (self.current-3.4*0.134)/np.abs(fft_current[indices[0]])   # Only valid for 3.4 A DC current and 0.34 A AC current
        ##current_normalized2 = (self.current-3.4*0.134)/(0.134*0.34)         # Only valid for 3.4 A DC current and 0.34 A AC current 

        # Multiply the normalized current with the direct voltage measurement
        ##multiply_factor = current_normalized*self.voltage
        ##multiply_factor2 = current_normalized2*self.voltage

        # Get phase angle from known current amplitude
        ##phase_angle_calc = -np.arccos(np.average(multiply_factor)*2/voltage_amplitude)
        ##phase_angle_calc2 = -np.arccos(np.average(multiply_factor2)*2/voltage_amplitude)

        # New EIS values
        ##New_magnitude = voltage_amplitude/np.abs(fft_current[indices[0]])
        ##New_magnitude2 = voltage_amplitude/(0.134*0.34)

        ##Old_magnitude = np.abs(self.impedance[0])
        ##Old_phase_angle = 1
        
    @staticmethod
    def get_full_save_path(save_path, file_path, voltage_loc, add_loc_save):
        """
        Parameters
        ----------

        file_path : str
            The absolute path to the file that should be loaded
        save_path :
            The absolute path to the directory where the processed data should be stored
        voltage_loc: default 2
            The index of the voltage column in the file
        add_loc_save: default False
            Bool to indicate wheter or not the voltage_loc should be added to the filename

        Returns
        ----------
        The absolute path to the file that would be save to if watch_call was called with
        these parameters as a string.

        """
        
        filename = os.path.basename(file_path)[:-4]
        if add_loc_save:
            #print("The add_loc_path is True")
            filename_split = filename.split("_")
            if len(filename_split) > 1:
                return os.path.join(
                    save_path,
                    "_".join(filename_split[:-1])
                    + f"v_{str(voltage_loc)}_{filename_split[-1]}.mmfile",
                )
                
            else:
                return os.path.join(
                    save_path, filename + f"v_{str(voltage_loc)}.mmfile"
                )
        else:
            #print("The save add_loc_path is False")
            return os.path.join(save_path, filename +  f"v_{str(voltage_loc)}.mmfile")#"_2.mmfile")

    @classmethod
    def watch_call(
        cls,
        file_path: str,
        save_path: str,
        time_loc=0,
        voltage_loc=1,
        current_loc=2,
        voltage_prominence=0.1,
        current_prominence=0.1,
        correction_factor_current=1,
        add_loc_save=False,
        filter_apply=True,
        filter_type="Kaiser",
        beta_factor=4.2,
    ):
        """
        Parameters:
        ----------
        - file_path : str
            The relative/absolute filepath to pico text file
        -save_path :
            The absolute path to the directory where the processed data should be stored
        - time_loc : int, default 0
            The column of the time loging in the file (zero indexed)
        - voltage_loc : int, default 1
            The column of the voltage loging in the file (zero indexed)
        - current_loc : int, default 2
            The column of the current loging in the file (zero indexed)
        - voltage_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the voltage fft
        - current_proportion : float, default 0.1
            The proportion of the maximum height a peak have to have to be
            counted as a valid peak, in the current fft
        - current_factor : float, default 0.01
            A factor to multiply the current data with. Relevant if a quasi
            measurment is done or some loging error is done.
        - add_loc_save: bool, default False
            If True the voltage index is added to the savefilename if False
            it is not added.
        - filter_apply: bool, default True
            If True a filter is to be applied prior to fft
        - filter_type: string, default Kaiser
            A string that determines the type of filter to be used
        - beta_factor: float, default 4.2
            A factor to be used when applying the Kaiser filter, values should be between 0 and 10.

        Does:
        ----------
        Makes a sample that reads data from the text file, details in the
        method from_file. After this it calls the fft method and saves
        the results.


        Returns:
        ----------
        The instance of the class created from the file with the fft done.

        """

        frequency_now = float(os.path.basename(file_path).split("freq")[1].split("Hz.txt")[0])

        sample = cls.from_file(
            file_path,
            time_loc=time_loc,
            voltage_loc=voltage_loc,
            current_loc=current_loc,
            voltage_proportion=voltage_prominence,
            current_proportion=current_prominence,
            correction_factor_current=correction_factor_current,
            filter_apply=filter_apply,
            filter_type=filter_type,
            beta_factor=beta_factor,
            frequency_now=frequency_now,
        )
        sample.fft()
        full_save_path = EIS_Sample.get_full_save_path(
            save_path, file_path, voltage_loc=voltage_loc, add_loc_save=add_loc_save
        )
        sample.save_to_MMFILE(full_save_path)
        return sample

    def plot_nyquist(self, axis, figure):
        """
        Parameters:
        ----------
        - axis : The matplotlib axis to draw the nyquist plot on
        - figure : The matplotlib figure that the axis is a part of

        Does:
        ----------
        Sets the labels as Re Z[Ohm] and -Im Z [Ohm] and draws the
        impedances as dots colorcoded after the logarithm of there
        frequency, where yellow corresponds to high frequency and
        blue to low.
        """
        axis.set_xlabel(r"Re$Z$  [$\Omega$]")
        axis.set_ylabel(r"-Im$Z$ [$\Omega$]")
        axis.grid()

        axis.scatter(
            self.impedance.real,
            -self.impedance.imag,
            c=self.fft_frequencies,
            norm=LogNorm(),
        )
        axis.axis("equal")
        figure.tight_layout()
        axis.axis("equal")

    def plot_nyquist_canvas(self, canvas: PlotCanvas):
        """
        Parameters:
        ----------
        - canvas : PlotCanvas defined in the GUI file

        Does:
        ----------
        Gets the axis and figure from the canvas and pases it to
        the plot_nyquist function.
        """
        self.plot_nyquist(canvas.get_axis(), canvas.get_figure())

    def plot_bode(self, axises, figure):
        """
        Parameters:
        ----------
        - axises : A iterable (usualy np.array) with to matplotlib axises.
            The first axis used to plot the amplitude of the impedance and the
            second axis used to plot the angle of the impedance.
        - figure : The matplotlib figure that the axises are a part of.

        Does:
        ----------
        Draws the amplitude of the impedace to the first axis and
        angle to the second axis as a function of frequency. Here
        also the dots are colerd based on the loagarith of there
        frequency.
        """
        axises[0].scatter(
            self.fft_frequencies,
            np.abs(self.impedance),
            c=self.fft_frequencies,
            norm=LogNorm(),
        )
        axises[0].set_xscale("log")
        axises[0].set_yscale("log")
        axises[0].grid()
        axises[1].scatter(
            self.fft_frequencies,
            np.angle(self.impedance) * 180 / np.pi,
            c=self.fft_frequencies,
            norm=LogNorm(),
        )
        axises[1].set_xscale("log")
        axises[1].set_xlabel("Frequency [Hz]")
        axises[0].set_ylabel(r"$|Z|$ [$\Omega$]")
        axises[1].set_ylabel(r"$\angle Z$ [deg]")
        axises[1].grid()

        figure.tight_layout()

    def plot_bode_canvas(self, canvas: PlotCanvas):
        """
        Parameters:
        ----------
        - canvas : PlotCanvas defined in the GUI file

        Does:
        ----------
        Gets the axis and figure from the canvas and pases it to
        the plot_bode function.
        """
        self.plot_bode(canvas.get_axis(), canvas.get_figure())

    def plot_fft_spectrum(self, axises, figure):
        """
        Parameters:
        ----------
        - axises : A iterable (usualy np.array) with to matplotlib axises.
            The first axis used to plot the amplitude of the voltage fft and the
            second axis used to plot the current fft of the impedance.
        - figure : The matplotlib figure that the axises are a part of.

        Does:
        ----------
        Draws the amplitude of the absolute value of voltage fft to
        the first axis and the absolute value of the current fft to
        the second axis. In both plots the red cross indicate where
        a peak is located in the different fft's and the dots
        represent the intersections of both locations of peaks.
        The color of the dots are given by the logarithm of
        there frequency.
        """
        axises[0].scatter(
            self.all_fft_frequencies[self.voltage_indicies],
            np.abs(self.all_fft_voltage[self.voltage_indicies]),
            c="r",
            marker="x",
        )
        axises[0].scatter(
            self.fft_frequencies,
            np.abs(self.all_fft_voltage[self.indicies]),
            c=self.fft_frequencies,
            norm=LogNorm(),
        )

        axises[0].plot(self.all_fft_frequencies, np.abs(self.all_fft_voltage))
        axises[0].set_xscale("log")
        axises[0].set_yscale("log")
        axises[0].grid()
        axises[0].set_ylabel(r"fft Voltage")
        axises[1].scatter(
            self.all_fft_frequencies[self.current_indicies],
            np.abs(self.all_fft_current[self.current_indicies]),
            c="r",
            marker="x",
        )
        axises[1].scatter(
            self.fft_frequencies,
            np.abs(self.all_fft_current[self.indicies]),
            c=self.fft_frequencies,
            norm=LogNorm(),
        )
        axises[1].plot(self.all_fft_frequencies, np.abs(self.all_fft_current))
        axises[1].set_xscale("log")
        axises[1].set_yscale("log")
        axises[1].grid()
        axises[1].set_xlabel("Frequency [Hz]")
        axises[1].set_ylabel(r"fft Current")

        figure.tight_layout()

    def plot_fft_spectrum_canvas(self, canvas: PlotCanvas):
        """
        Parameters:
        ----------
        - canvas : PlotCanvas defined in the GUI file

        Does:
        ----------
        Gets the axis and figure from the canvas and pases it to
        the plot_fft_spectrum function.
        """
        self.plot_fft_spectrum(canvas.get_axis(), canvas.get_figure())
