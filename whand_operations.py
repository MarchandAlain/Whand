# -*- coding: ISO-8859-1 -*-
# standard modules
from math import sqrt, log10                                                   # 
from random import random, shuffle                                       # a few functions

# whand modules
import whand_io as io                                                               #  I/O module for drivers
import whand_compile as cm
from whand_operators import *                                                # from... import because module only contains constants
from whand_tools import *                                                        # useful procedures only

# special operations
"""
    The following functions each perform a non distributive elementary operation O between triplet A and triplet B
    sorted by alphabetical order of operators
    called by whand_runtime: evaluate
    Parameters
    ------------
    sv: an instance of the spell class (program unit) from whand_sharedvars.py
    tree: a triplet, e.g. (O, A, B)
    nom: the name of an object
    O: an operator from whand_operators
    A, B: triplets
    nodA, nodB: objects corresponding to A and B
    n1, n2: natures of nodA and nodB
    res: an object, result of the evaluation of nod
    Returns
    --------
    sv: an instance of the spell class (program unit) from whand_sharedvars.py
    res: an object, result of the evaluation of nod
    None: indicates no hidden changes    
"""
# ==================================================== do_call
def do_call(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):  
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
        args=get_node(sv, block).value                   # extracts argument list (make it an object)
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
        return sv, res, None                           # end evaluation

# ==================================================== do_cumul
def do_cumul(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):   # cumulative list            
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
        return sv, res, None                                                   # end evaluation

# ==================================================== do_have    
def do_have(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):  # extract keys of a dict              
        root=A[0]                                                               # name of the dict
        if root in sv.Object:
                if sv.Object[root].isdict:                                
                        li=[]                       
                        dictels=sv.Object[root].value                               # list of keys
                        if dictels:
                                nb=len(root)+1                                              # to remove the root part
                                for elt in dictels:
                                    block=makekey(elt[nb:-1])                          # extract key
                                    if not block in [None, ""] : li+=[block]          
                                res.value=li
                else:
                        size=len(sv.Object[root].value)
                        res.value=[i+1 for i in range(size)]
        return sv, res, None                                                    # end evaluation    

# ==================================================== do_next
def do_next(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):            
        nodA=sv.Object[A[0]]
        vl=nodA.value
        if type(vl)==list and vl:                                          # only if list is initialized and not empty               
            if  nodA.lastchange!=sv.Current_time:                # only once per time step
                ptr=nodA.pointer
                ptr=1+(int(ptr) % len(vl))                               # cyclic index 
                el=vl[ptr-1]
                if type(el)==list:
                    res.value=el
                    res.nature=Lst
                else:
                    cop=get_node(sv, el)                                 # using get_node directly may not work
                    nd.copy_node2(sv, cop.name, res)
                nodA.pointer=ptr                                          # this is where pointer is updated                                  
                nodA.lastchange=sv.Current_time                 # mark as changed in this time step
        return sv, res, None                                                   # end evaluation   

# ==================================================== do_pointer    
def do_pointer(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):        
        nodA=sv.Object[A[0]]
        ptr=nodA.pointer
        res.value=ptr                                                           # cached value
        return sv, res, None                                                      # end evaluation    
    
# ==================================================== do_steps    
def do_steps(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):   # differential list
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
        return sv, res, None                                                   # end evaluation

# ==================================================== do_text    
def do_text(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res): 
        vl=nodA.value
        if vl is not None:
            if n1==Drtn: res.value=str(seconds(vl))+Unit_sec  # convert delay to seconds
            else: res.value=buildtext(sv, vl)                        # make text
        return sv, res, None                                                 # end evaluation

# ========================================================
# Normal operations
"""
    The following functions each perform a possibly distributive elementary operation O between values v1 and v2
    sorted by alphabetical order of operators
    called by whand_runtime: evaluate
    Parameters
    ------------
    sv: an instance of the spell class (program unit) from whand_sharedvars.py
    O: an operator from whand_operators
    v1, v2: values to combine, extracted by whand_runtime: prepareval
    Returns
    --------
    a value, depending on the type of operation, or None    
"""
# ======================================================== 
def do_absv(sv, O, v1, v2):                                                                                              # absv
        if type(v1) in [int, float]: return abs(v1)                   
        warn("\n"+Warn_invalid_nb+" "+str(v1)+"\n", sv.Do_tests)                # warning, not error
        return None

# ======================================= 
def do_add(sv, O, v1, v2):                                                                                                  # add
        if v2 is None: v2=[]                                        
        if v1 is None: v1=[]                                        
        if type(v1)==tuple: v1=Vrai if logic(v1, sv.Current_time) else Faux       # get logical value 
        elif type(v1)!=list: v1=get_node(sv, v1).value                                      # get list                                                   
        if type(v2)==tuple: v2=Vrai if logic(v2, sv.Current_time) else Faux       # get logical value       
        elif type(v2)!=list : v2=get_node(sv, v2).value                                     # get list                                      
        if type(v1)==list and type(v2)==list: return v1+v2                              # concatenate lists
        elif type(v1)==list: return v1+[v2]                                                      # add last element
        elif type(v2)==list: return [v1]+v2                                                      # add first element
        return None
    
# ======================================= 
def do_alea(sv, O, v1, v2):                                                                                                    # alea 
        if type(v1) in [int, float] and v1>=0:
            return [random() for i in range(int(v1))]
        warn("\n"+Warn_empty_alea+" "+v1+"\n", sv.Do_tests)                 # warning, not error
        return None
    
# ======================================= 
def do_all(sv, O, v1, v2):                                                                                                # all
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
                    
# ======================================= 
def do_and(sv, O, v1, v2):                                                                                           # and
        v1=logic(v1, sv.Current_time)
        v2=logic(v2, sv.Current_time)
        if v1 is True and v2 is True: return True
        if v1 is None or v2 is None: return None                                              
        return False                                        # at least one arg must be not None
    
# ======================================= 
def do_any(sv, O, v1, v2):                                                                                            # any
        v1=deep_get(sv, v1, Value)   # needed because by default deep_get does not extract event times
        if type(v1)==list:
            for x in v1:
                if type(x)==tuple:
                    st=logic(x, sv.Current_time)
                    if st: return True
        return False

# ======================================= 
def do_begin(sv, O, v1, v2):                                                                                            # begin
        v1=v1[0]                                                                                                                        
        return v1
    
# ======================================= 
def do_change(sv, O, v1, v2):                                                                                     # change
        return v1 if sv.Current_time>0 else None                    # no change at start      
    
# ======================================= 
def do_compare(sv, O, v1, v2):
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
               
# ======================================= 
def do_count(sv, O, v1, v2):                                                                                            # count
        if type(v1)==int: return v1
        if type(v1)==list: return len(v1)
        return None

# ======================================= 
def do_div(sv, O, v1, v2):                                                                                              # div
        if v2: return v1/v2           
        if v2==0: warn("\n"+Warn_div_zero+" "+str(v1)+"/0\n", sv.Do_tests)                    # warning, not error
        return None                                                         # no error if divide by zero or None
        
# ======================================= 
def do_end(sv, O, v1, v2):                                                                                          # End
        v1=v1[1] if sv.Current_time>0 else None                    
        return v1

# ======================================= 
def do_find(sv, O, v1, v2):                                                                                           # find
        v1,v2=v2,v1                                                       # switch args: list is v2
        if v1 is not None and v2 is not None:
            if type(v1)==tuple and type(v2)==list:         # find Bln v1 in a list 
                v1=logic(v1, sv.Current_time)                   # get status
                for vl, x in enumerate(v2):
                    x=get_node(sv, x).value                         # get value from name
                    if type(x)!=list or not x:                         # empty value not allowed
                        print(Anom_find, v2, x)             # "*** Anomaly Find: non Bln in list"
                        raise ReferenceError
                    x=logic(x[0], sv.Current_time)               # get status
                    if x==v1: return vl+1                             # found
            else:
                v1=get_node(sv, v1).value                          # get value from v1 name
                for vl, v in enumerate(v2):                         # match by value
                    x=get_node(sv, v).value
                    if x==v1: return vl+1                             # found
                    if type(x) in [int, float] and type(v1) in [int, float]:    
                        if abs(x-v1)<FloatPrecision:               # approximate
                            return vl+1
        return 0                                                              # not found
    
# ======================================= 
def do_hasvalue(sv, O, v1, v2):                                                                                   # hasvalue
        return ( v1 is not None )

# ======================================= 
def do_intg(sv, O, v1, v2):                                                                                          # intg
        if type(v1) in [int, float]: return float(int(v1))                  
        warn("\n"+Warn_invalid_nb+" "+str(v1)+"\n", sv.Do_tests)                 # warning, not error
        return None
                
# ======================================= 
def do_inter(sv, O, v1, v2):                                                                                          # inter
        if type(v1)==list and len(v1)>1:                          # uses occur attribute
            return v1[-1]-v1[-2]                            
        return None                                 

# ======================================= 
def do_isnot(sv, O, v1, v2):
        yes=False
        if coincide(v1, v2):
                yes=True                      # simple comparison
        else:
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
                                            if coincide(v, v2): yes=True   # name or value matches      
                                            n=v if n!=v else None       # get deeper value
                                            if type(n)==list: break      # value should not be a list
        return yes if O==Is else not yes
    
# ======================================= 
def do_isin(sv, O, v1, v2):                                                                                                                     # isin
        if v1 is not None and v2 is not None:
            if type(v1)==tuple and type(v2)==list:                  # match by logical status 
                v1=logic(v1, sv.Current_time)                            # get status
                for vl, x in enumerate(v2):
                    x=get_node(sv, x).value                                  # get value from name
                    if type(x)!=list or not x:                                  # empty value not allowed
                        print(Anom_isin, v2, x)                   # "*** Anomaly Isin: non Bln in list"
                        raise ReferenceError
                    x=logic(x[0], sv.Current_time)                        # get status
                    if x==v1: return True
            else:                                                                       # match by value
                for vl, x in enumerate(v2):
                    x=get_node(sv, x).value
                    if coincide(x, v1): return True
        return False

# ======================================= 
def do_itis(sv, O, v1, v2):
        v1=no_quotes(v1)
        # process time of day
        if isduration(v1): v1=seconds(v1)
        if isnumber(v1) or type(v1)==float: v1=int(v1)
        if type(v1)==int:
            now=(3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec)
            if 0<=v1<24*3600: return True if coincide(v1, now) else False                    
            print(Err_Val, Itis, v1)
            raise ReferenceError
        # else must be a string
        if type(v1)!=str:
            print(Err_Val, Itis, v1)
            raise ReferenceError
        # process weekday
        if v1 in Wday:
            return True if v1== Wday[io.localtime().tm_wday] else False
        # process date
        v1=change_all(v1, Space+Space," ")           # format is like "may 23", "may23" or may23
        tu=tuple(v1.split(Space))
        if len(tu)==1:                                             # no space
            tu=v1[:-1],v1[-1]                                    # split before last
            if tu[0][-1] in ["0","1","2","3"]:                 # split before second last
                tu=v1[:-2],v1[-2:].lstrip("0")
        elif len(tu)!=2:
            print(Err_Val, Itis, v1)
            raise ReferenceError
        vmon, vdn=tu
        if not vmon in Month or not isnumber(vdn) or not 0<int(vdn)<=Mndays[Month.index(vmon)] :
            print(Err_Val, Itis, v1)
            raise ReferenceError
        v1=vmon+vdn
        mon=Month[io.localtime().tm_mon-1]      
        dn=io.localtime().tm_mday                      
        now=mon+str(dn)
        return True if coincide(v1, now) else False
    
# ======================================= 
def do_lasted(sv, O, v1, v2):                                                                                        # lasted
        if type(v1)==tuple:                     
            if logic(v1, sv.Current_time): return sv.Current_time-v1[0]               # duration since onset           
        return 0                                 
        
# ======================================= 
def do_listfind(sv, O, v1, v2):                                                                                          # listfind
        v1,v2=v2,v1                                                       # switch args: list of lists is v2
        v1=get_node(sv, v1).value                                  # get value from v1 name
        for vl, v in enumerate(v2):                                  # match by value
            x=get_node(sv, v).value
            if x==v1: return vl+1                                     # found
        return 0                                                              # not found
    
# ======================================= 
def do_load(sv, O, v1, v2):                                                                                                                    # load    
        if type(v1)!= str:
            print("\n", Anom, Load,"'"+str(v1)+"' ***")                             
            raise ReferenceError
        v1=no_quotes(v1)                                             # remove quotes from filename
        v1=addparentdir(v1)                                       # complete path        
        try:
            brut=io.readtextfile(v1)                    
        except IOError:                                                # error opening or reading file
            print("\n", Err_404, str(v1), "\n")                                    
            raise ReferenceError
        li=[]                                                                  # split text into lines
        li=brut.split(Crlf)
        for i,expr in enumerate(li):                               # look for list in each line
            expr=expr.strip(Space)                                            
            li[i]=expr
            if detectlist(expr):                                                    
                expr=no_brackets(expr)                           # remove brackets
                li[i]=expr.split(Comma)                           # convert text to list
        if li[-1]=='' or li[-1]==Comma: li=li[:-1]          # remove trailing bits
        return li

# ======================================= 
def do_logd(sv, O, v1, v2):                                                                                             # logd  
        if type(v1) in [int, float] and v1>0: return log10(v1)                   
        warn("\n"+Warn_log_neg+" "+str(v1)+"\n", sv.Do_tests)                    # warning, not error
        return None

# ======================================= 
def do_match(sv, O, v1, v2):                                                                                                          # match 
        # not distributive: use '=' or 'is' instead                 
        if coincide(v1, v2): return True                               
        if type(v1)!=list or type(v2)!=list: return False     
        if len(v1)!=len(v2): return False                           
        for c,d in zip(v1,v2):                                     # deep matching (1 level)
            a,b=c,d                                                    # preserve initial lists
            if type(c)==list:                                        # element is a list
                a=c[:]
                for i, x in enumerate(a):                       # look into list
                    a[i]=get_node(sv, x).value                 # get value from name
            if type(d)==list:                                        # element is a list
                b=d[:]
                for i, x in enumerate(b):                       # look into list
                    b[i]=get_node(sv, x).value                 # get value from name
            if not coincide(a,b): return False
        return True                                                                                                   

# ======================================= 
def do_measure(sv, O, v1, v2):                                                                                     # measure 
        return scanalog(sv, v1)
    
# ======================================= 
def do_minus(sv, O, v1, v2):                                                                                         # minus
        return v1-v2

# ======================================= 
def do_mult(sv, O, v1, v2):   
            return v1*v2                                                                       # mult

# ======================================= 
def do_name(sv, O, v1, v2):                                                                                       # node attribute: name                                                        
        return '"'+str(v1)+'"'                                           # add quotes

# ======================================= 
def do_not(sv, O, v1, v2):                                                                                           # not
        v1=logic(v1, sv.Current_time)
        if v1 is True: return False
        if v1 is False: return True
        return None              
    
# ======================================= 
def do_occur(sv, O, v1, v2):                                                                                      # node attribute: occur     
        return v1[:]

# ======================================= 
def do_or(sv, O, v1, v2):                                                                                           # lazy 'Or' 
        v1=logic(v1, sv.Current_time)
        if v1 is True: return True 
        v2=logic(v2, sv.Current_time)
        if v2 is True: return True
        if v1 is None or v2 is None: return None                 
        return False                                             # only if both args are not None

# ======================================= 
def do_order(sv, O, v1, v2):                                                                     # order, sequence
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
                    for ti in occ[:-v1.count(evt)]:                    #  occur in wndow
                        if ti>tim[0] and ti<tim[-1]: return False
        tim2=tim[:]
        tim2.sort()
        if tim2==tim:
            return True                                                       # check order                              
        return False  

# ======================================= 
def do_pick(sv, O, v1, v2):                                                                                                 # pick
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
                y=get_node(sv, y).value                 # extract logical value from name
                if type(y)==list and y: y=y[0]        # first tuple from list gives current status
            if type(y)!=tuple:    
                print("\n", Err_arg_nat, Pick, y)
                raise ReferenceError
            if logic(y, sv.Current_time): li+=[x]   # add element if true in mask
        return li

# ======================================= 
def do_plus(sv, O, v1, v2):                                                                                     # plus
        # avoid creating a delayed object after the initial event has ended
        if type(v1)!= tuple:                                                                             # number or delay
            return v1+v2
        else:                                                                                                   # delayed event
            x=v1[0]
            y=v1[1]
            if x is not None: x+=v2                                                                 # on time 
            if y is not None and y!=0: y+=v2                             # 'false' at start: do not delay 
            return [(x,y)]

# ======================================= 
def do_powr(sv, O, v1, v2):                                                                                              # powr  
        if type(v1) in [int, float] and type(v2) in [int, float] \
           and (v1>=0 or v2.is_integer()): return pow(v1, v2)                   
        warn("\n"+Warn_compute_power+" "+ str(v1)+ " ^ "+ str(v2)+"\n"+" "+str(v1)+"\n", sv.Do_tests)  # warning, not error
        return None
      
# ======================================= 
def do_proba(sv, O, v1, v2):                                                                                         # proba     
        return True if (random()<v1) else False
    
# ======================================= 
def do_ramp(sv, O, v1, v2):                                                                                         # ramp
        if type(v1) in [int, float] and v1>=0:
            return list(range(int(v1+1)))[1:]                      #  works also for empty ramp
        return None
    
# ======================================= 
def do_read(sv, O, v1, v2):                                                                                           # read 
        return io.readmessage(sv, v1)

# ======================================= 
def do_shuffle(sv, O, v1, v2):                                                                                            # shuffle 
        if type(v1)==list:
            li=list(v1)
            shuffle(li)                                                                                              # do not change original
            return li
        return None
    
# ======================================= 
def do_since(sv, O, v1, v2):                                                                                         # since (not evt)
        if v1 is None or type(v2)!=tuple:                           # v2 expects event times
            return False
        toff=v2[1]                                                              # off time
        if toff is None:
            return False                                                       # no event or still true
        ok=sv.Current_time>(toff+v1) or coincide(sv.Current_time , (toff+v1)) 
        return ok                                                              # False also with None                                                                  
    
# ======================================= 
def do_sort(sv, O, v1, v2):                                                                                             # sort
        v,w=v1,v2
        if v is None: v=v2[:]                                # accept a single arg
        if v is None or w is None: return None   # do not sort None
        if w==[]: return v                                   # do not sort if no key
        if type(v)!=list or type(w)!=list:               # check args are lists            
            print("\n", Anom_comput, O, v1, v2)                           
            raise ReferenceError
        v=v[:]                                                      # make a copy of lists
        w=w[:]
        keyisbool=False                                      # maybe sort by logical value 
        z=[]                                                         # create list of logical values if needed
        for y in w:
            if type(y)!=tuple:                                 
                y=get_node(sv, y).value                   # extract logical value from second arg
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
       
# ======================================= 
def do_sqrt(sv, O, v1, v2):                                                                                              # sqrt
        if type(v1) in [int, float] and v1>=0:
            return sqrt(v1)                   
        warn("\n"+Warn_sqrt_neg+" "+str(v1)+"\n", sv.Do_tests)                    # warning, not error
        return None

# ======================================= 
def do_time(sv, O, v1, v2):                                                                                                                     # time  
        tm=None
        if type(v1)==tuple and v1[0] is not None:                                 
            beg=v1[0]+1                                           # correction
            now=3600*io.localtime().tm_hour+60*io.localtime().tm_min+io.localtime().tm_sec
            tm=now+beg-sv.Current_time
##            tm=io.clock()%(3600*24)+beg-sv.Current_time                                                 
        return tm

# ======================================= 
def do_to(sv, O, v1, v2):                                                                                                     # to
        if type(v1)==list and type(v2)==list:
            if v1[-1] is not None and v2[-1] is not None: return v2[-1]-v1[-1]
##        if type(v1)==tuple and type(v2)==tuple:                                         
##           if v1[0] is not None and v2[0] is not None: return v2[0]-v1[0]                     
        return None                                 
    
# ======================================= 
def do_touch(sv, O, v1, v2):                                                                                        # touch
        if v1:
            filename=v1[0]
            X=v1[1]
            Y=v1[2]
            res=io.readtouch(sv, filename, X, Y)
        else:
            res=io.readtouch(sv, None, 0, 0)
        if res is None: return None
        return [res[0], res[1], Vrai if res[2] else Faux]
    
# ======================================= 
def do_value(sv, O, v1, v2):                                                                    # node attribute        
        return v1

# ======================================= 
def do_within(sv, O, v1, v2):                                                                                                                    # within
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
        
# ==================================================== Specially_evaluated
# dict to special operations without distributivity
special_evaluation={Next: do_next, Pointer: do_pointer, Have: do_have, 
                     Cumul: do_cumul, Steps: do_steps, Text: do_text, Call: do_call}

#===================================================== normal_evaluation
# dict to normal operations
normal_evaluation={Absv: do_absv, Add: do_add, Alea: do_alea, All: do_all, And: do_and, Any: do_any, Begin: do_begin,
        Change: do_change, Count: do_count, Div: do_div, End: do_end, Equal: do_compare, Find: do_find,
        Greater: do_compare, Grequal: do_compare, Hasvalue: do_hasvalue, Inter: do_inter, Intg: do_intg,
        Is: do_isnot, Isin: do_isin, Isnot: do_isnot, Itis: do_itis, Lastchange: do_value, Lasted: do_lasted,
        Listfind: do_listfind, Load: do_load, Logd: do_logd, Match: do_match, Measure: do_measure,
        Minus: do_minus, Mult: do_mult, Name: do_name, Nequal: do_compare, Not: do_not, Occur: do_occur,
        Or: do_or, Order: do_order, Pick: do_pick, Plus: do_plus, Powr: do_powr, Proba: do_proba,
        Ramp: do_ramp, Read: do_read, Sequence: do_order, Shuffle: do_shuffle,
        Since: do_since, Smaller: do_compare, Smequal: do_compare, Sort: do_sort, Sqrt: do_sqrt,
        Time: do_time, To: do_to, Touch: do_touch, Value: do_value, Within: do_within}

# ==================================================== evaluate_special
def evaluate_special(sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res):
    """
    calls one of the special evaluation functions, using dictionary special_evaluation
    """
    args=sv, tree, nom, O, A, B, nodA, nodB, n1, n2, res
    return special_evaluation[O](*args)                                 # end evaluation    

#===================================================== normal_operation
def evaluate_normal(sv, O, v1, v2):                       
    """
    calls one of the normal evaluation functions, using dictionary normal_evaluation
    """
    # some empty args do not prevent evaluation
    if v1 is None and not O in [Or, Hasvalue]: return None                        # lazy 'Or'
    if (v1==[] and not O in {Count, Add, Match, Within, Pick, Sort, Find, Touch}): return None          
    if (v2==[] or v2 is None) and not O in Unary and not O in {Or, Add, Match, Within, Isin, Pick, Sort}: return None   

    if O in [And, Or, Not] and type(v1)==list:             # logical op: lists are not allowed
            print(Anom_logic, v1)                                 # *** Anomaly in rt.op: not a Bln logic value
            raise ReferenceError       
    
    try:
        return normal_evaluation[O](sv, O, v1, v2)                           # end evaluation    
    except KeyError:
        print("\n", Err_imposs_oper)                                                # impossible operation              
        print([O], Obr, v1, Comma, v2, Cbr)
        raise ReferenceError

# ==================================================== get_node
def get_node(sv, expr):                       
    """
    return a node with current value of nom, creates node once
    """
    if expr is None or expr=="":
        return sv.Object[Faux]                               

    nom=str(expr)                 
    
    if nom in sv.Object:                                                      # use existing node 
        return sv.Object[nom]

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

    if detectlist(no_brackets(nom)):                                     # create and link list                    
        li=splitlist(no_brackets(nom))
        res=insert_node(sv, nom, causelist=li, setto=None, always_update=False)
        res.value=li
        res.nature=Lst[:]
        
    else:                                                                             # a state or the copy of a node
        res=cm.add_object(sv, nom)
        if not nom.startswith(Special):                                # not a copy of a node
            res.nature=Stt[:]
            res.value=nom

    return res

#===================================================== insert_node
def insert_node(sv, nam, causelist=[], setto=None, always_update=False):  
    """
    create a new node and link it if necessary (done once)
    """
    if nam in sv.Object:                                        
        return sv.Object[nam]                                               # do not create 
    else:
        gli=nd.Node()                                                           # create node
        gli.name=nam 
        sv.Object[nam]=gli                                                   # add name to object dict (not ordered) 
        sv.Object_list.append(nam)                                      # add name to object list (ordered)                         
        # make clauses                                                              
        if always_update:
            gli.clauses=[((Always, None, None),setto)]           # n.b. dangerous after start because then clauses are numbers
                                                                                         # but this parameter is not used at runtime 
        # update causes                                                            
        if causelist:                                                                # use provided causes
            for nom in causelist:
                if nom in sv.Object:
                    if not nom in gli.causes: gli.causes+=nom    # link causes
                    nod=sv.Object[nom]
                    if not nam in nod.effects: nod.effects+=[nam]   # link effects

        # update glitches                                                           
        for op in Glitch_list:                                                             
            glitchname=op+Obr+nam+Cbr                            # begin, end, change                             
            if glitchname in sv.Object:            
                gli=sv.Object[glitchname]
                if not nam in sv.Glitches: sv.Glitches[nam]=[]     
                sv.Glitches[nam]+=[(op, glitchname, gli)]
        
        return gli

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
            st+=no_quotes(str(y))+Comma                    # add element to list
        st=st[:-1] if st and st[-1]==Comma else st      # remove last comma
        return Obr+st+Cbr if bracketflag else st
    return Quote+no_quotes(str(vl))+Quote              # not a list

#===================================================== deep_get
def deep_get(sv, nom, attr=None):                               
    """
    extract values of a list of objects or attributes from the name
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

#===================================================== scanalog
def scanalog(sv, nb):
    """
    read physical analog input on demand, returns value or None   
    """
    if isnumber(nb) and Special+Special+Measure+Obr+str(int(nb))+Cbr in sv.Object:   # !!! slow
        return io.getanalog(sv, nb, io.clock()-sv.t0)
    return None

#===================================================== TESTS
if __name__=="__main__":
    pass






