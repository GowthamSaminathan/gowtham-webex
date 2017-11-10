import json
import sys
import csv
import datetime
import time
import os.path
import logging
from logging.handlers import RotatingFileHandler
import shutil
import getpass
import ast
import re
import pymongo
import pandas
from flask import Flask, render_template, request
from flask import jsonify
import pexpect
from pexpect import pxssh
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import easysnmp
import yaml
from nmv1 import *



logger = logging.getLogger("Rotating Log")

app = Flask(__name__)

### PAGE 1 START ####
class score_gen(object):

    def __init__(self):
        logger.info("Scoring Object Insiated...")

    def get_querys_from_json(self, score_jsn, ip, function):
        '''
        Get queries to make score using ip and function
        '''
        try:
            jsn = score_jsn
            if jsn == None:
                logger.exception("get_querys_from_yaml > None JSON")
                return None
            all_list = []
            # Get all matched query for given function and IP address
            for data in jsn:
                if data.get("function") == function:
                    # Function matched with YAML file
                    host_list = data.get("host")
                    if  host_list != None:
                        host_list = host_list.split(" ")
                        for host in host_list:
                            if host == ip or host == "all":
                                # Host Matched with YAML file
                                for d in data.get("querys"):
                                    all_list.append(d)
                                break
            return all_list
        except Exception:
            logger.exception("get_querys_from_yaml")

    def mongo_search_score(self, INID, mdb, score_jsn):
        '''
        Create score for output and update score and issue funtion name
        
        '''
        try:
            logger.debug("Mongo search score for:"+str(str(INID)))
            mdb_out = mdb['OUTPUT']
            all_data = mdb_out.find({"INID":INID})
            for single_host in all_data:
                try:
                    #print single_host
                    IP = single_host.get("IP")
                    logger.debug("mongo_search_score > Starting score for > "+str(IP))
                    mon_objects = single_host.get("Objects")
                    obj_index = -1
                    for mon_obj in mon_objects:
                        obj_index = obj_index + 1
                        #ranks = mon_obj.get("rank")
                        # Converting Test to JSON
                        #ranks = json.loads(ranks)
                        elmt_id = mon_obj.get("id")
                        last_score = 100
                        note = ""
                        function = mon_obj.get("function")
                        ranks = self.get_querys_from_json(score_jsn, IP, function)
                        if type(ranks) != list:
                            logger.error("mongo_search_score > QUERY not found in YAML for:" + str(IP) + ":" + str(function))
                        for rank in ranks:
                            #print rank
                            #custom_query = json.loads(rank.get("Q"))
                            custom_query = rank.get("Q")
                            score = rank.get("score")
                            dafault_query = {"INID":INID,"IP":IP}
                            #print custom_query
                            new_dict = {"out."+key: value for key, value in custom_query.items()}
                            #print new_dict
                            new_dict.update({"id":elmt_id})
                            elmts = {"$elemMatch":new_dict}
                            dafault_query.update({'Objects':elmts})
                            logger.debug("mongo_search_score > searching DB for:"+str(dafault_query))
                            queryout = mdb_out.find_one(dafault_query, {"_id":0, "TD":0})
                            #print queryout
                            if queryout == None:
                                logger.debug("mongo_search_score > Pattern Not matched")
                            else:
                                # For adding issue note
                                if score != 100:
                                    if type(rank.get("Q")) == dict:
                                        for matched_type in rank.get("Q"):
                                            note = note + str(matched_type) + ","

                                logger.debug("mongo_search_score > Pattern Matched")
                                # Update very lowest score in rank pattern
                                if last_score >= score:
                                    last_score = score
                                    d = dafault_query, {"$set": {"Objects.$"+".score":last_score}}
                                    logger.debug("mongo_search_score > updating score >"+str(d))
                                    mdb_out.update(dafault_query, {"$set": {"Objects.$"+".score":last_score, "Objects.$"+".note":note}})
                except Exception:
                    logger.exception("mongo_search_score")
        except Exception:
            logger.exception("mongo_search_score")

### PAGE 1 END ####

class main_model():

    def __init__(self):
        pass

    def get_credentials_from_yaml(self, credential_file):
        
        '''
        Convert credential YAML file to json
        Organize all credentials ( ex: ssh,snmp ) for particular ip address
        
        '''
        try:
            fp = open(credential_file)
            jsn = yaml.load(fp)
            all_ip = {}
            for j in jsn:
                gips = j.get("ip")
                if gips != None:
                    gips = gips.split(" ")
                    for gip in gips:
                        new_dic = dict(j)
                        new_dic.pop("ip")
                        # Update from multiple field
                        old_update = all_ip.get(gip)
                        if type(old_update) == dict:
                            # This is not first cretential for IP , updating with OLD.
                            new_dic.update(old_update)
                            all_ip.update({gip:new_dic})
                        else:
                            # This is first cretential for IP
                            all_ip.update({gip:new_dic})
                else:
                    logger.warning("get_credentials_from_yaml : ip not found for: "+str(j))
    
            # Getting authentication from "all" and update it to all ip
            for j in jsn:
                gips = j.get("ip")
                if gips != None:
                    gips = gips.split(" ")
                    if "all" in gips:
                        new_dic = dict(j)
                        new_dic.pop("ip")
                        all_auth_type = list(new_dic.keys())
                        all_ip_key = list(all_ip.keys())
                        for single_ip in all_ip_key:
                            single_ip_data = all_ip.get(single_ip)
                            for single_auth in all_auth_type:
                                new_auth = single_ip_data.get(single_auth)
                                if new_auth == None:
                                    single_ip_data.update({single_auth:new_dic.get(single_auth)})
                                    all_ip.update({single_ip:single_ip_data})
            return all_ip
        except Exception:
            logger.exception("get_credentials")

    def login(self, hostname='', auth=[], logpath="default.log", login_timeout=10, etimeout=6):
        
        '''
        Login using open-ssl pxssh.
        1) Set StrictHostKeyChecking to no for open-ssl
        2) Set UserKnownHostFile to null
        3) Default time is 10 sec to login and prompt expecting time out is 6 sec
        4) Send enter 3 time to get better prompt
        5) Return session and expected string as list ( if login success )
        
        '''
        if len(auth) > 0:
            for au in auth:
                logger.info("Trying to Login:"+hostname)
                return_typ = None
                username = au.get("username")
                password = au.get("password")
                try:
                    s = pxssh.pxssh(options={"StrictHostKeyChecking": "no","UserKnownHostsFile": "/dev/null"}, timeout=login_timeout)
                    s.login(hostname, username, password, auto_prompt_reset=False, login_timeout=login_timeout)
                    s.logfile = open(logpath+"/"+str(hostname)+".txt", "ab")
                    # Send enter to get router prompt to check login success
                    ex = ["#", r">", r"\$", pexpect.TIMEOUT]
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt 
                    s.expect(ex, timeout=etimeout)
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt
                    s.expect(["#", ">", "\$", pexpect.TIMEOUT], timeout=etimeout)
                    s.sendline('')
                    # expecting cisco ,  juniper ,  fortigate prompt
                    match_ex = s.expect(["#", ">", "\$", pexpect.TIMEOUT], timeout=etimeout)

                    login_chk = s.before.strip()
                    if len(login_chk) > 0 and match_ex < 3:
                        host_name = login_chk.decode("utf-8")
                        aftr = s.after
                        if type(aftr) == str:
                            host_name = host_name+aftr.strip().decode("utf-8")
                        logger.info("Login Success :"+hostname+":"+host_name)
                        return s, host_name
                    else:
                        logger.info("Not able to reach device:"+hostname)
                    return "TIMEOUT"
                except pxssh.ExceptionPxssh as e:
                    err = str(e)
                    if err.find("password refused") != -1:
                        #logger.info("Login Failed:"+hostname)
                        return_typ = "LOGINFAIL"
                    else:
                        logger.info("Login Error>"+err+":"+hostname)
                        return "TIMEOUT"
                except Exception:
                    #logger.exception("login")
                    return "TIMEOUT"
            return return_typ
    
    def get_ssh_ses(self, IP, Authentication, timeout, dir_path):
        
        ''' Login to device and return session
        '''
        
        ses = None
        ses = self.login(IP, Authentication, dir_path)
        if type(ses) != str and ses != None:
            #self.ssh_ses.update({IP:ses}) # Not required to store session
            return ses
        return ses

    def self_check(self, IP, Hostname, dir_path, element, my_credentials):

        '''Do ssh / snmp check if required
        Login using ssh and share the sesssion with expectation string
        if type of the device is cisco then set terminal length 0
        Curently there is no snmp validation , simply create snmp engine session'''

        try:
            result = {}
            all_sessions = {"status":{}}
            # Get SSH session
            einput = element.get("input")
            check = einput.get("check")
            
            if "ssh" in check:
                try:
                    logger.info("getting ssh session")
                    ssh_auth = my_credentials.get("ssh")
                    username = ssh_auth.get("username")
                    password = ssh_auth.get("password")
                    timeout = einput.get("timeout")
                    etype = einput.get("type")
                    auth = {"username":username, "password":password}
                    sess = self.get_ssh_ses(IP, [auth], timeout, dir_path)
                    if type(sess) == tuple:
                        # SSH login success
                        if etype == "cisco":
                            sess[0].sendline("terminal length 0")
                        result.update({"ssh":"reachable"})
                        all_sessions.update({"ssh_session":sess})
                    else:
                        # SSH login failed
                        logger.info("Failed >"+str(Hostname)+" "+str(IP)+" Reasion>"+str(sess))
                        if sess == "LOGINFAIL":
                            result.update({"ssh":"Authentication Failed"})
                        else:
                            result.update({"ssh":"timeout"}) 
                    #Get snmp session
                except:
                    logger.exception("self_check")
    
            if "snmp" in check:
                try:
                    logger.info("getting snmp session")
                    snmp_conf = my_credentials.get("snmp")
                    snmp_conf.update({"hostname":IP})
                    logger.info(snmp_conf)
                    session = easysnmp.Session(**snmp_conf)
                    result.update({"snmp":"reachable"})
                    all_sessions.update({"snmp_session":session})
                    logger.info("getting snmp success")
                except:
                    logger.exception("self_check")
    
            all_sessions.update({"status":result})
            return all_sessions
        except Exception:
            logger.exception("self_check")

    def device_check(self, host_objects, dir_path, mcollection,INID):
        
        '''
        Read input and execute each function one by one.
        First execute self_check function if success then execute next function .
        
        1) Sort all functions based on id then execute
        2) Check "skip" is set for this particular ip, if set then skip all other function to be execute next
        3) Get credential based on IP address , if credential not found for specific ip then get default credential else exit
        4) Execute function and update output to Objects
        
        '''
        try:
            # Read Objects from input ( Objects contains function , id , input )
            Monitoring_obj = host_objects.get("Objects")
            ID = host_objects.get("ID")
            Hostname = host_objects.get("Hostname")
            IP = host_objects.get("IP")

            if Monitoring_obj == None:
                logger.error("device_check None Objects")
                return None

            # continue_next is only true when self_check succeed
            continue_next = False
            
            #Sort all functions based on id then execute
            Monitoring_obj = sorted(Monitoring_obj,  key=lambda k: k['id'])
            total_obj = str(len(Monitoring_obj))
            
            #skip is None until skip command received from user
            #If skip received stop execute next function
            skip = None
            running_job = 0
            # Monitoring object will execute based on shorting 
            for element in Monitoring_obj:
                running_job += 1
                myid = element.get("id")
                
                # Update SESSION ( make host as running host )
                # Check skip is send by user in HISTORY table
                try:
                    mcollection.update({"INID":INID, "STATUS.IP":IP}, {"$set": {"STATUS.$.STATUS" : "Tasks: "+str(running_job)+"/"+total_obj }})
                    skip = mcollection.find_one({"INID":INID, "SKIP":"yes"}, {"SKIP":1})
                except Exception:
                    logger.exception("device_check skip check failed")
                
                # User send skip if skip is not None
                if skip != None:
                    logger.info("SKIPPING RECEIVED FROM DB")
                    try:
                        mcollection.update({"INID":INID, "STATUS.IP":IP}, {"$set": {"STATUS.$.STATUS" : "SKIPPED"}})
                    except Exception:
                        logger.exception("device_check updating DB failed for skipping")
                    break
                
                # One more time verify that first id is self_check
                if myid == 0:
                    # Get credentials for my IP
                    my_credentials = self.credentials.get(IP)
                    
                    # If not get default credential
                    if my_credentials == None:
                        my_credentials = self.credentials.get("all")
                        logger.info("Special gredential not found , Getting Default gredential for "+str(IP))
                    
                    # If no credential then set out_session to None this will break the for loop
                    if my_credentials == None:
                        logger.error("credential not found for:"+str(IP))
                        out_session = None
                    else:
                        out_session = self.self_check(IP, Hostname, dir_path, element, my_credentials)
                    
                    if out_session != None:
                            
                        einput = element.get("input")
                        check = einput.get("check")
                        
                        all_status = out_session.get("status")
                        element.update({"out":all_status})
                        # Check all required sessions are reachable else make continue_next as False
                        for ses_chk in check:
                            if all_status.get(ses_chk) == "reachable":
                                continue_next = True
                            else:
                                continue_next = False
                                break
                        if continue_next != True:
                            # Only return self element output (device down)
                            try:
                                mcollection.update({"INID":INID, "STATUS.IP":IP}, {"$set": { "STATUS.$.STATUS" :all_status}})
                            except Exception:
                                logger.exception("device_check updating DB failed for device")
                            return [element]
                    else:
                        logger.error("device_check self_check failed")
                        continue_next = False
                        try:
                            mcollection.update({"INID":INID, "STATUS.IP":IP}, {"$set": {"STATUS.$.STATUS" :"self check failed"}})
                        except Exception:
                            logger.exception("device_check updating DB failed for device")
                        break
                # Execute next function
                elif continue_next == True:
                    try:
                        et = element.get("function")
                        logger.debug("Starting function: "+str(et)+":"+str(IP)+" element:"+str(element))
                        # Convert string to function and execute
                        out = globals()[et](out_session, element)
                        # Update output to its element which is having input
                        element.update({"out":out})
                    except Exception:
                        logger.exception("device_check")
                        element.update({"out":"Error: function not present: "+str(et)})

            return Monitoring_obj

        except Exception:
            logger.exception("device_check")

    def single_host(self, host_objects, dir_path , INID):
        
        '''
        This is thread function called by ThreadPoolExecution.
        Update "HISTORY" DB , set host status to running.
        collect output and pass to caller
        
        '''
        try:
            IP = host_objects.get("IP")
            try:
                # Unix Socket for quick process
                mongoc = pymongo.MongoClient('/tmp/mongodb-27017.sock')
                mdb = mongoc['LIVE']
                mcollection = mdb['HISTORY']
                mcollection.update({"INID":INID, "STATUS.IP":IP}, {"$set": {"STATUS.$.TYPE" : "Running"}})
            except Exception:
                logger.exception("single_host DB")

            jout = self.device_check(host_objects, dir_path, mcollection,INID)
            if type(jout) == None:
                logger.error("single_host return non list objects")
                jout = []

            try:
                mongoc.close()
            except Exception:
                logger.exception("single_host closing DB failed")

            host_objects.update({"Objects":jout})
            return host_objects
    
        except Exception:
            logger.exception("single_host")

    def get_support_files(self, input_file_path):
        
        """
        Read input YAML and get credential file path and score file path.
        If score file not present then use "default_score" file as a scoring file.
        
        """
        try:
            fils = {"credential_file":None, "score_file":"default_score"}
            fp = open(input_file_path)
            jsn = yaml.load(fp)
            fils.update({"credential_file":jsn.get("credential")})
            if jsn.get("score") != None:
                fils.update({"score_file":jsn.get("score")})
            return fils
        except Exception:
            logger.exception("get_support_files")

    def start_run(self, input_file_path, jobname,device_log_file_path,INID,TD,apprentice):
        
        '''
        Start thread for each host and save output to OUTPUT DB.
        Calculate score for all hosts
        
        1) Get support file names from input file
        2) Get credential for all hosts from credential YAML file
        3) Get score query from score YAML file
        4) update "HISTORY" table
        
        '''
        try:
            # Insert input file to DB
            self.jobname = jobname
            if self.adding_input_session_to_db(INID ,input_file_path) == True:
                # input and session status update to DB
                pass
            else:
                logger.error("INPUT FILE ERROR")
                return None
            
            # Get Supporting files
            fils = self.get_support_files(input_file_path)
            
            #Get credential for all hosts from credential YAML file
            # Get score file path
            credential_file_path = fils.get("credential_file")
            score_file_path = fils.get("score_file")
            
            if credential_file_path == None:
                logger.error("CREDENTIAL FILE NOT FOUND")
                return None
            if score_file_path == None:
                logger.error("SCORE FILE NOT FOUND")
                return None
            
            # Join path for credential file
            default_path = os.path.join(os.getcwd(), "input_file")
            credential_file_path = os.path.join(default_path, credential_file_path)
            self.credentials = self.get_credentials_from_yaml(credential_file_path)
            
            if self.credentials == None:
                logger.error("CREDENTIAL FILE ERROR")
                return None
            
            # Number of time job need to execute @ present one 
            for y in range(1):
                #Get input from "INPUT" database based on INID
                mcollection = self.mdb['INPUT']
                all_data = mcollection.find({"INID":INID})
                
                # Set number of parallel execution for hosts 
                # Start parallel threads and assign task
                with ThreadPoolExecutor(max_workers=apprentice) as executor:
                    futures = [executor.submit(self.single_host, row, device_log_file_path,INID) for row in all_data]
                    for future in as_completed(futures):
                        try:
                            jout = future.result()
                            #INSERT OUTPUT TO DB
                            jout.update({"TD":TD, "JOBNAME":jobname})
                            mcollection = self.mdb['OUTPUT']
                            mcollection.insert(jout)
                        except Exception:
                            logger.exception("start_run")

                        try:
                            #Update HISTORY table
                            mcollection = self.mdb['HISTORY']
                            mcollection.update({"INID":INID, "STATUS.IP":jout.get("IP")}, 
                                {"$set": {"STATUS.$.TYPE" : "Completed"}})
                        except Exception:
                            logger.exception("start_run db")
                
                #Start Scoring for OUTPUT 
                try:
                    logger.info("Scoring Started")
                    score_file_path = os.path.join(default_path, score_file_path)
                    fp = open(score_file_path)
                    score_jsn = yaml.load(fp)
                    self.mongo_search_score(INID,self.mdb, score_jsn)
                    logger.info("Scoring Completed")
                except Exception:
                    logger.exception("start_run scoring")
        except Exception:
            logger.exception("start_run")

    def input_yaml_check(self, file_path):
        
        '''
        Validating input YAML file and return as json,
        Set id value for each function,
        Make id "0" for self_check function to execute first.
        
        1) Check 'networksnap' key present in yaml
        2) Check 'IP' key present in yaml
        3) Set id for each functions
        4) Set id 0 for self_check function
        
        '''
        try:
            fp = open(file_path)
            jsn = yaml.load(fp)
            jsn = jsn.get("networksnap")
            
            if jsn == None:
                logger.error("Not a valid YAML : 'networksnap' missing")
                return None
        
            if type(jsn)!= list or len(jsn) < 1:
                logger.error("Not a valid YAML : 'required one or more flow'")
                return None
        
            for obj in jsn:
                all_obj = obj.get("Objects")
                if obj.get("IP") == None:
                    logger.error("Not a valid YAML : 'IP' Missed")
                    return None
                if all_obj == None or type(all_obj) != list or len(all_obj) < 1:
                    logger.error("Not a valid YAML : 'Objects' missed")
                    return None
            
                # Setting Object ID
                objid = 0
                for one_obj in all_obj:
                    if one_obj.get("function") == "self_check":
                        one_obj.update({"id":0})
                    else:
                        objid = objid + 1
                        one_obj.update({"id":objid})

            return jsn
        except Exception:
            logger.exception("input_yaml_check")

    def adding_input_session_to_db(self,INID, filepath=None):
        
        '''
        Inserting input to mongoDB database and updating HISTORY to MongoDB database.
        1) verify input yaml file
        2) update "INID" to all hosts ( to track host individually )
        3) updating session status in "HISTORY" table with hostname , IP , STATUS and STARTDATE 
        
        '''
        try:
            json_input = self.input_yaml_check(filepath)
            if json_input == None or len(json_input) == 0:
                logger.error("No valid input yaml file")
                return None
            
            # Adding "INID" to all hosts
            for d in json_input:
                d.update({"INID":INID})
            
            # inserting input to json
            mcollection = self.mdb['INPUT']
            mcollection.insert(json_input)
            ses = mcollection.find({"INID":INID}, {"Hostname":1, "IP":1, "_id":0})
            
            # update session with all hostname and ip
            mcollection = self.mdb['HISTORY']
            mcollection.update({"INID":INID},{"$set":{"STATUS":list(ses)}})
            return True
        except Exception:
            logger.exception("mongdb")

    def main_run(self, filepath, jobname, apprentice,INID = None):
        
        '''
            Program starting Point , preparing necessary objects
            1) Initializing MongoDB and connect it to "LIVE" database.
            2) Initializing "score" function.
            3) Start executing "start_run".
            4) Create INID for job if not received from API , Auto increment the INID in "HISTORY" table and return.
            
        '''
        try:     
            # Connect to localhost mongoDB "LIVE" database
            TD = datetime.datetime.now()
            td_path = TD.strftime("%Y_%m_%d_%H_%M_%S_%f")
            device_log_file_path = os.path.join(os.getcwd(), "divlog")
            log_file_folder = jobname+"_"+str(INID)+"_"+td_path
            device_log_file_path = os.path.join(device_log_file_path, log_file_folder)

            #Check device log file storing folder exist else make folder
            if not os.path.exists(device_log_file_path):
                os.makedirs(device_log_file_path)

            #Create Logging file
            logger.setLevel(logging.DEBUG)
            handler = RotatingFileHandler(device_log_file_path+"/_div.log", maxBytes=5000000, backupCount=25)
            formatter = logging.Formatter('%(asctime)s > %(levelname)s > %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            #logger.propagate = False # DISABLE LOG STDOUT

            try:
                logger.info("Initializing Job >>>>>>>>>> "+str(jobname))
                logger.info("Input file: "+str(filepath))
                logger.info("Apprentice: "+str(apprentice))
                logger.info("INID: "+str(INID))
                self.mongoc = pymongo.MongoClient('localhost', 27017)
                self.mdb = self.mongoc['LIVE']
                logger.info("Connected to 'LIVE' database success")
            except Exception:
                logger.exception("Connected to 'LIVE' database failed")
                return None
    
            if INID == None:
                # INID not found in API or it may be direct run without API
                # Increase INID from DB and get assign to this JOB
                try:
                    mcollection = self.mdb['SESSION']
                    new_id = mcollection.find_and_modify(query = {"_id":1}, update = { "$inc": { "INID" : 1 }})
                    INID = new_id.get("INID")
                    INID = INID + 1
                    logger.info("New INID gendrated :"+str(INID))
                except Exception:
                    logger.exception("Getting INID from SESSION failed")
                    return None
            
            if INID == None:
                logger.error("No valid INID found")
                return None
            
            # Initializing Score Me object
            mcollection = self.mdb['HISTORY']
            mcollection.insert({"INID":INID,"JOBSTATUS" : "running","startedtime":TD,"JOBNAME":jobname,"logfile":log_file_folder})
            
            scor = score_gen()
            self.mongo_search_score = scor.mongo_search_score
            self.start_run(filepath, jobname, device_log_file_path, int(INID), TD, int(apprentice))
            
            completed_time = datetime.datetime.now()
            mcollection = self.mdb['HISTORY']
            mcollection.update({"INID":INID}, {"$set": {"JOBSTATUS" : "completed","completedtime":completed_time}})

            # Update the competed INID in "HISTORY" table
            mcollection = self.mdb['SESSION']
            new_id = mcollection.update({"_id":1}, {"$set": {"LASTINID" : INID } } )
        
        except Exception:
            logger.exception("main error")

if __name__ == '__main__':
    fil = sys.argv[1]
    jobname = sys.argv[2]
    appr = sys.argv[3]
    m = main_model()
    m.main_run(fil,jobname,appr)