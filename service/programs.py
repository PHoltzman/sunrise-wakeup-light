from time import sleep
import multiprocessing
from Queue import Empty, Full
import random

import rpi_ws281x as rpi

class ProgramList(object):
	valid_programs = ["wakeup", "wakeup_demo", "single_color", "changing_color", "blackout", "sleepy_time"]
	current_program_filename = 'current_program.txt'

class ColorObject(object):
	'''Object for defining RGB color'''
	def __init__(self, r, g, b):
		self.r = r
		self.g = g
		self.b = b
		
class ProgramTask(object):
	'''Object for defining a program to run'''
	def __init__(self, program, arg_dict=None):
		self.program = program
		
		if arg_dict is None:
			self.arg_dict = {}
		else:
			self.arg_dict = arg_dict

class BaseProgram(multiprocessing.Process):
	
	def __init__(self, logger, queue, num_pixels):
		'''
		Initialize a program
		
		Arguments:
			stop_event (multiprocessing.Event) - event for this subprocess being notified that it should cleanup and exit
		'''
		super(BaseProgram, self).__init__()
		self.daemon = True
		
		self.logger = logger
		self.queue = queue
		self.num_pixels = num_pixels
		
		# used for wakeup program and changing_color program
		self.base_multiplier = 60
		
		self._set_current_program("None")
		
		self.strip = rpi.PixelStrip(self.num_pixels, 10)
		self.strip.begin()
	
	def _exit_gracefully(self):
		'''Exit the subprocess when instructed. Should only be called if the whole service is coming down.'''
		self.strip._cleanup()
		self._set_current_program("None")
		
	def _set_current_program(self, program):
		self.current_program = program
		with open(ProgramList.current_program_filename, 'w') as f:
			f.write(self.current_program)
		
	def _send_data(self, data):
		'''
		Send a data packet to the pixels.
		
		Arguments:
			data (list[ColorObject]) - list of color objects to be transmitted to pixels
		'''
		for i in range(0,len(data)):
			# note the ordering of RBG in the mapping. Not sure how to make the library do that for me in the PixelStrip function
			self.strip.setPixelColorRGB(i,data[i].r, data[i].b, data[i].g)
		
		self.strip.show()
		
	def _check_for_task(self):
		'''Returns boolean indicating if new task was found on the queue'''
		try:
			task = self.queue.get_nowait()
			self.queue.task_done()
			self.queue.put_nowait(task)
			self.logger.info('Detected new task on queue')
			return True

		except Empty:
			return False
	
	
	def run(self):
		while True:
			try:
				next_task = self.queue.get_nowait()
				self.queue.task_done()
			
				if next_task.program == 'KILL':
					# Received kill task so exit
					self.logger.info('Received shutdown command so exiting this process.')
					self.quit_blackout()
					self._exit_gracefully()
					break
					
				elif next_task.program == 'blackout':
					self.blackout()
					
				elif next_task.program == 'single_color':
					self.single_color(**next_task.arg_dict)
					
				elif next_task.program == 'changing_color':
					self.changing_color(**next_task.arg_dict)
					
				elif next_task.program == 'sleepy_time':
					exited_normally = self.sleepy_time(**next_task.arg_dict)
					
					if exited_normally:
						# if we weren't given a new task that caused us to abandon the program early, then
						# queue up the blackout program since that is our base resting state
						self.queue.put_nowait(ProgramTask('blackout'))
					
				elif next_task.program == 'wakeup':
					exited_normally = self.wakeup(**next_task.arg_dict)
					
					if exited_normally:
						# if we weren't given a new task that caused us to abandon the program early, then
						# queue up the blackout program since that is our base resting state
						self.queue.put_nowait(ProgramTask('blackout'))
					
			except Empty:
				# Queue is empty so let's sleep for a second before checking again.
				# Realistically, shouldn't really get here since paradigm is to always be executing a program, even if it's blackout
				sleep(1)
			
	
	# definition of individual programs
	def quit_blackout(self):
		'''Program to turn all LEDs to black briefly before the subprocess is killed.'''
		self._set_current_program('quit_blackout')
		self.logger.info('Starting Program: {}'.format(self.current_program))
		
		data = [ColorObject(0,0,0) for i in range(self.num_pixels)]
		for i in range(0,5):
			self._send_data(data)
			sleep(.01)
		
		self.logger.info('Exiting Program: {}'.format(self.current_program))

	def blackout(self):
		'''Program to turn all LEDs to black and keep them there.'''
		self._set_current_program('blackout')
		self.logger.info('Starting Program: {}'.format(self.current_program))
		
		data = [ColorObject(0,0,0) for i in range(self.num_pixels)]
		while not self._check_for_task():
			self._send_data(data)
			sleep(.1)
			
		self.logger.info('Exiting Program: {}'.format(self.current_program))
			
	def single_color(self, red=0, green=0, blue=0):
		'''
		Program to turn all LEDs to a single RGB color.
		
		Args:
			(opt) red (int) - red value
			(opt) green (int) - green value
			(opt) blue (int) - blue value
		'''
		self._set_current_program('single_color')
		self.logger.info('Starting Program: {} with rgb = {}, {}, {}'.format(self.current_program, str(red), str(green), str(blue)))
		
		data = [ColorObject(red, green, blue) for i in range(self.num_pixels)]
		while not self._check_for_task():
			self._send_data(data)
			sleep(.1)
		
		self.logger.info('Exiting Program: {}'.format(self.current_program))		
		self.quit_blackout()

	def changing_color(self, dwell_time_ms=10000, transition_time_ms=3000, brightness_scale_pct=100):
		'''Program that shifts randomly between a list of colors.'''	
		self._set_current_program('changing_color')
		self.logger.info('Starting Program: {} with dwell_time_ms={} and transition_time_ms={} and brightness_scale_pct={}'.format(self.current_program, str(dwell_time_ms), str(transition_time_ms), str(brightness_scale_pct)))
		
		# r, g, b, led pct
		raw_program_options = [
			(255,0,255,100),	# pink
			(128,0,255,100),	# purple
			(64,0,255,100),		# bluish purple
			(255,0,128,100),	# bright pink
			(255,0,64,100),		# reddish pink
			(255,64,0,100),		# orange
			(255,255,0,100),	# yellow
			(0,255,255,100),	# teal
			(0,255,128,100),	# green teal
			(0,255,50,100),		# bluish green
			(0,128,255,100),	# blue teal
			(0,64,255,100),		# light blue
			(255,0,0,100),		# red
			(0,255,0,100),		# green
			(0,0,255,100)		# blue
		]
		
		# scale the programs to control brightness
		scale_factor = float(brightness_scale_pct) / float(100)
		program_options = [(int(x[0]*scale_factor), int(x[1]*scale_factor), int(x[2]*scale_factor), x[3]) for x in raw_program_options]
			
		
		# pick the first color
		prev_program = random.choice(program_options)
		self.logger.info(prev_program)
		
		while not self._check_for_task():
			
			# setup the data array for the color
			data = [ColorObject(prev_program[0], prev_program[1], prev_program[2]) for i in range(self.num_pixels)]
			
			# loop through the dwell time and send the color to the pixels
			for i in range(0, dwell_time_ms, 100):
				self._send_data(data)
				sleep(.1)
				if self._check_for_task():
					break
			
			# pick the next color
			while True:
				program = random.choice(program_options)
				if program != prev_program:
					# if the random color is the same as the previous one, then keep repicking until it isn't
					break
			
			self.logger.info(program)
			
			# transition between colors over the transition_time_ms period
			iter_count = transition_time_ms * self.base_multiplier / 10000
			exited_normally = self._iterate_color_transition(prev_program, program, iter_count, data)
			if not exited_normally:
				break
			
			
			# prep for the next iteration
			prev_program = program

			
		self.logger.info('Exiting Program: {}'.format(self.current_program))		
		self.quit_blackout()
		
	def sleepy_time(self, multiplier=5):
		'''Program that slowly goes from light on to dark.
		
		Args:
			(opt) multiplier (int) - sets the total duration of the program. Completion is reached in roughly the number of minutes equal to the multiplier.
		'''
		self._set_current_program('sleepy_time')
		self.logger.info('Starting Program: {} with multiplier={}'.format(self.current_program, str(multiplier)))
		
		# r, g, b, led pct, transition time ratio from this to next
		program_sequence = [
			(128,0,0,100,1),
			(0,0,0,100,0)
		]
		
		exited_normally = self._wakeup_core(program_sequence, multiplier, base_multiplier=600)
				
		self.logger.info('Exiting Program: {}'.format(self.current_program))
		self.quit_blackout()
		
		return exited_normally

		
	def wakeup(self, multiplier=30):
		'''
		Program that simulates a sunrise sequence increasing in color, brightness, and pixel count throughout.
		
		Args:
			(opt) multiplier (int) - sets the total duration of the sunrise. Full brightness is reached in roughly the number of minutes equal to the multiplier.
		'''
		self._set_current_program('wakeup')
		self.logger.info('Starting Program: {} with multiplier={}'.format(self.current_program, str(multiplier)))
		
		# r, g, b, led pct, transition time ratio from this to next
		program_sequence = [
			(0,0,0,10,1),	# black
			(0,0,10,15,1),	# dark blue
			(2,0,15,20,1),	# purple
			(7,0,10,25,1),	# reddish purple
			(20,1,0,30,1),	# blood orange
			(50,6,0,40,1),	# orange
			(70,15,0,50,1),	# yellow
			(70,15,2,60,2),	# warm white
			(255,200,100,100,5), # white
			(255,200,100,100,0)	# white
		]
		
		exited_normally = self._wakeup_core(program_sequence, multiplier)
				
		self.logger.info('Exiting Program: {}'.format(self.current_program))
		self.quit_blackout()
		
		return exited_normally
		
	def _wakeup_core(self, program_sequence, multiplier, base_multiplier=60):
		exited_normally = True
		
		data = [ColorObject(0,0,0) for x in range(0,self.num_pixels)]
		for i in range(1, len(program_sequence)):
			from_state = program_sequence[i-1]
			to_state = program_sequence[i]
			self.logger.info(str(i))
			self.logger.info(from_state)
			
			iter_count = multiplier * base_multiplier * from_state[4]
			self.logger.info("iter_count = " + str(iter_count))
			exited_normally = self._iterate_color_transition(from_state, to_state, iter_count, data)
			
			if exited_normally == False or self._check_for_task():
				exited_normally = False
				break
				
		return exited_normally

	def _iterate_color_transition(self, from_state, to_state, iter_count, data):
		red_delta, green_delta, blue_delta, pixel_delta = self._calc_deltas(from_state, to_state)
		self.logger.info("deltas: ")
		self.logger.info((red_delta, green_delta, blue_delta, pixel_delta))
		
		for j in range(0, iter_count):
			if iter_count % 10 == 0:
				if self._check_for_task():
					return False
			red = from_state[0] + self._calc_delta_influence(red_delta, iter_count, j)
			green = from_state[1] + self._calc_delta_influence(green_delta, iter_count, j)
			blue = from_state[2] + self._calc_delta_influence(blue_delta, iter_count, j)
			pixel_count = int(round(float(from_state[3])/100.0*self.num_pixels)) + self._calc_delta_influence(pixel_delta, iter_count, j)
			
			
			# set unused pixels to black
			for idx in range(pixel_count, self.num_pixels):
				data[idx] = ColorObject(0,0,0)
			
			try:
				# set used pixels to correct color
				for k in range(0, pixel_count):
					data[k] = ColorObject(red, green, blue)
			except Exception as e:
				self.logger.info(str(k))
				self.logger.info(str(pixel_count))
				self.logger.info(str(pixel_delta))
				self.logger.info(str(self.num_pixels) + '\n')
				
				raise e
				
			self._send_data(data)
			sleep(.1)
		
		return True
		
	
	def _calc_deltas(self, from_state, to_state):
		'''
		Calculate deltas between one state and another
		
		Arguments:
			from_state (list) - starting state
			to_state (list) - ending state
			
		Returns:
			tuple
				red_delta (float) - delta in red
				green_delta (float) - delta in green
				blue_delta (float) - delta in blue
				pixel_delta (float) - delta in pixel count
		'''
		red_delta = self._calc_delta(to_state[0], from_state[0])
		green_delta = self._calc_delta(to_state[1], from_state[1])
		blue_delta = self._calc_delta(to_state[2], from_state[2])
		pixel_delta = (float(to_state[3])/100.0 * float(self.num_pixels)) - (float(from_state[3])/100.0 * float(self.num_pixels))
		
		return red_delta, green_delta, blue_delta, pixel_delta
		
	def _calc_delta(self, to_item, from_item):
		'''
		Calculate delta between two items
		
		Arguments:
			to_item (int/float) - end item
			from_item (int/float) - starting item
			
		Returns:
			(float) - delta between the items
		'''
		return float(to_item - from_item)
		
	def _calc_delta_influence(self, delta, iter_count, j):
		'''
		Determine the influence of the delta for a given iteration.
		
		Arguments:
			delta (float) - the delta to check
			iter_count (int) - total number of iterations
			j (int) - current value of the iteration
			
		Returns:
			(int) - the portion of the delta to apply on this iteration
		'''
		return int(round(float(delta) * (float(j) / float(iter_count))))