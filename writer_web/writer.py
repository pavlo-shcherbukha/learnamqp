import os
import time 
import json
import sys
#from receiver_web.rabbitmq import RabbitMQ
import logging
import writer_web.shjsonformatter
from datetime import datetime,timedelta
import pika
import os

from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator

from writer_web.couchdb import CouchDB

logger = logging.getLogger(__name__)
img_gray = None
img_prop = None

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
handler.setFormatter( writer_web.shjsonformatter.JSONFormatter())

logger.addHandler(handler)

logger.debug("debug message")


def read_image(file_path):
    with open(file_path, "rb") as file:
        image_bytes = file.read()
    return image_bytes

def save_modified_image(file_path, modified_bytes):
    with open(file_path, "wb") as file:
        file.write(modified_bytes)

def changeext(file_name, new_ext):
    ext = '.'+ os.path.realpath(file_name).split('.')[-1:][0]
    filefinal = file_name.replace(ext,'')
    filefinal = filefinal + '.zip'
    return filefinal



def main():
    logger.debug("Читаю налаштування")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    logger.debug("Підключаюся до Rabbit MQ")
    #connection = pika.BlockingConnection(pika.ConnectionParameters(host))

    credentials = pika.PlainCredentials(  username=user, password=password )
    parameters = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
    connection = pika.BlockingConnection(parameters)


    channel = connection.channel()

    logger.debug("Налаштовую черги")
    q_name_in="test_dbwrt"
    
    logger.debug("Налаштовую канал для читання повідомтлень")
    channel.queue_declare(queue=q_name_in, durable=True) 

    logger.debug("Підключаю базу даних")
    couchd = CouchDB( __name__)
    dblist=couchd.checkDataBases()
    logger.debug(f"Database lists: {dblist}")

    try:
        logger.debug("Connection to RabbitMQ established successfully.")
        def callback(ch, method, properties, body):
            """
                Обробка отриманого повідомлення
            """
            logger.debug(f"Received message: ====================================================================================")
            logger.debug(f"Received message: {properties}")
            logger.debug(f" app-id {properties.app_id}")
            logger.debug(f" custom headers: {properties.headers}")
            logger.debug(f"Received message: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            imgprops={}
            imgprops["filename"]=properties.headers["filename"]
            imgprops["filedsc"]=properties.headers["filedescription"]
            imgprops["contenttype"]=properties.content_type
            imgprops["contentecoding"]=properties.content_encoding
            imgprops["correlation_id"]=properties.correlation_id
            logger.debug("Записую образ в базу даних")
            doccrts=couchd.saveImage(body, imgprops )
            logger.debug(f"Результат запису в БД {doccrts}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

            

        logger.debug(f"Налаштовую читання повідомлень з черги")
        channel.basic_consume(queue=q_name_in, on_message_callback=callback)

        logger.debug(f"Читаю повідомлення з черги")
        channel.start_consuming()

   

        
        
        
        
        #logger.debug(f"Читаю COUCHDB SERVICE{response}")
        logger.debug(f"Читаю COUCHDBи OOOOO")


        
      
    except Exception as e:
        logger.debug(f"Failed to establish connection to RabbitMQ: {e}")
        sys.exit(1)
    #finally:
        #rabbitmq.close()
    

