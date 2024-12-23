import os
import time 
import json
import sys
from receiver_web.rabbitmq import RabbitMQ
import logging
import receiver_web.shjsonformatter
from datetime import datetime,timedelta


logger = logging.getLogger(__name__)

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

def callback(ch, method, properties, body):
    logger.debug(f"Received message: {body}")


def main():
    rabbitmq = RabbitMQ()
    try:
        logger.debug("Connection to RabbitMQ established successfully.")
        rabbitmq.consume(queue_name="test_queue", callback=callback)
    except Exception as e:
        logger.debug(f"Failed to establish connection to RabbitMQ: {e}")
        sys.exit(1)
    finally:
        rabbitmq.close()

def mainlog():
    logger.debug("DEBUGGGGG")
    logger.info("INFOOOOOO")


