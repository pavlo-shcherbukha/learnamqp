from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, jsonify, make_response, g
from flask.logging import default_handler
from urllib.parse import unquote
import json
import logging
import datetime
import base64
from . import app
#from hello_app.eds_srvc import Eds 
from hello_app.eds_srvc_ext import Eds 
from hello_app.Errors import exProcessor, AppError, AppValidationError 
# my own logger
import hello_app.shjsonformatter
import hello_app.shreqjsonformatter
#, IttLibError
#  IIT CRYPTO
import sys
import traceback
import os
import redis
import time

import gevent
from gevent.event import AsyncResult
from gevent.timeout import Timeout
from gevent import monkey


ver='101'
if os.environ.get("APP_DEBUG") == 'DEBUG_BRK':
    import debugpy
    print("===========1-DEBUG-BREAK======")
    breakpoint() 
    print("===========2-DEBUG-BREAK======")

application = Flask(__name__)
application.logger.removeHandler(default_handler)

@application.before_request
def start_timer():
    g.start = time.time()

@application.after_request
def log_request(response):
    if request.path == '/favicon.ico':
        return response
    #elif request.path.startswith('/static'):
    #    return response

    now = time.time()
    duration = round(now - g.start, 2)
    
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    host = request.host.split(':', 1)[0]
    args = dict(request.args)

    log_params = {
        'method': request.method, 
        'path': request.path,
        'request_content_type': request.headers.get('Content-Type'),
        'request_size': int(request.headers.get('Content-Length') or 0),
        'status': response.status_code, 
        'duration': duration, 
        'time': now,
        'ip': ip,
        'host': host,
        'params': args,
        'response_content_type': response.content_type,
        'response_size': response.calculate_content_length()

    }

    logger.info("HTTP API REQ", extra=log_params)

    return response


logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
apploglevel=os.environ.get("LOGLEVEL")
if apploglevel==None:
    logger.setLevel(logging.DEBUG)
elif apploglevel=='DEBUG':
    logger.setLevel(logging.DEBUG)    
elif apploglevel=='INFO':
    logger.setLevel(logging.INFO)    
elif apploglevel=='WARNING':
    logger.setLevel(logging.WARNING)    
elif apploglevel=='ERROR':    
    logger.setLevel(logging.ERROR)    
elif apploglevel=='CRITICAL':
    logger.setLevel(logging.CRITICAL)    
else:
    logger.setLevel(logging.DEBUG)  

handler = logging.StreamHandler()
handler.setFormatter( hello_app.shjsonformatter.JSONFormatter())
logger.addHandler(handler)


#application.logger.addHandler(handler)
# =============================================
# Обробник помилок використання API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   "Error":    {
#      "code": "IIB.MNEMONICCODEERROR",
#      "description": "Short error description",
#      "target": "Target",
#      "Inner": {
#          "code": "IIB.InnerCodeError",
#          "description": "Full error description"
#      }
#   }
#
# ==============================================
class InvalidAPIUsage(Exception):
    status_code = 400

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



class UnexpectedHttpMethod(Exception):
    status_code = 404

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




# =======================================================
# Перехоплювач помилок API  та формування відповіді
# =======================================================

@application.errorhandler(InvalidAPIUsage)
def invalid_api_usage(e):
    r=e.to_dict()
    return json.dumps(r), e.status_code, {'Content-Type':'application/json'}

@application.errorhandler(IttLibError)
def itt_lib_error(e):
    r=e.to_dict()
    logger.debug( f"IttLibError: Вертаю результат: status=  {e.status_code} body: " +  json.dumps(  r ))
    return json.dumps(r), e.status_code, {'Content-Type':'application/json'}

@application.errorhandler( UnexpectedHttpMethod)
def unexpected_http_method_error(e):
    r=e.to_dict()
    return json.dumps(r), e.status_code, {'Content-Type':'application/json'}

@application.errorhandler( AppError)
def apperror_error(e):
    r=e.to_dict()
    return json.dumps(r), e.status_code, {'Content-Type':'application/json'}



def add_cors_headers(response):
    """
        CORSA headers
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Content-Type"] = "applicaion/json"
    response.headers["Accept"] = "applicaion/json"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "DELETE,GET,POST,OPTIONS"
    return response

logger.debug("Read env variables")

irds_host = None
irds_port = None
irds_psw = None
irds_channel = None

caspth=""

eds = Eds( __name__)

logger.debug( "Реєструю сервіс в ситсемі отримання налаштувань " )
reg_result=eds.register_service()       
logger.debug( "Реєструю сервіс в ситсемі отримання налаштувань reg_result=" + json.dumps(reg_result, ensure_ascii=False) )

eds.load()

logger.debug( "Завантаження ключа: " + str( eds.isKeyLoaded() ))
logger.debug( "!!!!=======Читаю список підключених пристроїв=======!!!!!!")

def readkeymedia():
    """
            Прочитати підключені носії
    """
    logger=logging.getLogger(__name__).getChild("readkeymedia")
    logger.debug('readkeymedia - start')
    logger.debug('Читаю key media')
    devlist=[]
    dwType = 0
    lDescription = []
    lDevDescription = []
    try:
        logger.debug("eds.KeyMediaTypes")
        rd_result=eds.KeyMediaTypes(dwType, lDescription)        
        typex={}
        if rd_result["ok"]:
            typex["type_index"]=rd_result["typeindex"]
            typex["type_description"]=rd_result["typedescription"]
            typex["devices"]=[]            
            dv_index=0
            dv_res=eds.KeyMediaDevices(rd_result["typeindex"], dv_index ,lDevDescription )
            if dv_res["ok"]==True:
                devex={}
                devex["dev_index"]=dv_res["devindex"]
                devex["dev_description"]=dv_res["devdescription"]
                typex["devices"].append(devex)

            while dv_res["ok"]:
                devex={}
                dv_index +=1
                dv_res=eds.KeyMediaDevices(rd_result["typeindex"], dv_index  ,lDevDescription )
                if dv_res["ok"]==True:
                    devex["dev_index"]=dv_res["devindex"]
                    devex["dev_description"]=dv_res["devdescription"]
                    typex["devices"].append(devex)
            devlist.append( typex )
    
        while rd_result["ok"]:
            dwType += 1
            rd_result=eds.KeyMediaTypes(dwType, lDescription)        
            typex={}
            
            typex["type_index"]=rd_result["typeindex"]
            typex["type_description"]=rd_result["typedescription"]
            typex["devices"]=[]
            if rd_result["ok"]:
                dv_index=0
                dv_res=eds.KeyMediaDevices(rd_result["typeindex"], dv_index ,lDevDescription )
                if dv_res["ok"]==True:
                    devex={}
                    devex["dev_index"]=dv_res["devindex"]
                    devex["dev_description"]=dv_res["devdescription"]
                    typex["devices"].append(devex)

                while dv_res["ok"]:
                    devex={}
                    dv_index +=1
                    dv_res=eds.KeyMediaDevices(rd_result["typeindex"], dv_index  ,lDevDescription )
                    if dv_res["ok"]==True:
                        devex["dev_index"]=dv_res["devindex"]
                        devex["dev_description"]=dv_res["devdescription"]
                        typex["devices"].append(devex)
                devlist.append( typex )

        res={}
        res["ok"]=True
        res["devlist"]=devlist

        logger.debug('Вертаю результат:' +  json.dumps(  res, ensure_ascii=False ))
        return  res 
    except Exception as e:
        dError = eval(str(e))
        logger.error("EnumKeyMediaTypes failed. Error code: " + str(dError['ErrorCode']) + ". Description: " + dError['ErrorDesc'].decode("utf-8"))
        logger.error('Вертаю помилку бібліотеки')
        res={}
        res["ok"]=False
        res["status"] = 503
        res["description"] = "EnumKeyMediaTypes failed. Error code: " + str(dError['ErrorCode']) + ". Description: " + dError['ErrorDesc'].decode("utf-8")
        return res 

logger.debug( "!!!=Будую список підключених носіїв!!!")
i_devlist=readkeymedia()
logger.debug( "!!===Будую список підключених носіїв=OK!!!")


logger.debug("Читаю параметри підключення ло Redis")    
irds_host = os.getenv('RDS_HOST');
irds_port = os.getenv('RDS_PORT');
irds_psw = os.getenv('RDS_PSW');
irds_channel = os.getenv('RDS_CHANNEL');
logger.debug('Підключеня до redis: ' + 'host=' + irds_host + ' Порт=' + irds_port + ' Пароль: ' + irds_psw + ' Канал=' + irds_channel)


red = None
ichannel = None

i_key_read = "keyread"
i_key_readerror_text = "keyread_error_text"
i_key_info = "key_info"

#Канал комунікації з іншими сервісвами
ichannel = irds_channel
logger.debug("Connect to Redis")
red = redis.StrictRedis(irds_host, irds_port, charset="utf-8", password=irds_psw, decode_responses=True)
logger.debug(" Trying PING")
rping=red.ping()
logger.debug( str(rping) )
if rping:
    logger.debug("redis Connected")
    sub = red.pubsub()    
    sub.subscribe( ichannel )   
    logger.debug("Встановлюю в REDIS ознаки читання ключа") 
    red.set(i_key_read, 0)
    red.set(i_key_readerror_text, "")
    red.set(i_key_info, json.dumps({}))
else:
    logger.error("redis NOT CONNECTED!!!")    

#==========================================
# Публікація команди в чергу
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ap_cmd = { "cmd": "readkey", "params": {}}
#========================================== 
def sendCmd( ap_cmd ):
    logger=logging.getLogger(__name__).getChild("sendCmd")
    logger.debug("Відправляюь комнаду сервсам: ")
    res=red.publish(ichannel, json.dumps(ap_cmd) )
    return res   

# =====================================================================================
# Завантаження ключа з гряда
# http://localhost:5000/api/readkey
# {"szPassword": "##username##password", "dwDevIndex": 0, "dwTypeIndex": 3}
# {"szPassword": "##E1804005##ASVP-HM-207136", "dwDevIndex": 4, "dwTypeIndex": 5}
# =====================================================================================

def aureadkey(  ap_username ,ap_password, ap_DevIndex, ap_TypeIndex ):
    logger=logging.getLogger(__name__).getChild("aureadkey")
    logger.debug('aureadkey: Формую структуру KM')
    pKM={}
    pKM = {"szPassword" : "##"+ap_username+"##"+ap_password, "dwDevIndex": ap_DevIndex, "dwTypeIndex": ap_TypeIndex }
    logger.debug('Cтруктура KM  для заватнтаження ключа: ' + json.dumps(pKM , ensure_ascii=False)  )
    if eds.isKeyLoaded():
        eds.ResetPrivateKey()
    res=eds.ReadPrivateKey(pKM)
    logger.debug('Результат завантаження ключа: ' +  json.dumps(  res, ensure_ascii=False ) )
    if res["ok"]==True:
        red.set(i_key_read, 1)
        red.set(i_key_readerror_text, "")
        red.set(i_key_info, json.dumps(res["info"], ensure_ascii=False))
    else:
        red.set(i_key_read, -1)
        red.set(i_key_readerror_text, res["errorCode"] + "-" + res["error"])
        red.set(i_key_info, json.dumps({}))

    return res

# ========================================================
#  Завантажуємо ключ з файла
#  
#  {"szPassword" : "key password", "szPth": "C:\\PSHDEV\\PSH-PVX\\PVX-CERT\\Key-6.dat"}
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def aureadkeyfile( ap_password, ap_pth ):
    logger=logging.getLogger(__name__).getChild("aureadkeyfile")
    logger.debug('aureadkeyfile: Формую структуру KM')
    pKM={}
    pKM = {"szPassword" : ap_password, "szPth": ap_pth}
    logger.debug('Cтруктура KM  для заватнтаження ключа: ' + json.dumps(pKM , ensure_ascii=False)  )
    if eds.isKeyLoaded():
        eds.ResetPrivateKey()
    try:    
        res=eds.ReadPrivateKeyFile(pKM)
        if res["ok"]==True:
            red.set(i_key_read, 1)
            red.set(i_key_readerror_text, "")
            red.set(i_key_info, json.dumps(res["info"], ensure_ascii=False))
        else:
            red.set(i_key_read, -1)
            red.set(i_key_readerror_text, res["errorCode"] + "-" + res["error"])
            red.set(i_key_info, json.dumps({}))

    except Exception as e:    
        logger.error(f" Error: ")

    logger.debug('Результат завантаження ключа: ' +  json.dumps(  res , ensure_ascii=False) )
    return res

#================================================
# Скинути ключ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def auresetPrivateKey():
    logger=logging.getLogger(__name__).getChild("auresetPrivateKey")
    logger.debug('auresetPrivateKey: Скинути ключ')
    res=eds.ResetPrivateKey()
    red.set(i_key_read, 0)
    red.set(i_key_readerror_text, "")
    red.set(i_key_info, json.dumps({}))
    logger.debug('Результат зкидання ключа: ' +  json.dumps(  res, ensure_ascii=False ) )
    return res


#==================================================
# Отримати інформацію про ключа
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#==================================================
def auKeyInfo():
    logger=logging.getLogger(__name__).getChild("auKeyInfo")
    logger.debug("auKeyInfo - start. Отримати інформацію про стан завантаження ключа")
    logger.debug("Перевіряю чи ключ завантажено")
    res={}
    rd_iskeyloaded=eds.isKeyLoaded()
    rd_info={}

    keyread=int(red.get(i_key_read))
    keyread_error_str=red.get(i_key_readerror_text)
    keyinfo_str=red.get(i_key_info)

    logger.debug("keyread=" + str(keyread))
    logger.debug("keyread_error_str=" + keyread_error_str)
    logger.debug("keyinfo_str" + keyinfo_str)


    if rd_iskeyloaded:
        logger.debug("Ключ завантажено!")

        rd_info=json.loads(keyinfo_str)
        rd_res=eds.ReadPrivateKeyInfo()
        logger.debug("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$") 
        logger.debug("Сертиф:" + json.dumps(rd_res["certs"] , ensure_ascii=False))
        
        if rd_res["ok"] == True:
           rd_info["certs"]=rd_res["certs"] 
    else:
        logger.debug("Ключ не завантажено! Інформація про ключ не може бути прочитаною")
        
        if keyread<0:
            logger.debug("Помилка при завантаженні ключа: " + keyread_error_str) 
            res["error"]=keyread_error_str
    
    logger.debug("Вертаю резулдьтат!!")
    res["ok"]=True

    res["iskeyload"]=rd_iskeyloaded

    logger.debug("Перевіряю наявність info")
    if rd_iskeyloaded: 
        res["certinfo"]=rd_info
    logger.debug("--------Вертаю резулдьтат 2!!---" +  json.dumps(  res , ensure_ascii=False))
    return res


#===============================================
# ********* UI UI UI UI UI UI UI****************
#===============================================


#=================================================
# Головна сторінка
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#=================================================
@application.route("/")
def home():
    logger=logging.getLogger(__name__).getChild("home")
    logger.debug("render home.html")
    res=auKeyInfo()
    logger.debug(f"Повертаю результат з даними: {json.dumps(  res, ensure_ascii=False )}")
    return render_template("home.html" , data=res)



#=================================================
# Про програму
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#=================================================
@application.route("/about/")
def about():
    logger=logging.getLogger(__name__).getChild("about")
    logger.debug("render about")
    return render_template("about.html")


#============================================
# Формочка завантаження ключа з файла
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#============================================
@application.route("/uireadkeyfile/")
def ui_readkeyfile():
    logger=logging.getLogger(__name__).getChild("ui_readkeyfile")
    logger.debug("render readkeyfile.html")
    return render_template("readkeyfile.html")


#===========================================
# Обробка завантаження ключа з файла
# відправка команди на завантаення ключа сервісам
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#==========================================
@application.route("/uireadkeyfileres/", methods=["POST"])
def ui_readkeyfileres():
    logger=logging.getLogger(__name__).getChild("ui_readkeyfileres")
    body={}
    mimetype = request.mimetype
    logger.debug(f"mimetype = {mimetype}")
    if mimetype == 'application/x-www-form-urlencoded':
        iterator=iter(request.form.keys())
        for x in iterator:
            body[x]=request.form[x]            
    elif mimetype == 'application/json':
        body = request.get_json()
    else:
        orm = request.data.decode()

    logger.debug('розбираю тіло запита' + json.dumps(  body, ensure_ascii=False ))
    logger.debug('Готую команду завантаження ключа' )

    lcmdparams={}
    lcmdparams["szPth"]=body["szPth"]
    lcmdparams["szPassword"]=body["szPassword"]

    lcmd = {}
    lcmd["cmd"]="readkeyfile"
    lcmd["params"]=lcmdparams
    logger.debug('Посилаю команду: ' +  json.dumps(  lcmd , ensure_ascii=False ))
    res=sendCmd(  lcmd )
    logger.debug('Вертаю результат: ' +  json.dumps(  res , ensure_ascii=False ))

    return render_template("readkeyfile_res.html")
    


#============================================================
# Сториінка вводу параметрыв для завантаження ключа з  гряда
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#============================================================
@application.route("/uireadkeygryada/")
def ui_readkeygryada():
    logger=logging.getLogger(__name__).getChild("ui_readkeygryada")
    logger.debug("render readkey.html")
    return render_template("readkey.html")

#============================================================
# Обробка завантаження ключа з  гряда
# Відпарвка комнади сервісам на завантаження
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#============================================================
@application.route("/uireadkeygryadares/", methods=["POST", "GET"])
def ui_readkeyres():
    logger=logging.getLogger(__name__).getChild("ui_readkeyres")
    body={}
    mimetype = request.mimetype
    logger.debug(f"mimetype = {mimetype}")
    logger.debug( "=============Request Headers================" )
    hiterator=iter(request.headers.keys())
    for x in hiterator:
        logger.debug( "header " + x +":" +  request.headers[x] )  
    logger.debug( "=============**************================" )
    if mimetype == 'application/x-www-form-urlencoded':
        iterator=iter(request.form.keys())
        for x in iterator:
            body[x]=request.form[x]            
    elif mimetype == 'application/json':
        body = request.get_json()
    else:
        orm = request.data.decode()

    logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False  ))
    logger.debug('Готую команду завантаження ключа' )

    lcmdparams={}
    lcmdparams["szUsername"]=body["szUsername"]
    lcmdparams["szPassword"]=body["szPassword"]
    lcmdparams["dwDevIndex"]=int( body["dwDevIndex"] )
    lcmdparams["dwTypeIndex"]=int( body["dwTypeIndex"] )

    lcmd = {}
    lcmd["cmd"]="readkey"
    lcmd["params"]=lcmdparams
    logger.debug('Посилаю команду: ' +  json.dumps(  lcmd , ensure_ascii=False ))
    res=sendCmd(  lcmd )
    logger.debug('Вертаю результат: ' +  json.dumps(  res, ensure_ascii=False  ))
    return render_template("readkey_res.html")   

#========================================================
# Завантаження сторінки завантаження для скидання ключа
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#========================================================
@application.route("/uiresetkey/")
def ui_resetkey():
    logger=logging.getLogger(__name__).getChild("ui_resetkey")
    logger.debug("render resetkey.html")
    return render_template("resetkey.html")

#=====================================================
# Обробка зкидання ключа
# (Відправка комнади на скидання ключа)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#=====================================================
@application.route("/uiresetkeyres/", methods=["POST"])
def ui_resetkeyres():
    logger=logging.getLogger(__name__).getChild("ui_resetkeyres")
    body={}
    mimetype = request.mimetype
    logger.debug(f"mimetype = {mimetype}")
    if mimetype == 'application/x-www-form-urlencoded':
        iterator=iter(request.form.keys())
        for x in iterator:
            body[x]=request.form[x]            
    elif mimetype == 'application/json':
        body = request.get_json()

    logger.debug('розбираю тіло запита' + json.dumps(  body, ensure_ascii=False  ))
    logger.debug('Готую команду скидання ключа' )

    lcmdparams={}
    lcmdparams["szMsg"]=body["szMsg"]

    lcmd = {}
    lcmd["cmd"]="resetkey"
    lcmd["params"]=lcmdparams
    logger.debug('Посилаю команду: ' +  json.dumps(  lcmd , ensure_ascii=False ))
    res=sendCmd(  lcmd )
    logger.debug('Вертаю результат: ' +  json.dumps(  res , ensure_ascii=False ))
    return render_template("resetkey_res.html")   



#==================================================================
# Завантаження сторінки з інформацією про стан завантаження ключа
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@application.route("/keyinfo/")
def ui_keyinfo():
    logger=logging.getLogger(__name__).getChild("ui_keyinfo")
    res=auKeyInfo()
    logger.debug("Повертаю результат :::" + json.dumps(  res , ensure_ascii=False ) )
    return render_template("keyinfo_res.html", data=res)



#===========================================================================
#    *********** Сервісні  АПІ для роботи EDS ******************************
#===========================================================================

# =================================================================================
# Метод health check
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Повертає {'success':True} якщо контейнер працює
# =================================================================================
@application.route("/api/health", methods=["GET", "OPTIONS"])
def health():
    logger=logging.getLogger(__name__).getChild("health")
    if request.method=='GET':
        logger.debug('Health check')
        response=make_response(  jsonify(  {'success':True, 'version': ver}  ), 200 )
        response=add_cors_headers(response)
        return response 
    elif request.method=='OPTIONS':
        #response = flask.Response()
        response=make_response()
        response=add_cors_headers(response)
        return response, 200    

@application.route("/api/readkey", methods=["POST"])
def readkey():
    """
        Прочитати клч з грядки
    """
    logger=logging.getLogger(__name__).getChild("readkey")
    logger.debug('readkey - start')
    if request.method=='POST':
        logger.debug('Отримую тіло запита')
        body = request.get_json()

        logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False ))
        usrname = body["szUsername"]
        psw = body["szPassword"]
        devindex = body["dwDevIndex"]
        devtype = body["dwTypeIndex"]
        res=aureadkey(usrname ,psw, devindex, devtype)
        logger.debug('Вертаю результат:' +  json.dumps(  res , ensure_ascii=False  ))
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}
    else:
        logger.debug('возвращаю ошибку о недопустимомо методе')
        res={}
        res["status"] = 404
        res["description"] = "Метод не найден!"
        return json.dumps( res ), 404, {'Content-Type':'application/json'}




@application.route("/api/readkeyfile", methods=["POST"])
def readkeyfile():
    """
        Прочитати ключа з файлового носія
    """
    logger=logging.getLogger(__name__).getChild("readkeyfile")
    logger.debug('readkeyfile - start')
    if request.method=='POST':
        body={}
        mimetype = request.mimetype
        logger.debug(f"mimetype =  {mimetype}" )
        if mimetype == 'application/x-www-form-urlencoded':
            iterator=iter(request.form.keys())
            for x in iterator:
                body[x]=request.form[x]            
        elif mimetype == 'application/json':
            body = request.get_json()
        else:
            logger.debug('Не допустимий mimetype' + mimetype )
            raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод", target='/api/sigdocument',status_code=404 )
        body_dict = dict(body)
        logger.debug('Перевіряю наявність поля szPassword')
        if not 'szPassword' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [szPassword!]", target=' /api/readkeyfile check input params ',status_code=422, payload = {"code": "NoKey", "description": "Не вказано обов'язковий ключ в запиті" } )
        logger.debug('Перевіряю наявність поля szPth')
        if not 'szPth' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [szPth!]", target=' /api/readkeyfile check input params ',status_code=422, payload = {"code": "NoKey", "description": "Не вказано обов'язковий ключ в запиті" } )

        if not os.path.exists(  body["szPth"] ):
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No file in path " +  body["szPth"], target=' /api/readkeyfile check if the file exists ',status_code=422, payload = {"code": "NoKey", "description": "Не існує файл за вказаним шляхом" } )


        logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False ))
        psw = body["szPassword"]
        pth = body["szPth"]
        logger.debug('Викликаю: aureadkeyfile')
        res=aureadkeyfile(psw, pth) 
        if res["ok"]==False:
                raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/sigdocument process signature',status_code=500, payload = {"code": res["errorCode"], "description": res["error"] } )    
        logger.debug('Вертаю результат:' +  json.dumps(  res, ensure_ascii=False  ))
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}
    else:
        logger.debug('возвращаю ошибку о недопустимомо методе')
        raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод", target='/api/sigdocument',status_code=404 )




# ==================================================
# Скинути секретний ключ
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ==================================================
@application.route("/api/resetkey", methods=["DELETE"])
def resetkey():
    """
        Вивантажити (скинути серкретний ключ)
    """
    logger=logging.getLogger(__name__).getChild("resetkey")
    logger.debug('resetkey - start')
    if request.method=='DELETE':
        logger.debug('Скинути секретний ключ')
        
        logger.debug('Викликаю API IIT')
        res=eds.ResetPrivateKey()
        if res["ok"]==False:
                raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/sigdocument process signature',status_code=500, payload = {"code": res["errorCode"], "description": res["error"] } )    
        logger.debug('Вертаю результат:' +  json.dumps(  res ))
        pres={}
        pres["ok"]=res["ok"]
        return json.dumps(  pres ), 200, {'Content-Type':'application/json'}
    else:
        logger.debug('возвращаю ошибку о недопустимомо методе')
        raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод", target='/api/sigdocument',status_code=404 )

# =======================================================
# Чи був завантажений ключ.
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# =======================================================
@application.route("/api/iskeyloaded", methods=["GET", "OPTIONS"])
def iskeyloaded():
    """
        Чи завантажно ключа в системі True-False
    """
    logger=logging.getLogger(__name__).getChild("iskeyloaded")
    if request.method=='GET':
        logger.debug('iskeyloaded - start')
        if request.method=='GET':
            logger.debug('Скинути секретний ключ')
            logger.debug('Викликаю API IIT')
            rd=eds.isKeyLoaded()
            logger.debug('Вертаю результат:' )
            res={}
            res["ok"] = True
            res["iskeyloaded"] = rd 
            response=make_response(  jsonify(  res  ), 200 )
            response=add_cors_headers(response)
            return response             

    elif request.method=='OPTIONS':

        response=make_response()
        response=add_cors_headers(response)
        return response, 200    

# ================================================
# Підписати дані. Підпис окремо
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ================================================
@application.route("/api/signdata", methods=["POST"])
def signdata():
    """
        Підписати дані функцією SignData
    """
    logger=logging.getLogger(__name__).getChild("signdata")
    logger.debug('signdata - start')
    if request.method=='POST':
        logger.debug('Отримую тіло запита')
        body = request.get_json()
        logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False ))
        body_dict = dict(body)
        logger.debug('Перевіряю наявність поля signdata')
        if not 'signdata' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [signdata!]", target=' /api/signdata check input params ',status_code=422, payload = {"code": "NoKey", "description": "Не вказано обов'язковий ключ в запиті" } )
        sgData = body["signdata"]
        logger.debug('Викликаю функцію підпису IIT')
        res=eds.SignData( sgData )
        if res["ok"]==False:
                raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/sigdocument process signature',status_code=500, payload = {"code": res["errorCode"], "description": res["error"] } )    
        logger.debug('Вертаю результат:' +  json.dumps(  res, ensure_ascii=False  ))
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}
    else:
        logger.debug('возвращаю ошибку о недопустимомо методе')
        raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод", target='/api/sigdocument',status_code=404 )


# ================================================
# Перевірити пдпис. Підпис окремо, дані окремо
# {"signdata":"", "sign":""}
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ================================================
@application.route("/api/verifydata", methods=["POST"])
def verifydata():
    """
        Перевірити дані, що були Підписані функцією SignData
    """
    logger=logging.getLogger(__name__).getChild("verifydata")
    logger.debug('signdata - start')
    if request.method=='POST':
        #try:
        logger.debug('Отримую тіло запита')
        body = request.get_json()

        logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False  ))
        sgData = body["signdata"]
        sgSign = body["sign"] 
        logger.debug('Викликаю функцію перевірки підпису IIT')
        res=eds.VerifyData(sgData, sgSign)
        logger.debug('Вертаю результат:' +  json.dumps(  res, ensure_ascii=False  ))
        if res["ok"]==False:
            raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/verifydata process signature',status_code=422, payload = {"code": res["errorCode"], "description": res["error"] } )                
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}

    else:
        logger.debug('возвращаю ошибку о недопустимомо методе')
        res={}
        res["ok"]=False
        res["status"] = 404
        res["description"] = "Метод не найден!"
        return json.dumps( res ), 404, {'Content-Type':'application/json'}        


# ================================================
# Перевірити пдпис. Підпис окремо, дані окремо
# {"signdata":"", "sign":""}
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ================================================
@application.route("/api/verifyhash", methods=["POST"])
def verifyhash():
    """
        Перевірити дані, що були Підписаний hash
    """
    logger=logging.getLogger(__name__).getChild("verifyhash")
    logger.debug('verifyhash - start')
    if request.method=='POST':
        
        logger.debug('Отримую тіло запита')
        body = request.get_json()

        logger.debug('розбираю тіло запита' + json.dumps(  body , ensure_ascii=False ))
        sgData = body["signhash"]
        sgSign = body["sign"] 
        logger.debug('Викликаю функцію перевірки підпису IIT')
        res=eds.VerifyHash(sgData, sgSign)
        logger.debug('Вертаю результат:' +  json.dumps(  res , ensure_ascii=False ))
        if res["ok"]==False:
            raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/verifyhash process signature',status_code=422, payload = {"code": res["errorCode"], "description": res["error"] } )                
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}
   

@application.route("/api/hash", methods=["POST"])
def hash():
    """
        Перевірити дані, що були Підписаний hash
    """
    logger=logging.getLogger(__name__).getChild("hash")
    logger.debug('verifyhash - start')
    if request.method=='POST':
        logger.debug('Отримую тіло запита')
        body = request.get_json()

        logger.debug('розбираю тіло запита' + json.dumps(  body, ensure_ascii=False  ))
        sgData = body["data"]
        logger.debug('Викликаю функцію перевірки підпису IIT')
        res=eds.Hash(sgData)
        logger.debug('Вертаю результат:' +  json.dumps(  res , ensure_ascii=False ))
        if res["ok"]==False:
            raise IttLibError( "IitLibraryError",   [res["error"]], target='/api/hash process signature',status_code=422, payload = {"code": res["errorCode"], "description": res["error"] } )                
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}

@application.route("/api/unpack", methods=["POST"])
def unpack_data():
    logger=logging.getLogger(__name__).getChild("unpack_data")
    body_dict = dict()
    l_step='start'
    logger.debug(l_step)
    l_step='Отримую тіло запита'
    logger.debug(l_step)
    if 'multipart/form-data' in request.content_type :
        l_step='Отримано multipart/form-data та перетворюю її в dictionary'
        logger.debug(l_step)
        body_dict = request.form.to_dict(flat=True)
    elif 'application/x-www-form-urlencoded' in  request.content_type :  
        l_step='Отримано application/x-www-form-urlencoded'
        logger.debug(l_step)
        requestData = request.get_data()
        if len(requestData) == 0:
            l_step='Отримано масив даних 0-го розміру'
            logger.debug(l_step)  
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "Розмір отриманих даних = 0", target='unpack_data',status_code=422, payload = {"code": "recdata_0_size", "description": "Розмір отриманих даних = 0" } )
            
        l_step='Декодую з urlencoded'
        logger.debug(l_step)  
        datastr=requestData.decode(encoding="utf-8")
        datastrdc=unquote(datastr)
        requestData=None
        datastr=None
        l_step='Розбираю отримані дані по ключах'
        logger.debug(l_step)  

        x=datastrdc.split("&")
        for i in x:
            try:
                a,b=i.split(":")
                body_dict[a]=b
            except Exception as e:          
                ex_proc=exProcessor(e)
                ex_name=ex_proc["ex_name"]
                ex_dsc=ex_proc["ex_dsc"]
                raise AppError( "AppError",  "DecriptionProcessingError", target="unpack_data",status_code=422, payload = {"code": ex_name, "description": ex_dsc })   
    
    l_step='Перевіряю наявність обов!язкових ключів у запиті '
    logger.debug(l_step)           
    if not "SignData" in body_dict:
        raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [SignData!]", target='unpack_data',status_code=422, payload = {"code": "NoKey", "description": "Не вказано обов'язковий ключ в запиті" } )
    if not "FileData" in body_dict:
        raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [FileData!]", target='unpack_data',status_code=422, payload = {"code": "NoKey", "description": "Не вказано обов'язковий ключ в запиті" } )
      
    logger.debug('Викликаю функцію перевірки підпису IIT ' )
    resinfo=eds.VerifyData( body_dict["FileData"], body_dict["SignData"])

    if resinfo["ok"]==False:
        logger.debug('Вертаю помилку' )
        raise IttLibError( "IitLibraryError",   resinfo["error"], target='/api/unpack process signature',status_code=422, payload = {"code": resinfo["errorCode"], "description": resinfo["error"] } )                
    
    logger.debug('Вертаю результат:' +  json.dumps(  resinfo , ensure_ascii=False ))
    return json.dumps(  resinfo , ensure_ascii=False), 200, {'Content-Type':'application/json'}


# ================================================
# RFC-5577 Підписати запит для АСВП
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ================================================
@application.route("/api/aswpsign", methods=["POST"])
def aswpsign():
    """
        Підписати дані для АСВП RFC-5577
    """
    logger=logging.getLogger(__name__).getChild("aswpsign")
    l_step='start'
    logger.debug(l_step)
    if request.method=='POST':
        l_step='Отримую тіло запита'
        try:
            l_step='отримую тіло запиту'
            logger.debug(l_step)
            body = request.get_json()
            l_step='Розбираю тіло запиту в dict' + json.dumps(  body , ensure_ascii=False )
            logger.debug(l_step)
            body_dict = dict(body)
        except Exception as e:
            ex_code=e.code
            ex_name=e.name
            ex_dsc=e.description
            raise InvalidAPIUsage(  "InvalidAPIRequest",  "Помилка при отриманні запиту", target="aswpsign", status_code=ex_code, payload = {"code": ex_name, "description": ex_dsc} )              

        l_step='Перевіряю наявність [signdata]'
        logger.debug(l_step)
        if not 'signdata' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [signdata]", target="aswpsign",status_code=422, payload = {"code": "NoKey", "description": l_step } )
        
        sgData = body["signdata"]
        l_step='Викликаю функцію накладання підпису IIT'
        logger.debug(l_step)
        res=eds.SignData(sgData)
        if res["ok"]==False:
            raise IttLibError( "IitLibraryError",   res["error"], target="aswpsign" ,status_code=500, payload = {"code": res["errorCode"], "description": res["error"], "trace": res["trace"] } )    
     
        l_step='Готую результат:' +  json.dumps(  res , ensure_ascii=False )
        logger.debug(l_step)
        retres={}
        retres["payload"]=body["signdata"]
        retres["signature"]=res["signature"]

        l_step='Повертаю результат:' +  json.dumps(  res , ensure_ascii=False )
        logger.debug(l_step)
        return json.dumps(  retres ), 200, {'Content-Type':'application/json'}
    else:
        l_step="Не допустимий метод!"
        logger.debug(l_step)
        raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод: " + request.method, target='/api/aswpsign',status_code=404 )


# ================================================
# RFC-5577 Перевірити підпис на відповідь від АСВП
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ================================================
@application.route("/api/aswpverify", methods=["POST"])
def aswpverify():
    """
        Перевірити підпис на даних для АСВП RFC-5577
    """
    logger=logging.getLogger(__name__).getChild("aswpverify")
    
    l_step=''
    logger.debug(l_step)
    if request.method=='POST':
        l_step='Отримую тіло запита'
        try:
            l_step='отримую тіло запиту'
            logger.debug(l_step)
            body = request.get_json()
            l_step='Розбираю тіло запиту в dict' + json.dumps(  body , ensure_ascii=False )
            logger.debug(l_step)
            body_dict = dict(body)
        except Exception as e:
            ex_code=e.code
            ex_name=e.name
            ex_dsc=e.description
            raise InvalidAPIUsage(  "InvalidAPIRequest",  "Помилка при отриманні запиту", target="aswpverify", status_code=ex_code, payload = {"code": ex_name, "description": ex_dsc} )              

        l_step='Перевіряю наявність [payload]'
        logger.debug(l_step)
        if not 'payload' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [payload]", target="aswpverify",status_code=422, payload = {"code": "NoKey", "description": l_step } )

        l_step='Перевіряю наявність [signature]'
        logger.debug(l_step)
        if not 'signature' in body_dict:
            raise InvalidAPIUsage( "InvalidAPIRequestParams",  "No key [signature]", target="aswpverify",status_code=422, payload = {"code": "NoKey", "description": l_step } )

        sgData = body["payload"]
        sgSignature = body["signature"]

        l_step='Перетворюю [payload] в JSON-object'
        logger.debug(l_step)
        try:
            pzData=base64.b64decode(sgData)
            pzDataStr=pzData.decode('utf-8')
            l_step='Перетворюю [payload] в JSON-object. String= ' + pzDataStr
            logger.debug(l_step)
            

            pzDataObj=json.loads(pzDataStr)
            
        except Exception as e:       
                ex_type, ex_value, ex_traceback = sys.exc_info()
                trace_back = traceback.extract_tb(ex_traceback)
                stack_trace = list()
                for trace in trace_back:
                    stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
                #ex_code=e.code
                ex_name=ex_type.__name__
                ex_dsc=ex_value.args[0]
                raise InvalidAPIUsage( "InvalidAPIRequestParams",  'Помилка при [' + l_step + ']', target="aswpverify" ,status_code=422, payload = {"code": ex_name, "description": ex_dsc, "trace": stack_trace } )    

        l_step='Декодую з base64 [signature] '
        logger.debug(l_step)
        try:
            sgSignatureB=base64.b64decode(sgSignature)
        except Exception as e:       
                ex_type, ex_value, ex_traceback = sys.exc_info()
                trace_back = traceback.extract_tb(ex_traceback)
                stack_trace = list()
                for trace in trace_back:
                    stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
                #ex_code=e.code
                ex_name=ex_type.__name__
                ex_dsc=ex_value.args[0]
                raise InvalidAPIUsage( "InvalidAPIRequestParams",  'Помилка при [' + l_step + ']', target="aswpverify" ,status_code=422, payload = {"code": ex_name, "description": ex_dsc, "trace": stack_trace } )    
       
        l_step='Викликаю функцію підпису IIT'
        logger.debug(l_step)
        
        res=eds.VerifyData( sgData, sgSignature )
        if res["ok"]==False:
                raise IttLibError( "IitLibraryError-VerifyData",   res["error"], target="aswpverify" ,status_code=500, payload = {"code": res["errorCode"], "description": res["error"], "trace": res["trace"] } )    
        l_step='Результат перевірки підпису IIT:' +  json.dumps(  res )
        logger.debug(l_step)
        res["payloaddata"]=pzDataObj
        l_step='Повертаю результат:' +  json.dumps(  res , ensure_ascii=False )
        logger.debug(l_step)
        return json.dumps(  res ), 200, {'Content-Type':'application/json'}
    else:
        l_step="Не допустимий метод!"
        logger.debug(l_step)
        raise UnexpectedHttpMethod( "UnexpectedHttpMethod",  "Не допустимий http метод: " + request.method, target='/api/aswpsign',status_code=404 )


# ========================================================
#  прочитати KeyMedias
#  
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@application.route("/api/keymedia", methods=["GET"])
def getkeymedia():
    """
        Прочитати дані носіїв секретних ключів
    """
    logger=logging.getLogger(__name__).getChild("getkeymedia")
    logger.debug('readkeymedia - start')
    filtername = request.args.get('filter')
    if filtername == None:
        logger.debug('Вертаю результат:' +  json.dumps(  i_devlist , ensure_ascii=False  ))
        return json.dumps(  i_devlist ), 200, {'Content-Type':'application/json'}
    elif filtername == 'active':    
        logger.debug('Fileter =' +filtername)
        dict_list=i_devlist["devlist"]
        active_list = []
        for item in  dict_list:
            devs=item["devices"]
            if len(devs)!=0 :
                active_list.append(item) 
        logger.debug('Вертаю фільтрований результат:' +  json.dumps(  active_list , ensure_ascii=False ))
        return json.dumps(  active_list ), 200, {'Content-Type':'application/json'}
    else:    
        logger.debug('Вертаю результат для не допутимого фільтра:' +  json.dumps(  i_devlist , ensure_ascii=False ))
        return json.dumps(  i_devlist ), 200, {'Content-Type':'application/json'}

@application.route("/api/libsetting", methods=["GET"])
def libsetting():
    """
        Прочитати насторйки бібліотеки
    """
    logger=logging.getLogger(__name__).getChild("libsetting")
    logger.debug('readkeymedia - start')

    res=eds.readLibsettings()
    return json.dumps(  res ), 200, {'Content-Type':'application/json'}

def redlst():
    """
        Обробка команд REDIS
    """
    logger=logging.getLogger(__name__).getChild("redlst")
    while True:
        gevent.sleep(4.0)
        lpid = os.getpid()
        logger.debug( str(lpid) + " : timeout ")
        for message in sub.listen():
            if message['type'] != 'message':
                continue
            logger.debug( "Pid: "+ str(lpid) + " - Get message: " +  json.dumps( message['data'] , ensure_ascii=False ) ) 
            cmdobj =  json.loads(  message['data'] )
            cmd = cmdobj["cmd"]

            if cmd == "readkey":
                logger.debug("Запкскаю команду: "+ cmd)
                logger.debug("Параметри: "+ json.dumps( cmdobj["params"], ensure_ascii=False)  )
                cmdprm=cmdobj["params"]
                res=aureadkey(  cmdprm["szUsername"]  , cmdprm["szPassword"], cmdprm["dwDevIndex"], cmdprm["dwTypeIndex"] )
                logger.debug("Завантажено ключ з гряда: " + json.dumps( res , ensure_ascii=False )  )
            elif  cmd == "readkeyfile":
                logger.debug("Commbd: "+ cmd)
                logger.debug("Запкскаю команду: "+ cmd)
                logger.debug("Параметри: "+ json.dumps( cmdobj["params"], ensure_ascii=False)  )
                cmdprm=cmdobj["params"]

                res=aureadkeyfile( cmdprm["szPassword"], cmdprm["szPth"] )
                logger.debug("Завантажено ключ з файла: " + json.dumps( res, ensure_ascii=False )  )
            elif  cmd == "resetkey":
                logger.debug("Commbd: "+ cmd)
                logger.debug("Запкскаю команду: "+ cmd)
                logger.debug("Параметри: "+ json.dumps( cmdobj["params"] , ensure_ascii=False)  )
                cmdprm=cmdobj["params"]
                res=auresetPrivateKey()
                logger.debug("Скинути ключ: " + json.dumps( res , ensure_ascii=False)  )

 
gevent.spawn(redlst)

