LXRS_csv_file_processor.py

	This script is for processing of accelerometer data that LORD MicroStrain's SensorConnect software creates. 
    Providing it is in *.csv format and contains 3 channels (axies), I'm also using the v5.0.0 version of 
    SensorConnect, so if for some reason the parsing action of this is broken it is likely to be caused by a
    rewrite of the CSV file format on SensorConnect's side.

	To use this software you need Python, 2.7. I'm using 2.7.12 but any 2.7 will likely work. It can be found 
    here,

https://www.python.org/downloads/release/python-2712/

	Then once Python is installed open the .\Scripts folder of the python directory. Typically at,

C:\Python27\Scripts

	And run the command,
	
pip.exe install matplotlib

	Once this is completed the script should be ready to run.
	
LXRS_csv_file_processor.py --help
	or
LXRS_csv_file_processor.py -h

	Will show all the command line arguments needed to change the processing parameters. They can also be
    changed in the defaults section in the top of the script to avoid having to type them in every time.
