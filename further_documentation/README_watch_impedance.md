####	Watch impedance	####

Short description:
The main function of the script is to process and watch a folder of time sampled voltage 
and current data on the format from the picoscope (shown later) and convert it to a 
impedance spectra, via the fourier transform of the time signal. The program has an
interface with differnt options to control how this is done. There are also additional
features for doing a single file. The running results are displayed in three figures
a nyquist plot, a bode plot and a fft spectrum plot. 



Input parameters:
The input parameters are
- Time index: The column of the time data in the input files (zero indexed)
- Voltage index: The column/columns of the voltage date in the input file (zero indexed)
	If svereal numbers are writen with "," as a seporator between all these columns
	will be processed and the saved files will be tagged with "v_{index}" to 
	distinguish the different files.
- Current index: The column of the current data in the input files (zero indexed)
Note: All the indexes shold be integers and the input field should only contain that 
      number, else the program will fail.

- Voltage proportion: The proportion of the maximum voltage FFT signal a peak has
	to exceed to be a valid peak.
- Current proportion: The proportion of the maximum current FFT signal a peak has
	to exceed to be a valid peak.
Note: The proporitons are given as decimal numbers, i.e. 0.5 would corespond to
	a peak having to be more than 50% of the largest peak. The numbers are
	interperted as float and should have "." as decimal point and contain
	only numbers otherwise.

- Current correction: A way to correct the current signal if either a 
	psuedo current measurment has been done or the size is otherwise off.
	The whole current time sample will be divided by that number, which is 
	equivalent to setting the value to the resistance of the measurement.
Note: This as with the proportions are interperted as floats and should use "."
	as decimal point and else only contian numbers.



Input files:
The choosen input files should be on the format
	
Time	Voltage1 Current Voltage2 ...
unit	unit	 unit	 unit	  ...
				  (blank line)
number	number	 number	 number	  ...
number	number	 number	 number	  ...
...

When reading these files the second row is used to see if the unit is in milli 
instead of no prefix. And if the unit contain a "m" it will be multiplied with 10^(-3)
so that all units have no prefixes. Then the date is taken from the fourth row an until
the end of the file, here the numbers shoul be floats with "." as decimal point. The
indicies from the paramameters here corespond to the columns. In this case the Time index
is 0, index of Voltage1 is 1, index of Voltage2 is 3 and index of Current is 2. Thus if 
both voltage signals should be calculated the Voltage index inbox contain "1,3".


Save file:
The resulting calculated impedance are saved as a MMFILE that has the format

Frequency	Real	Imaginary
number		number	number
number		number	number
...

If only one column is specified in the Voltage index inbox the saved file will have the
same name and be stored in the choosen save folder. If multiple indicies are specifies
the filename will have an added "v_{voltage_index}" so that the names can be
distinguished. In addition if the filename contains a "_" and multiple indicies are
specified, the addon will be placed before the last "_" since the number after the last
"_" is used for sorting the files in the folder_fitting.py program.  


Calculations:
The voltage and current time signals are converted to the frequency domain via the RFFT
method from numpy. The RFFT method is used since the input is real and we are not 
interested in the negativ frequencies, thus this is faster than the normal FFT method.
When the FFT are calculated the first two frequency components are set to zero. This 
means that the constant term and the term coresponding to the smallest detecteable 
frequencies are removed. The smallest decectable frequency is given by 1/sampling time.
This then restricts the frequencies on uses to twice this smallest frequency. When the
RFFT's are found the scipy method find_peaks, searches for the peaks of each of the two
RFFT's seperatly. Here a peaks has to be higher than the max peak amplitude multiplied 
by the proportion factor to be valid. Then the intersection of the two sets of peaks is 
found and used as the final peaks of the RFFT's. Then the impedance is found by dividing
the voltage at the peaks by the current at the peaks. If the peak finding is not good
enough one can add additional elements to the find_peak method for a better search. 


Figures:
The three figures are
- Nyquist plot: Shows the impedance as a scatter plot. The dots are the found impedances
	and there color are coded after the logarithm of there coresponding frequency.
	The same colorcoding is in the other figures aswell. (Figure to the left)

- Bode plot: Show the absolute size of the impedance and the angle of the impedance as
	a function of the frequency. The colorcoding is the same as in the nyquist plot.
	(Figure in the middel)

- FFT spectrum: Show the two fft spectrums for the voltage and the current. The dots 
	represent the intersection of the found peaks and have the same colorcoding as
	the nyquist figure. The red crosses are the found peaks for the coresponding
	transformation. 

Interface:
The code runs by a call to the Interface classes constructor (__init__). This class
handels the logistics of the interface and the different inputs and outputs. This 
class uses the eis_sample.py file's EIS_Sample class to do the calculaton of impedance 
and the saving and plotting of the result. For simple change of the 

The watch part:
The file watching is done by the watchdog object. This is searches the input file path
for created files and when one is decected it calls the on_created method, which is
the created method from the interface class, but with the save path specified from the
time the object was instantiated. 


Dependancies:
- GUI (own made)
- eis_sample (own made)
- matplotlib
- numpy
- os
- tkinter
- typing(Iterable)
- shutil(rmtree)
- watchdog
- time
- scipy











