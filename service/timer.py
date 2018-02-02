import json

from crontab import CronTab

from programs import ProgramList

class Timers(object):
	'''Object defining the collection of timers'''
	
	def __init__(self, logger, timer_file):
		self.logger = logger
		self.timer_file = timer_file
	
	def enable_timer(self, timer_id):
		timer = self.get_timer_by_id(timer_id)
		timer.is_enabled = True
		self.add_or_modify_timer(timer)
		
		return timer
		
	def disable_timer(self, timer_id):
		timer = self.get_timer_by_id(timer_id)
		timer.is_enabled = False
		self.add_or_modify_timer(timer)
		
		return timer
	
	def add_or_modify_timer(self, timer):
		timer_dict = self.read_timers_from_file()
		timer_dict[timer.timer_id] = timer
		timer.save_to_cron()
		self.write_timers_to_file(timer_dict)
		
		return timer
		
	def delete_timer(self, timer_id):
		timer = self.get_timer_by_id(timer_id)
		timer_dict = self.read_timers_from_file()
		timer_dict.pop(timer_id)
		timer.delete_from_cron()
		self.write_timers_to_file(timer_dict)
		
	def read_timers_from_file(self):
		'''
		Read timers from the timer file into a dictionary
		
		Returns:
			timer_dict (dict) - dictionary of timers
		'''
		with open(self.timer_file, 'r') as f:
			timer_dict = json.loads(f.read())
			
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = Timer.from_json(self.logger, timer_dict[timer_id])
		
		return timer_dict
		
	
	def write_timers_to_file(self, timer_dict):
		'''
		Write all timers to the timer file.
		
		Arguments:
			timer_dict (dict) - dictionary of timers
		'''
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = timer_dict[timer_id].to_storage_json()
				
		with open(self.timer_file, 'w') as f:
			f.write(json.dumps(timer_dict, indent=4))


	def get_timer_by_id(self, timer_id):
		'''
		Get a specific timer from the timer file based on timer_id.
		
		Arguments:
			timer_id (string) - id of the desired timer
			
		Raises:
			TimerNotFound
			
		Returns:
			Timer object for the desired timer
		'''
		timer_dict = self.read_timers_from_file()
		
		try:
			return timer_dict[timer_id]
		
		except KeyError:
			raise TimerNotFound()

class Timer(object):
	'''Object defining a timer'''

	def __init__(self, logger, timer_id, trigger_hour, trigger_minute, timer_schedule, program_to_launch, is_enabled=True, arguments=None):
		'''
		Initialize a timer object.
		
		Arguments:
			timer_id (string) - ID/name of the timer
			trigger_hour (integer) - hour of the day for the timer
			trigger_minute (integer) - minute of the hour for the timer
			timer_schedule (list) - list of days of the week for the timer
			program_to_launch (string) - name of the program to launch when the timer fires
			(opt) is_enabled (boolean) - indicates if the timer should be enabled
			(opt) arguments (dict) - dictionary of URL parameter arguments to pass when calling the program_to_launch
			
		Raises:
			InvalidTimerException
		'''
		self.logger = logger
		self.cron = CronTab(user='pi')
		
		self.timer_id = timer_id
		if is_enabled is None:
			self.is_enabled = True
		else:
			self.is_enabled = is_enabled
		
		try:
			if not (trigger_hour >= 0 and trigger_hour <=23):
				raise InvalidTimerException("Trigger hour must be between 0 and 23")
			
			if not (trigger_minute >= 0 and trigger_minute <= 59):
				raise InvalidTimerException("Trigger minute must be between 0 and 59")
				
			self.trigger_hour = trigger_hour
			self.trigger_minute = trigger_minute
		
		except InvalidTimerException:
			raise
		
		except Exception as e:
			raise InvalidTimerException("Could not parse input time")
			
		if program_to_launch in ProgramList.valid_programs:
			self.program_to_launch = program_to_launch
		else:
			raise InvalidTimerException("{} is not a valid program to launch.".format(program_to_launch))
		
		self.arguments = arguments
		if arguments is not None:
			if not isinstance(arguments, dict):
				raise InvalidTimerException("Arguments list must be key/value pairs")
		
		self.timer_schedule = self.ingest_timer_schedule(timer_schedule)


	def ingest_timer_schedule(self, timer_schedule):
		'''
		Validate and process a provided timer schedule.
		
		Arguments:
			timer_schedule (list) - list of days of the week for the timer
			
		Raises:
			InvalidTimerException
		
		Returns:
			(list) - processed timer schedule with numeric days of week
		'''
		valid_entries = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
		
		for item in timer_schedule:
			if item not in valid_entries:
				raise InvalidTimerException('{} is not a valid entry for a timer schedule'.format(item))
		
		a = [self.dow_to_num(x) for x in timer_schedule]
		b = set(a)
		sched = list(b)
		
		return sched

	
	@staticmethod
	def dow_to_num(dow):
		'''Convert three-letter day of week to number'''
		d = dow.lower()
		if d == 'mon':
			return 1
		elif d == 'tue':
			return 2
		elif d == 'wed':
			return 3
		elif d == 'thu':
			return 4
		elif d == 'fri':
			return 5	
		elif d == 'sat':
			return 6
		elif d == 'sun':
			return 7
	
	@staticmethod
	def num_to_dow(num):
		'''Convert numeric day of week to three-letter format'''
		if num == 1:
			return 'mon'
		elif num == 2:
			return 'tue'
		elif num == 3:
			return 'wed'
		elif num == 4:
			return 'thu'
		elif num == 5:
			return 'fri'
		elif num == 6:
			return 'sat'
		elif num == 7:
			return 'sun'
		
	@classmethod
	def from_json(cls, logger, json_dict):
		'''
		Instantiate timer object from the json representation.
		
		Arguments:
			json_dict (dict) - dictionary representation of the timer
			
		Returns:
			(Timer) - timer object from the provided data
		'''
		timer_id = json_dict['timerId']
		is_enabled = json_dict['isEnabled'] if json_dict['isEnabled'] is not None else True
		
		try:
			args = json_dict['arguments']
		except KeyError:
			args = None
			
		if json_dict['timerSchedule'] is not None:
			if isinstance(json_dict['timerSchedule'][0], int):
				json_dict['timerSchedule'] = [cls.num_to_dow(x) for x in json_dict['timerSchedule']]
			
		timer_obj = Timer(logger, timer_id, json_dict['triggerHour'], json_dict['triggerMinute'], json_dict['timerSchedule'], json_dict['programToLaunch'], is_enabled, args)
		
		return timer_obj
	
	def to_storage_json(self):
		'''
		Output the json storage format of the timer (schedule in numeric day of week)
		
		Returns:
			(dict) - dict for storage as json
		'''		
		resp = {
			'timerId': self.timer_id,
			'isEnabled': self.is_enabled,
			'triggerHour': self.trigger_hour,
			'triggerMinute': self.trigger_minute,
			'timerSchedule': self.timer_schedule,
			'programToLaunch': self.program_to_launch,
			'arguments': self.arguments
		}
		
		return resp
	
	def to_json(self):
		'''
		Output the client-facing json format of the timer (schedule in three-letter day of week)
		
		Returns:
			(dict) - dict for showing to client
		'''
		resp = self.to_storage_json()
		resp['timerSchedule'] = [self.num_to_dow(x) for x in self.timer_schedule]
		
		return resp
		
	def save_to_cron(self):
		'''
		Save the timer to the crontab
		'''
		# first see if this is new or update
		found_cron = False
		for job in self.cron:
			if job.comment == self.timer_id:
				# we found a matching record so just update item
				found_cron = True
				self.set_cron_record(job)
				break
				
		if not found_cron:
			job = self.cron.new(command='test')
			self.set_cron_record(job)

		self.cron.write()
	
	def set_cron_record(self, job):
		'''
		Set the parameters of the crontab entry
		
		Arguments:
			job - the new or existing cron job to populate
		'''
		self.logger.info(self.to_storage_json())
		arg_string = ''
		if self.arguments is not None:
			arg_list = []
			for name, value in self.arguments.iteritems():
				arg_list.append(name + "=" + str(value))
			arg_string = '?' + '&'.join(arg_list)
			
		job.comment = self.timer_id
		job.enable(self.is_enabled)
		job.command = 'curl localhost:8081/programs/{}{}'.format(self.program_to_launch, arg_string)
		job.minute.on(self.trigger_minute)
		job.hour.on(self.trigger_hour)
		job.dow.on(*self.timer_schedule)
	
	def delete_from_cron(self):
		'''Delete the timer from the crontab'''
		self.cron.remove_all(comment=self.timer_id)
		self.cron.write()
		
#################### CUSTOM EXCEPTIONS ###########################	
class TimerNotFound(Exception):
	pass

class InvalidTimerException(Exception):
	pass
		