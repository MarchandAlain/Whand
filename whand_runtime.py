# -*- coding: ISO-8859-1 -*-
# standard modules
from math import *                                                                   # think about changing it to 'import math' (find where used)
from random import random, shuffle                                       # a few functions

# whand modules
from whand_parameters import *                                             # options, constants
from whand_operators import *                                                # from... import because module only contains constants
from whand_tools import *                                                        # useful procedures only
import whand_io as io                                                               #  I/O module for drivers
import whand_nodes as nd                                                       # object class
import whand_compile as cm

# ==================================================== getvalue
def getvalue(sv, expr):                       
    """
    returns a node with current value of nom, creates node once
    """
    if expr is None or expr=="":
        return sv.Object[Faux]                               

    nom=str(expr)                 
    
    if nom in sv.Object:                                                      # use existing node 
        return sv.Object[nom]

    if nom==Always:                                                          # create 'Always' event
        res=cm.add_object(sv, nom)   
        res.value=sv.Object[Vrai].value
        res.nature=Bln[:]
        return res       

    if isnumber(nom):                                                         # create a number                                 
        res=cm.add_object(sv, nom)   
        res.value=float(nom)
        res.nature=Nmbr[:]
        return res
    
    elif isduration(nom):                                                    # create a duration                                                                           
        res=cm.add_object(sv, nom)   
        res.value=str(seconds(nom))+Unit_sec
        res.nature=Drtn[:]
        return res

    if detectlist(nobrackets(nom)):                                     # create and link list                    
        li=splitlist(nobrackets(nom))
        res=cm.insert_node(sv, nom, causelist=li, setto=None, always_update=False)
        res.value=li
        res.nature=Lst[:]
        
    else:                                                                             # a state or the copy of a node
        res=cm.add_object(sv, nom)
        if not nom.startswith(Special):                                # not a copy of a node
            res.nature=Stt[:]
            res.value=nom

    return res

# ==================================================== evalstatus
def evalstatus(sv, tree):                       
    """
    computes the status of a tree expression (not cached)
    returns True or False (default)
    """
    st=False                                            
    vl, ch=evaluate(sv, tree)
    ev=vl.value                                                                  # list of on/off doublets, or None
    if ev: st=logic(ev[0], sv.Current_time)                          # first delayed event
    
#===================================================== evaluate
def evaluate(sv, tree, objname=None, clausenum=0):                  
    """
    compute current value of a tree expression (recursive)
    applies distributivity
    clausenum is a key to parameters for prepareval to accelerate processing
    """
    Verbose='evl' in Debog and ('stv' in Debog or sv.Current_time>0) 
    if not tree: return sv.Object[Faux], None    
    
    sv.Eval_depth+=1                                                       # recursivity counter
    if sv.Eval_depth>Max_depth:                                      # error if too deep (circular)
        print("\n", Err_nb_recurse)                             
        raise ReferenceError

    nom=treejoin(tree)                                                    # compute name of tree expression                                            

    # process pin input    
    if nom in sv.Pinlist:                                                     # is it a pin input?
        res=sv.Object[nom]                                               # compare cached value of pin to Pinstate 
        st=(sv.Pinstate[nom]==Vrai)
        if st!=istrue(res, sv.Current_time):                          # update status according to Pinstate                             
            setstatus(res, st, sv.Current_time) 
        sv.Eval_depth-=1
        return res, None                                                    # end evaluation
            
    O,A,B=tree                                                                 # decompose expression and check operator   
    if O==Special:                                                            # subscripting ( e.g. cumul(L)(0) )
        O=treejoin(A)                                                         # make operator from first term 
        A=B                                                                        # make subscript from second term
        B=None
        
    if not A and not B:                                                      # simple leaf object (not expression)
        res=getvalue(sv, O)                                                # directly get value and create object
        sv.Eval_depth-=1
        return res, None                                                     # end evaluation

    if O==Obr:                                                                  # bracketed block
        res, changes=evaluate(sv, A)                                  # evaluate expression inside block
        sv.Eval_depth-=1
        return res, None                                                     # end evaluation    

    # prepare a temporary node for result
    res=cm.add_object(sv, Special+Special+nom)          # initialize res                  
    if nom in sv.Object:
        nd.copynode2(sv.Object[nom], res)                       # copy current attributes to the new node                          
    
    if O==Idem:                                                               # Idem is processed elsewhere (prepare_idem)
        sv.Eval_depth-=1
        return res, None                                                     # end evaluation   

    if O==Comma:                                                           # defined list
        liA=buildlist(sv, A)                                                  # construct list of names from triplets
        res.value=liA                                                          # (consider doing this at an earlier stage)
##        print("evaluate list",liA)
        for x in liA:
            if x in sv.Object and sv.Object[x].lastchange==sv.Current_time: # deep change in list
##                print("CHANGED", liA, tree)
                sv.Eval_depth-=1
                return res, True                                                    # end evaluation
        sv.Eval_depth-=1
        return res, None                                                    # end evaluation
       
    #  other expressions: compute terms
    nodA, changes=evaluate(sv, A)                           
    nodB, changes=evaluate(sv, B)
    if Fatal_use_before and sv.Current_time>0 :                   # avoid reusing a value after it is changed
        for nodx in [nodA, nodB]:
            if nodx.reuse is not None and nodx.value!=nodx.reuse:
                if nodx.nature==Bln and (istrue(nodx, sv.Current_time)==Vrai)==logic(nodx.reuse[0], sv.Current_time):
                    pass
                else:
                    nodx.isunstable=True
                    res.isunstable=True
            elif type(nodx.value)==list:
                nodx.reuse=list(nodx.value)
            else:
                nodx.reuse=nodx.value

    n1=nodA.nature[:]
    n2=nodB.nature[:]
    if Verbose:
        print("xxxx evaluate", sv.Current_time, "s :", nom, tree)
        if nom in sv.Object: print("xxxx    ->", sv.Object[nom].content())
        
    sv.Current_clause=nom, None, None                             # debugging clue            

    if O in sv.Object:                                                             # list element (subscripted)       
        nod=sv.Object[O]
        vlist=nod.value                                                           # get full list
        nat=nod.nature[:]

        if sv.Object[O].isdict:                                                  # a "dict" is a list defined element by element
            res, changes=getdictv(sv, nom, O, nodA.name)    # extract value (not so simple)
            sv.Eval_depth-=1                                                  
            return res, None                                                     # end evaluation
        
        elif n1==Nmbr:                                                          # list element addressed by position
            vlu=nodA.value
            if vlist and vlu is not None:
                el=getelement(vlist, vlu)                                    # cyclic index
                if el is not None:
                    res=getvalue(sv, el)                                       # access named object
            sv.Eval_depth-=1
            return res, None                                                    # end evaluation    
                
        elif n1==Lst:                                                              # list element addressed by list of indices
            res.value=getlistlist(sv, nom, nodA, vlist)              # extract value
            sv.Eval_depth-=1                                                  
            return res, None                                                   # end evaluation

    if not (O in Allowed):                                                  # not an operator (e.g. pin)
        sv.Eval_depth-=1
        return res, None

    if nodA.value==[] and not (O in [Add, Count, Find, Is, Isnot, Match, Pick, Sort, Within, Next]):
        if res.value!=[]:                                                       # empty yields empty
##            print(O)
            res.value=[]
            changes=True
        return res, changes

    # special functions (non distributive)
    elif O in [Begin, End]:                                                    # distribute begin/end if needed       
        nodA=sv.Object[A[0]]                                               # object which is argument to begin/end
        if nodA.nature==Lst:                                                # only for lists: distribute references, not values
            res.value=distribute_glitch(sv, tree, nom)            # call rather complex routine
            sv.Eval_depth-=1
            return res, True                                                    # indicate change to update list 
                               
    elif O==Pointer:                                                          # pointer
        nodA=sv.Object[A[0]]
        ptr=nodA.pointer
        res.value=ptr                                                          # cached value
        sv.Eval_depth-=1
        return res, None    
    
    elif O==Next:                                                             # next
        nodA=sv.Object[A[0]]
        vl=nodA.value
        if type(vl)==list and vl:                                           # only if list is initialized and not empty               
            if  nodA.lastchange!=sv.Current_time:               # only once per time step
                ptr=nodA.pointer
                ptr=1+(int(ptr) % len(vl))                               # cyclic index 
                el=vl[ptr-1]
                if type(el)==list:
                    res.value=el
                    res.nature=Lst
                else:
                    cop=getvalue(sv, el)                                  # using getvalue directly may not work
                    nd.copynode2(cop, res)
                nodA.pointer=ptr                                          # this is where pointer is updated                                  
                nodA.lastchange=sv.Current_time                # mark as changed in this time step
        sv.Eval_depth-=1
        return res, None    

    elif O==Plus:
        if n1==Lst and n2==Drtn:                                        # Plus: delayed list, make a list of references and link it
##                print("xxxx preparing a list of delayed objects", nom, tree, n1, n2)
                li=[]
                mylist=deep_get(sv, A[0], None)                      # get explicit list (but do not extract event times)
                if not mylist:
                    sv.Eval_depth-=1
                    return res, None   
                if objname is not None: nom=objname           # avoid changing linked name
                elif not nom in sv.Object:                                    # may happen if a single operation
                    nod=cm.add_object(sv, nom)
                    nod.nature=Lst[:]
                    nod.value=[]
                if mylist:
                    for x in mylist:                                                    # extract elements
                        if x is not None:
                            if isnumber(x):
                                print(Err_conflict_nat)
                                print(x, O, B[0])
                                raise ReferenceError
                            if isduration(x):                                          # list of delays should be second
                                print(Err_switch_operands)
                                print("("+str( x)+",...)", O, B[0], " --> ", B[0], O, "("+str( x)+",...)")
                                raise ReferenceError
                            y=treejoin((Plus,(x, None, None), B))    # create delayed reference
                            if not y in sv.Object:               
                                nodY=cm.add_object(sv, y)
                                nodY.nature=Bln[:]
                                nodY.isdelayed=True
                                if not y in sv.Delayed_objects: sv.Delayed_objects.append(y)
                                if not y in sv.Active_list: sv.Active_list.append(y) # add to active list
                                st=evalstatus(sv, (Plus,(x, None, None), B))  # recursively calls evaluate
                                setstatus(nodY, st, 0)                   
                                if not isduration(B[0]):                        # if changeable delay 
                                    link_node(sv, B[0], y, (Plus,(x, None, None), B)) # delay to delayed event                           
                                link_node(sv, x, y, (Plus,(x, None, None), B)) # event to delayed event
                                link_node(sv, y, nom, tree)               # delayed event to list                
                            li+=[y]                                                  # create value
                if not nom in sv.Active_list: sv.Active_list+=[nom] # add to active list
                res.value=li
                sv.Eval_depth-=1
                return res, True                                                # indicate change to update list
        
        elif n1==Bln and n2==Lst:                                       # Plus: delayed list, make a list of references and link it
##                print("xxxx preparing a list of delayed objects", nom, tree, n1, n2)
            li=[]
            mylist=deep_get(sv, B[0], None)                         # explicit list 
            if not mylist:
                sv.Eval_depth-=1
                return res, None
            if objname is not None: nom=objname             # avoid changing linked name
            elif not nom in sv.Object:                                      # may happen if a single operation
                nod=cm.add_object(sv, nom)
                nod.nature=Lst[:]
                nod.value=[]
            if mylist:
                for x in mylist:                                                # extract elements
                    if x is not None:                       
                        y=treejoin((Plus, A, (x, None, None)))    # create delayed reference
                        if not y in sv.Object:                 
                            nodY=cm.add_object(sv, y)
                            nodY.nature=Bln
                            nodY.isdelayed=True
                            if not y in sv.Delayed_objects: sv.Delayed_objects.append(y)
                            if not y in sv.Active_list: sv.Active_list.append(y) # add to active list
                            st=evalstatus(sv, (Plus, A, (x, None, None))) # recursively calls evaluate
                            setstatus(nodY, st, 0)                   
                            if not isduration(x):                           # if changeable delay 
                                link_node(sv, x, y, (Plus, A, (x, None, None)))  # delay to delayed event 
                            link_node(sv, A[0], y, (Plus, A, (x, None, None))) # event to delayed event
                            link_node(sv, y, nom, tree)                 # delayed event to list                            
                        li+=[y]                                                    # create value
            if not nom in sv.Active_list: sv.Active_list+=[nom] # add to active list
            res.value=li                                                                                    
            sv.Eval_depth-=1
            return res, True                                                  # indicate change to update list
        
    elif O==Have:                                                             # extract keys of a dict              
        root=A[0]                                                               # name of the dict
        if root in sv.Object and sv.Object[root].isdict:                                
            li=[]                       
            dictels=sv.Object[root].value                             # list of keys
            if dictels:
                nb=len(root)+1                                              # to remove the root part
                for elt in dictels:
                    block=makekey(elt[nb:-1])                        # extract key
                    if not block in [None, ""] : li+=[block]          
                res.value=li        
        sv.Eval_depth-=1
        return res, None    

    elif O==Cumul:                                                          # cumulative list            
        li=[]
        cumul=0
        vl=nodA.value
        if vl:
            if isnumber(vl[0]):                                              # accumulate numbers
                for x in vl:
                    cumul+=x
                    li+=[cumul]
            elif isduration(vl[0]):                                          # accumulate delays
                for x in vl:
                    cumul+=seconds(x)
                    li+=[str(cumul)+Unit_sec]                
        res.value=li        
        sv.Eval_depth-=1
        return res, None
    
    elif O==Steps:                                                            # differential list
        li=[]
        last=0
        vl=nodA.value
        if vl:
            if isnumber(vl[0]):                                              # numbers
                for x in vl:
                    li+=[x-last]
                    last=x
            elif isduration(vl[0]):                                          # delays
                for x in vl:
                    li+=[str(seconds(x)-last)+Unit_sec]
                    last=seconds(x)
        res.value=li        
        sv.Eval_depth-=1
        return res, None
    
    elif O==Text:                                                            # text
        vl=nodA.value
        if vl is not None:
            if n1==Drtn: res.value=str(seconds(vl))+Unit_sec  # convert delay to seconds
            else: res.value=buildtext(sv, vl)                        # make text
        sv.Eval_depth-=1
        return res, None

    elif O==Call:                                                            # call
        # address by name a function defined in whand_io.py, e.g. call("display(dessin.jpg, 1500)")
        # Warning: execution is suspended until function terminates
        vl=nodA.value.strip(Space)
        if vl[0]=='"' and vl[-1]=='"': vl=vl[1:-1]         # remove outer quotes 
        while '""' in vl: vl=vl.replace('""','"')               # replace double inner quotes  
        vl=vl.strip(Space)
        here, block, there=findblock(vl)                   # find inner brackets e.g. (dessin.jpg, 1500)
        root=vl[:here]                                               # function name e.g. display
        end=vl[there:]                                              # there should be nothing after closing bracket
        if not block or not root or end:                   # check call structure
            print("\n"+Anom_call_struct)
            print("    ", O+str([vl]))
            raise ReferenceError
        if not hasattr(io, root):                                # check function exists in whand_io.py
            print("\n"+Err_unknown_funct)
            print("-->", root)
            raise ReferenceError            
        args=getvalue(sv, block).value                   # extracts argument list (make it an object)
        if type(args)==list:
            args=deep_get(sv, block, Value)             # extract deep value 
        if type(args)!=list: args=[args]                    # make single arg into a list
        namespace = {"io":globals()["io"]}              # access whand_io global reference space
        argtxt="def myfunc():"+Crlf+"  return io."+root+"("+str(args)+")" # define function myfunc  
        exec(argtxt,namespace)                             # create function myfunc in namespace
        retval=namespace['myfunc']()                   # call function myfunc and get result
        if type(retval)==bool:                                # adjust event format
            retval=[(sv.Current_time, None)] if retval else [(None, sv.Current_time)]
        res.value=retval
        sv.Eval_depth-=1
        return res, None

    # internal functions and operators with possible distributivity   
    nodistr1=(O in Non_distributive1)
    nodistr2=(O in Non_distributive2)

    ambiguity=0                                                                            # initialize flag for ambiguous ops                                                      
    if clausenum in sv.Allow_dic and sv.Allow_dic[clausenum]:     # already computed for this clause        
        allow=sv.Allow_dic[clausenum]
        if Verbose: print("xxxx allow", nom, clausenum, allow)
    else: allow=Allowed[O]                                                            # possible arg and res natures          

    for nat1, attr1, nat2, attr2, natres, attres in allow:                   # loop looking for a nature match
        if Verbose: print("xxxx allow try", nom, clausenum, nat1, attr1, nat2, attr2, natres, attres)
        makedelay= False                                                                # flag for delayed objects
        if O==Plus and natres==Bln:                                               # mark delayed object
            makedelay=True
            if nom in sv.Object:                                                          # make sure object is marked delayed and active 
                if not nom in sv.Delayed_objects: sv.Delayed_objects.append(nom)     
                if not nom in sv.Active_list: sv.Active_list.append(nom) # add to active list
            
        li1, distrib1=prepareval(sv, nodA, nat1, attr1, nodistr1)  # extract appropriate attributes 
        if Verbose: print("xxxx preparing", O, A,nat1, attr1, nodistr1)
        li2, distrib2=prepareval(sv, nodB, nat2, attr2, nodistr2)  # as lists to allow distributivity
        if Verbose: print("xxxx result nature", O, A, distrib1, B, distrib2, natres, res.nature)
        # do not change delay in a delayed event until event itself changes 
        if makedelay and coincide(nodB.lastchange, sv.Current_time): li1=[]
        
        if O==Pick and (li2==[] or li2==[None]):                              # pick from empty list -> empty list
            cop=sv.Object[Empty]                                   
            nd.copynode2(cop, res)                                 
            sv.Eval_depth-=1                           
            return res, None                            

        if not li1 and O!=Add: li2, distrib2=([], False)                        # no empty first term except to add to list
        
        if ((li1 or not nat1) and (li2 or not nat2)) or O in [Or, Hasvalue]: # lazy Or does not need both terms to have values
            if li2:
                ziplist=list(zip(li1, li2))                                                   # create list of pairs of terms
            else:
                ziplist=[(x, None) for x in li1]                                        # pair all first terms with None
                    
            if distrib1 and distrib2:                                                     # double distribute
                diff=len(li1)-len(li2)                                                       # match number of elements
                if diff>0: ziplist=ziplist+[(x, None) for x in li1[-diff:]]
                elif diff<0: ziplist=ziplist+[(None, x) for x in li2[diff:]]
                    
            elif distrib1:                                                                      # left distribute
                elt=li2[0] if li2 else None                                              # develop li2
                ziplist=[(x, elt) for x in li1]
                        
            elif distrib2:                                                                     # right distribute
                elt=li1[0] if li1 else None                                             # develop li1
                ziplist=[(elt, x) for x in li2]

            lisres=[]
            
            for v1, v2 in ziplist:                                                                        # individual operation
                vlu=operation(sv, O, v1, v2)          # NOW COMPUTE OPERATION
                if Verbose: print("xxxx COMPUTED", sv.Current_time, "s:", nom, ":", O, v1,v2, "-->", vlu, natres, res.nature)
                if natres==Drtn and vlu is not None: vlu=str(vlu)+Unit_sec     # is it a duration

                if O==Add:
                    if type(vlu)==list and vlu:
                        if nat2==Drtn: vlu[-1]=str(vlu[-1])+Unit_sec                    # make last element a duration
                        if nat1==Drtn: vlu[0]=str(vlu[0])+Unit_sec                       # make first element a duration
                        
                if makedelay and vlu and type(vlu)!=list:
                    vlu=[vlu]                                                                              # convert to on/off list for event
                
                if O in Glitch_list:                                                                     # build a glitch (begin/end/change) from a time  
                    if type(vlu) in [int, float]: 
                        if coincide(vlu, sv.Current_time): vlu=sv.Current_time     # correct approximate current time
                        vlu=[(vlu, vlu+Glitch_time)] if O!=Change else [(vlu, vlu+Change_time)] # glitch duration
                        makedelay=True                                                             # glitches are delayed

                if (distrib1 or distrib2):                                                            # list of true/false values                             
                    if vlu is True: vlu=Vrai                                                          
                    if vlu is False: vlu=Faux

                lisres+=[vlu]                                                                            # build list of results
                
            # end of distribute loop
                
            finish=False
            newnat=natres
            if (distrib1 or distrib2):                                                                # result is a list
                    vlu=lisres
                    newnat=Lst[:]
                    for x in vlu:
                        if x is not None: finish=True
            else:                                                                                            # result is simple
                    if lisres:
                        vlu=lisres[0]
                        finish=True
                    else:
                        vlu=None               
                    if makedelay: res.isdelayed=True                                       # mark as delayed
            if finish:                                                                                       # check if ambiguous operation 
                ambiguity+=1                                                       
                if ambiguity>1:
                    print(Err_ambig_op, O, A, B)                             # *** Error: Operation is ambiguous ***
                    raise ReferenceError
                if clausenum and not clausenum in sv.Allow_dic:                              # clausenum identifies the clause 
                    sv.Allow_dic[clausenum]=[(nat1, attr1, nat2, attr2, natres, attres)]  # store parameters for faster use (not newnat)

            if Verbose: print("xxxx rt eval call setvalue", sv.Current_time, "s", nom, (O, res.content(), newnat, attres, vlu))
            ok=setvalue(sv, O, res, vlu, sv.Current_time, newnat)       # attribute value to res (not directly to object)

    sv.Eval_depth-=1
    return res, None
    
#===================================================== prepareval
def prepareval(sv, nod, nat, attr, nodistr):
    """
    extracts and checks value for operation
    nat is the expected nature of the result
    attr is the name of the attribute to extract (typically value)
    nodistr if true prevents distributivity (because operator expects a list)
    returns a list [li, distrib] where
    li is a list of values with only one element if no distributivity is required
    distrib indicates that distributivity is required
    """
    if not nat or not attr:
        return [], False                                              # return an empty list
    
    distrib=True                                                     # decide about distributivity
    if nodistr: distrib=False                                    # operator does not allow it
    elif nat==Lst: distrib=False                              # expected value is already a list
    else:
        li=nod.value
        if type(li)!=list: distrib=False                        # actual value is not a list
        elif nat==Bln:
            if not li : distrib=False                              # empty list
            if li and type(li[0])==tuple: distrib=False # a single event, not a list
            
    if not distrib: li=[nod.name]                            # make a list with single object           
    lisres=[]                                                           # always work with a list
    lastnat=None
    for vlu in li:                                                      # get and check all values in a list
        resx=getvalue(sv, vlu)                                   # retrieve full node for each
        nt=resx.nature[:]
        if nt!=lastnat:                                              # verify list is homogeneous
            if lastnat is None: lastnat=nt
            elif sv.Current_time!=0:                           # only allowed at initialization
                warn(Warn_Heterogeneous+"\n"+nod.content(), sv.Do_tests)
                
        if len(set(nt)&set(nat))!=1:                          # if nature is ambiguous                 
                return [], False                                     # break out 
            
        vlu=resx.value                          
        if nat==Lst:                                                  # get full value of list through indirection
            vlu=deep_get(sv, vlu, None)                    # sometimes not deep enough. But avoid extracting event times                                  
        elif resx.nature==Bln and attr==Value:        # Bln has other attributes (e.g. Occur, Lastchange)
            if vlu: vlu=vlu[0]                                       # first in list of on/off doublets (assumes list is well ordered) !
        else: 
            vlu=getattr(resx, attr)                                # general case: get attribute                                                    

        if nat==Drtn and isduration(vlu):                # convert delays to numbers (for arithmetics)
            vlu=seconds(vlu)
            
        lisres+=[vlu]                                                # add result to list
    return lisres, distrib

# ======================================= operation
def operation(sv, O, v1, v2):                       
    """
    computes operation between two simple values
    """
##    print("xxxx rt op", sv.Current_time,"s:", O, v1, v2)
    # some empty args do not prevent evaluation
    if v1 is None and not O in [Or, Hasvalue]: return None                        # lazy 'Or'

    if O in [And, Or, Not]:                                                                           # logical op                                 
        if type(v1)==list:                                                                               # lists are not allowed
            print(Anom_logic, v1)                                 # *** Anomaly in rt.op: not a Bln logic value
            raise ReferenceError       
    
    if (v1==[] and not O in [Count, Add, Match, Within, Pick, Sort, Find, Touch]): return None          
    if (v2==[] or v2 is None) and not O in Unary+[Or, Add, Match, Within, Isin, Pick, Sort]: return None   

    if O==Plus:
        # avoid creating a delayed object after the initial event has ended
        if type(v1)!= tuple:                                                                             # number or delay
            return v1+v2
        else:                                                                                                   # delayed event
            x=v1[0]
            y=v1[1]
            if x is not None: x+=v2                                                                 # on time 
            if y is not None and y!=0: y+=v2                             # 'false' at start: do not delay 
            return (x,y)
        
    elif O==Change:                                                                                     # change
        return v1 if sv.Current_time>0 else None                    # no change at start      
    
    elif O==Begin:                                                                                        # Begin
        v1=v1[0]                                                                                                                        
        return v1
    
    elif O==End:                                                                                           # End
        v1=v1[1] if sv.Current_time>0 else None                    
        return v1
                
    elif O==And:                                                                                           # and
        v1=logic(v1, sv.Current_time)
        v2=logic(v2, sv.Current_time)
        if v1 is True and v2 is True: return True
        if v1 is None or v2 is None: return None                                              
        return False                                        # at least one arg must be not None
    
    elif O==Or:                                                                                           # lazy 'Or' 
        v1=logic(v1, sv.Current_time)
        if v1 is True: return True 
        v2=logic(v2, sv.Current_time)
        if v2 is True: return True
        if v1 is None or v2 is None: return None                 
        return False                                             # only if both args are not None
                
    elif O==Not:                                                                                            # not
        v1=logic(v1, sv.Current_time)
        if v1 is True: return False
        if v1 is False: return True
        return None              
    
    elif O ==Any:                                                                                            # any
        v1=deep_get(sv, v1, Value)   # needed because by default deep_get does not extract event times
        if type(v1)==list:
            for x in v1:
                if type(x)==tuple:
                    st=logic(x, sv.Current_time)
                    if st: return True
        return False
    
    elif O ==All:                                                                                              # all
        v1=deep_get(sv, v1, Value)   # needed because by default deep_get does not extract event times                                  
        if type(v1)==list:
            non=False                                                    
            for x in v1:
                if type(x)==tuple:
                    st=logic(x, sv.Current_time)
                    if st is False: return False
                    if st is None: non=True                        
            if non: return False                         # not true until all is determined
        return True
                    
    elif O==Count:                                                                                           # count
        if type(v1)==int: return v1
        if type(v1)==list: return len(v1)
        return None
       
    elif O==Minus:                                                                                           # minus
        return v1-v2
        
    elif O==To:                                                                                                # to
        if type(v1)==list and type(v2)==list:
            if v1[-1] is not None and v2[-1] is not None: return v2[-1]-v1[-1]
##        if type(v1)==tuple and type(v2)==tuple:                                         
##           if v1[0] is not None and v2[0] is not None: return v2[0]-v1[0]                     
        return None                                 
    
    elif O==Inter:                                                                                           # inter
        if type(v1)==list and len(v1)>1:                          # uses occur attribute
            return v1[-1]-v1[-2]                            
        return None                                 

    elif O==Since:                                                                                          # since (not evt)
        if v1 is None or type(v2)!=tuple:                           # v2 expects event times
            return False
        toff=v2[1]                                                              # off time
        if toff is None:
            return False                                                       # no event or still true
        ok=sv.Current_time>(toff+v1) or coincide(sv.Current_time , (toff+v1)) 
        return ok                                                              # False also with None                                                                  
    
    elif O in [Order, Sequence]:                                                                     # order, sequence
        # order allows repeats, sequence does not  
        if type(v1)!=list or len(v1)<1:                                # v1 expects a list of event names
            return False  
        nb=[]
        for i, evt in enumerate(v1):                                   # count repeats from end in a list of results
            nb+=[v1[i:].count(evt)]
        tim=[]                                                                   # verify occurrences and times
        for i, evt in enumerate(v1):                                   # works on occur
            occ=sv.Object[v1[i]].occur                               # occurrences of event
            if len(occ)<nb[i]: return False                           # not enough occurrences
            tim+=[occ[-nb[i]]]                                            # get last occurrences in a list       
        if len(v1)==1: return True                                     # only one event that has occurred
        if O==Sequence and len(v1)>2:                           # check extra occurrences  
            for i, evt in enumerate(v1):                
                occ=sv.Object[v1[i]].occur                           # occurrences of event
                if len(occ)>v1.count(evt):                             # more occurrences should not
                    for ti in occ[:-v1.count(evt)]:                    #  occur in window
                        if ti>tim[0] and ti<tim[-1]: return False
        tim2=tim[:]
        tim2.sort()
        if tim2==tim:
            return True                                                       # check order                              
        return False  
    
    elif O==Lasted:                                                                                       # lasted
        if type(v1)==tuple:                     
            if logic(v1, sv.Current_time): return sv.Current_time-v1[0]               # duration since onset           
        return 0                                 
        
    elif O==Mult: return v1*v2                                                                       # mult
    elif O==Div:
        if v2: return v1/v2                                                                                 # div
        if v2==0: warn("\n"+Warn_div_zero+" "+str(v1)+"/0\n", sv.Do_tests)                    # warning, not error
        return None                                                         # no error if divide by zero or None
        
    elif O in [Value, Lastchange] :                                                                  # node attribute        
        return v1
    elif O== Name:                                                                                        # node attribute: name                                                        
        return '"'+str(v1)+'"'                                           # add quotes
    elif O==Occur:                                                                                         # node attribute: occur     
        return v1[:]
    
    elif O==Ramp:                                                                                         # ramp
        if type(v1) in [int, float] and v1>=0:
            return list(range(int(v1+1)))[1:]                      #  works also for empty ramp
        return None
    
    elif O==Measure:                                                                                     # measure 
        return scanalog(sv, v1)
    
    elif O==Read:                                                                                          # read 
        return io.readmessage(sv, v1)

    elif O==Touch:                                                                                        # touch
        if v1:
            filename=v1[0]
            X=v1[1]
            Y=v1[2]
            res=io.readtouch(sv, filename, X, Y)
        else:
            res=io.readtouch(sv, None, 0, 0)
        if res is None: return None
        return [res[0], res[1], Vrai if res[2] else Faux]
    
    elif O==Proba:                                                                                         # proba     
        return True if (random()<v1) else False
    
    elif O==Find:                                                                                           # find
        v1,v2=v2,v1                                                       # switch args: list is v2
        if v1 is not None and v2 is not None:
            if type(v1)==tuple and type(v2)==list:         # find Bln v1 in a list 
                v1=logic(v1, sv.Current_time)                   # get status
                for vl, x in enumerate(v2):
                    x=getvalue(sv, x).value                         # get value from name
                    if type(x)!=list or not x:                         # empty value not allowed
                        print(Anom_find, v2, x)             # "*** Anomaly Find: non Bln in list"
                        raise ReferenceError
                    x=logic(x[0], sv.Current_time)               # get status
                    if x==v1: return vl+1                             # found
            else:
                v1=getvalue(sv, v1).value                          # get value from v1 name
                for vl, v in enumerate(v2):                         # match by value
                    x=getvalue(sv, v).value
                    if x==v1: return vl+1                             # found
                    if type(x) in [int, float] and type(v1) in [int, float]:    
                        if abs(x-v1)<FloatPrecision:               # approximate
                            return vl+1
        return 0                                                              # not found
    
    elif O==Listfind:                                                                                           # listfind
        v1,v2=v2,v1                                                       # switch args: list of lists is v2
        v1=getvalue(sv, v1).value                                  # get value from v1 name
        for vl, v in enumerate(v2):                                  # match by value
            x=getvalue(sv, v).value
            if x==v1: return vl+1                                     # found
        return 0                                                              # not found
    
    elif O==Sqrt:                                                                                              # sqrt
        if type(v1) in [int, float] and v1>=0:
            return sqrt(v1)                   
        warn("\n"+Warn_sqrt_neg+" "+str(v1)+"\n", sv.Do_tests)                    # warning, not error
        return None
    elif O==Intg:                                                                                              # intg
        if type(v1) in [int, float]: return float(int(v1))                  
        warn("\n"+Warn_invalid_nb+" "+str(v1)+"\n", sv.Do_tests)                 # warning, not error
        return None
    elif O==Absv:                                                                                              # absv
        if type(v1) in [int, float]: return abs(v1)                   
        warn("\n"+Warn_invalid_nb+" "+str(v1)+"\n", sv.Do_tests)                # warning, not error
        return None
    elif O==Logd:                                                                                              # logd  
        if type(v1) in [int, float] and v1>0: return log10(v1)                   
        warn("\n"+Warn_log_neg+" "+str(v1)+"\n", sv.Do_tests)                    # warning, not error
        return None
    elif O==Powr:                                                                                              # powr  
        if type(v1) in [int, float] and type(v2) in [int, float] \
           and (v1>=0 or v2.is_integer()): return pow(v1, v2)                   
        warn("\n"+Warn_compute_power+" "+ str(v1)+ " ^ "+ str(v2)+"\n"+" "+str(v1)+"\n", sv.Do_tests)  # warning, not error
        return None
    
    elif O==Shuffle:                                                                                            # shuffle 
        if type(v1)==list:
            li=list(v1)
            shuffle(li)                                                                                              # do not change original
            return li
        return None
    
    elif O==Alea:                                                                                                # alea 
        if type(v1) in [int, float] and v1>=0:
            return [random() for i in range(int(v1))]
        warn("\n"+Warn_empty_alea+" "+v1+"\n", sv.Do_tests)                 # warning, not error
        return None
    
    elif O==Add:                                                                                                 # add
        if v2 is None: v2=[]                                        
        if v1 is None: v1=[]                                        
        if type(v1)==tuple: v1=Vrai if logic(v1, sv.Current_time) else Faux    # get logical value 
        elif type(v1)!=list: v1=getvalue(sv, v1).value                                      # get list                                                   
        if type(v2)==tuple: v2=Vrai if logic(v2, sv.Current_time) else Faux    # get logical value       
        elif type(v2)!=list : v2=getvalue(sv, v2).value                                     # get list                                      
        if type(v1)==list and type(v2)==list: return v1+v2                            # concatenate lists
        elif type(v1)==list: return v1+[v2]                                                      # add last element
        elif type(v2)==list: return [v1]+v2                                                      # add first element
        return None
    
    elif O in [Nequal, Grequal, Smequal, Equal, Greater, Smaller]:
        if O in [Nequal, Equal] and type(v1)==tuple and type(v2)==tuple:                     # compare event status
            if O==Equal: return logic(v1, sv.Current_time)==logic(v2, sv.Current_time)   # Equal
            return logic(v1, sv.Current_time)!=logic(v2, sv.Current_time)                          # Nequal
        if type(v1) in [int, float] and type(v2) in [int, float]:                                              # correct float precision errors                            
            if abs(v1-v2)<FloatPrecision: v2=v1
        elif type(v1)!=type(v2):                                                                                        # do not compare different types  
            return (O==Nequal)                                                                                        # but accept they are not equal
        if v1<v2:                                                                                                              # compare values
            if O in [Nequal, Smequal, Smaller]: return True
            if O in [Equal, Grequal, Greater]: return False
        elif v1>v2:
            if O in [Nequal, Grequal, Greater]: return True
            if O in [Equal, Smequal, Smaller]: return False
        else:
            if O in [Equal, Grequal, Smequal]: return True
            if O in [Nequal, Greater, Smaller]: return False           
            
    # time.struct_time(tm_year=2014, tm_mon=10, tm_mday=19, tm_hour=7, tm_min=58, tm_sec=27, tm_wday=6, tm_yday=292, tm_isdst=1)
    elif O==Timeis:                                         # n.b. also create delayed object at start    # timeis  
        now=(3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec)
        return True if coincide(v1, now) else False
    
    elif O==Dayis:                                         # n.b. also create delayed object at start    # dayis  
        now=Wday[io.localtime().tm_wday]
        return True if coincide(v1, now) else False
    
    elif O==Dateis:                                         # n.b. also create delayed object at start    # dateis  
        mon=Month[io.localtime().tm_mon-1]      # format is like "may 23", "may23" or may23
        dn=io.localtime().tm_mday                       # format is like "may 23", "may23" or may23
        now=mon+str(dn)
        v1=noquotes(v1).replace(Space,"")
        return True if coincide(v1, now) else False
    
    elif O==Weekis:                                         # n.b. also create delayed object at start    # weekis  
        thisday=io.localtime().tm_wday                 # week starts on monday except on jan 1
        nbday=io.localtime().tm_yday
        now=int((nbday-thisday+14)/7)
        return True if coincide(v1, now) else False
    
    elif O==Time:                                                                                                               # time  
        tm=None
        if type(v1)==tuple and v1[0] is not None:                                 
            beg=v1[0]
            now=3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec
            tm=now+beg-sv.Current_time
##            tm=io.clock()%(3600*24)+beg-sv.Current_time                                                 
        return tm
    
    elif O==Match:                                                                                                          # match 
        # do not distribute because complex and '=' or 'is' should work                 
        if coincide(v1, v2): return True                               
        if type(v1)!=list or type(v2)!=list: return False     
        if len(v1)!=len(v2): return False                           
        for c,d in zip(v1,v2):                                     # deep matching (1 level)
            a,b=c,d                                                    # preserve initial lists
            if type(c)==list:                                        # element is a list
                a=c[:]
                for i, x in enumerate(a):                       # look into list
                    a[i]=getvalue(sv, x).value                 # get value from name
            if type(d)==list:                                        # element is a list
                b=d[:]
                for i, x in enumerate(b):                       # look into list
                    b[i]=getvalue(sv, x).value                 # get value from name
            if not coincide(a,b): return False
        return True                                                                                                   

    elif O==Isnot:                                                                                                              # isnot 
       neg=operation(sv, Is, v1, v2)
       return True if neg is False else False              # None returns False                                                    
   
    elif O==Is:                                                                                                                   # is
        if coincide(v1, v2): return True                      # simple comparison                    
        for dic in list(sv.Object.values()):                  # comparison by attributes
            # e.g. 'eye is blue' from 'color(eye)=blue'
            if dic.isdict and dic.name[0]!=Special:      # scan all dicts                                                
                vl=dic.value                                          # list of dict elements
                if type(vl)==list:
                    #  look for v1 in args: some attribute must be v2           
                    ky=makekey(v1)                               # adjust key name e.g. 'eye'                                
                    for elt in vl:
                        if elt==dic.name+Obr+ky+Cbr:    # found v1 in args e.g. 'color(eye)'
                            for attr in [Name, Value]:                       
                                n=elt
                                while n in sv.Object:              # extract value e.g. what color
                                    v=getattr(sv.Object[n], attr)                                          
                                    if coincide(v, v2): return True   # name or value matches      
                                    n=v if n!=v else None       # get deeper value
                                    if type(n)==list: break      # value should not be a list
        return False
    
    elif O==Pick:                                                                                               # pick
        # create a sublist from first arg using true elements mask from second arg 
        li=[]
        if v1==[] or v2==[]: return []                 # pick from empty is empty                                           
        if v1 is None or v2 is None: return None
        if type(v1)!=list or type(v2)!=list:           # check args are lists             
            print("\n", Anom_comput, O, v1, v2)                           
            raise ReferenceError
        for x,y in zip(v1,v2):
            if y is None: return None                  # do not pick if mask contains None
            if type(y)!=tuple:               
                y=getvalue(sv, y).value                 # extract logical value from name
                if type(y)==list and y: y=y[0]        # first tuple from list gives current status
            if type(y)!=tuple:    
                print("\n", Err_arg_nat, Pick, y)
                raise ReferenceError
            if logic(y, sv.Current_time): li+=[x]   # add element if true in mask
        return li

    elif O==Sort:                                                                                             # sort
        v,w=v1,v2
        if v is None: v=v2[:]                                # accept a single arg
        if v is None or w is None: return None  # do not sort None
        if type(v)!=list or type(w)!=list:               # check args are lists            
            print("\n", Anom_comput, O, v1, v2)                           
            raise ReferenceError
        v=v[:]                                                      # make a copy of lists
        w=w[:]
        keyisbool=False                                      # maybe sort by logical value 
        z=[]                                                         # create list of logical values if needed
        for y in w:
            if type(y)!=tuple:                                 
                y=getvalue(sv, y).value                   # extract logical value from second arg
                if type(y)==list and y: y=y[0]
            if type(y)==tuple:
                keyisbool=True
                z+=[logic(y, sv.Current_time)]
        if keyisbool: w=z                                     # replace sort key with logical key
        ok=True
        for i, x in enumerate(w[:]):                       # scan sort key                                                                  
            if x in sv.Object and sv.Object[x].value!=x:
                x=sv.Object[x].value                        # extract value of key 
            if x is None: ok=False
            w[i]=x                                                  # replace key with its value
        if  not ok: return v                                   # do not sort if None keys
        else:
            z=list(zip(v, w))
            z.sort(key=lambda x: x[1])                   # sort according to key        
            if z: return list(list(zip(*z))[0])               # unzip                                                                                      
            else: return []
       
    elif O==Isin:                                                                                                                      # isin
        if v1 is not None and v2 is not None:
            if type(v1)==tuple and type(v2)==list:                  # match by logical status 
                v1=logic(v1, sv.Current_time)                            # get status
                for vl, x in enumerate(v2):
                    x=getvalue(sv, x).value                                  # get value from name
                    if type(x)!=list or not x:                                  # empty value not allowed
                        print(Anom_isin, v2, x)                   # "*** Anomaly Isin: non Bln in list"
                        raise ReferenceError
                    x=logic(x[0], sv.Current_time)                        # get status
                    if x==v1: return True
            else:                                                                       # match by value
                for vl, x in enumerate(v2):
                    x=getvalue(sv, x).value
                    if coincide(x, v1): return True
        return False

    elif O==Within:                                                                                                                  # within
        v1=deep_get(sv, v1, Value)                               # extract list of references or values                     
        v2=deep_get(sv, v2, Value)
        if v1 is None or v2 is None: return None
        if type(v1)!=list or type(v2)!=list:                      # check args are lists            
            print("\n", Anom_comput, O, v1, v2)                           
            raise ReferenceError
        l=len(v1)
        if l==0:                                                             # trick to allow 'is not empty'    
            return True if len(v2)>0 else False   # empty within not empty, but not empty within empty   
        for here in range(len(v2)-l+1):                         # match values
            if coincide(v2[here:here+l], v1): return True
        for here in range(len(v1)):                                # replace all v1 elements with logical status  
            if type(v1[here])!=tuple: return False
            v1[here]=logic(v1[here], sv.Current_time)
        for here in range(len(v2)):                                # replace all v2 elements with logical status  
            if type(v2[here])!=tuple: return False
            v2[here]=logic(v2[here], sv.Current_time)
        for here in range(len(v2)-l+1):                          # test again
            if v2[here:here+l]==v1: return True               
        return False
        
    elif O==Hasvalue:                                                                                                              # hasvalue
        return ( v1 is not None )
    
    elif O==Load:                                                                                                                    # load    
        if type(v1)!= str:
            print("\n", Anom, Load,"'"+str(v1)+"' ***")                             
            raise ReferenceError
        v1=noquotes(v1)                                             # remove quotes from filename
        v1=addparentdir(v1)                                       # complete path        
        try:
            brut=io.gettextfile(v1)                    
        except IOError:                                                # error opening or reading file
            print("\n", Err_404, str(v1), "\n")                                    
            raise ReferenceError
        li=[]                                                                  # split text into lines
        li=brut.split(Crlf)
        for i,expr in enumerate(li):                               # look for list in each line
            expr=expr.strip(Space)                                            
            li[i]=expr
            if detectlist(expr):                                                    
                expr=nobrackets(expr)                           # remove brackets
                li[i]=expr.split(Comma)                           # convert text to list
        if li[-1]=='' or li[-1]==Comma: li=li[:-1]          # remove trailing bits
        return li
       
    print("\n", Err_imposs_oper)                               # impossible operation              
    print([O], Obr, v1, Comma, v2, Cbr)
    raise ReferenceError

#===================================================== getelement
def getelement(alist, ind):                                                                                       
    """
    extract element. Range allowed is -len(vl) to infinity (cyclic)
    backward access allowed from last element (-1) to first (-len(vl)), but not before
    first element is 1, last is -1
    """
    if ind==0: return None                                                    # no element before the first
    if ind<-len(alist): return None                                         # no element before the first
    if ind>0:
        return alist[(int(ind)-1) % len(alist)]                             # positive indices cycle
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
    res=getvalue(sv, nom)
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
                res=getvalue(sv, ky)
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

#===================================================== deep_get
def deep_get(sv, nom, attr=None):                               
    """
    extracts values of a list of objects or attributes from the name
    returns None (not an empty list) if list cannot be found
    does not extract event times from a list if attr is not Value
    """
##    print("xxxx deepg", nom, attr)
    v=nom
    if v is None: return v
    prev=None
    while type(v)!=list:                                             #  search for a list
        if v in sv.Object:              
            v=sv.Object[v].value                                  # iterate until no more progress 
            if v is None or v==prev:                            # return if list not found
                return None
            prev=v
        else:                                                               # not a list and not an object
            print("\n", Anom_deep_get)                        
            print( v, [attr])
            raise ReferenceError

##    print("xxxx going deeper in", nom, "with", v)
    li=[]                                                                 # found a list, go deeper for each element  
    for w in v:                                                   
        x=w
        prev=None
        while type(x)!=list and x in sv.Object:          # name: look deeper for value 
            if sv.Object[x].nature==Lst:
                x=deep_get(sv, x, attr)                        # recurse to access deep values 
            elif sv.Object[x].nature!=Bln:                   # do not extract event times here
                x=sv.Object[x].value                           # one more step
            if x==prev: break                                    # no progress
            prev=x                                                    # monitor progress
        li+=[x]                                                         # rebuild list with deep elements

    if attr:                                                             # extract each attribute
        v=li
        li=[]
        for x in v:
            at=x
            if type(x)!=list and x in sv.Object:              
                at=getattr(sv.Object[x], attr)          
                if sv.Object[x].nature==Bln and at: at=at[0]   # extract first Bln onoff
            li+=[at]
##    print("xxxx -->", li)
    return li

#===================================================== buildlist
def buildlist(sv, A):
    """
    make a list of names from list of triplets
    convert numbers to float, delays to seconds
    use treejoin to reconstruct name of expressions
    """
    verbose=('bdl' in Debog)
    li=[]
    if not A: return li
    if verbose: print("      buildlist", treejoin((Comma, A, None)))
    for x in A:
        if x:
            op=x[0]                                                               # get operator/leaf
            if isnumber(op):
                li+=[float(op)]                                                 # a number (float)
            elif isduration(op):                       
                li+=[str(seconds(op))+Unit_sec]                     # a delay (seconds)
            else:
                li+=[treejoin(x)]                                              # just the name (reconstruct expression)
    return li

#===================================================== buildtext
def buildtext(sv, vl):                               
    """
    builds a string from value, recursively, adding quotes
    """
    if type(vl)==tuple:                                                # a logic value
        return Vrai if logic(vl, sv.Current_time) else Faux
    if type(vl)==list:                                                    # a list  
        st=""
        bracketflag=True
        for x in vl:                                                         # access value of each element
            y=x
            if type(x)==str and x in sv.Object:               # a name: recurse on value
                vlu=sv.Object[x]
                y=buildtext(sv, vlu.value)
            if type(x)==tuple:                                        # an event, not a list               
                y=buildtext(sv, x)                                    # recurse to get logic value
                bracketflag=False                            
            if type(x)==list:                                            # a list: recurse                   
                y=buildtext(sv, x)
            st+=noquotes(str(y))+Comma                    # add element to list
        st=st[:-1] if st and st[-1]==Comma else st      # remove last comma
        return Obr+st+Cbr if bracketflag else st
    return Quote+noquotes(str(vl))+Quote              # not a list

#===================================================== link_node
def link_node(sv, cause, effect, tree):                               
    """
    creates the appropriate links between two objects
    cause and effect are names, tree is the effect tree
    """
    Verbose="lnk" in Debog
    if Verbose:  print("linking", cause, "-->", effect)
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
                condnum=one_condition(sv, effect, c, tree, condnum)  # reprocess condition
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
                    st=evalstatus(sv, (O,(x, None, None), None))               # recursively calls evaluate
                    setstatus(nodY, st, 0)                   
                    nodX=sv.Object[x]                                                        # the element node
                    link_node(sv, x, y, (O, (x, None, None), None))             # link event to glitch 
                    link_node(sv, y, nom, tree)                                            # link glitch to list
                li+=[y]                                                                               # add to value list
        if not nom in sv.Active_list: sv.Active_list+=[nom]                    # add to active list
    return li

#===================================================== setvalue
def setvalue(sv, O, res, vlu, time, natres):
    """
    stores value and relevant attributes in node res (not yet into nod)    
    Always store result in value
    For Bln when vlu is Vrai / Faux, compute on and off times
    for delayed objects, set res then fuse delays with nod
    For Change, update change times immediately
    """
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
            if not (res.isdelayed):             # delayed objects must fuse delays, not change them                                     
                if vlu is True or vlu==[(time, None)]: vlu=[(time, None)]   # store on time
                else: vlu=[(None, time)]                                                     # store off time (on time is unknown)  
                if O == Change and time>0: res.lastchange=time            # update change times
    if ok:
        res.value=vlu if type(vlu)!=list else vlu[:]                                   # now store
    else:                                                                                               # nature is not identified
        print(Anom_setv_nat, res.content(), [vlu], "\n")  # "*** Anomaly in rt.setv: unknown nature ***   "
        raise ReferenceError
    return ok

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
    nam=noquotes(fname)                                         # filename used as key in sv.Buff
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
            fname=getvalue(sv, fname).value                        # extract name from ref
        fname=noquotes(fname)                                         # remove quotes
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
        
#===================================================== updateval
def updateval(sv):                                                               
    """
    Compute values when something changes, based on haschanged flag.
    Allows multiple changes in one time step for delays only.   
    """
    Verbose='upv' in Debog

    start_list=[nom for nom in sv.Active_list if sv.Object[nom].haschanged]   # sv.Active_list is computed in make_activelist after initialization  
##    print(sv.Current_time, start_list)                                                                              # then completed with newly created events or glitches 
    next_list=[]               
    for nom in start_list:                                                               # make list of required updates
        nod=sv.Object[nom]        
        next_list+=nod.effects                                                       # list based on object effects
        nod.haschanged=False                                                      # reset after processing       
        
        if applied(nom, Idem):                                                       # make sure consequences of idem/old will be processed
            if nod.nature==Bln:
                updatecond(sv, nom, st=istrue(nod, sv.Current_time))  # immediately update condition
            else:
                updatecond(sv, nom, ch=True)                                  # object has changed, so idem must change too

        if nod.nature==Bln and istrue(nod, sv.Current_time) and (nod.occur==[] or nod.occur[-1]!=sv.Current_time): 
            set_occur(nod, sv.Current_time)                                        # occur of a changed event
            if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became true")
        
    if Verbose and start_list: print("xxxx UPV start list:", sv.Current_time, start_list, "active:", sv.Active_list)

    count_iter=0                                                                            # avoid too many iterations

    while start_list and count_iter<Max_iter:                                 # outer loop: repeat until no more consequences or too many iterations
                                                                                                    # start_list will be updated with consequences during loop 
        count_iter+=1                                                                     # iteration count
        
        for nom in start_list:                                                             # scan nodes that have changed or need changing
            changes=False                                                                 # flag: continue updating until no change left
            sv.Eval_depth=0                                                               # avoid excess recursivity (circular dependencies)            
            nod=sv.Object[nom]
            if Verbose: print("xxxx updating", sv.Current_time, "s:", nom, nod.value, nod.nature)
            
            for c,vnum in nod.clauses:                                               # browse clauses for the object (as numbers)                                
              if c is not None:                                                             # None would mean the clause is obsolete
                  
                cnd, nam, v=sv.Save_value[vnum]                               # retrieve clause as full tree
                sv.Current_clause=(nom, cnd, v)                                 # keep track of current clause for debugging purposes                          

                if Verbose: print("xxxx cond", sv.Current_time, "s:", nom, Col, When, cnd, (c,), [sv.Condition[c]==1], Col, v)

                if (sv.Condition[c]==1):                                               # condition is fulfilled if equal to 1 (see updatecond)
                    # verify stability of condition
                    if cnd[1] is not None:
                        cx=treejoin(cnd[1])
                    else:
                        cx=cnd[0]
                    if sv.Current_time>0:
                        if cx in sv.Object and sv.Object[cx].isunstable:
                            print(Warn_unstable, cx, "at", sv.Current_time)   # Unstable condition:
                            if Fatal_use_before: raise ReferenceError
                                                                                             
                    res, ch=evaluate(sv, v, clausenum=vnum)                                               # NOW EVALUATE NODE <---------------
                                                                                                   # clausenum helps accelerate processing in prepareval 
                    changes=changes or ch                                         # keep track of changes across conditions            

                    if Verbose: print("xxxx result", sv.Current_time, "s", nom, nod.nature, nod.value, "<--", res.content())

                    # Is it a new value (negative pointer indicates deep changes in a list) 
                    newval=(res.value!=nod.value) or ch                           # a valid new value
                    if (applied(nom, Store) or applied(nom, Output) or applied(nom, Command) or applied(nom, Write)) \
                        and (nod.lastchange!=sv.Current_time and sv.Current_time>0):
                        newval=True                                                             # output once even if value has not changed
                    if nod.nature==Bln and newval:
                        if nod.isdelayed:
                            prev=nod.value[:]                                                # delayed event: check if changed
                            if nod.nature!=Lst: fuse_delays(sv, nod, res)        # set new delays (would be better if done later)       
                            if nod.value==prev:
                                newval=False                                                   # no change if delays are the same
                        else:                                                                         # adjust event times
                            res.value=[(sv.Current_time, None)] if istrue(res, sv.Current_time) else [(None, sv.Current_time)]
                            if istrue(res, sv.Current_time)==istrue(nod, sv.Current_time):
                                newval=False                                                   # no change if status is unchanged
                            
                    if newval:                                                                     # validate change
                        if not nod.nature[0] in res.nature:
                            if sv.Current_time!=0:
                                print(Err_conflict_nat)
                                print(nom, res.nature, nod.nature)
                                raise ReferenceError
                        nod.lastchange=sv.Current_time
                        if applied(nom, Store): bufstore(sv, applied(nom, Store), res.value)  # store in memory
                  
                        # copy result to nod
                        nod.isunstable=res.isunstable
                        if  nod.isdelayed:
                            cleanup_delays(sv, nod)                                       # remove past delays without sorting
                        else:
                            if type(res.value)==list and res.value!=nod.value:   # works also for simple events
                                nod.value=res.value[:]                                      # make a true copy of list  
                                nod.pointer=0                                                  # reset pointer if list changes (avoid next with event lists)
                            else:                                                                       
                                nod.value=res.value                                         # simple copy

                        # update conditions        
                        updatecond(sv, nom, ch=True)
                        if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just changed")
                        if nod.nature==Bln:
                            if istrue(nod, sv.Current_time) and nod.value[0][0]==sv.Current_time:    # just became true
                                updatecond(sv, nom, st=True)
                                if nod.occur==[] or nod.occur[-1]!=sv.Current_time:
                                    set_occur(nod, sv.Current_time)
##                                    nod.occur+=[sv.Current_time]                                                         # occur of changing object
                                if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became true")
                            elif not istrue(nod, sv.Current_time) and nod.value and nod.value[0][1]==sv.Current_time:    # just became false
                                updatecond(sv, nom, st=False)
                                if Verbose: print("xxxx at", sv.Current_time, nod.content(), "just became false")

                        # update conditions for a list (for changing lists)
                        if nod.nature==Lst:
                            for eff in nod.effects:                                                    # access effects of this list
                                nodE=sv.Object[eff]
                                for i, (num,vnum) in enumerate(nodE.clauses):        # extract condition
                                    c, nam, w=sv.Save_value[vnum]                           # retrieve original condition                                   
                                    one_condition(sv, eff,c,w,num)                             # reprocess condition

                        # update outputs and controlpanel
                        link_output(sv, nom)                                                         # OUTPUT EFFECTS   
                        if sv.Graphic:
                            updatepanel(sv, nom)
                            if nom in sv.Visible and not nom in sv.Namedpinlist:   # slow 'in' but only with graphic
                                sv.interface.update(sv, nom)                                                                                                           

                        # continue updating with effects
                        next_list+=nod.effects                                                      # determine effects
                        if v[0]==Next:                                                                   # next must update pointer
                            pname=Pointer+Obr+v[1][0]+Cbr
                            if pname in sv.Object: next_list+=[pname]

                    next_list=[x for x in next_list if x!=nom]                                # do not update same object twice

            if Verbose: print("xxxx Current value at", sv.Current_time, ":", nod.content(), Crlf)

        # continue updating with consequences
        start_list=noduplicate(next_list)                                         # fixed updating order
        if Random_update_order:
            shuffle(start_list)                                                             # random updating
##        else:
##             start_list=reorder(start_list)                                     # control order during debugging
           
        next_list=[]                                                                        # clear list of required updates
        if Verbose: print("xxxx next:", start_list, Crlf)
        
    filestore(sv)                                                                           # now store to file                                                       
    if count_iter>=Max_iter:
        warn("\n"+Warn_circular+"\n"+str(start_list), sv.Do_tests)     # warnings are fatal during tests

#===================================================== update_loop   
def update_loop(sv):
    """
    Process one time step
    """
    stlist=[]                                                                              # clear all changes
    if not istrue(sv.Object[Exit], sv.Current_time):
        io.keyscan()                                                                       # scan key input 
        pinscan(sv)                                                                        # scan pins before each time step 
        sv.delayed_list = nextevents(sv)                                         # reorder all delays (keys and pins are delayed)
    
    # first process new events that occurred 
    for nom in sv.Volatile:                                                       # volatiles are changed at least here
        # volatile objects are displayed outputs and implementations of 'lasted' (see whand_compile)
        # updatecond is not needed because clause is 'always'                                         
        if not (applied(nom, Output) or applied(nom, Command) or applied(nom, Write)) :
            sv.Object[nom].haschanged=True       
            sv.Object[nom].lastchange=sv.Current_time
            if sv.Graphic:  updatepanel(sv, nom)
            updateval(sv)                                                            # start updating process before all                            

    # process all delayed events within timestep before refreshing display and scanning inputs
    nextstep=sv.Current_time+Timestep                                # avoids time slippage within loop and guarantees updating 
    while sv.delayed_list and abs(sv.delayed_list[-1][0])-FloatPrecision<nextstep:  # process delayed event if within timestep   
        done= False                                                                  #  allow simultaneous delays       
        while sv.delayed_list and not done:                                 
            done=True                                                               
            evt=sv.delayed_list.pop()                                          # extract delayed event (earliest is last in the list)
            nexttime=abs(evt[0])                                                # delayed event time
            nom=evt[1]                                                              # delayed event name
            nod=sv.Object[nom]
            if nod.nature==Lst:                                                  
                print(Anom_trigger, nexttime, "s", nod.content(), "\n")   # "*** Anomaly: attempt to trigger a list ***   "
                raise ReferenceError
            
            advance_time(sv, nexttime)                                      # ADVANCE TIME HERE to delayed event

            if evt[0]>0:                                                                # ON event
                nod.value=[(sv.Current_time, None)]+nod.value  # make it the first delay in list                                                 
            else :                                                                         # OFF event
                nod.value=[(None, sv.Current_time)]+nod.value  # make it the first delay in list (supersedes ON)                                                 

            if applied(nom, Pin) or applied(nom, Key):               # process pins and keys as delayed events       
                sv.Pinstate[nom]=Vrai if istrue(nod, sv.Current_time) else Faux

            nod.haschanged=True                                              # mark object as changed                                       
            stt=istrue(nod, sv.Current_time)                               # new status 
            updatecond(sv, nom, st=stt)                                    # update condition       
            nod.lastchange=sv.Current_time                              # set change time 
            cleanup_delays(sv, nod)                                            # cleanup old delays in delayed_list
            fuse_delays(sv, nod)                                                  # reorder delays
            if sv.delayed_list and abs(sv.delayed_list[-1][0])<= sv.Current_time:
                done=False                                                           #  allow simultaneous delays
            
            if sv.Graphic and nom in sv.Visible and not nom in sv.Namedpinlist:       
                sv.interface.update(sv, nom)                                 # display on controlpanel                                                            

            updateval(sv)                                                             # update consequences of delayed event 

        sv.delayed_list = nextevents(sv)                                     # reorder all delays       
        if istrue(sv.Object[Exit], sv.Current_time): break            # EXIT

    if not sv.Graphic and not sv.Do_tests:                               # wait for clock 
        while (io.clock()-sv.t0)<sv.Current_time:           # do not anticipate. Avoid missing delayed Pins 
            pass                                                                           # wait
##    jitter()
            
##    io.keyscan()                                                                       # scan key input 
##    pinscan(sv)                                                                        # scan pins before each time step 
##    sv.delayed_list = nextevents(sv)                                         # reorder all delays (keys and pins are delayed)
    if len(sv.delayed_list)>len(sv.Object):
        print(Warn_multi_update, sv.Do_tests)                               # *** Warning: multiple updating ***                             
        
    advance_time(sv, nextstep)                                               # ADVANCE TIME to next time step 

#===================================================== advance_time
def advance_time(sv, newtime):
    if newtime>sv.Current_time:
        prepare_idem(sv)                                                          # make a copy for function idem before advancing time    
        sv.Current_time=newtime                                             # ADVANCE TIME HERE without slippage
        for n in range(1, len(sv.Condition)):
            sv.Condition[n]=0                                                     # reset all conditions to 0, except always at index 0

##    elif newtime<sv.Current_time-FloatPrecision:                                          # debugging
##        print (newtime, sv.Current_time, Crlf)
##        1/0
   
#===================================================== test_update
def test_update(sv):
    """
    run real time
    """
    init_outputs(sv)                                                                 # set all outputs to their initial status                                                           
    pinscan(sv)                                                                        # scan inputs and make them delayed events                                                               
    sv.delayed_list = nextevents(sv)                                         # prepare list of delayed events
    sv.Counter=0                                                                     # used to time short sections during debugging

    while not istrue(sv.Object[Exit], sv.Current_time):             # loop until exit
        while io.testpause()!=1:                                                 # check for pause: wait for 1   
            io.keyscan()
            if io.testpause()==2: raise KeyboardInterrupt           # abort from keyboard (Ctrl-C)
        update_loop(sv)                                                             # run program                                                            
        
    print("\n",End_prog, "\n")                                          
##    print("Counter", sv.Counter)
    print("Lasted", io.clock()-sv.t0+2*Epsilon_time)

#===================================================== updatepanel
def updatepanel(sv, nom):
    """
    update one value on graphic panel if appropriate
    object must be visible and not pin which has been named
    """
    if nom in sv.Visible and not nom in sv.Namedpinlist:
        sv.interface.update(sv, nom)                                                       
   
#===================================================== one_condition
def one_condition(sv, nam, c,v, num=0):                                                                       
    """
    Replace a condition with a table entry (index N). Condition c concerns object nam.
    Returns a number for the condition
    Makes a code for different types of conditions and make pointers from cause c
    sv.Condition_number[obj] is the list (coded) of clauses depending on cause c
    Here, only the current clause  is added to the list
    codes are 0, N-2^20, -N, +N and N+2^20 (BigNumber=2^20=1.048.576)
    for always, when change X, when end X, and when begin X, respectively
    For change of lists and dicts, make a direct pointer from each element to the condition for nam
    bypassing the list itself. Also increments effect list from element to nam when needed 
    if list changes at runtime, updating is performed, except for effect lists.
    """
    op=c[0]                                                               # op must be begin, end or change
    obj=None                                                           # name of a cause for object nam
    code=None                                                        # code depending on type of condition
    if op==Always:                                                    # only one condition for always
        condnum=0                                                    # index is 0, status 1, never updated
    else:
        condnum=num                                               # attribute a number to condition
        
        # bypass cached conditions
        x=applied(op, Change)                                   # op is a cache for change                       
        if x:
            op=Change
            c=(op, (x, None, None), None)                    # eliminate cache
        x=applied(op, Begin)                                       # op is a cache for begin                                  
        if x:
            op=Begin
            c=(op, (x, None, None), None)                    # eliminate cache
        x=applied(op, End)                                          # op is a cache for end                                    
        if x:
            op=End
            c=(op, (x, None, None), None)                    # eliminate cache
            
        # compute condition code
        obj=c[1][0] if c[1] else Faux                             # extract name of cause c (without op)
        if isnumber(obj) or isduration(obj): obj=Faux  # do not link constants
        if op==End: code=condnum                           # compute code depending on type of condition
        elif op==Begin: code=condnum+BigNumber
        elif op==Change: code=-condnum
        
        # create links 
        sv.Condition+=[0]                                           # expand condition logical state table
        if not obj in sv.Condition_number:                  # create key for cause if needed
            sv.Condition_number[obj]=[code]        
        elif not code in sv.Condition_number[obj]:     # avoid duplicates (slow 'in')
            sv.Condition_number[obj]+=[code]            # append code to dictionary for cause c
            
        # make direct links from lists (only condition change is allowed)
        if op==Change:
            nodX=sv.Object[obj]                                   # the cause object (without op)                                   
            if nodX.nature==Lst:                                   # list: each element may drive condition change
                if (obj, nam) in sv.All_conditions:                  
                    for ky, i in sv.All_conditions[(obj,nam)]: # revert prior shortcuts
                        sv.Condition_number[ky][i]=None  # make condition obsolete (do not distroy order)
                sv.All_conditions[(obj,nam)]=[]               # re-initialize revert pointers
                if sv.Object[obj].value:                            # extract list if not None
                    for elt in sv.Object[obj].value:             # make pointer for each element
                        ky=makekey(elt)                             # create a key as name  
                        if not ky in sv.Condition_number: sv.Condition_number[ky]=[]   # possible new object (e.g. from file)
                        if not code in sv.Condition_number[ky]: # avoid duplicates
                            sv.All_conditions[(obj,nam)]+=[(ky, len(sv.Condition_number[ky]))]  # keep pointers to revert shortcuts
                            sv.Condition_number[ky]+=[code]     # append code to dictionary for cause elt
                        if ky in sv.Object and not nam in sv.Object[ky].effects:      # slow 'in'
                            sv.Object[ky].effects+=[nam]             # update effects directly from element
    return condnum
        
#===================================================== updatecond
def updatecond(sv, nam, st=None, ch=False):               
    """
    directly update conditions if value of nam changes (see one_condition)
    st is None if status has not changed, True or False otherwise
    ch is False if value has not changed
    sv.Condition_number[nam] gives a list of all clauses involving nam
    with a specific code n for each type of condition (begin, end or change)
    Each clause is a single event
    sv.Condition gives the current status of this event
    """
    if nam in sv.Condition_number:                                                    
        li=sv.Condition_number[nam]
        if st is not None:                                                                        # status has changed
            for n in li:
                if n is not None:                                                                 # protect from obsolete conditions
                    if n<0:                                                                            # condition change
                        sv.Condition[-n]=1
                    elif n>BigNumber:                                                         # condition begin
                        if st is True: sv.Condition[n-BigNumber]=1            
                    elif n>0:                                                                         # condition end
                        if st is False: sv.Condition[n]=1                             
        elif ch:                                                                                       # value has changed
            for n in li:
                if n is not None:                                                                # protect from obsolete conditions
                    if n<0:                                                                           # condition change
                        sv.Condition[-n]=1

#===================================================== fuse_delays
def fuse_delays(sv, nod, res=None):                                    
    """
    updates delay list of event nod using res
    reduces delay list to a minimum, in particular when res is None
    preserves onsets when updating offsets
    """
    if nod.nature!=Bln:                                                                    # nod must be an event
        print("*** Anomaly in rt.fuse_delays: not a Bln", nod.content(), "\n")
        raise ReferenceError
    if res is not None and res.value is not None:                             #  v2.603
        dly=nod.value+res.value 
    else:
        dly=nod.value        # combine both lists
#    dly=nod.value+res.value if res is not None else nod.value        # combine both lists
    times=list(set([x[0] for x in dly if x and x[0] is not None]))         # ontimes without duplicates (also prior to current time)                                
    times+=list(set([-x[1] for x in dly if x and x[1] is not None and x[1]>=sv.Current_time]))  # offtimes with negative sign  
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
        if nod.value and nod.isdelayed:                             # exclude lists 
            for u,v in nod.value:
##                if u and u<sv.Current_time: print(sv.Current_time, nam,u,v)
                if u is not None and u>sv.Current_time:   
                    li+=[(u, nam)]                                           # store on events with positive sign
                if v is not None and v>sv.Current_time:   
                    li+=[(-v, nam)]                                          # store off events with negative sign
    li=list(set(li))                                                              # remove duplicates                                                          
    li.sort(key=lambda x: abs(x[0]), reverse=True)         # sort according to decreasing time
    return li

#===================================================== prepare_idem
def prepare_idem(sv):  
    """
    make a copy of every node required for function idem and update
    this is done before advancing time, which is why updating is tricky
    reinitialize change flag for all events
    """
    for nam in sv.Idem_list:                                                     
        copy=Idem+Obr+nam+Cbr                                                # name of the copy 
        cop=sv.Object[copy]                                                           # object copy
        nod=sv.Object[nam]                                                            # original object    
        nd.copynode2(nod, cop)                                                     # duplicate basic properties 
        if nod.lastchange==sv.Current_time:                                   # update change time of copy
            cop.lastchange=sv.Current_time
            cop.haschanged=True
        if nod.nature==Bln:                                                             # update event status of copy
            updatecond(sv, copy, st=istrue(cop, sv.Current_time))                       
        else:
            updatecond(sv, copy, ch=cop.haschanged)                    # update change of copy
            
##        # for lists, replace each element by its idem copy, recursively             
##        if type(cop.value)==list: deep_idem(sv, cop)                              
    for nod in sv.Object.values():
        nod.reuse=None                                                                  # reset reuse
        nod.isunstable=False                                                            
        
###===================================================== deep_idem
##def deep_idem(sv, cop):                                                                   
##    """
##    make a copy of every element in a list for function idem (recursive)
##    so, idem([element1, element2...]) will become [idem(element1), idem(element2)...] 
##    """
##    newlist=[]
##    for eltnam in cop.value:
##        ok=True
##        if type(eltnam)!=str:
##            ok=False                                                                   # do not reprocess numbers
##        elif isduration(eltnam):
##            ok=False                                                                   # do not reprocess durations
##        elif applied(eltnam,Idem):
##            ok=False                                                                   # do not reprocess Idem
##        elif not eltnam in sv.Object:
##            ok=False                                                                   # ignore new objects
##        elif len(sv.Object[eltnam].clauses)<=1:
##            ok=False                                                                   # ignore constants
##        if not ok:
##            newlist+=[eltnam]                                                     # element will be unchanged
##        else:
##            elt=sv.Object[eltnam]
##            copy2=Idem+Obr+eltnam+Cbr                                # Idem of this element
##            newlist+=[copy2]
##            cm.insert_node(sv, copy2)                                         # create copy if needed 
##            cop2=sv.Object[copy2]
##            nd.copynode2(elt, cop2)                                           # duplicate properties
##            if elt.lastchange==sv.Current_time:
##                cop2.lastchange=sv.Current_time
##                cop2.haschanged=True
##            if type(cop2.value)==list: deep_idem(sv, cop2)         # recurse
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

#===================================================== scanalog
def scanalog(sv, nb):
    """
    Read physical analog input on demand, returns value or None   
    """
    if isnumber(nb) and Special+Special+Measure+Obr+str(int(nb))+Cbr in sv.Object:   # !!! slow
        return io.getanalog(sv, nb, io.clock()-sv.t0)
    return None
    
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
        io.outmsg(sv, nb, noquotes(vl), time)

    li=applied(nom, Display)                                                    # arguments for display
    if li:
        vl=deep_get(sv, li, None) if li in sv.Object else splitlist(li)
        if len(vl)!=3 or not isnumber(vl[1]) or not isnumber(vl[2]):
            print(Err_syntax, vl, Crlf)
            raise ReferenceError
        vl[0]=noquotes(vl[0])
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
