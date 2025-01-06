import os
import logging
import base64
from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator


class CouchDB:
    def __init__(self, xlogger):

        self.plogger=xlogger
        self.DB_AUTH_TYPE = os.getenv( "COUCHDB_AUTH_TYPE"  ,"COUCHDB_SESSION")
        self.DB_URL = os.getenv(  "COUCHDB_URL" , "http://localhost:5984")
        self.DB_USERNAME = os.getenv( "COUCHDB_USERNAME"  ,"devadm")
        self.DB_PASSWORD = os.getenv(  "COUCHDB_PASSWORD" ,"qq")
        self.service = None
        self.authenticator = None

        self.connect()

    def connect(self):
        logger=logging.getLogger(self.plogger).getChild( f"{__name__}:Connect")
        self.authenticator = CouchDbSessionAuthenticator( self.DB_USERNAME, self.DB_PASSWORD, disable_ssl_verification=True)
        self.service = CloudantV1(authenticator=self.authenticator)
        self.service.set_service_url( self.DB_URL )
        dbserverinfo = self.service.get_server_information().get_result()
        logger.debug(f"Інформація про сервер:  {dbserverinfo}")

    def checkDataBases(self):
        logger=logging.getLogger(self.plogger).getChild( f"{__name__}:createDataBases")
        dbList = self.service.get_all_dbs().get_result()
        logger.debug(f"Отримали список DB:  ")
        logger.debug(f"Список баз даних сервера:  {dbList}")
        isDBUsers=False
        DBUsers=None
        isDBImage=False
        DBImage=None
        for dbitem in dbList:
            if dbitem == '_users':
                isDBUsers=True
            if dbitem=='dbimage':
                isDBImage=True

        if not isDBUsers:
            DBUsers = self.service.put_database(db='_users', partitioned=False).get_result()
            logger.debug(f"Створено БД: {DBUsers}")
            if DBUsers['ok']:
                logger.debug(f"Створено БД: _users створена успішно! ")
            else:
                logger.debug(f"Створено БД: _users НЕ створено !!!! ")    

        if not isDBImage:
            DBImage = self.service.put_database(db='dbimage', partitioned=False).get_result()
            logger.debug(f"Створено БД {DBImage}")
            if DBImage['ok']:
                logger.debug(f"Створено БД: dbimage створена успішно! ")
            else:
                logger.debug(f"Створено БД: dbimage НЕ створено !!!! ")    
        
        dbList = self.service.get_all_dbs().get_result()
        for dbitem in dbList:
            logger.debug(f"Після створення DB {dbitem}")
        return dbList    

    def saveImage(self, img, imgprops):
        imgdsc={}
        uuid=None
        img_b = base64.b64encode(   img   )
        imgb64=img_b.decode('utf-8')

        response = self.service.get_uuids(count=1).get_result()
        uuid=response["uuids"][0]

        imgdsc["_id"]=uuid
        imgdsc["typedoc"]="GREY"
        imgdsc["filename"]=imgprops["filename"]
        imgdsc["description"]=imgprops["filedsc"]

        bino={}   
        bino["data"]=imgb64
        bino["content_type"]=imgprops["contenttype"]
        fl={}
        fl[imgprops["filename"]]=bino

        imgdsc["_attachments"]=fl
        doc = self.service.post_document(db='dbimage', document=imgdsc).get_result()  
        return  doc  
    
    def readImage(self, docid):
        doc = self.service.get_document(db='dbimage',doc_id=docid).get_result()

        attachment = self.service.get_attachment( db='dbimage', doc_id=doc["_id"], attachment_name=doc["filename"] ).get_result().content
        return attachment
    
    def imageList(self):
        imgList = self.service.post_find(
                                        db='dbimage',
                                        selector={"typedoc": {"$eq": "GREY"}},
                                        fields=["_id","filename","typedoc","correlation_id"],
                                        limit=3
                                        ).get_result()
        return imgList     

    
   

