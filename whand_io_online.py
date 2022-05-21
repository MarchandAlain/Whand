# -*- coding: ISO-8859-1 -*-
"""
This module contains drivers to perform file operations
includes functions to normalize argument types
Some functions and variables are expected to be here by Whand
Here is also a logging function (not required by Whand)
The logger function stores a trace of all events on disk as follows: 
Time is stored in seconds with 3 digits (= millisecond)
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
import whand_driver as dr                            # needed to access ASi though dll

# Attempt to import optional modules. If import fails, keeps an indicator ===============
Withkeys=True                                             # indicates availability of msvcrt module                                       
try:                                                                                          
    from msvcrt import getch as getcar, kbhit, ungetch as letcar                                       
except:
    print('\n*** msvcrt module is not available: keypress detection will not work ***')
    Withkeys=False                                                                     

# Global text constants ================================================
Legend="\n\n 1 :  front montant présentation pédale A\n"
Legend+=" 2 :  front montant présentation pédale B\n"
Legend+=" 3 :  front montant ouverture trou C\n"
Legend+=" 4 :  front montant ouverture trou D\n"
Legend+=" 5 :  front montant ouverture trou E\n"
Legend+=" 6 :  front montant appui pédale A\n"
Legend+=" 7 :  front montant appui pédale B\n"
Legend+=" 8 :  front montant visite trou C\n"
Legend+=" 9 :  front montant visite trou D\n"
Legend+="10 :  front montant visite trou E \n"
Legend+="11 :  front montant visite mangeoire A vide \n"
Legend+="12 :  front montant visite mangeoire B vide\n"
Legend+="13 :  front montant visite mangeoire A pleine\n"
Legend+="14 :  front montant visite mangeoire B pleine\n"
Legend+="15 :  front montant relachement pédale OU fin visite trou ou DB ou ..\n"
Legend+="16 :  front montant distribution mangeoire A\n"
Legend+="17 :  front montant distribution mangeoire B\n"
Legend+="18 :  front montant enclenchement led A\n"
Legend+="19 :  front montant enclenchement led B\n"
Legend+="20:   front montant enclenchement led C\n"
Legend+="21 :  front montant enclenchement led D\n"
Legend+="22 :  front montant enclenchement led E\n"
Legend+="23 :  front montant enclenchement led F\n"
Legend+="24 :  front montant enclenchement son\n"
Legend+="25 :  front montant enclenchement lumière EA\n"
Legend+="26 :  front montant enclenchement injection\n"
Legend+="27 :  front montant enclenchement choc\n"
Legend+="28 :  front montant enclenchement stimulation\n"
Legend+="29 :  ACTIVITE front montant entree zone gauche\n"
Legend+="30 :  ACTIVITE front montant entree zone droite\n"
Legend+="41 :  rétraction pédale A\n"
Legend+="42 :  rétraction pédale B\n"
Legend+="43 :  fermeture trou C\n"
Legend+="44 :  fermeture trou D\n"
Legend+="45 :  fermeture trou E\n"
Legend+="46 :  relachement pédale A\n"
Legend+="47 :  relachement pédale B\n"
Legend+="48 :  fin visite trou C\n"
Legend+="49 :  fin visite trou D\n"
Legend+="50 :  fin visite trou E \n"
Legend+="51 :  fin visite mangeoire A vide \n"
Legend+="52 :  fin visite mangeoire B vide\n"
Legend+="53 :  fin visite mangeoire A pleine\n"
Legend+="54 :  fin visite mangeoire B pleine\n"
Legend+="56 :  fin distribution mangeoire A\n"
Legend+="57 :  fin distribution mangeoire B\n"
Legend+="58 :  fin led A\n"
Legend+="59 :  fin led B\n"
Legend+="60:   fin led C\n"
Legend+="61 :  fin led D\n"
Legend+="62 :  fin led E\n"
Legend+="63 :  fin led F\n"
Legend+="64 :  fin son\n"
Legend+="65 :  fin lumière EA\n"
Legend+="66 :  fin injection\n"
Legend+="67 :  fin choc\n"
Legend+="68 :  fin stimulation\n"
Legend+="69 :  fin zone gauche\n"
Legend+="70 :  fin zone droite\n"
Legend+="99 :  fin séance\n"

Header1="Date version:  18/04/2017\nDate expérience:\t"
Header2="Heure expérience:\t"   
Header3="Expérience dans cage:\t"   
Header4="Animal:\t0\nNuméro séance:\t1\nSéance précédente:\t0\n"
Header4+="Séance suivante:\t0\nGène:\t\nTraitement:\t\nDose:\t\nVoie:\t\n"      
Header4+="Solvant:\t\nProduit2:\t\nLésion:\t\nRemarque:\t\nNom fichier données:\t"
Header5="Nom fichier exercice:\t"   
Header6="[fin section etiquette]\n\nInstant(s10):   Event1: Event2: Event3:"


# Global variables required/modified by Whand ===============================
Inpause=0                                                                         # 0: pause, 1: run, 2: abort

# Free global variables (not required by Whand) ===============================
Parallel=False                                                                      # indicates multiple parallel scripts
DoubleBuffer=[[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]]]      # double buffer for pin interrupts (max 8 boxes) SEE ALSO whand_sharedvars
BufferPointer=[0,0,0,0,0,0,0,0]       # 0 / 1 : current buffer, used by interrupt callback, controlled by readpins
Started=[False,False,False,False, False,False,False,False]     # indicator of box execution
Input_state={}                                                                     # used to scan pins without interrupts
Displayed=[{}, {}, {}, {}, {}, {}, {}, {}]                                        # list of dicts of displayed images
Mylog=[None, None, None, None, None, None, None, None]  # handle to save data to file
Mybuff=["", "", "", "", "", "", "", ""]                                        # temporary data store in memory
Svlist=[]                                                                             # list of active instances of scripts
Scriptname=["","","","","","","",""]                                        # list of names of scripts
Runfilename=""                                                                 # chosen name for script list file
Filename=""                                                                       # chosen name for results
Codes={}                                                                             # codes for logging (read from file)
Lastkey=""                                                                          # last key pressed
    
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
        Opens file and returns a dictionary with codes for inputs and outputs
        config file should contain three values per line, separator is comma
        first value is a port number (1 to n) for outputs, (-1 to -n) for inputs
        port number may be an alphabetic key for keypress
        second value is a name or code for the port UP front (max 4 chars)
        third value is a name or code for the port DOWN front (max 4 chars)
        Whand calls this function then passes the result to function initialize
        A dummy function returning any iocodes may be sufficient
        """
        global Svlist
        Svlist=[]
        nam=fname 
        old=open(nam,"r")                
        raw=old.read()                                    
        old.close()
        lines=raw.split("\n")
        iocodes={}
        iocodes.clear()
        for li in lines:
                ni=li.split(",")
                try:
                        if len(ni)<3: raise ValueError
                        nb=int(ni[0].strip(" "))
                        codeU=ni[1].strip(" ")
                        codeD=ni[2].strip(" ")
                        if len(codeU)>4 or len(codeD)>4: raise ValueError
                        iocodes[nb]=(codeU, codeD)
                except ValueError:
                        print(Err_config)                     # *** Configuration error *** 
                        print("-->", [li], "\n")
        return iocodes

#=============================================================
def initialize(sv, iocodes):                                                         # required by Whand         
    """
    Initializes i/o variables
    Puts iocodes provided by Whand into a dictionary:
    """
    global Input_state
    global Codes
    
    if sv.Do_tests: return
    Input_state.clear()                                                              # initialize input dictionary
    Codes=iocodes                                                                  # dictionary of i/o codes
    Scriptname=["","","","","","","",""]                                       # list of names of scripts
    # check input and output numbers
    try:
        Pins=[int(pin[len(Pin)+1:-1]) for pin in sv.Pinlist]
        Outputs=[int(pin[len(Output)+1:-1]) for pin in sv.Outlist]
    except:
        print(Err_io_number)
        print(sv.Pinlist)
        print(sv.Outlist)
        raise ReferenceError  
    dr.init_hardware(Pins, Outputs)

#===================================================== init_interrupts  
def init_interrupts(sv):
    """
    initialize interrupts for declared pins only
    box is one instance of the hardware
    nb is an input pin number for this box
    """
    box=sv.Boxnumber
    for pi in sv.Pinlist:
        num=pi[4:-1]
        if checknumber(num):                                                    # extract pin number      
            nb=int(num)
            dr.init_pin_callback(box, nb)
            dr.activate_interruption(box, nb)

#=============================================================
def initbox(sv, sourcename):                                                  # required by Whand         
    """
    Initializes each box
    Initializes input list
    Opens file for event logging
    This function prepares execution but does not correspond to actual start (see function 'run')
    Whand calls this function but does not expect any return
    """
    global Input_state
    global Inpause
    global Mylog
    global Mybuff
    global Svlist
    global Boxinputs
    global Scriptname
    global Filename

    sv.t0=clock()
    box=sv.Boxnumber
    Scriptname[box]=sourcename
    dr.open_one_box(box)                                               # initialize access to box
    for pin in sv.Pinstate:
        nb=int(pin[4:-1])+Boxinputs*box
        Input_state[nb]=False

    if sv.Do_tests: return
    if not Nosave:
        Svlist.append(sv)
        if Autoname:                                                                      # automatic naming of result files
            date=("0"+str(localtime().tm_mon))[-2:]+("0"+str(localtime().tm_mday))[-2:]
            prefix="wh"+date+"_"
            fname=os.path.join(Datadir, prefix+"01_"+str(box+1)+".e01")
            num=1
            while os.path.isfile(fname):
                num+=1
                ser=str(num)
                if len(ser)==1: ser="0"+ser
                fname=os.path.join(Datadir, prefix+ser+"_"+str(box+1)+".e01")
        elif box==0:                                # ask name
            Filename=""
            ok=False
            while not ok:
                print(Prompt_data_file, end="")                     # \nSelect file to output results ?
                Filename=input_text()                                             
                fname=os.path.join(Datadir, Filename+str(box+1)+".e01")
                if not os.path.isfile(fname):
                    ok=True
                else:
                    print(Prompt_file_exist, end="")                 # File exists: overwrite (Y/N) ? 
                    answ=input_text()
                    if answ in ["y", "Y"]: ok=True
            if "\\" in Filename:                                                        # verify or create directory
                dirname=Filename[:Filename.rfind("\\")]
                dirname=os.path.join(Datadir, dirname)
                os.makedirs(dirname, exist_ok=True)
            elif "/" in Filename:                                                        # verify or create directory
                dirname=Filename[:Filename.rfind("/")]
                dirname=os.path.join(Datadir, dirname)
                os.makedirs(dirname, exist_ok=True)
        else:                                                                                  # use provided name
            fname=os.path.join(Datadir, Filename+str(box+1)+".e01")

        try:
            Mylog[box]=open(fname, 'w')                                           # overwrite mode
            Mybuff[box]=""                                                                 # to save log to file
        except IOError:
            print(Err_create, Filename, "***\n")               # *** Unable to create Filename ***
            finish()
            waitforuser()
            os._exit(1)

#==============================================================
def run(sv):                                                                          # required by Whand
    """
    This function is required to start execution of each box
    Initializes a reference time in each box for logging
    """
    global Mylog
    global Started
    global Scriptname
    box=sv.Boxnumber
    Started[box]=True
    sv.t0=clock()
    if sv.Do_tests: return
    if Mylog[box]: header(sv, box)

#==============================================================
def header(sv, box):                                                                          # required by Whand
    """
    Output box information to file
    This function is called by run for each box
    and at close time if box has not been started
    """
    global Mylog
    global Started
    global Scriptname

    date=("0"+str(localtime().tm_mday))[-2:]+"/"+("0"+str(localtime().tm_mon))[-2:]+"/"+str(localtime().tm_year)
    time=("0"+str(localtime().tm_hour))[-2:]+":"+("0"+str(localtime().tm_min))[-2:]+":"+("0"+str(localtime().tm_sec))[-2:]
    res=Mylog[box].name
    script=Scriptname[box]
    Mylog[box].write(Header1)       ##    Header1="Date version:    18/04/2017\nDate expérience:\t"
    Mylog[box].write(date+"\n")
    Mylog[box].write(Header2)       ##    Header2="Heure expérience:\t"
    Mylog[box].write(time+"\n")
    Mylog[box].write(Header3)       ##    Header3="Expérience dans cage:\t" 
    Mylog[box].write(str(box+1)+"\n")
    Mylog[box].write(Header4)       ##    Header4="Animal:\t0\nNuméro séance:\t0\nSéance précédente:\t0\n"
                                                      ##    Header4+="Séance suivante:\t0\nGène:\t\nTraitement:\t\nDose:\t\nVoie:\t\n"      
                                                      ##    Header4+="Solvant:\t\nProduit2:\t\nLésion:\t\nRemarque:\t\nNom fichier données:\t"
    Mylog[box].write(res+"\n")
    Mylog[box].write(Header5)       ##    Header5="Nom fichier exercice:\t" 
    Mylog[box].write(script+"\n")
    Mylog[box].write(Header6+"\n")       ##    Header6="[fin section etiquette]\n\n Instant(s10):   Event1: Event2: Event3:"

    
#==============================================================
def closebox(sv):                                                                          # required by Whand
    """
    This function is required to clean up when execution of one box terminates
    Resets all outputs via whand.driver.py
    Stores buffer and/or close log file
    also closes yoked boxes
    Whand calls this function but does not expect any return
    """
    global Mylog
    global Mybuff
    global Started
    if sv.Do_tests: return
    for b in sv.masterto:                                                              # also close yoked boxes
        box=b-1
        if not Nosave:
            if Mylog[box]:                                                                # if file has not been closed
                if not Started[box]: header(sv, box)                          # add header to file
                if not Online_save: Mylog[box].write(Mybuff[box])   # save log to file and/or close it
                msg=buildtime(clock()-sv.t0)
                msg+="99\n"                                     
                Mylog[box].write(msg)                                     
                Mylog[box].write(Legend)
                Mylog[box].close()
                Mylog[box]=None                                                     # mark file as closed

        if Started[box]:
            print(Msg_end_box, box+1, "***")                                             # *** Terminating box
            dr.close_one_box(box)                                                              # close hardware 
        Started[box]=False

#==============================================================
def finish():                                                                          # required by Whand
    """
    This function is required to clean up on exit 
    Stores buffer and/or close log file
    Resets the whole hardware via whand.driver.py
    Whand calls this function but does not expect any return
    """
    # beware of order of instructions below
    global Mylog
    global Mybuff
    global Svlist   
    global Started

    if not Nosave:
        for sv in Svlist:
            box=sv.Boxnumber
            if Mylog[box]:                                          # if file has not been closed
                if not Online_save: Mylog[box].write(Mybuff[box])   # save log to file and/or close it
                msg=buildtime(clock()-sv.t0)
                msg+="99\n"                                     
                Mylog[box].write(msg)                                     
                Mylog[box].write(Legend)
                Mylog[box].close()
                Mylog[box]=None                                # mark file as closed
            Started[box]=False

    if Svlist:
        dr.close_hardware()                                      # clean up on exit                

    if not Nosave:
            export()                                                     # save screen data

#=============================================================
def export():                                                                             # called by finish
    """
    This function exports visible variables from screen to text file (.xls)
    """
    fname=os.path.join(Datadir, Filename+".xls" if Filename else "export.xls")
    try:
        exportfile=open(fname, 'w')                                                    # overwrite mode
        Vu=[]
        for i, sv in enumerate(Svlist):
            if sv.Visible!=Vu:
                Vu=sv.Visible
                title="Runfile\tSavefile\tScript\tBox\tTime\t"
                for nam in sv.Visible:
                    title+=nam+"\t"
                exportfile.write(title[:-1]+"\n")
            values=Runfilename+"\t"+fname[len(Datadir)+1:]+"\t"+removepath(Scriptname[sv.Boxnumber])+"\t"+str(i+1)+"\t"+('%9.3f' % sv.Current_time)+"\t"
            for nam in sv.Visible:
                if sv.Object[nam].nature==["bln"]:
                    values+=str(sv.Object[nam].count)+"\t"
                else:
                    values+=str(sv.Object[nam].value)+"\t"
            exportfile.write(values[:-1]+ "\n")
        exportfile.close()
    except IOError:
        print(Err_create, Filename, "***\n")                                # *** Unable to create
        waitforuser()
        os._exit(1)

#================================================================
def clearbuffer(sv):                                                                   # required by Whand
    """
    This function is called by whand_sharevars
    clears input buffer for the current script instance 
    """
    global DoubleBuffer
    box=sv.Boxnumber
    DoubleBuffer[box]=[[],[]]
    
#================================================================
def setpin(sv, pinnumber, status, tim=0):                          # required by Whand
    """
    Output Booleans in Whand. Sets one output at a time
    There is currently no analog output available
    pinnumber expects a number or a string representing a number (positive integer)
    Floats are truncated, non-numbers, negative or zero values are ignored (no error)
    status must have a Boolean value (ignored otherwise, no error)
    Sets physical output to 1 if status is True, to 0 if False, no change if None
    Logs or stores information to file, with exact time provided by Whand
    Also controls yoked boxes
    Whand calls this function but does not expect any return
    """
    if sv.Do_tests: return
##    print("output", pinnumber, status)
    global Mylog
    global Mybuff
    global Codes

    x=checknumber(pinnumber)                 # check argument
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return                                      # now use nb instead of pinnumber
    st=checkboolean(status)                       # check argument
    if st is None: return                               # now use st instead of status
    bit=1 if st else 0
    for b in sv.masterto:                                                   # also control yoked boxes
        box=b-1
        ##  call output driver
        dr.write_one_bit(box, nb, bit)

        if not Nosave and Started[box]:                                       # do not record before start
            cd=Codes[nb] if nb in Codes else ("NA", "NA")           # store info to file or buffer                 
            msg=buildtime(tim)                                           # ("%d" % (tim*Split_second))+"\t"                                       
            msg+=cd[0] if st else cd[1]                                                 
            if Online_save:
                Mylog[box].write(msg+'\n')
            else:
                Mybuff[box]+=msg+'\n'

#================================================================
def getpin(box, pinnumber):                        # called by scanpins if Use_interrupts is False
    """
    Directly read one input without interrupts and returns state 0 or 1
    Does not log data
    scanpins calls this function and uses the returned value
    """
    global Mylog
    global Mybuff
    global Codes
    st=None
    x=checknumber(pinnumber)                 # check argument
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return st                                   # now use nb instead of pinnumber
    
    st=dr.read_one_pin(box, nb)                 # call driver
    return st

#================================================================
def scanpins(sv):                                            # called by readpins if Use_interrupts is False
    """
    Checks inputs for one box without interrupts if Use_interrupts is False
    Scans all declared pins and looks for state change
    Uses exact time from clock
    Stores change events in double buffer
    Does not log data
    readpins calls this function then reads the double buffer
    """
    global Input_state
    global Boxinputs
    global DoubleBuffer
    global BufferPointer

    box=sv.Boxnumber
    exact_time=clock()                                                           # use real time
    for num in Input_state:                                                     # list of active pins
        pinnumber=num-Boxinputs*box
        if pinnumber>0 and pinnumber<=Boxinputs:
            st=False
            st=getpin(box, pinnumber)                                 # get current value
            if Simulatepin: st=dr.simulate_one_pin(box, pinnumber, sv.Current_time)
            if Printout:  print("scanpin getpin", box+1, num, pinnumber, st)
            if st!=Input_state[num]:                                            # only store if state has changed
                Input_state[num]=st
                nb="P"+str(pinnumber)                                       # compatibility with keys ("K")                                
                DoubleBuffer[box][BufferPointer[box]]+=[(nb, st, exact_time)] # store event and time
                if Printout: print("Pin", nb, "of box", box+1, "has changed to", st)

#================================================================
def readpins(sv):                                                                   # required by Whand
    """
    This function is compatible with access to input pins through interrupts
    Scans inputs without interrupts if Use_interrupts is False
    Scans for input in double buffer, clears buffer
    Logs or stores information to file, with time provided by interrupts
    Whand expects this function to return the most recent info from double buffer
    """
    global Parallel
    global DoubleBuffer
    global BufferPointer
    global Mybuff

    if sv.Do_tests: return
    if not Use_interrupts:
        dr.read_all_pins()                                                    # get current hardware values
        scanpins(sv)                                                           # directly read pin input
    box=sv.Boxnumber
    BufferPointer[box]=1-BufferPointer[box]                  # first switch buffer to catch next interrupt
    ch=DoubleBuffer[box][1-BufferPointer[box]]            # collect last changes 
    DoubleBuffer[box][1-BufferPointer[box]]=[]              # clear changes
    
    if (Printout or not Nosave) and Started[box]:                         # log or print results
        for nb, st, tim in ch:
            msg=buildtime(tim-sv.t0)                 #    ("%d" % ((tim-sv.t0)*Split_second))+"\t"
            if nb[0]=="P":
                nb=-int(nb[1:])
                cd=Codes[nb] if nb in Codes else ("0", "0")   # keep it numeric
                msg+=cd[0] if st else cd[1]
            else:
                nb=-int(nb[1:])                              # key press
                msg+=str(nb)                             # negative ascii code of key
            if Printout: print(msg)            
            if not Nosave and Started[box]:
                if Online_save:
                    Mylog[box].write(msg+'\n')
                else:
                    Mybuff[box]+=msg+'\n'

    for i,  (nb, st, tim) in enumerate(ch):                               
        if nb[0]=="P":
            nb="P"+str(int(nb[1:]))
        ch[i]=(nb, st, tim-sv.t0)
##    print(ch)    
    return ch

#================================================================
def keyscan():                                                                    # required by Whand
    """
    Scans for keypressed and stores result in double buffer
    inputs are stored with their actual time into double buffer
    Does not log data
    does not work under Idle mode
    Whand calls this function then readpins reads the double buffer
    """
    global DoubleBuffer
    global BufferPointer
##    global T0
    global Lastkey

    if not Withkeys: return                                      # ignored if module has not been loaded
    exact_time=clock()                                           # use real time

    if not kbhit(): return
    car=getcar()
    Lastkey=car                                                     # used by testpause
            
    nb="K"+str(ord(car))#[2:-1]                                  # for compatibility with pins ("K")                               
    DoubleBuffer[0][BufferPointer[0]]+=[(nb, 1, exact_time)]        # store event and time
    if Printout: print('Key "'+nb+'" has been pressed at', ("%d" % (exact_time*Split_second)))

# The following function is needed when using Whand control panel
#================================================================
def panelpin(sv, nb, st, exact_time=0):                             # required by Whand control panel
    """
    Record pin input from control panel into double buffer
    with exact time provided by Whand control panel
    sv is script instance, nb is pin number, st is Boolean status of this input
    Does not log data
    readpins will read the double buffer if not empty
    Whand controlpanel calls this function but does not expect any return
    """
    global Parallel
    global DoubleBuffer
    global BufferPointer
    box=sv.Boxnumber
    nb="P"+str(nb)                       # n.b. use with controlpanel is incompatible with key press                       
    DoubleBuffer[box][BufferPointer[box]]+=[(nb, 1 if st else 0, exact_time)]# store event and controlpanel time
    if Printout: print("Box", box+1, "Pin", nb, "has changed to", st)

#================================================================
def getanalog(sv, ADnumber, tim=0):                            # required by Whand
    """
    Input driver for numbers in Whand. Scans one input at a time
    There is currently no analog input available
    ADnumber expects a positive integer, floats are truncated, negative or zero ignored
    tim expects a positive or zero number, float or integer (may be omitted)
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Returns value of analog input, None if unknown
    """
    global Mybuff
    if sv.Do_tests: return 9.99 # dr.read_one_AD(1, ADnumber) 
    box=sv.Boxnumber
    res=None                                              # return variable
    x=checknumber(ADnumber)                 # check arguments
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return                                      # now use nb instead of ADnumber
    curt=checknumber(tim)                        # check arguments
    if curt is None: curt=0                           # now use curt instead of exact_time

# add here driver to actually read analog input into res
    res=dr.read_one_AD(box, ADnumber)              
    if (Printout or not Nosave) and Started[box]:
        msg=buildtime(tim)                      #  ("%d" % (tim*Split_second))
        msg+="measure "+str(nb)+" :"+str(res)
        if Printout: print(msg)
        if not Nosave and Started[box]:
            if Online_save:
                Mylog[box].write(msg+'\n')
            else:
                Mybuff[box]+=msg+'\n'                                                        
    return res

#================================================================
def readmessage(sv, address, tim=0):                            # required by Whand
    """
    Input driver for text in Whand. Scans one input at a time
    There is currently no text input available
    address expects a positive integer, floats are truncated, negative or zero ignored
    tim expects a positive or zero number, float or integer (may be omitted)
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Returns value of text input, None if unknown
    """
    global Mybuff
    if sv.Do_tests: return "ok" 
    box=sv.Boxnumber
    res=None                                              # return variable
    x=checknumber(address)                     # check arguments
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return                                      # now use nb instead of ADnumber
    curt=checknumber(tim)                       # check arguments
    if curt is None: curt=0                           # now use curt instead of exact_time

# add here driver to actually read analog input into res
    res=dr.read_message(box, address)              
    if (Printout or not Nosave) and Started[box]:
        msg=buildtime(tim)                      #  ("%d" % (tim*Split_second))
        msg+="reading "+str(nb)+" :"+str(res)
        if Printout: print(msg)
        if not Nosave and Started[box]:
            if Online_save:
                Mylog[box].write(msg+'\n')
            else:
                Mybuff[box]+=msg+'\n'                                                        
    return res

#================================================================
def readtouch(sv, filename, X, Y, tim=0):                            # required by Whand
    """
    Input driver for touchscreen. 
    filename is None or the file containing an image
    tim expects a positive or zero number, float or integer (may be omitted)
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Returns None or coordinates of touch and whether it is on target
    """
    global Mybuff
    if sv.Do_tests: return 100, 100, True 
    box=sv.Boxnumber
    res=None                                              # return variable
    curt=checknumber(tim)                        # check arguments
    if curt is None: curt=0                           # now use curt instead of exact_time

# add here driver to actually read screen touch into res
    res=dr.read_touchscreen(box, filename, X, Y)              
    if (Printout or not Nosave) and Started[box]:
        msg=buildtime(tim)                      #  ("%d" % (tim*Split_second))
        msg+="reading screen for"+(filename if filename else "")+" :"+str(res)
        if Printout: print(msg)
        if not Nosave and Started[box]:
            if Online_save:
                Mylog[box].write(msg+'\n')
            else:
                Mybuff[box]+=msg+'\n'                                                        
    return res

#================================================================
def outcommand(sv, outnumber, value, tim=0):                            # required by Whand
    """
    Driver for number output in Whand
    outnumber expects a channel number or a string representing a number (positive integer)
    tim expects a positive or zero number, float or integer (may be omitted)
    Ignores None value
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Also controls yoked boxes
    Whand calls this function but does not expect any return
    """
    if sv.Do_tests: return
    x=checknumber(outnumber)                 # check argument
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return                                      # now use nb instead of pinnumber
    if value is None: return
    
    for b in sv.masterto:                                  # also output to yoked boxes
        box=b-1
        if nb is not None and Started[box]:
            dr.write_message(box, nb, value)      # calls  output driver code
            cd=str(value)
            if value==int(value): cd=str(int(value)) # no decimals for integers
            msg=buildtime(tim)                          # ("%d" % (tim*Split_second))+"\t"
            msg+=cd                                         # store info to file or buffer                                  
            if Printout: print(msg)
            if not Nosave and Started[box]:
                if Online_save:
                    Mylog[box].write(msg+'\n')
                else:
                    Mybuff[box]+=msg+'\n'                                                        

#================================================================
def outmsg(sv, outnumber, code, tim=0):                            # required by Whand
    """
    Driver for string output in Whand. Outputs one string of chars
    outnumber expects a channel number or a string representing a number (positive integer)
    tim expects a positive or zero number, float or integer (may be omitted)
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Also controls yoked boxes
    Whand calls this function but does not expect any return
    """
    if sv.Do_tests: return
    x=checknumber(outnumber)                 # check argument
    nb=0 if x is None else int(x)                  # truncate to integer
    if nb<1: return                                      # now use nb instead of pinnumber
    if code is None: return
    cd=str(code)                                         # now use cd instead of code
    
    for b in sv.masterto:                               # also output to yoked boxes
        box=b-1
        if nb is not None and Started[box]:
            dr.write_message(box, nb, cd)         # calls  output driver code
            msg=buildtime(tim)                          # ("%d" % (tim*Split_second))+"\t"
            msg+=cd                                         # store info to file or buffer                                  
            if Printout: print(msg)
            if not Nosave and Started[box]:
                if Online_save:
                    Mylog[box].write(msg+'\n')
                else:
                    Mybuff[box]+=msg+'\n'                                                        

#================================================================
def display(sv, filename, X, Y, closing=False, tim=0):         # required by Whand
    """
    Driver for image display in Whand.
    filename is the file containing the image (already sized, w or w/o transparency)
    X and Y are the coordinates for the upper left corner of the window
    closing is True if image is present and must be closed
    tim expects a positive or zero number, float or integer (may be omitted)
    box is 0 to Boxes-1
    Logs or stores information to file, with exact time provided by Whand
    Also controls yoked boxes
    Whand calls this function but does not expect any return
    """
    if sv.Do_tests: return
    for box in sv.masterto:                                  # also control yoked boxes
        if Started[box-1]:
            dr.display_image(box, filename, X, Y, Displayed, closing)   # calls  output driver code
            msg=buildtime(tim)                          # ("%d" % (tim*Split_second))+"\t"
            msg+=filename                                        # store info to file or buffer
            msg+=str(X)
            msg+=str(Y)
            if closing: msg+="close"
            if Printout: print(msg)
            if not Nosave and Started[box]:
                if Online_save:
                    Mylog[box].write(msg+'\n')
                else:
                    Mybuff[box]+=msg+'\n'                                                        

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
    global Inpause
    global Lastkey
    if not Lastkey: return Inpause
    if ord(Lastkey)==13 and Inpause!=1:
        Inpause=1                                           # Enter to start
        print(Msg_continue)                            # *** Continue *** 
        Lastkey=""                                           # capture this key
    elif ord(Lastkey)==27 and Inpause==1:
        Inpause=0                                           # Esc to pause
        print(Msg_pause)                                # ***  Pause   ***
        Lastkey=""                                           # capture this key
    return Inpause

#================================================================
def screenprint(li):                                                                    # required by Whand
    """
    final formatting before printing a list to screen with Whand 'print'
    formatting still needs to be improved
    """
    for x in li:
        print(str(x).strip('"'), end="")
    print()

##    txt=""
##    for v in li:
##        unit=""
##        if type(v)==str:
##            if v and v[0]=='"' and v[-1]=='"': v=v[1:-1]          # do not print outer quotes
##            while '""' in v: v=v.replace('""','"')                        # replace double inner quotes
##            if v and v[-1]=="s":                                            # look for durations in s
##                try:
##                    x=float(v[:-1])
##                    v=x
##                    unit="s"
##                except ValueError:
##                    pass
##        if type(v)==float:                                                  # type may have changed to float
##            v=int(v*10**6+.5)/10**6                                   # round to 6 places
##            if int(v)==v: v=int(v)                                         # find integer values
##        txt+=(" " if type(v)!=str else "")+str(v)+unit
##    print(txt)
            
###===================================================== doprint
##def doprint(sv, nom):
##    """
##    Print a list of values to screen. Computes result of formulas. Is it necessary?
##    """
##    if sv.Object[nom].lastchange!=sv.Current_time:
##        sv.Object[nom].lastchange=sv.Current_time     # print only once per timestep
##        vlu=applied(nom, Print)
####        print("xxxx printing:", vlu)
##        args=splitlist(vlu, quotes=True)
##        li=[]
##        for x in args:
####            print("xxxx print arg:", x)
##            if x and not(x[0]==Quote and x[-1]==Quote):        
##                x=pc.singlebrackets(x)
####            print("xxxx print sgbr:", x)
##            v=cm.treebuild(sv, x)
##            if v and v[0].startswith(Special+Bloc) and not v[2]: v=v[1]
####            print("xxxx print value:", v)
##            xp=tree_join(v, spacing=Underscore)
####            print("xxxx print eval:", xp)
##            res=evaluate(sv, (xp, None, None))[0].value
##            if res==xp:
##                res=evaluate(sv, v)[0].value
####            print("xxxx res", res)
##            li+=[res]                           
##        io.screenprint(li)                                          

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
    example of a dialog function
    Whand syntax is of the following form:
    result: when condition: call("dialog(Please enter a value )")
    """
    print(prompt[0]+"> ", end="")                     # arguments always come as a list
    try:
        txt=input()
    except ValueError:
        txt=""
    return txt
        
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

#===================================================== controlled_proba
def controlled_proba(args):
    """
    Pseudo-random sequence generator of 0 and 1 with constraints
    on each block of size block_size, there should be exactly block_ones 1s
    on each sub-block (part) of size part_size, there should be between part_min and part_max 1s
    there should not be more than max_seq_0 consecutive 0s
    there should not be more than max_seq_1 consecutive 1s
    this should remain true at the transition between blocks
    if no solution is found, the block is discarded and a new block is generated
    """
    from random import random  # function random() generates a random float uniformly in the semi-open range [0.0, 1.0)
    # Parameters (convert from list)
    if not args: return []
    nb_blocks=int(args[0])                   # how many consecutive blocks to generate (e.g. 15)
    block_size=int(args[1])                  # size over which the frequency is defined (e.g. 20)
    block_ones=int(args[2])                # exact number of 1s over each block_size (e.g. 15)
    part_size=int(args[3])                    # size of a sub-block where the frequency is limited (e.g. 5)
    part_min=int(args[4])                    # minimum number of 1s in a sub-block (e.g. 3)
    part_max=int(args[5])                   # maximum number of 1s in a sub-block (e.g. 4)
    max_seq_0=int(args[6])                 # max length of series of 0s (e.g. 1)
    max_seq_1=int(args[7])                 # max length of series of 1s (e.g. 8)

    max_iter=100                 # limit of search with constraints before discarding

    #-----------------------------------------------------------------
    def analyze(part, prev0=0, prev1=0):
        """
        Analyse a proposed sub-block
        Returns the number of 1s in sub-block, the maximum sequence of 0s and 1s
        and the last sequence of 0s or 1s
        prev0 and prev1 are the final sequences of 0s or 1s in the previous sub-block
        this allows control of sequences across transitions between sub-blocks
        """
        seq0=prev0                                              # store values until a satisfactory sub-block is found 
        seq1=prev1
        top_seq0=prev0     # maximum sequence length of 0s initialized with end of previous sub-block
        top_seq1=prev1     # maximum sequence length of 1s initialized with end of previous sub-block
        nb_ones=0
        for x in part:
            nb_ones+=x                                         # count 1s
            if x==0:
                seq0+=1                                          # count consecutive 0s
                if seq1>top_seq1: top_seq1=seq1     # store largest
                seq1=0
            else:
                seq1+=1                                          # count consecutive 1s
                if seq0>top_seq0: top_seq0=seq0     # store largest
                seq0=0
        if seq0>top_seq0: top_seq0=seq0             # check largest before returning
        if seq1>top_seq1: top_seq1=seq1             # check largest before returning
        return nb_ones, top_seq0, top_seq1, seq0, seq1

    #-----------------------------------------------------------------
    def generate_part(part, prev0=0, prev1=0):
        """
        generate a sub-block according to constraints
        Returns a copy of sub-block, number of 1s, last sequences of 0s or 1s and number of iterations
        prev0 and prev1 are the final sequences of 0s or 1s in the previous sub-block
        this allows control of sequences across transitions between sub-blocks
        if no solution is found after max_iter, return with a signal to discard whole block (itere==max_iter)
        """
        itere=0                                                     # maximum number of iterations
        good=False                                              # flag for a valid sub-block
        while not good and itere<max_iter:           # restart sub-block if not valid, limit iterations
           itere+=1
           good=True
           for i in range(part_size):                          # generate a random sub-block
               part[i]=1 if random()<proba else 0      # probability of 1s is matched to required frequency
           ones_in_part, seq0, seq1, lastseq0, lastseq1=analyze(part, prev0, prev1)  # analyze
           if ones_in_part<part_min: good=False     # discard if not enough 1s
           if ones_in_part>part_max: good=False    # discard if too many 1s
           if seq0>max_seq_0: good=False             # discard if too long sequence of 0s
           if seq1>max_seq_1: good=False             # discard if too long sequence of 1s
        return list(part), ones_in_part, lastseq0, lastseq1, itere

    #=======================================  main program
    # Initialize
    part=part_size*[0]                                  # reserve space for a sub-block 
    ones_in_part=0                                      # counters
    ones_in_block=0                                    # number of ones in a block 
    lastseq0=0                                             # sequence of 0s at end of previous block
    lastseq1=0                                             # sequence of 0s at end of previous block
    itere=0                                                   # number of iterations

    # Generate blocks
    whole=[]
    proba=float(block_ones)/block_size                # probability of 1s is matched to required frequency
    for i in range(nb_blocks):                       # multiple blocks
        ok=False                                           # flag for a valid block
        while not ok:                                     # try to construct a valid block
            seq0=lastseq0                               # store end sequence of previous block until a valid block is found
            seq1=lastseq1                               # store end sequence of previous block until a valid block is found
            block=[]                                        # initalize empty block
            total_ones=0                                 # initialize number of 1s in block
            while len(block)<block_size and itere<max_iter:           # increment block with sub-blocks
                new_part, ones_in_part, seq0, seq1, itere=generate_part(part, seq0, seq1)
                block+=new_part                      # increment block with the valid sub-block   
                total_ones+=ones_in_part         # update number of 1s in block
            if itere==max_iter:                         # discard block if no valid sub-block can be found
                ok=False
            elif total_ones==block_ones:          # exactly the required number of 1s
                ok=True                                    # valid block
                lastseq0=seq0                           # update end of block sequence
                lastseq1=seq1                           # update end of block sequence
        whole+=list(block)                            # concatenate blocks while controlling sequence at the junction
    return whole

 ###===================================================== main
if __name__== "__main__":
    print("\n*** whand_io ONLINE ***")
    waitforuser()
    
##    li=getbinfile("../scripts/essai.txt")
##    li=no_line_feed(li)
##    print(bin_to_text(li))
##    print("==================================")
##    li=fuse_continued_lines(li)
##    txt=bin_to_text(li)
##    print(txt)

