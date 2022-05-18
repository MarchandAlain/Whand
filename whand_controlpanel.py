import whand_runtime as rt
import whand_io as io                               
from whand_parameters import * # options, constants
from whand_operators import *   # module only contains constants
from whand_tools import *          # useful procedures only
try:
    try:                                              # name changed in Python 3
        from tkinter import *            # from... import is recommended by doc
    except:
        from Tkinter import *           # Python 2 compatibility
except:
    raise ImportError('Tk wrapper not available')

Screen_width = 1300                 # for labels only. Actual screen size is determined later in makebox
PFColor=PinFalseColor if Speed_factor==1 else PinFastColor if Speed_factor>1 else PinSlowColor
LabelGS=Label_global_start if Speed_factor==1 else Label_global_fast+str(Speed_factor) if Speed_factor>1 else Label_global_slow

#===================================================== Framing  
class Framing(Frame):
    """ Container """
    def __init__(self, fenetre, **kwargs):
        Frame.__init__(self, fenetre, width=1, height=1, **kwargs)                      # prepare window
        self.pack(fill=BOTH)
        self.pack(side="left")
                
#===================================================== Supervisor  
class Supervisor(Frame):
    """ Container for global controls """
    def __init__(self, cadre, fenetre, svlist, **kwargs):
        Frame.__init__(self, width=1, height=1, bg=BackColor, **kwargs)                      # prepare window
        self.pack(fill=BOTH)
        self.pack(side="left")  

        self.new_session=False
        self.bouton_start = Button(self, text=LabelGS, bg=PFColor, fg=LightColor, command=lambda: self.global_start(svlist))
        self.bouton_start.pack()                                                              # general start button   
        
        self.bouton_quitter = Button(self, text=Label_global_stop, bg=PFColor, fg=LightColor, command=lambda: self.global_stop(fenetre, svlist))
        self.bouton_quitter.pack()                                                         # general stop button   
  
        self.bouton_session = Button(self, text=Label_restart, bg=PFColor, fg=LightColor, command=lambda: self.restart(fenetre, svlist))
        self.bouton_session.pack()                                                         # general stop button   
  
        label=Label_run+io.Runfilename[:-4]
        label=(label+"                   ")[:20]
        self.bouton_runfile = Button(self, text=label, bg=FalseColor, fg=DarkColor,
                            command=self.ignore)
        self.bouton_runfile.pack()                                                       # info run file name   
        
        label="-> "+io.Filename
        label="                "+label                                                        # right
        label=label[len(label)-16:]
        self.bouton_file = Button(self, text=label, bg=FalseColor, fg=DarkColor,
                            command=self.ignore)
        self.bouton_file.pack()                                                               # info save file name   
        
    def global_start(self, svlist):
        """ start all programs in parallel """
        print ("\n***" + Label_global_start + "***")
        for sv in svlist:
            sv.interface.go(self, sv, svlist)
        self.bouton_start["bg"] = FalseColor
       
    def multi_start(self, box, svlist):
        """
        start multiple programs in parallel
        this method is called from an Interface instance
        to start slave boxes in other instances
        """
        startlist=[x for x in svlist if x.Boxnumber+1 in svlist[box-1].masterto]
        for sv in startlist:
            sv.interface.go(self, sv, svlist)
            
    def multi_stop(self, box, svlist):
        """
        stop multiple programs in parallel
        this method is called from an Interface instance
        to stop slave boxes in other instances
        """
        startlist=[x for x in svlist if x.Boxnumber+1 in svlist[box-1].masterto]
        for sv in startlist:
            sv.interface.bouton_start["text"] =Label_closed
            sv.interface.bouton_start["bg"] = FalseColor                # appearance of start button
            sv.interface.bouton_quitter["bg"] = FalseColor
            sv.interface.pause=True
            if not sv.interface.closed: sv.interface.finish(self, sv, svlist)
            
    def global_stop(self, fenetre, svlist):
        """ stop all running programs"""
        print ("\n***" + Label_global_stop + "***")
        self.bouton_start["bg"] = FalseColor                # appearance of global start button
        for sv in svlist:
            sv.interface.bouton_start["text"] =Label_closed
            sv.interface.bouton_start["bg"] = FalseColor
            sv.interface.bouton_quitter["bg"] = FalseColor
            sv.interface.pause=True
            if not sv.interface.closed: sv.interface.finish(self, sv, svlist)       # not just a pause
        fenetre.protocol("WM_DELETE_WINDOW", fenetre.destroy)         # allow direct window closure
        io.finish()
        self.bouton_quitter["bg"] = FalseColor
        self.new_session=False
                 
    def restart(self, fenetre, svlist):
        """ stop all running programs close window and start a new session """
        self.global_stop(fenetre, svlist)
        self.new_session=True
        fenetre.destroy()
                 
    def ignore(self):                                                             
        pass
        
#===================================================== Interface  
class Interface(Frame):
    """ interactive interface """
    def __init__(self, sv, cadre, supervisor, svlist, autotest, **kwargs):
        mywidth=int((Screen_width-Left_margin)/Displayed_boxes)
        Frame.__init__(self, width=mywidth, height=1, bg=BackColor, **kwargs)   # prepare window
        self.pack(fill=BOTH)
        self.pack(side="left")
        self.pack_propagate(False)
        
        self.bouton_cliquer={}                                                                                  #  prepare dictionary for all objects
        self.output_list=[]                                                                                         #  prepare list for displayed outputs
        self.unused_pins=[]                                                                                       #  prepare list for unused pins
        self.closed=True
        
        # make start stop and time widgets
        self.message = Label(self, text=("Box"+str(1+sv.Boxnumber))+" "+Label_start)               # start message   
        self.message.pack()
        
        # use multi_start to start both master and slave boxes
        self.bouton_start = Button(self, text="      Start     ", bg=PFColor, fg=LightColor, command=lambda: supervisor.multi_start(1+sv.Boxnumber, svlist)) 
        self.bouton_start.pack(side="top")                                                              # start button   
        
        self.bouton_quitter = Button(self, text=Label_pause_quit, bg=PFColor, fg=LightColor, command=lambda: self.finish(supervisor, sv, svlist))
        self.bouton_quitter.pack(side="top")                                                         # pause/quit button   

        self.bouton_name = Button(self, text=io.Scriptname[sv.Boxnumber], bg=FalseColor, fg=LightColor, command=lambda: self.ignore())
        self.bouton_name.pack(side="top")                                                         # pause/quit button   

        self.pause=False
        self.autotest=autotest

    def labelling(self, sv, element):                                                                        # Appearance: colors and texts (dynamic)
            nam=no_quotes(element)                                                                        # remove external quotes from names
            if not element in sv.Object:                                                                     # check existence 
                print(Err_key, Crlf, "-->", element)
                raise ReferenceError                       
            nod=sv.Object[element]
            nat=nod.nature
            vlu=no_quotes(nod.value)                                                                       # remove external quotes from values
            vlu=self.formatting(sv, nat, vlu)                                                             # format numbers, durations and lists
            bgcolor=ValueColor                                                                               
            fgcolor=DarkColor                                                                               # default colors for standard nodes
            if nat==Bln:                                                                                          # especially for Booleans
                vlu=""
                bgcolor=FalseColor                                                                           # color for false
                if element in sv.Namedpinlist.values() or element in sv.Pinlist or applied(element, Output):  
                    if Allow_manual: bgcolor=PFColor                                       # color for false Pins 
                if istrue(nod, sv.Current_time):
                    bgcolor=TrueColor                                                                        # color for true Booleans 
                    if element in sv.Namedpinlist.values() or element in sv.Pinlist or applied(element, Output): 
                        if Allow_manual: bgcolor=PinTrueColor                                   # color for true Pins 
            if nat in [Bln, Stt]:
                if vlu==nam: vlu=""                                                                          # empty value if same as name
                # check for forced color
                if no_quotes(nod.value) in Tkinter_colors:                                           # use color names from name
                    bgcolor=no_quotes(nod.value)
                    vlu=""
                if no_quotes(nod.name) in Tkinter_colors:                                          #  use color names from value 
                    bgcolor=no_quotes(nod.name)
                    if nat==Bln and istrue(nod, sv.Current_time): bgcolor=ValueColor  #  revert to standard value color if true
                    if vlu in sv.Pinlist: vlu=""                                                               # empty value for Pins
                if type(vlu)==list and vlu \
                   and type(vlu[0])==tuple: vlu=logic(vlu[0], sv.Current_time)                         # status 
            if bgcolor in DarkColorList:                                                                    # for all types of nodes
                fgcolor=LightColor                                                                            # write white on dark colors
            label=nam
            if not vlu in[None, ""]: label+=" : "+str(vlu)                                     # create label as 'name : value'
            cnt=Count+Obr+element+Cbr   
            if cnt in sv.Object:                                                                                # add count if any
                if sv.Object[element].nature==Bln:
                    label+=" # "+str(sv.Object[element].count)                                # occurrences
                else:
                    label+=" # "+str(len(sv.Object[element].value))                          #size
            return label, bgcolor, fgcolor

    def formatting(self, sv, nat, vlu):                                                           # format numbers, durations and lists
        if nat in [Bln, Stt]: return vlu
        if nat==Lst and type(vlu)==list:                                                        # process list elements
            cop=vlu
            vlu=Obr
            l=len(cop)
            if  l>4: l=4
            for elt in cop[:l]:
                nt=get_nature(sv, elt)
                elt=self.formatting(sv, nt, elt)
                vlu+=str(elt)+","
            if len(cop)<=4 and l>0: vlu=vlu[:-1]         # remove final comma
            if len(cop)>4: vlu=vlu+"..."       # shorten list values
            vlu=vlu+Cbr
        if nat==Drtn and type(vlu)==str:                                                       # format durations
            vlu=float(vlu[:-1])
        if type(vlu)==int: vlu=str(vlu)                                                             # format integers
        if type(vlu)==float:
            vlu=int(.5+1000*vlu)/1000                                                              # round values
            vlu=('%9.3f' % vlu).rstrip("0").rstrip(".").lstrip(" ")                       # format float values
        if nat == Drtn and vlu is not None: vlu+="s"
        return vlu   
    
    def create(self, sv, supervisor, svlist, args):                                          # interface.create: define button actions
        # invert Namedpinlist
        self.Pinname={sv.Namedpinlist[x] : x for x in sv.Namedpinlist}

        # detect unused pins
        for element in sv.Namedpinlist:
            nam=sv.Namedpinlist[element]
            if not nam in args:
                self.unused_pins.append(nam)

        for element in args:
            label, bgcolor, fgcolor=self.labelling(sv, element)                                     # get appearance: colors and texts
            if element in sv.Namedpinlist.values():                                                       # named pin: use name
                nam=self.Pinname[element]
                label, bgcolor, fgcolor=self.labelling(sv, element)
                bgcolor=FalseColor                                                                        #  neutral color of Pins until start
                self.bouton_cliquer[element] = Button(self, text=label, bg=bgcolor, fg=fgcolor,
                        command=lambda i=nam : self.changepin(sv, i))                   # use lambda to pass function changepin
                self.bouton_cliquer[element].pack(fill=X)                                              # display button
            elif element in sv.Pinlist:                                                                        # unnamed pin
                label, bgcolor, fgcolor=self.labelling(sv, element)
                bgcolor=FalseColor                                                                        #  neutral color of Pins until start
                self.bouton_cliquer[element] = Button(self, text=label, bg=bgcolor, fg=fgcolor,
                        command=lambda i=element : self.changepin(sv, i))                   # use lambda to pass function changepin
                self.bouton_cliquer[element].pack(fill=X)                                              # display button
                
            elif applied(element, Output):                                                             # allow buttons to act on outputs 
                nam=element                                                                                 
                self.output_list+=[nam]
                label, bgcolor, fgcolor=self.labelling(sv, nam)
                bgcolor=FalseColor                                                                        #  neutral color until start
                self.bouton_cliquer[nam] = Button(self, text=label, bg=bgcolor, fg=fgcolor,
                        command=lambda i=element : self.changeout(i))                   # use lambda to pass function changeout
                self.bouton_cliquer[nam].pack(fill=X)                                              # display button
            
            else:                                                                                                   # inactive object on display
                if not element in sv.Namedpinlist.values():                                   # ignore named pins (displayed elsewhere)
                    self.bouton_cliquer[element] = Button(self, text=label, bg=bgcolor, fg=fgcolor,
                            command=self.ignore)                                                       # button has no effect
                    self.bouton_cliquer[element].pack(fill=X)

        if Exit in sv.Object and istrue(sv.Object[Exit], sv.Current_time):              # stop after updating once if finished 
            self.pause=False
            self.suite(sv, supervisor, svlist)

    def update(self, sv, element):                                                                      # apply one button appearance
        if element in sv.Visible:
            label, bgcolor, fgcolor=self.labelling(sv, element)
            self.bouton_cliquer[element]["text"] = label
            self.bouton_cliquer[element]["bg"] = bgcolor
            self.bouton_cliquer[element]["fg"] = fgcolor

    def go(self, supervisor, sv, svlist):                           # (re)start program
        self.bouton_start["bg"] = FalseColor                   # appearance of start button
        if sv.Current_time==0:                                        #  initialize at start
            io.run(sv)                                                   
            rt.init_outputs(sv)
            self.closed=False
            init_update(sv, self.autotest)
        if not (Exit in sv.Object and istrue(sv.Object[Exit], sv.Current_time)): # do not resume after exit
            if self.pause:                                                   # resume after pause
                self.pause=False
                sv.t0=io.clock()*Speed_factor-sv.Current_time+Epsilon_time  # adjust clock with delay  
                print(Warn_resume)            
            for element in sv.Visible:                                # update display before starting
                self.update(sv, element)
            self.suite(sv, supervisor, svlist)
            
    def wait(self, sv, supervisor, svlist):                                          # synchronize and retrigger suite
            clock=io.clock()
            delay=int(1000*((sv.Current_time+sv.t0+Timestep/2)-clock*Speed_factor))    # milliseconds
            if delay<0: delay=0
            if delay==0 and abs(2*clock-int(2*clock))<0.01: delay=1
            if not self.pause:              
                self.callback=self.after(delay, lambda: self.suite(sv, supervisor, svlist))   
       
    def suite(self, sv, supervisor, svlist):                                 # continue program
        rt.update_loop(sv)                                     # execute loop in runtime module
        self.message["text"]=("Box"+str(1+sv.Boxnumber))+" time: "+('%0.1f' % sv.Current_time)+"s  lag: "+('%0.1f' % max(0,(io.clock()*Speed_factor-sv.Current_time-sv.t0)))+"s" # display time bar
        if not (Exit in sv.Object and istrue(sv.Object[Exit], sv.Current_time)):
            self.wait(sv, supervisor, svlist)                                  # continue if not exit
        else:
            supervisor.multi_stop(1+sv.Boxnumber, svlist)       # exit sequence using multistop
            
    def finish(self, supervisor, sv, svlist):                                         # exit or pause program
        if Exit in sv.Object and istrue(sv.Object[Exit], sv.Current_time) or self.pause: # finished or already in pause
            if not self.closed:
                self.exitbox(sv, supervisor, svlist)                                     # exit sequence
                if getattr(self, 'callback', 0)!=0: self.after_cancel(self.callback)   # prevent 'after' callback
        else:                                                                            # resume after a pause     
            self.bouton_start["bg"] = PFColor                  
            self.bouton_start["text"] =Label_resume
            self.pause=True
            print(Warn_pause)

    def exitbox(self, sv, supervisor, svlist):                                       # exit sequence
        if Exit in sv.Object and not istrue(sv.Object[Exit], sv.Current_time) and not self.closed:
            sv.Object[Exit].value=[(sv.Current_time, None)]
            self.suite(sv, supervisor, svlist)                       # forced stop: run one last update loop
            self.closed=True                                            # do not update again
        for element in sv.Visible:                                   # update display before leaving
            self.update(sv, element)
        self.bouton_start["text"] =Label_closed
        self.bouton_start["bg"] = FalseColor                # appearance of start button
        self.bouton_quitter["bg"] = FalseColor
        io.closebox(sv)

    def ignore(self):                                                             
        pass
        
    def changepin(self, sv, nam):
        if not Allow_manual: return
        if not nam in sv.Pinstate:
            print("\n", Anom, "   ", Within, nam)          # *** Anomaly in", nam,"***                     
        else:
            if nam in sv.Namedpinlist:
                self.update(sv, sv.Namedpinlist[nam])
            else:
                self.update(sv, nam)
            # transmit info to io module                      
            nb=nam[len(Pin)+1:-1]
            if not isnumber(nb): nb="0"
            pinnumber=int(nb)
            value=(sv.Pinstate[nam]!=Vrai)    # n.b. will react slowly 
            io.panelpin(sv, pinnumber, value, io.clock()*Speed_factor)

    def changeout(self, sv, nam):                                                             
        if not nam in sv.Object:
            print("\n", Anom, "   ", Within, nam)          # *** Anomaly in", nam,"***                     
        else:
                                                                         # fit into Whand
            nod=sv.Object[nam]
            if not istrue(nod, sv.Current_time):
                nod.value=[(sv.Current_time, None)]
            else:
                nod.value=[(nod.value[0][0], sv.Current_time)]
            nod.lasttime=sv.Current_time
            nod.lastchange=sv.Current_time
            nod.haschanged=True
                                                                        # transmit info to io module    
            nb=nam[len(Output)+1:-1]
            if not isnumber(nb): nb="0"
            pinnumber=int(nb)
            io.setpin(pinnumber, st, io.clock()*Speed_factor-sv.t0)
                                                                         # update display
            self.update(sv, nam)                                                  

#===================================================== protect  
def protect():                                                 # do not allow closing the window with X
    print (Warn_noclose)  # "\n*** Direct window closure is disabled. Use 'Global stop' button ***\n")
    pass
    
#===================================================== makebox  
def makebox(svlist, autotest):                                                # configure and display interface
    fenetre = Tk()
    Screen_width = fenetre.winfo_screenwidth()
    Screen_height = fenetre.winfo_screenheight()
    fenetre.protocol('WM_DELETE_WINDOW', protect)          #  do not allow direct window closure
    cadre = Framing(fenetre)                                                  #        fenetre = Tk()
    geom=str(Screen_width-Width_margin)+"x"+str(Screen_height-Height_margin)+Window_position
    fenetre.geometry(geom)                                                   # e.g. ("1910x990")
    fenetre.resizable(0, 0)
    fenetre.configure(background=BackColor)
    supervisor=Supervisor(cadre, fenetre, svlist)
    for sv in svlist:
        # invert Namedpinlist
        Pinname={sv.Namedpinlist[x] : x for x in sv.Namedpinlist}
        sv.Visible=[]
        unusedlist=[]
        if Unused in sv.Object: unusedlist=[applied (x, Unused) for x in sv.Object[Unused].value]
            
        # use show order if given    
        orderlist=[]
        if Show in sv.Object:
            for nam in sv.Object_list:
                if not isdictkey(sv, nam, Unused):
                    showed=applied(nam, Show)                            # show object in given order   
                    counted=applied(showed, Count)                     # show object if counted   
                    if counted and not counted in orderlist:        
                        orderlist+=[counted]
                    if showed and not counted and not showed in orderlist:                   
                        orderlist+=[showed]
                if isdictkey(sv, All, Show): orderlist+=[nam for nam in sv.Object_list if not nam in orderlist]
        if Allow_manual:
            plist=[]
            for nam in sv.Pinlist:
                num=applied(nam, Pin)
                if num and int(num)>Max_show_pins:
                    continue                                                          # do not show
                if not isdictkey(sv, nam, Unused):
                    if not nam in orderlist:
                        if not nam in sv.Namedpinlist:
                            plist+=[nam]
                        elif not sv.Namedpinlist[nam] in orderlist:
                            plist+=[sv.Namedpinlist[nam]]
            plist.sort()
            orderlist.extend(plist)
            
        # determine visibility
        for nam in orderlist:                                                     # transfer orderlist to sv.Visible
            ok=True
            for f in Internal_Functions:                                       # cannot display functions
                if applied(nam, f) and not f==Pin: ok=False            
            if ok: sv.Visible+=[nam]
        sv.interface = Interface(sv, cadre, supervisor, svlist, autotest)       # create display
        sv.interface.create(sv, supervisor, svlist, sv.Visible)
    fenetre.mainloop()
    fenetre.quit()
    return supervisor.new_session
   
#===================================================== isdictkey
def isdictkey(sv, mykey, dictname):
    """
    verifies if mykey is a key to Whand dictionary, returns True/False         
    """
    if not dictname in sv.Object: return False
    li=sv.Object[dictname].value
    if li is None: return False
    if type(li)!=list:
        print("\n", Anom_illegal_dict_val)                          # *** Anomaly: illegal dict value ***                        
        print(dictname, "=", li)
        raise ReferenceError
    ky=dictname+Obr+mykey+Cbr    
    for elt in li:                                    
        if elt==ky: return True              
    return False

#===================================================== init_update  
def init_update(sv, autotest):
    """
    run real time
    """
    sv.t0=io.clock()*Speed_factor+Epsilon_time                # synchro (inputs as delayed events)     
    sv.delayed_list=[]                                                      
    if not istrue(sv.Object[Exit], sv.Current_time):
        rt.pinscan(sv)                                     # scan inputs and make them delayed events                                                               
        sv.delayed_list = rt.nextevents(sv)     # prepare list of delayed events
        rt.update_loop(sv)                                                               

    


