#!/usr/bin/env python

'''
Ensure that the com port is an absolute working directory.
The UWB is a state machine. It maintains the last state left by the previous program.
The __init__ standardises the  program to start form the 'ready' state.
Do ensure to stop the data flow manually otherwise the program will only work alternately.

Possible states:
- Reset: When the UWB is plugged in the first time/is manually reset by code or by presing the button
- 'ready': when no data in flowing in but the UWB is online
- Data flowing in - when the UWB is continuously sending in data waiting for a keyboard interrupt
'''
import serial
import random
import sys
import glob
import datetime as dt
from time import sleep


def list_devices(): #returns a list of com ports on the system(Windows, linux and darwin) otherwise raises environment Error
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result # in the form of a list


class DWM1001DevBoard: 
	def __init__(self, com_port, baud_rate = 115200):
		
		# 'Just-plugged-in' state
		self.si = serial.Serial(com_port, baud_rate, timeout=1)
		# Ensure that the port is open
		if not self.si.isOpen():
			self.si.open()
		self.get_ready()

	def get_ready(self):
		x = self.si.in_waiting
		sleep(1)
		y = self.si.in_waiting
		if y > x: # if it detects incoming data, which shouldn't be the case, it shows that the previous program left it in the 'data in-flow' state
			self.stop_data_flow()

		elif x == 0 and y == 0: #if no data is received, means this is in the 'ready' state or it is the 1st time the device is plugged into the computer. Normal proceudres of switching to serial mode apply
			self.switch_to_serial()

		elif x == y and x != 0 and y != 0: # To handle single data transmissions in future versions
			self.stop_data_flow()

		return self

	def switch_to_serial(self):	
		self.si.write(b'\r\r')
		sleep(1) #impt to wait for 1s for this cmd to work

		# Clear away the welcome message & byte strings: b'dwm> dwm> '
		self.si.reset_input_buffer()	
		self.si.reset_input_buffer()
		return self

	def stop_data_flow(self): 
		self.si.write(b'\r') # Stops the data flow, but input buffer will still contain the leftover data
		self.si.reset_input_buffer()		# Ensures that the input buffer is 100% cleared
		self.si.reset_input_buffer()
		return self

	def cmd(self, cmd): 
		ent_cmd = cmd.lower() + '\r'
		self.si.write(ent_cmd.encode('utf-8'))
		return self

	def start(self):
		self.cmd("lec")

	def localize(self):
		line = self.si.readline()
		return line

	@staticmethod
	def process_data(bstring):
	# Truncate away the irrelevant parts, convert the bString into a list
		record2 = []
		ln_strip = bstring.strip(b'\r\n')		#   DIST,3,AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56
		single_record = ln_strip.split(b',')	# ['DIST','3','AN0','582A','0.00','0.80','0.00','0.46','AN1','5AA5','0.00','0.00','0.00','0.77','AN2','95A7','0.80','0.00','0.00','0.92','POS','0.26','0.60','0.36','56']
		record = single_record[1:]				# 			 ['AN0','582A','0.00','0.80','0.00','0.46','AN1','5AA5','0.00','0.00','0.00','0.77','AN2','95A7','0.80','0.00','0.00','0.92','POS','0.26','0.60','0.36','56']
		for element in record:
			try:
				record2.append(float(element))
			except ValueError:
				record2.append(str(element.decode('utf-8'))) #['AN0','582A',0.00,0.80,0.00,0.46,'AN1','5AA5',0.00,0.00,0.00,0.77,'AN2','95A7',0.80,0.00,0.00,0.92,'POS',0.26,0.60,0.36,56]
		
		ls = record2
		dic = {}
		if ls != []:
			truncated_list = ls[1:]

			# Check if the localisation happened
			if truncated_list[-5] == "POS":
				dic['x'] = truncated_list[-4]
				dic['y'] = truncated_list[-3]
				dic['z'] = truncated_list[-2]
				dic['qf'] = truncated_list[-1]
				dic['status'] = True
				return dic
			
		dic['status'] = False
		return dic

	@staticmethod
	def process_str(bstring):
		dic = {}
		string = str(bstring.decode('utf-8')).strip('\r\n')
		string_csv = string.split(',')[1:]
		if string_csv == []:
			dic['status'] = False
			return dic

		numAnchors = int(string_csv.pop(0))
		anchors = []
		for i in range(numAnchors):
			anchor = {}
			anchorData = string_csv[6*i:6*i+6]
			anchorID = anchorData[1]
			anchorX = float(anchorData[2])
			anchorY = float(anchorData[3])
			anchorZ = float(anchorData[4])
			anchorDist = float(anchorData[5])

			anchor["id"] = anchorID
			anchor["x"] = anchorX
			anchor["y"] = anchorY
			anchor["z"] = anchorZ
			anchor["dist"] = anchorDist
			anchors.append(anchor)

		dic["anchors"] = anchors

		if string_csv[-5] == "POS":
			dic['x'] = float(string_csv[-4])
			dic['y'] = float(string_csv[-3])
			dic['z'] = float(string_csv[-2])
			dic['qf'] = float(string_csv[-1])
			dic['status'] = True
			return dic

		dic['status'] = False
		return dic

'''
dict
	anchors[]
		str id
		float x
		float y
		float z
		float dist
	status
'''

if __name__ == '__main__':
	print(list_devices())