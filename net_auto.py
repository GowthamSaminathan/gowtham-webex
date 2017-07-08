from nmv1 import *
import json
import csv
import MySQLdb
import datetime
import time
import os.path
import shutil
from pexpect import pxssh
import pexpect
import getpass
import ast
import pymongo
import re
import pandas as pd
from flask import Flask, render_template, request
from flask import jsonify
from threading import Thread


#j = {"objects":[{"id":"1","type":"interface","in":"Gi0/0","monitor":["speed","duplex","bits","error"]},{"id":"2","type":"interface","name":"Gi0/1","monitor":["speed","duplex","bits","error"]}]}
#jj = json.dumps(j)
#O = json.loads(jj)

app = Flask(__name__)

### PAGE 1 START ####
class score_gen():
    def __init__(self):
        print("Scoring Object Insiated...")
    def regex_check(self,ranks,alloutput):
        try:
            # Get jsion data
            #print "<<<",alloutput
            alloutput = "|".join(alloutput.values())

            for rank in ranks:
                reg = rank.get("regex")
                score = rank.get("score")
                score_match = False
                if type(reg) != list:
                    print "Warning: regex vlaue is not in list format"
                    return -1
                for r in reg:
                    # Match all regex to retun the score
                    #print "Reg>>",r
                    rd = re.findall(r,alloutput)
                    if len(rd) > 0:
                        return score
                        score_match = True
                    else:
                        # Regex not matched with string
                        score_match = False
                        break
                if score_match == True:
                    return score
            return -1
            #sprint rank,alloutput
        except Exception as e:
            print("regex_check Error>"+str(e))
            return -1
    def score_me(self,dinput,doutput):
        # Create Score based on INPUT and OUTPUT
        try:
            scored_output = []
            elements_input = dinput.get("Monitoring_obj")
            elements_output = doutput.get("OUT")
            total_score = 100
            for eo in elements_output:
                # Process every elemet output with element input
                # default score -1
                score = -1
                try:
                    eout_id = eo.get("id")
                    for ei in elements_input:
                        #print ei.get("rank"),eo.get("out")
                        if ei.get("id") == eout_id:
                            #Input and Output ID matched 
                            # Check regex for scoring
                            score = self.regex_check(ei.get("rank"),eo.get("out"))
                            if eout_id != 0 and score != 100:
                                # if score is not equal to 100 and and sore is not self score
                                total_score = total_score - 1
                except Exception as e:
                    print("score_me Error>"+str(e))
                    total_score = -1

                eo.update({"score":score})
                scored_output.append(eo)
            for seo in scored_output:
                if seo.get("id") == 0:
                    seo.update({"score":total_score})
            doutput.update({"OUT":scored_output})
            #print (doutput)
            return doutput
        except Exception as e:
            print("score_me Error>"+str(e))
            return doutput


### PAGE 1 END ####


class main_model():
    def __init__(self):
        #Saving ssh session
        self.ssh_ses = {}

    def login(self,hostname='',auth=[],login_timeout=1,etimeout=5):
        # Login to NPCI device , "enable" password check disabled because of aaa conf in NPCI
        if len(auth) > 0:
            for au in auth:
                print ("Trying to Login:"+hostname)
                return_typ = None
                username = au.get("username")
                password = au.get("password")
                try:
                    s = pxssh.pxssh(options={
                                    "StrictHostKeyChecking": "no",
                                    "UserKnownHostsFile": "/dev/null"},timeout=login_timeout)
                    s.login(hostname, username, password,auto_prompt_reset=False,login_timeout=login_timeout)
                    #s.logfile = open("ssh_log.txt", "ab")
                    # Send enter to get router prompt to check login success
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt 
                    s.expect(["#",">","\$",pexpect.TIMEOUT],timeout=etimeout)
                    login_chk = s.before.strip()
                    if len(login_chk) > 0:
                        host_name = login_chk.decode("utf-8")
                        aftr = s.after
                        if type(aftr) == str:
                            host_name = host_name+aftr.strip().decode("utf-8")
                        print("Login Success :"+hostname+":"+host_name)
                        return s,host_name
                    else:
                        print("Not able to reach device:"+hostname)
                    return "TIMEOUT"
                except pxssh.ExceptionPxssh as e:
                    err = str(e)
                    if err.find("password refused") != -1:
                        print("Login Failed:"+hostname)
                        return_typ = "LOGINFAIL"
                    else:
                        print("Error>"+err+":"+hostname)
                        return "TIMEOUT"
                except Exception as e:
                    print("Unknown Error"+str(e))
                    return "TIMEOUT"
            return return_typ

    def clock(self,ses,a):
        try:
            #print("Clock function")
            session = ses[0]
            exp = ses[1]
            session.sendline("show clock")
            session.expect(["show clock",pxssh.TIMEOUT],timeout=5)
            #session.before
            session.expect([exp,pxssh.TIMEOUT],timeout=5)
            v = session.before
            return v.strip()
        except Exception as e:
            pass;
        

    def get_ssh_ses(self,IP,Authentication,timeout):
        try:
            ses = self.ssh_ses.get(IP)
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
            ses = self.login(IP,Authentication)
            if type(ses) != str and ses != None:
                self.ssh_ses.update({IP:ses})
                return ses
        return ses

    def device_check(self,ses,Os):
        try:
            # Check Single devices based on JSON Object
            out = []
            if Os == None :
                # Objects Not Found
                return None
            for element in Os:
                #Object found ; reading elements
                et = element.get("type")
                id_ = element.get("id")
                out_ = globals()[et](ses,element)
                #print(out_)
                out_ =  {"id":id_,"out":out_}
                out.append(out_)
            
            return out
        except Exception as e:
            print("Error >"+str(e))

            
    def start_run(self,input_file_path):
        try:
            # start create DB function
            if self.mongdb("xls",input_file_path) == True:
                pass;
            else:
                print("STOPPED")
                return
            session = 0
            for y in range(1):
                tim = time.strftime('%Y-%m-%d %H:%M:%S')
                session = session + 1
                print("STARTING SESSION >"+str(session))
                mcollection = self.mdb['SESSION']
                sesout = mcollection.find_one({"_id":1})
                INID = sesout.get("INID")

                #Get INPUT based on INID
                mcollection = self.mdb['INPUT']
                all_data = mcollection.find({"INID":INID})
                for row in all_data:
                    try:
                        ID = Hostname = IP = Authentication = Model = Monitoring_obj = Mode = timeout = None
                        ID = row.get("ID")
                        Hostname = row.get("Hostname")
                        IP = row.get("IP")
                        Authentication = json.loads(row.get("Authentication"))
                        Model = row.get("Model")
                        Monitoring_obj = row.get("Monitoring_obj")
                        Mode = row.get("Mode")
                        timeout = row.get("timeout")
                        sess = self.get_ssh_ses(IP,[Authentication],timeout)
                        jout = {}
                        if sess == None or type(sess) == str:
                            print("Failed >"+str(Hostname)+" "+str(IP))
                            jout = [{"id":0,"out":{"status":"unreachable"}}]
                        else:
                            jout = self.device_check(sess , Monitoring_obj)

                        #INSERT OUTPUT TO DB
                        dbdata = self.score_me(row,{"SESSION":int(session),"ID":int(ID),"OUT":jout,"TD":datetime.datetime.now(),"INID":INID})
                        mcollection = self.mdb['OUTPUT']
                        mcollection.insert(dbdata)
                    except Exception as e:
                        print("start_run trying Error>>"+str(e))

                #UPDATE CURRENT SESSION
                mcollection = self.mdb['SESSION']
                mcollection.update({"_id":1},{"$set":{"SESSION":session}})
        except Exception as e:
            print("start_run Error >"+str(e))

    def xls_input(self,filename):
        try:
            xl = pd.ExcelFile(filename)
            df1 = xl.parse('input')
            ID = list(set((df1.get("ID"))))
            full_list = []
            for i in ID:
                local_list = []
                xx = ""
                for index, row in df1.iterrows():
                    if row["ID"] == i:
                        a = {"id":int(row["_id"]),"type": row["_type"] , "name": row["_name"] , "monitor":row["_monitor"], "rank": json.loads(row["_rank"])}
                        local_list.append(a)
                        xx = row
                full_list.append({"ID":int(xx["ID"]),"Hostname": str(xx["Hostname"]),"IP":str(xx["IP"]),"Authentication":xx["Authentication"],
                    "Model":str(xx["Model"]),"Mode":str(xx["Mode"]),"timeout":int(xx["timeout"]),"Monitoring_obj":local_list})
            return full_list

        except Exception as e:
            print("xls_input Error>"+str(e))


    def mongdb(self,input="xls",filepath=None):
        try:
            INID  = 1
            if input == "xls":
                csv_data = self.xls_input(filepath)
                if csv_data == None or len(csv_data) == 0:
                    print("No valid XLS input")
                    return None
            else:
                return None
                #csv_data = list(csv.DictReader(open('input.csv')))
            
            # Add or Update new session in SESSION collection
            mcollection = self.mdb['SESSION']
            session = (list(mcollection.find()))
            if len(session) > 0:
                INID = session[0].get("INID")
                if INID != None:
                    INID = INID+1
                    mcollection.update({"_id":1},{"_id":1,"INID":INID,"SESSION":0})
                    print("SESSION UPDATED , INID = "+str(INID))
            else:
                mcollection.insert({"_id":1,"INID":INID,"SESSION":0})
                print("CREATING NEW SESSION ADDED , INID = 1")
            
            # ADD INID in INPUT collection
            for d in csv_data:
                # Json loads used to convert string to array object
                if input == "xls":
                    d.update({"INID":INID,"Monitoring_obj":d.get("Monitoring_obj")})
                else:
                    d.update({"INID":INID,"Monitoring_obj":json.loads(d.get("Monitoring_obj"))})

            mcollection = self.mdb['INPUT']
            mcollection.insert(csv_data)
            #self.mongoc.close()
            return True
        except Exception as e:
            print(e,"Error mongdb")



    def main_run(self,filepath,jobname):
        # connect to LIVE database
        self.mongoc = pymongo.MongoClient('localhost', 27017)
        self.mdb = self.mongoc['LIVE']
        print ("Connected to 'LIVE' database...")

        # Insitate Score Me object
        scor = score_gen()
        self.score_me = scor.score_me

        print ("Starting...")
        self.start_run(filepath)




        

if __name__ == '__main__':
    pass;
