# -*- coding: ISO-8859-1 -*-
"""
This module contains drivers to interface Whand with physical inputs and outputs (except files)
Drivers should be adapted to each physical system
There should be no reference in here to other Whand modules except whand_parameters
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

Current driver is implemented for Raspberry pi without interrupts
Only box 1 is actually connected to Raspberry pi
There are currently up to 26 inputs or outputs
A pin must be declared either as an input or an output
An error is raised if input and output numbers collide
pin naming follows BCM (GPIO2 to GPIO27) 
""" 

from __future__ import print_function                          # Python 2/3 compatibility
import os                                       
import sys
from whand_parameters import *                               # options
import whand_controlpanel as cp                              # needed for display
if Hardware==Raspy:                                                  # option in whand_parameters.py
    try:
        import RPi.GPIO as GPIO                                            # Library for Raspy
    except:
        print("*** I/O Error: no driver for Raspberry pi ***")
        raise ReferenceError

# Global variables
global Boxes
global Boxinputs
Pins=[]
Outputs=[]
Err_io_number="\n*** Error in input or output number ***"

# Initialization ============================================
def init_hardware(Pins, Outputs):                                                     # required by Whand         
    """
    Initializes Raspy
    Tests whether the hardware is on (else exits)
    Pins and Outputs are lists of numbers of used inputs and outputs
    whand_io calls this function but does not expect any return
    A pin must be declared either as an input or an output
    An error is raised if input and output numbers collide
    pin naming follows BCM (pin(1) does not exist)
    """
    if Hardware==Raspy:                                                  # option in whand_parameters.py    
        print("Initializing Raspy for I/O")
        # check for collisions
        err=[pin for pin in Pins if pin in Outputs]
        if err:
            print(Err_io_number)
            print("pin/output", err)
            raise ReferenceError
        err=[]
        for pin in Pins:
            if pin<2 or pin>Boxinputs: err+=["pin("+str(pin)+")"]
        for pin in Outputs:
            if pin<2 or pin>Boxinputs: err+=["output("+str(pin)+")"]
        if err:
            print(Err_io_number)
            print(err)
            raise ReferenceError

        # initialize I/O
        GPIO.setmode(GPIO.BCM)                                       
        GPIO.setwarnings(False)
        for pin in Pins:
            print("Initializing pin", pin,"as input")
            GPIO.setup(pin, GPIO.IN)                                       
        for pin in Outputs:
            print("Initializing pin", pin,"as output")
            GPIO.setup(pin, GPIO.OUT)                                       
    else:
        print("*** I/O Error: wrong driver for Raspberry pi ***")
        raise ReferenceError

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
    pass
    
#================================================================
def read_one_pin(box, nb):                                             # required by Whand    
    """ 
    This function is called by whand_io.py
    Directly read one input without interrupts
    box is 0 to Boxes-1
    nb is input pin (1 to ...)
    returns state as 0 or 1
    """
    if Hardware==Raspy:
##        print("reading pin", nb)
        state=GPIO.input(nb)
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
    if Hardware==Raspy:
##        print("setting pin", nb, "to", bit)
        GPIO.output(nb, GPIO.HIGH if bit else GPIO.LOW)

#================================================================
def read_one_AD(box, ADnumber):                                            # required by Whand
    """
    Input driver for numbers in Whand. Scans one input at a time
    The current Raspy hardware does not support analog input
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
    if Hardware==Raspy:
        GPIO.cleanup()
    
#==============================================================
def close_hardware():                                                          # required by Whand
    """
    This function is required to clean up on exit 
    disable interrupt detection for  pin inputs and clear outputs 
    whand.io calls this function but does not expect any return
    """
    if Hardware==Raspy:
        pass
    
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



