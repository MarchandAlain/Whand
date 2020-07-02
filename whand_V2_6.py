# -*- coding: ISO-8859-1 -*-
from __future__ import print_function                                       # Python 2/3 compatibility

# standard modules
import sys
import os                                                                                  # system module, used to exit gracefully
from types import *                                                                  # names for standard types. doc says import * is safe
here=os.path.dirname(os.path.abspath(__file__))                      # valid for Python3
sys.path.append(os.path.join(here, "whand_modules"))          # else specify full path
import six                                                                                  # Python 2/3 compatibility
from string import *                                                                  # Python 2/3 compatibility
from random import random, shuffle                                       # a few functions

# whand modules
from whand_parameters import *                                             # options, constants
import whand_io as io                                                               # I/O module for files   
import whand_driver as dr                                                        # I/O module for hardware   
from whand_operators import *                                               # names, constants, messages
import whand_nodes as nd                                                       # object structure and methods 
from whand_tools import *                                                       # useful procedures 
import whand_sharedvars as sp                                                # to create multiple instances
import whand_precompile as pc                                               # to prepare script text file
import whand_compile as cm                                                   # to build program tree
import whand_controlpanel as cp                                             # to display objects in real time
import whand_runtime as rt                                                      # to control execution
from whand_critic import criticize                                             # verify script reliability

Pywin=True
if Pywin:
    import win32console, win32gui, win32con                              # window lock control (needs pywin)

#===================================================== startvalues
def startvalues(sv):
    """
    Compute all initial values
    Relies on whand_runtime
    Loop until values stabilize
    Finally convert clauses to numbers
    sv.Current_time is 0
    """
    verbose=('stv' in Debog)                                                    # controls debugging messages
    partial=not sv.Graphic or 'stp' in Debog                            # display initial values
    if verbose: print()

    sv.Current_time=0                                                                  # monitors time in experiment
    sv.Buff.clear()                                                                          # buffer to store text in file                                                    
    start_list=[]                                                                             # objects needing updating                                                    
    condlist=[]                                                                              # before converting clauses
    rt.prepare_idem(sv)                                                                # initialize copies of objects

    # Simple objects 
    for nom in sv.Object:                                                             
        nod=sv.Object[nom]
        nod.once=False                                                                   # limits changes of stochastic objects during initialization
        if nom==Vrai: nod.value=[(0, None)]                                 #   true 
        elif nom==Faux: nod.value=[(None, 0)]                             #   false 
        elif isnumber(nom): nod.value=float(nom)                         # explicit number  
        elif isduration(nom): nod.value=str(seconds(nom))+Unit_sec # explicit duration
        elif applied(nom, Change): nod.value=[(None, 0)]              # no change at start
        else:
            if nod.nature==Lst: nod.value = []                                  # initialize list 
            elif nod.nature==Stt: nod.value=nod.name                    # initialize state to its name
            elif nod.nature==Bln: nod.value=[(None, None)]           # initialize Boolean to undefined
            if nom!=Exit and nod.clauses:                                         # exit is evaluated later
                start_list+=[nom]                                                        # list of objects to be computed
                  
    verify_nature(sv, start_list)                                                      # stop and ask nature if necessary
    if verbose:                                                                              # display start list
        indprint ("start list:")
        for nom in start_list:
            indprint (sv.Object[nom].content())
        indprint ("\ninitializing values:")
    
    nod=sv.Object[Start]                                                             # start of experiment
    nod.value=[(0, Glitch_time)]
    nod.isdelayed=True
    nod.occur=[0]
    nod.count=1
    nod.lastchange=0

    # Full evaluation 
    count_changes=1                                                                 # loop until stabilizes
    count_iter=0                                                                         # avoid too many cycles
    while count_changes and count_iter<Max_iter:                   # BEGIN INTITIALIZATION LOOP
        modified=[]                                                                     # to help debug circular dependencies 
        count_iter+=1                                                                  # count iterations  
        count_changes=0                                                             # loop until no change

        for nom in start_list:                                                         # process all except simple objects
            nod=sv.Object[nom]
            res=cm.insert_node(sv, Special+nom)                         # use existing temporary node if possible 
            nd.copynode(nod,res)                                                  # copy current value
            sv.Indent=""                                                                 # for printout and debugging
            sv.Eval_depth=0                                                           # check recursivity (circular dependencies)
            if verbose: indprint (Crlf+"doing", nom, Col)               # for debugging
             
            if not nod.once:
                for i, (c,v) in enumerate(nod.clauses):                       # c and v are triplets                   
                    sv.Current_clause=nom, c, v                                 # keep trace of clause                   
                    valid, changes=rt.evaluate(sv, c)                           # first EVALUATE CONDITION
                    if verbose: indprint ("  condition", c, valid.value)

                    if istrue(valid, 0):                                                   # then if condition true : EVALUATE VALUE
                            if verbose: indprint ("  MAKING VALUE")
                            res, changes=rt.evaluate(sv, v, objname=nom) # result of evaluation in res

                            if verbose:                                                      # for debugging purposes
                                prev=cm.insert_node(sv, Special+'prev')   # use a single node as buffer   
                                nd.copynode(nod,prev)                             # and store previous value
                                indprint("res:", res.content())                      # display new value
                                
                                                                                                   # now APPLY CHANGES from res to nod
                                                                                                   
                            if res.isdelayed and not nod.isdelayed:           # newly delayed object
                                nod.isdelayed=True                                    # mark as delayed
                                if nod.value is None:
                                    print(Crlf, Err_syntax, nod.name)
                                    raise ReferenceError
                                vlu=nod.value[:]                                          # keep previous value for comparison
                                rt.fuse_delays(sv, nod, res)                          # incorporate new delays                                                                  
                                if vlu!=nod.value:                                        # look for changes
                                    count_changes+=1 
                                    modified+=[nom]                                   # information in case of circular refs
                                    if verbose:
                                        indprint ("change delayed", nod.name, "from", "delayed" if prev.isdelayed else "not delayed", \
                                                  prev.value, "to", "delayed" if nod.isdelayed else "not delayed", nod.value)

                            if res.value is not None and res.value!= nod.value and not nod.once:                # NEW VALUE
                                if len(nod.nature)==1 and not nod.nature[0] in res.nature:
                                    if Stt[0] in nod.nature+res.nature:
                                        print("\n", Err_ask_nature)                     # "*** Indeterminate nature: Please add a 'be' instruction ...
                                    else:
                                        print("\n", Err_conflict_nat)                      # ***Error: nature conflict ***
                                    print(nom+Col, nod.nature, res.nature)
                                    raise ReferenceError 
                                if verbose: indprint ("change value", nod.name, "from", prev.value, "to", res.value)
                                count_changes+=1                                     # it is a new value
                                if v[0] in Stochastic: nod.once=True           # also detect stochastic operator
                                if v[0]==Call:
                                    for f in Volatile_calls:
                                        if v[1][0].startswith(Quote+f+Obr): nod.once=True     # stochastic call
##                                if v[0]==Call and v[1][0].startswith(Quote+"controlled_proba"+Obr): nod.once=True     # stochastic call
                                fst=applied(nom, Store)                             # prepare for file storage if required
                                if fst: rt.bufstore(sv, fst, res.value)               # store value
                                nod.value=res.value if type(res.value)!=list else res.value[:]   # transfer value from res to nod
                                cop=Idem+Obr+nom+Cbr                        # transfer value from res to copy of nod
                                if cop in sv.Object: sv.Object[cop].value=res.value # idem tracks node at start                       
                                if nod.nature==Bln:
                                    if istrue(nod, 0):                                      # Boolean changed if true at start 
                                        nod.lastchange=0                         
                                        nod.occur=[0]
                                        nod.count=1
                                    else:                                                        # reset if false 
                                        nod.lastchange=None                         
                                        nod.occur=[]

            if verbose: print("causes", nom, ":", nod.causes)
            for x in nod.causes:                                                        # update start_list with newly created nodes   
                if not x in start_list:
                    start_list+=[x]
                    if verbose: print("adding", x, "cause of", nom, "to start_list")
                    count_changes+=1

        if count_changes==0:                                                        # set unitialized Booleans to false by default
            for nod in sv.Object.values():                                                  
                if nod.nature==Bln and nod.value==[(None, None)]:
                    nod.value=[(None, 0)]
                    count_changes=1                                                  # update opposite (not) events 
                
        if count_changes==0 and Exit in sv.Object and not Exit in start_list: # compute Exit after full initialization
            start_list=[Exit]
            count_changes=1

    for nod in sv.Object.values():                                                  # cancel all changes after initialization  
        if nod.nature!=Bln: nod.lastchange=None                         # except for Booleans

    if not Exit in sv.Object:                                                            # if there is no exit
        cm.insert_node(sv, Exit)                                                      # add exit node
        sv.Object[Exit].nature=Bln                                                  # make it an event          
        sv.Object[Exit].value=[(None, 0)]                                        # set it to false          
        if not sv.Graphic:
            warn("\n"+Warn_no_exit+"\n")           
        
    if count_iter>=Max_iter:                                                         # initialization failed (infinite loop)
        warn("\n"+Warn_iterations+" ---> "+str(modified)+"\n", autotest)

    if verbose or partial:                                                               # LIST OBJECTS HERE
        print("Initial values:")
        for nom in sv.Object_list:
            ok=True
            if not verbose:
                if nom.startswith(Special) or isnumber(nom) or isduration(nom):
                    ok=False
                if nom in Fixed+[Start, Exit, Controlpanel]+ \
                   ["(None, None)", "(None, 0)", "(0, None)", "(0, 2e-06)"]:
                    ok=False
                for x in [Hide, Show, Unused, Load, Store, Output, Command, Write, \
                          Begin, End, Change, Count]:
                    if applied(nom, x): ok=False
                if ok:
                    nod=sv.Object[nom]
                    if not nod.isexpression:                                               # exclude some objects by properties
                        print(sv.Object[nom].content()) 
                
    uninit=[]                                                                                 # check if all objects have been initialized
    for nom in sv.Object_list:                                                        # exclude some objects by name
        if not(nom.startswith(Special) or nom in Fixed+[Start, Exit, Controlpanel, Ewent, Number, Delay, State, List]  \
                    or isnumber(nom) or isduration(nom) \
                    or applied(nom, Hide) or applied(nom, Show) \
                    or applied(nom, Unused) ):      
            nod=sv.Object[nom]
            if not nod.isexpression:                                                   # exclude some objects by properties
                bad=False
                if nod.value is None: bad=True   
                elif type(nod.value)==list and len(nod.value)>0:        # special case: lists
                    bad=True
                    for x in nod.value:                                                   # look for at least one initialized element
                        if x is not None: bad=False       
                if bad: uninit+=[nom]
            
    if (verbose or partial) and sv.Buff: print()                             
    if uninit and Warnings:
        warn("\n"+Warn_no_value_at_start+"    "+str(uninit)[1:-1])
            
#===================================================== verify_nature
def verify_nature(sv, start_list):                                                           
    """
    verify that all needed objects have an unambiguous nature, else stop and ask
    """
    undet=[]
    for nom in start_list:      
        if len(sv.Object[nom].nature)!=1:                                                        # more than one possible nature     
            undet+=[nom]  
    if undet:
            print("\n", Err_ask_nature)           
            print("    ", str(undet)[1:-1])
            raise ReferenceError

#===================================================== removechangeconst
def removechangeconst(sv, tree=Special):                             
    """
    remove change of constants in conditions after initialization 
    works on every object (if tree is Special), then recursively on tree
    eliminates one clause at a time, never the last one
    Fixed=[Vrai, Faux, Epsilon, Empty]
    Glitch_list=[Begin, End, Change]
    """
    if tree is None: return None
    if tree==Special:                                                                # process all program
        chg=True
        while chg:                                                                      # loop until no more change
            chg=False
            for nod in list(sv.Object.values()):                              # browse all objects that have clauses
                if nod.clauses:
                    clau=list(nod.clauses)                                        # make a copy of clauses
                    cnt=0                                                                 # count non empty clauses
                    for i, (c,v) in enumerate(nod.clauses):                # browse clauses
                        k=removechangeconst(sv, c)                        # RECURSE on conditions
                        if k!=c:
                            clau[i]=(k,v) if k else None                        # simplify copy
                        if k: cnt+=1
                    if not cnt: clau[0]=nod.clauses[0]                     # restore at least one clause
                    chg=(nod.clauses!=clau)                                  # continue checking if changed      
                    nod.clauses=[]                                                  # transfer back copy
                    for xy in clau:
                        if xy: nod.clauses+=[xy]                               # ignore None clauses 
            
    else:                                                                                 # process a single condition
        if tree[0] in Glitch_list:                                                 # change, begin or end
            if not tree[1]: return None
            t1=tree[1]
            if not t1[1] and not t1[2]:                                        # a leaf
                nom=t1[0]
                if nom in sv.Object:
                    nod=sv.Object[nom]                                      # access object
                    if len(nod.clauses)==1:                                   # single clause 
                        c,v=nod.clauses[0]                                     # look for assignment at start
                        if c ==(Start, None, None):
                            if v and not v[1] and not v[2]:                # a leaf value
                                vl=v[0]
                                if vl in [Vrai, Faux, Ewent, Number, Delay, List, Text] or isnumber(vl) or isduration(vl):
                                    return None                                   # a constant does not change
                                if vl in sv.Object and not sv.Object[vl].clauses and \
                                   not applied (vl, Pin) and not applied (vl, Key):    
                                    return None                                    # no change without clause
            return tree
                                    
        op=tree[0]                                                                 # a tree other than glitch
        if not tree[1] and not tree[2]:                                     # remove constants 
            if op ==Start: return None
            if isnumber(op): return None
            if isduration(op): return None
        elif op==Plus: return tree                                          # keep delayed expressions
        elif op==Comma: return tree                                    # keep lists
        t1=removechangeconst(sv, tree[1])
        t2=removechangeconst(sv, tree[2])
        if op==Or and not t2: return t1                                # remove functions of None
        if op==Or and not t1: return t2
        if op==And and not (t1 and t2): return None
        if op in Unary and not t1: return None 
        return op, t1, t2

#===================================================== deep_verify
def deep_verify(sv, op, t1, t2, funct):
    """
    checks various problems by exploring full tree with verification function "funct"
    potentially useful
    """
    if not funct(sv, op, t1, t2): return False                        # check current level
    ok=True
    if not t1 and not t2: return ok                                     # ignore leaf
    if op==Obr: return deep_verify(sv, op, t1[1], None, funct)  # skip brackets
    if op==Comma:                                                         # list: check each element
        for x in t1:                                                
            if ok: ok=deep_verify(sv, None, (x, None, None), None, funct)
    else:                                                                            # not a list
        if ok and t1: ok = deep_verify(sv, t1[0], t1[1], t1[2], funct)  # check each term
        if ok and t2: ok = deep_verify(sv, t2[0], t2[1], t2[2], funct)
    return ok                            

#===================================================== verify_stochastic
def verify_stochastic(sv, tree=All):
    """
    make sure stochastic objects are not used in conditions or expressions
    recursively explores all program
    """
    if tree==All:                                                         # explore all program
        ok=True
        for nod in sv.Object.values():
            for c,v in nod.clauses:
                op,A,B=c                                                 # explore conditions 
                if A:
                    for sto in Stochastic: 
                        if applied(A[0], sto):                        # fatal error
                            print("\n", Err_not_allowed_cond)  # *** Syntax error: operator not allowed in a condition ***
                            print("    ", sto, "-->", A[0])
                            raise ReferenceError
                    if applied(A[0], Call):                            # verify volatile calls
                        for y in Volatile_calls:
                            sto=Call+Obr+Quote+y+Obr
                            if A[0].startswith(sto):                   # fatal error               
                                print("\n", Err_not_allowed_cond)  # *** Syntax error: operator not allowed in a condition ***
                                print("    ", sto, "-->", A[0])
                                raise ReferenceError
                op,A,B=v                                                 # explore values
                if op==Comma and A:                            # a list: recursively explore each element
                    for x in A:
                        if x: verify_stochastic(sv, tree=x)
                else:
                    for x in [A, B]:
                        if x:
                            for sto in Stochastic: 
                                if applied(x[0], sto):                   # fatal error               
                                    print("\n", Err_not_allowed_expr) # *** Syntax error: operator not allowed in an expression ***
                                    print("    ", sto, "-->", treejoin(v))
                                    raise ReferenceError
                            if applied(x[0], Call):                            # verify volatile calls
                                for y in Volatile_calls:
                                    sto=Call+Obr+Quote+y+Obr
                                    if x[0].startswith(sto):                   # fatal error               
                                        print("\n", Err_not_allowed_expr) # *** Syntax error: operator not allowed in an expression ***
                                        print("    ", sto, "-->", treejoin(v))
                                        raise ReferenceError
                            verify_stochastic(sv, tree=x)         # recursively explore each term

#===================================================== verify_clauses
def verify_clauses(sv):                   
    """
    checks that objects have valid clauses   
    """
    neverdef=[]
    for nod in sv.Object.values():                                      # detect objects that are never defined                   
        if not nod.clauses:                      
            nom=nod.name
            if not nom in Fixed and not isnumber(nom) and not isduration(nom) \
                and not nom in [Ewent, Number, Delay, List, Text] and not nom in Tkinter_colors \
                and sv.Object[nom].nature!=Stt and not Obr in nom: # standard variables and functions 
                    ok=False                                                                                                 
                    if detectlist(nom): ok=True                         # ignore names that are lists
                    if not ok:
                        neverdef+=[nom]
    return neverdef

#===================================================== makeidemlist 
def makeidemlist(sv, tree=Special):
    """
    make a list of objects for function old/idem with tree search
    explore clauses and recurse on all terms
    """
    if tree==Special:                                                            # explore all tree  
        sv.Idem_list=[]                                                       
        for nod in list(sv.Object.values()):                              # list may change during recursion
            for (c,v) in nod.clauses:
                makeidemlist(sv, c)
                makeidemlist(sv, v)
    elif tree:                                                                        # recursively explore branches
        op,A,B=tree
        if not A and not B: return                                         # ignore leaf
        if op==Comma:                                                       # special case: list
            for x in A:
                makeidemlist(sv, x)                                          # process each element
        elif op!=Idem:                                                          # process deeper branches
            makeidemlist(sv, A)
            makeidemlist(sv, B)
        else:                                                                          # idem detected: add object
            if not A[0] in sv.Idem_list: sv.Idem_list+=[A[0]]    # normally only a leaf
            nam=Idem+Obr+A[0]+Cbr                                 # create object if necessary
            cm.insert_node(sv, nam)

#===================================================== makedelayedlist 
def makedelayedlist(sv):
    """
    create a list of delayed objects. Delayed lists are forbidden (only delayed elements).
    nb: change(x) is not delayed. It has an until clause in the case of lists.
    """
    sv.Delayed_objects[:]=[]                  
    for nam in sv.Object:
        if applied(nam, Pin) or applied(nam, Key) \
                  or applied(nam, Begin) or applied(nam, End) : sv.Object[nam].isdelayed=True
        if sv.Object[nam].nature==Lst: sv.Object[nam].isdelayed=False                           
        if sv.Object[nam].isdelayed and nam[0]!=Special:    # ignore old/idem and special objects
            sv.Delayed_objects+=[nam]
##    print("Delayed objects", sv.Delayed_objects)

#===================================================== makepinlist 
def makepinlist(sv):
    """
    Identify inputs in use and related identities
    Pinlist is a list of pin names (e.g. "pin(3)") or key names (e.g. 'key("a")')
    Use slicing [len(Pin)+1:-1] to get number from name
    Pinstate is a dict from pin name to pin status (on/off times)
    Namedpinlist is a dict from pin name to equivalent name,
    Naming is used to easily identify pin function
    """
    sv.Pinstate.clear()                                     
    li=[]
    for nam in sv.Object_list:                                                   # browse objects                                                                      
        if  applied(nam, Key):                                                    # detect keys              
            sv.Pinlist+=[nam]
        elif applied(nam, Pin) and isnumber(nam[len(Pin)+1:-1]): # detect pins
            sv.Pinlist+=[nam]
            li+=[x for x in sv.Object[nam].effects if not x in li]    # list effects of pins (to look for named pins)
    for nam in sv.Pinlist:                                                                                    
        sv.Pinstate[nam]=Faux                                                 # initialize to false                                          
        sv.Object[nam].clauses=[((Always, None, None),(nam, None, None))] # make sure pin is regularly scanned       
    for nam in li:                                                                     # browse list of effects to find equivalent names                                                                              
        for pi in sv.Pinlist:                                                         # create Namedpinlist                                                                                       
            if pi.startswith(Pin):                                                   # (not for keys) 
                ok=True
                for c,v in sv.Object[nam].clauses:
                    # condition must be start or change(pin)
                    if c!=(Start, None, None) and c!=(Change, (pi, None, None), None): ok=False                    
                    # value must be pin with numerical index
                    if not (v and v[0]==Pin and treejoin(v)==pi): ok=False
                if ok:
                    sv.Namedpinlist[pi]=nam                                # found equivalent name

#===================================================== make_activelist
def make_activelist(sv):                                                                                            
    """
    create a short list of active objects directly susceptible to change and that have consequences
    volatile objects are displayed outputs, named pins and implementations of 'lasted' (see whand_compile)
    """
    sv.Active_list=[]                                                     
    for nam in sv.Object_list:                                                  # freeze evaluation order
        if nam[0]!=Special and sv.Object[nam].effects:            #must have effects
            if (nam in sv.Volatile or sv.Object[nam].isdelayed or applied(nam, Idem) \
                or applied(nam, Pin) or applied(nam, Measure) or applied(nam, Read) ):  
                sv.Active_list+=[nam]
    if Random_update_order: shuffle(sv.Active_list)               # randomize evaluation order

#===================================================== changeglitch
def changeglitch(sv):
    """
    modifies conditions involving glitch cached objects to 'change' instead of 'begin' or 'end'  
    e.g. ('begin', ('end(t)', None, None), None) to ('change', ('end(t)', None, None), None)
    so that they may be correctly involved in a delayed effect (see 'test abchange.txt')
    """
    for nod in sv.Object.values():
        for i, (c,v) in enumerate(nod.clauses):
            if c and c[1] and isaglitch(c[1][0]):                            # only for conditions 
                c=(Change, c[1], c[2])
                nod.clauses[i]=(c,v)

#===================================================== unused
def unused(sv, neverdef):
    """
    checks references to inputs or outputs declared as unused (fatal error)
    object should have no effect except to name a pin or an output
    and no cause except to name an output
    """
    if Unused in sv.Object:                                                    # check presence and integrity of unused list
        unusedlist=[applied (x, Unused) for x in sv.Object[Unused].value]
        if not unusedlist: return
        for nam in unusedlist:                                                # check each unused declaration
            nod=sv.Object[nam]
            if applied(nam, Pin) and len(nod.effects)==1 and nam in sv.Namedpinlist \
               and sv.Namedpinlist[nam]==nod.effects[0]: pass
            elif applied(nam, Output) and len(nod.effects)==1 and len(nod.causes)<=2: pass
            elif applied(nam, Output) and len(nod.effects)==1 and len(nod.causes)<=4 \
                 and Faux in nod.causes and Ewent in nod.causes: pass  # allow 'take event'
            elif nod.causes or nod.effects:                               # object should have no cause and no effect
                print(Err_unused_obj)                       
                print(str(nam))
                sv.Current_clause=None, None, None
                raise ReferenceError
        
###===================================================== init_interrupts  
##def init_interrupts(sv):
##    """
##    initialize interrupts for pins using dr.initpin    
##    """
##    for pi in sv.Pinlist:
##        num=pi[4:-1]
##        if isnumber(num):                                                     # extract pin number      
##            nb=int(num)
##            dr.initpincallback(nb)
##            dr.activInterruption(nb)

#===================================================== make_conditions
def make_conditions(sv):                                                                                            
    """
    replace conditions with a table. Each condition will be an index N to the table  
    makes a different code for different types of conditions and makes pointers from the X object
    codes are 0, N-2^20, -N, +N and N+2^20 (BigNumber=2^20=1.048.576)
    corresponding to always, when change X, when end X, and when begin X, respectively
    for lists and dicts, make a pointer from each element
    if list changes at runtime, need to implement this for the new list instead of the old one
    also replace values with a numerical pointer into a table
    see one_condition in whand_runtime.py
    """
    sv.Condition=[1]                                                             # unique condition for Always
    for nam in sv.Object:
        sv.Condition_number[nam]=[]                                   # initialize pointer dictionary
    for nam in sv.Object_list:
        nod=sv.Object[nam]
        if nam[0]==Special:                                                    # no clause for special objects                                        
            nod.clauses=[]                                
        else:                                                                        
            if len(nod.clauses)==1:                                        
                if nod.clauses[0][0]==(Start, None, None):         # no change after start              
                    nod.clauses=[]
            for i, (c,v) in enumerate(nod.clauses):                      # extract condition
                condnum=len(sv.Condition)                                # attribute a number to condition
                vnum=len(sv.Save_value)                                    # attribute a number to value 
                condnum=rt.one_condition(sv, nam,c,v,condnum)  # reprocess condition
                sv.Save_value[vnum]=c, nam, v                           # save old value for debugging
                nod.clauses[i]=(condnum, vnum)                        # replace with number  
        
#===================================================== absolute_times 
def absolute_times(sv, tree=Special):
    """
    make delayed objects for absolute time 
    search tree to detect functions Timeis, Dayis, Dateis, Weekis
    """
    if tree==Special:                       # explore all
        for nod in list(sv.Object.values()):
            for (c,v) in nod.clauses:
                absolute_times(sv, c)
                absolute_times(sv, v)
    elif tree:                                    # recursively explore branches
        op,A,B=tree
        if A is None:                          # ignore leaf
            return
        if op==Comma:                   # special case: list
            for x in A:
                absolute_times(sv, x)
        elif not op in [Timeis, Dayis, Dateis, Weekis]:       # process deeper branches
            absolute_times(sv, A)
            absolute_times(sv, B)
        else:                                               # create delayed object
        # time.struct_time(tm_year=2014, tm_mon=10, tm_mday=19, tm_hour=7, tm_min=58, tm_sec=27, tm_wday=6, tm_yday=292, tm_isdst=1)
            argu=rt.getvalue(sv, A[0]).value
            if type(argu)!=list: argu=[argu]
            for v1 in argu:                             # distributivity
                if op==Timeis:                          
                    then=seconds(v1)                      # prescribed absolute time
                    if then is None:                    
                        print(Err_Val, v1)
                        raise ReferenceError
                    now=(3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec)
                    dt=then-now                               # compute delay
                    if dt<=0: dt=dt+24*3600             # wait until next day
                    dur=Glitch_time
                    
                if op==Dayis:
                    then=None
                    for i, x in enumerate(Wday):
                        if x==v1: then=i       # prescribed absolute time
                    if then is None:
                        print(Err_Val, v1)
                        raise ReferenceError
                    dy=io.localtime().tm_wday
                    tm=3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec
                    dt=(((then-dy)+7)%7)*24*3600                         # compute delay
                    dur=24*3600
                    if dt==0:
                        dt=Epsilon_time
                        dur=dur-tm
                    else:
                        dt=dt-tm
                     
                if op==Dateis:                  # n.b. also formula for leap years
                    nbday=io.localtime().tm_yday
                    tm=3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec
                    v1=noquotes(v1).replace(Space,"")
                    then, mn, md=countdayswithleap(v1, io.localtime().tm_year)                    
                    dt=then-nbday                         # compute delay
                    if dt<0:
                        then, mn, md=countdayswithleap(Month[11]+"31", io.localtime().tm_year)  
                        dt=then-nbday                                                                    # finish year
                        then, mn, md=countdayswithleap(v1, io.localtime().tm_year+1)   # next year 
                        dt+=then                    
                    dt=dt*24*3600
                    dur=24*3600
                    if dt==0:
                        dt=Epsilon_time
                        dur=dur-tm
                    else:
                        dt=dt-tm
                     
                if op==Weekis:                  # n.b. also formula for leap years
                    tm=3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec
                    thisday=io.localtime().tm_wday
                    nbday=io.localtime().tm_yday
                    nowwk=int((nbday-thisday+14)/7)
                    dw=v1-nowwk                  # compute week difference
                    dur=7*24*3600
                    if dw==0:                           # same week
                        dt=Epsilon_time
                        dur=dur-thisday*24*3600-tm
                    elif dw>0:                          # same year
                        dt=(7*dw-thisday)*24*3600-tm
                    elif dw<0:                           # days till end of year
                        then, mn, md=countdayswithleap(Month[11]+"31", io.localtime().tm_year)  
                        remain=then-nbday                                                   # finish year
                        firstday=(thisday+remain+1)%7
                        if v1==1: firstday=0
                        dt=(remain+1+7*(v1-1)-firstday)*24*3600-tm

                if dt is not None:                                                                  # create delayed time object                                                
                    nam=op+Obr+A[0]+Cbr
                    cm.insert_node(sv, nam)
                    if sv.Object[nam].value is None: sv.Object[nam].value=[]           # v2.103
                    if not (dt, dt+dur) in sv.Object[nam].value: sv.Object[nam].value+=[(dt, dt+dur)]  
                    sv.Object[nam].nature=Bln
                    sv.Object[nam].isdelayed=True

#===================================================== countdayswithleap
def countdayswithleap(dat, yr):
    """
    count number of days for a date, allowing for leap years
    """
    mn=None
    md=None
    leap=1 if (yr%4)==0 else 0   # leap year
    for i, x in enumerate(Month):
        if dat.startswith(x):
            maxd=Mndays[i]
            if i==1: maxd+=leap                 # february
            nb=int(dat[len(x):])
            if nb<=maxd:
                mn, md=i, nb       # prescribed absolute time
    if mn is None or md is None:
        print(Err_Val, v1)
        raise ReferenceError
    then=0
    for i in range(mn):                 # count days
        then+=Mndays[i]
    if mn>1: then+=leap
    then+=md
    return then, mn, md

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
    
##===================================================== buildprog
def buildprog(sv):
            prog=pc.precompile(sv, tout+Crlf)
            if sv.slaveto: prog=make_yoked(prog)
            cm.wcompile(sv, prog)
            neverdef=verify_clauses(sv)     # detect never defined objects                               
            sv.Graphic=(Controlpanel in sv.Object)                
            if "lst" in Debog: print("\n"+cm.reconstruct(sv))
            
            verify_stochastic(sv)                # make sure stochastic objects are not used in expressions
            makepinlist(sv)                        # detect and initialize inputs (to false) 
            startvalues(sv)                         # ==========  find initial values ====================
            absolute_times(sv)                   # create delayed objects for absolute time   
            makeidemlist(sv)                      # create a list of used old/idem (not needed during initialization) 
            makedelayedlist(sv)                 # create a list of delayed objects
            changeglitch(sv)                       # adjust conditions for glitches
            
            if "lsf" in Debog: print ("\n"+cm.reconstruct(sv))
            if 'obj' in Debog:
                print()
                for n in sv.Object_list:
                    x=sv.Object[n]
                    if x.name and x.name[0]!=Special:   
                        print("*", x.content())
                        if x.clauses:
                            for c,v in x.clauses:
                                print("   cond:", c, "val:",v)
                        print()

            make_activelist(sv)                   # list of objects that have effects                     
            unused(sv, neverdef)               # check physical and logical configurations match

            if Random_update_order: shuffle(sv.Object_list)
            if Race_test: criticize(sv)           # check program for collisions
            removechangeconst(sv)          # eliminate clauses for constant objects                          
                        
            make_conditions(sv)                # convert conditions to numbers       

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
    IDLE=sys.stdin.__class__.__module__.startswith('idlelib')       # check if running under IDLE, normally should be "_io"
    ErrorFound=False                                                                 # indicates error or keyboard abort
    autotest=False                                                                      # indicates all tests should be run sequentially without clock
    initialized=False                                                                    # indicates when a closing routine is needed
    new_session=True                                                                # allows to run successive sessions
    windowlock=False                                                                # command is only allowed once
    
    while new_session:
        try:
            print()
            scriptlist, autotest, parallel=io.getscriptlist()
            new_session=False
            filename="config.txt"
            iocodes=io.getiocodes(filename)                                     # codes for event logging 
            svlist=[]
            box=0
            testnum=0
            
            if Pywin and not autotest and not windowlock:
               windowlock=True
               hwnd = win32console.GetConsoleWindow()                # prevent window from closing
               if hwnd:
                   hMenu = win32gui.GetSystemMenu(hwnd, 0)
                   if hMenu:
                       win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)
                       
            if autotest: debut=io.clock()         
            for sourcename in scriptlist:                                          # begin loop on script names
                showname=io.removepath(sourcename)
                master=0                                                                    # not yoked
                if sourcename.startswith(Equal) and isnumber(sourcename[1:]):    # yoked script
                    showname="yoked"+showname
                    master=int(sourcename[1:])
                    if master<1 or master>Boxes or scriptlist[master-1].startswith(Equal):
                        print(Err_yoked, master)
                        raise ReferenceError
                    sourcename=scriptlist[master-1]
                    
                testnum+=1
                sv=sp.spell()
                sv.Boxnumber=box
                if parallel: box+=1                      # different channel numbers on each box
                sv.Graphic=False                        # no controlpanel
                sv.clear_all()                                # reset all variables except Graphic and Debog
                sv.slaveto=master                      # yoked script if master!=0
                sv.Current_clause=None, None, None
                sv.Do_tests=autotest
                if autotest: print("\nTESTING", testnum, sourcename)         
                try:                                                            # try opening script file
                        filename=sourcename
                        tout=io.gettextfile(filename)                
                except IOError:
                        print("\n", Err_no_source)           
                        print("-->", filename)
                        if initialized: io.finish()
                        if not IDLE: io.waitforuser()
                        os._exit(1)                                         # graceful exit   

                print("building", sourcename)
                buildprog(sv)                                                  # FULL INITIALIZATION PROCEDURE
                if not initialized: io.initialize(sv, iocodes)         # input and output codes for event logging  
                io.init_interrupts(sv)                                          
                io.initbox(sv, showname)                                   
                initialized=True
                if parallel: sv.Graphic=True
                sv.Counter=0
                print("\n============================================")

                rt.filestore(sv)                                    # open file(s) for storage if needed                                                                     
                
                if not ErrorFound:      
                    if not sv.Graphic:    # RUN PROGRAM WITHOUT CONTROL PANEL  
                        if IDLE:
                            print("\nYou are running under IDLE: keyboard key input is not available\n")
                        if autotest:
                            io.Inpause=1                            # start at once in autotest
                        else:
                            io.waitforuser("Press Enter to start, Ctrl-C to abort")
                            if io.Inpause==2: raise KeyboardInterrupt
                        io.run(sv)                                             
                        sv.Current_time=0 
                        sv.t0=io.clock()+Epsilon_time        # synchro (inputs as delayed events)     
                        rt.test_update(sv)
                        io.closebox(sv)
                        initialized=False

                    if sv.Graphic:    # RUN PROGRAM WITH CONTROLPANEL
                        if not parallel:
                            svlist=[sv]
                            sv.masterto=[1]                             # include master box      v2.602
                            sv.Current_time=0                       
                            sv.t0=io.clock()+Epsilon_time  # synchro (inputs as delayed events)     
                            new_session=cp.makebox(svlist, autotest)
                            initialized=False
                        else:
                            svlist.append(sv)                      # run when all scripts compiled

            # end loop on script names                                        
            if parallel and not ErrorFound:             # RUN SCRIPTS IN PARALLEL
                for i, sv in enumerate(svlist):
                    sv.masterto=[i+1]+sv.masterto           # include master box
                    if sv.slaveto: svlist[sv.slaveto-1].masterto+=[i+1]  # master control on yoked scripts 
                    sv.Current_time=0                       
                    sv.t0=io.clock()+Epsilon_time     # synchro (inputs as delayed events)     
                new_session=cp.makebox(svlist, autotest)
                initialized=False

            pass            # do not loop for another session

        except ReferenceError:                            # error
                        ErrorFound=True                                     
                        if initialized:
                            io.finish()
                            rt.clear_outputs(sv)
                            if sv.Current_clause:
                                print("\n-->", sv.Current_clause)
                            print(Err_abort)
                        if autotest: print("\nTests lasted", io.clock()-debut)
                        if not IDLE: io.waitforuser()
                        os._exit(1)                              # graceful exit   

        except KeyboardInterrupt:	                 # manual abort	    
                        if initialized:
                            io.finish()
                            rt.clear_outputs(sv)
                        print(Err_abort, Crlf)
                        if Dumps:                                 # dump tree structure
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

        if initialized:                                         # exit autotest
            io.finish()
            rt.clear_outputs(sv)
            initialized=False
        if autotest: print("\nTests lasted", io.clock()-debut)
        
    if initialized:
        io.finish()
        rt.clear_outputs(sv)
    if not IDLE: io.waitforuser()
    os._exit(1)                                              # graceful exit

