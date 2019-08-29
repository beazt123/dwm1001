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


def serial_ports(): #returns a list of com ports on the system(Windows, linux and darwin) otherwise raises environment Error
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

#   ['/dev/ttyACM0' , '/dev/ttyACM1']



# TODO: UWB doesnt stop reporting lec coordinates after sometime and the state is unable to change to 'idle' once that happens. The only way to get it back is to enter another cmd.
# to stop the data flow in another way.
class DWM1001DevBoard: 
	def __init__(self, com_port, baud_rate = 115200,state = 'start'):
		
		# 'Just-plugged-in' state
		self.si = serial.Serial(com_port, baud_rate, timeout=1)
		self._state = state
		# Ensure that the port is open
		if not self.si.isOpen():
			self.si.open()
		# Check if the data in flow is occuring by taking the input buffer at 2 points in time
		self.get_ready()
	
	def get_ready(self):
		x = self.si.in_waiting
		sleep(1)
		y = self.si.in_waiting
		if y > x: # if it detects incoming data, which shouldn't be the case, it shows that the previous program left it in the 'data in-flow' state
			self._state = 'data flowing in'
			self.stop_data_flow()
			print('Previous program started data in-flow. Now, data flow has been stopped.\nUWB state: ready')
			self._state = 'ready'

		elif x == 0 and y == 0: #if no data is received, means this is in the 'ready' state or it is the 1st time the device is plugged into the computer. Normal proceudres of switching to serial mode apply
			self.switch_to_serial()
			print('No data/data in-flow detected in input buffer.\nUWB state: ready')
			self._state = 'ready'

		elif x == y and x != 0 and y != 0: # To handle single data transmissions in future versions
			print('UWB in "ready" state, but some data is detected in the input buffer')
			self.stop_data_flow()
			print('Tried eliminating the data in the buffer')

		else:
			print('new state detected!') 	# I should have covered all possible states, but leaving an opening to discover more
	# Commands that can be used in any state:

		# Enter a string command thru the API into the serial command line
	def cmd(self, cmd): 
		ent_cmd = cmd.lower() + '\r'
		self.si.write(ent_cmd.encode('utf-8'))
		sleep(0.2)
		if cmd == 'les' or cmd == 'lec' or cmd == 'lep':
			self._state = 'data flowing in'

		# Resets the cmd line interface & clear input buffer
	def reset(self): 
		self.si.write(b'reset\r')
		sleep(1)
		self._state = 'start'

		# Read serial input(to the computer) while it is in the 'continuous data inflow' state.
		# Use after commands like 'lec', 'lep', 'les'
	def readline(self): # Provided by PySerial serial.Serial().readline()
		if self._state != 'data flowing in':
			print('no data is flowing in. Reading leftover data in the input buffer.\nUWB state: ' + self._state)
		else:
			print('detected data flowing in. Reading the 1st line.\nUWB state: ' + self._state)
		a = self.si.readline()
		return a
		
		
	# 'Reset' State commands:
	def switch_to_serial(self):	
		# welcome msg will pop up in putty
		if self._state == 'start':
			self.si.write(b'\r\r')
			sleep(1) #impt to wait for 1s for this cmd to work

			# Clear away the welcome message & byte strings: b'dwm> dwm> '
			self.si.reset_input_buffer()	
			self.si.reset_input_buffer()
			self._state = 'ready'
		else:
			print('Tag object is either in "ready" state or has data flowing in.\nUWB state: ' + self._state)
		
		# Done thrice to confirm the input buffer is empty. 
		# Bcoz the total no. of bytes that cn be queued is 4351 but
		# the self.si.in_waiting getter can only see 4096 so it takes
		# 2 reset_input_buffer() to completely clear the input buffer
	
	


	# 'data flowing in' state commands:

		# Stops the perpetual data flow to ready the command line for the next command
	def stop_data_flow(self): 
		if self._state == 'data flowing in':
			self.si.write(b'\r') # Stops the data flow, but input buffer will still contain the leftover data
			self.si.reset_input_buffer()		# Ensures that the input buffer is 100% cleared
			self.si.reset_input_buffer()
			self.si.reset_input_buffer()
			self._state = 'ready'

		else:
			print('data flow already stopped')

		# Before reading any serial inputs, discard the first X readings as they contain unwanted characters
	def trim_unwanted_data(self,num_of_lines):
		if self._state == 'data flowing in':
			for i in range(num_of_lines):
				self.si.readline()
			
		else:
			print('No inward flowing data to trim. Enter commands "lec", "les" or "lep" to get the POS and/or DIST')


	# Debugging tools:

		# Prints whatever is left in the input buffer
	def show_input_buffer(self):
		a = self.si.read(self.si.in_waiting)
		print(a.decode('utf-8'))

		# Shows the number of bytes in the input buffer
	def in_waiting(self): #Provided by PySerial serial.Serial().in_waiting
		print(self.si.in_waiting)

		# Runs a serial test to check what the state of the UWB is(low level check)
	def check_state(self):
		x = self.si.in_waiting
		sleep(1)
		y = self.si.in_waiting
		if y > x: # if it detects incoming data, which shouldn't be the case, it shows that the previous program left it in the 'data in-flow' state
			return 'data flowing in'

		elif x == 0 and y == 0: #if no data is received, means this is in the 'ready' state or it is the 1st time the device is plugged into the computer. Normal proceudres of switching to serial mode apply
			return 'ready'
		
		elif x == y and x != 0 and y != 0:
			return 'ready but input buffer not clear'
	
		# A high level check on the state of the uwb.
	def get_state(self):
		return self._state


	# Localisation functions
		# Use only when 'lec' command is written to the UWB device to process the data that the UWB sends over there after
	def truncate_lec_data(self,bstring):
	# Truncate away the irrelevant parts, convert the bString into a list
		if self._state == 'data flowing in':
			record2 = []
			ln_strip = bstring.strip(b'\r\n')		#   DIST,3,AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56
			single_record = ln_strip.split(b',')	# ['DIST','3','AN0','582A','0.00','0.80','0.00','0.46','AN1','5AA5','0.00','0.00','0.00','0.77','AN2','95A7','0.80','0.00','0.00','0.92','POS','0.26','0.60','0.36','56']
			record = single_record[2:]				# 			 ['AN0','582A','0.00','0.80','0.00','0.46','AN1','5AA5','0.00','0.00','0.00','0.77','AN2','95A7','0.80','0.00','0.00','0.92','POS','0.26','0.60','0.36','56']
			for element in record:
				try:
					record2.append(float(element))
				except ValueError:
					record2.append(str(element.decode('utf-8'))) #['AN0','582A',0.00,0.80,0.00,0.46,'AN1','5AA5',0.00,0.00,0.00,0.77,'AN2','95A7',0.80,0.00,0.00,0.92,'POS',0.26,0.60,0.36,56]
			return record2	# Returns [''] if the byte string is b'\r\n'
		else:
			print('"lec" data unavailable to truncate. Please use tag_obj.cmd("lec") to obtain localisation data')

		# Converts an output list from truncate_lec_data into a dictionary
	# TODO: change back the dic[ls[1]] = ls[5]   																#Temporary chnage!
	def process_lec_data(self,ls): 
		timestamp = dt.datetime.now()
		dic = {'date':timestamp.strftime("%d/%m/%y"),'time':timestamp.strftime("%H:%M")}
		if ls == ['']: # If no anchor communicates with the tag
			dic['localisation status'] = False
			print('0 tag')
			
		elif len(ls) == 6: # If only 1 anchor managed to talk to the tag
			dic[str(ls[:5])] = ls[5]   																#Temporary chnage!
			dic['localisation status'] = False
			print('1 tag')
			
		elif len(ls) == 12: # If only 2 anchors managed to talk to the tag
			print('2 tag')
			an0 = ls[0:6]
			an1 = ls[6:]
			dic[str(an0[:5])] = an0[5]
			dic[str(an1[:5])] = an1[5]
			
			dic['localisation status'] = False
			
		elif len(ls) == 23: # If 3 anchors managed to talk to the tag
			print('3 tag')
			an0 = ls[0:6]	# i.e. [AN0,582A,0.00,0.80,0.00,0.46,	AN1,5AA5,0.00,0.00,0.00,0.77,	AN2,95A7,0.80,0.00,0.00,0.92,	POS,0.26,0.60,0.36,56]
			an1 = ls[6:12]
			an2 = ls[12:18]
			pos = ls[19:23]
			dic[str(an0[:5])] = an0[5]
			dic[str(an1[:5])] = an1[5]
			dic[str(an2[:5])] = an2[5]
			dic['X coord'] = pos[0]
			dic['Y coord'] = pos[1]
			dic['Z coord'] = pos[2]
			dic['QF'] = pos[3]
			dic['localisation status'] = True
			
		elif len(ls) == 29: 	# If 4 anchors managed to talk to the tag
			print('4 tag')
			an0 = ls[0:6]
			an1 = ls[6:12]
			an2 = ls[12:18]
			an3 = ls[18:24]
			pos = ls[25:29]
			
			dic[str(an0[:5])] = an0[5]
			dic[str(an1[:5])] = an1[5]
			dic[str(an2[:5])] = an2[5]
			dic[str(an3[:5])] = an3[5]
			
			dic['X coord'] = pos[0]
			dic['Y coord'] = pos[1]
			dic['Z coord'] = pos[2]
			dic['QF'] = pos[3]
			
			dic['localisation status'] = True
		return dic
	
	
	# High level functions:
	
		# Use after inputting th 'lec' command. Can be used recursively for each line of data
	def read_localisation_data(self):
		line = self.readline()					#  b'DIST,3,AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56\r\n'
		record = self.truncate_lec_data(line)			#  [AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56]
		record_line = self.process_lec_data(record)		# {(AN0,582A,0.00,0.80,0.00):0.46,(AN1,5AA5,0.00,0.00,0.00):0.77,(AN2,95A7,0.80,0.00,0.00):0.92,'X coord':0.26,'Y coord':0.60,'Z coord':0.36,'QF':56}
		return record_line
		
		
		# Use immediately after initialisation. UWB will collect x sets of data & return it as a list of dictionaries
		# Use only when 'ready'
		# Same start state and end state. Will leave the UWB in ready state for the next command
	def log_tag_coords(self,num_pts = 1,data_to_trim = 3):
		if self._state == 'ready':
			self.cmd('lec')
			self.trim_unwanted_data(data_to_trim)
			raw_data = []
			for i in range(num_pts):
				line = self.readline()						#  b'DIST,3,AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56\r\n'
				record = self.truncate_lec_data(line)				#  [AN0,582A,0.00,0.80,0.00,0.46,AN1,5AA5,0.00,0.00,0.00,0.77,AN2,95A7,0.80,0.00,0.00,0.92,POS,0.26,0.60,0.36,56]
				record_line = self.process_lec_data(record)			# {'AN0':0.46,'AN1':0.77,'AN2':0.92,'X coord':0.26,'Y coord':0.60,'Z coord':0.36,'QF':56}
				raw_data.append(record_line)
			self.stop_data_flow()
			return raw_data
		else:
			print('UWB not ready to log data. Current UWB state: ' + self._state)

	

	





class DWM1001DevBoardStimulator(DWM1001DevBoard):
	def __init__(self,x,y,z,qf,state = 'ready'):
		timestamp = dt.datetime.now()
		self._state = state
		self._read_localisation_data_response = {'localisation status':True,'date':timestamp.strftime("%d/%m/%y"),'time':timestamp.strftime("%H:%M"),('AN0','582A',0.00,8,0.00):0,('AN1','5AA5',0.00,0.00,0.00):0,('AN2','95A7',8,0.00,0.00):0,'X coord':x,'Y coord':y,'Z coord':z,'QF':qf}
		self._read_localisation_data_failure = {'localisation status':False,'date':timestamp.strftime("%d/%m/%y"),'time':timestamp.strftime("%H:%M"),('AN0','582A',0.00,8,0.00):0,('AN1','5AA5',0.00,0.00,0.00):0}


	def cmd(self, cmd):						 # ready --> data flowing in
		if cmd == 'les' or cmd == 'lec' or cmd == 'lep':
			self._state = 'data flowing in'
		else:
			pass

	def reset(self):						 					# any state--> start
		self._state = 'start'
	
	def stop_data_flow(self): 
		if self._state == 'data flowing in':
			self._state = 'ready'
		else:
			print('There is no data flow detected') 			  # data flowing in --> ready

	def switch_to_serial(self):				 # any --> Ready
		self._state = 'ready'
	
	def read_localisation_data(self,success=True):		 # data flowing in
		if self._state == 'data flowing in':
			if success:
				return self._read_localisation_data_response
			elif not success:
				return self._read_localisation_data_failure
		else:
			print("there is no localisation data")
	
	def log_tag_coords(self,num_pts = 1):	 # Ready --> ready
		if self._state == 'ready':
			return num_pts*[self._read_localisation_data_response]
		else:
			print('UWB not ready to log data. Current UWB state: ' + self._state)
	def get_state(self):
		return self._state

	def check_state(self):
		return self._state
	def trim_unwanted_data(self,num_of_lines=0):
		pass

	def readline(self): 
		print("This function is not supported by this stimulator")
	
	def show_input_buffer(self):
		print("This function is not supported by this stimulator")

		# Shows the number of bytes in the input buffer
	def in_waiting(self):
		print("This function is not supported by this stimulator")
	
	
		

		

# Testing code for a single tag
if __name__ == "__main__":
	tag_port = serial_ports()[0]
	num_data_pts = 30

	# Initialise the tag object 		
	tag = DWM1001DevBoard(tag_port)
	print('Tag initialised')
	print(tag.check_state())			# UWB state: 'ready'
	# Start the data collection			
	print('Starting data collection')
	tag.cmd('lec')						# Show POS, and DIST, in csv. Data will flow in perpetually until uwb is plugged out
										# Alternatively, one can use 'lep' or 'les' to show just position or POS & DIST in human readable form respectively
	
	print('Current UWB state: ',tag.check_state())			# UWB state: data flowing in

	# Prepare for data collection		
	tag.trim_unwanted_data(5) 			# Trim the first 5 lines worth of data in case they contain unwanted characters, i.e. 'dwm>> \r\n'. 
	print('data trimmed')				# Normally 3 lines would be sufficient. 5 lines for good measure
	
	print(tag.check_state())			# UWB state: data flowing in
	# Start the data collection			
		# Prepare the data structures

	for i in range(num_data_pts):		# Collects data pts 30 times and prints them to the screen
		single_line = tag.readline()
		print(single_line)
	
	tag.stop_data_flow()
	print('Stopped data flow')
	print(tag.check_state())			# UWB state: 'ready'
	print('done!')