from pexpect import pxssh
import pexpect
import getpass
import re

def login(hostname='',auth=[],logpath="default_log.txt",login_timeout=6,etimeout=5):
        # Login to NPCI device , "enable" password check disabled because of aaa conf in NPCI
        if len(auth) > 0:
            for au in auth:
                print ("Trying to Login:"+hostname)
                print (auth)
                return_typ = None
                username = str(au.get("username"))
                password = str(au.get("password"))
                try:
                    s = pxssh.pxssh(options={
                                    "StrictHostKeyChecking": "no",
                                    "UserKnownHostsFile": "/dev/null"},timeout=login_timeout)
                    s.login(hostname, username, password,auto_prompt_reset=False,login_timeout=login_timeout)
                    s.logfile = open(logpath+"_"+str(hostname)+".txt", "ab")
                    # Send enter to get router prompt to check login success
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt
                    s.expect(["#",">","\$",pexpect.TIMEOUT],timeout=etimeout)
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt
                    s.expect(["#",">","\$",pexpect.TIMEOUT],timeout=etimeout)
                    s.sendline('')
                    # expecting cisco , juniper , fortigate prompt
                    s.expect(["#",">","\$",pexpect.TIMEOUT],timeout=etimeout)
                    login_chk = s.before.strip()
                    print "================================"
                    print login_chk
                    print "================================"
                    if len(login_chk) > 0:
                        host_name = login_chk.decode("utf-8")
                        #host_name = str(login_chk)
                        aftr = s.after
                        if type(aftr) == str:
                            host_name = host_name+aftr.strip().decode("utf-8")
                            #host_name = host_name+aftr.strip()
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


def juniper_interface(ses,monobj):
	# Monitor cisco switch interface : speed, duplex, error , bits 
	try:
		out = {}
		x_input = monobj.get("input")
		mon_ = x_input.get("check")
		mon_ = mon_.split(",")
		in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show interface "+in_+" | no-more"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		
		print data
		if re.search(r'physical link is up',data):
			out.update({"interface":"up"})
		else:
			return {"interface":"down"}

		if "bits" in mon_:
			irate = ""
			orate = ""
			
			redata = re.search(r'input rate.*[0-9].*bps',data)

			if redata:
				irate = redata.group(0).split(":")[1].replace(" ","")

			redata = re.search(r'output rate.*[0-9].*bps',data)

			if redata:
				orate = redata.group(0).split(":")[1].replace(" ","")

			out.update({"inrate":irate,"outrate":orate})
		
		if "duplex" in mon_:
			if data.find("half") != -1:
				out.update({"duplex":"Half"})
			if data.find("full") != -1:
				out.update({"duplex":"Full"})

		if "speed" in mon_:
			speed = ""
			spd = re.search(r'speed:.*[0-9].*,',data)
			if spd:
				speed = spd.group(0).split(":")[1].replace(" ","").replace(",","")
			
			out.update({"speed":speed})


		if "error" in mon_:
			error = ""
			err = re.search(r'bpdu error: .*,',data)
			print "=======",err
			if err:
				error = err.group(0).split(",")[0].replace("bpdu error: ","")
				if error == "none":
					error = "0"
				out.update({"error":error})
		return out
	except Exception as e:
		print e
		#logger.exception("cis_sw_int")

auth = []
auth.append({"username":"gowtham","password":"Google@5432"})

monobj = {"input":{"interface":"ge-0/0/0","check":"bits,duplex,speed,error"}}


print auth
ses = login("192.168.175.4",auth)
print ses
if type(ses) != str and ses != None:
    print "Login Success"
    #ssh_ses.update({IP:ses})
else:
    print "Failed"
    exit()

print juniper_interface(ses,monobj)

