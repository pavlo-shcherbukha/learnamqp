import os
import time 
import json
import sys
#from receiver_web.rabbitmq import RabbitMQ
import logging
import receiver_web.shjsonformatter
from datetime import datetime,timedelta
import cv2
import numpy as np 
import pika
import os

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
handler.setFormatter( receiver_web.shjsonformatter.JSONFormatter())

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
    filefinal = filefinal + '.png'
    return filefinal



def imagedecode(imgbarray):
    """
        Перекодувати зображення в сірий колір і як .png
    """
    # Перекодуб вмасив байт
    img = np.asarray(bytearray( imgbarray ), dtype="uint8") 
    # Пеоетворюю в CV2 image
    image = cv2.imdecode(img, cv2.IMREAD_COLOR) 
    # пробимо зображення сірим
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #Перетворюю image як масив байт як .png
    gray_image_b = cv2.imencode(".png", gray_image)[1].tobytes() 
    #save_modified_image("./result2.bmp", gray_image_b)
    # повертаю результат 
    return gray_image_b




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
    q_name_in="test_queue"
    q_name_out="test_dbwrt"
    logger.debug("Налаштовую канал для читання повідомтлень")
    channel.queue_declare(queue=q_name_in, durable=True) 

    logger.debug("Налаштовую канал для публікації повідомтлень")
    channel.queue_declare(queue=q_name_out, durable=True)

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
            
            logger.debug(f"Декодую зображення і перетворюю в масив банй")
            processed_message = imagedecode(body)

            logger.debug(f"Публікую повідомлення в чергу")
            cust_headers_in = properties.headers;
            cust_headers = {"filename": changeext(  cust_headers_in["filename"] , ".png"), "filedescription": cust_headers_in["filedescription"]}
            msgprop = {
                "content_type": 'image/png',
                "content_encoding": properties.content_encoding,
                "headers": cust_headers,
                "delivery_mode": 2,
                "correlation_id": properties.correlation_id,
                "app_id": "receiver_web"
            }   

            channel.basic_publish(exchange='', routing_key=q_name_out, body=processed_message, properties=pika.BasicProperties(
                            content_encoding=msgprop["content_encoding"],
                            content_type=msgprop["content_type"],
                            headers={"filename":  changeext(  cust_headers_in["filename"] , ".png"), "filedescription": cust_headers_in["filedescription"] },
                            delivery_mode=2,
                            correlation_id=msgprop["correlation_id"],
                            app_id= "receiver_web")
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.debug(f"Публікую повідомлення в чергу ---- OKKKKKK")

        logger.debug(f"Налаштовую читання повідомлень з черги")
        channel.basic_consume(queue=q_name_in, on_message_callback=callback)

        logger.debug(f"Читаю повідомлення з черги")
        channel.start_consuming()

        
      
    except Exception as e:
        logger.debug(f"Failed to establish connection to RabbitMQ: {e}")
        sys.exit(1)
    #finally:
        #rabbitmq.close()
    

