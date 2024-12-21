"""
    Processing errors

"""

import sys
import traceback


def exProcessor( ex ):
    """
        Обробник стека помилок
    
    """
    ex_type, ex_value, ex_traceback = sys.exc_info()
    trace_back = traceback.extract_tb(ex_traceback)
    stack_trace = list()
    for trace in trace_back:
        stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
    #ex_code=e.code
    if type(ex_type.__name__) is bytes:
        ex_name=ex_type.__name__.decode("utf-8")
    else:        
        ex_name=ex_type.__name__
    if not ex_value.args:
        if ex.payload :
            if "code" in ex.payload: 
                ex_name=ex.payload["code"]
            if "description" in ex.payload: 
                ex_dsc=ex.payload["description"]
        else:     
            ex_dsc="None"
    elif type( ex_value.args[0] ) is bytes:
        ex_dsc=ex_value.args[0].decode("utf-8")
    elif isinstance(ex_value.args[0], dict):
        for k, v in ex_value.args[0].items():
            if type(v) is bytes:
                ex_value.args[0][k] = v.decode("utf-8")   
                          
        ex_dsc=ex_value.args[0]    
    else:
        ex_dsc=ex_value.args[0]    

    result={}
    result["ex_name"]=ex_name
    result["ex_dsc"]=ex_dsc
    result["stack_trace"]=stack_trace
    return result


class InvalidAPIUsage(Exception):
    """
        Use this Error class in case of errors in checking request parameters
    """
    status_code = 422

    def __init__(self, code, message, target=None, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code 
        if target is not None:
            self.target = target
        else:
            self.target = ""
        self.payload = payload

    def to_dict(self):
        errdsc = {}
        errdsc["code"] = self.code
        errdsc["description"] = self.message
        errdsc["target"] = self.target
        rv={}
        rv["Error"]=errdsc
        rv["Error"]["Inner"]=dict(self.payload or ())
        return rv

class AppValidationError(Exception):
    """
        Use this Error class in case of validation errors in business logic
    """

    status_code = 422

    def __init__(self, code, message, target=None, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code 
        if target is not None:
            self.target = target
        else:
            self.target = ""
        self.payload = payload

    def to_dict(self):
        errdsc = {}
        errdsc["code"] = self.code
        errdsc["description"] = self.message
        errdsc["target"] = self.target
        rv={}
        rv["Error"]=errdsc
        rv["Error"]["Inner"]=dict(self.payload or ())
        return rv


class AppError(Exception):
    """
        Use this Error class in case of any errors in business logic
    """    
    status_code = 503

    def __init__(self, code, message, target=None, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code 
        if target is not None:
            self.target = target
        else:
            self.target = ""
        self.payload = payload

    def to_dict(self):
        errdsc = {}
        errdsc["code"] = self.code
        errdsc["description"] = self.message
        errdsc["target"] = self.target
        rv={}
        rv["Error"]=errdsc
        rv["Error"]["Inner"]=dict(self.payload or ())
        return rv


class IttLibError(Exception):
    status_code = 500

    def __init__(self, code, message, target=None, status_code=None, payload=None, header=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code 
        if target is not None:
            self.target = target
        else:
            self.target = ""
        self.payload = payload
        if header is not None:
            self.header=header 
        else:
            self.header={} 

    def to_dict(self):
        errdsc = {}
        errdsc["code"] = self.code
        errdsc["description"] = self.message
        errdsc["target"] = self.target
        rv={}
        rv["Header"]=self.header
        rv["Error"]=errdsc
        rv["Error"]["Inner"]=dict(self.payload or ())
        return rv

