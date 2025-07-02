import asyncio
from picosdk.ps4000a import ps4000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
from SquidstatPyLibrary import AisDeviceTracker, AisExperiment, AisConstantCurrentElement, AisEISGalvanostaticElement
from PySide6.QtWidgets import QApplication
import qasync
import sys
import ctypes
import numpy as np
import time
import threading
import statistics
import os
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter
from scipy.fft import rfft, rfftfreq, next_fast_len

class EIS_experiment():
    def __init__(self, num_picoscopes, channels, range_of_freqs, bias, amplitude, sleep_time, constants, parameters, save_path):
        self.start_time = time.time()

        self.num_picoscopes = num_picoscopes
        self.channels = channels
        self.squid_channel = 1
        self.range_of_freqs = range_of_freqs
        self.num_freqs = len(self.range_of_freqs)
        self.bias = bias
        self.amplitude = amplitude
        self.sleep_time = sleep_time
        self.constants = constants
        self.parameters = parameters
        self.save_path = save_path

        self.pos = np.arange(16384, 16384 + self.num_picoscopes)     # The first picoscope is at 16384 from the manual # arange for faster creation (EDIT ELLING)
        self.c_handle = self.pos.astype(ctypes.c_int16)
        self.results = []

        self.admiral_started_sem = threading.Semaphore(0)
        self.pico_ready = threading.Semaphore(0)
        self.admiral_ready = asyncio.Event()
        self.admiral_started_event = asyncio.Event()

    async def perform_experiment(self):

        def device_connected_signal():
            print("Connection signal received")

        def new_element_signal(stepnumber):
            if stepnumber == 1 or stepnumber > self.num_freqs + 1:
                print(f"Admiral sleeping for {self.sleep_time} seconds")
            else:
                print(f"Admiral ready to start {self.range_of_freqs[stepnumber-2]}Hz")
                handler.pauseExperiment(self.squid_channel)

        def element_paused():
            self.admiral_ready.set()

        def element_resumed():
            for _ in range(self.num_picoscopes):
                self.admiral_started_sem.release()
            self.admiral_started_event.set()

        def experiment_stopped():
            print(f"Experiment complete at {time.time() - self.start_time }")
    
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
        handler.experimentPaused.connect(lambda: element_paused())
        handler.experimentResumed.connect(lambda: element_resumed())
        handler.experimentStopped.connect(lambda: experiment_stopped())

        #build experiment:
        experiment = AisExperiment()
        
        constant_element = AisConstantCurrentElement(self.bias, self.sleep_time, self.sleep_time)

        experiment.appendElement(constant_element, 1)
        for frequency_index in range(self.num_freqs):
            freq = self.range_of_freqs[frequency_index]
            geis_element = AisEISGalvanostaticElement(freq, freq, 1, self.bias, self.amplitude)
            periods = find_periods(freq)
            geis_element.setMinimumCycles(int(periods + 4 * freq))
    
            experiment.appendElement(geis_element, 1) 
        experiment.appendElement(constant_element, 1)

        uploading_status = handler.uploadExperimentToChannel(self.squid_channel,experiment)     #uploading the experiment onto a channel where it can be run
        if uploading_status:
            print(f"Uploading experiment to instrument: {uploading_status.message()}")
            
        await self.pico_setup()     #sets up the picoscope

        async def pico_task():
            """
            Coroutine for controlling the Picoscopes
            """
            
            for frequency_index in range(self.num_freqs):

                freq = self.range_of_freqs[frequency_index]

                print(f"Picoscopes sampling for {freq}Hz")
                res = await self.run_one_freq(freq)

                self.saveData(frequency_index, freq, res)
                self.results.append(res)      #This is where the sampling happens

        async def admiral_task():
            """
            Coroutine for controlling Admiral instruments
            """
            starting_error = handler.startUploadedExperiment(self.squid_channel)         #starting experiment
            if starting_error:
                print(f'Experiment starting: {starting_error.message()}')
                #self.log(f'Experiment starting: {starting_error.message()}')

            for _ in range(self.num_freqs):
                await self.admiral_ready.wait()
                self.admiral_ready.clear()
                for _ in range(self.num_picoscopes):
                    self.pico_ready.acquire()

                handler.resumeExperiment(self.squid_channel)
                
        task_p = asyncio.create_task(pico_task())
        task_a = asyncio.create_task(admiral_task())

        await task_p
        await task_a
        self.pico_close()

    def run_one_pico(self, picoscope_index, timebase, samples):
            for channel_index in range(4):
                valid_buffers = ps.ps4000aSetDataBuffer(self.c_handle[picoscope_index],
                                                        channel_index,
                                                        ctypes.byref(self.bufferMax[picoscope_index][channel_index]),
                                                        samples,
                                                        0,
                                                        0)
                assert_pico_ok(valid_buffers)
        
            preTriggerSamples = 0
            postTriggerSamples = samples
            #Here is the actual taking of data
            self.pico_ready.release()
            self.admiral_started_sem.acquire()

            time.sleep(2)
            error_RunBlock = ps.ps4000aRunBlock(self.c_handle[picoscope_index], preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
            assert_pico_ok(error_RunBlock)

            ready = ctypes.c_int16(0)
            check = ctypes.c_int16(0)
            while ready.value == check.value:
                ps.ps4000aIsReady(self.c_handle[picoscope_index], ctypes.byref(ready))      #Making sure the program waits until Pico is done sampling
            
            overflow = ctypes.c_int16()
            error_GetValues = ps.ps4000aGetValues(self.c_handle[picoscope_index], 0, ctypes.byref(ctypes.c_int16(samples)), 0, 0, 0,  ctypes.byref(overflow))
            assert_pico_ok(error_GetValues)

    async def pico_setup(self):      
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
                    pico_channel_status = ps.ps4000aSetChannel(self.c_handle[picoscope_index],
                                        channel_index,
                                        1,
                                        1,
                                        self.constants["currentRange" if channel_index == 0 else "cellPotentialRange"],
                                        0)
                    assert_pico_ok(pico_channel_status)

        print("PicoScope(s) is(are) ready")
        
    async def run_one_freq(self, freq):
        """
        Does the sampling for a single frequency. Is called once per frequency.
        """
        periods = find_periods(freq)

        timebase = find_timebase(freq)
        samples = int(np.ceil(sample_time(periods, freq)/((timebase-2)*20e-9)))
        time_intervals = ctypes.c_float()
        returned_max_samples = ctypes.c_int32()
        print(f"sample time: {sample_time(periods, freq)}")

        self.bufferMax = []

        threads = []
        for picoscope_index in range(self.num_picoscopes):

            valid_timebase = ps.ps4000aGetTimebase2(self.c_handle[picoscope_index], timebase, samples, ctypes.byref(time_intervals), ctypes.byref(returned_max_samples), 0)  #test if chosen timebase is valid
            assert_pico_ok(valid_timebase)

            self.bufferMax.append([])
            for channel_index in range(4):
                self.bufferMax[picoscope_index].append((ctypes.c_int16*samples)())
            threads.append(threading.Thread(target=self.run_one_pico, args=(picoscope_index, timebase, samples)))

        for thread in threads:
            thread.start()

        await self.admiral_started_event.wait()
        self.admiral_started_event.clear()
        print("Waiting for threads")
        for thread in threads:
            thread.join()

        freq_results = np.zeros([self.num_picoscopes, 4, samples])
        try:
            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(4):
                    fs = samples/sample_time(periods,freq)
                    unfiltered_results = np.asarray(adc2mV(self.bufferMax[picoscope_index][channel_index],
                                                        self.constants["currentRange" if channel_index == 0 else "cellPotentialRange"],
                                                        self.constants["maxADC"]))        #transforming data in buffer into readable mV data

                    freq_results[picoscope_index, channel_index] = filter_data(unfiltered_results, freq, fs)

        except Exception as exc:
            print(f"Exception in collecting and filtering data: {exc}", flush=True)
            raise(exc)
        
        return freq_results

    def pico_close(self):

        """
        Closing the unit and turning of led to indicate this
        """
        for i in range(self.num_picoscopes):
            ps.ps4000aFlashLed(self.c_handle[i],0)
            ps.ps4000aCloseUnit(self.c_handle[i])
        print("Closed picoscopes")

    def plot(self):
        for frequency_index in range(self.num_freqs):
            periods = find_periods(self.range_of_freqs[frequency_index])               
            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(4):
                    if self.channels[picoscope_index, channel_index]:
                        t = np.linspace(0,sample_time(periods, self.range_of_freqs[frequency_index]),len(self.results[frequency_index][picoscope_index,channel_index]))
                        fs = len(self.results[frequency_index][picoscope_index,channel_index])/sample_time(periods, self.range_of_freqs[frequency_index])

                        filtered_res = self.results[frequency_index][picoscope_index,channel_index]

                        plt.subplot(1,2,1)
                        plt.plot(t, filtered_res, label=f"{self.range_of_freqs[frequency_index]}Hz, pico {picoscope_index}, channel {channel_index}")

                        fourier_length = next_fast_len(len(t))
                        fourier = rfft(filtered_res, fourier_length)
                        f = rfftfreq(fourier_length)*fs
                    
                        plt.subplot(1,2,2)
                        plt.plot(f, fourier, label=f"{self.range_of_freqs[frequency_index]}Hz, pico {picoscope_index}, channel {channel_index}")

                plt.legend()
                plt.show()
    
    def saveData(self, frequency_index, freq, results):
        start_time = time.time()
        print("Start making raw data file:", flush=True)
        try:

            lst = []
            periods = find_periods(freq)

            time_ax = np.linspace(0,sample_time(periods, self.range_of_freqs[frequency_index]),len(results[0,0]))

            for k in range(len(time_ax)):                                                    
                lst.append(str(time_ax[k]))
                for picoscope_index in range(self.num_picoscopes):
                    for channel_index in range(4):
                        if self.channels[picoscope_index,channel_index]:
                            lst.append("\t"+str(results[picoscope_index, channel_index][k]))
                lst.append("\n")

            
            save_file = open("temp.txt","x")

            save_file.write("Date: \t" + datetime.today().strftime("%Y-%m-%d-") + "\n")
            save_file.write("Time: \t" + datetime.now().strftime("%H%M-%S") + "\n\n")
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
            input_value = "N"
            save_file.write("Run without potentiostat [Y/N]: \t" + str(input_value) + "\n")
            save_file.write("Frequencies selected: \t" + str(self.range_of_freqs)+ "\n")               
            save_file.write("\n")
            save_file.write("Time")
            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(4):
                    if self.channels[picoscope_index, channel_index]:
                        if channel_index == 0:
                            save_file.write("\tCurrent (as voltage)")
                        else:
                            save_file.write(f"\tVoltage{4 * picoscope_index + channel_index}")
            save_file.write("\n")
            save_file.write("s")

            for picoscope_index in range(self.num_picoscopes):
                for channel_index in range(4):
                    if self.channels[picoscope_index, channel_index]:
                        if picoscope_index == 0 and channel_index == 0:
                            save_file.write("\tmV")
                        else:
                            save_file.write("\tmV")
            save_file.write("\n\n")
            save_file.writelines(lst)
            save_file.close()

            os.rename("temp.txt", f"Raw_data\\{self.save_path}\\freq{self.range_of_freqs[frequency_index]}Hz.txt")
            print(f"Raw data file closed after {time.time() - start_time} s.\n")
            #self.log(f"Raw data file closed after\n\t{(time.time() - start_time):.2f} s.")
        except Exception as e:
            print(f"Exception in creating file: {e}")

#Convenience functions
def sample_time(periods, freq):        
    return periods/freq             #[s]

def find_timebase(freq):
    """
    Helper function to calculate timebase for each frequency. This is to avoid oversampling lower frequencies
    """
    sampling_freq_multiplier = 25
    return int(np.ceil(50000000/(sampling_freq_multiplier*freq)+ 2))

def find_periods(freq):
    if freq > 1000:
            periods = 890 + 0.111 * freq
    elif freq > 10:
            periods = freq 
    else:
        periods = 3 * freq
        
    return periods

def filter_data(data, freq, fs):
    filtered_data = data
    mean = statistics.mean(data)
    filtered_data = data - mean
    filtered_data = butter_lowpass_filter(filtered_data, [0.25*freq, 4*freq], fs, order=4)
    return filtered_data

def butter_lowpass_filter(data, cutOff, fs, order=4):
    nyq = 0.5*fs
    normalCutoff = [cutOff[0] / nyq,  cutOff[1] /nyq]
    b, a = butter(order, normalCutoff, btype='bandpass', analog = False)
    y = lfilter(b, a, data)
    return y


"""Notes:
- Currently saves data *twice* in order to interface with watch impedance. Optimally would just read the correct lines from the saved data, not save it twice
"""

if __name__ == "__main__":
    channels = np.array([[1,1,1,1],[1,1,1,0]])
    range_of_freqs = [1000, 100, 10, 1]

    constants = {
                    "timeIntervalns" : ctypes.c_float(),
                    "returnedMaxSamples" : ctypes.c_int32(),
                    "overflow" : ctypes.c_int16(),                                # create overflow location
                    "maxADC" : ctypes.c_int16(32767),                             # find maximum ADC count value
                    "currentRange" : int(float(10)),
                    "stackPotentialRange" : int(float(10)),
                    "cellPotentialRange" : int(float(10)),
                          }
    
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

    measurer = EIS_experiment(2, channels, range_of_freqs, 1, 0.4, constants, parameters, "Raw_data")

    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.run_until_complete(measurer.perform_experiment())
    app.quit()
