from pexpect import pxssh
import pexpect
import getpass

def login(hostname='',auth=[],login_timeout=6,etimeout=5):
    # Login to NPCI device , "enable" password check disabled because of aaa conf in NPCI
    if len(auth) > 0:
        for au in auth:
            #print "Trying to Login:"+hostname
            return_typ = None
            username = au.get("username")
            password = au.get("password")
            try:
                s = pxssh.pxssh(options={
                                "StrictHostKeyChecking": "no",
                                "UserKnownHostsFile": "/dev/null"},timeout=login_timeout)
                s.login(hostname, username, password,auto_prompt_reset=False,login_timeout=login_timeout)
                s.logfile = open("loggg.txt", "w")
                # Send enter to get router prompt to check login success
                s.sendline('')
                # expecting cisco , juniper , fortigate prompt 
                s.expect(["#",">","\$",pexpect.TIMEOUT],timeout=etimeout)
                login_chk = s.before.strip()
                if len(login_chk) > 0:
                    host_name = str(login_chk)
                    aftr = s.after
                    if type(aftr) == str:
                        host_name = host_name+aftr.strip()
                    print "Login Success :"+hostname+":"+host_name
                    return s,host_name
                else:
                    print "Not able to reach device:"+hostname
                return "TIMEOUT"
            except pxssh.ExceptionPxssh as e:
                err = str(e)
                if err.find("password refused") != -1:
                    print "Login Failed:"+hostname
                    return_typ = "LOGINFAIL"
                else:
                    print "Error>"+err+":"+hostname
                    return "TIMEOUT"
            except Exception as e:
                #print("Unknown Error"+str(e))
                return "TIMEOUT"
        return return_typ


auth = []
auth.append({"username":"gowtham","password":"Pong@123"})

def cis_bgp():
