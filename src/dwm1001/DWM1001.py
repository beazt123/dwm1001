#!/usr/bin/env python

import serial
import datetime as dt
from time import sleep

class DWM1001DevBoard: 
	"""!
	This class serves as an API interface that communicates with the UWB beacon via serial communication.
	The beacon is a state machine with 3 states and low level methods are used to switch from state to state.
	Users can ignore the state transitions and use the high level methods which will abstract the state transitions for you.
    """
	def __init__(self, com_port, baud_rate = 115200):
		"""!Initialises the communication with the UWB beacon that is currently plugged in to the machine via serial. Throws an error on linux if the port is not opened by the super user.
		@param str com_port : The open port that the object can use to communicate with the beacon via serial.
 
		@returns @c DWM1001DevBoard object in shell mode
		"""
		
		##!@private
		self.si = serial.Serial(com_port, baud_rate, timeout=1)

		# Ensure that the port is open
		if not self.si.isOpen():
			self.si.open()
		self.get_ready()

	def get_ready(self):
		"""!Switches the UWB beacon from whichever state it was in to the READY state.
		@param None

		@returns @c DWM1001DevBoard object in shell mode
		"""
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
		"""!Switches to shell mode. 
		However, this function only works when the UWB beacon has just been plugged in and it is the first time the programme talks to the beacon since it is plugged in.
		@param None

		@returns @c DWM1001DevBoard object in shell mode
		"""
		self.si.write(b'\r\r')
		sleep(1) #impt to wait for 1s for this cmd to work

		# Clear away the welcome message & byte strings: b'dwm> dwm> '
		self.si.reset_input_buffer()	
		self.si.reset_input_buffer()
		return self

	def stop_data_flow(self): 
		"""!Equivalent to pressing ENTER to the terminal when the UWB is in shell mode. 
		Used to stop the previous command, especially if the previous command causes the beacon to send serial data to the computer
 		@param None
		
		@returns @c DWM1001DevBoard object in shell mode
		"""
		self.si.write(b'\r') # Stops the data flow, but input buffer will still contain the leftover data
		self.si.reset_input_buffer()		# Ensures that the input buffer is 100% cleared
		self.si.reset_input_buffer()
		return self

	def cmd(self, cmd): 
		"""!Helps to send a command to the UWB beacon via the terminal in shell mode. Only known commands are allowed. 
		Common commends are 'lep', 'lec' and 'les'. This library uses the 'lec' command which requests for location data in csv format.
		@param str cmd : A command to send to the UWB when it is in shell mode.
 
		@returns @c DWM1001DevBoard object
		"""
		ent_cmd = cmd.lower() + '\r'
		self.si.write(ent_cmd.encode('utf-8'))
		return self

	def start(self):
		"""!A high level method to kickstart the localisation process.
		Subsequently, use self.get_localisation_str() to receive the localisation data as an unprocessed string.
		
		@param None
		
		@returns @c DWM1001DevBoard object
		"""
		self.cmd("lec")
		return self

	def get_localisation_str(self):
		"""!Reads the localisation data in the buffer.
		Only works if self.start() has been used.
		Keep using this method to get updated localisation data from the beacon.
		Subsequently, you can use DWM1001DevBoard.process_localisation_str(string) to parse it into a dictionary.
 
		@param None

		@returns @c String The unprocessed localisation data
		"""
		line_byte_str = self.si.readline()
		line_str = str(line_byte_str.decode('utf-8'))
		return line_str

	@staticmethod
	def process_localisation_str(localisation_str):
		"""!Parses the localisation data into a dictionary
		The dictionary will then have the following attributes:
		- bool status: whether the beacon managed to localise successfully.
		- Anchor[] anchors: A list of anchors that the beacon chose to calculate its coordinates. Each Anchor dictionary has the following attributes:
			- str id: The BLE id of the anchor.
			- float x,y,z: The pre-set coordinates of the anchor.
			- float dist: The TWR distance, measured using UWB, between the anchor and beacon.
		- float x,y,z: The coordinates calculated by the beacon based on the TWR distance from the anchors it chose to communicate with.
		- float qf: An estimate of the quality of the localisation (0-100). The higher this number, the better.
		
		@param str localisation_str : The unprocessed localisation data


 
		@return Dict.

		"""
		dic = {}
		string = localisation_str.strip('\r\n')
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