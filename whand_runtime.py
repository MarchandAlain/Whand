# -*- coding: ISO-8859-1 -*-
### whand modules
from whand_parameters import *                                             # options, constants
from whand_operators import *                                                # from... import because module only contains constants
from whand_tools import *                                                        # useful procedures only
import whand_io as io                                                               #  I/O module for drivers
import whand_nodes as nd                                                       # object class
import whand_compile as cm
import whand_initial as iv
from whand_operations import *

#===================================================== test_update
def run_update(sv):
    """
    Run real time without controlpanel. Initialize outputs and scan pins. Run update loop
    called by Whand_V2 (main)
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    # initialize execution
    init_outputs(sv)                                                                 # set all outputs to their initial status                                                           
    pinscan(sv)                                                                       # scan inputs and make them delayed events                                                               
    sv.delayed_list = nextevents(sv)                                         # prepare list of delayed events

    # loop or pause
    while not istrue(sv.Object[Exit], sv.Current_time):                # loop until exit
        while io.testpause()!=1:                                                 # check for pause: wait for 1   
            io.keyscan()                                                              # scan keyboard
            if io.testpause()==2: raise KeyboardInterrupt             # abort from keyboard (Ctrl-C)
        update_loop(sv)                                                           # run program                                                            

    # end program   
    print("\n",End_prog, "\n")                                          
    print("Lasted", io.clock()-sv.t0+2*Epsilon_time)

#===================================================== update_loop   
def update_loop(sv):
    """
    Process one time step with additional steps for delayed events occurring within the step
    called by test_updates and whand_controlpanel
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    # compute next time step (avoids time slippage and guarantees updating)
    nextstep=sv.Current_time+Timestep

    # initialize time step
    stlist=[]                                                                                # clear all changes
    if not istrue(sv.Object[Exit], sv.Current_time):
        io.keyscan()                                                                     # scan key input 
        pinscan(sv)                                                                      # scan pins before each time step 
        sv.delayed_list = nextevents(sv)                                       # reorder all delays (keys and pins are delayed)
        # if no input is expected, force exit from infinite loop
        if not sv.delayed_list and not sv.Pinlist and Testerror in sv.Object:                            
            print("\n*** Infinite loop detected: Execution stopped ***")
            sv.Object[Exit].value=[(sv.Current_time, None)]   
    
    # check and process objects whose values may change without direct cause, first of all
    # volatile objects are pointer, lasted itis (see whand_compile). What about displayed outputs ???
    for nom in sv.Volatile:                                                                                          
        sv.Object[nom].haschanged=True                                   # update_condition is not tested because clause is 'always'   
        sv.Object[nom].lastchange=sv.Current_time                    # mark object as changed  
##        if sv.Graphic:  updatepanel(sv, nom)                               # update display on controlpanel ???
        updateval(sv)                                                                 # start updating                                                      
    
    # process all delayed events within timestep before refreshing display and scanning inputs        
    while sv.delayed_list and abs(sv.delayed_list[-1][0])-FloatPrecision<nextstep:   # look for delayed event within timestep 
        done= False                                                                  #  iterate (in case of simultaneous delays)

        # extract delayed event (earliest is last in the list)        
        while not done:                                                              
            done=True                                                               
            evt=sv.delayed_list.pop()             
            nexttime=abs(evt[0])                                                   # delayed event time
            nom=evt[1]                                                                # delayed event name
            nod=sv.Object[nom]                                                   # delayed event
            
            advance_time(sv, nexttime)                                        # ADVANCE TIME to delayed event

            # update event status
            cleanup_delays(sv, nod)                                              # cleanup old delays in object occurrence times
            fuse_delays(sv, nod)                                                   # reorder delays
            status=istrue(nod, sv.Current_time)                             # new status (may be an ON or OFF event)

            # update pinstate of pins and keys as delayed events (do not updateval until all are done)
            if applied(nom, Pin) or applied(nom, Key): sv.Pinstate[nom]=Vrai if status else Faux

            # display on controlpanel              
            if sv.Graphic and nom in sv.Visible and not nom in sv.Namedpinlist: sv.interface.update(sv, nom)                                                           

            # update consequences of delayed event 
            iv.update_condition(sv, nom, st=status)                      # update condition to update consequences       
            nod.haschanged=True                                               # mark object as changed                                       
            nod.lastchange=sv.Current_time                                 # set change time 

            #  test for more simultaneous delays
            if sv.delayed_list and abs(sv.delayed_list[-1][0])<= sv.Current_time: done=False

        updateval(sv)                                                                # now for all events within the same time step
        
        # END of loop: while not done 

        sv.delayed_list = nextevents(sv)                                      # reorder all delayed events       
        if istrue(sv.Object[Exit], sv.Current_time): break               # EXIT

    # END of loop: while sv.delayed_list                                  # all current delayed events ave been processed

    if not sv.Graphic and not sv.Do_tests:                                # wait for clock 
        while (io.clock()-sv.t0)<sv.Current_time:                         # do not anticipate. Avoid missing delayed Pins 
            pass                                                                         # wait
##    jitter()                                                                           # debugging tool
            
    if len(sv.delayed_list)>Max_iter*len(sv.Delayed_objects):     # detect delayed objects explosion
        print(Warn_multi_update, sv.Do_tests)                           # *** Warning: multiple updating ***                             
        
    advance_time(sv, nextstep)                                               # ADVANCE TIME to next time step 

#===================================================== advance_time
def advance_time(sv, newtime):
    """
    Advance current time to newtime
    called by update_loop
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        newtime: new value for sv_Current_time
    Returns
    --------
        all information is directly stored in sv (old), sv.Current_time and sv.Condition
    """
    if newtime>sv.Current_time:
        prepare_old(sv)                                                            # make a copy for function old before advancing time    
        sv.Current_time=newtime                                            # ADVANCE TIME HERE without slippage
        for n in range(1, len(sv.Condition)):
            sv.Condition[n]=0                                                    # reset all conditions to 0, except 'always' at index 0

# ==================================================== evalue_status
def evalue_status(sv, tree):                       
    """
    computes the status of a tree expression based on first element in a delayed event list
    called by update_loop, evaluate, distribute_glitch
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: expression corresponding to an event, delayed or not
    Returns
    --------
        True or False (default)
    """
    status=False                                            
    val, chg=evaluate(sv, tree)                                                     # compute current value of expression
    occurrences=val.value                                                           # list of on/off doublets, or None
    if occurrences: status=logic(occurrences[0], sv.Current_time)  # status of first element in list
    
#===================================================== updateval
def updateval(sv):                                                               
    """
    Compute values when something changes, based on haschanged flag in sv.Active_list
    sv.Active_list is computed in make_activelist after initialization  
    then completed with newly created events or glitches
    Allow multiple changes in one time step for delays only   
    called by update_loop
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv 
    """
    Verbose='upv' in Debog

    start_list=[nom for nom in sv.Active_list if sv.Object[nom].haschanged]
    if Verbose and start_list: print("xxxx UPV start list:", sv.Current_time, start_list, "active:", sv.Active_list)

    next_list=[]                                                                            # list of effects to update            
    for nom in start_list:                                                              
        nod=sv.Object[nom]
         
        # count occurrences of events
        if nod.nature==Bln and istrue(nod, sv.Current_time) and (nod.occur==[] or nod.occur[-1]!=sv.Current_time): 
            set_occur(nod, sv.Current_time)                                     # add a new occurrence and update count
            if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became true")     

        # make sure consequences of old will be processed                                                                    
        if applied(nom, Old):                                                         
            if nod.nature==Bln:
                iv.update_condition(sv, nom, st=istrue(nod, sv.Current_time))  # immediately update condition
            else:
                iv.update_condition(sv, nom, ch=True)                      # object has changed, so old must change too

        # list effects of changed objects
        next_list+=nod.effects                                                       # duplicates are removed later                                                 
        nod.haschanged=False                                                      # reset after processing       

    # start iterative updating
    count_iter=0                                                                         # avoid too many iterations
    while start_list and count_iter<Max_iter:                                 # outer loop: repeat until no more effects or too many iterations
                                                                                                # start_list will be updated with effects during loop 
        count_iter+=1                                                                   # iteration count

        # nodes that have changed or need changing        
        for nom in start_list:                                                          
            nod=sv.Object[nom]
            changes=False                                                              # flag: continue updating until no change left
            sv.Eval_depth=0                                                            # avoid excess recursivity (circular dependencies)            
            if Verbose: print("xxxx updating", sv.Current_time, "s:", nom, nod.value, nod.nature)

            # browse clauses for the object (as numbers)            
            for c,vnum in nod.clauses:                                                                             
                if c is None: continue                                                # obsolete clause
                  
                cnd, nam, v=sv.Save_value[vnum]                              # retrieve clause as full tree
                sv.Current_clause=(nom, cnd, v)                                 # keep track of current clause for debugging purposes                          
                if Verbose: print("xxxx cond", sv.Current_time, "s:", nom, Col, When, cnd, (c,), [sv.Condition[c]==1], Col, v)

                if (sv.Condition[c]!=1): continue                                # condition is fulfilled if equal to 1 (see update_condition)

                # special case: function tell
                if v[0]==Tell:
                    evaluate(sv, v, clausenum=vnum)                        # evaluate and print
                    return                                                                   # do not evaluate node
                
                # compute value and deep changes                                                                                            
                res, ch=evaluate(sv, v, clausenum=vnum)                                     # NOW EVALUATE NODE <---------------
                                                                                               # clausenum helps accelerate processing in prepareval 
                changes=changes or ch                                           # keep track of changes across conditions            
                if Verbose: print("xxxx result", sv.Current_time, "s", nom, nod.nature, nod.value, "<--", res.content())

                # Is it a new value
                if not value_has_changed(sv, nod, res, ch): continue   # no change
                avoid_reuse(sv, nod)                                                 # already changed in same time step ?
                
                # verify nature at runtime
                if sv.Current_time!=0 and not nod.nature[0] in res.nature:   
                    print(Err_conflict_nat)
                    print(nom, res.nature, nod.nature)
                    raise ReferenceError                      

                if applied(nom, Store): bufstore(sv, applied(nom, Store), res.value)  # store in memory to write on disk later

               # copy result to nod
                accept_result(sv, res, nod)                                           

                # update conditions      
                if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just changed")
                iv.update_condition(sv, nom, ch=True)                            # update conditions for change
                if nod.nature==Bln: update_event_conditions(sv, nod)     # update conditions for event transition: occur and status
                if nod.nature==Lst: update_list_conditions(sv, nod)          # update conditions for a list (changing list)

                # update output and controlpanel
                update_output(sv, nom)

                # effects for further updating
                next_list+=nod.effects                                                    # determine effects
                if v[0]==Next:                                                                 # next must update pointer
                    pname=Pointer+Obr+v[1][0]+Cbr
                    if pname in sv.Object: next_list+=[pname]

                next_list=[x for x in next_list if x!=nom]                           # do not update same object

            if Verbose: print("xxxx Current value at", sv.Current_time, ":", nod.content(), Crlf)

        # further updating with effects. Control updating order
        start_list=no_duplicate(next_list)                                               # remove duplicates keeping fixed updating order
        next_list=[]                                                                               # clear list of required updates
        if Random_update_order:
            shuffle(start_list)                                                                   # random updating order
##        else:
##             start_list=reorder(start_list)                                               # controlled order to debug special cases           
        if Verbose: print("xxxx next:", start_list, Crlf)

    # END OF LOOP while start_list and count_iter<Max_iter
    if count_iter>=Max_iter:
        warn("\n"+Warn_circular+"\n"+str(start_list), sv.Do_tests)          # too many iterations: fatal during tests

    # now store to file 
    filestore(sv)

#===================================================== value_has_changed
def value_has_changed(sv, nod, res, ch):
    """
    determine whether res is a new value for nod
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object 
        res: an object, result of the evaluation of nod
        ch: a Boolean, indicating changes
    Returns
    --------
        newval: a Boolean, True if value has changed
    """
    nom=nod.name
    newval=(res.value!=nod.value) or ch                         # a valid new value
    # outputs: write once even if value has not changed
    for x in Outputs:
        if applied(nom, x) and nod.lastchange!=sv.Current_time and sv.Current_time>0:
            newval=True
            break

    # special case for events: no change if delays or status are the same                   
    if newval and nod.nature==Bln:
        if nod.isdelayed or res.isdelayed:                          # modified after Whanda 
            prev=nod.value[:]                                             # delayed event: check if changed
            fuse_delays(sv, nod, res)                                   # set new delays (would be better if done later)       
            if nod.value==prev:
                newval=False                                               # no change if delays are the same
        else:                                                                     # adjust event times
            res.value=[(sv.Current_time, None)] if istrue(res, sv.Current_time) else [(None, sv.Current_time)]
            if istrue(res, sv.Current_time)==istrue(nod, sv.Current_time):
                newval=False                                               # no change if status is unchanged
                
    return newval                            

#===================================================== update_event_conditions
def update_event_conditions(sv, nod):
    """
    updates conditions based on onset or offset of an event
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object (event)
    Returns
    --------
        all information is directly stored in sv.Condition
    """
    Verbose='uec' in Debog
    nom=nod.name
    if nod.value[0][0]==sv.Current_time:                                 # onset
        iv.update_condition(sv, nom, st=True)
        set_occur(nod, sv.Current_time)
        if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became true")
        
    elif nod.value[0][1]==sv.Current_time:                              # offset
        iv.update_condition(sv, nom, st=False)
        if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became false")

#===================================================== update_list_conditions
def update_list_conditions(sv, nod):
    """
    updates conditions of effects based on all elements of a list
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object (list)
    Returns
    --------
        all information is directly stored in sv.Condition
    """
    for eff in nod.effects:                                                   # access effects of this list
        nodE=sv.Object[eff]
        for i, (num,vnum) in enumerate(nodE.clauses):         # extract condition
            c, nam, w=sv.Save_value[vnum]                           # retrieve original condition                                   
            if c[0]!=Start: iv.one_condition(sv, eff, c, num)      # reprocess condition

#===================================================== accept_result
def accept_result(sv, res, nod):                                     
    """
    copy result to nod
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object
        res: an object, result of the evaluation of nod
    Returns
    --------
        all information is directly stored in nod
    """
    nod.lastchange=sv.Current_time                  
    if  nod.isdelayed:
        cleanup_delays(sv, nod)                                           # remove past delays without sorting
    else:
        if type(res.value)==list and res.value!=nod.value:      # lists: works also for nondelayed events
            nod.value=res.value[:]                                          # make a true copy of list  
            nod.pointer=0                                                     # reset pointer if list changes (avoid next with event lists)
        else:
            nod.value=res.value                                             # simple copy

#===================================================== update_output
def update_output(sv, nom):
    """
    apply output to hardware and display
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nom: an object name
        Returns
    --------
        all information is directly applied
    """
    link_output(sv, nom)                                                       # OUTPUT EFFECTS   
    if sv.Graphic:
        updatepanel(sv, nom)
        if nom in sv.Visible and not nom in sv.Namedpinlist:   # slow 'in' but only with graphic - maybe use a set instead
            sv.interface.update(sv, nom)

#===================================================== evaluate
def evaluate(sv, tree, objname=None, clausenum=0):                  
    """
    compute current value of a tree expression
    applies distributivity
    called by updateval, evalue_status, RECURSIVE
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: an object triplet or None
        objname: name of object, if tree is a formula for the value of this object
        clausenum is a key to parameters for prepareval to accelerate processing
    Returns
    --------
        res: an object, result of the evaluation of tree
        change: a Boolean indicating hidden changes (inside a list)
        other information is directly stored in sv (old), sv.Current_time and sv.Condition
    """
    Verbose='evl' in Debog and ('stv' in Debog or sv.Current_time>0)

    # simple expressions    
    if not tree: return sv.Object[Faux], None                     # nothing to evaluate    
    inc_recurse(sv)                                                           # recursivity level 

    nom=tree_join(tree)                                                   # name of tree expression                                                  
    if nom in sv.Pinlist: return evaluate_pin(sv, nom)         # process pin input
            
    O,A,B=tree                                                                # decompose expression         
    if not A and not B: return evaluate_simple(sv, O)        # simple leaf object (not expression)
    
    if O==Obr: return evaluate_bracket(sv, A)                   # bracketed block - RECURSIVE

    # prepare a temporary node for result
    res=cm.add_object(sv, Special+Special+nom)                               
    nd.copy_node2(sv, nom, res)                                      # copy current attributes (if any) to the new node
    
    if O==Old: return dec_recurse(sv, res, None)               # Old is processed elsewhere (prepare_old)
    if O==Comma: return evaluate_list(sv,A, res)               # defined list: return list of names
       
    #  other expressions: debugging clues
    sv.Current_clause=nom, None, None                                      
    if Verbose:
        print("xxxx evaluate", sv.Current_time, "s :", nom, tree)
        if nom in sv.Object: print("xxxx    ->", sv.Object[nom].content())

    # evaluate terms        
    nodA, changes=evaluate(sv, A)                                    # RECURSIVE                         
    nodB, changes=evaluate(sv, B)                                    # RECURSIVE
    n1=nodA.nature[:]
    n2=nodB.nature[:]
    args=tree, nom, O, A, B, nodA, nodB, n1, n2, res

    if O in sv.Object: return evaluate_list_element(sv, *args)  # list element (subscripted)       

    # special functions (non distributive)
    if O in special_evaluation:
        return dec_recurse(*evaluate_special(sv, *args))

    # distribute list of Begin or End
    if O in [Begin, End] and sv.Object[A[0]].nature==Lst:
        res.value=distribute_glitch(sv, tree, nom)                  # call rather complex routine
        return dec_recurse(sv, res, True)                                # end evaluation 

    # distribute list of delayed events (event list+delay or event+delay list)
    dd=distributive_delay(sv, objname, *args)
    if dd: return dec_recurse(sv, *dd)                                   # end evaluation 
        
    # operators with possible distributivity   
    nodistr1=(O in Non_distributive1)
    nodistr2=(O in Non_distributive2)

    # has this operation been disambiguated ?
    allow=sv.Allow_dic[clausenum] if clausenum in sv.Allow_dic else Allowed[O]       

    # look for a nature match
    ambiguity=0                                                                          # flag for ambiguous ops                                                      
    for nat1, attr1, nat2, attr2, natres in allow:               

        # extract appropriate attributes as lists to allow distributivity    
        if Verbose: print("xxxx allow try", nom, clausenum, nat1, attr1, nat2, attr2, natres)
        li1, distrib1=prepareval(sv, nodA, nat1, attr1, nodistr1)         
        if Verbose: print("xxxx preparing", O, A,nat1, attr1, nodistr1)
        li2, distrib2=prepareval(sv, nodB, nat2, attr2, nodistr2)          
        if Verbose: print("xxxx result nature", O, A, distrib1, B, distrib2, natres, res.nature)
        
        # check validity of operands
        valid=valid_operands(sv, O, li1, li2, nodB, nat1, nat2, natres)
        if not valid: continue                                                          # do not evaluate
        
        ziplist=make_distribute_list(li1, li2, distrib1, distrib2)    
        result_list=[]

        # individual operation on each pair of ziplist         
        for v1, v2 in ziplist:                                                          
            vlu=evaluate_normal(sv, O, v1, v2)                                # NOW COMPUTE OPERATION
            if Verbose: print("xxxx COMPUTED", sv.Current_time, "s:", nom, ":", O, v1,v2, "-->", vlu, natres, res.nature)
            
            # build list of results
            result_list+=[adjust_result(sv, O, vlu, nat1, nat2, natres, distrib1, distrib2)]            
            
        # end of distribute loop                    
        ambiguity+=1                                                                  # check if ambiguous operation                            
        if ambiguity>1:
            print(Err_ambig_op, O, A, B)                                           # *** Error: Operation is ambiguous ***
            raise ReferenceError

        # store disambiguation parameters for faster use                
        if clausenum and not clausenum in sv.Allow_dic:                 # one operation per clause 
            sv.Allow_dic[clausenum]=[(nat1, attr1, nat2, attr2, natres)]  

        # solve distributivity
        if (distrib1 or distrib2):                                                        # result is a list due to distributivity
                vlu=result_list
                newnat=Lst[:]
        else:                                                                                   # result is a single value
                vlu=result_list[0] if result_list else None
                newnat=natres
        
        # attribute value to res (not directly to object)
        set_value(sv, O, res, vlu, sv.Current_time, newnat)       

    return dec_recurse(sv, res, None)

#===================================================== inc_recurse   
def inc_recurse(sv):
    """
    Increment sv.Eval_depth and check if Max_depth is exceeded (fatal error)
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        directly applied to Eval_depth 
    """
    sv.Eval_depth+=1                                                      # recursivity counter
    if sv.Eval_depth>Max_depth:                                      # error if too deep (circular)
        print("\n", Err_nb_recurse)                             
        raise ReferenceError

#===================================================== inc_recurse   
def dec_recurse(sv, res, change):
    """
    Decrement sv.Eval_depth prior to return
    called by updateval
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        res: an object, result of the evaluation of tree
        change: a Boolean indicating hidden changes (inside a list)
    """
    sv.Eval_depth-=1                                                      # recursivity counter
    return res, change

#===================================================== evaluate_pin
def evaluate_pin(sv, nom):  
    """
    Process pin input
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly applied
    """
    res=sv.Object[nom]                                                   # compare cached value of pin to Pinstate 
    st=(sv.Pinstate[nom]==Vrai)
    if st!=istrue(res, sv.Current_time):                               # update status according to Pinstate                             
        set_status(res, st, sv.Current_time) 
    return dec_recurse(sv, res, None)                           # end evaluation

# ==================================================== evaluate_simple
def evaluate_simple(sv, O):                                            
    """
    Evaluate simple leaf object (not expression)
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        O: an operator
    Returns
    --------
        res: an object, result of the evaluation
        change: a Boolean indicating hidden changes (inside a list)
    """
    res=get_node(sv, O)                                                 # directly get value and create object
    return dec_recurse(sv, res, None)                              # end evaluation

# ==================================================== evaluate_bracket
def evaluate_bracket(sv,A):                                           
    """
    Evaluate bracketed block - RECURSIVE
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        A: a triplets, representing the operand
    Returns
    --------
        res: an object, result of the evaluation of tree
        change: a Boolean indicating hidden changes (inside a list)
    """
    res, changes=evaluate(sv, A)                                    # evaluate expression inside block
    return dec_recurse(sv, res, None)                             # end evaluation

# ==================================================== evaluate_list    
def evaluate_list(sv, A, res):                                               # defined list
    """
    Evaluate a list
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        A: a triplets, representing the operand
        res: an object, result of the evaluation
    Returns
    --------
        res: an object, result of the evaluation
        change: a Boolean indicating hidden changes (inside a list)
    """
    li=[]
    if not A:
        res.value=li
        return dec_recurse(sv, res, None)
    
    # create a list of names from triplets
    for x in A:
        if x:
            op=x[0]                                                                # get operator/leaf
            if isnumber(op):
                li+=[float(op)]                                                  # a number (float)
            elif isduration(op):                       
                li+=[str(seconds(op))+Unit_sec]                        # a delay (seconds)
            else:
                li+=[tree_join(x)]                                              # just the name (reconstruct expression)

    res.value=li
    # detect deep change in list
    for x in li:
        if x in sv.Object and sv.Object[x].lastchange==sv.Current_time: 
            return dec_recurse(sv, res, True)                         # change is True
        
    return dec_recurse(sv, res, None)

# ==================================================== avoid_reuse
def avoid_reuse(sv, nodx):
    """
    prevent more than one change of a value in a time step (if parameter Fatal_use_before is True)
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nodX: object
    Returns
    --------
        all information is directly stored in sv.Object
    """
    if Fatal_use_before and sv.Current_time>0 :                   # avoid reusing a value after it is changed
        if nodx.reuse is not None and nodx.value!=nodx.reuse:
            if nodx.nature==Bln and (istrue(nodx, sv.Current_time)==Vrai)==logic(nodx.reuse[0], sv.Current_time):
                pass
            else:
                print(Warn_unstable, nodx.name, "at", sv.Current_time)   # Unstable condition:
                raise ReferenceError
        elif type(nodx.value)==list:
            nodx.reuse=list(nodx.value)
        else:
            nodx.reuse=nodx.value

# ==================================================== evaluate_list_element
def evaluate_list_element(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):         
    """
    evaluate list element (subscripted)
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: an object triplet or None
        nom: name for the tree
        O: an operator
        A, B: triplets, representing the operands
        nodA, nodB: objects, corresponding to A and B
        n1, n2: nature of nodA and nodB
        res: an object, result of the evaluation of tree
    Returns
    --------
        res: an object, result of the evaluation of tree
        change: a Boolean indicating hidden changes (inside a list)
    """
    nod=sv.Object[O]
    vlist=nod.value                                                        # get full list
    nat=nod.nature[:]

    if sv.Object[O].isdict:                                                # a "dict" is a list defined element by element
        res, changes=getdictv(sv, nom, O, nodA.name)     # extract value (not so simple)
        return dec_recurse(sv, res, None)                          # end evaluation
    
    elif n1==Nmbr:                                                       # list element addressed by position
        vlu=nodA.value
        if vlu==0:
            if sv.Current_time!=0: print(Warn_null_index, Crlf, vlist)
        elif vlist and vlu is not None:
            el=getelement(vlist, vlu)                                 # cyclic index
            if el is not None:
                res=get_node(sv, el)                                   # access named object
        return dec_recurse(sv, res, None)                        # end evaluation    
            
    elif n1==Lst:                                                          # list element addressed by list of indices
        res.value=getlistlist(sv, nom, nodA, vlist)             # extract value
        return dec_recurse(sv, res, None)                        # end evaluation

    else:
        print(Anom_deep_get)
        print(tree, nom, O, A, B)
        raise ReferenceError
    
# ==================================================== distributive_delay
def distributive_delay(sv, objname, tree, nom, O, A, B, nodA, nodB, n1, n2, res):
    """
    compute a list of delayed objects
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        objname: name of object, if tree is a formula for the value of this object
        tree: an object triplet or None
        nom: name for the tree
        O: an operator
        A, B: triplets, representing the operands
        nodA, nodB: objects, corresponding to A and B
        n1, n2: nature of nodA and nodB
        res: an object, result of the evaluation of tree
    Returns
    --------
        None if not applicable
        res: an object, result of the evaluation of tree
        change: a Boolean indicating hidden changes (inside a list)
        other information is directly stored in sv.Object
    """
    if O!=Plus: return None                                             # not applicable
    if n1==Lst and n2==Drtn:                                         # Plus: delayed list, make a list of references and link it
        li=[]
        mylist=deep_get(sv, A[0], None)                            # get explicit list (but do not extract event times)
        if not mylist:
            return res, None                                               # end evaluation  
        if objname is not None: nom=objname                # avoid changing linked name
        elif not nom in sv.Object:                                      # may happen if a single operation
            nod=cm.add_object(sv, nom)
            nod.nature=Lst[:]
            nod.value=[]
        if mylist:
            for x in mylist:                                                  # extract elements
                if x is not None:
                    if isnumber(x):
                        print(Err_conflict_nat)
                        print(x, O, B[0])
                        raise ReferenceError
                    if isduration(x):                                        # list of delays should be second
                        print(Err_switch_operands)
                        print("("+str( x)+",...)", O, B[0], " --> ", B[0], O, "("+str( x)+",...)")
                        raise ReferenceError
                    y=tree_join((Plus,(x, None, None), B))       # create delayed reference
                    if not y in sv.Object:               
                        nodY=cm.add_object(sv, y)
                        nodY.nature=Bln[:]
                        nodY.isdelayed=True
                        if not y in sv.Delayed_objects: sv.Delayed_objects.append(y)
                        if not y in sv.Active_list: sv.Active_list.append(y) # add to active list
                        st=evalue_status(sv, (Plus,(x, None, None), B))  # recursively calls evaluate
                        set_status(nodY, st, 0)                   
                        if not isduration(B[0]):                         # if changeable delay 
                            link_node(sv, B[0], y, (Plus,(x, None, None), B)) # delay to delayed event                           
                        link_node(sv, x, y, (Plus,(x, None, None), B)) # event to delayed event
                        link_node(sv, y, nom, tree)                   # delayed event to list                
                    li+=[y]                                                    # create value
            if not nom in sv.Active_list: sv.Active_list+=[nom] # add to active list
            res.value=li
            return res, True                                                # end evaluation
        
    elif n1==Bln and n2==Lst:                                       # Plus: delayed list, make a list of references and link it
##                print("xxxx preparing a list of delayed objects", nom, tree, n1, n2)
        li=[]
        mylist=deep_get(sv, B[0], None)                            # explicit list 
        if not mylist:
            return res, None                           # end evaluation
        if objname is not None: nom=objname                # avoid changing linked name
        elif not nom in sv.Object:                                     # may happen if a single operation
            nod=cm.add_object(sv, nom)
            nod.nature=Lst[:]
            nod.value=[]
        if mylist:
            for x in mylist:                                                  # extract elements
                if x is not None:                       
                    y=tree_join((Plus, A, (x, None, None)))       # create delayed reference
                    if not y in sv.Object:                 
                        nodY=cm.add_object(sv, y)
                        nodY.nature=Bln
                        nodY.isdelayed=True
                        if not y in sv.Delayed_objects: sv.Delayed_objects.append(y)
                        if not y in sv.Active_list: sv.Active_list.append(y) # add to active list
                        st=evalue_status(sv, (Plus, A, (x, None, None))) # recursively calls evaluate
                        set_status(nodY, st, 0)                   
                        if not isduration(x):                              # if changeable delay 
                            link_node(sv, x, y, (Plus, A, (x, None, None)))  # delay to delayed event 
                        link_node(sv, A[0], y, (Plus, A, (x, None, None))) # event to delayed event
                        link_node(sv, y, nom, tree)                   # delayed event to list                            
                    li+=[y]                                                    # create value
        if not nom in sv.Active_list: sv.Active_list+=[nom] # add to active list
        res.value=li                                                                                    
        return res, True                                                   # end evaluation 

    return None                                                           # not applicable

#===================================================== prepareval
def prepareval(sv, nod, nat, attr, nodistr):
    """
    extracts and checks value and nature for operation
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object
        nat: expected nature of the result
        attr is the name of the attribute to extract (typically value)
        nodistr: a Boolean, True prevents distributivity (because operator expects a list)
    Returns
    --------
        result_list: a list of values with only one element if no distributivity is required
        distrib: a Boolean, indicates that distributivity is required
    """
    if not nat or not attr:
        return [], False                                             # return an empty list

    # decide about distributivity    
    distrib=not nodistr                                  
    if nat==Lst: distrib=False                                 # expected value is already a list
    else:
        li=nod.value
        if type(li)!=list: distrib=False                         # actual value is not a list
        elif nat==Bln:
            if not li : distrib=False                              # empty list
            if li and type(li[0])==tuple: distrib=False  # a single event, not a list
            
    if not distrib: li=[nod.name]                             # make a list with single object           
    result_list=[]                                                    # always work with a list
    lastnat=None
    for vlu in li:                                                      # get and check all values in a list
        resx=get_node(sv, vlu)                                 # retrieve full node for each
        nt=resx.nature[:]
        if nt!=lastnat:                                              # verify list is homogeneous
            if lastnat is None: lastnat=nt
            elif sv.Current_time!=0:                            # only allowed at initialization
                warn(Warn_Heterogeneous+"\n"+nod.content(), sv.Do_tests)
                
        if len(set(nt)&set(nat))!=1:                            # if nature is ambiguous                 
                return [], False                                     # break out 
            
        vlu=resx.value                          
        if nat==Lst:                                                  # get full value of list through indirection
            vlu=deep_get(sv, vlu, None)                     # sometimes not deep enough. But avoid extracting event times                                  
        elif resx.nature==Bln and attr==Value:         # Bln has other attributes (e.g. Occur, Lastchange)
            if vlu: vlu=vlu[0]                                       # first in list of on/off doublets (assumes list is well ordered) !
        else: 
            vlu=getattr(resx, attr)                               # general case: get attribute                                                    

        if nat==Drtn and isduration(vlu):                 # convert delays to numbers (for arithmetics)
            vlu=seconds(vlu)
            
        result_list+=[vlu]                                         # add result to list
    return result_list, distrib

#===================================================== valid_operands
def valid_operands(sv, O, li1, li2, nodB, nat1, nat2, natres):
    """
    verify if operands are not empty or None or are compatible with operator
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        O: an operator
        li1, li2: lists of values for the operands
        nodB: a node, the second operand
        nat1, nat2: nature of the operands
        natres: nature of the result
    Returns
    --------
        a Boolean, True if valid arguments
    """
    # is second term required    
    if nat2 and not li2: return False

    # no empty first term
    elif nat1 and not li1: return False

    # do not change delay in a delayed event until event itself changes 
    elif O==Plus and natres==Bln and coincide(nodB.lastchange, sv.Current_time): return False

    return True

#===================================================== make_distribute_list
def make_distribute_list(li1, li2, distrib1, distrib2):
    """
    compute a list of pairs of operand values
    called by evaluate
    Parameters
    ------------
        li1, li2: lists of operand values to combine
        distrib1, distrib2: Booleans, indicate that left or right distributivity is required
    Returns
    --------
        ziplist: list of pairs of operand values to combine
    """
    if li2:
        ziplist=list(zip(li1, li2))                                                   # create list of pairs of terms
    else:
        ziplist=[(x, None) for x in li1]                                        # pair all first terms with None
            
    if distrib1 and distrib2:                                                     # double distribute
        diff=len(li1)-len(li2)                                                      # match number of elements
        if diff>0: ziplist=ziplist+[(x, None) for x in li1[-diff:]]
        elif diff<0: ziplist=ziplist+[(None, x) for x in li2[diff:]]
            
    elif distrib1:                                                                      # left distribute
        elt=li2[0] if li2 else None                                              # develop li2
        ziplist=[(x, elt) for x in li1]
                
    elif distrib2:                                                                     # right distribute
        elt=li1[0] if li1 else None                                             # develop li1
        ziplist=[(elt, x) for x in li2]
        
    return ziplist
   
#===================================================== adjust_result
def adjust_result(sv, O, vlu, nat1, nat2, natres, distrib1, distrib2):
    """
    correct result when needed, in particular for durations, lists and glitches
    called by evaluate
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        O: an operator
        vlu: a value, result of the evaluation
        nat1, nat2: nature of the operands
        natres: nature of the result
        distrib1, distrib2: Booleans, indicate application of left or right distributivity    
    Returns
    --------
        vlu: a value, corrected result of the evaluation    
    """
    # result is a duration
    if natres==Drtn and vlu is not None:                            
        vlu=str(vlu)+Unit_sec

    # add a duration as a list element
    elif O==Add and vlu:                                                   
            if nat2==Drtn:
                vlu[-1]=str(vlu[-1])+Unit_sec                            # make last element a duration
            elif nat1==Drtn:
                vlu[0]=str(vlu[0])+Unit_sec                               # make first element a duration

    # result is a list of true/false values
    elif vlu is True and (distrib1 or distrib2):  vlu=Vrai                                                     
    elif vlu is False and (distrib1 or distrib2): vlu=Faux

    # result is a glitch            
    elif O in Glitch_list and vlu is not None:                       # build a glitch (begin/end/change) from a time  
            if coincide(vlu, sv.Current_time): vlu=sv.Current_time     # adjust to current time
            vlu=[(vlu, vlu+Glitch_time)] if O!=Change else [(vlu, vlu+Change_time)] # glitch duration

    return vlu

#===================================================== getelement
def getelement(alist, ind):                                                                                       
    """
    extract element from a list. Index range is -len(vl) to infinity (cyclic)
    backward access allowed from last element (-1) to first (-len(vl)), but not before
    first element is 1, last is -1. Index 0 does not exist and gives a warning.
    called by evaluate
    Parameters
    ------------
        alist: a list of object names
        ind: an integer used as index
    Returns
    --------
        element name extracted from list    
    """
    if ind<-len(alist):
        print("*** Warning: cannot reach beyond first element ***")
        return None                                                               # no element before the first
    if ind>0:
        return alist[(int(ind)-1) % len(alist)]                              # positive indices cycle
    if ind<0:
        return alist[int(len(alist)+ind)]                                      # negativeindices do not cycle

# ==================================================== getlistlist
def getlistlist(sv, nom, nodA, vlist):                                                    
    """
    extracts a list of values from a list using a list of indices
    used for distributivity in evaluate
    """
    listeres=[]
    if vlist and nodA.value is not None:
        for vlu in nodA.value:                                                    # get value for each list element
            if vlu==0 and sv.Current_time!=0: print(Warn_null_index, Crlf, vlist)
            if vlu is not None:
                obtained=getelement(vlist, vlu)                            # cyclic index
            else: obtained=None                                                               
            listeres+=[obtained]
    return listeres    
    
# ==================================================== getdictv
def getdictv(sv, nom, O, keyname):                                                    
    """
    extracts a value from a dictionary, if any, returns a node and a Boolean for changes                      
    """
    changes=False
    res=get_node(sv, nom)
    if res.isdefined: return res, changes                          # element is defined: use cached value 

    mykey=sv.Object[keyname].value                            # access indirect key from name if needed 
    my=makekey(mykey)                                               # make sure it is a string and remove decimal point if integer
    myname=O+Obr+my+Cbr                                      # construct object name dict(key)  
        
    vl=sv.Object[O].value                                               # obtain list of dictionary elements vl  
    if type(vl)!=list or not vl:                                          # no dict elements assigned yet      
        return res, None                                              
    
    if type(mykey)!=list:                                                 # if key is a single element  
        for ky in vl:                                                           # look for match in dictionary 
            if ky ==myname :                                         
                res=get_node(sv, ky)
                break                                                           # stop after first match
        return res, changes
    
    listeres=[]                                                                # if key is a list of dict elements
    mykey=deep_get(sv, mykey)                                  # get deep value
    mykey=[str(x) for x in mykey]
    one=O+Obr+",".join(mykey)+Cbr                          # try building a single key from list
    if one in vl:
        res=sv.Object[one]
        return res, changes
    
    for myk in mykey:                                                   # process each key
        my=makekey(myk)                                             # make sure it is a string and remove decimal point if integer                                        
        myname=O+Obr+my+Cbr                                 # construct object name dict(key)                        
        listeres+=[myname]                                           # return a list of names                                              
    res.value=listeres                                                    # distribute dict on keys 
    return res, changes

#===================================================== link_node
def link_node(sv, cause, effect, tree):                               
    """
    creates the appropriate links between two objects
    cause and effect are names, tree is the effect tree
    """
    Verbose="lnk" in Debog
    if Verbose:  print("linking", cause, "-->", effect)
    if not effect in sv.Object:
        print(Err_unknown_object, effect)                                # *** Error: unknown object ***
        raise ReferenceError
    if not cause in sv.Object:
        print(Err_unknown_object, cause)                                # *** Error: unknown object ***
        raise ReferenceError
    nodeffect=sv.Object[effect]                                                   
    nodcause=sv.Object[cause]
    if not effect in nodcause.effects: nodcause.effects+=[effect]  # link cause to effect   
    if not cause in nodeffect.causes: nodeffect.causes+=[cause]  # link effect to cause
    for c in [Starttree, (Change, (cause, None, None), None)]:
        if sv.Current_time==0:                                                            # if execution has not started
            if not (c,tree) in nodeffect.clauses: nodeffect.clauses+=[(c,tree)]  
        else:                                                                                        # execution has started: clauses change format
            clau=(c, effect, tree)                                                           # make clause   
            if not clau in sv.Save_value.values():
                condnum=len(sv.Condition)                                           # attribute a new number to condition 
                vnum=len(sv.Save_value)                                                # attribute a new number to value 
                if c[0]!=Start: iv.one_condition(sv, effect, c, condnum)  # reprocess condition
                sv.Save_value[vnum]=clau                                               # store old value 
                nodeffect.clauses.append((condnum, vnum))                 # make clause a number
    if Verbose:  print("effects of", cause, ":", nodcause.effects)
    if Verbose:  print("causes of", effect, ":", nodeffect.causes)

#===================================================== distribute_glitch  
def distribute_glitch(sv, tree, nom):                                          
    """
    for lists: create and link glitch references (begin/end of each element)
    returns a list of glitch names
    """
    Verbose="dgl" in Debog
    O,A,B=tree                                                                                     # O is begin/end 
    li=[]
    mylist=deep_get(sv, A[0], None)                                                   # extract explicit list
    if mylist is not None:
        for x in mylist:                                                                            # browse elements
            if x is not None:                       
                y=O+Obr+x+Cbr                                                               # create glitch reference (begin/end of each element)
                if not y in sv.Object:                 
                    if Verbose: print("xxxx create and link", y, "to", nom)
                    nodY=cm.add_object(sv, y)                                           # create glitch node
                    nodY.nature=Bln[:]                                                       # set nature (it is a new object)
                    st=evalue_status(sv, (O,(x, None, None), None))               # recursively calls evaluate
                    set_status(nodY, st, 0)                   
                    nodX=sv.Object[x]                                                        # the element node
                    link_node(sv, x, y, (O, (x, None, None), None))             # link event to glitch 
                    link_node(sv, y, nom, tree)                                            # link glitch to list
                li+=[y]                                                                               # add to value list
        if not nom in sv.Active_list: sv.Active_list+=[nom]                    # add to active list
    return li

#===================================================== set_value
def set_value(sv, O, res, vlu, time, natres):
    """
    stores value and relevant attributes in node res (not yet into nod)    
    Always store result in value
    For Bln when vlu is Vrai / Faux, compute on and off times
    for delayed objects, set res then fuse delays with nod
    For Change, update change times immediately
    """
##    Verbose="svl" in Debog
##    if Verbose: print("xxxx rt eval call set_value", sv.Current_time, "s", nom, (O, res.content(), natres, vlu))
    if vlu is None: return False
    ty= type(vlu)
    ok=True

    # check nature of result
    if natres==Drtn and not isduration(vlu): ok=False                        # a duration 
    elif natres==Nmbr and not ty in [int, float]: ok=False                  # a number 
    elif natres==Stt and ty!=str: ok=False                                          # a state 
    elif natres==Lst and ty!=list: ok=False                                         # a list
    elif natres==Bln:                                                                           # an event
        if not (ty==list or vlu in [True, False]):                                                    
            print(Anom_setv_logic, res.content(), [vlu], "\n")  # "*** Anomaly in rt.setv: not a Bln logic value ***   "
            ok=False
        else:
            if vlu is True: vlu=[(time, None)]                                           # store on time
            if vlu is False: vlu=[(None, time)]                                          # store off time (on time is unknown)  
            if O == Change and time>0:
                if not (res.isdelayed):                                                       # delayed objects must fuse delays, not change them                                     
                    res.lastchange=time                                                    # update change times
    if ok:
        res.value=vlu if type(vlu)!=list else vlu[:]                                   # now store
    else:                                                                                            # nature is not identified
        print(Anom_setv_nat, res.content(), [vlu], "\n")  # "*** Anomaly in rt.setv: unknown nature ***   "
        raise ReferenceError

#===================================================== bufstore  
def bufstore(sv, fname, li, now=False):
    """
    Prepares text for file storage in fname
    store lists one line per element (else use function text)
    on screen, separates elements with a space
    delay storage at start until now is True
    """
    if type(li)!=list:
        print(Anom_bufstore, li, "***")                           # *** Anomaly in bufstore: not a list:
        raise ReferenceError
    nam=no_quotes(fname)                                         # filename used as key in sv.Buff
    endcar=" " if nam==Screen else Crlf                         
    if li==[Empty]:                                                       # special case:  
        sv.Buff[nam]=[Empty+"\n"]                              # this is a code to erase the file (not a singleton)
    elif sv.Current_time==0 and not now:                   # delay file output until initialization is complete
        sv.Buff[nam]=li
    else:
        sv.Buff[nam]=[]
        if len(li)==1 and li[0] in sv.Object and not (li[0].startswith(Obr) and li[0].endswith(Cbr)):   
            l=sv.Object[li[0]].value                                  # extract list from name, except if bracketed  
            if type(l)==list and not (l and type(l[0])==tuple): li=l   # avoid Booleans
        for i, x in enumerate(li):                                    # browse list of objects to store
            if type(x)==list:                                             # element is a list
                y=x
            elif x in sv.Object:                                         # element is an object name
                elt=sv.Object[x] 
                y=elt.value                                                # extract value
                if elt.nature==Bln:
                    y=Vrai if istrue(elt, sv.Current_time) else Faux  # convert Boolean to true/false
            else: y=str(x)                                                 # text
            if type(y)==list:                                             # again element is a list
                y=str(y).replace("'", "")                              # remove all quotes
                y=y.replace(Quote+Quote, Quote)           # insert double quote where needed
                y=y.replace("[", Obr)                                 # change square brackets to brackets
                y=y.replace("]", Cbr)
                y=y.replace(Comma+Space, Comma)      # no space after comma
                y=y[1:-1]                                                   # remove surrounding brackets
            sv.Buff[nam]+=[(y)]                                      # add text as a singleton 
            if i<len(li): sv.Buff[nam]+=[endcar]               # add separator          
    
#===================================================== filestore
def filestore(sv):
    """
    appends content of sv.Buff to a file, rewrites file if code 'empty'
    also prints to screen if fname='screen'
    calls bufstore at start after initialization is complete
    """
    for nam in sv.Buff:                                                        # allow indirect ref 
        if sv.Current_time==0:                                              # delayed storage
            li=sv.Buff[nam]
            sv.Buff[nam]=[]
            bufstore(sv, nam, li, now=True)                           # process now
        fname=nam
        if fname in sv.Object:
            fname=get_node(sv, fname).value                        # extract name from ref
        fname=no_quotes(fname)                                         # remove quotes
        if sv.Buff[nam]:                                                         # buffer is not empty
            if fname==Screen:                                              
                io.screenprint(sv.Buff[nam])                             # print to screen
                sv.Buff[nam]=[]                                                # clear buffer
            else:
                fname=addparentdir(fname)                           # allow access to other directories 
                try:                                                                   # may be unable to open or write 
                    if Empty+"\n" in sv.Buff[nam]:
                        fic=io.opentextfile(fname, RAZ=True)     # erase the file (see whand_io.py)
                    else:
                        fic=io.opentextfile(fname)                       # append to the file (see whand_io.py)
                        for x in sv.Buff[nam]:
                            io.writetextfile(fic,x)                             # write to the file (see whand_io.py) 
                    io.closetextfile(fic)                                       # close the file (see whand_io.py) 
                    sv.Buff[nam]=[]                                           # clear buffer
                except IOError:
                    print("\n", Err_no_open, fname)
                    raise ReferenceError
        
#===================================================== updatepanel
def updatepanel(sv, nom):
    """
    update one value on graphic panel if appropriate
    object must be visible and not pin which has been named
    """
    if nom in sv.Visible and not nom in sv.Namedpinlist:
        sv.interface.update(sv, nom)                                                       
   
#===================================================== fuse_delays
def fuse_delays(sv, nod, res=None):                                    
    """
    updates delay list of event nod using res
    reduces delay list to a minimum, in particular when res is None
    preserves onsets when updating offsets
    """
    if not Bln[0] in nod.nature:                                                                    # nod must be an event
        print("*** Anomaly in rt.fuse_delays: not a Bln", nod.content(), "\n")
        raise ReferenceError
    nod.nature=Bln
    if res and res.value is not None:                             
        dly=nod.value+res.value 
    else:
        dly=nod.value        # combine both lists
#    dly=nod.value+res.value if res is not None else nod.value        # combine both lists
##    times=list(set([x[0] for x in dly if x and x[0] is not None]))         # ontimes without duplicates (also prior to current time)                                
##    times+=list(set([-x[1] for x in dly if x and x[1] is not None and x[1]>=sv.Current_time]))  # offtimes with negative sign  
    times=no_duplicate([x[0] for x in dly if x and x[0] is not None])         # ontimes without duplicates (also prior to current time)                                
    times+=no_duplicate([-x[1] for x in dly if x and x[1] is not None and x[1]>=sv.Current_time])  # offtimes with negative sign  
    if not times: return                                                                     # nothing to fuse
    times.sort(key=abs)                                                                   # sort on and off in proper time order
                                                            # because sort is stable, an on will still precede a simultaneous off
    dly=[]                                                                                        # build ordered pairs
    laston=None                                                                             # previous on time
    stored=False                                                                             # whether on time has been processed
    for x in times: 
        if x<0:                                                                                    # off time
            if stored:                                                                            # on time has been processed
                stored=False
                if -x==laston: x=-laston-Glitch_time/2                          # no event with zero duration
                dly[-1]=(laston, -x)                                                        # insert known off time and replace
            else:
                dly+=[(laston, -x)]                                                         # maybe off without on
            laston=None                                                                     # forget on time when event ends
        else:                                                                                       # on time
            laston=x                                                                            # remember on time for next off
            if x>=sv.Current_time:                                                       # only keep future delays
                dly+=[(x, None)]                                                           # off time unknown
                stored=True                                                                  # no need to duplicate on time 
    nod.value=dly

#===================================================== cleanup_delays
def cleanup_delays(sv, nod):                                         
    """
    reduces delay list from an event by removing past occurrences
    where both on and off times are before current time
    n.b. (None, None) will be replaced with (None, 0)
    """
    dly=[x for x in nod.value if ((x[0] is not None and x[0]>=sv.Current_time) or (x[1] is not None and x[1]>=sv.Current_time)) ]
    if not dly: dly=[(None, 0)]                                                          # at least one element (=false)
    nod.value=dly

#===================================================== nextevents
def nextevents(sv):
    """
    returns a list of all future delayed events according to their time of occurrence
    first term of each pair is time, positive for on events, negative for off events
    second term of each pair is event name
    events at current time are ignored
    the earliest events are last in the reverse sorted list (ready to be popped)
    """
    li=[]
    for nam in sv.Delayed_objects:
        nod=sv.Object[nam]
        for u,v in nod.value:
            if u is not None and u>sv.Current_time:   
                li+=[(u, nam)]                                           # store on events with positive sign
            if v is not None and v>sv.Current_time:   
                li+=[(-v, nam)]                                          # store off events with negative sign
    li=no_duplicate(li)                                                        # remove duplicates while preserving order
##    li=list(set(li))                                                             # remove duplicates        
    li.sort(key=lambda x: abs(x[0]), reverse=True)            # sort according to decreasing time
    return li

#===================================================== prepare_old
def prepare_old(sv):  
    """
    make a copy of every node required for function old and update
    this is done before advancing time, which is why updating is tricky
    reinitialize change flag for all events
    """
    for nam in sv.Old_list:                                                     
        copy=Old+Obr+nam+Cbr                                                # name of the copy 
        cop=sv.Object[copy]                                                           # object copy
        nod=sv.Object[nam]                                                            # original object    
        nd.copy_node2(sv, nam, cop)                                              # duplicate basic properties 
        if nod.lastchange==sv.Current_time:                                   # update change time of copy
            cop.lastchange=sv.Current_time
            cop.haschanged=True
        if nod.nature==Bln:                                                             # update event status of copy
            iv.update_condition(sv, copy, st=istrue(cop, sv.Current_time))                       
        else:
            iv.update_condition(sv, copy, ch=cop.haschanged)                    # update change of copy
            
##        # for lists, replace each element by its old copy, recursively             
##        if type(cop.value)==list: deep_old(sv, cop)                              
    for nod in sv.Object.values():
        nod.reuse=None                                                                  # reset reuse
##        nod.isunstable=False                                                            
        
###===================================================== deep_old
##def deep_old(sv, cop):                                                                   
##    """
##    make a copy of every element in a list for function old (recursive)
##    so, old([element1, element2...]) will become [old(element1), old(element2)...]
##    not done because too slow
##    """
##    newlist=[]
##    for eltnam in cop.value:
##        ok=True
##        if type(eltnam)!=str:
##            ok=False                                                                   # do not reprocess numbers
##        elif isduration(eltnam):
##            ok=False                                                                   # do not reprocess durations
##        elif applied(eltnam,Old):
##            ok=False                                                                   # do not reprocess Old
##        elif not eltnam in sv.Object:
##            ok=False                                                                   # ignore new objects
##        elif len(sv.Object[eltnam].clauses)<=1:
##            ok=False                                                                   # ignore constants
##        if not ok:
##            newlist+=[eltnam]                                                     # element will be unchanged
##        else:
##            elt=sv.Object[eltnam]
##            copy2=Old+Obr+eltnam+Cbr                                # Old of this element
##            newlist+=[copy2]
##            insert_node(sv, copy2)                                         # create copy if needed 
##            cop2=sv.Object[copy2]
##            nd.copy_node2(elt, cop2)                                           # duplicate properties
##            if elt.lastchange==sv.Current_time:
##                cop2.lastchange=sv.Current_time
##                cop2.haschanged=True
##            if type(cop2.value)==list: deep_old(sv, cop2)         # recurse
##    cop.value=newlist                       

#===================================================== init_outputs
def init_outputs(sv):
    """
    set outputs at start
    """
    for nom in sv.Object_list:
        if applied(nom, Output) or applied(nom, Command) or applied(nom, Write):
            if sv.Object[nom].nature==Bln:
                if istrue(sv.Object[nom], 0):                                 # only change if true at start (default is false)
                    link_output(sv, nom)
            else:
                    link_output(sv, nom)                                       # other than Boolean

#===================================================== clear_outputs
def clear_outputs(sv):
    """
    clears outputs at end
    """
    for nom in sv.Object_list:
        if applied(nom, Output):
            sv.Object[nom].value=[(None, sv.Current_time)]                 # set all to false
            link_output(sv, nom)

#===================================================== pinscan
def pinscan(sv):
    """
    Scan physical inputs. Calls io.readpins 
    directly sets inputs as delayed to improve accuracy 
    """
    ch=io.readpins(sv)                                                                # needed even under interrupts
    if ch:
        for code,st, tim in ch:                                                        # triplet: code, state, time
##            if tim<=sv.Current_time:
##                tim=sv.Current_time+Glitch_time                        
            tim=sv.Current_time+Glitch_time                                  # do not use exact time !                   
            if code[0]=="P":                                                            # compatibility with keys 
                nom=Pin+Obr+code[1:]+Cbr                                   # a Pin  e.g.  pin(3)
                newstatus=(tim, None) if st else (None, tim)
            else:                                                                               # not a pin  
                car=code[1:]
                nom=Key+Obr+car+Cbr                                          # a Key  e.g.  key(ç)    
                if not nom in sv.Object: nom=Key+Obr+Quote+car+Quote+Cbr  # key("ç")
                newstatus=(tim, tim+Glitch_time)                             # briefly on
            if nom in sv.Object:                                 
                nod=sv.Object[nom]
                nod.value+=[newstatus]                                           # set delayed object 
##                print("pinscan1", newstatus, nod.content())
                fuse_delays(sv, nod)                       # beware of destroying input here if time advances
                nod.haschanged=True                                              # even if state is back to the same
                nod.lastchange=sv.Current_time                                
##                print("pinscan2", newstatus, nod.content())

#===================================================== link_output
def link_output(sv, nom):
    """
    Link changed nodes to control panel and physical outputs. Calls io.setpin, io.outmsg, io.outcommand
    Bit output aborts if istrue is given a non Bln value
    Write always converts to string
    Command aborts if given a non number input
    """
    nb=applied(nom, Output)                                                   # output a Boolean
    if nom in sv.Object and isnumber(nb):                                # verify it exists 
        time=io.clock()-sv.t0                                                       # compute time 
        vl=sv.Object[nom].value                                                 # value to output
        st=True if istrue(sv.Object[nom], sv.Current_time) else False   # Boolean
        io.setpin(sv, nb, st, time)                                                 # apply        

    nb=applied(nom, Command)                                              # output a number
    if nom in sv.Object and isnumber(nb):                                # verify it exists 
        time=io.clock()-sv.t0                                                       # compute time 
        vl=sv.Object[nom].value                                                 # value to output
        if not type(vl) in [float, int, type(None)]:
            print(Warn_invalid_nb)
            print(vl)
            raise ReferenceError
        io.outcommand(sv, nb, vl)

    nb=applied(nom, Write)                                                     # output a text
    if nom in sv.Object and isnumber(nb):                                # verify it exists 
        time=io.clock()-sv.t0                                                       # compute time 
        vl=sv.Object[nom].value                                                 # text to output
        if type(vl)!=str: vl=str(vl)                                                 # convert to string
        io.outmsg(sv, nb, no_quotes(vl), time)

    li=applied(nom, Display)                                                    # arguments for display
    if li:
        vl=deep_get(sv, li, None) if li in sv.Object else splitlist(li)
        if len(vl)!=3 or not isnumber(vl[1]) or not isnumber(vl[2]):
            print(Err_syntax, vl, Crlf)
            raise ReferenceError
        vl[0]=no_quotes(vl[0])
        if istrue(sv.Object[nom], sv.Current_time):
            io.display(sv, *vl, closing=False)     
        else:
            io.display(sv, *vl, closing=True)

#===================================================== reorder
def reorder(li):
    """
    modify the order of particular lists for debugging
    """
    changes=[( ['(A,)', 'end(A)', 'end(li)', 'li'] , ['(A,)', 'li', 'end(li)', 'end(A)'] ) \
      , ( ['t', 'start_to_end(li)', 'end(li)'] , ['start_to_end(li)', 't', 'end(li)'] ) \
      , ( ['t=.2s'] , ['start_to_end(li)', 't=.2s', 't'] ) \
             ]
    for old, new in changes:
        if li==old: li=new
    return li
        
#===================================================== TESTS
if __name__=="__main__":
    pass






