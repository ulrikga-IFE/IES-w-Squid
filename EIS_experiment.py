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
    """
    EIS_experiment
    ===========
    Class which handles connecting to hardware,
    syncing experiments and measurements,
    taking data, and pre-processing and saving of data.

    Member functions
    --------
    - perform_experiment
    - run_one_pico
    - pico_setup
    - run_one_freq
    - pico_close
    - plot
    - saveData
    
    """
    def __init__(self, 
                    num_picoscopes      : int,
                    channels            : np.ndarray[tuple[int,int], bool],
                    experiment_ranges   : np.ndarray[int, int],
                    range_of_freqs      : np.ndarray[int, float],
                    bias                : float,
                    amplitude           : float,
                    low_freq_periods    : float,
                    sleep_time          : float, 
                    time_path           : str,
                    save_metadata       : dict[str, str]
    ) -> None:
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

        Description
        ----------
        Initializes all member variables.
        """
        
        self.start_time = time.time()
        self.admiral_channel = 1


        self.num_picoscopes = num_picoscopes
        self.channels = channels

        self.experiment_ranges = experiment_ranges

        self.range_of_freqs = range_of_freqs
        self.num_freqs = len(self.range_of_freqs)

        self.bias = bias
        self.amplitude = amplitude
        self.low_freq_periods = low_freq_periods
        self.sleep_time = sleep_time

        self.save_path = time_path
        self.save_metadata = save_metadata

        self.pos = np.arange(16384, 16384 + self.num_picoscopes)     # The first picoscope is at 16384 from the manual # arange for faster creation (EDIT ELLING)
        self.c_handle = self.pos.astype(ctypes.c_int16)
        self.results = []

        self.admiral_started_sem = threading.Semaphore(0)
        self.pico_ready = threading.Semaphore(0)
        self.admiral_ready = asyncio.Event()
        self.admiral_started_event = asyncio.Event()
        self.experiment_complete = asyncio.Event()

    async def perform_experiment(self) -> None:

        def device_connected_signal() -> None:
            print("Connection signal received")

        def new_element_signal(stepnumber) -> None:
            if stepnumber == 1 or stepnumber > self.num_freqs + 1:
                print(f"Admiral sleeping for {self.sleep_time} seconds")
            else:
                print(f"Admiral ready to start {self.range_of_freqs[stepnumber-2]}Hz")
                handler.pauseExperiment(self.admiral_channel)

        def element_paused() -> None:
            self.admiral_ready.set()

        def element_resumed() -> None:
            for _ in range(self.num_picoscopes):
                self.admiral_started_sem.release()
            self.admiral_started_event.set()

        def experiment_stopped() -> None:
            print(f"Experiment complete at {time.time() - self.start_time }")
            self.experiment_complete.set()
    
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
            periods = find_periods(freq, self.low_freq_periods)
            geis_element.setMinimumCycles(int(periods + 4 * freq))
    
            experiment.appendElement(geis_element, 1) 
        experiment.appendElement(constant_element, 1)

        uploading_status = handler.uploadExperimentToChannel(self.admiral_channel,experiment)     #uploading the experiment onto a channel where it can be run
        if uploading_status:
            print(f"Uploading experiment to instrument: {uploading_status.message()}")
            
        await self.pico_setup()     #sets up the picoscope

        async def pico_task() -> None:
            """
            Coroutine for controlling the Picoscopes
            """
            
            for frequency_index in range(self.num_freqs):

                freq = self.range_of_freqs[frequency_index]

                print(f"Picoscopes sampling for {freq}Hz")
                res = await self.run_one_freq(freq)

                self.saveData(frequency_index, freq, res)
                self.results.append(res)      #This is where the sampling happens

        async def admiral_task() -> None:
            """
            Coroutine for controlling Admiral instruments
            """
            starting_error = handler.startUploadedExperiment(self.admiral_channel)         #starting experiment
            if starting_error:
                print(f'Experiment starting: {starting_error.message()}')
                #self.log(f'Experiment starting: {starting_error.message()}')

            for _ in range(self.num_freqs):
                await self.admiral_ready.wait()
                self.admiral_ready.clear()
                for _ in range(self.num_picoscopes):
                    self.pico_ready.acquire()

                handler.resumeExperiment(self.admiral_channel)
            
            await self.experiment_complete.wait()
                
        task_p = asyncio.create_task(pico_task())
        task_a = asyncio.create_task(admiral_task())

        await task_p
        await task_a
        self.pico_close()

    def run_one_pico(self,
                        picoscope_index : int,
                        timebase : int,
                        samples : int,
    ) -> None:
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

    async def pico_setup(self) -> None:      
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
                                        self.experiment_ranges[0 if channel_index == 0 else 2],
                                        0)
                    assert_pico_ok(pico_channel_status)


        print("PicoScope(s) is(are) ready")
        
    async def run_one_freq(self, freq : float) -> np.ndarray:
        """
        Does the sampling for a single frequency. Is called once per frequency.
        """
        periods = find_periods(freq, self.low_freq_periods)

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
                                                        self.experiment_ranges[0 if channel_index == 0 else 2],
                                                        ctypes.c_int16(32767)))        #transforming data in buffer into readable mV data

                    freq_results[picoscope_index, channel_index] = filter_data(unfiltered_results, freq, fs)

        except Exception as exc:
            print(f"Exception in collecting and filtering data: {exc}", flush=True)
            raise(exc)
        
        return freq_results

    def pico_close(self) -> None:

        """
        Closing the unit and turning of led to indicate this
        """
        for i in range(self.num_picoscopes):
            ps.ps4000aFlashLed(self.c_handle[i],0)
            ps.ps4000aCloseUnit(self.c_handle[i])
        print(f"Closed picoscopes at {time.time()}")

    def plot(self) -> None:

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
    
    def saveData(self,
                    frequency_index : int,
                    freq            : float,
                    results         : np.ndarray,
    ) -> None:
        start_time = time.time()
        print("Start making raw data file:", flush=True)
        try:

            lst = []
            periods = find_periods(freq, self.low_freq_periods)

            time_ax = np.linspace(0,sample_time(periods, self.range_of_freqs[frequency_index]),len(results[0,0]))

            for k in range(len(time_ax)):                                                    
                lst.append(str(time_ax[k]))
                for picoscope_index in range(self.num_picoscopes):
                    for channel_index in range(4):
                        if self.channels[picoscope_index,channel_index]:
                            lst.append("\t"+str(results[picoscope_index, channel_index][k]))
                lst.append("\n")

            if os.path.exists("temp.txt"):
                os.remove("temp.txt")
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

            save_file.write("Picoscope code: \t" + picoscope_string + "\n\n")
            save_file.write("Max potential (current channel) [V]: \t" + self.save_metadata["max_potential_channel"]+ "\n")
            save_file.write("Max stack potential [V]: \t" + self.save_metadata["max_potential_stack"] + "\n")
            save_file.write("Max cell potential [V]: \t" + self.save_metadata["max_potential_cell"] + "\n\n")
            save_file.write("Cell numbers: \t" + self.save_metadata["cell_numbers"]+ "\n")
            save_file.write("Area [cm2]: \t" + self.save_metadata["area"]+ "\n")
            save_file.write("Temperature [degC]: \t" + self.save_metadata["temperature"]+ "\n")
            save_file.write("Pressure [bar]: \t" + self.save_metadata["pressure"]+ "\n")
            save_file.write("DC current [A]: \t" + self.save_metadata["DC_current"]+ "\n")
            save_file.write("AC current [in pct of DC current]: \t" + self.save_metadata["AC_current"]+ "\n")
            save_file.write("Shunt: \t" + self.save_metadata["shunt"]+ "\n\n")

            #removes ability to run without pstat, but lowkey then just run the old program?
            input_value = "N"
            save_file.write("Run without potentiostat [Y/N]: \t" + str(input_value) + "\n")
            save_file.write("Frequencies selected: \t" + self.save_metadata["selected_frequencies"]+ "\n")               
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
def sample_time(periods : float, freq : float) -> float:
    return periods/freq             #[s]

def find_timebase(freq : float) -> int:
    """
    Helper function to calculate timebase for each frequency. This is to avoid oversampling lower frequencies
    """
    if freq <= 500:
        sampling_freq_multiplier = -0.5*freq + 300
    else:
        sampling_freq_multiplier = 25

    return int(np.ceil(50000000/(sampling_freq_multiplier*freq)+ 2))

def find_periods(freq : float, low_freq_periods : float) -> float:
    if freq > 1000:
            periods = 890 + 0.111 * freq
    elif freq > 10:
            periods = freq 
    else:
        periods = low_freq_periods * freq
        
    return periods

def filter_data(data : np.ndarray, freq : float, fs : float) -> np.ndarray:
    filtered_data = data
    mean = statistics.mean(data)
    filtered_data = data - mean
    filtered_data = butter_lowpass_filter(filtered_data, [0.25*freq, 4*freq], fs, order=4)
    return filtered_data
 
def butter_lowpass_filter(data : np.ndarray,
                            cutOff : tuple[float, float],
                            fs : float,
                            order : int = 4
) -> np.ndarray:
    nyq = 0.5*fs
    normalCutoff = [cutOff[0] / nyq,  cutOff[1] /nyq]
    b, a = butter(order, normalCutoff, btype='bandpass', analog = False)
    y = lfilter(b, a, data)
    return y


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
