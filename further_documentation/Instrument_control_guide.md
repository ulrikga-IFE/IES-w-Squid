## A guide to instrument control

The overarching goal of this program is to communicate with the PicoScope 4000 series and Admiral Instruments Squidstat Cycler, and synchronize their operation. To do this, we must familiarize ourselves with their APIs. The PicoScope requires you to install the PicoSDK library and is operated by calling functions described in the documentation (PicoScope 4000 Series (A API) Programmer's Guide.pdf). For the Squidstat, the installation requires a few more steps; see README_admiralinstruments.md in this folder. Once SquidstatPyLibrary is installed, the Squidstat is controlled using an object-oriented structure with the support of QApplication (which you must also install). Documentation for this is found here: https://admiral-instruments.github.io/AdmiralSquidstatAPI/

This guide provides a concise overview of the functionality and logic used to communicate with and control each instrument in the context of this program. I recommend using this guide in conjunction with reviewing the code directly to fill gaps in the in-program documentation
_________________________________________________________________________
This guide includes:


1. Picoscope API
2. Squidstat API
3. Program structure 
4. Threading with multiple picoscopes
__________________________________________________________________________

### Picoscope API

PicoScope has arguably the easier of the two APIs, based solely on calling different functions to tell the PicoScope what to do. All the functions return only a PICO_STATUS object, which is either PICO_OK if everything is good or some custom error if there is a problem. Using assert_pico_ok, you can test every function call. Also, keep in mind that we are using a Python wrapper on a program written in C/C++, so we often have to pass c_types and pointers. For more details, refer to the documentation. Here, we will quickly go over the most important of these functions.

Some variables we see often:
>handle: Identifier for unit    
>channel: which channel this function applies to. [0,1,2,3] for [A,B,C,D] in our case.  


`ps4000aOpenUnit(*handle, *serial)`    
This function opens/starts a picoscope and assigns it a handle. In the code the picoscopes have handels starting from 16384, and `None` as the serial. * at the start of the parameter means pass by referance (pointer). Note: I am not sure why the original author chose to start at 16384. When `None` is passed it will open the first unit it can find, if you pass a serial number this function will open that spesific unit.


`ps4000aGetTimebase2(handle, timebase, noSamples, \*timeIntervalNanoseconds, \*MaxSamples, segmentIndex)`   
This function can be thought of as a test function that makes sure that the timebase you have chosen is valid and possible to preform on the unit. The `timebase` is a number indicating to the PicoScope what frequency it should sample on. `find_timebase()` will calculates what this should be based on what frequency you wish to sample. Using timebase and how long you want to sample for you can find the number of samples (`noSamples`) you are going to make. For the last three arguments we pass null pointers and 0.


`ps4000aSetDataBuffers(handle, channel, *bufferMax, *bufferMin, bufferLth, segmentIndex, mode)`     
A data buffer is a place where memory is stored temporarly. In our case in a list called buffers. This function registers that this is the place to put the data. Hence we are passing pointers (`*bufferMax` and `*bufferMin`) to tell it the adress for storing. The differance between bufferMax and bufferMin is important for downsampling, but we are not interested in that and send the same buffer-addres to both. `bufferLth` is the length of the buffer i.e. how many samples the buffer must have room for. For the last two arguments we sent 0.


`ps4000aRunBlock(handle, noOfPreTriggerSamples, noOfPostTriggerSamples, timebase, *timeIndesposedMs, segmentIndex, lpReady, pParameter)`    
This is where we tell the unit to start sampling. If we wished we could let some samples go before starting to record after a trigger. However this was not of interest in this case, so `noOfPreTriggerSamples` was set to 0, and `noOfPostTriggerSamples` was set to the number of samples we expect. `timebase` tells the unit what sampling frequency to use.  The last 4 arguments are for advanced settings we have not used. We set `None`, 0, `None`, `None`. Keep in mind that this function does not halt the program until the sampling is done. It only starts it off. 


`ps4000aIsReady(handle, *ready)`    
After starting a unit this function should be called. `*ready` is a pointer to some variable. On entry the variable is set to 0, when the picoscope has finished collecting data it will change the `ready` variable into a non-zero.

`ps4000aGetValues(handle, startIndex, *noOfSamples, downSampleRation, downSampleRatioMode, segmentIndex, *overflow)`    
This function takes the collected data and places it in the predefined buffer. Meaning we can now collect our data in the predefined list. We are interested in all samples, so `startIndex` is set to 0, `*noOfSamples` points to the number of samples, the next three arguments are 0 as we are not interested in downsampling or special memory storage, and `*overflow`is given a null pointer. If interested one could change this last bit in order to detect if an overvoltage has occured. 

`ps4000aCloseUnit(handle)`  
Finally closes the unit after a hard day at work.

____________________________________________________________________________________________________

### Squidstat API

Squidstat uses an altogether different approach than PicoScope. Like PicoScope's API, SquidstatPyLibrary is a Python wrapper, but the C/C++ version is also a wrapper on the Qt application framework. This means we need to keep QApplication running in order to manage the Squidstat. This will impact us later when parallelizing, but for now, we can keep this in the back of our minds.

The Qt framework allows us to work with *signals* in the following form:

>class.signal.connect(callable)

You can find available signals for each of the classes we will use in the documentation. The callable is any function you decide, and whenever the event specified by the signal occurs, the passed function is called. For this program, there are three main classes to keep track of: `tracker`, `handler`, and `experiment`, each with its own methods and signals. Like with the PicoScope, the methods return status/errors. Let us go through the classes one by one.

`tracker`   
This is essentially only used to find and connect to the device, and then initiate the `handler`. First thing after creating an instance of tracker is calling the method **connectToDeviceOnComPort("COM3")** where you have to manually enter the port in which the Squidstat is connected (COM3 is just my spesific case).  After that you initiate the handler like so: `handler = tracker.getInstrumentHandler("Cycler2151")` and you are done with `tracker`, unless you also want to add the signal *newDeviceConnected.connect()* which triggers when the device is connected. 

`handler`   
This class handles everything else regarding the Squidstat; everything from uploading experiment to starting and stopping. It also has some useful signals for keeping track of what the Squidstat is doing. The most important methods are:
**uploadExperimentToChannel(channel,experiment)** which uploads experiment to channel specified by `channel` (0 or 1). `experiment` is an instance of the experiment class containing all information on how the experiment should procceed. More on that later.
**startUploadedExperiment(channel)** which starts the experiment.       
Handler also has a couple useful signals:   
*experimentNewElementStarting.connect()* which triggers when a new element in the experiment starts.        
*experimentStopped.connect()* triggers when the experiment is stopped or ends.      
These are just the most important functionalities in our code as it is now, but it can be expanded with other uses of the handler class.

`experiment`    
This class is really only initiated and appended on, so it works more like a container class than anything else. What is different about this, is that what is appended on is instances of different types of spesific experiment-classes. We only use galvinostatic EIS, but here you could in theory add all the different predefined experiments that Admiral Instruments provide. The process here is initiating an instance of `AisEISGalvanostaticElement(startFrequency, endFrequency, stepsPerDecade, currentBias, currentAmplitude)`, filling out the spesification of that element, and appending in to the `experiment` class like so: `experiment.appendElement(element, repetitions)`. 


### Program structure

With an understanding of the APIs, we can delve into the structure and logic of the program. The first important point is the event loop. QApplication uses an event loop to coordinate its actions and handle the signals, and we wish to use asyncio to coordinate our operations. The first few lines are there to create one event loop for QApplication and asyncio to share. Asyncio is a Python library used for parallelization of input/output-bound tasks. It works by creating coroutines with the `async def` syntax, which can be run concurrently. Note that this is not the same as threading, but it is related

Asyncio requires you to define a `main()` function, which is then run in the predefined common event loop. Inside `main()`, we start by setting up the events `pico_ready` and `admiral_ready`. These are synchronization primitives. In other words, these variables are booleans (True/False) that tell the event loop when to wait and when to proceed. They start off as clear/False.

The next step is setting up everything related to Admiral Instruments. This includes connecting to the Squidstat, building the experiment, and uploading it to the device. The details of this process are described in the **Squidstat API** section of this document. The subsequent step is setting up the PicoScope, which is organized into the function `pico_setup()`. When this setup is complete, the `pico_ready` event is set to True.

After the initial setup, we define the concurrent tasks that will be responsible for running the experiment. It is harder to control the Squidstat, so `admiral_task()` waits for `pico_ready` to be true and then starts the experiment. `pico_task()` waits for `admiral_ready` to be set and then begins sampling at a given frequency. `admiral_ready` is set by the locally defined `new_element_signal()`, which is called by the *experimentNewElementStarting()* signal. Right after the `admiral_ready` event is set, it is cleared. It is critical that the experiment element lasts longer than the sampling period so that `pico_task()` is idle and prepared to start sampling at a new frequency when a new element starts. Schematically, you can think of it like this:

===== : operating      
------- : waiting       
pico_task()--------=======================-----------=================----------=============------->      
admiral_task()----=============================-======================-================---->     


Where every time the Squidstat changes element, the picoscope starts again with the correct sampling frequencies. The tasks are started and the program runs (hopefully) smoothly. 


### Threading with multiple picoscopes

The question of when to use asyncio and when to use threading is sometimes difficult. In this case, there is a program almost identical to the one described here, but with threading instead of asyncio (`threading_structure.py`), and for some reason beyond my understanding, it does not work. However, in the main module, several PicoScopes are threaded. The problem with this is that asyncio events are not thread-safe, which can cause trouble when implementing this into the general script. One idea is to use asyncio for managing the different PicoScopes. This way, we need not worry about our events getting mixed up.

Another solution could be threading the PicoScopes and using the asyncio `admiral_ready` event to trigger a threading event to communicate with the PicoScopes. Either way, this must be tested.