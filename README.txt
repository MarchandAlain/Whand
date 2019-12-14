WHAND aims at being the simplest possible language for programming small automatons. It was originally developed by Alain Marchand to control experiments in Skinner boxes with parallel stimuli, manipulanda and rewards. Whand focuses on the readability of programs. Variables have explicit names and their behavior is entirely described in the variable definition. Here is a short but complete Whand script:

exit: when start + 15min                   # stop experiment after 15 minutes
reward: when lever_pressed              # definition of "reward", a 500 ms pulse
   until reward + 500ms                     # definition (continued)
output(1): reward                             # link "reward" to hardware output port 1
lever_pressed: pin(2)                        # define "lever_pressed", link to hardware input port 2

To set up and test a working version, see WHAND USER MANUAL.docx
A complete (if somewhat technical) description of the language is given in WHAND REFERENCE MANUAL.docx
Whand is written in Python and is open source. A Python module named whand_drive.py contains all functions that need to be adapted to each type of hardware.
