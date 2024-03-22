# -*- coding: ISO-8859-1 -*-
"""
Whand language: Alain Marchand 2019.
This is the options and parameters module. 
"""
# system =====================================================
Pywin=False                                     # True when running under Windows
Nosave= True                                  # set to False to record/read event data
Printout= False    # True                    # display message when i/o change (debugging tool)

# timing constants ===============================================
Speed_factor=10                                  # to accelerate (or slow down) clock under controlpanel
Timestep=.05                                    # display refresh period (seconds)

# I/O options ====================================================
ASi="ASi"
Raspy="Raspy"
Hardware= None #Raspy #ASi                                                      # ASi for Imetronic or None
Boxes=8                                                                             # number of parallel setups  
Boxinputs=12                                                                     # for input with multiple parallel scripts
Max_show_pins=80                                                            # do not show pins with large number
Online_save= False    # True                                              # record data online or when finished
Autoname=False                                                                # automatic naming of result files
Use_interrupts=False                                                          # allow interruptions on pin inputs
Split_second=10                                                                 # time unit for results (1/s)

# global constants ===============================================
Scriptdir="scripts"                              # Subdirectory for scripts and run files
Datadir="data"                                   # Subdirectory for results
Max_occur_list=300                              # memory span for event occurrence
Max_iter=100
Max_depth=20
Change_time= 0.000001                      # used to create transients (change) 
Glitch_time= 3*Change_time               # used to create transients (begin, end)   
Epsilon_time= 8*Change_time            # used to prevent event synchrony
FloatPrecision=0.00000005                 # absolute limit for equality
BigNumber=1048576                         # used to extend code range in conditions 

# debug options ====================================================
Allow_manual=True                           # interactive buttons
Simulatepin=False                              # simulation of inputs
Simulatepinlist=[10]                         # simulated inputs
Simulatepinfreq=4                            # simulated input frequency  
Debug=False

# compilation
Warnings=True                                   # display warnings at compile time
Dumps=False                                      # in case of error or abort
Race_test=False                                  # looks for collisions at compile 
Fatal_race=False                                  # abort if a collision is found
Fatal_use_before=False                       # abort at runtime if a value is used before being updated
Random_update_order=False             # update order varies randomly at each compilation

# Additional calls =================================================
Volatile_calls=[]
Volatile_calls+=["controlled_proba"]

# Display options =================================================
Width_margin=16                             # do not fill all screen 
Height_margin=76                            # leave a band at bottom 
Left_margin=100                               # space for global buttons 
Displayed_boxes=8                           # to divide remaining space
Window_position="+0+0"                # from top left

DarkColor="black"
LightColor="white"
ValueColor="#62c4dd"                    # CNRS 
FalseColor="#456487"                     # CNRS bleu anthracite clair
TrueColor="yellow2"
PinFalseColor="#9c126d"                # CNRS INSB (maybe "purple4")
PinFastColor="red"
PinSlowColor="green4"
PinTrueColor="yellow2"
BackColor="#00294b"                     # CNRS bleu anthracite
DarkColorList=[DarkColor, PinFalseColor]

# Debugging options ===============================================
Debog=""
##Debog+='prc'                  # check precompile
##Debog+='crd'                  # creating nodes
##Debog+='sti'                   # creating nodes
##Debog+='stx'                  # storing expressions
##Debog+='xps'                  # creating expressions
##Debog+='loc sbs sgn'      # compute local generic
##Debog+='sgn'                  # compute local generic
##Debog+='rel'                   # verify effects
##Debog+='fnt cmb dtr'      # analyze nature
##Debog+='nto'                  # list natures
##Debog+='stv lnk'             # start values link nodes
##Debog+='trb'                  # build tree
##Debog+='trm'                   # tree maker
##Debog+='lst'                   # list tree
##Debog+='lsf'                   # list final tree
##Debog+='obj'                   # list objects
##Debog+='evl upv'           # check updating
##Debog+='evl'                  # check updating

###===================================================== main
if __name__== "__main__":
    print("whand_parameters.py: syntax is correct")

