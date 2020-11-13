# -*- coding: ISO-8859-1 -*-
"""
This module contains drivers to interface Whand with physical inputs and outputs (except files)
Drivers should be adapted to each physical system
There should be no reference in here to other Whand modules except whand_parameters
Each box is an independent setup running a Whand script in parallel
An entry to the functions below is expected, even if the function is not really implemented:

init_hardware()                                                                          # open access to the hardware
open_one_box(box)                                                                  # initializes access to one box
init_pin_callback(box, nb)                                                          # needed even if no interrupt is used
activate_interruption(box, nb)                                                   # needed even if no interrupt is used
read_all_pins()                                                                           # read all box bit inputs at once
read_one_pin(box, nb)                                                              # read a single bit input
simulate_one_pin(box, pinnumber, time)                                  # simulate a single bit input
write_one_bit(box, nb, bit)                                                        # write a single bit output (0 or 1)
read_one_AD(box, ADnumber)                                                  # read a single analog port
write_one_DA(box, DAnumber, value)                                       # write to a single analog port
read_message(box, nb)                                                             # input a text to a port
write_message(box, nb, text)                                                     # output a text to a port
display_image(filename, X, Y)                                                    # display image from file 
read_touchscreen(filename, X, Y)                                               # test touch on image
close_one_box(box)                                                                   # terminate one box
close_hardware()                                                                        # reset and close access to the hardware

Logical values for pins and bit outputs are 0 or 1
Numbers or times are in float format with at least one digit
Message is any string
Lists are not exchanged here, only through files in whand_io

Current driver is implemented for ASi interface (Imetronic) without interrupts
There are currently 12 inputs and 12 outputs
Pin with numbers above 12 will be accessible through controlpanel only
""" 

from __future__ import print_function                          # Python 2/3 compatibility
import os                                       
import sys
from ctypes import*                                                    # needed to access ASi though dll
from whand_parameters import *                               # options
import whand_controlpanel as cp                              # needed for display

# Global variables needed to access ASi through dll in C
if Hardware==ASi:                                                      # option in whand_parameters.py
    libname="ASIDRV32.dll"                                         # not the standard ASi dll
    s_IniFileName="AsiDrv32_c1.ini"                             # Python string
    s_Settings="asipci.dll: ID 0xFFFF Circ 1"                  # Python string
    b_IniFileName=s_IniFileName.encode('utf-8')         # create byte object from string
    b_Settings=s_Settings.encode('utf-8')                     # create byte object from string
    b_EcFlags=create_string_buffer(2)                           # create mutable byte array
    b_LDS=create_string_buffer(8)                                 # create mutable byte array
    b_LPS=create_string_buffer(8)                                 # create mutable byte array
    b_ODI=create_string_buffer(32)                               # create mutable byte array
    b_IDI=create_string_buffer(32)                                # create mutable byte array
    b_Errname=create_string_buffer(32)                        # create mutable byte array
    # ctype conversion
    IniFileName=c_char_p(b_IniFileName)                     # *char
    Settings=c_char_p(b_Settings)                                 # *char
    EcFlags=cast(b_EcFlags, c_char_p)                           # *char (not unsigned but...)
    HiFlags=c_int(5)                                                       # int
    LDS=cast(b_LDS, c_char_p)                                      # *char (not unsigned but...)
    LPS=cast(b_LPS, c_char_p)                                       # *char (not unsigned but...)
    ODI=cast(b_ODI, c_char_p)                                      # *char (not unsigned but...)
    IDI=cast(b_IDI, c_char_p)                                         # *char (not unsigned but...)
    Errname=cast(b_Errname, c_char_p)                        # *char (mutable)
    MasterID=c_int(0)                                                    # int
    TimedOut=c_int(0)                                                   # int
    Mode=c_int(0)                                                         # int
    Milliseconds=c_int(2000)                                         # int
    Error=c_int(0)                                                          # int
    Errcode=c_int(0)                                                      # int
    my_dir=os.sys.path[0]                                              # get absolute path
    libname=os.path.join(my_dir, libname)
    mydll = windll.LoadLibrary(libname)                       # load dll to access ASi
    print("* Library ASIDRV32.dll loaded")

# Initialization ============================================
def init_hardware(Pinlist, Outlist):                                 # required by Whand         
    """
    Initializes ASi
    Tests whether the hardware is on (else exits)
    Pinlist and Outlist are lists of the names of used inputs and outputs
    whand_io calls this function but does not expect any return
    """
    if Hardware==ASi:
        print("Initializing ASi")
        Error=mydll.ASiRegisterMaster(byref(MasterID))
        if Error or Debug:
            print("* ASiRegisterMaster(&MasterID)")
            print("  MasterID:", MasterID, ", error code", "0x"+"{:02x}".format(Error))

        Error=mydll.ASiRegisterIniFileName(MasterID, IniFileName)
        if Error or Debug:
            print("* ASiRegisterIniFileName(", MasterID, ",", str(IniFileName)[10:-1], ")")
            printhex(Error)

        Error=mydll.ASiInit(MasterID, Settings)
        if Error or Debug:
            print("* ASiInit(", MasterID, ",", str(Settings)[10:-1], ")")
            printhex(Error)

        Error=mydll.ASiWriteHiFlags(MasterID, HiFlags)
        if Error or Debug:
            print("* ASiWriteHiFlags(", MasterID, ",", HiFlags, ")")
            printhex(Error)

        Error=mydll.ASiSetConfigMode(MasterID, Mode)
        if Error or Debug:
            print("* ASiSetConfigMode(", MasterID, ",", Mode,")")
            printhex(Error)

        Error=mydll.ASiReadEcFlags(MasterID, byref(EcFlags))
        if Error or Debug:
            print("* ASiReadEcFlags(", MasterID, ", &EcFlags)")
            print("  EcFlags:", "0x"+" 0x".join("{:02x}".format(x) for x in b_EcFlags[:]))
            printhex(Error)

        Error=mydll.ASiSetWatchdog(MasterID, Milliseconds)
        if Error or Debug:
            print("* ASiSetWatchdog(", MasterID, ",", Milliseconds,")")
            printhex(Error)

        Error=mydll.ASiDataExchange(MasterID, byref(b_ODI), byref(b_IDI), byref(EcFlags))
        inp=0                                                                            # verify data can be read
        for cage in range(8):
            for module in range(3):
                for bit in range(4):
                    inp+=(extract_bit(cage, module+1, bit+1))
        if Error or not inp:
            print("*** OOPS: no hardware detected ! ***")  
            exitASi(MasterID)
            wait_for_user()
            os._exit(1)

#=============================================================
def open_one_box(box):                                              # required by Whand
    """
    initializes access to one box
    """
    pass
 
#=============================================================
def init_pin_callback(box, nb):                                       # required by Whand
    """
    This function is always called by whand_io.py
    Only needs to perform something if input pins are accessed through interrupts
    Assigns callback for interrupt
    box is one instance of the hardware
    nb is an input pin number for this box
    Whand calls this function but does not expect any returned value
    """
    pass                                                                            # interrupts are not used

#============================================================== 
def activate_interruption(box, nb):                                  # required by Whand
    """
    This function is always called by whand_io.py
    Only needs to perform something if input pins are accessed through interrupts
    Activates interrupt detection for one pin input 
    Whand calls this function but does not expect any return
    """
    pass                                                                            # interrupts are not used
    
#================================================================
def read_all_pins():                                                          # required by Whand
    """
    This function is called by whand_io.py
    Directly read inputs without interrupts if Use_interrupts is False
    Gets input for all boxes
    """
    if Hardware==ASi:
        global mydll
        global b_ODI
        global b_IDI
        global b_EcFlags

        # read all inputs
        Error=mydll.ASiDataExchange(MasterID, byref(b_ODI), byref(b_IDI), byref(EcFlags))
        if Error:
            print("* ASiDataExchange(", MasterID, ", ODI, IDI, &EcFlags)")
            print("  OA", "0x"+" 0x".join("{:02x}".format(c) for c in b_ODI[:16]))
            print("  OB", "0x"+" 0x".join("{:02x}".format(c) for c in b_ODI[16:]))
            print("  IA  ", "0x"+" 0x".join("{:02x}".format(c) for c in b_IDI[:16]))
            print("  IB  ", "0x"+" 0x".join("{:02x}".format(c) for c in b_IDI[16:]))
            print("  EcFlags:", "0x"+" 0x".join("{:02x}".format(x) for x in b_EcFlags[:]), ", error code", "0x"+"{:02x}".format(Error))       

#================================================================
def read_one_pin(box, nb):                                             # required by Whand    
    """ 
    This function is called by whand_io.py
    Directly read one input without interrupts
    box is 0 to Boxes-1
    nb is input pin (1 to ...)
    returns state as 0 or 1
    """
    state=0
    if Hardware==ASi:
        global b_IDI
        module=1+int((nb-1)/4)
        position=1+(nb-1) % 4
        state=extract_bit(box+1, module, position)
    return state

#================================================================
def simulate_one_pin(box, pinnumber, time):                         # required by Whand
    """
    simulates an input
    called by whand_io
    box is 0 to Boxes-1
    nb is input pin (1 to ...)
    time is current time for this box
    returns 0 or 1
    """
    global Simulatepinlist, Simulatepinfreq
    if pinnumber in Simulatepinlist and int(2*Simulatepinfreq*time)%2<1: return 1
    return 0

#================================================================
def write_one_bit(box, nb, bit):                                                  # required by Whand
    """
    Outputs Boolean value to hardware
    There is currently no analog output
    box is 0 to Boxes-1
    nb is output pin (1 to ...)
    bit is 0 or 1
    whand.io calls this function but does not expect any return
    """
    if Hardware==ASi:
        global b_ODI
        global b_IDI
        global b_EcFlags    
        if nb<=12:
            module=1+int((nb-1)/4)
            position=1+(nb-1) % 4
            outlist=[(box+1, module, position, bit)]
            integrate_bit(outlist)
            Error=mydll.ASiDataExchange(MasterID, byref(b_ODI), byref(b_IDI), byref(EcFlags))
            if Error:
                print("* ASiDataExchange(", MasterID, ", ODI, IDI, &EcFlags)")
                print("  OA", "0x"+" 0x".join("{:02x}".format(c) for c in b_ODI[:16]))
                print("  OB", "0x"+" 0x".join("{:02x}".format(c) for c in b_ODI[16:]))
                print("  IA  ", "0x"+" 0x".join("{:02x}".format(c) for c in b_IDI[:16]))
                print("  IB  ", "0x"+" 0x".join("{:02x}".format(c) for c in b_IDI[16:]))
                print("  EcFlags:", "0x"+" 0x".join("{:02x}".format(x) for x in b_EcFlags[:]), ", error code", "0x"+"{:02x}".format(Error))       

#================================================================
def read_one_AD(box, ADnumber):                                            # required by Whand
    """
    Input driver for numbers in Whand. Scans one input at a time
    The current ASi hardware does not support analog input
    called by whand_io
    box is 0 to Boxes-1
    ADnumber identifies the analog input
    returns float value
    """
    res=9.99                                                                                 # dummy value
    return res

#================================================================
def write_one_DA(box, DAnumber, value):                             # required by Whand
    """
    Output driver for numbers (not implemented)
    box is 0 to Boxes-1
    """
    pass

#==============================================================
def read_message(box, nb):                                                   # required by Whand
    """
    Inputs a message string from a port (not implemented)
    box is 0 to Boxes-1
    """
    pass

#==============================================================
def write_message(box, nb, text):                                        # required by Whand
    """
    Outputs a message string to hardware (not implemented)
    box is 0 to Boxes-1
    nb is output number
    text is a string of chars
    whand.io calls this function but does not expect any return
    """
    pass

#==============================================================
def display_image(box, filename, X, Y, Displayed, closing):          # required by Whand
    """
    Displays an image on screen
    box is 0 to Boxes-1
    filename is the file containing the image (already sized, w or w/o transparency)
    X and Y are the coordinates for the upper left corner of the wndow
    closing is True if image is displayed and must be removed
    needs import from whand_controlpanel (cp)
    whand.io calls this function but does not expect any return
    """
    if (filename, X, Y) in Displayed[box]:
        if closing:
            label=Displayed[box][(filename, X, Y)][0]
            Displayed[box][(filename, X, Y)] = None          # remove reference
            del Displayed[box][(filename, X, Y)]
            label.destroy()
    else:
        photo = cp.PhotoImage(file=filename)
        label = cp.Label(image=photo, borderwidth=0)
        label.place(x=X, y=Y)
        Displayed[box][(filename, X, Y)] = label, photo    # keep a reference

#==============================================================
def read_touchscreen(box, filename, X, Y):                      # required by Whand
    """
    Tests contact with target image on screen (not implemented)
    box is 0 to Boxes-1
    filename is the file containing the target image (as in display_image) or None
    X and Y is where the image is supposed to have been displayed (not verified)
    contacts outside image are also detected
    returns None or a triplet of 2 touch coordinates and a Boolean indicating
    whether touch is on target
    whand.io calls this function
    """
    return 100, 100, True                                                     # simulation

#==============================================================
def close_one_box(box):                                                   # required by Whand
    """
    This function is required to clean up when execution of one box terminates
    box is the number of the box to be closed (0 to Boxes-1)
    Resets all outputs to zero
    whand.io calls this function but does not expect any return
    """
    if Hardware==ASi:
        global mydll                                                              # required to access ASi
        for module in range(3):
            nybble=box*3+module+1                                    # position of module
            rang=int(nybble/2)                                               # position of module byte in ODI
            mask=0xf0 if (nybble%2)==0 else 0x0f
            before=int.from_bytes(b_ODI[rang],byteorder='little', signed=False)  # convert bytes to integer
            new=before&mask                                              # clear bit
            b_ODI[ rang]=new                                               # write ODI
        Error=mydll.ASiDataExchange(MasterID, byref(b_ODI), byref(b_IDI), byref(EcFlags))

#==============================================================
def close_hardware():                                                          # required by Whand
    """
    This function is required to clean up on exit 
    disable interrupt detection for  pin inputs and clear outputs 
    whand.io calls this function but does not expect any return
    """
    if Hardware==ASi:
        global mydll                                                               # required to access ASi
        for rang in range(32): b_ODI[ rang]=0                       # clear all outputs                                                            
        Error=mydll.ASiDataExchange(MasterID, byref(b_ODI), byref(b_IDI), byref(EcFlags))
        exitASi(MasterID)                                                        # cleanup ASi
               
# The followng function is not required by Whand but is needed when inputs trigger interrupts
#================================================================
def my_callback(event):                                                   
    """
    This function is required only if input pins are accessed through interrupts
    It must be interfaced with whand_io DoubleBuffer (see io.readpins)
    Keep as short as possible
    """
    pass

# Hardware-specific functions called only from this module  
#===================================
def exitASi(MasterID):                      # Exit (twice)
    """
    Terminates hardware access
    called by init_hardware and close_hardware
    """
    if Hardware==ASi:
    ##    print("* ASiExit(", MasterID," )")
        Error=mydll.ASiExit(MasterID)
    ##    print("  error code", "0x"+"{:02x}".format(Error))
    ##    print("* ASiUnRegisterMaster(", MasterID," )")
        Error=mydll.ASiUnRegisterMaster(MasterID)
    ##    print("  error code", "0x"+"{:02x}".format(Error))
    ##    print("* ASiExit(", MasterID," )")
        Error=mydll.ASiExit(MasterID)
    ##    print("  error code", "0x"+"{:02x}".format(Error))
    ##    print("* ASiUnRegisterMaster(", MasterID," )")
        Error=mydll.ASiUnRegisterMaster(MasterID)
    ##    print("  error code", "0x"+"{:02x}".format(Error))
        
#===================================
def integrate_bit(outlist):
    """
    called by set_one_bit
    recodes a single bit in b_ODI without modifying the rest
    outlist contains a list of quadruplets:
    (boxnumber, module, bitposition, value)
    boxnumber: 1 to 8
    module: 1 to 3
    bitposition: 1 to 4
    value: 0 ou 1, set in b_ODI
    """
    global b_ODI
    for cage, module, bit, valeur in outlist:
        nybble=(cage-1)*3+module                                # position of module in ODI
        rang=int(nybble/2)                                              # position of module in ODI
        position=2**(bit-1+4*(nybble % 2))                     # position of bit in byte
        before=int.from_bytes(b_ODI[rang],byteorder='little', signed=False)  # convert bytes to integer
        new=before&(~position)                                    # clear bit
        if valeur: new=new|position                                 # set bit (if value is 1)
        b_ODI[ rang]=new                                               # write ODI
    return

#===================================
def extract_bit(cage, module, bit):
    """
    decodes one bit from IDI 
    boxnumber: 1 to 8
    module: 1 to 3
    bitposition: 1 to 4
    called by init_hardware and read_one_pin
    """
    global b_IDI
    nybble=(cage-1)*3+module                                # position of module in ODI
    rang=int(nybble/2)                                              # position of module in ODI
    position=2**(bit-1+4*(nybble % 2))                     # position of bit in byte
    value=int.from_bytes(b_IDI[rang],byteorder='little', signed=False)  # convert bytes to integer
    st=value&position                                               # get bit
    return st

#==============================================================
def printhex(Error):
    print("  error code", "0x"+"{:02x}".format(Error))
    stop_if(Error)
    
#===================================
def stop_if(Error):
    if Error:
##        mydll.ASiGetErrorMessage(MasterID, Error,  byref(Errname))
        print("*** Error", "0x"+"{:02x}".format(Error), ",", str(Errname)[11:-2], "***")
        if Hardware ==ASi:
            finish()
            Inpause=2

 #================================================================
def wait_for_user(prompt="\nPress Enter to leave"):               
    """
    Yields control to outside process to wait before continuing execution 
    return code 0 to pause, 1 to continue, 2 to abort  
    Whand calls this function and locks execution until Enter or Ctrl-C is pressed
    """
    print(prompt, end=" ")
    try:
        if sys.version_info[0]==2:
            raw_input()                                  # Python 2.7
        else:
            input()                                             # Python 3
    except KeyboardInterrupt:                  # catch exception to finish process
        raise ReferenceError
    except ValueError:
        pass
           

