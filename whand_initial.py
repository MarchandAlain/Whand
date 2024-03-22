# -*- coding: ISO-8859-1 -*-
# standard modules
from math import *                                                                   # think about changing it to 'import math' (find where used)
from random import random, shuffle                                        # a few functions

# whand modules
from whand_parameters import *                                             # options, constants
from whand_operators import *                                                # from... import because module only contains constants
from whand_tools import *                                                       # useful procedures only
import whand_io as io                                                              # I/O module for files   
import whand_nodes as nd                                                       # object class used for copy_node
import whand_runtime as rt
import whand_compile as cm

##===================================================== prepare_program
def prepare_program(sv):
    """
    Compute initial values and prepare script before run
    called by whand_V2 (main)
    Parameters
    ------------
    sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
    all information is directly stored in sv
    """
    start_values(sv)                                        # determine initial values 

    make_delayed_list(sv)                              # create a list of delayed objects

    make_active_list(sv)                                 # short list of objects that have effects                     
    prune_clauses(sv)                          # eliminate clauses for constant objects                          

    if Random_update_order:
            shuffle(sv.Object_list)                      # randomize evaluation order
    if Race_test: criticize(sv)                           # look for collisions      

    if "lsf" in Debog: print ("\n"+cm.reconstruct(sv))
    if 'obj' in Debog: list_object_clauses(sv)

    numerize_conditions(sv)                               # convert conditions to numbers
        
#=====================================================
#                                INITIALIZE PROGRAM
#===================================================== start_values
def start_values(sv):
    """
    Compute all initial values iteratively until values stabilize
    Relies on whand_runtime
    sv.Current_time is 0
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    verbose=('stv' in Debog)                                                         # controls debugging messages
    partial=not sv.Graphic or 'stp' in Debog                                  # display initial values
    if verbose: print()

    # initialize some variables
    sv.Current_time=0                                                                  # monitors time in experiment
    sv.Buff.clear()                                                                         # buffer to store text in file                                                    
    condlist=[]                                                                             # before converting clauses

    # list objects that must be initialized
    start_list=[nom for nom in sv.Object_list if nom!=Exit and sv.Object[nom].clauses]  # exit is evaluated later
    if verbose:                                                                              # display start list for debugging
        print ("start list:")
        for nom in start_list:
            print (sv.Object[nom].content())
        print ("\ninitializing values:")

    # stop and ask nature if necessary
    verif_nature(sv, start_list)                                                           

    # initialize simple objects
    initialize_simple(sv)

    # initialize copies of objects    
    rt.prepare_old(sv)                                                                   
    
    count_changes=1                                                                 # 0 if stabilized
    count_iter=0                                                                         # avoid too many cycles
    # INITIALIZATION LOOP
    while count_changes and count_iter<Max_iter:                      
        count_changes=0                                                             # loop until no change
        modified=[]                                                                      # used to debug circular dependencies 
        count_iter+=1                                                                  # count iterations  

        # browse objects that have clauses
        for nom in start_list:
            sv.Eval_depth=0                                                           # check recursivity (circular dependencies)
            sv.Indent=""                                                                # for printout and debugging
            if verbose: indprint (Crlf+"doing", nom, Col)                 # for debugging

            # get object and duplicate it
            nod=sv.Object[nom]
            if nod.once: continue                                               # if True, evaluation should not be repeated (volatile object)
            
            res=rt.insert_node(sv, Special+nom)                         # use temporary node for result 
            nd.copy_node(sv, nom,res)                                        # copy current value
         
            for i, (c,v) in enumerate(nod.clauses):                        # c and v are triplets                   
                sv.Current_clause=nom, c, v                                 # keep trace of clause
                
                # first EVALUATE CONDITION
                valid, changes=rt.evaluate(sv, c)                           
                if verbose: indprint ("  condition", c, valid.value)

                if not istrue(valid, 0): continue                              # do not evaluate
                
                # condition is true : EVALUATE VALUE
                if verbose: indprint ("  MAKING VALUE")
                res, changes=rt.evaluate(sv, v, objname=nom)     # result of evaluation in res

                # now APPLY CHANGES from res to nod

                # newly delayed object: update if needed
                if res.isdelayed and not nod.isdelayed:             
                    nod.isdelayed=True
                    count_changes+=1

                if res.value== nod.value or res.value is None: continue   # no new value
                    
                # NEW VALUE
                count_changes+=1                                             # it is a new value
                if verbose: indprint ("change value", nod.name, "from", nod.value, "to", res.value)

                # verify nature compatibility
                compare_nature(nod, res)                             
                
                # mark stochastic objects as evaluated once
                if v[0] in Stochastic: nod.once=True                     #  stochastic operator
                if v[0]==Call:
                    for f in Volatile_calls:
                        if v[1][0].startswith(Quote+f+Obr): nod.once=True  # stochastic call
                        
                # prepare file storage if required
                fst=applied(nom, Store)                             
                if fst: rt.bufstore(sv, fst, res.value)                        # store value
                
                # transfer value from res to nod
                nod.value=res.value if type(res.value)!=list else res.value[:]
                
                # make copy of nod as old
                cop=Old+Obr+nom+Cbr                           
                if cop in sv.Object:
                    sv.Object[cop].value=res.value if type(res.value)!=list else res.value[:]

                # store occurrence if Boolean
                store_event(nod)

            # END for i, (c,v) in enumerate(nod.clauses)
            
            # update start_list with newly created nodes
            for x in nod.causes:                                                        
                if not x in start_list:
                    start_list+=[x]
                    count_changes+=1

        # END for nom in start_list
        
        # set unitialized Booleans to false by default then loop
        if count_changes==0:                                                        
            for nod in sv.Object.values():                                                  
                if nod.value==[(None, None)]:
                    nod.value=[(None, 0)]
                    count_changes=1                                                  # needed to update opposite (not) events 

        # compute Exit only after full initialization then loop               
        if count_changes==0 and Exit in sv.Object and not Exit in start_list: 
            start_list=[Exit]
            count_changes=1

    # END while count_changes and count_iter<Max_iter

    # update lastchange
    for nod in sv.Object.values():                                                  # cancel all changes after initialization  
        if nod.nature!=Bln: nod.lastchange=None                          # except for Booleans

    # add exit object if absent
    add_exit(sv)

    # check initialization (infinite loop)
    if count_iter>=Max_iter:                                                         
        warn("\n"+Warn_iterations+" ---> "+str(modified)+"\n")

    # list objects when debugging
    if verbose or partial:
        list_objects(sv, verbose)

    # check if all objects have been initialized
    verif_init(sv)
    
    if (verbose or partial) and sv.Buff: print()                             
            
#===================================================== verif_nature
def verif_nature(sv, start_list):                                                           
    """
    verify that all needed objects have unambiguous nature, else stop and ask
    called by start_values 
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        start_list: a list of object names
    Returns
    --------
        an error message asking for information (user must complete script)
    """
    undet=[nom for nom in start_list if len(sv.Object[nom].nature)!=1]                      
    if undet:                                                                               # more than one possible nature
        print("\n", Err_ask_nature, "\n    ", str(undet)[1:-1])
        raise ReferenceError
    
#===================================================== initialize_simple
def initialize_simple(sv):
    """
    give a value to simple objects. Initialize lists to empty lists, states to their name and Booleans to undefined
    called by start_values
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for nom in sv.Object_list:                                                             
        nod=sv.Object[nom]
        nod.once=False                                                                      # limits changes of stochastic objects during initialization
        if nom==Vrai or nod.value==Vrai: nod.value=[(0, None)]        #   true 
        elif nom==Faux or nod.value==Faux: nod.value=[(None, 0)]   #   false 
        elif applied(nom, Change): nod.value=[(None, 0)]                    # no change at start
        
        elif nod.value is None:
            if isnumber(nom): nod.value=float(nom)                            # explicit number  
            elif isduration(nom): nod.value=str(seconds(nom))+Unit_sec  # explicit duration
            elif nod.nature==Lst: nod.value = []                                    # initialize list 
            elif nod.nature==Stt: nod.value=nod.name                         # initialize state to its name
            elif nod.nature==Bln and nom!=Start: nod.value=[(None, None)]  # initialize Boolean to undefined   

#===================================================== compare_nature
def compare_nature(nod, res):
    """
    verify that result has same nature as object
    called by start_values 
    Parameters
    ------------
        nod: a node representing an object
        res: a copy of this node holding a new result
    Returns
    --------
        an error message asking for information (user must complete script)
    """
    if len(nod.nature)==1 and not nod.nature[0] in res.nature:
        if Stt[0] in nod.nature+res.nature:
            print("\n", Err_ask_nature)                     # "*** Indeterminate nature: Please add a 'be' instruction ...
        else:
            print("\n", Err_conflict_nat)                    # ***Error: nature conflict ***
        print(nod.name+Col, nod.nature, res.nature)
        raise ReferenceError

#===================================================== store_event
def store_event(nod):
    """
    store occurrence for Booleans true at start
    called by start_values
    Parameters
    ------------
        nod: a node representing an object
    Returns
    --------
        all information is directly stored in sv
    """
    if nod.nature==Bln:
        if istrue(nod, 0):                                      # Boolean changed if true at start 
            nod.lastchange=0                         
            nod.occur=[0]
            nod.count=1

#===================================================== add_exit
def add_exit(sv):
    """
    add exit object if absent (required in runtime and controlpanel)
    called by start_values
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    if not Exit in sv.Object:                                                            
        if not sv.Graphic: warn("\n"+Warn_no_exit+"\n")           
        rt.insert_node(sv, Exit)                                                         # add exit node
        sv.Object[Exit].nature=Bln                                                   # make it an event          
        sv.Object[Exit].value=[(None, 0)]                                          # set it to false          

#===================================================== verif_init
def verif_init(sv):
    """
    verify objects are initialized
    called by start_values
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        a warning message
    """
    uninit=[]                                                                                 # check if all objects have been initialized
    for nom in sv.Object_list:                                                         # exclude some objects by name
        if (nom.startswith(Special) or nom in Fixed+[Start, Exit, Controlpanel, Ewent, Number, Delay, State, List]  \
                    or isnumber(nom) or isduration(nom) \
                    or applied(nom, Show) \
                    or applied(nom, Unused) ): continue                        # ignore these objects
        
        # exclude some objects by properties
        nod=sv.Object[nom]
        if nod.isexpression: continue                                                
        bad=False
        if nod.value is None: bad=True   
        elif type(nod.value)==list and len(nod.value)>0:               # special case: lists
            bad=True
            for x in nod.value:                                                       # look for at least one initialized element
                if x is not None: bad=False       
        if bad: uninit+=[nom]
            
    if uninit and Warnings:
        warn("\n"+Warn_no_value_at_start+"    "+str(uninit)[1:-1])

#===================================================== make_delayed_list 
def make_delayed_list(sv):
    """
    create a list of delayed events. Delaying a list is forbidden (only delayed elements).
    nb: change(x) is not delayed. It has an until clause in the case of lists.
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv.Delayed_objects
    """
    sv.Delayed_objects=[]
    
    for nam in sv.Object_list:
        nod=sv.Object[nam]
##    for nod in sv.Object.values():                                  # WRONG BECAUSE RANDOMIZES ORDER
##        nam=nod.name
        if nam[0]==Special: continue                                   # ignore old and special objects
        if nod.nature==Lst: nod.isdelayed=False                           
        elif applied(nam, Begin) or applied(nam, End) or applied(nam, Pin) or applied(nam, Key) \
             or applied(nam, Measure) or applied(nam, Read): nod.isdelayed=True

        if nod.isdelayed: sv.Delayed_objects+=[nam]     # LIST COMPREHENSION IS WRONG BECAUSE RANDOMIZES ORDER
##    sv.Delayed_objects=[nod.name for nod in sv.Object.values() if nod.isdelayed]

#===================================================== make_active_list
def make_active_list(sv):                                                                                            
    """
    create a short list of active objects directly susceptible to change and that have consequences
    this list is used at runtime to initialize updating
    volatile objects are displayed outputs, named pins and implementations of 'lasted' (see whand_compile)
    sv.Active_list may be shuffled if parameter Random_update_order is True
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv.Active_list
    """
    sv.Active_list=[]                                                     
    for nam in sv.Object_list:                                                  
        if nam[0]!=Special and sv.Object[nam].effects:              #must have effects
            if nam in sv.Volatile or sv.Object[nam].isdelayed or applied(nam, Old): 
                sv.Active_list+=[nam]
    if Random_update_order: shuffle(sv.Active_list)                # randomize evaluation order

#===================================================== prune_clauses
def prune_clauses(sv, tree=Special):                             
    """
    remove change of constants in conditions after initialization 
    works on each object (if tree is Special), then recursively on tree
    eliminates one clause at a time, never the last one
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet or None. Special means scan whole program
    Returns
    --------
        all information is directly stored in sv
    """
    if tree is None: return None
    # process all program
    if tree==Special:
        for nod in sv.Object.values():                                           # browse all objects that have clauses
            clau=[]
            for (c,v) in nod.clauses:                                               # browse clauses
                if c==(Start, None, None): continue                        # remove start conditions
                k=prune_clauses(sv, c)                                            # RECURSE on conditions
                if k: clau+=[(k,v)]                                                    # simplify
            nod.clauses=clau                                                       # store clauses
                    
    # process a single condition or value           
    else:                                                                                 
        op=tree[0]
        if not tree[1] and not tree[2]:                                          # remove constants
            if op in Fixed: return None                                         # Fixed=[Vrai, Faux, Epsilon, Empty]
            if op in sv.Object and not sv.Object[op].clauses:
                if not sv.Object[op].nature in [Bln, Lst]:                   # only number, duration or state
                    return None
            
        if op==Comma:                                                             # process lists
            active=False
            for x in tree[1]:
                if prune_clauses(sv, x): active=True
            return tree if active else None

        # process operators        
        t1=prune_clauses(sv, tree[1])                                         # RECURSE
        t2=prune_clauses(sv, tree[2])                                         # RECURSE
        if op==Or and not t2: return t1                                     # remove functions of None
        if op==Or and not t1: return t2
        if op==And and not (t1 and t2): return None
        if op in Unary and not t1: return None 
        return op, t1, t2

#=====================================================
#                                  BUILD CONDITIONS AS NUMBERS
#===================================================== numerize_conditions
def numerize_conditions(sv):                                                                                            
    """
    replace conditions with a table. Each condition corresponds to an index in the table  
    makes a different code for different types of conditions and makes pointers from the X object
    sv.Condition_number is a pointer to a list of condition codes
    sv.Condition is a variable: 1 means condition fulfilled, 0 otherwise
    also saves value in dict sv.Save_value
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information stored in sv.Condition_number, sv.Condition, sv.Save_value and sv.Object
    """
    sv.Condition=[1]                                                             # unique condition for Always
    for nam in sv.Object_list:
        sv.Condition_number[nam]=[]                                    # initialize code list for all objects
        
    for nam in sv.Object_list:                                                # n.b. this loop modifies other dict elements  
        nod=sv.Object[nam]
        if nam[0]==Special:                                                    # no clause for special objects (old value or temporary copy)                                       
            nod.clauses=[]
            continue
        
        clause_list=[]
        for c,v in nod.clauses:                                                 # extract condition and value
            if c[0]==Start or c[0] is None: continue
            if c[0]==Always: 
                condnum=0                                                      # always: single condition equal to 1 (true)
            else:                                                                      # begin, end, change
                condnum=len(sv.Condition)                              # attribute next number to condition
                one_condition(sv, nam, c, condnum)                  # reprocess condition
            valnum=len(sv.Save_value)                                    # attribute next number to value
            clause_list+=[(condnum, valnum)]                         # replace c and v with numbers
            sv.Save_value[valnum]=c, nam, v                           # save original condition and value 
        nod.clauses=clause_list                                              # rewrite clause list 
        
#===================================================== one_condition
def one_condition(sv, nam, c, condnum):                                                                       
    """
    Replace a condition with a table entry (index N). Condition c concerns object nam.
    Returns a numeric code for the condition
    Makes a code for different types of conditions and make pointers from cause c
    sv.Condition_number[obj] is the list (coded) of clauses depending on cause c
    Here, only the current clause  is added to the list
    codes are 0, -N, +N and N+2^20 (BigNumber=2^20=1.048.576)
    for always, when change X, when end X, and when begin X, respectively
    For change of lists and dicts, make a direct pointer from each element to the condition for nam
    bypassing the list itself. Also increments effect list from element to nam when needed 
    if list changes at runtime, updating is performed, except for effect lists.
    called by prepare_program and runtime.py
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, the name of an object
        c: a triplet, a condition for this object
        condnum: an integer indexing the new condition
    Returns
    --------
        information is directly stored in sv.Condition and sv.Object
    """
    # compute condition code
    op=c[0]                                                              # op must be begin, end or change (not always)   
    code=None                                                        # code depending on type of condition
    cause=c[1][0]                                                      # extract name of cause from c (without op) 
    if isnumber(cause) or isduration(cause): return     # do not link constants
    if op==End: code=condnum                               # compute code depending on type of condition
    elif op==Begin: code=condnum+BigNumber
    elif op==Change: code=-condnum
    
    # create links 
    sv.Condition+=[0]                                               # expand condition logical state table
    if not cause in sv.Condition_number:                   # create key for cause if needed
        sv.Condition_number[cause]=[code]        
    elif not code in sv.Condition_number[cause]:       # avoid duplicates (list lookup)
        sv.Condition_number[cause]+=[code]              # append code to list for cause c
        
    # make direct links from list elements (only condition change is allowed)
    if op==Change and sv.Object[cause].nature==Lst: # each element may drive condition change

        # remove direct change conditions from cause to nam (cause is the list)
        if (cause, nam) in sv.All_conditions:                  
            for ky, i in sv.All_conditions[(cause,nam)]:   # revert prior shortcuts
                sv.Condition_number[ky][i]=None         # make condition obsolete (do not distroy order)
        sv.All_conditions[(cause,nam)]=[]                   # re-initialize revert pointers

        # create new change conditions from elements to nam        
        if sv.Object[cause].value:                                # extract list of elements if not None
            for elemname in sv.Object[cause].value:     # get element name
                if isnumber(elemname) or isduration(elemname) or elemname is None: continue    # ignore constants
                elt=str(elemname)                                 # create a key from name
                if not elt in sv.Condition_number: sv.Condition_number[elt]=[]   # element may not already have effects
                if not code in sv.Condition_number[elt]: # avoid duplicates
                    sv.All_conditions[(cause,nam)]+=[(elt, len(sv.Condition_number[elt]))]  # keep pointers to revert shortcuts
                    sv.Condition_number[elt]+=[code]     # append new code to elt effects
                if elt in sv.Object and not nam in sv.Object[elt].effects:      # slow 'in'
                    sv.Object[elt].effects+=[nam]             # update effects directly from element
                    sv.Object[nam].causes+=[elt]             # update cause directly to element (for consistency)
        
#===================================================== updatecond
def update_condition(sv, nam, st=None, ch=False):               
    """
    directly update conditions if value of nam changes (see one_condition)
    st is None if status has not changed, True or False otherwise
    ch is False if value has not changed
    sv.Condition_number[nam] gives a list of all clauses involving nam
    with a specific code n for each type of condition (begin, end or change)
    Each clause is a single event
    sv.Condition gives the current status of this event
    called by runtime.py
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    if nam in sv.Condition_number:                                                    
        if st is not None:                                                                        # status has changed
            for n in sv.Condition_number[nam]:
                if n is not None:                                                                 # protect from obsolete conditions
                    if n<0:                                                                            # condition change
                        sv.Condition[-n]=1
                    elif n>BigNumber:                                                         # condition begin
                        if st is True: sv.Condition[n-BigNumber]=1            
                    elif n>0:                                                                         # condition end
                        if st is False: sv.Condition[n]=1                             
        elif ch:                                                                                       # value has changed
            for n in sv.Condition_number[nam]:
                if n is not None:                                                                # protect from obsolete conditions
                    if n<0:                                                                           # condition change
                        sv.Condition[-n]=1

#=====================================================
#                                  LIST VARIABLES
#===================================================== list_objects
def list_objects(sv, verbose):
    """
    print a list of objects for debugging
    called by start_values
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        verbose: a Boolean: print all objects if True
    Returns
    --------
        only prints to screen
    """
    print("Initial values:")
    for nom in sv.Object_list:
        ok=True
        if not verbose:
            if nom.startswith(Special) or isnumber(nom) or isduration(nom):
                ok=False
            if nom in Fixed+[Start, Exit, Controlpanel]+ \
               ["(None, None)", "(None, 0)", "(0, None)", "(0, 3e-06)"]:
                ok=False
            for x in [Show, Unused, Load, Store, Output, Command, Write, \
                      Begin, End, Change, Count]:
                if applied(nom, x): ok=False
        if ok:
            nod=sv.Object[nom]
            if not nod.isexpression:                                                # exclude some objects by properties
                print(sv.Object[nom].content()) 

#===================================================== list_object_clauses
def list_object_clauses(sv):
    """
    print a list of all objects and their clauses for debugging
    called by prepare_program
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        only prints to screen
    """
    print()
    for nam in sv.Object_list:
        if nam[0]!=Special:                    # do not print object copies
            nod=sv.Object[nam]
            print("*", nod.content())
            for c,v in nod.clauses:
                print("   cond:", c, "val:",v)
            print()

###===================================================== __main__ (tests)
if __name__== "__main__":
    import whand_sharedvars as sp
    import whand_precompile as pc
    import sys
##    sys.exit()

    Debog="lsf obj"
    sv=sp.spell()
    try:
        tout=io.readscriptfile("../scripts/essai.txt")                   # try precompiling a script and print result            
        prog=pc.precompile(sv, tout)
        cm.compile(sv, prog)
        prepare_program(sv)
        
    except ReferenceError:
        if type(sv.Current_clause)==tuple:
            nam, c, v = sv.Current_clause       
            sv.Current_clause=nam+Col+Space+When+Space+tree_join(c)+Col+Space+tree_join(v)       
        print(sv.Current_clause)
        print("\n---  PROCESS ABORTED  ---")



