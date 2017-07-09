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
                s.logfile = open("log1.txt", "ab")
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


def raw(ses,monobj):
    try:
        out = {"result":"failed"}
        mon = monobj.get("monitor")
        mon = mon.split(",")
            
        type_ = monobj.get("type")
        in_ = monobj.get("name")
        exp = ses[1]
        ses[0].sendline("terminal length 0")
        for cmd in mon:
            ses[0].sendline(cmd)
            ses[0].expect([cmd,pxssh.TIMEOUT])
            ses[0].expect([exp,pxssh.EOF,pxssh.TIMEOUT],timeout=300)
            #data = str(ses[0].before)
        out.update({"result":"success"})
        return out
    except:
        return out

def cis_bgp(ses,monobj):
    try:
        out = {}
        mon_ = monobj.get("monitor")
        mon_ = mon_.split(",")
        
        type_ = monobj.get("type")
        in_ = monobj.get("name")

        exp = ses[1]
        cmd = "show ip bgp summary "
        ses[0].sendline("terminal length 0")
        ses[0].sendline(cmd)
        ses[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
        ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
        data = str(ses[0].before)
        for host in mon_:
            try:
                ot=""
                pos = data.find(host)
                print host
                if pos > -1:
                    n = filter(None,data[pos:].split("\n")[0].split(" "))
                    ot = "neighbor:"+n[0]+"|"+"AS:"+n[2]+"|"+"uptime:"+n[-2]+"|"+"received-prf:"+n[-1]
                    ot = ot.strip()
            except Exception as e:
                print("cis_bgp Error 2>"+str(e))
            out.update({host:ot})
        print out
        return out
    except Exception as e:
        print("cis_bgp Error 1>"+str(e))

auth = []
auth.append({"username":"cisco","password":"cisco"})

monobj = {"monitor":"show clock,show tech","type":"raw","name":"raw"}


ses = login("10.1.1.2",auth)
if type(ses) != str and ses != None:
    print "Login Success"
    #ssh_ses.update({IP:ses})
else:
    print "Failed"
    exit()

print raw(ses,monobj)

