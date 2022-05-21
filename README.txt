WHAND aims at being the simplest possible language for programming small automatons. It was originally developed by Alain Marchand to control experiments in conditioning chambers with parallel stimuli (outputs) and  manipulanda (inputs), with a focus on readability.
A Whand script is NOT a sequence of instructions! It is a set of object definitions that fully describe each object's behavior (typically on/off events). Objects can be defined in any order. They should be given explicit names.
Here is a short but complete Whand script that reads the state of a lever. Each time the subject (rat/mouse) presses the lever, it will trigger the delivery of a reward:

exit: when start + 15min                    # definition of "exit": stop experiment after 15 minutes
reward: when lever_pressed                  # definition of "reward", a 500 ms on/off pulse
   until reward + 500ms                     # definition of "reward" (continued)
output(1): reward                           # definition of "output(1)": link "reward" to hardware output port 1
lever_pressed: pin(2)                       # definition of "lever_pressed": link to hardware input port 2

Some of the characteristics of Whand are described in The_book_of_Whand.pdf. More in directory: doc
A full (if somewhat technical) description of the language is given in WHAND REFERENCE MANUAL.docx
To set up and test a working version, see WHAND USER MANUAL.docx
Whand is written in Python and is open source. The Python module named whand_driver.py contains all functions that need to be adapted to each type of hardware. Currently available for Imetronic(R) and Raspberry Pi hardware.
Version 2.7 now features a driver to control a Raspberry pi under Linux (Raspbian), see whand_on_Raspberry_pi.pdf.
Whand is currently being refactored and a DEVELOPPER MANUAL is under way.
