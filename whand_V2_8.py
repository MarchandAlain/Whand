# -*- coding: ISO-8859-1 -*-
from __future__ import print_function                                       # Python 2/3 compatibility

# standard modules
import sys
import os                                                                                  # system module, used to exit gracefully
from types import *                                                                  # names for standard types. doc says import * is safe
from functools import lru_cache                                                # cache accelerator

here=os.path.dirname(os.path.abspath(__file__))                      # valid for Python3
sys.path.append(os.path.join(here, "whand_modules"))          # else specify full path
import six                                                                                  # Python 2/3 compatibility
from string import *                                                                  # Python 2/3 compatibility
from random import random, shuffle                                       # a few functions

# whand modules
from whand_parameters import *                                             # options, constants
import whand_io as io                                                               # I/O module for files   
##import whand_driver as dr                                                        # I/O module for hardware   
from whand_operators import *                                               # names, constants, messages
import whand_nodes as nd                                                       # object structure and methods 
from whand_tools import *                                                       # useful procedures 
import whand_sharedvars as sp                                                # to create multiple instances
import whand_precompile as pc                                               # to prepare script text file
import whand_compile as cm                                                   # to build program tree
import whand_controlpanel as cp                                             # to display objects in real time
import whand_runtime as rt                                                      # to control execution
import whand_initial as iv                                                         # initializes objects before run
from whand_critic import criticize                                             # verify script reliability

if Pywin:
    import win32console, win32gui, win32con                              # window lock control (needs pywin)
            
##===================================================== make_yoked
def make_yoked(prog):
    """
    remove outputs and exit from slave program
    """
##    print(prog, Crlf)
    lines=prog.split(Crlf)
    li=[]
    ok=True
    for lin in lines:
        if not (lin.startswith(Col) or lin.startswith(When)): ok=True
        if Exit in lin or Output in lin or Command in lin or Write in lin: ok=False
        if ok: li+=[lin]
    prog=Crlf.join(li)
##    print(prog)
    return prog

###===================================================== actual_script
def actual_script(sourcename, master=0):
    showname=io.removepath(sourcename)
    master=0                                                                                    # not yoked
    if sourcename.startswith(Equal) and isnumber(sourcename[1:]):    # yoked script
        showname="yoked"+showname
        master=int(sourcename[1:])
        if master<1 or master>Boxes or scriptlist[master-1].startswith(Equal):
            print(Err_yoked, master)
            raise ReferenceError
        sourcename=scriptlist[master-1]
    return sourcename, master, showname

##===================================================== lock_window
def lock_window(windowlock):
    if Pywin and not autotest and not windowlock:
       windowlock=True
       hwnd = win32console.GetConsoleWindow()                
       if hwnd:
           hMenu = win32gui.GetSystemMenu(hwnd, 0)
           if hMenu:
               win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)
    return windowlock
 
##===================================================== prepare_script
def prepare_script():
    """
    compile and initialize script 
    store result in sv
    parameters sv, sourcename, autotest, box, parallel, iocodes, showname are defined in main procedure
    """
    sv.clear_all()                                                    # reset all variables except Graphic and Debog
    sv.Graphic=False                                             # no controlpanel
    sv.Do_tests=autotest
    sv.Boxnumber=box
    sv.slaveto=master                                           # yoked script if master!=0
    sv.Current_clause=None, None, None
    sv.Current_time=0 
    sv.Counter=0                                                  # debugging variable

    try:                                                            
            tout=io.readscriptfile(sourcename)                
    except IOError:
            print("\n", Err_no_source, "\n-->", sourcename)
            if initialized: io.finish()                              # properly close boxes
            if not IDLE: io.waitforuser()
            os._exit(1)                                                # graceful exit   

    print("building", sourcename)
    prog=pc.precompile(sv, tout)
    if sv.slaveto: prog=make_yoked(prog)
    cm.compile(sv, prog)                                      # compile script
    sv.Graphic=((Show in sv.Object) or parallel) and not Blind in sv.Object      # interactive panel if "show" is detected       

    iv.prepare_program(sv)                                  # full initialization
    if not initialized: io.initialize(sv, iocodes)         # input and output codes for event logging  
    io.init_interrupts(sv)                                          
    io.initbox(sv, showname)                                   
    rt.filestore(sv)                                               # open file(s) for storage if needed                                                                     
    svlist.append(sv)                                           # list of programs
    print("\n============================================")

###===================================================== main
"""
Main program calls whand_io to get a list of script names. Scripts may be run in parallel or sequentially
autotest option and controlpanel option are not compatible.
autotest option specifies that all scripts in directory autotest should be run sequentially without clock.
autotest is the default option in whand_io. whand_io returns this option as a flag.
Parallel scripts are detected by whand_io which returns this option as a flag.
controlpanel option is automatically enabled when scripts are run in parallel.
controlpanel may also be enabled within a script in a sequence.
In that case, detection of controlpanel occurs within main and remains local to this script.
"""
if __name__== "__main__":
    IDLE=sys.stdin.__class__.__module__.startswith('idlelib')          # check if running under IDLE, normally should be "_io"
    autotest=False                                                                      # indicates all tests should be run sequentially without clock
    initialized=False                                                                    # indicates when a closing routine is needed
    new_session=True                                                                # allows to run successive sessions
    windowlock=False                                                                # command is only allowed once
    iocodes=io.getiocodes("config.txt")                                       # codes for event logging 
    if IDLE:
        print("\nYou are running under IDLE: keyboard key input is not available")
    
    while new_session:
        try:
            # initialize session
            print()
            new_session=False
            svlist=[]
            box=0
            testnum=0
            scriptlist, autotest, parallel=io.getscriptlist()                      # read script
            if autotest: debut=io.clock()                                              # store test start time

            # begin loop on script names
            for sourcename in scriptlist:
                sourcename, master, showname = actual_script(sourcename)     # adjust if yoked                                      

                # initialize box                    
                sv=sp.spell()
                try:
                    prepare_script()                                                         # read and compile script, initialize box
                except ReferenceError:
                    if not autotest or not Testerror in sv.Object: raise ReferenceError
                    continue                                                                    # ignore voluntary errors during tests
                initialized=True
                if parallel: box+=1                                                        # increment box channel number
                testnum+=1
                if sv.Do_tests: print("\nTESTING", testnum, sourcename)

                if not sv.Graphic:    
                    # RUN SCRIPTS SEQUENTIALLY WITHOUT CONTROL PANEL                          
                    sv.masterto=[1]                                         # include master box 
                    if autotest:
                        io.Inpause=1                                         # start at once in autotest
                    else:
                        io.waitforuser("Press Enter to start, Ctrl-C to abort")
                        if io.Inpause==2: raise KeyboardInterrupt
                    io.run(sv)                                             
                    sv.t0=io.clock()+Epsilon_time                    # synchro (inputs as delayed events)
                    try:
                        rt.run_update(sv)                                      # START RUNTIME
                    except ReferenceError:
                        if not autotest or not Testerror in sv.Object: raise ReferenceError
                        continue                                                   # ignore voluntary errors during tests                        
                    io.closebox(sv)
                    io.finish()
                        
                    initialized=False           

            if sv.Graphic:                    
                # RUN SCRIPTS IN PARALLEL
                windowlock=lock_window(windowlock)   # prevent window from closing
                for i, sv in enumerate(svlist):                         
                    sv.masterto=[i+1]+sv.masterto                 # include master box
                    if sv.slaveto: svlist[sv.slaveto-1].masterto+=[i+1]  # master control on yoked scripts 
                    sv.Current_time=0                       
                    sv.t0=io.clock()+Epsilon_time                  # synchro (inputs as delayed events)     
                new_session=cp.makebox(svlist, autotest)    # lauch control panel
                
        except ReferenceError:                                      # error
            if initialized:
                io.finish()
                rt.clear_outputs(sv)
                if sv.Current_clause:
                    print("\n-->", sv.Current_clause)
                print(Err_abort)
            if autotest: print("\nTests lasted", io.clock()-debut)
            if not IDLE: io.waitforuser()
            os._exit(1)                                                  # graceful exit   

        except KeyboardInterrupt:	                 # manual abort	    
            if initialized:
                io.finish()
                rt.clear_outputs(sv)
            print(Err_abort, Crlf)
            if Dumps:                                                # dump tree structure
                    print()
                    for x in list(sv.Object.values()):
                        if x.name and x.name[0]!=Special:   
                            print("*", x.content())
                            if x.clauses:
                                for c,v in x.clauses:
                                    print("   cond:", c, "val:",v)
                            print()
        if autotest: print("\nTests lasted", io.clock()-debut)
        if not IDLE: io.waitforuser()
        os._exit(1)

    # no new session        
    if autotest: print("\nTests lasted", io.clock()-debut)
    if not IDLE: io.waitforuser()
    os._exit(1)                                                     # graceful exit

