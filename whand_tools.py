# this module contains only functions that take arguments and return values
# because they are imported as * they should not change shared variables
import os
import re
from whand_parameters import *  # options, constants
from whand_operators import *   # from... import because module only contains constants
import whand_nodes as nd

Dic_tree_join={}                               # dictionaries to accelerate computations and searches                      
Dic_brackets={}                              # results are stored and retrieved, rather than recomputed    
Dic_quotes={}                                    
Dic_applied={}                                    
Dic_blocks={}

#===================================================== tree_join
def tree_join(tree):
    """
    builds a string line from binary tree (no outer brackets) made of
    triplet of nodes (op, b1, b2) with op=string and b1, b2 nodes (or None)
    for lists triplets are (comma, [list], None)
    uses a dictionary when possible for faster runtime
    Parameters
    ------------
        tree: a triplet representing an expression
    Returns
    --------
        txt: a string representing a name for the expression
    """
    if tree is None: return ""                                               # empty tree
    op,t1,t2=tree                                                                # decompose tree 
    if t1 is None and t2 is None:                                        # simple node: return op name
        return op

    # Comma 
    if op ==Comma:                                                          # a list (not hashable)
        li=[tree_join(x) for x in t1]                                          # list elements RECURSIVE
        txt=Comma.join(li)
        if len(li)==1: txt+=Comma                                       # comma if single element
        return Obr+txt+Cbr                                                 # (elt1, elt2, ...)

    # has result been computed before
    try:                                                    
        if tree in Dic_tree_join:
            return Dic_tree_join[tree]                                      # retrieve from dict when possible        
        can_hash=True                                                       # tree is hashable
    except TypeError:
        can_hash=False                                                      # unhashable type
    
    term1=tree_join(t1)                                                      # recursive call for terms
    term2=tree_join(t2)
    
    # Special (subscripting) 
    if op ==Special:                                                          # used for subscripting lists, dicts or attributes
        txt=term1+Obr+no_brackets(term2)+Cbr                # term1(term2)     

    # Bracketed block
    elif op==Obr:                                                             # brackets (disambiguating)
        if t2:
            print("\n", Anom_text_after_block, Obr+no_brackets(term1)+Cbr+term2)  # no second term allowed
            raise ReferenceError
        txt=Obr+no_brackets(term1)+Cbr                           # (term1)                           
        
    # other   
    elif not t2:                                                                  # unary operator: no second term
        txt=op+Obr+no_brackets(term1)+Cbr                     # op(term1)

    else:
        if op in Alphakwords: op=Underscore+op+Underscore   # special spacing for expression names    
        txt=term1+op+term2                                              # term1 op term2   (no brackets)

    if can_hash: Dic_tree_join[tree]=txt                                 # save result for later          
    return txt                                                              

##===================================================== warn
def warn(text, fatal=False):
    """
    display warnings according to Warnings option and autotest option
    Parameters
    ------------
        text: a string, error or warning message
        fatal: a Boolean, abort if True
    Returns
    --------
        None
    """
    if Warnings or fatal:
        print(text)
    if fatal: raise ReferenceError                                   

#===================================================== is_glitch
def is_glitch(expr):
    """
    detects expressions change(objectname), begin(objectname) or end(objectname)
    glitchname is change, begin or end
    Parameters
    ------------
        expr: a string representing an expression
    Returns
    --------
        a tuple (glitchname, objectname), or None if not a glitch
    """
    for gl in Glitch_list:                                                                # [Change, Begin, End]
        nam=applied(expr, gl)                                                       # applied returns objectname
        if nam: return gl, nam       
    return None

#===================================================== get_nature
def get_nature(sv, expr, hint=All_natures[:]):
    """
    detects and returns nature of expr if obvious and compatible with nt 
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        expr: a string representing an expression
        hint: a list representing possible natures
    Returns
    --------
        newnat: a list representing possible natures 
    """
    nat=All_natures[:]                                          
    if expr is None or expr=="": return nat                                         # empty object: nature unknown

    if expr in sv.Object:                                                                      # is object is known                                         
        nod=sv.Object[expr]
        nat= nod.nature                                                                      # retrieve object info 
        if nod.isdelayed: nat=Bln[:]          
        
    if expr in [Exit, Controlpanel]: nat=Bln[:]                                       # use object itself        
    elif isnumber(expr): nat=Nmbr[:]                                                  # a plain number
    elif isduration(expr): nat=Drtn[:]                                                   # a plain delay
    elif detectlist(expr): nat=Lst[:]                                                       # a plain list
    elif expr.startswith(Output+Obr): nat=Bln[:]                                  # logical output (event)
    elif expr.startswith(Pin+Obr): nat=Bln[:]                                        # logical input (event)
    elif expr.startswith(Key+Obr): nat=Bln[:]                                       # character key (event)   
    elif expr[0]==Quote and expr[-1]==Quote : nat=Stt[:]                  # quoted text (state) 
    elif is_glitch(expr):                                                                       # begin, end or change
        nat=Bln[:]                                                                               # a list only if object itself may be a list
        if Lst[0] in get_nature(sv, is_glitch(expr)[1]): nat+=Lst                                                                             
    
    elif expr==Number: nat=Nmbr[:]                                                 # by definition           
    elif expr==Delay: nat=Drtn[:]                              
    elif expr==Ewent: nat=Bln[:]
    elif expr==State: nat=Stt[:]
    elif expr==List: nat=Lst[:]
               
    elif expr.startswith(Special) and expr[1:] in sv.Object:                    # copy of existing object
        nat=sv.Object[expr[1:]].nature

    elif applied(expr, Store): nat=Lst[:]                                                       
    elif applied(expr, Cumul) or applied(expr, Steps): nat=Lst[:]          # these functions work element by element
    elif Cumul+Obr+expr+Cbr in sv.Object or Steps+Obr+expr+Cbr in sv.Object: nat=Lst[:]

    newnat=list(set(hint) & set(nat))                                                 # check consistency
    if not newnat:            
            print("\n", Err_inconsistent_nat)                                          # *** Error in get_nature: inconsistent nature ***         
            print(expr, hint, nat)
            raise ReferenceError
    return newnat

#===================================================== coincide
def coincide(t1, t2):                                                          
    """
    Verifies equality of expressions (within float error range)
    FloatPrecision constant is defined in whand_parameters.py
    Quotes around strings are ignored
    Parameters
    ------------
        t1, t2: values
    Returns
    --------
        a Boolean, True or False 
    """
    if t1==t2: return True                                                                  # no difference
    if no_quotes(t1)==no_quotes(t2): return True                                 # (do not move this line)             
    if isnumber(t1): t1=float(t1)                                                         # compare numbers   
    else: return False                                              
    if isnumber(t2): t2=float(t2)
    else: return False                                        
    if abs(t2-t1)<=FloatPrecision: return True                                     # float error range
    return False
    
#===================================================== no_brackets
def no_brackets(expr):
    """
    remove brackets around a block (recursively if several layers)
    much faster when using the dict   
    Parameters
    ------------
        expr: a string representing an expression
    Returns
    --------
        result: a string representing an expression without outer brackets
    """
    result=expr.strip(Space)
    try:
        if expr in Dic_brackets:
            return Dic_brackets[expr]                                    # retrieve already computed
        
        if result and result[0]==Obr and result[-1]==Cbr:    # brackets found
            first, block,last=findblock(result)                         # is it a bracketed block
            if first==0 and last==len(result):
                result=no_brackets(result[1:-1])                      # RECURSIVE
            
        Dic_brackets[expr]=result                                       # save result for later    
    except TypeError:
        pass
    return result
       
#===================================================== no_quotes
def no_quotes(expr):
    """
    remove quotes around a text if none are present inside
    much faster when using the dict   
    Parameters
    ------------
        expr: a string representing an expression
    Returns
    --------
        result: a string representing an expression without outer quotes
    """
    result=expr
    try:
        if expr in Dic_quotes:
            return Dic_quotes[expr]                     # retrieve already computed
        
        if expr and expr[0]==Quote and expr[-1]==Quote and not Quote in expr[1:-1]:
            result=expr[1:-1]                              # no inner quotes allowed

        Dic_quotes[expr]=result                       # save result for later
    except TypeError:
        pass
    return result

#===================================================== change_all
def change_all(expr, old, new):
    """
    replaces all occcurrences even if new ones are formed in the process
    Parameters
    ------------
        expr: a string representing an expression
        old, new: strings
    Returns
    --------
        expr: a string where substrings old have been replaced by new
    """
    while old in expr:
        expr=expr.replace(old, new)
    return expr

#===================================================== no_duplicate
def no_duplicate(seq):
    """
    List unique elements while preserving order
    stores values in set for faster lookup
    Parameters
    ------------
        seq: a list
    Returns
    --------
        a list of unique elements in order of appearance
    """
    seen = set()
    seen.clear()                                                     # make sure nothing remains
    return [x for x in seq if not (x in seen or seen.add(x))]

#===================================================== fromlist   
def fromlist(sv, expr):
    """
    checks whether expr has form  'root(block)' and is a list and extracts root (list or dict)
    much faster when using the dict sv.Elements 
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        expr: a string
    Returns
    --------
        part of expr before first bracket (empty string if none)
    """
    if expr in sv.Elements: return sv.Elements[expr]                  # retrieve already computed 
    root=""
    if expr[-1]==Cbr and Obr in expr:                     
        here, block, there=findblock(expr)        # checks whether expr has form  'root(block)'
        if there==len(expr):
            x=expr[:here]
            if x in sv.Object : root=x                                            # do not extract functions      
    sv.Elements[expr]=root
    return root

#===================================================== applied   
def applied(expr, root):
    """
    checks whether expr has form  'root(block)' and extracts block     
    much faster when using the dict   
    Parameters
    ------------
        expr: a string
        root: a string to look for
    Returns
    --------
        part of expr between brackets
    """
    if expr=="": return ""
    applied=""
    if expr[-1]==Cbr and expr.startswith(root+Obr):
        if expr in Dic_applied: return Dic_applied[expr]                  # retrieve already computed     
        here, block, there=findblock(expr)            # checks whether expr has form  'root(block)'
        if there==len(expr):
            applied=block
        Dic_applied[expr]=applied               # for some unclear reason, do not store all strings                
    return applied

#===================================================== findblock
def findblock(expr):
    """
    find first block enclosed in corresponding brackets (ignores internal blocks)
    much faster when using the dict   
    Parameters
    ------------
        expr: a string
    Returns
    --------
        a t-uplet:
            position of opening bracket
            a string: block (without brackets)
            position of closing bracket + 1 i.e. len(expr) if last char
            or (-1,"",-1) if no block found
    """
    if expr in Dic_blocks: return Dic_blocks[expr]
    level=0                                           # bracket level
    quot=0                                           # quote level
    for here,c in enumerate(expr):
        if c==Quote: quot=1-quot
        if quot==1:                                # ignore anything between quotes
            continue
        if c==Obr:                                  # open block 
            level+=1
            if level==1:                            # first level brackets only
                position=here+1                # store first position
        elif c==Cbr:                               # close block
            level-=1
            if level==0:                            # ignore inner blocks
                Dic_blocks[expr]=(position-1, expr[position:here], here+1)
                return position-1, expr[position:here], here+1  # block found           
        elif c==Crlf :                              # end of line
            break
    Dic_blocks[expr]=(-1,"",-1)
    return -1,"",-1
           
#===================================================== isnumber
def isnumber(expr):
    """
    general Boolean test for for a floating point value
    Parameters
    ------------
        expr: a string
    Returns
    --------
        a Boolean, True if expr is numeric
    """
    try:
        float(expr)
        return True
    except ValueError:
        return False
    except TypeError:
        return False

#===================================================== seconds
def seconds(expr):
    """
    converts a duration into seconds - allows concatenated times (e.g. 1h 30mn)
    Parameters
    ------------
        expr: a string
    Returns
    --------
        a float or None
    """
    if type(expr)!=str : return None                                            # ignore non string
    obj=expr.replace(Space,"")                                                  # eliminate all spaces        
    if not obj : return None  
    for unit in Time_unit_list:                                                      
        here=obj.find(unit)
        if here>-1 and here<len(obj)-len(unit):                           # if unit not at the end
            t1=obj[:here+len(unit)]                                               # cut after unit  
            t2=obj[len(t1):]
            s1=seconds(t1)                                                           # recurse on pieces
            s2=seconds(t2)
            if not (s1 is None or s2 is None): return s1+s2             # concatenate 
            return None

    for unit in Time_unit_list:                                                    # convert unit
        sec=convert_to_seconds(obj, unit)
        if sec is not None: return sec       
    return None

#===================================================== convert_to_seconds
def convert_to_seconds(tim, unit):
    """
    converts a value into seconds if unit matches
    Parameters
    ------------
        tim: a string
    Returns
    --------
        a float or None
    """
    if tim.endswith(unit):                                                           # only apply to this unit
        num=tim[:-len(unit)]
        if isnumber(num): return float(num)*Time_unit_duration[unit]
    return None

#===================================================== isduration
def isduration(obj):
    """
    check if name can be read as a duration
    Parameters
    ------------
        tim: a string
    Returns
    --------
        a Boolean, True if name is a duration
    """
    return (seconds(obj) is not None)

#===================================================== detectlist
def detectlist(exprs):                                                    
    """
    check if an expression is a list, detecting comma outside brackets or quotes
    Parameters
    ------------
        exprs: a string
    Returns
    --------
        a Boolean, True if a list is detected
    """
    if type(exprs)!= str: return False
    expr=no_brackets(exprs)                            # remove external brackets                                                                                          
    bracketlevel=0                                           
    quotelevel=0                                           
    found=False
    for c in expr:
        if c==Quote: quotelevel=1-quotelevel
        if quotelevel==1:                                  # ignore anything between quotes
            continue
        if c==Comma and bracketlevel==0:
            found=True                                      # comma found
            break
        if c==Obr: bracketlevel+=1                   # open block 
        elif c==Cbr: bracketlevel-=1                  # close block
    return found

#===================================================== splitlist
def splitlist(expr):                                 
    """
    splits an expression into a list, using comma separator
    but ignoring commas inside brackets or quotes
    ignore quotes inside brackets and brackets inside quotes
    detect close brackets that do not correspond to open brackets
    Parameters
    -----------
        expr: a string
    Return
    -------
        li: a list        
    """
    if type(expr) != str: return None
    if not expr: return []
    if not Obr in expr and not Quote in expr:           # neither brackets nor quotes
        li=[x.strip(Space) for x in expr.split(Comma)]   # use standard split             
        if li[-1]=='': li=li[:-1]                                       # avoid last empty element                         
        return li
    # explore string sequentially
    bad=False
    quotelevel=0
    bracketlevel=0
    li=[]                                                                   # result list
    elt=""                                                                # string element in list
    for c in expr:
        elt+=c                                                           # build string from chars
        if c==Quote and bracketlevel==0:
                quotelevel=1-quotelevel                        # quote/unquote
        if quotelevel==0:
            if c==Comma and bracketlevel==0:
                li+=[elt[:-1].strip(Space)]                         # store string without comma if level 0
                elt=""
            elif c==Obr: bracketlevel+=1                     # up bracket level
            elif c==Cbr: bracketlevel+=-1                    # down bracket level
    if elt: li+=[elt.strip(Space)]
    return li

#===================================================== makekey
def makekey(mykey):
    """
    converts key into a string, make sure integer keys have no decimal point         
    Parameters
    -----------
        mykey: some object
    Return
    -------
        a string      
    """
    ky=mykey
    if isnumber(ky): ky=float(ky)                                           # convert to number if possible
    if type(ky)==float and coincide(int(ky), ky): ky=int(ky)     # convert to integer if possible
    return str(ky)                                                                  # return as a string 

#===================================================== parentdir
def addparentdir(name):
    """
    verifies if name refers to parent directory '..\' and returns appropriate name         
    Parameters
    -----------
        name: a file name
    Return
    -------
        name: a file name
    """
    if name.startswith("..\\") or name.startswith("../"): return os.path.join(os.pardir, name[3:])          
    return name

#===================================================== logic
def logic(tup, time):
    """
    determines whether an onoff tuple is true by checking with current time
    Parameters
    ------------
        tup: a tuple representing an event
        time: a float representing current time
    Returns
    --------
        st: a Boolean
    """
    st=False
    if tup==(None, None): st=None    
    elif tup:                                                        # empty tuple means False
        ontime=tup[0]
        offtime=tup[1]
        if (ontime is not None and ontime<=time) \
           and (offtime is None or offtime>time): st=True
    return st

#===================================================== istrue
def istrue(nod, time):
    """
    determines whether a Boolean is true by checking on and off times in value
    nod is considered already false at exactly off time
    Parameters
    ------------
        nod: an object, representing an event
        time: a float representing current time
    Returns
    --------
        st: a Boolean
    """
    if Bln[0] in nod.nature:                                                                                          
        nod.nature=Bln
        if nod.value is None: nod.value=[(None, None)]                                              
    if nod.nature!=Bln or type(nod.value)!=list:
        print("*** Node anomaly in tools istrue: should be Bln ***\n-->", nod.content(), "\n")
        raise ReferenceError
    st=False
    if nod.value:                           # empty list means False
        onoff=nod.value[0]
        st=logic(onoff, time)
    return st

#===================================================== set_occur
def set_occur(nod, newtime):
    """
    add a new occurrence and update count
    memory of occurrences is limited to Max_occur_list
    Parameters
    ------------
        nod: an object, representing an event
        newtime: a float representing a new occurrence time
    Returns
    --------
        info is updated in nod.occur
    """
    if nod.occur==[] or nod.occur[-1]!=newtime:
        nod.count+=1
        if len(nod.occur)>=Max_occur_list:
            nod.occur=nod.occur[-Max_occur_list+1:]
        nod.occur+=[newtime]
   
#===================================================== set_status
def set_status(nod, st, time):
    """
    Sets the status of a Boolean by adjusting on and off times in value
    time is the Current_time.
    Does nothing if status is already st
    Parameters
    ------------
        nod: an object, representing an event
        st: a Boolean, the new object status
        time: a float representing current time
    Returns
    --------
        True if status has changed, False if not
        info is updated in nod.value, nod.haschanged, nod.lastchange
    """
    if nod.nature!=Bln or (nod.value is not None and type(nod.value)!=list):
        print("*** Node anomaly in nd.set_status: should be Bln ***\n-->", nod.content())
        raise ReferenceError
    if not nod.value: nod.value=[(None, None)]   # means False
    
    onoff=nod.value[0]                                      # check status
    if logic(onoff, time)==st: return False            # no change needed        
        
    ontime=onoff[0]
    offtime=onoff[1]
    if st:                                                             # means True      
        nod.value=[(time, None)]                         # onset
    else:
        nod.value=[(ontime, time)]                       # offset
    nod.lastchange=time                                   # indicates that value (status) has changed
    nod.haschanged=True
    return True
    
#===================================================== indprint
def indprint(*li):
    """
    print a list with indentation
    """
    print("     ", " ".join(map(str, li)))
    
###===================================================== main
if __name__== "__main__":
##    print (findblock(' anything " )((xx" (findblock test: (19 and 54) is ok) "azerty" '))
    res = splitlist('aha(1),"a,b,c",x("alpha",5)(2), def, "g()", h')
    print(res)
    assert(res==['aha(1)', '"a,b,c"', 'x("alpha",5)(2)', 'def', '"g()"', 'h'])
##    indprint(*range(5))










