# -*- coding: ISO-8859-1 -*-
"""
This module contains drivers to perform file operations OFFLINE
includes functions to normalize argument types
There should be no reference in here to other Whand modules
but some functions and variables are expected to be here by Whand
Port code is generally an integer, floats are truncated, zero ignored
A negative port code is for input, a positive port code for output
An alphabetic port code goes for a key pressed
Value is any string, numbers are in float format with at least one digit
Booleans should be "0" for false, "1" for true
""" 

from __future__ import print_function           # Python 2/3 compatibility
import os                                       
import sys
from time import time as clock, localtime     # the same clock as Whand
from math import atan                                  # used to test external calls
from whand_operators import *                    # options, constants
from whand_parameters import *                 # options, constants
from whand_tools import *                           # functions

# Global variables required/modified by Whand ===============================
Inpause=0                                                                         # 0: pause, 1: run, 2: abort

# Free global variables (not required by Whand) ===============================
Parallel=False                                                                      # indicates multiple parallel scripts
Input_state={}                                                                     # used to scan pins without interrupts
Scriptname=["","","","","","","",""]                                        # list of names of scripts
Runfilename=""                                                                 # chosen name for script list file
Filename=""                                                                       # chosen name for results

# global variables for offline version
Svlist=[None]
Position=-1                                                                          # index of event in file
Previous_time=0
Min_step=0.0001                                                                 # minimum event spacing
Store_off_time=[]
Event_list=[]

# GET EVENTS FROM FILE
#================================================================
def readpins(sv):                                                                   # required by Whand
    """
    opens result file and store all events in Event_list - OFFLINE
    reads next event
    Parameters
    -----------
        sv: a script instance
    Return
    -------
        ch: a list of change triplets  (nb, st, tim) with
            nb="P"+str(pinnumber)
            st: Boolean, state of the input
            tim: time in s after start
    """
    global Event_list
    global Position
    global Max_occur_list
    global Svlist
    global Previous_time
    global Store_off_time
    ch=[]

    # initialize on first call
    if Position==-1:
        if not sv.Graphic: sv.Do_tests=True                                       # set maximum speed
        Svlist=[sv]
        Event_list=read_event_file(sv)                                               # get event list
        Position+=1
        Previous_time=0

    if Store_off_time:                                                                     # add off event
        ch=Store_off_time
        Store_off_time=[]
        return ch
        
    if Position>=len(Event_list):
        print("\n*** Process complete ***\n")
        sv.Object[Exit].value=[(0, None)]                       # exit
        
    else:            
        time, code=Event_list[Position]                        # code is number from .e01 output file 
        if sv.Current_time>=time:
            if time<=Previous_time: time=Previous_time+Min_step
            Position+=1                                                # advance event list
            if 40<=code<Max_show_pins:
                numcode, st = code-40, False
            else:
                numcode, st = code, True
            event_name=sv.Namedpinlist.get("pin("+str(numcode)+")", "NA"+str(numcode))
            if not st: event_name="FI"+event_name
            event="P"+str(numcode)
            ch=[(event, st, time)]
            if code>Max_show_pins:                           # add offset
                Store_off_time=[(event, False, time+Min_step)]
            Previous_time=time
            if sv.Graphic: print(int(.5+10*time)/10, event_name)

    return ch
    
#=============================================================
def read_event_file(sv):                                                           
    """
    opens result file and store all events in Event_list
    set maximum speed
    reads next event
    Parameters
    -----------
        sv: a script instance
    Return
    -------
        Event_list: global list of (time, event_output_code)
    """
    global Data_file
    Event_list=[]
    fname=os.path.join(Datadir, Data_file+".e01")
    try:
        with open(fname,"r") as file: 
            line_list=file.read().split("\n")                  # read all events
    except IOError:
        print("*** I/O error ***")
        return None

    try:    
        for line in line_list[21:]:
            li=line.split("\t")
            time, code=float(li[0]), int(float(li[1]))
            if time==0: time=Min_step                     # avoid 0
            if code==99: break
            Event_list+=[(time/Split_second, code)] 
##            print(time, code)
    except ValueError:
        print("*** Error in file", fname+":", " invalid value :", str([line])[1:-1])
        os._exit(1)

    print("Event list loaded\n")

    return Event_list

#=============================================================
def initbox(sv, sourcename):                                                  # required by Whand         
    """
    ask name for input file - OFFLINE
    """
    global Data_file
    ok=False
    while not ok:
        print("\nSelect result file (.e01) ? ", end="")                     
        filename=input_text()
        if not filename.endswith(".e01"):  filename+=".e01"
        fname=os.path.join(Datadir, filename)         # directory is Data

##        fname="Data\\essai.e01"             # full test
##        if __name__== "__main__": fname="..\\Data\\essai.e01"
        
        if os.path.isfile(fname):
            ok=True
        else:
            print("File not found:", fname)

    Data_file=os.path.split(os.path.splitext(fname)[0])[-1]
    return

#==============================================================
def finish():                                                                          # required by Whand
    """
    This function saves results to file on exit  - OFFLINE
    saves occur times as csv for each object of type 'event' in 'show'
    n.b. occur list is limited in size by parameter Max_occur_list in whand_parameters.py
    """
    sv=Svlist[0]
    if not sv or not Show in sv.Object: return
    for obj in sv.Object[Show].value:                                        # extract objects to show
        sh=applied(obj, Show)
        ct=applied(sh, Count)
        name=ct if ct else sh
        if name in sv.Object and sv.Object[name].nature==Bln and sv.Object[name].occur:
            filename=os.path.join(Datadir, name+"_"+Data_file+".csv")
            print("Creating", filename)
            try:
                with open(filename,"w") as file:
                    file.write("timestamps\n") 
                    for occ in sv.Object[name].occur:
                        file.write('{:.3f}'.format(occ)+"\n")                
            except IOError:
                print("*** I/O error ***\n", filename)            
    return

# READING A WHAND SCRIPT - This section contains functions to read and cleanup the text file 
#================================================================
def readscriptfile(fname):                                      # required by Whand
    """
    opens specified script file, reads it as a binary and closes it using getbinfile
    filters line feeds, fuses continued lines, remove comments
    Parameters
    -----------
        fname: a string, filename with path and extension
    Return
    -------
        prog: a string, cleaned up program with lines separated by CR+LF, ends with CR+LF        
    """
    values=getbinfile(fname)                              # read file as a list of int character codes
    values=no_line_feed(values)                         # remove line feeds temporarily                                 
    values=fuse_continued_lines(values)             # continued lines fused into a single line                                
    values=no_comment(values)                        # remove comments (n.b. # is not allowed between quotes)
    values=unaccented(values)                          # remove accents except within strings (between quotes)
    values=printable(values)                              # change tabs to spaces and remove nonprintable chars
    prog=bin_to_text(values)                              # n.b. line feeds are added to CR here
    if Special in prog:                                        # Special char ` = chr(96) is not allowed in script
            print(prog)
            print("\n", Err_illegal_special)                                      
            raise ReferenceError
    return prog

#================================================================
def getbinfile(fname):                                      # required by Whand
    """
    opens specified (text) file, reads and converts chars one by one as a list of int
    some special chars (e.g. accented) are encoded into two consecutive ints
    called by readscriptfile
    Parameters
    -----------
        fname: a string, filename with path and extension
    Return
    -------
        values: a list of int representing character codes        
    """
    with open(fname,"rb") as file:               
        byte = file. read(1)
        values=[]
        while byte:                                           # EOF is not returned
            values+=[ord(byte)]                          # convert to int
            byte = file. read(1)
    return values

#================================================================
def no_line_feed(values):                                      # required by Whand
    """
    look for line feeds (10) in int list 
    remove them and return new list
    if not preceded by CR (13), replace with CR
    called by readscriptfile
    Parameters
    -----------
        values: a list of int representing character codes
    Return
    -------
        li: a list of int representing character codes        
    """
    li=[]
    preced=None
    for byte in values:
        if preced!=13 and byte==10: li+=[13]
        elif byte!=10: li+=[byte]
        preced=byte
    return li

#================================================================
def fuse_continued_lines(values):                                      # required by Whand
    """
    look for continuation char Mline in int list followed by carriage return,
    with or without intervening spaces and tabs
    remove continuation chars and return new list with fused lines
    called by readscriptfile
    Parameters
    -----------
        values: a list of int representing character codes
    Return
    -------
        li: a list of int representing character codes        
    """
    li=[]
    temp=[]
    escape=False
    for byte in values:
        if escape:                                                               # after possible continuation
            if byte==13:
                temp=[]                                                         # clear buffer, spaces, tabs and CR
                li=li[:-1]                                                         # remove prior Mline char
                escape=False
            elif byte==9 or byte==32:                                  # spaces and tabs are allowed before CR
                temp+=[byte]                                                 # store char in buffer
            else:                                                                   # not a continued line
                li+=temp                                                        # add and clear buffer, keep spaces and tabs
                li+=[byte]
                temp=[]
                escape=False
        else:                                                                       # normal text
            li+=[byte]
        if byte==ord(Mline):                                               # detect possible continuation
            escape=True                                                      
    return li

#================================================================
def no_comment(values):                                             # required by Whand                              
    """
    in list of int representing text, remove comments from Hash (#) to end of line
    called by readscriptfile
    Parameters
    -----------
        values: a list of int representing character codes
    Return
    -------
        li: a list of int representing character codes        
    """
    li=[]
    comment=False
    for byte in values:
        if byte==ord(Hash): comment=True
        if byte==13: comment=False
        if not comment: li+=[byte]
    return li

#================================================================
def unaccented(values):                                                  # required by Whand                         
    """
    in list of int representing text, convert accented chars and ç except within strings
    using dictionary 'Accented' of accented-to-unaccented chars
    called by readscriptfile
    Parameters
    -----------
        values: a list of int representing character codes
    Return
    -------
        li: a list of int representing character codes        
    """
    li=[]
    instring=False
    double=[]
    for byte in values:
        if double:                                                 # char on two bytes             
            for x in Accented:                                 # check if convertible
                if double[0]==195 and byte==ord(x)-64:
                    li+=[ord(Accented[x])]
                    double=[]
                    break
            if double:                                             # not convertible --> error
                txt=bin_to_text(values)
                print(txt)
                print("\n", Err_illegal_char, "\n", double[0], byte, chr(double[0]))                                      
                raise ReferenceError
        else: 
            if byte==ord(Quote): instring=not instring  # detect beginning and end of strings
            if byte>127 and not instring:                    # special char ossibly on two bytes
                double=[byte]
                for x in Accented:                                 # check if directly convertible
                    if double[0]==ord(x):                       # coded on one byte
                        li+=[ord(Accented[x])]
                        double=[]
                        break
            else:
                li+=[byte]                                              # ordinary char (1 byte)
    return li

#================================================================
def printable(values):                                                      # required by Whand            
    """
    in list of int representing text, change tabs to spaces and remove unprintable chars except CR
    ignore quoted strings
    called by readscriptfile
    Parameters
    -----------
        values: a list of int representing character codes
    Return
    -------
        li: a list of int representing character codes        
    """
    li=[]
    instring=False
    for byte in values:
        if byte==ord(Quote): instring=not instring  # detect beginning and end of strings
        if instring or byte==13 or (byte<127 and byte>=32):       # printable
            li+=[byte]
        elif byte==9:
            li+=[32]                                                # convert tab to space
        else:                                                          # non printable
            print("\n", Err_illegal_char, "\n", byte)                                      
            raise ReferenceError      
    return li

#===================================================== to_text  
def bin_to_text(charcodes):                                                 # required by Whand
    """
    converts a list of int (character codes) into a string
    adds a line feed after each carriage return
    some characters are coded as two integers
    called by readscriptfile
    Parameters
    -----------
        fname: a string, filename with path and extension
    Return
    -------
        txt: a string with LF added after CR, ends with CR+LF        
    """
    txt=""
    double=[]                               # buffer to hold first byte of two
    for byte in charcodes:
        if double:                           # special char on two bytes
            if double[0]==194: txt+=chr(byte-7)
            elif double[0]==195: txt+=chr(64+byte)
            double=[]                      # clear buffer
        elif byte>127: 
            double=[byte]               # detect special char and store first byte
        else:                    
            txt+=chr(byte)              # simple char on one byte
            if byte==13: txt+=chr(10)  # add line feed to carriage return            
    if charcodes and byte!=13:
        txt+=chr(13)+chr(10)        # end with CR+LF
    return txt

#==============================================================

# OTHER REQUIRED FUNCTIONS - The following functions must be present at least as dummies
#==============================================================
def getiocodes(fname):                                                       # required by Whand
        """
        Opens file and returns a dictionary with codes for inputs and outputs - NOT NEEDED OFFLINE
        """
        return

#=============================================================
def initialize(sv, iocodes):                                                         # required by Whand         
    """
    Initializes i/o variables - NOT NEEDED OFFLINE
    """
    return

#===================================================== init_interrupts  
def init_interrupts(sv):
    """
    initialize interrupts for declared pins only - NOT NEEDED OFFLINE
    """
    return

#==============================================================
def run(sv):                                                                          # required by Whand
    """
    This function is required to start execution of each box - NOT NEEDED OFFLINE
    """
    return

#==============================================================
def header(sv, box):                                                                          # required by Whand
    """
    Output box information to file - NOT NEEDED OFFLINE
    """
    return
    
#==============================================================
def closebox(sv):                                                                          # required by Whand
    """
    This function is required to clean up when execution of one box terminates - NOT NEEDED OFFLINE
    """
    return

#=============================================================
def export():                                                                             # called by finish
    """
    This function exports visible variables from screen to text file (.xls) - NOT NEEDED OFFLINE
    """
    return

#================================================================
def clearbuffer(sv):                                                                   # required by Whand
    """
    This function is called by whand_sharevars - NOT NEEDED OFFLINE
    """
    return
    
#================================================================
def setpin(sv, pinnumber, status, tim=0):                          # required by Whand
    """
    Output Booleans in Whand. Sets one output at a time - NOT NEEDED OFFLINE
    """
    return

#================================================================
def getpin(box, pinnumber):                        # called by scanpins if Use_interrupts is False
    """
    Directly read one input without interrupts and returns state 0 or 1 - NOT NEEDED OFFLINE
    """
    return

#================================================================
def scanpins(sv):                                            # called by readpins if Use_interrupts is False
    """
    Checks inputs for one box without interrupts if Use_interrupts is False - NOT NEEDED OFFLINE
    """
    return

#================================================================
def keyscan():                                                                    # required by Whand
    """
    Scans for keypressed and stores result in double buffer - NOT NEEDED OFFLINE
    """
    return

# The following function is needed when using Whand control panel
#================================================================
def panelpin(sv, nb, st, exact_time=0):                             # required by Whand control panel
    """
    Record pin input from control panel into double buffer - NOT NEEDED OFFLINE
    """
    return

#================================================================
def getanalog(sv, ADnumber, tim=0):                            # required by Whand
    """
    Input driver for numbers in Whand. Scans one input at a time - NOT NEEDED OFFLINE
    """
    return

#================================================================
def readmessage(sv, address, tim=0):                            # required by Whand
    """
    Input driver for text in Whand. Scans one input at a time - NOT NEEDED OFFLINE
    """
    return

#================================================================
def readtouch(sv, filename, X, Y, tim=0):                            # required by Whand
    """
    Input driver for touchscreen.  - NOT NEEDED OFFLINE
    """
    return

#================================================================
def outcommand(sv, outnumber, value, tim=0):                            # required by Whand
    """
    Driver for number output in Whand - NOT NEEDED OFFLINE
    """
    return

#================================================================
def outmsg(sv, outnumber, code, tim=0):                            # required by Whand
    """
    Driver for string output in Whand. Outputs one string of chars - NOT NEEDED OFFLINE
    """
    return

#================================================================
def display(sv, filename, X, Y, closing=False, tim=0):         # required by Whand
    """
    Driver for image display in Whand - NOT NEEDED OFFLINE
    """
    return

#================================================================
def waitforuser(prompt="\nPress Enter to leave"):                     # required by Whand
    """
    Yields control to outside process to wait before continuing execution 
    return code 0 to pause, 1 to continue, 2 to abort  
    Whand calls this function and locks execution until Enter or Ctrl-C is pressed
    """
    global Inpause
    Inpause=1
    print(prompt, end=" ")
    try:
        if sys.version_info[0]==2:
            raw_input()                                  # Python 2.7
        else:
            input()                                             # Python 3
    except KeyboardInterrupt:                  # catch exception to finish process
        Inpause=2
        raise ReferenceError
    except ValueError:
        pass
    
#================================================================
def testpause():                                                                     # required by Whand
    """
    Allows control by outside process to pause/abort execution
    return code 0 to pause, 1 to continue, 2 to abort 
    Beware of possible interference with keyscan
    Keys do not work under Idle mode
    Whand calls this function then reads result or variable Inpause
    """
    return 1

#================================================================
def screenprint(li):                                                                    # required by Whand
    """
    final formatting before printing a list to screen with Whand 'print'
    formatting still needs to be improved
    """
    for x in li:
        print(str(x).strip('"'), end="")
    print()

# The following file functions are called by Whand 
#================================================================
def input_text():                                                   # required by Whand
        """
        input a text (Python 2 and 3)
        """
        if sys.version_info[0]==2:
            text=raw_input()                                      # Python 2.7
        else:
            text=input()                                             # Python 3
        return text
    
#================================================================
def readtextfile(fname):                                      # required by Whand
        """
        opens specified file, reads and closes it
        filters line feeds, fuses continued lines, remove comments
        and returns content as a list of int
        """
        file=open(fname,"r")                
        txt = file. read()
        file. close()
        return txt
    
#================================================================
def getscriptlist():                                                # required by Whand
        """
        Select file containing a list of script names 
        returns scriptlist as list, autotest as Boolean, Parallel as Boolean
        autotest is set to True if file does not exist
        in which case, script names are all filenames in directory "Autotest"
        parallel is set to True if script names are on a single line in file
        otherwise, one file name per line
        """
        global Parallel
        global Runfilename
        Parallel=False
        autotest=False
        print(Prompt_script_list, end="")                # Select file containing script list ?
        fname=input_text()
        if not fname.endswith(".txt"): fname+=".txt"
        Runfilename=fname
        scriptlist=[]                                                       # look for script files
        try:
            fname=os.path.join(Scriptdir, fname)      
            fh=open(fname,"r")
            text=fh.read()
            fh.close()
        except IOError:                                                # file not found: run tests
            autotest=True
        if autotest:
            repertoire = "autotests"                                                   
            print("Accessing", repertoire)
            filelist = [os.path.normcase(nom)
                       for nom in os.listdir(repertoire)]
            if "repeat.txt" in filelist:                            # repeat same script many times
                try:
                    fnam=os.path.join(repertoire, "repeat.txt")
                    fhr=open(fnam,"r")
                    txt=fhr.read()
                    fhr.close()
                    if txt:
                        filelist=[os.path.normcase(txt)]*1000
                except IOError:
                    print("Unable to repeat script", txt)
                    pass
            scriptlist = [os.path.join(repertoire, nom)      # repeat
                                for nom in filelist
                                 if os.path.splitext(nom)[1] == ".txt"]
            if not scriptlist:
                    print("Missing .txt extension in repeat.txt", txt)

        else:
##            print(text)
            if "," in text:                                                      # detect parallel files
                Parallel=True
                scriptlist=text.split("\n")[0].split(",")      # keep only one line, split on comma
            else:
                scriptlist=text.split("\n")                          # several lines
            scriptlist=[x.strip(" ") for x in scriptlist]     # but do not process names starting with "="
            scriptlist=[os.path.join(Scriptdir, x) if not x.startswith(Equal) else x for x in scriptlist if x!=""]
            scriptlist=[x if x.endswith(".txt") or x.startswith(Equal) else x+".txt" for x in scriptlist]
            if not "," in text.split("\n")[0]:
                try:                                                               # verify if scriptlist[0] is valid
                    fhr=open(scriptlist[0], "r")
                    fhr.close()
                except IOError:                                          # use run file name as script name
                    print(Msg_runfile, Runfilename)         # Using run file name:
                    scriptlist=[os.path.join(Scriptdir, Runfilename)]
        return scriptlist, autotest, Parallel

 #================================================================
def opentextfile(fname, RAZ=False):                                 # required by Whand
        """
        opens file to append or overwrite 
        """
        if RAZ:
                new=open(fname,"w")                
        else:
                new=open(fname,"a")
        return new

#================================================================
def closetextfile(ident):                                                   # required by Whand
        """
        closes file  
        """
        ident.close()
        
#================================================================
def removepath(text):                                                   # required by Whand
        """
        remove path info from name (Windows)  
        """
        return os.path.basename(text)
        
#================================================================
def writetextfile(ident, vlu):                                              # required by Whand
        """
        appends value to file 
        """
        ident.write(vlu)
   
# basic tools
#===================================================== buildtime
def buildtime(tim):
    """
    format a time to save in result file
    depends on Split_second (time resolution)
    called by input and output functions
    """
    return ("%9.1f" % (float(int(.5+10*tim*Split_second))/Split_second))+"\t"                                       

#===================================================== checkboolean
def checkboolean(s):
    """
    Controls the type of a numeric variable
    Expects a Boolean
    Returns True or False if ok
    Anything other than True or False returns None
    """
    return s if s in [True, False] else None    # only accepts True or False

#===================================================== checknumber
def checknumber(x):
    """
    Controls the type of a numeric variable
    Expects a number or a string representing a number
    Returns the float value of x if ok
    Non-numbers return None
    """
    try:                                                            # check argument
        fx=float(x)                                             # convert to float
    except ValueError:                                     # catch error if non-number
        fx=None                                               # error value
    return fx


# The following functions are examples of external function calls from Whand
#===================================================== dialog
def dialog(prompt):
    """
    example of a dialog function - NOT NEEDED OFFLINE
    """
    return
        
#===================================================== arct
def arct(l):
        """
        example of external call
        expects a list of float arguments l (implements distributivity)
        returns a list of arctangents for each argument in list
        if only one argument, returns a float value
        """
        print("EXTERNAL FUNCTION arctangent:", l)
        res=[]
        for x in l:
            if x is None: return None
            if type(x)!=float and type(x)!=int:                # check numeric value
                print("*** Value error in arctangent", x, "in", l)
                raise ReferenceError
            res.append(atan(x))
        if len(res)==1: res=res[0]    # if only one argument, returns a float value
        return res

 ###===================================================== main
if __name__== "__main__":
    pass
