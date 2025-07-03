"""
Watch impedance V2

Short description:
The main function of the script is to process and watch a folder of time sampled voltage 
and current data on the format from the picoscope (shown later) and convert it to a 
impedance spectra, via the fourier transform of the time signal. The program has an
interface with different options to control how this is done. There are also additional
features for doing a single file. The running results are displayed in three figures
a nyquist plot, a bode plot and a fft spectrum plot. 

Addition by Thomas Holm:
Adding filter functions for advanced signal processing of the input signal during FFT process.

Changes by Håkon Kvitvik Eckle:
Change window a to tk.Toplevel-window of the main window in control_GUI_with_FFT.py, which can
be opened through the main GUI window.

Dependencies:
The helper files eis_sample.py and GUI.py
The icon file "ife.ico", located in the same folder as the program
Modules:
    numpy
    matplotlib
    impedance (circuit_handler)
    os
    time
    tkinter
    watchdog
    typing
    shutil

The V2 version differs from the first in that i is changed to better fit with the GUI control system

@author: Håkon Kvitvik Eckle (hakon.eckle@gmail.com)
Based on watch_impedance.py by Christoffer Askvik Faugstad (christoffer.askvik.faugstad@hotmail.com)
"""
import os
import dependencies.GUI_helper as GUI_helper
import tkinter as tk
from shutil import rmtree
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dependencies.eis_sample import EIS_Sample
import time
import re
import numpy as np


# The class that handels the folder watching and trigers when a file is created
class Watchdog(PatternMatchingEventHandler, Observer):
    """
    Handles the watching of the folder by the Observer class and the
    PatternMatchingEventHandler. Works by continuously searching the path
    for updates and if a file is created is calls the on_created function.
    """

    def __init__(self,
                    path            : str = ".",
                    patterns        : tuple[str, str] = ("*.txt",),
                    logfunc         : callable = print,
                    detected_file   : callable = None):
        """
        Parameters:
        ----------
        - path: str
            The path that should be watched (input folder)
        - patterns: tuple of strings, default "*.txt"
            The file patterns that are acted upon, the default means that
            only files with the endig ".txt" are acted upon, only a "*"
            would mean that all are acted upon.
        - logfunc: function(str)
            A loging function that takes a string as input
        - created: function(file_path)
            The function that is called when a new file is detected. Should take
            a file_path as input.

        """
        PatternMatchingEventHandler.__init__(self, patterns=patterns)
        Observer.__init__(self)
        self.schedule(self, path=path, recursive=False)
        self.log = logfunc
        self.created = detected_file

    def on_created(self, event):
        self.created(event.src_path)


class Data_processor:
    def __init__(self,
                    current_channels    : str,
                    voltage_channels    : str,
                    resistor_value      : float,
                    num_freqs           : int,
                    save_path           : str,
                    num_picoscopes      : int, 
                    channels            : np.ndarray[tuple[int, int], bool],
                    save_metadata       : dict[str, str],
    ) -> None:
        """
        Set up the interface and its widgets. Calls the nroot.mainloop starting
        the programs looping.
        """
        # Watch and save default values
        self.watchdog = None
        self.watch_path = "."
        self.save_path = "."
        self.temp_save_path = "temp_watch_impedance"
        self.current_channels = current_channels
        self.voltage_channels = voltage_channels
        self.resistor_value = str(resistor_value)
        self.num_freqs = num_freqs
        self.num_picoscopes = num_picoscopes
        self.channels = channels
        self.save_metadata = save_metadata

        # Tikinter set up
        self.nroot = tk.Toplevel()
        self.nroot.title("EIS")
        self.nroot.iconbitmap("ife.ico")
        #self.nroot.attributes("-fullscreen", True)
        self.fullScreenState = True
        self.nroot.bind("<F11>", self.toggleFullScreen)
        self.nroot.bind("<Escape>", self.quitFullScreen)

        # Screen constants
        self.SCREENX = 1600#1920  # Screen size horizontal [pixels]
        self.SCREENY = 930#1080  # Screen size vertiacal [pixels]
        self.FONTSIZE = 16  # Fontsize [pixels]
        self.FONTWIDTH = 8  # Font width [pixels]
        self.FIGL_INCH = 8  # Figure length
        self.TOOLBAR_OFFSET = 100  # Toolbar size for centering
        self.BUTTON_HEIGHT_CHARACTERS = 1
        self.BUTTON_WIDTH_CHARACTERS = 20
        self.BUTTON_PAD_EXTRA = 10  # Extra padding for buttons to not overlap

        # Derived constants
        self.FIGL_PIXELS = self.SCREENX // 3
        self.DPI = self.FIGL_PIXELS / self.FIGL_INCH
        self.FIGSIZE = (self.FIGL_INCH, self.FIGL_INCH)
        self.START_FIG_Y = self.SCREENY - self.FIGL_PIXELS - self.TOOLBAR_OFFSET
        self.TEXT_HEIGHT = self.START_FIG_Y // self.FONTSIZE
        self.TEXT_WIDTH = 2 * self.FIGL_PIXELS // self.FONTWIDTH
        self.BUTTON_HEIGHT_PIXELS = (
            self.BUTTON_HEIGHT_CHARACTERS * self.FONTSIZE + self.BUTTON_PAD_EXTRA
        )
        self.BUTTON_WIDTH_PIXELS = (
            self.BUTTON_WIDTH_CHARACTERS * self.FONTWIDTH + self.BUTTON_PAD_EXTRA
        )
        self.nroot.geometry(f"{self.SCREENX}x{self.SCREENY}")

        # Make the different widgets
        self.messagebox = tk.Text(self.nroot,width=self.TEXT_WIDTH, height=self.TEXT_HEIGHT)
        self.messagebox.place(x=0, y=0)

        self.make_canvases()
        self.make_buttons()
        self.make_inboxes()
        self.make_filterfunction()

        self.files_processed = 0

        self.select_path(save_path)
        self.select_save_path(save_path)

        self.save_time_string = save_path

    def make_canvases(self) -> None:
        """Creates the Canvases for the interface"""
        self.plot_canvas_nyquist = GUI_helper.PlotCanvas.place(
            self.nroot, self.FIGSIZE, self.DPI, 0, self.START_FIG_Y
        )

        self.plot_canvas_bode = GUI_helper.PlotCanvas.place(
            self.nroot,
            self.FIGSIZE,
            self.DPI,
            self.FIGL_PIXELS,
            self.START_FIG_Y,
            num_vertical_subplots=2,
            sharex=True,
        )
        self.plot_canvas_fft = GUI_helper.PlotCanvas.place(
            self.nroot,
            self.FIGSIZE,
            self.DPI,
            2 * self.FIGL_PIXELS,
            self.START_FIG_Y,
            num_vertical_subplots=2,
            sharex=True,
        )

    def make_buttons(self) -> None:
        """Creates the buttons for the interface"""
        tk.Button(
            self.nroot,
            text="Browse watch",
            command=self.select_path,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=0)
        butt_num = 1
        tk.Button(
            self.nroot,
            text="Browse save",
            command=self.select_save_path,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=self.BUTTON_HEIGHT_PIXELS * butt_num)
        butt_num += 1
        tk.Button(
            self.nroot,
            text="Start watch",
            command=self.start_processing,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=self.BUTTON_HEIGHT_PIXELS * butt_num)
        butt_num += 1
        tk.Button(
            self.nroot,
            text="Stop Watch",
            command=self.stop_processing,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=self.BUTTON_HEIGHT_PIXELS * butt_num)
        butt_num += 1
        tk.Button(
            self.nroot,
            text="Single file",
            command=self.single_file,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=self.BUTTON_HEIGHT_PIXELS * butt_num)

    def make_inboxes(self) -> None:
        """Creates the inboxes for the parameters for the interface"""
        # Button texts
        self.inbox_names = [
            "Time index",
            "Voltage index",
            "Current index",
            "Voltage proportion",
            "Current proportion",
            "Current correction / Ohm",
        ]
        # Creating and placing buttons from GUI_helper.py
        self.inboxes = [
            GUI_helper.InboxPlace(
                self.nroot,
                name,
                2 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS,
                i * 2 * self.BUTTON_HEIGHT_PIXELS,
                self.BUTTON_WIDTH_CHARACTERS,
                0,
            )
            for i, name in enumerate(self.inbox_names)
        ]
        # Setting default values                          ####################################### CHANGE DEFAULT VALUES HERE ################################################
        self.inboxes[0].set("0")
        self.inboxes[1].set(self.voltage_channels)    # Gets the channels you picked at the beginning (except 'current channel' 1)
        self.inboxes[2].set(self.current_channels)                        # Hard coded as 1 as standard (channel 1 = first channel on picoscope).
        self.inboxes[3].set("0.001")                                    # This is set very low because that includes all peaks, and ensures that the current peak is also found in the potential sweep.
        self.inboxes[4].set("0.4")                                     # SHOULD BE 0.5
        self.inboxes[5].set(self.resistor_value)                      # This is set as Ohm to be more understandable. Option let's the operator set this in the main GUI interface

    def make_filterfunction(self) -> None:
         # Button texts
        self.filter_name = tk.Label(self.nroot,text = "Window function for filtering")
        self.filter_name.place(x = 2.3 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS, y = 0)

        # Check button for applying filter  
        self.applyfilter = tk.IntVar()
        self.applyfilter.set(1)         # DEFAULT IS 1

        self.check = tk.Checkbutton(self.nroot,text = "Apply window", variable = self.applyfilter, onvalue = 1, offvalue = 0)
        self.check.place(x = 2.3 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS, y = self.BUTTON_HEIGHT_PIXELS)

        # Dropdown menu to chose filter type
        self.filter_name2 = tk.Label(self.nroot,text = "Select window function")
        self.filter_name2.place(x = 2.3 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS, y = 2*self.BUTTON_HEIGHT_PIXELS)

        self.options = [
                "Rectangle",
                "Hann",
                "Hamming",
                "Blackman",
                "Kaiser"
                ]

        self.value_inside = tk.StringVar(self.nroot)        
        self.value_inside.set("Rectangle")

        self.option_default = self.options[0]

        self.dropmenu = tk.OptionMenu(self.nroot, self.value_inside, *self.options)
        self.dropmenu.place(x = 2.3 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS, y = 3 * self.BUTTON_HEIGHT_PIXELS, height = self.BUTTON_HEIGHT_PIXELS, width = self.BUTTON_WIDTH_PIXELS)
        
        # Parameter input for the Kaiser function's beta value see https://en.wikipedia.org/wiki/Window_function#Kaiser_window where beta = pi*alpha
        self.filter_names3 = [
                "Beta parameter (for Kaiser function)",
        ]

    
        # Creating and placing buttons from GUI.py
        self.filters = [
            GUI_helper.InboxPlace(
                self.nroot,
                name,
                2.3 * self.FIGL_PIXELS + self.BUTTON_WIDTH_PIXELS,
                4 * self.BUTTON_HEIGHT_PIXELS,
                self.BUTTON_WIDTH_CHARACTERS,
                0,
            )
            for i, name in enumerate(self.filter_names3)
        ]

        self.filters[0].set("4.2")

    def get_inbox_values(self) -> list:
        """
        Reads the values from the inboxes and returns a list of them.
        Does the conversions by the float method and if the voltage index
        string contains a "," it is separated into a list of indexes.
        """
        out = []
        # Index of time
        out.append(int(float(self.inboxes[0].get())))
        # Index of voltage, possible many
        voltage_loc = [
                int(float(loc_str)) for loc_str in self.inboxes[1].get().split(",")
            ]
        out.append(voltage_loc)
        # Index of current, possible many
        current_loc = [
                int(float(loc_str)) for loc_str in self.inboxes[2].get().split(",")
            ]
        out.append(current_loc)

        # Voltage prominence
        out.append(float(self.inboxes[3].get()))
        # Current prominence
        out.append(float(self.inboxes[4].get()))
        # Current correction factor
        out.append(float(self.inboxes[5].get()))
        return out

    def toggleFullScreen(self, event) -> None:
        """Function for toggeling fullscreen window"""
        self.fullScreenState = not self.fullScreenState
        self.nroot.attributes("-fullscreen", self.fullScreenState)

    def quitFullScreen(self, event) -> None:
        """Function for quiting fullscreen window"""
        self.fullScreenState = False
        self.nroot.attributes("-fullscreen", self.fullScreenState)

    def start_processing(self) -> None:
        """
        When
        ----------
        Calles when the start watch button is pressed.

        Does
        ----------
        If no watchdog is pressent it creates a new one with the
        current watch_path and save_path. It also starts to go
        through all the files currently present in the watch_path
        and processes them.

        If a watchdog is present it reports that it alerady is active

        Note
        ----------
        Checks that watch_path and save_path do not have there defualt
        value. If they have default no watchdog is initialized.

        """
        if self.watchdog is None:
            if self.watch_path == ".":
                self.log("No watch path selected!")
                return
            if self.save_path == ".":
                self.log("No save path selected!")
                return
            self.watchdog = Watchdog(
                path=self.watch_path,
                logfunc=self.log,
                detected_file=lambda file_path: self.detected_file(self.save_path, file_path),
            )
            self.watchdog.start()
            self.log("Watch started")
            # Find the files already in the folder
            file_paths_in_watch = [
                os.path.join(self.watch_path, file)
                for file in os.listdir(self.watch_path)
                if os.path.isfile(os.path.join(self.watch_path, file))
                and file[-4:] == ".txt"
            ]
            # Sort them if possible
            '''try:
                file_paths_in_watch.sort(key=lambda f: int(f.split("_")[-1][:-4]))
            except:
                pass'''
            self.log(
                "Starting to process existing files present in watch path and not in save path."
            )
            for i, file_path in enumerate(file_paths_in_watch):
                self.detected_file(self.save_path, file_path)
                self.log(f"Done with {i+1} of {len(file_paths_in_watch)}")
            self.log("Finished processing existing files.")
        else:
            self.log("Watch already started")

    def stop_processing(self) -> None:
        """
        When
        ----------
        Calles when the stop watch button is pressed.

        Does
        ----------
        If a watchdog is pressent it stops this.

        If a watchdog is not present it reports that there do not
        exsist a watchdog to stop

        Note
        ----------
        Checks that watch_path and save_path do not have there defualt
        value. If they have default no watchdog is initialized.

        """
        if self.watchdog:
            self.watchdog.stop()
            self.watchdog = None
            self.log("Watch stopped")
        else:
            self.log("Watch is already not running")

        self.log(f"Processing complete at {time.time()}")
        self.save_total_mm()

    def single_file(self) -> None:
        """
        When
        ----------
        Calles when the single_file button is pressed.

        Does
        ----------
        Opens a folder browser where the user can open a choose
        a file that should be processed. This only works is the
        watch is inactive. Due to how to program is made it calls
        the created method and since this has to store somewhere it
        produces a folder at the location of the program with name
        as specified in the class variable temp_save_path. After
        the procesing is finished the folder/directory is deleted
        along with anyting in it.

        """
        if self.watchdog is None:
            file_path = tk.filedialog.askopenfilename(
                #initialdir="/",  # Start directory
                initialdir="\\Raw_data_results",
                title="Browse files",
                filetypes=(("txt", "*.txt"),),
            )

            save_path = self.temp_save_path

            if file_path[-4:] == ".txt":
                if not os.path.exists(save_path):
                    os.mkdir(save_path)
                self.detected_file(save_path, file_path)
                rmtree(save_path)
        else:
            self.log("Watch activated, turn of to use single file.")

    def detected_file(self, save_path : str, file_path : str) -> None:
        """
        Parameters:
        ----------
        - save_path: str
            The path to the folder/directory where the impedance data
            should be stored.
        - file_path: str
            The absolute file path to a text file from the picoscope
            with time, voltage, and current data.

        Does:
        ----------
        The function is called each time a file is found and should be procesed.
        If the file that is found already has a save file it will ask a question
        wheater or not is should be overwritten. If the answer is yes, or no file
        already exsists. It will call the watch_call method from eis_sample.py
        with the parameters from the inboxes. If it detects that there are multiple
        instanses of voltace indexes one call to watch_call will be done for each
        and the saved files will be tagged with what index they correspond to.
        The impedance data calculated in the watch_call will be displayed in
        the figures (nyquist, bode and fft_spectrum).
        """
        # Logging that a file is found
        self.log(f"Detected the file\n {os.path.basename(file_path)}")
        # Due to the fact that the operation system, has the files open
        # the program waits a second to let the file be cloed by the OS.
        frequency_now = float(os.path.basename(file_path).split("freq")[1].split("Hz.txt")[0])
        self.log(f"Frequency now is: {frequency_now} Hz")

        # getting the parameters from the inboxes
        parameters = self.get_inbox_values()
        if self.applyfilter.get() == 1:
            self.filter_apply = True
        else:
            self.filter_apply = False

        self.filter_type= self.value_inside.get()
        self.beta_factor= self.filters[0].get()

        # Loops through the different voltage indicies if several
        for current_loc in parameters[2]:
            for voltage_loc in range(current_loc+1, current_loc+4):
                if voltage_loc in parameters[1]:
                    self.log(f"Processing for current location: {current_loc}")
                    self.log(f"and voltage location: {voltage_loc}")

                    sample = EIS_Sample.watch_call(
                        file_path,
                        save_path,
                        time_loc=parameters[0],
                        voltage_loc=voltage_loc,
                        current_loc=current_loc,
                        voltage_prominence=parameters[3],
                        current_prominence=parameters[4],
                        correction_factor_current=parameters[5],
                        add_loc_save=True,
                        filter_apply=self.filter_apply,
                        filter_type=self.filter_type,
                        beta_factor=self.beta_factor,
                    )
                    # Log that this file and index is finished
                    self.log(
                        f"Successfully saved and processed data from voltage index {voltage_loc}."
                    )
                    
                    # Plot to the different figures
                    self.plot_canvas_nyquist.clear()
                    sample.plot_nyquist_canvas(self.plot_canvas_nyquist)
                    self.plot_canvas_nyquist.update()

                    self.plot_canvas_bode.clear()
                    sample.plot_bode_canvas(self.plot_canvas_bode)
                    self.plot_canvas_bode.update()

                    self.plot_canvas_fft.clear()
                    sample.plot_fft_spectrum_canvas(self.plot_canvas_fft)
                    self.plot_canvas_fft.update()
                    # Update the window so all changes are visible
                    self.nroot.update()
                    
        self.files_processed += 1
        if self.files_processed ==  self.num_freqs:
            self.stop_processing()

    def select_path(self, save_path : str) -> None:
        """Helper function to select input folder/directory, called by Browse watch button"""
        # Ask for input file folder/directory
        path = f"Raw_data\\{save_path}"
        # If the path is not ""
        if path:
            # Store in object and log that it is selected
            self.watch_path = path
            self.log(f"Selected watch path:\n {path}")
        if not os.path.exists(path):
            raise Exception(f"Cannot find {path}")

    def select_save_path(self, save_path : str) -> None:
        """Helper function to select save folder/directory, called by Browse save button"""
        # Ask for save file folder/directory
        path = f"Save_folder\\{save_path}"
        # If the path is not ""
        if path:
            # Store in object and log that it is selected
            self.save_path = path
            self.log(f"Selected save path:\n {path}")
        if not os.path.exists(path):
            raise Exception(f"Cannot find {path}")

    def log(self, message : str) -> None:
        """
        Parameters:
        --------
        - message : str
            The message that shall be logged

        Does:
        --------
        Writes the message to the messagebox and makes a newline after
        the message, allso calls the nroot.update method.
        """
        try:
            self.messagebox.insert(tk.END, f"{message}\n")
            self.messagebox.see(tk.END)
            self.nroot.update()
        except Exception as e:
            print(f"Detected exception: {e}")

    def save_total_mm(self) -> None:
        merge_start = time.time()
        self.log("\nStart merging to one .mmfile.")

        # Make unique folder with timestamp as filename such that all measurements can be saved when run one after the other
        parent_dir = os.path.dirname(__file__)
        sub_path = os.path.join(parent_dir, "Total_mm")
        path = os.path.join(sub_path, self.save_time_string)
        os.mkdir(path) 

        
        selected_frequencies = self.save_metadata["selected_frequencies"].split(",")
        
        range_of_freqs = []
        for frequency in selected_frequencies:
            range_of_freqs.append(float(frequency))

        # Correctly identifies channels that are used for potential measurements, and not all channels
        for picoscope_index in range(self.num_picoscopes):
            for channel_index in range(1,4):
                if(self.channels[picoscope_index][channel_index]):
                    make_file = False
                    for filename in os.listdir(f"Save_folder\\{self.save_time_string}"):
                        num = re.findall(r'\d+', filename)
                        #f = os.path.join("Save_folder",filename)
                        if int(float(num[-1])) == 4*picoscope_index + channel_index + 1:
                            make_file=True

                    # If the channel is found, it will merge all files ending in the right integer into a single .mmfile. We want this corrected to sort in order from high to low.
                    if make_file == True:    
                        fil = open(f"Total_mm\\{self.save_time_string}\\total_mmfile_{4*picoscope_index + channel_index + 1}.mmfile", "w")

                        fil.write("Frequency\tReal\tImaginary\n")
                        data_all = []
                        for filename in os.listdir(f"Save_folder\\{self.save_time_string}"):
                            num = re.findall(r'\d+', filename)
                            f = os.path.join(f"Save_folder\\{self.save_time_string}",filename)
                            if int(float(num[-1])) == 4*picoscope_index + channel_index + 1:
                                tiny_file = open(f,"r")
                                lines = tiny_file.readlines()
                                length = len(lines)
                                if length == 2:
                                    line = lines[-1]
                                    data_all.append(line + "\n")
                                    #fil.write(line + "\n")
                                elif length == 1:
                                    self.log(f"File {f} do not have any values.")
                                else:
                                    self.log(f"File {f} has more than 1 line with values. The number of peaks are {length-1}. All will be added to the merged file.")
                                    for p in range(1,length):
                                        line = lines[p]
                                        data_all.append(line + "\n")
                                        #fil.write(line + "\n")

                                tiny_file.close()
                            
                        #contents = fil.readlines()
                        def my_sort(line):
                            line_fields = line.strip().split('\t')
                            amount = float(line_fields[0])
                            return amount

                        data_all.sort(key=my_sort)
                        f_from_FFT = []
                        Z_values_from_FFT = []
                        
                        for k in range(1, len(data_all)):
                            line_fields = data_all[k].strip().split('\t')
                            f_from_FFT.append(float(line_fields[0]))
                            Z_value_now = complex(float(line_fields[1]),float(line_fields[2]))
                            Z_values_from_FFT.append(Z_value_now)
                        
                        # Transforming the arrays to the correctd format
                        f_from_FFT = np.array(f_from_FFT)
                        Z_values_from_FFT = np.array(Z_values_from_FFT)
                        self.log("f_from_FFT is: " + str(f_from_FFT))
                        self.log("Z_values_from_FFT is: " + str(Z_values_from_FFT))
                        """
                        M, mu, Z_linKK, res_real, res_imag = linKK(f_from_FFT, Z_values_from_FFT, c=.85, max_M=100, fit_type='complex', add_cap=False)
                        print("M value is :" + str(M))
                        print("mu value is :" + str(mu))
                        print("Z lin kk array is :" + str(Z_linKK))
                        print("res_real array is :" + str(res_real))
                        print("res_imag array is :" + str(res_imag))
                        """



                        for line_index in range(len(data_all)):
                            line = data_all[line_index]
                            linesplit = float(line.split("\t")[0])
                            for frequency_index in range(self.num_freqs):
                                if abs((linesplit-float(range_of_freqs[frequency_index]))/linesplit) < 0.01:
                            # Criteria for K-K, that the real residual is less than 10%. For now this function is basically turned off
                            #if abs(res_real[p-1]) < 1:
                                    fil.write(line)

                        fil.close()
                        self.log(f"Made .mm file for pico: {picoscope_index} channel: {channel_index}")
            
        # Generate the Parameters.txt file that helps for plotting
        fil = open(f"Total_mm\\{self.save_time_string}\\Parameters.txt","w")

        fil.write(f"Date:\t{self.save_time_string[:10]}\n")
        fil.write(f"Time:\t{self.save_time_string[11:]}\n\n")

        fil.write(f"Cell numbers:\t{self.save_metadata["cell_numbers"]}\n")
        fil.write(f"Area:\t{self.save_metadata["area"]}\n")
        fil.write(f"Temperature:\t{self.save_metadata["temperature"]}\n")
        fil.write(f"Pressure:\t{self.save_metadata["pressure"]}\n")
        fil.write(f"DC current:\t{self.save_metadata["DC_current"]}\n")
        fil.write(f"AC current:\t{self.save_metadata["AC_current"]}\n")
        fil.close()

        self.log(f"Done creating merged .mmfile after\n\t{(time.time() - merge_start):.2f} s.\n")

if __name__ == "__main__":
    current_channels = [1,5]
    voltage_channels = [2,3,4,6,7]
    channels = np.array([[1,1,1,1],[1,1,1,0]])


    range_of_freqs = [1000, 100, 10, 1]


    parameters = { 
            "max_potential_channel" : str(20),
            "max_potential_stack" : str(20),
            "max_potential_cell" : str(20),
            "cell_numbers" : str(),
            "area" : str(),
            "temperature" : str(),
            "pressure" : str(),
            "DC_current" : str(1),
            "AC_current" : str(0.4),
            "shunt" : str(1),
            "selected_frequencies" : str(range_of_freqs)
            }
    save_path = os.listdir("Save_folder")[0]

    processor = Data_processor(current_channels, voltage_channels, 1, 4, save_path, 1, 2, channels, parameters)
    processor.nroot.mainloop()
