from nmv1 import *
import json
import csv
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
import pandas
from flask import Flask, render_template, request
from flask import jsonify
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed


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
                            elif eout_id == 0:
                                total_score = score
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

    def mongo_search_score(self,INID,session,mdb):
        try:
            mcollection = mdb['INPUT']
            all_data = mcollection.find({"INID":INID})
            mdb_out = mdb['OUTPUT']
            for single_input in all_data:
                try:
                    elements_input = single_input.get("Monitoring_obj")
                    hostname = single_input.get("Hostname")
                    ip = single_input.get("IP")
                    input_id = single_input.get("ID")
                    # Read elements for single hosts
                    for elmt in elements_input:
                        try:
                            elmt_id = elmt.get("id")
                            emon = elmt.get("monitor")
                            etype = elmt.get("type")
                            ename = elmt.get("name")
                            elmt_rank = elmt.get("rank")
                            #print elmt
                            last_score = 100
                            desc = ""
                            for rank in elmt_rank:
                                custom_query = rank.get("regex")
                                score = rank.get("score")
                                dafault_query = {"INID":INID,"SESSION":session,"ID":input_id,"OUT.id":elmt_id}
                                # Adding "OUT.out" in key
                                new_dict = {"OUT.out."+key: value for key, value in custom_query.items()}
                                dafault_query.update(new_dict)
                                #print dafault_query
                                queryout = mdb_out.find_one(dafault_query,{"_id":0,"TD":0})
                                #print queryout
                                if queryout == None:
                                    print "Issue Pattern Not matched"
                                else:
                                    print "Issue Pattern  Matched"
                                    # Update very lowest score in rank pattern
                                    if last_score > score:
                                        last_score = score
                                    #tmpdesc = hostname+" "+ip+" "+str(emon)+" "+str(etype)+" "+str(ename)+" "+str(custom_query)+" "+str(last_score)+" "+str(queryout.get("OUT"))
                                    #desc = desc+"\n"+str(tmpdesc)
                                    #print "Issue pattern matched > ",desc
                                    mdb_out.update(dafault_query,{"$set": {"OUT.$.score":last_score,"OUT.$.note":'desc'}})
                        except Exception as e:
                            print ("mongo_search_score Error2>"+str(e))
                except Exception as e:
                    print ("mongo_search_score Error1>"+str(e))
        except Exception as e:
            print("mongo_search_score Error>"+str(e))

### PAGE 1 END ####


class main_model():
    def __init__(self):
        #Saving ssh session
        self.ssh_ses = {}

    def login(self,hostname='',auth=[],logpath="default_log.txt",login_timeout=10,etimeout=6):
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
                    print("Unknown Error :"+str(e))
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

    def single_host(self,row2,dir_path):
        #Login and run
        ID = Hostname = IP = Authentication = Monitoring_obj = timeout = None
        ID = row2.get("ID")
        Hostname = row2.get("Hostname")
        IP = row2.get("IP")
        Authentication = json.loads(row2.get("Authentication"))
        #Model = row2.get("Model")
        Monitoring_obj = row2.get("Monitoring_obj")
        #Mode = row2.get("Mode")
        timeout = row2.get("timeout")

        try:
            mongoc = pymongo.MongoClient('localhost', 27017)
            mdb = mongoc['LIVE']
            mcollection = mdb['SESSION']
            mcollection.update({"_id":1,"STATUS.IP":IP},{ "$set": { "STATUS.$.TYPE" : "Running" } })
            mongoc.close()
        except Exception as e:
            print("Error > single_host"+str(e))

        sess = self.get_ssh_ses(IP,[Authentication],timeout,dir_path)
        jout = {}
        if sess == None or type(sess) == str:
            print("Failed >"+str(Hostname)+" "+str(IP))
            jout = [{"id":0,"out":{"status":"down"}}]
        else:
            jout = self.device_check(sess , Monitoring_obj)

        return [jout,ID,IP]
            
    def start_run(self,input_file_path,jobname,apprentice = 5):
        try:
            # start create DB function
            self.jobname = jobname
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
                jobname = jobname.replace(":","-")
                dir_path = os.path.join(os.getcwd(),"divlog")
                dir_path = os.path.join(dir_path,jobname)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                dir_path = os.path.join(dir_path,jobname)
                print "Apprentice>"+str(apprentice)
                # Share work to threads
                with ThreadPoolExecutor(max_workers=apprentice) as executor:
                    futures = [executor.submit(self.single_host, row,dir_path) for row in all_data]
                    for future in as_completed(futures):
                        try:
                            jout2 = future.result()
                            jout = jout2[0]
                            ID = jout2[1]
                            IP = jout2[2]
                            #INSERT OUTPUT TO DB
                            #dbdata = self.score_me(row,{"SESSION":int(session),"ID":int(ID),"OUT":jout,"TD":datetime.datetime.now(),"INID":INID,"JOBNAME":jobname})
                            dbdata = {"SESSION":int(session),"ID":int(ID),"OUT":jout,"TD":datetime.datetime.now(),"INID":INID,"JOBNAME":jobname}
                            mcollection = self.mdb['OUTPUT']
                            mcollection.insert(dbdata)


                            #Update session table
                            mcollection = self.mdb['SESSION']
                            mcollection.update({"_id":1,"STATUS.IP":IP},{ "$set": { "STATUS.$.TYPE" : "Completed" } })
                        except Exception as e:
                            print("start_run trying Error>>"+str(e))
                
                #Start Scoring
                print("Scoring Started")
                self.mongo_search_score(INID,session,self.mdb)
                print("Scoring Completed")
                #UPDATE CURRENT SESSION
                mcollection = self.mdb['SESSION']
                mcollection.update({"_id":1},{"$set":{"SESSION":session}})
        except Exception as e:
            print("start_run Error >"+str(e))

    def xls_input(self,filename):
        try:
            xl = pandas.ExcelFile(filename)
            df1 = xl.parse('input')
            IP = list(set((df1.get("IP"))))
            full_list = []
            for inx , i in enumerate(IP):
                elmt_id = 0
                local_list = []
                xx = ""
                for index, row in df1.iterrows():
                    if row["IP"] == i:
                        # Setting "self" name id to "0"
                        if row["name"] == "self":
                            elmt_id2 = 0
                        else:
                            elmt_id = elmt_id + 1
                            elmt_id2 = elmt_id
                        a = {"id":elmt_id2,"type": row["type"] , "name": row["name"] , "monitor":row["monitor"], "rank": json.loads(row["rank"])}
                        local_list.append(a)
                        xx = row
                full_list.append({"ID":inx,"Hostname": str(xx["Hostname"]),"IP":str(xx["IP"]),"Authentication":xx["Authentication"],
                    "timeout":int(xx["timeout"]),"Monitoring_obj":local_list})
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
                if input == "xls":
                    d.update({"INID":INID,"Monitoring_obj":d.get("Monitoring_obj")})
                else:
                    d.update({"INID":INID,"Monitoring_obj":json.loads(d.get("Monitoring_obj"))})

            mcollection = self.mdb['INPUT']
            mcollection.insert(csv_data)

            ses = mcollection.find({"INID":INID},{"Hostname":1,"IP":1,"_id":0})
            # Add or Update new session in SESSION collection
            mcollection = self.mdb['SESSION']
            #print list(ses)
            mcollection.update({"_id":1},{"_id":1,"INID":INID,"SESSION":0,"JOBNAME":self.jobname,"STATUS":list(ses),"STARTDATE":datetime.datetime.now()})
            print("SESSION UPDATED , INID = "+str(INID))
            
            #self.mongoc.close()
            return True
        except Exception as e:
            print(e,"Error mongdb")



    def main_run(self,filepath,jobname,apprentice):
        # connect to LIVE database
        self.mongoc = pymongo.MongoClient('localhost', 27017)
        self.mdb = self.mongoc['LIVE']
        print ("Connected to 'LIVE' database...")

        # Insitate Score Me object
        scor = score_gen()
        self.mongo_search_score = scor.mongo_search_score

        print ("Starting...")
        self.start_run(filepath,jobname,apprentice)




        

if __name__ == '__main__':
    pass;
