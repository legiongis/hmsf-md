import json
import time


def get_node_value(resource, node_name):
    """this just flattens the response from Resource().get_node_values()"""

    values = resource.get_node_values(node_name)
    if len(values) == 0:
        value = ""
    elif len(values) == 1:
        value = values[0]
    else:
        value = "; ".join(values)

    return value


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

    def get_load_details(self):
        """
        returns this result's data in the desired format for insertion into
        the load_event table (column: load_details) - inserts self.message into
        the returned data.
        """
        details = dict(self.data)
        details['Message'] = self.message
        return json.dumps(details)

    def serialize(self):

        details = dict(self.data)
        details['Message'] = self.message

        return {
            "operation": self.operation,
            "success": self.success,
            "data": details,
        }

