import csv
import argparse
import os
import sys
import re
import matplotlib.pyplot as plt
from fractions import Fraction
from datetime import datetime
"""
    This script if for processing of accelerometer *.csv data produced by LORD MicroStrain's Sensor Connect
software. It takes one non-optional argument namely the sample file name for example,

    csv_processor.py sample_data.csv

    This mode simply outputs several cropped csv files around the Nth highest peaks in the file, parameters
detailing the specifics of how that triggering action works are available to be changed either via optional
arguments or in the constants block directly below this message.
"""

# constants
# ------------------------
# the x,y,z constants refer to which channel is which when you look at the device in such a way the writing on top
# is oriented correctly
X_CHANNEL = 2
Y_CHANNEL = 1
Z_CHANNEL = 3
TIME_FORMAT = "%m/%d/%y %H:%M:%S.%f"
MINUTES_ONLY = "%M:%S.%f"
SECONDS_ONLY = "%S.%f"
DEFAULT_VERBOSITY = False
DEFAULT_MAX_MODE = False
DEFAULT_PLOT_MODE = False
DEFAULT_NUM_CAPTURES = 3
DEFAULT_SAMPLE_SIZE = 300
DEFAULT_DEADZONE = DEFAULT_SAMPLE_SIZE / 4
DEFAULT_TRIGGER_AXIS = "xyz"
DEFAULT_SAMPLE_SIZE = 300
DEFAULT_LOCATION_COEFFICIENT = Fraction(1, 5)
DEFAULT_POLARITY = '+-'
DEFAULT_PLOT_TITLE = "G-Force Over Time"
PLOT_LEGEND_LOCATION = "lower left"


def printSampleData(data, lC=DEFAULT_LOCATION_COEFFICIENT):
    """
    this function takes a matrix of sample data and writes it too the screen all pretty like
    :param data: formatted data, [[time1, xVal1, yVal1, zVal1], [time2, xVal2, yVal2, ZVal2], ...]
    :param lC: the location coefficient, defined as the distance into the sample where the trigger
    is located.
    :return: No return data.
    """
    i = 0
    for time, x, y, z in data:
        outputStr = "<[{}] TIME={}, X=".format(i, time.strftime(MINUTES_ONLY)).rjust(29) + \
                    "{}, Y=".format(x).rjust(13) + \
                    "{}, Z=".format(y).rjust(13) + \
                    "{}>".format(z).rjust(10)
        if i == round(len(data) * lC): outputStr += " <---- Trigger"
        print outputStr
        i += 1


class MicroStrainData:
    """
    This class serves to encapsulate all the data and functions relating to grabbing data from a
    properly formatted csv file, finding peaks, and outputting it in a usable format.
    """
    def __init__(self, csvFilename, v=DEFAULT_VERBOSITY):
        self.__verbosity = v
        self.numCaptures = DEFAULT_NUM_CAPTURES
        self.plotMode = DEFAULT_PLOT_MODE
        self.triggerAxis = DEFAULT_TRIGGER_AXIS
        self.__AxisLst = self.__parseAxies(self.triggerAxis)
        self.sampleSize = DEFAULT_SAMPLE_SIZE
        self.locationCoefficient = DEFAULT_LOCATION_COEFFICIENT
        self.polarity = DEFAULT_POLARITY
        self.deadzone = DEFAULT_DEADZONE
        self.__originalFilename = csvFilename
        self.__sampleData = self.__parseFromFile(csvFilename)
        self.maxPeaks, self.minPeaks = self.__findMaxMinPeaks(self.__sampleData)
        self.totalNumSamples = len(self.__sampleData)
        self.sampleRate = self.__findSampleRate(self.__sampleData)

    def __repr__(self):
        """
        prints out a short text representation of the sample data
        :return:
        """
        line1 = "<{}; containing {} samples, {}.{} seconds per sample>\n".format(self.__originalFilename,
                                                                                 self.totalNumSamples,
                                                                                 self.sampleRate.seconds,
                                                                                 self.sampleRate.microseconds)
        line2 = "<xMax; {}@{}, yMax; {}@{}, zMax, {}@{}>\n".format(self.maxPeaks[0][2],
                                                                   self.maxPeaks[0][1].strftime(MINUTES_ONLY),
                                                                   self.maxPeaks[1][2],
                                                                   self.maxPeaks[1][1].strftime(MINUTES_ONLY),
                                                                   self.maxPeaks[2][2],
                                                                   self.maxPeaks[2][1].strftime(MINUTES_ONLY))
        line3 = "<xMin; {}@{}, yMin; {}@{}, zMin, {}@{}>".format(self.minPeaks[0][2],
                                                                 self.minPeaks[0][1].strftime(MINUTES_ONLY),
                                                                 self.minPeaks[1][2],
                                                                 self.minPeaks[1][1].strftime(MINUTES_ONLY),
                                                                 self.minPeaks[2][2],
                                                                 self.minPeaks[2][1].strftime(MINUTES_ONLY))
        return line1 + line2 + line3

    def sliceMax(self):
        """
        This function slices the data in self.__sampleData around the maximum peak, using the sampleSize and
        locationCoefficient values to determine slice size and location the the trigger within
        :return: a sliced down copy of self.__sampleData
        """
        self.__AxisLst = self.__parseAxies(self.triggerAxis)
        val, index = 0, 0
        for axis in self.__AxisLst:
            if "+" in self.polarity:
                if self.maxPeaks[axis][2] > val:
                    val = self.maxPeaks[axis][2]
                    index = self.maxPeaks[axis][0]
            if "-" in self.polarity:
                if abs(self.minPeaks[axis][2]) > val:
                    val = abs(self.minPeaks[axis][2])
                    index = self.minPeaks[axis][0]
        return self.__cropData(index)

    def sliceNumTriggers(self):
        """
        similar to the sliceMax method only this version allows for multiple captures
        :return: cropped version of sample data
        """
        self.__AxisLst = self.__parseAxies(self.triggerAxis)
        newLst = []
        val = []
        index = []
        deadzone = []
        for x in range(self.numCaptures):
            if self.__verbosity: print "<-> Cropping data from trigger #{}".format(x+1)
            val.append(0)
            index.append(0)
            for axis in self.__AxisLst:
                i = 0
                for row in self.__sampleData:
                    if "+" in self.polarity:
                        if row[axis+1] > val[x]:
                            if i not in deadzone:
                                val[x] = row[axis+1]
                                index[x] = i
                                deadzone.extend(range(i - self.deadzone, i + self.deadzone))
                    if "-" in self.polarity:
                        if abs(row[axis+1]) > val[x]:
                            if i not in deadzone:
                                val[x] = abs(row[axis+1])
                                index[x] = i
                                deadzone.extend(range(i - self.deadzone, i + self.deadzone))
                    i += 1
            if self.__verbosity: print "<+> Found trigger at sample #{}, value; {}".format(index[x], val[x])
        for i in index:
            newLst.append(self.__cropData(i))
        return newLst

    def __cropData(self, index):
        """
        Slices a piece of the sample data from the greater whole of samples
        :param index: the index of the peak data being looked at, note sample size and coefficient are considered
        also
        :return: the cropped data
        """
        # beginning index = positionalIndex - (size * coefficient)
        # ending index = positionalIndex + (size - (size * coefficient))
        s = self.sampleSize
        lC = self.locationCoefficient
        bI = int(index - (s * lC))
        eI = int(index + (s - (s * lC)))
        return self.__sampleData[bI:eI]

    @staticmethod
    def __parseAxies(axisStr):
        """
        takes a string containing any combination of x, y, and z and places the sample data index number into a list
        to be used by the cropping tool to identify which columns can initiate peak triggers
        :param axisStr: Any combination of x, y and z in a string
        :return: A list of 0, 1, or 2 corresponding to x, y, z
        """
        new = []
        for char in axisStr:
            if char == 'x':
                assert 1 not in new
                new.append(0)
            elif char == 'y':
                assert 2 not in new
                new.append(1)
            elif char == 'z':
                assert 3 not in new
                new.append(2)
        return new

    @staticmethod
    def __findSampleRate(data):
        """
        finds the mean sample rate over all samples
        :rtype: datetime.timedelta
        """
        return (data[-1][0] - data[0][0]) / len(data)

    @staticmethod
    def __findMaxMinPeaks(data):
        """
        Does stuff to data and returns peak data
        :param data: the parsed CSV data
        :return: maximum and minimum peak data in the following format
        [maxIndex, maxTimestamp, maxValue], [minIndex, minTimestamp, minValue]
        """
        aMax = sys.maxint
        aMin = sys.maxint * -1
        newMax = [[], [], []]
        newMin = [[], [], []]
        buffMax = [aMin, aMin, aMin]
        buffMin = [aMax, aMax, aMax]
        for row in data:
            for col in range(1, 4):
                if row[col] > buffMax[col - 1]:
                    buffMax[col - 1] = row[col]
                    newMax[col - 1] = [data.index(row), row[0], row[col]]
                if row[col] < buffMin[col - 1]:
                    buffMin[col - 1] = row[col]
                    newMin[col - 1] = [data.index(row), row[0], row[col]]
        return newMax, newMin

    def __parseFromFile(self, csvFilename):
        """
        opens the csv file, checks for valid data the parses the data into a matrix list and returns
        :param csvFilename: the name of the csv file being worked with
        :return: the matrix of data [[datetime1, x1, y1, z1], [datetime2, x2, y2, z2], ...]
        """
        if self.__verbosity: print '<-> Opening CSV file..'
        try:
            if not os.access(csvFilename, os.F_OK):
                print "<ERROR> file does not exist"
                raise OSError(csvFilename)
            if not os.access(csvFilename, os.R_OK):
                print "<ERROR> unable to read file, check permissions"
                raise OSError(csvFilename)
        except OSError:
            sys.exit(1)
        with open(csvFilename, 'rb') as csvFilename:
            if self.__verbosity: print '<+> File opened successfully'
            if self.__verbosity: print '<-> Checking validity..'
            dialect = self.__checkCsvValidity(csvFilename)
            if self.__verbosity:
                print '<+> Valid file'
                print '<-> Loading file into CSV parser..'
            self.__findDataStart(csvFilename)
            while True:
                if csvFilename.read(1) == "\n": break  # skip over the column title line
            csvReadObj = csv.reader(csvFilename, dialect)
            # convert the reader object to a linked list
            samples = []
            for row in csvReadObj:
                # the samples list is filled with the parsed csv data in this format
                #    0 = a datetime object that matches the timestamp of the csv row
                #    1 = the x axis g-force value as a floating point number object
                #    2 = the y axis in the same format
                #    3 = the z axis in the same format
                x = float(row[X_CHANNEL])
                y = float(row[Y_CHANNEL])
                z = float(row[Z_CHANNEL])
                samples.append([datetime.strptime(row[0][:24], TIME_FORMAT), x, y, z])
            if self.__verbosity: print '<+> CSV file successfully parsed'
        return samples

    @staticmethod
    def __checkCsvValidity(csvFile):
        """
        This function takes a CSV file produced by LORD corp's Sensor Connect software and checks for proper CSV
        formatting if found it returns a CSV library's dialect object
        :param csvFile: an open csv file of the right format
        :return: no return value
        """
        MicroStrainData.__findDataStart(csvFile)
        try:
            dialect = csv.Sniffer().sniff(csvFile.read(1024))
            csvFile.seek(0)
            return dialect
        except csv.Error:
            print "<ERROR> improper formatting of CSV file, Exiting."
            sys.exit(1)

    @staticmethod
    def __findDataStart(csvFile):
        """
        This function takes a CSV file produced by LORD corp's Sensor Connect software and searches for the beginning of
        raw data, this is tagged 'DATA_START', if none is found it throws the error message and exits
        :param csvFile: The current open csv file
        :return: The same file but now at the appropriate line where raw data begins
        """
        try:
            while True:
                line = csvFile.readline()
                if "" == line:
                    raise EOFError
                if 'DATA_START' in line:
                    return csvFile
        except EOFError:
            print '<ERROR> Did not find DATA_START tag in CSV file, ' + \
                  'likely it did not come from the Sensor Connect software. Exiting.'
            sys.exit(1)

    # the rest of these are just accessor functions
    def setVerbosity(self, v):
        assert type(v) == bool
        self.__verbosity = v

    def setMaxMode(self):
        self.numCaptures = 1

    def setNumCaptures(self, c):
        assert type(c) == int
        self.numCaptures = c

    def setDeadzone(self, d):
        assert type(d) == int
        self.deadzone = d

    def setPlotMode(self, p):
        assert type(p) == bool
        self.plotMode = p

    def setTriggerAxis(self, t):
        assert type(t) == str
        self.triggerAxis = t

    def setSampleSize(self, s):
        assert type(s) == int
        self.sampleSize = s

    def setPolarity(self, p):
        assert p in ["+", "-", "+-"]
        self.polarity = p

    def setLocationCoefficient(self, lc):
        assert type(lc) == Fraction
        self.locationCoefficient = lc


def main():
    # argument data
    verbose_help = "Verbose: Prints a lot more data to the screen concerning what the parser is doing"
    max_help = "Maximum mode: This mode finds the largest spike on the specified axis and truncates that " + \
               " value to the width specified."
    number_help = "Number: This specifies the number of captures the program will copy from the CSV file, " + \
                  " default value is %s.  This is the default mode." % \
                  DEFAULT_NUM_CAPTURES + \
                  " maximum mode though setting the value to 1 essentially does the same thing. "
    deadzone_help = "Dead-zone: when preforming multiple captures this value creates a dead-zone of N captures" + \
                    "both before and after the trigger. When the next highest peak is within the dead-zone it will" + \
                    "not initiate the next trigger, done to avoid all triggers within one graph, default is {}," + \
                    "usually 1/4 of sample size.".format(DEFAULT_DEADZONE)
    axis_help = "Axis: This is where to specify the axis or axises that will initiate triggering " + \
                " default is to use all axises(xyz)."
    axis_choices = ["x", "y", "z", "xy", "xz", "yz", "xyz"]
    plot_help = "Plot: When this mode is active a plot is drawn to the screen after file processing"
    title_help = 'Title: Allows for changing of the plot title, make sure to put the new title in quotation ' + \
                 'marks, "title"'
    printout_help = "Printout: This mode outputs sample data to the screen as it is being parsed"
    size_help = "Sample Size: the number of samples to include in each truncated export file. Default is %d." % \
                DEFAULT_SAMPLE_SIZE
    polarity_help = "Polarity: Sets triggering to activate on positive spike, negative spike, or both. " + \
                    " Default is %s" % DEFAULT_POLARITY
    coefficient_help = "Location Coefficient: This a fraction that details how far into the cropped sample the " + \
                       "detected peak should be, default is %s" % DEFAULT_LOCATION_COEFFICIENT
    file_help = "File: the absolute path of the CSV file being parsed\n"
    output_help = "Output: specify the name of an output file, the default is the input filename appended " + \
                  " with a '_trunc.csv' at the end. specified output files need to end with a .csv also if " + \
                  " creating multiple output files they will be numbered regardless of whether the user " + \
                  " specifies a new file or not. Example; sample.csv >> sample_trunc1.csv"

    # argument parsing section, setup and execution
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help=verbose_help)
    parser.add_argument("-m", "--maximum", action="store_true", help=max_help)
    parser.add_argument("-n", "--number", type=int, default=DEFAULT_NUM_CAPTURES, help=number_help)
    parser.add_argument("-d", "--deadzone", type=int, default=DEFAULT_DEADZONE, help=deadzone_help)
    parser.add_argument("-p", "--plot", action="store_true", help=plot_help)
    parser.add_argument("-t", "--title", type=str, help=title_help)
    parser.add_argument("-po", "--printout", action="store_true", help=printout_help)
    parser.add_argument("-a", "--axis", type=str, choices=axis_choices, default=DEFAULT_TRIGGER_AXIS,
                        help=axis_help)
    parser.add_argument("-s", "--size", type=int, default=DEFAULT_SAMPLE_SIZE, help=size_help)
    parser.add_argument("-pol", "--polarity", type=str, choices=["+", "-", "+-"],
                        default=DEFAULT_POLARITY, help=polarity_help)
    parser.add_argument("-c", "--coefficient", type=Fraction, default=DEFAULT_LOCATION_COEFFICIENT,
                        help=coefficient_help)
    parser.add_argument("-o", "--output", type=str, help=output_help)
    parser.add_argument("filename", type=str, help=file_help)
    args = parser.parse_args()

    verbose = args.verbose if args.verbose != DEFAULT_VERBOSITY else DEFAULT_VERBOSITY

    # Handle the above data via our new class
    msd = MicroStrainData(args.filename, v=verbose)
    if args.maximum: msd.setMaxMode()
    if args.number != DEFAULT_NUM_CAPTURES: msd.setNumCaptures(args.number)
    if args.plot != DEFAULT_PLOT_MODE: msd.setPlotMode(args.plot)
    if args.axis != DEFAULT_TRIGGER_AXIS: msd.setTriggerAxis(args.axis)
    if args.size != DEFAULT_SAMPLE_SIZE: msd.setSampleSize(args.size)
    if args.deadzone != DEFAULT_DEADZONE: msd.setDeadzone(args.deadzone)
    if args.polarity != DEFAULT_POLARITY: msd.setPolarity(args.polarity)
    if args.coefficient != DEFAULT_LOCATION_COEFFICIENT: msd.setLocationCoefficient(args.coefficient)

    if verbose:
        print ""
        print msd
        print ""

    if msd.numCaptures == 1 or args.maximum:  # maximum mode
        postCroppedSamples = [[]]
        postCroppedSamples[0] = msd.sliceMax()

        if args.printout: printSampleData(postCroppedSamples[0])

        if verbose: print "<-> Saving data.."
        filenameRe = re.compile(r"(.*)\.csv")
        matchRe = filenameRe.match(args.filename)
        outputFilename = matchRe.group(1) + "_trunc.csv" if not args.output else args.output
        if outputFilename[-4:] != ".csv":
            outputFilename += ".csv"
        print "<-> Saving data to {}".format(outputFilename)
        with open(outputFilename, 'wb') as outputFile:
            outputWriter = csv.writer(outputFile)
            for row in postCroppedSamples[0]:
                time = row[0].strftime(TIME_FORMAT)
                outputWriter.writerow([time, row[1], row[2], row[3]])
        print "<+> Data saved!"

    else:  # number mode
        postCroppedSamples = msd.sliceNumTriggers()
        if args.printout:
            for capture in postCroppedSamples:
                print ""
                print "Capture number {}:".format(postCroppedSamples.index(capture) + 1)
                print "-" * 60
                printSampleData(capture, lC=msd.locationCoefficient)
                print ""
        if verbose: print "<-> Saving data.."
        for capture in postCroppedSamples:
            filenameRe = re.compile(r"(.*)\.csv")
            if not args.output:
                matchRe = filenameRe.match(args.filename)
                outputFilename = matchRe.group(1) + "_trunc{}.csv".format(postCroppedSamples.index(capture) + 1)
            else:
                outputFilename = args.output if args.output[-4:] != ".csv" else args.output[:-4]
                outputFilename += "{}.csv".format(postCroppedSamples.index(capture) + 1)
            print "<-> Saving data to {}".format(outputFilename)
            with open(outputFilename, 'wb') as outputFile:
                outputWriter = csv.writer(outputFile)
                for row in postCroppedSamples[0]:
                    time = row[0].strftime(TIME_FORMAT)
                    outputWriter.writerow([time, row[1], row[2], row[3]])
            print "<+> Data saved!"

    if msd.plotMode:
        for data in postCroppedSamples:
            print "<+> Drawing plot number {}, Exit plot window to view the next.."\
                .format(postCroppedSamples.index(data) + 1)
            rotatedData = [[time.strftime(SECONDS_ONLY), x, y, z] for time, x, y, z in data]
            rotatedData = zip(*rotatedData)
            if "x" in msd.triggerAxis: plt.plot(rotatedData[0], rotatedData[1], 'b-', label="x")
            if "y" in msd.triggerAxis: plt.plot(rotatedData[0], rotatedData[2], 'g-', label="y")
            if "z" in msd.triggerAxis: plt.plot(rotatedData[0], rotatedData[3], 'r-', label="z")
            plt.legend(loc=PLOT_LEGEND_LOCATION)
            if len(postCroppedSamples) > 1: plotNum = postCroppedSamples.index(data) + 1
            else: plotNum = ""
            plt.title(args.title + " " + str(plotNum)) if args.title\
                else plt.title(args.filename) + "" + str(plotNum)
            plt.ylabel("G-Force")
            plt.xlabel("Timestamp (Shows only seconds & microseconds)")
            plt.show()

    print "<!> Processing complete, Exiting"


if __name__ == "__main__": main()
