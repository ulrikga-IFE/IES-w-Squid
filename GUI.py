import tkinter as tk
import tkinter.simpledialog
import tkinter.font
import numpy as np
import ctypes
import matplotlib.pyplot as plt
import os
import numpy as np

class GUI():
    def __init__(self, num_picoscopes, channels, start_measurements, open_fitting) -> None:
        self.root = tk.Tk()                             # Create main window
        self.root.geometry('1280x720')
        self.root.minsize(1800,900)                     # Makes the minimum size of the window equal to the initial size
        self.root.title("Control Panel")
        self.root.iconbitmap("ife.ico")

        for i in range(30):
            tk.Grid.rowconfigure(self.root, i, weight=1)
            tk.Grid.columnconfigure(self.root, i, weight=1)
        
        menubar = tk.Menu(self.root)
        helpmenu = tk.Menu(menubar,tearoff=0)
        helpmenu.add_command(label="How To",command=self.how_to)
        helpmenu.add_command(label="About",command=self.about)
        menubar.add_cascade(label="Help",menu=helpmenu)
        self.root.config(menu=menubar)

        scope_label = tk.Label(self.root,text="Number of picoscopes:")
        scope_label.grid(row=1,column=1, sticky='nsew')
        
        num_scope = tk.Label(self.root,text=num_picoscopes)
        num_scope.grid(row=1,column=2, sticky='nsew')


        for picoscope_index in range(num_picoscopes):
            chosen_channels = ""
            channels_label = tk.Label(self.root, text=f"From picoscope {picoscope_index+1}, you picked channels:")
            channels_label.grid(row=2+picoscope_index, column=1, sticky='nsew')

            for channel_index in range(4):
                if channels[picoscope_index,channel_index]:
                    chosen_channels += f"Channel {chr(65 + channel_index)} & " #note how 65 is the HTML number for A
            chosen_channels = chosen_channels[0:-3] + "\n"
    
            if num_picoscopes < 10:
                    chosen = tk.Label(self.root,text=chosen_channels[0:-1])
                    chosen.grid(row=2+picoscope_index,column=2, sticky='nsew')
        if num_picoscopes >= 10:                                   # If more than or equal to 10 channels, the screen is to small so instead make button to show as pop up-window
            chosen_channels_btn = tk.Button(self.root,text="Show chosen channels",command=lambda: self.show_chosen_channels(chosen_channels))
            chosen_channels_btn.grid(row=2,column=2, sticky='nsew')

        self.messagebox = tk.Text(self.root)
        self.messagebox.grid(row=1,column=4,rowspan=num_picoscopes+14,columnspan=20, sticky='nsew')
        
        self.start_equip_btn = tk.Button(self.root,text="Start measurements",command=start_measurements)
        self.start_equip_btn.grid(row=num_picoscopes+15,column=20, sticky='nsew')

        self.full = False
        fullscreen_btn = tk.Button(self.root,text="Fullscreen",command=self.fullscrn)
        fullscreen_btn.grid(row=num_picoscopes+15,column=21, sticky='nsew')

        quit_btn = tk.Button(self.root,text="Exit window",command=self.destroy)
        quit_btn.grid(row=num_picoscopes+15,column=22, sticky='nsew')

        # Button that open the dashboard_for_plotting_and_fitting-window. 
        open_db_for_plotting_and_fitting_btn = tk.Button(self.root, text="Open dashboard for plotting and fitting", bg='sky blue', command=open_fitting)
        open_db_for_plotting_and_fitting_btn.grid(row=num_picoscopes+19, rowspan=2, column=20, columnspan=4 ,sticky='nsew')
        
        par_label = tk.Label(self.root,text="Parameters:")
        par_label.grid(row=num_picoscopes+3,column=1, sticky='nsew')
        self.submit_btn = tk.Button(self.root,text="Submit all parameters",command=self.collect_parameters)
        self.submit_btn.grid(row=num_picoscopes+3,column=2, sticky='nsew')

        ps_par_label = tk.Label(self.root,text="Parameters for Picoscopes:")
        ps_par_label.grid(row=num_picoscopes+4,column=1, sticky='nsew')

        maximumsamplingfreq_label = tk.Label(self.root,text="Maximum frequency sampled (Hz):")
        maximumsamplingfreq_label.grid(row=num_picoscopes+6,column=1, sticky='nsew') 
        self.maximumsamplingfreq = tk.Entry(self.root)
        self.maximumsamplingfreq.grid(row=num_picoscopes+6,column=2, sticky='nsew') 
        self.maximumsamplingfreq.insert(0,"5000")

        max_pot_current_channel_label = tk.Label(self.root,text="Max potential (current channel):")
        max_pot_current_channel_label.grid(row=num_picoscopes+7,column=1, sticky='nsew')
        self.max_pot_current_channel = tk.Entry(self.root)
        self.max_pot_current_channel.grid(row=num_picoscopes+7,column=2, sticky='nsew')
        self.max_pot_current_channel.insert(0,"20")     
                                                    # CHANGE THIS STRING TO CHANGE DEFAULT VALUE
        max_pot_stack_voltage_channel_label = tk.Label(self.root,text="Max stack potential [V]:")
        max_pot_stack_voltage_channel_label.grid(row=num_picoscopes+8,column=1, sticky='nsew')
        self.max_pot_stack_voltage_channel = tk.Entry(self.root)
        self.max_pot_stack_voltage_channel.grid(row=num_picoscopes+8,column=2, sticky='nsew')
        self.max_pot_stack_voltage_channel.insert(0,"20") # CHANGE THIS STRING TO CHANGE DEFAULT VALUE

        max_pot_cell_voltage_channel_label = tk.Label(self.root,text="Max cell potential [V]:")
        max_pot_cell_voltage_channel_label.grid(row=num_picoscopes+9,column=1, sticky='nsew')
        self.max_pot_cell_voltage_channel = tk.Entry(self.root)
        self.max_pot_cell_voltage_channel.grid(row=num_picoscopes+9,column=2, sticky='nsew')
        self.max_pot_cell_voltage_channel.insert(0,"20")                                            # CHANGE THIS STRING TO CHANGE DEFAULT VALUE

        experimental_description_label = tk.Label(self.root,text="Description of experiment:")
        experimental_description_label.grid(row=num_picoscopes+10,column=1, sticky='nsew')

        cell_numbers_label = tk.Label(self.root,text="Cell numbers (separate by comma):")
        cell_numbers_label.grid(row=num_picoscopes+11,column=1, sticky='nsew')
        self.cell_numbers = tk.Entry(self.root)
        self.cell_numbers.grid(row=num_picoscopes+11,column=2, sticky='nsew')
        self.cell_numbers.insert(0,"1,2,3,4,5,6,7,8,9,10")

        area_label = tk.Label(self.root,text="Area (in cm2):")
        area_label.grid(row=num_picoscopes+12,column=1, sticky='nsew')
        self.area = tk.Entry(self.root)
        self.area.grid(row=num_picoscopes+12,column=2, sticky='nsew')
        self.area.insert(0,"195")

        temperature_label = tk.Label(self.root,text="Temperature (in C):")
        temperature_label.grid(row=num_picoscopes+13,column=1, sticky='nsew')
        self.temperature = tk.Entry(self.root)
        self.temperature.grid(row=num_picoscopes+13,column=2, sticky='nsew')
        self.temperature.insert(0,"50")

        pressure_label = tk.Label(self.root,text="Pressure (in bar):")
        pressure_label.grid(row=num_picoscopes+14,column=1, sticky='nsew')
        self.pressure = tk.Entry(self.root)
        self.pressure.grid(row=num_picoscopes+14,column=2, sticky='nsew')
        self.pressure.insert(0,"0")

        dc_current_label = tk.Label(self.root,text="DC current (in A):")
        dc_current_label.grid(row=num_picoscopes+15,column=1, sticky='nsew')
        self.dc_current = tk.Entry(self.root)
        self.dc_current.grid(row=num_picoscopes+15,column=2, sticky='nsew')
        self.dc_current.insert(0,"1") 

        ac_current_label = tk.Label(self.root,text="AC current (in percent of DC):")
        ac_current_label.grid(row=num_picoscopes+16,column=1, sticky='nsew')
        self.ac_current = tk.Entry(self.root)
        self.ac_current.grid(row=num_picoscopes+16,column=2, sticky='nsew')
        self.ac_current.insert(0,"0.4") 

        shunt_selector_name = tk.Label(self.root,text = "Select shunt:")
        shunt_selector_name.grid(row=num_picoscopes+17,column=1,sticky='nsew')
        shunt_options = [
                "200mA/200mV",
                "2A/200mV",
                "5A/50mV",
                "25A/60mV",
                "100A/60mV",
                "200A/60mV",
                "Custom"
                ]

        self.shunt_value = tk.StringVar(self.root)                                                 # CHANGE THIS STRING TO CHANGE DEFAULT VALUE
        self.shunt_value.set("200mA/200mV")

        dropmenu = tk.OptionMenu(self.root, self.shunt_value, *shunt_options)
        dropmenu.grid(row=num_picoscopes+17,column=2,sticky='nsew') 

        # The frequencies selected when running without pstat connected
        frequencies_selected_label = tk.Label(self.root,text="Frequencies selected (separated by comma):")
        frequencies_selected_label.grid(row=num_picoscopes+19,column=1, sticky='nsew')
        self.frequencies_selected = tk.Entry(self.root)#,height=1,width=35)
        self.frequencies_selected.grid(row=num_picoscopes+20,column=1, columnspan = 4, sticky='nsew')     
        self.frequencies_selected.insert(0,"10000,5000,2000,1000,500,200,100,50,20,10,5,2,1")

        self.runwithoutpstat_button = tk.Label(self.root,text="Run without potentiostat:")
        self.runwithoutpstat_button.grid(row=num_picoscopes+21,column=1,sticky='nsew')
        self.runwithoutpstatcheck = tk.IntVar()
        self.runwithoutpstatcheck.set(1)
        self.runwithoutpstat = tk.Checkbutton(self.root,variable=self.runwithoutpstatcheck, onvalue=1, offvalue=0)
        self.runwithoutpstat.grid(row=num_picoscopes+21,column=2,sticky='nsew')

        self.test_mode_button = tk.Label(self.root,text="Test mode (data is loaded from file):")
        self.test_mode_button.grid(row=num_picoscopes+22,column=1,sticky='nsew')
        self.test_mode_check = tk.IntVar()
        self.test_mode_check.set(0)
        self.test_mode = tk.Checkbutton(self.root,variable=self.test_mode_check, onvalue=1, offvalue=0)
        self.test_mode.grid(row=num_picoscopes+22,column=2,sticky='nsew')

        self.btn_font = tk.font.Font(quit_btn, quit_btn.cget("font"))
        self.textbox_font = tk.font.Font(self.messagebox, self.messagebox.cget("font"))
        self.STANDARD_FONTSIZE = self.btn_font.configure()["size"]
        self.STANDARD_FAMILY = self.btn_font.configure()["family"]
        self.TEXTBOX_FONTSIZE = self.textbox_font.configure()["size"]
        self.TEXTBOX_FAMILY = self.textbox_font.configure()["family"]

    def how_to(self):
        tk.messagebox.showinfo("How To",
                            "How to use the GUI control panel:\n"+
                            "----------------------------------------------------\n\n"+
                            "- After picking the number of picoscopes and the wanted channels, you get to the GUI control panel.\n\n"+
                            "- Here you can set the parameters for the biologic device and the picoscopes. Remember '.' for decimal.\n\n"+
                            "- After picking your parameters, you click on the 'Submit all parameters'-button. When this button turns green, your parameters are submitted.\n\n"+
                            "- Now, you can connect to devices through the 'Connect to devices'-button. When connected, the button turns green.\n\n"+
                            "- When connected, you can start the measurements through the button 'Start measurements'.\n\n"+
                            "- You will now get a pop-up window confirming that the measurements started.\n\n"+
                            "- Click 'OK' to continue.\n\n"+
                            "- Now, wait while your program runs the measurements. There will be printed useful information on the screen during this time.\n\n"+
                            "- When the measurement is done, you will see a plot with the voltage as a function of time.\n\n"+
                            "- If this looks nice, accept it in the pop up-window.\n\n"+
                            "- Wait for the remaining program to finish. It is finished when multiple windows showing complete nyquist and bode plots appear.\n\n"+
                            "- Close the windows by using the 'Exit window'-button.",
                            parent=self.root)

    def about(self):
        tk.messagebox.showinfo("About",
                            "Author: Håkon Kvitvik Eckle\n"+
                            "Contact: hakon.eckle@gmail.com\n\n"+
                            "Made for IFE - Institutt for Energiteknologi during the summer of 2022.\n\n"+
                            "The program will be used to help improve fuel cell analyses by simultaneously running a biologic device and multiple picoscopes, and do FFT on the results to get impedance data.",
                            parent=self.root)
    
    def show_chosen_channels(self, chosen_channels=""):
        tk.messagebox.showinfo("Chosen channels:",chosen_channels,parent=self.root)

    def collect_parameters(self):
        '''
        Initializes the parameters into the corresponding arrays,
        finds the corresponding voltage ranges, calculates the total
        time for the potentiostat and picoscope, so that these can
        be matched.
        '''

        def find_voltage_range(potential):
            """
            Parameters:
            --------
            - potential : str or float
                The maximum potential expected to be measured on a channel

            Does:
            --------
            Finds the corresponding settting for the picoscope unit so the 
            potential range is as small as possible. This ensures maximum
            resolution of the measurements.
            """
            potential = float(potential)
            if potential > 10.01:           
                range = 10                  # 10 = +-20V (See picoscope SDK documentation page 83)
            elif potential > 5.01:
                range = 9                   # 9 = +- 10V
            elif potential > 1.01:
                range = 8                   # 8 = +- 5V
            elif potential > 0.501:
                range = 7                   # 7 = +- 1V
            elif potential > 0.201: 
                range = 6                   # 6 = +- 0.5 V
            elif potential > 0.101: 
                range = 5                   # 5 = +- 200 mV
            else: 
                range = 4                   # 4 = +- 100 mV
            return(range)
    
        current_range = find_voltage_range(self.max_pot_current_channel.get())
        stack_potential_range = find_voltage_range(self.max_pot_stack_voltage_channel.get())
        """NOTE: 1B and 5B were set to stack potential. Ask about this"""

        cell_potential_range = find_voltage_range(self.max_pot_cell_voltage_channel.get())
 
        parameters = { 
                       "max_potential_channel" : str(self.max_pot_current_channel.get()),
                       "max_potential_stack" : str(self.max_pot_stack_voltage_channel.get()),
                       "max_potential_cell" : str(self.max_pot_cell_voltage_channel.get()),
                       "cell_numbers" : str(self.cell_numbers.get()),
                       "area" : str(self.area.get()),
                       "temperature" : str(self.temperature.get()),
                       "pressure" : str(self.pressure.get()),
                       "DC_current" : str(self.dc_current.get()),
                       "AC_current" : str(self.ac_current.get()),
                       "shunt" : str(self.shunt_value.get()),
                       "selected_frequencies" : str(self.frequencies_selected.get())
                       }
        constants = {
                          "timeIntervalns" : ctypes.c_float(),
                          "returnedMaxSamples" : ctypes.c_int32(),
                          "overflow" : ctypes.c_int16(),                                # create overflow location
                          "maxADC" : ctypes.c_int16(32767),                             # find maximum ADC count value
                          "currentRange" : int(float(current_range)),
                          "stackPotentialRange" : int(float(stack_potential_range)),
                          "cellPotentialRange" : int(float(cell_potential_range)),
                          }

        match parameters["shunt"]:
            case "200mA/200mV":
                parameters["resistor_value"] = 1
            case "2A/200mV":
                parameters["resistor_value"] = 0.134                 # Modified from experimental measurement 30.11.2022 - Based on connection on large pins
            case "5A/50mV":
                parameters["resistor_value"] = 0.01
            case "25A/60mV":
                parameters["resistor_value"] = 0.0024
            case "100A/60mV":
                parameters["resistor_value"] = 0.0006
            case "200A/60mV":
                parameters["resistor_value"] = 0.0003
            case "Custom":
                parameters["resistor_value"] = tk.simpledialog.askfloat("Resistor value in Ohm", "You have selected a custom shunt, please give the resistance value in ohm.",
                                parent=self.root)
        
        self.submit_btn.config(bg="#00ff00")

        return parameters, constants
    
    def fullscrn(self):
        '''
        The function to control full screen, and resize text.
        '''
        try:
            self.full = not self.full       
            self.root.attributes('-fullscreen', self.full)
            all_widgets = self.root.winfo_children()
            for item in all_widgets:
                if item.winfo_class() == "Text":
                    if self.full:
                        item.configure(font=tk.font.Font(size=18,family=self.TEXTBOX_FAMILY))
                    else:
                        item.configure(font=tk.font.Font(size=self.TEXTBOX_FONTSIZE,family=self.TEXTBOX_FAMILY))
                else:
                    if self.full:
                        item.configure(font=tk.font.Font(size=16,family=self.STANDARD_FAMILY))
                    else:
                        item.configure(font=tk.font.Font(size=self.STANDARD_FONTSIZE,family=self.STANDARD_FAMILY))
        except:
            pass        # Try/Except to get rid of some weird error raised somewhere

    def destroy(self):
        '''
        Function to destroy all plots and all windows
        '''
        print("\nPROGRAM CLOSED BY USER.\n\n")
        plt.close('all')
        self.root.destroy()

    def log(self, message):
        """
        Parameters:
        --------
        - message : str
            The message that shall be logged

        Does:
        --------
        Writes the message to the messagebox and makes a newline after
        the message, also calls the root.update method.
        """
        self.messagebox.insert(tk.END, message+"\n")
        self.messagebox.see(tk.END)
        self.root.update()

    
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
            
    GUI()

"""Notes:
- When multithreading, one cannot log to the main GUI window. 
    -This is because only one thread can access the GUI at once, and in order to use watch_impedance, we need it to be in the main thread as it also opens a GUI window
    -This means the other thread, the one doing the measurements, cannot have access to GUI beyond matplotlib

- The "connect" feature is missing. I could maybe add it, will look into it.

- TODO:
    - Fix the save_total_mm to not be as cursed
    - Cleanup, I've done too many cursed things due to threading, and this class is way beyond its actual scope atm
"""