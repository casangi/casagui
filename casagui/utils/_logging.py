""" Use the python logging interface for casagui logs.
If casalog is available, then send log messages to it.
Otherwise, use the base python logging mechanisms.
"""
import logging

try:
	from casatasks import casalog
	__casalog_avail = True
except ImportError:
	__casalog_avail = False

class _Logging:
	# singleton instance
	logger = None
	log_handler = None

class CasalogHandler(logging.Handler):
	""" Logs to casalog, as appropriate """
	# map from python logging levels to casalog priorities
	level_to_priority = {
		"DEBUG": "DEBUG",
		"INFO": "INFO",
		"WARNING": "WARN",
		"ERROR": "SEVERE",
		"CRITICAL": "SEVERE"
	}

	def _level_to_levelname(self, level):
		if (level >= 50):
			return "CRITICAL"
		if (level >= 40):
			return "ERROR"
		if (level >= 30):
			return "WARNING"
		if (level >= 20):
			return "INFO"
		return "DEBUG"

	def setLevel(self, level_or_levelname):
		super().setLevel(level_or_levelname)
		if type(level_or_levelname) != str:
			levelname = self._level_to_levelname(level_or_levelname)
		else:
			levelname = level_or_levelname
		casalog.filter(CasalogHandler.level_to_priority[levelname])

	def emit(self, record):
		# promote log level for casalog
		levelname = self._level_to_levelname(_Logging.logger.getEffectiveLevel())
		if levelname == "DEBUG":
			casalog.filter(CasalogHandler.level_to_priority["DEBUG"])

		# get log properties
		origin = (record.filename) if (record.filename != None) else ("")
		casalog.origin(origin)
		priority = CasalogHandler.level_to_priority[record.levelname]
		self.format(record) # populates record.message

		# emit the log
		casalog.post(message=record.message, priority=priority, origin=record.funcName)

class CasalogLogger(logging.getLoggerClass()):
	def setLevel(self, level):
		super().setLevel(level)
		_Logging.log_handler.setLevel(level)

def get_logger():
	""" Returns the singleton logger instance. """
	if _Logging.logger != None:
		return _Logging.logger

	if __casalog_avail:
		_Logging.log_handler = CasalogHandler()

		curr_logger_class = logging.getLoggerClass()
		logging.setLoggerClass(CasalogLogger)
		_Logging.logger = logging.getLogger(__name__)
		logging.setLoggerClass(curr_logger_class)

		_Logging.logger.addHandler(_Logging.log_handler)
		_Logging.logger.propagate = False
	else:
		_Logging.logger = logging.getLogger(__name__)
	return _Logging.logger