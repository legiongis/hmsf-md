import time

class ETLOperationResult():

    def __init__(self, operation, loadid=None, success=True, message="", data={}):
        self.operation = operation
        self.loadid = loadid
        self.start_time = time.time()
        self.success = success
        self.message = message
        self.data = data
        self.seconds = 0

    def __str__(self):
        return str(self.serialize())
    
    def stop_timer(self):
        self.seconds = round(time.time() - self.start_time, 2)

    def log(self, logger, level='info'):
        level_lookup = {
            "critical": 50,
            "error": 40,
            "warn": 30,
            "info": 20,
            "debug": 10,
            "none": 0,
        }
        message = f"loadid: {self.loadid} | {self.message}"
        logger.log(level_lookup[level], message)

    def serialize(self):

        data = self.data

        return {
            "operation": self.operation,
            "success": self.success,
            "data": data,
        }