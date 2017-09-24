from nmv1 import *
import json
import csv
import datetime
import time
import os.path
import logging
from logging.handlers import RotatingFileHandler
import shutil
from pexpect import pxssh
import pexpect
import getpass
import ast
import pymongo
import re
import pandas
from flask import Flask, render_template, request
from flask import jsonify
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

logger =  logging.getLogger("Rotating Log")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(os.getcwd()+"/MonitorEngine.log",maxBytes=5000000,backupCount=25)
formatter = logging.Formatter('%(asctime)s > %(levelname)s > %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
#logger.propagate = False # DISABLE LOG STDOUT

logger.info("Starting MonitoringEngine")

app = Flask(__name__)

### PAGE 1 START ####
class score_gen():

    def __init__(self):
        logger.info("Scoring Object Insiated...")
    
    def mongo_search_score(self,INID,session,mdb):
        try:
            logger.debug("Mongo search score for:"+str(str(INID)+" "+str(session)))
            mdb_out = mdb['OUTPUT']
            all_data = mdb_out.find({"INID":INID,"SESSION":session})
            for single_host in all_data:
                try:
                    #print single_host
                    IP = single_host.get("IP")
                    logger.debug("mongo_search_score > Starting score for > "+str(IP))
                    mon_objects = single_host.get("Objects")
                    obj_index = -1
                    for mon_obj in mon_objects:
                        obj_index = obj_index + 1
                        ranks = mon_obj.get("rank")
                        elmt_id = mon_obj.get("id")
                        last_score = 0
                        for rank in ranks:
                            #print rank
                            custom_query = rank.get("regex")
                            score = rank.get("score")
                            dafault_query = {"INID":INID,"SESSION":session,"IP":IP}
                            #print custom_query
                            new_dict = {"out."+key: value for key, value in custom_query.items()}
                            #print new_dict
                            new_dict.update({"id":elmt_id})
                            elmts = {"$elemMatch":new_dict}
                            dafault_query.update({'Objects':elmts})
                            logger.debug("mongo_search_score > searching DB for:"+str(dafault_query))
                            queryout = mdb_out.find_one(dafault_query,{"_id":0,"TD":0})
                            #print queryout
                            if queryout == None:
                                logger.debug("mongo_search_score > default_query > Pattern Not matched")
                            else:
                                logger.debug("mongo_search_score > default_query > Pattern Matched")
                                # Update very lowest score in rank pattern
                                if last_score < score:
                                    last_score = score
                                #tmpdesc = hostname+" "+ip+" "+str(emon)+" "+str(etype)+" "+str(ename)+" "+str(custom_query)+" "+str(last_score)+" "+str(queryout.get("OUT"))
                                #desc = desc+"\n"+str(tmpdesc)
                                #print "Issue pattern matched > ",desc
                                d = dafault_query,{"$set": {"Objects.$"+".score":last_score}}
                                logger.debug("mongo_search_score > updating score >"+str(d))
                                mdb_out.update(dafault_query,{"$set": {"Objects.$"+".score":last_score}})
                except Exception as e:
                    logger.exception("mongo_search_score")
        except Exception as e:
            logger.exception("mongo_search_score")

### PAGE 1 END ####

class main_model():

    def __init__(self):
        #Saving ssh session
        self.ssh_ses = {}

    def login(self,hostname='',auth=[],logpath="default_log.txt",login_timeout=10,etimeout=6):
        # Login to NPCI device , "enable" password check disabled because of aaa conf in NPCI
        if len(auth) > 0:
            for au in auth:
                logger.info("Trying to Login:"+hostname)
                return_typ = None
                username = au.get("username")
                password = au.get("password")
                try:
                    s = pxssh.pxssh(options={
                                    "StrictHostKeyChecking": "no",
                                    "UserKnownHostsFile": "/dev/null"},timeout=login_timeout)

                    s.login(hostname, username, password,auto_prompt_reset=False,login_timeout=login_timeout)
                    s.logfile = open(logpath+"_"+str(hostname)+".txt", "ab")
                    # Send enter to get router prompt to check login success
                    s.sendline('')
                    ex = ["#",">","\$",pexpect.TIMEOUT]
                    # expecting cisco , juniper , fortigate prompt 
                    match_ex = s.expect(ex,timeout=etimeout)
                    login_chk = s.before.strip()
                    if len(login_chk) > 0 and match_ex < 3:
                        host_name = login_chk.decode("utf-8")
                        aftr = s.after
                        if type(aftr) == str:
                            host_name = host_name+aftr.strip().decode("utf-8")
                        logger.info("Login Success :"+hostname+":"+host_name)
                        return s,host_name
                    else:
                        logger.info("Not able to reach device:"+hostname)
                    return "TIMEOUT"
                except pxssh.ExceptionPxssh as e:
                    err = str(e)
                    if err.find("password refused") != -1:
                        logger.info("Login Failed:"+hostname)
                        return_typ = "LOGINFAIL"
                    else:
                        logger.info("Login Error>"+err+":"+hostname)
                        return "TIMEOUT"
                except Exception as e:
                    logger.exception("login")
                    return "TIMEOUT"
            return return_typ
        
    def get_ssh_ses(self,IP,Authentication,timeout,dir_path):
        try:
            #ses = self.ssh_ses.get(IP)  # Not required to store session
            ses = None
            live_ses = False
            if ses == None:
                #print("SSH SESSION NOT FOUND FOR "+str(IP))
                live_ses = False
            else:
                # Check ssh session
                if len(ses) == 2:
                    # Previous session is valid , Checking Live
                    ses[0].sendline()
                    if ses[0].expect([ses[1],pxssh.TIMEOUT],timeout=20) == 0:
                        live_ses = True
        except:
            live_ses = False

        if live_ses != True:
            ses = self.login(IP,Authentication,dir_path)
            if type(ses) != str and ses != None:
                #self.ssh_ses.update({IP:ses}) # Not required to store session
                return ses
        return ses

    def self_check(self,IP,Hostname,dir_path,element):
        try:
            result = {}
            einput = element.get("input")
            username = einput.get("username")
            password = einput.get("password")
            timeout = einput.get("timeout")
            etype = einput.get("type")
            # Get SSH session
            auth = {"username":username,"password":password}
            sess = self.get_ssh_ses(IP,[auth],timeout,dir_path)
            print type(sess)
            if type(sess) == tuple :
                # SSH login success
                result.update({"status":"reachable"})
                if etype == "cisco":
                    sess[0].sendline("terminal length 0")
            else:
                # SSH login failed
                logger.info("Failed >"+str(Hostname)+" "+str(IP)+" Reasion>"+str(sess))
                if sess == "LOGINFAIL":
                    result.update({"status":"Authentication Failed"})
                else:
                    result.update({"status":"timeout"}) 
            #Get snmp session
            return result,sess
        except Exception as e:
            logger.exception("self_check")

    def device_check(self,host_objects,dir_path):
        try:

            Monitoring_obj = host_objects.get("Objects")
            ID = host_objects.get("ID")
            Hostname = host_objects.get("Hostname")
            IP = host_objects.get("IP")

            if Monitoring_obj == None:
                logger.error("device_check None Objects")
                return None

            continue_next = False
            Monitoring_obj = sorted(Monitoring_obj, key=lambda k: k['id'])
            for element in Monitoring_obj:
                    myid = element.get("id")
                    # Self check
                    if myid == 0:
                        out_session = self.self_check(IP,Hostname,dir_path,element)
                        if out_session != None:
                            out = out_session[0]
                            session = out_session[1]
                            # Removing username and password
                            element.update({"input":""})
                            element.update({"out":out})
                            if out.get("status") == "reachable":
                                continue_next = True
                            else:
                                # Only return self element output (device down)
                                return [element]
                        else:
                            logger.error("device_check self_check failed")
                    elif continue_next == True:
                        et = element.get("function")
                        out = globals()[et](session,element)
                        element.update({"out":out})

            return Monitoring_obj
        except Exception as e:
            logger.exception("device_check")

    def single_host(self,host_objects,dir_path):

        try:
            IP = host_objects.get("IP")
            try:
                mongoc = pymongo.MongoClient('localhost', 27017)
                mdb = mongoc['LIVE']
                mcollection = mdb['SESSION']
                mcollection.update({"_id":1,"STATUS.IP":IP},{ "$set": { "STATUS.$.TYPE" : "Running" } })
                mongoc.close()
            except Exception as e:
                logger.exception("single_host DB")

            jout = self.device_check(host_objects,dir_path)
            if type(jout) == None:
                logger.error("single_host return non list objects")
                jout = []
            host_objects.update({"Objects":jout})
            return host_objects
        
        except Exception as e:
            logger.exception("single_host")

    def start_run(self,input_file_path,jobname,apprentice = 5):
        try:
            # start create DB function
            self.jobname = jobname
            TD = datetime.datetime.now()
            if self.mongdb(TD,"xls",input_file_path) == True:
                pass;
            else:
                logger.error("STOPPED")
                return
            session = 0
            for y in range(1):
                tim = time.strftime('%Y-%m-%d %H:%M:%S')
                session = session + 1
                logger.info("STARTING SESSION >"+str(session))
                mcollection = self.mdb['SESSION']
                sesout = mcollection.find_one({"_id":1})
                INID = sesout.get("INID")

                #Get INPUT based on INID
                mcollection = self.mdb['INPUT']
                all_data = mcollection.find({"INID":INID})
                jobname = jobname.replace(":","-")
                dir_path = os.path.join(os.getcwd(),"divlog")
                dir_path = os.path.join(dir_path,jobname)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                dir_path = os.path.join(dir_path,jobname)
                logger.info("Apprentice>"+str(apprentice))
                # Share work to threads
                with ThreadPoolExecutor(max_workers=apprentice) as executor:
                    futures = [executor.submit(self.single_host, row,dir_path) for row in all_data]
                    for future in as_completed(futures):
                        try:
                            jout = future.result()
                            #INSERT OUTPUT TO DB
                            jout.update({"SESSION":int(session),"TD":TD,"JOBNAME":jobname})
                            mcollection = self.mdb['OUTPUT']
                            mcollection.insert(jout)
                        except Exception as e:
                            logger.exception("start_run")

                        try:
                            #Update session table
                            mcollection = self.mdb['SESSION']
                            mcollection.update({"_id":1,"STATUS.IP":jout.get("IP")},{ "$set": { "STATUS.$.TYPE" : "Completed" } })
                        except Exception as e:
                            logger.exception("start_run db")
                        
                
                #Start Scoring
                logger.info("Scoring Started")
                self.mongo_search_score(INID,session,self.mdb)
                logger.info("Scoring Completed")
                #UPDATE CURRENT SESSION
                mcollection = self.mdb['SESSION']
                mcollection.update({"_id":1},{"$set":{"SESSION":session}})
                mcollection = self.mdb['HISTORY']
                mcollection.insert({"INID":int(INID),"SESSION":int(session),"TD":TD,"JOBNAME":jobname})
        except Exception as e:
            logger.exception("start_run")

    def xls_input(self,filename):
        # Ready XLS input file and formate to JSON for inserting to MongoDB
        try:
            xl = pandas.ExcelFile(filename)
            # Ready 'input' worksheet
            df1 = xl.parse('input')
            IP = list(set((df1.get("IP"))))
            full_list = []
            authentication = None
            for inx , i in enumerate(IP):
                elmt_id = 0
                local_list = []
                xx = ""
                for index, row in df1.iterrows():
                    if row["IP"] == i:
                        if row["function"] == "self_check":
                            # Set id zero for self check , and get authentication details
                            elmt_id2 = 0
                            authentication = row["input"]
                        else:
                            elmt_id = elmt_id + 1
                            elmt_id2 = elmt_id
                        a = {"id":elmt_id2, "function":row["function"],"input": json.loads(row["input"]),"rank": json.loads(row["rank"])}
                        local_list.append(a)
                        xx = row
                full_list.append({"Hostname": str(xx["Hostname"]),"IP":str(xx["IP"]),"Authentication":json.loads(authentication),"Objects":local_list})
            return full_list
        except Exception as e:
            logger.exception("xls_input")
    
    def mongdb(self,TD,input="xls",filepath=None):
        try:
            INID  = 1
            if input == "xls":
                csv_data = self.xls_input(filepath)
                if csv_data == None or len(csv_data) == 0:
                    logger.error("No valid XLS input")
                    return None
            else:
                return None
                #csv_data = list(csv.DictReader(open('input.csv')))
            
            #Get INID from SESSION
            mcollection = self.mdb['SESSION']
            session = (list(mcollection.find()))
            if len(session) > 0:
                INID = session[0].get("INID")
                if INID != None:
                    INID = INID+1
                    
            # ADD INID in INPUT collection
            for d in csv_data:
                # Json loads used to convert string to array object
                d.update({"INID":INID,"Objects":d.get("Objects")})

            mcollection = self.mdb['INPUT']
            mcollection.insert(csv_data)

            ses = mcollection.find({"INID":INID},{"Hostname":1,"IP":1,"_id":0})
            # Add or Update new session in SESSION collection
            mcollection = self.mdb['SESSION']
            #print list(ses)
            mcollection.update({"_id":1},{"_id":1,"INID":INID,"SESSION":0,"JOBNAME":self.jobname,"STATUS":list(ses),"STARTDATE":TD})
            logger.info("SESSION UPDATED , INID = "+str(INID))
            
            #self.mongoc.close()
            return True
        except Exception as e:
            logger.exception("mongdb")
    
    def main_run(self,filepath,jobname,apprentice):
        # connect to LIVE database
        self.mongoc = pymongo.MongoClient('localhost', 27017)
        self.mdb = self.mongoc['LIVE']
        logger.info("Connected to 'LIVE' database...")

        # Insitate Score Me object
        scor = score_gen()
        self.mongo_search_score = scor.mongo_search_score

        logger.info("Starting Job ===============> "+str(jobname))
        self.start_run(filepath,jobname,apprentice)


if __name__ == '__main__':
    pass;
    logger.info("Manual Mode Running")
    #m = main_model()
    #m.main_run("/home/gow/network_snap/input_file/06-August-08_41_07-GNS.xlsx","TESTTTT",5)