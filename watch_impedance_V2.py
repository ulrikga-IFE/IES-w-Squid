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
from typing import Iterable
import dependencies.GUI_helper as GUI_helper
import tkinter as tk
from shutil import rmtree
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from dependencies.eis_sample import EIS_Sample
import time


# The class that handels the folder watching and trigers when a file is created
class Watchdog(PatternMatchingEventHandler, Observer):
    """
    Handles the watching of the folder by the Observer class and the
    PatternMatchingEventHandler. Works by continuously searching the path
    for updates and if a file is created is calls the on_created function.
    """

    def __init__(self, path=".", patterns=("*.txt",), logfunc=print, created=None):
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
        self.created = created

    def on_created(self, event):
        # This function is called when a file is created
        self.created(event.src_path)


class Interface:
    def __init__(self,current_channel,channels_from_main, resistor_value, num_freqs, save_path, is_last, save_final):
        """
        Set up the interface and its widgets. Calls the nroot.mainloop starting
        the programs looping.
        """
        # Watch and save default values
        self.watchdog = None
        self.watch_path = "."
        self.save_path = "."
        self.temp_save_path = "temp_watch_impedance"
        self.current_channel = current_channel
        self.channels_from_main = channels_from_main
        self.resistor_value = str(resistor_value)
        self.num_freqs = num_freqs

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
        self.is_last = is_last
        self.save_final = save_final

    def make_canvases(self):
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

    def make_buttons(self):
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
            command=self.start_watch,
            width=self.BUTTON_WIDTH_CHARACTERS,
            height=self.BUTTON_HEIGHT_CHARACTERS,
        ).place(x=2 * self.FIGL_PIXELS, y=self.BUTTON_HEIGHT_PIXELS * butt_num)
        butt_num += 1
        tk.Button(
            self.nroot,
            text="Stop Watch",
            command=self.stop_watch,
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

    def make_inboxes(self):
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
        # Creating and placing buttons from GUI.py
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
        self.inboxes[1].set(self.channels_from_main)    # Gets the channels you picked at the beginning (except 'current channel' 1)
        self.inboxes[2].set(self.current_channel)                        # Hard coded as 1 as standard (channel 1 = first channel on picoscope).
        self.inboxes[3].set("0.001")                                    # This is set very low because that includes all peaks, and ensures that the current peak is also found in the potential sweep.
        self.inboxes[4].set("0.4")                                     # SHOULD BE 0.5
        self.inboxes[5].set(self.resistor_value)                      # This is set as Ohm to be more understandable. Option let's the operator set this in the main GUI interface

    def make_filterfunction(self):
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
        self.value_inside.set("Kaiser")

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

    def get_inbox_values(self):
        """
        Reads the values from the inboxes and returns a list of them.
        Does the conversions by the float method and if the voltage index
        string contains a "," it is separated into a list of indexes.
        """
        out = []
        # Index of time
        out.append(int(float(self.inboxes[0].get())))
        # Index of voltage, possible many
        voltage_loc_str = self.inboxes[1].get()
        # Check if multiple
        if "," in voltage_loc_str:
            voltage_loc = [
                int(float(loc_str)) for loc_str in voltage_loc_str.split(",")
            ]
            out.append(voltage_loc)
        else:
            out.append(int(float(self.inboxes[1].get())))
        # Current index
        out.append(int(float(self.inboxes[2].get())))
        # Voltage prominence
        out.append(float(self.inboxes[3].get()))
        # Current prominence
        out.append(float(self.inboxes[4].get()))
        # Current corection factor
        out.append(float(self.inboxes[5].get()))
        return out

    def toggleFullScreen(self, event):
        """Function for toggeling fullscreen window"""
        self.fullScreenState = not self.fullScreenState
        self.nroot.attributes("-fullscreen", self.fullScreenState)

    def quitFullScreen(self, event):
        """Function for quiting fullscreen window"""
        self.fullScreenState = False
        self.nroot.attributes("-fullscreen", self.fullScreenState)

    def start_watch(self):
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
                created=lambda file_path: self.created(self.save_path, file_path),
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
                self.created(self.save_path, file_path)
                self.log(f"Done with {i+1} of {len(file_paths_in_watch)}")
            self.log("Finished processing existing files.")
        else:
            self.log("Watch already started")

    def stop_watch(self):
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
        print("Stopped Watch")
        if(self.is_last):
            self.log("Processing complete")
            self.save_final()

    def single_file(self):
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
                self.created(save_path, file_path)
                rmtree(save_path)
        else:
            self.log("Watch activated, turn of to use single file.")

    def created(self, save_path, file_path):
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
        print(f"Detected the file\n {os.path.basename(file_path)}")
        # Due to the fact that the operation system, has the files open
        # the program waits a second to let the file be cloed by the OS.
        frequency_now = float(os.path.basename(file_path).split("freq")[1].split("Hz.txt")[0])
        self.log(f"Frequency now is: {frequency_now} Hz")
        print(f"Frequency now is: {frequency_now} Hz")
        time.sleep(1)
        # getting the parameters from the inboxes
        parameters = self.get_inbox_values()
        if self.applyfilter.get() == 1:
            self.filter_apply = True
        else:
            self.filter_apply = False

        self.filter_type= self.value_inside.get()
        self.beta_factor= self.filters[0].get()

        # Checking is the voltage indicies are more than one (Iterable)
        if isinstance(parameters[1], Iterable):
            # Loops through the different voltage indicies if several
            for voltage_loc in parameters[1]:
                # Check if the file should be processed
                save = True
                full_save_file_path = EIS_Sample.get_full_save_path(
                    save_path, file_path, voltage_loc=voltage_loc, add_loc_save=True
                )
                if os.path.exists(full_save_file_path):
                    # Ask yes/no queston if the save file already exsists
                    '''
                    save = GUI.popupYesNo(
                        f"The save file {full_save_file_path} already exists, do you want to overwrite?",
                        "File already exists",
                    )
                    '''
                    save = True
                # When file should be processed
                if save:
                    # Create EIS_Sample and do RFFT,fit, and saving
                    sample = EIS_Sample.watch_call(
                        file_path,
                        save_path,
                        time_loc=parameters[0],
                        voltage_loc=voltage_loc,
                        current_loc=parameters[2],
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
                    
        else:
            voltage_loc = parameters[1]
            save = True
            full_save_file_path = EIS_Sample.get_full_save_path(
                save_path, file_path, voltage_loc, True
            )
            if os.path.exists(full_save_file_path):
                # Ask yes/no queston if the save file already exsists
                save = GUI_helper.popupYesNo(
                    f"The save file {full_save_file_path} already exists, do you want to overwrite?",
                    "File already exists",
                )
            #print("Doing single file fitting")
            if save:
                # Create EIS_Sample and do RFFT,fit, and saving
                sample = EIS_Sample.watch_call(
                    file_path,
                    save_path,
                    time_loc=parameters[0],
                    voltage_loc=voltage_loc, #parameters[1],
                    current_loc=parameters[2],
                    voltage_prominence=parameters[3],
                    current_prominence=parameters[4],
                    correction_factor_current=parameters[5],
                    filter_apply=self.filter_apply,
                    filter_type=self.filter_type,
                    beta_factor=self.beta_factor,
                )
                # Log that this file is finished
                self.log(f"Successfully saved and processed data voltage index {voltage_loc}.")
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
                self.nroot.update()
        # log any error that happens
        #except Exception as E:
        #    self.log(
        #        f"The following error occured while trying to process {os.path.basename(file_path)}:\n{str(E)}"
        #    )
        #    print(f"The following error occured while trying to process {os.path.basename(file_path)}:\n{str(E)}")

        self.files_processed += 1
        if self.files_processed ==  self.num_freqs:
            self.stop_watch()

    def select_path(self,save_path):
        """Helper function to select input folder/directory, called by Browse watch button"""
        # Ask for input file folder/directory
        path = f"Data_for_processing\\{save_path}"
        # If the path is not ""
        if path:
            # Store in object and log that it is selected
            self.watch_path = path
            self.log(f"Selected watch path:\n {path}")
        if not os.path.exists(path):
            raise Exception(f"Cannot find {path}")

    def select_save_path(self, save_path):
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

    def log(self, message):
        """
        Parameters:
        --------
        - message : str
            The message that shall be logged

        Does:
        --------
        Writes the message to the messagebox and makes a newline after
        the message, allso calls the nroot.updete method.
        """
        self.messagebox.insert(tk.END, f"{message}\n")
        self.messagebox.see(tk.END)
        self.nroot.update()


if __name__ == "__main__":
    Interface()
