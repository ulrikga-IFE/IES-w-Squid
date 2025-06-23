import asyncio
from picosdk.ps4000a import ps4000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
from SquidstatPyLibrary import AisDeviceTracker
from SquidstatPyLibrary import AisExperiment
from SquidstatPyLibrary import AisEISGalvanostaticElement
import ctypes
import numpy as np
import time
import threading
import os
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter

class Measurer():
    def __init__(self, log, num_picoscopes, channels, range_of_freqs, bias, amplitude, constants, parameters):
        self.log = log
        self.num_picoscopes = num_picoscopes
        self.channels = channels
        self.squid_channel = 1
        self.periods = 30
        self.range_of_freqs = range_of_freqs
        self.num_freqs = len(self.range_of_freqs)
        self.bias = bias
        self.amplitude = amplitude
        self.constants = constants
        self.parameters = parameters

        self.pos = np.arange(16384, 16384 + self.num_picoscopes)     # The first picoscope is at 16384 from the manual # arange for faster creation (EDIT ELLING)
        self.c_handle = self.pos.astype(ctypes.c_int16)
        self.results = []

        self.date_today = datetime.today().strftime("%Y-%m-%d-")
        self.time_now = datetime.now().strftime("%H%M-%S")

    async def measure(self):

        def device_connected_signal():
            print("Connection signal received")
            self.log("Connection signal received")

        def new_element_signal(stepnumber):
            print(f"New element beginning:{stepnumber}")
            self.log(f"New element beginning:{stepnumber}")
            admiral_ready.set()


        pico_ready = asyncio.Event()            #initiating True/False flags in order to keep pico/admiral in sync
        admiral_ready = asyncio.Event()

        """
        admiral instruments setup      (not done in a pretty function because we need instances globally avaliable)
        """
        tracker = AisDeviceTracker.Instance()
        connection_status = tracker.connectToDeviceOnComPort("COM4")        #must manually write port
        if connection_status:
            print(f'Connection to Admiral instrument: {connection_status.message()}')  

        handler = tracker.getInstrumentHandler("Cycler2151") 
        
        
        tracker.newDeviceConnected.connect(device_connected_signal)  
        handler.experimentNewElementStarting.connect(lambda channel, data:new_element_signal(data.stepNumber))
        handler.experimentStopped.connect(lambda: print("Experiment complete"))

        #build experiment:
        experiment = AisExperiment()

        for i in range(self.num_freqs):
            freq = self.range_of_freqs[i]
            geisElement = AisEISGalvanostaticElement(freq, freq, 1, self.bias, self.amplitude)

            geisElement.setMinimumCycles(int(self.periods*2))
            experiment.appendElement(geisElement, 1)

        uploading_status = handler.uploadExperimentToChannel(self.squid_channel,experiment)     #uploading the experiment onto a channel where it can be run
        if uploading_status:
            print(f"Uploading experiment to instrument: {uploading_status.message()}")
            
        await self.pico_setup(pico_ready)     #sets up the picoscope


        #almost ready, now we prepare the concurrent tasks

        async def pico_task():
            """
            Coroutine for controlling the Picoscopes
            """
            
            for frequency_index in range(self.num_freqs):
                freq = self.range_of_freqs[frequency_index]
                await admiral_ready.wait()
                admiral_ready.clear()
                #time.sleep(sample_time(self.periods, freq)*0.5)
                print(f"Pico sampling for {freq}Hz")
                res = await self.run_one_freq(freq)
                #self.saveData(frequency_index, res)
                self.results.append(res)      #This is where the sampling happens


        async def admiral_task():
            """
            Coroutine for controlling Admiral instruments
            """
            await pico_ready.wait()
            starting_error = handler.startUploadedExperiment(self.squid_channel)         #starting experiment
            if starting_error:
                print(f'Experiment starting: {starting_error.message()}')

        
        task_p = asyncio.create_task(pico_task())
        task_a = asyncio.create_task(admiral_task())

        await task_p
        await task_a

        self.pico_close()

    def run_one_pico(self, picoscope_index, timebase, samples):
            for channel_index in range(4):
                valid_buffers = ps.ps4000aSetDataBuffers(self.c_handle[picoscope_index],
                                                        channel_index,
                                                        ctypes.byref(self.bufferMax[picoscope_index][channel_index]),
                                                        ctypes.byref(self.bufferMin[picoscope_index][channel_index]),
                                                        self.constants["maxSamples"],
                                                        0,
                                                        0)
                assert_pico_ok(valid_buffers)
        
            preTriggerSamples = 0
            postTriggerSamples = samples
            #Here is the actual taking of data
            error_RunBlock = ps.ps4000aRunBlock(self.c_handle[picoscope_index], preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
            assert_pico_ok(error_RunBlock)

            ready = ctypes.c_int16(0)
            check = ctypes.c_int16(0)
            t1 = time.time()
            while ready.value == check.value:
                ps.ps4000aIsReady(self.c_handle[picoscope_index], ctypes.byref(ready))      #Making sure the program waits until Pico is done sampling
            t2 = time.time()
            print(f"measured sample time: {t2-t1}")

            overflow = ctypes.c_int16()
            error_GetValues = ps.ps4000aGetValues(self.c_handle[picoscope_index], 0, ctypes.byref(ctypes.c_int16(samples)), 0, 0, 0,  ctypes.byref(overflow))
            assert_pico_ok(error_GetValues)

    async def pico_setup(self, pico_ready):      
        """
        Opens PicoScopes and sets channels. 
        """

        for picoscope_index in range(self.num_picoscopes):
            open_unit_status = ps.ps4000aOpenUnit(ctypes.byref(ctypes.c_int16(self.pos[picoscope_index])), None)
            assert_pico_ok(open_unit_status)

            flash_led_status = ps.ps4000aFlashLed(self.c_handle[picoscope_index],-1)
            assert_pico_ok(flash_led_status)       #add delay in order to indentify which unit is which?

            for channel_index in range(4):
                if self.channels[picoscope_index, channel_index]:
                    ps.ps4000aSetChannel(self.c_handle[picoscope_index],
                                        channel_index,
                                        1,
                                        1,
                                        self.constants["currentRange" if channel_index == 0 else "cellPotentialRange"],
                                        0)

        time.sleep(5)
        pico_ready.set()
        print("PicoScope(s) is(are) ready")
        
    async def run_one_freq(self, freq):
        """
        Does the sampling for a single frequency. Is called once per frequency.
        """
        timebase = find_timebase(freq)
        samples = int(np.ceil(sample_time(self.periods, freq)/((timebase-2)*20e-9)))
        time_intervals = ctypes.c_float()
        returned_max_samples = ctypes.c_int32()
        print(f"sample time: {sample_time(self.periods, freq)}")
        self.bufferMax = []
        self.bufferMin = []

        threads = []
        for picoscope_index in range(self.num_picoscopes):

            valid_timebase = ps.ps4000aGetTimebase2(self.c_handle[picoscope_index], timebase, samples, ctypes.byref(time_intervals), ctypes.byref(returned_max_samples), 0)  #test if chosen timebase is valid
            assert_pico_ok(valid_timebase)

            self.bufferMax.append([])
            self.bufferMin.append([])
            for channel_index in range(4):
                self.bufferMax[picoscope_index].append((ctypes.c_int16*samples)())
                self.bufferMin[picoscope_index].append((ctypes.c_int16*samples)())
            threads.append(threading.Thread(target=self.run_one_pico, args=(picoscope_index, timebase, samples)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        freq_results = np.zeros([self.num_picoscopes, 4, samples])
        maxADC = ctypes.c_int16(32767) #?????
        for picoscope_index in range(self.num_picoscopes):
            for channel_index in range(4):
                freq_results[picoscope_index, channel_index] = adc2mV(self.bufferMax[picoscope_index][channel_index],
                                                    self.constants["currentRange" if channel_index == 0 else "cellPotentialRange"],
                                                    self.constants["maxADC"])        #transforming data in buffer into readable mV data
        return freq_results

    def pico_close(self):
        """
        Closing the unit and turning of led to indicate this
        """
        for i in range(self.num_picoscopes):
            ps.ps4000aFlashLed(self.c_handle[i],0)
            ps.ps4000aCloseUnit(self.c_handle[i])
        print("pico is closed")

    def plot(self):
        for frequency_index in range(self.num_freqs):
            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(1,3):
                    t = np.linspace(0,sample_time(self.periods, self.range_of_freqs[frequency_index]),len(self.results[frequency_index][picoscope_index,channel_index]))
                    print(f"t is of lenght: {len(t)} for freq: {self.range_of_freqs[frequency_index]}")
                    fs = len(self.results[frequency_index][picoscope_index,channel_index])/sample_time(self.periods, self.range_of_freqs[frequency_index])

                    #filtered_res = butter_lowpass_filter(self.results[frequency_index][picoscope_index,channel_index], 10*self.range_of_freqs[frequency_index], fs)

                    filtered_res = self.results[frequency_index][picoscope_index,channel_index]
                    #filtered_res = filtered_res - statistics.mean(filtered_res)
                    #filtered_res = filtered_res/max(abs(filtered_res))
                
                    plt.subplot(1,2,1)
                    plt.plot(t, filtered_res, label=f"{self.range_of_freqs[frequency_index]}Hz, pico {1}, channel {channel_index}")
                    fourier = np.fft.fft(filtered_res)
                    f = np.fft.fftfreq(len(fourier))*fs
                    
                    plt.subplot(1,2,2)
                    plt.plot(f, fourier, label=f"{self.range_of_freqs[frequency_index]}Hz, pico {1}, channel {channel_index}")
                plt.legend()
                plt.show()

    def saveData(self, frequency_index, results):
        start_time = time.time()
        print("\nStart making raw data file:")
        self.log("Start making raw data file:")

        
        save_time_string = self.date_today + self.time_now
        save_path = f"Raw_data_result\\{save_time_string}"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        lst = []

        time_ax = np.linspace(0,sample_time(self.periods, self.range_of_freqs[frequency_index]),len(results[0,0]))

        for k in range(len(time_ax)):                                                    
            lst.append(str(time_ax[k]))
            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(4):
                    if self.channels[picoscope_index,channel_index]:
                        lst.append("\t"+str(results[picoscope_index, channel_index][k]))
            lst.append("\n")


        save_file = open(f"Raw_data_result\\{save_time_string}\\{self.range_of_freqs[frequency_index]}_Hz_freq_results.txt","x")

        save_file.write("Date: \t" + str(self.date_today) + "\n")
        save_file.write("Time: \t" + str(self.time_now) + "\n\n")
        picoscope_string = str()
        for picoscope_index in range(self.num_picoscopes):
            for channel_index in range(4):
                if int(self.channels[picoscope_index, channel_index]) == 1:
                    picoscope_string += str(1)
                else:
                    picoscope_string += str(0)

        if float(len(picoscope_string)) < 40:
            for picoscope_index in range(len(picoscope_string), 40, 1):
                picoscope_string += str(0)
        # NOT TESTED

        save_file.write("Picoscope code: \t" + str(picoscope_string) + "\n\n")
        save_file.write("Max potential (current channel) [V]: \t" + str(self.parameters["max_potential_channel"])+ "\n")
        save_file.write("Max stack potential [V]: \t" + str(self.parameters["max_potential_stack"]) + "\n")
        save_file.write("Max cell potential [V]: \t" + str(self.parameters["max_potential_cell"]) + "\n\n")
        save_file.write("Cell numbers: \t" + str(self.parameters["cell_numbers"])+ "\n")
        save_file.write("Area [cm2]: \t" + str(self.parameters["area"])+ "\n")
        save_file.write("Temperature [degC]: \t" + str(self.parameters["temperature"])+ "\n")
        save_file.write("Pressure [bar]: \t" + str(self.parameters["pressure"])+ "\n")
        save_file.write("DC current [A]: \t" + str(self.parameters["DC_current"])+ "\n")
        save_file.write("AC current [in pct of DC current]: \t" + str(self.parameters["AC_current"])+ "\n")
        save_file.write("Shunt: \t" + str(self.parameters["shunt"])+ "\n\n")

        #removes ability to run without pstat, but lowkey then just run the old program?
        input_value = "Y"
        save_file.write("Run without potentiostat [Y/N]: \t" + str(input_value) + "\n")
        save_file.write("Frequencies selected: \t" + str(self.range_of_freqs)+ "\n")               
        save_file.write("\n")
        save_file.write("Time")
        for picoscope_index in range(len(results)):
            if picoscope_index == 0:
                save_file.write("\tCurrent (as voltage)")
            else:
                save_file.write(f"\tVoltage{picoscope_index}")
        save_file.write("\n")
        save_file.write("s")
        for picoscope_index in range(len(results)):
            if picoscope_index == 0:
                save_file.write("\tmV")
            else:
                save_file.write("\tmV")
        save_file.write("\n\n")
        save_file.writelines(lst)
        save_file.close()
        print(f"Raw data file closed after {time.time() - start_time} s.")
        self.log(f"Raw data file closed after\n\t{(time.time() - start_time):.2f} s.")

    def print_internal(self):
        print(f"amplitude: {self.amplitude}")
        print(f"bias: {self.bias}")
        print(f"range of freqs: {self.range_of_freqs}")
        print(f"channels: {self.channels}")
        print(self.constants)



def sample_time(periods, freq):              #can also easily return a set time independent of frequency        
    return periods/freq             #[s]

def find_timebase(freq):
    """
    Helper function to calculate timebase for each frequency. This is to avoid oversampling lower frequencies
    """
    sampling_freq_multiplier = 200
    return int(np.ceil(50000000/(sampling_freq_multiplier*freq)+ 2))


def butter_lowpass(cutOff, fs, order=5):
    nyq = 0.5*fs
    normalCutoff = cutOff / nyq
    b, a = butter(order, normalCutoff, btype='low', analog = False)
    return b, a

def butter_lowpass_filter(data, cutOff, fs, order=4):
    b, a = butter_lowpass(cutOff, fs, order=order)
    y = lfilter(b, a, data)
    return y