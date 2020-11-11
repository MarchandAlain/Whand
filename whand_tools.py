# this module contains only functions that take arguments and return values
# because they are imported as * they should not change shared variables
import os
import re
from whand_parameters import *  # options, constants
from whand_operators import *   # from... import because module only contains constants
import whand_nodes as nd

Dic_treejoin={}                               # dictionaries to accelerate computations and searches                      
Dic_brackets={}                              # results are stored and retrieved, rather than recomputed    
Dic_quotes={}                                    
Dic_applied={}                                    
Dic_blocks={}                                    

#===================================================== treejoin
def treejoin(tree):
    """
    builds a string line from binary tree (no outer brackets) made of
    triplet of nodes (op, b1, b2) with op=string and b1, b2 nodes (or None)
    for lists triplets are (comma, [list], None)
    uses a dictionary when possible for faster runtime
    """
    if tree is None: return ""                                               # empty tree
    op,t1,t2=tree                                                                # decompose tree 
    if t1 is None and t2 is None:                                        # simple node: return op name
        return op

    # Comma 
    if op ==Comma:                                                          # a list (not hashable)
        txt=""                                           
        for index, term in enumerate(t1):                            # second term is a list, not a triplet
            x=treejoin(term)                                                  # *** recursive call for list elements ***
            txt+=x
            if index<len(t1)-1 or len(t1)==1: txt+=Comma
        return Obr+nobrackets(txt)+Cbr                             # (elt1, elt2, ...)

    # has result been computed before
    can_hash=True                                                             # check if tree is hashable
    try:                                                    
        if tree in Dic_treejoin:
            return Dic_treejoin[tree]                                      # retrieve from dict when possible        
    except TypeError:
        can_hash=False                                                       # skip error (unhashable type)
    
    term1=treejoin(t1)                                                      # recursive call for terms
    term2=treejoin(t2)
    
    # Special (subscripting) 
    if op ==Special:                                                          # used for subscripting lists, dicts or attributes
        txt=term1+Obr+nobrackets(term2)+Cbr              # term1(term2)     
        if can_hash: Dic_treejoin[tree]=txt                                             
        return txt

    # Bracketed block
    if op==Obr:                                                                # brackets (disambiguating)
        if not t2:
            txt=Obr+nobrackets(term1)+Cbr                      # (term1)                           
            if can_hash: Dic_treejoin[tree]=txt                                           
            return txt                                                             
        print("\n", Anom_text_after_block, Obr+nobrackets(term1)+Cbr+term2)  # no second term allowed   
        
    # other   
    if not t2:                                                                      # unary operator: no second term
        txt=op+Obr+nobrackets(term1)+Cbr                    # op(term1)
        if can_hash: Dic_treejoin[tree]=txt                                           
        return txt                                                             

    if op in Alphakwords: op=Underscore+op+Underscore   # special spacing for expression names
    
    txt=term1+op+term2                                                # term1 op term2   (no brackets)
    if can_hash: Dic_treejoin[tree]=txt                                           
    return txt                                                              

##===================================================== warn
def warn(text, fatal=False):
    """
    display warnings according to Warnings option and autotest option
    """
    if Warnings or fatal:
        print(text)
    if fatal: raise ReferenceError                                   

#===================================================== isaglitch
def isaglitch(expr):
    """
    detects change(objectname), begin(objectname) or end(objectname)
    returns a tuple (glitchname, objectname), or None if not a glitch
    """
    for gl in Glitch_list:                                                                         # [Change, Begin, End]
        nam=applied(expr, gl)                                                               # applied returns objectname
        if nam: return gl, nam       
    return None

#===================================================== getnature
def getnature(sv, expr, nt=All_natures[:]):
    """
    detects and returns nature of expr if compatible with nt 
    """
    nat=All_natures[:]                                          
    if expr is None or expr=="": return nat                                        # empty object: nature unknown

    if expr in sv.Object:                                                                       # is object is known                                         
        nod=sv.Object[expr]
        nat= nod.nature[:]                                                                    # retrieve object info 
        if nod.isdelayed: nat=Bln[:]          
        
    if 1:                                                                                               # always verify
##    if len(nat)>1:                                                                                 # if still ambiguous 
        if expr in [Exit, Controlpanel]: nat=Bln[:]                                   # use object itself        
        elif isnumber(expr): nat=Nmbr[:]                                              # a plain number
        elif isduration(expr): nat=Drtn[:]                                               # a plain delay
        elif detectlist(expr): nat=Lst[:]                                                   # a plain list
        elif expr.startswith(Output+Obr): nat=Bln[:]                             # logical output (event)
        elif expr.startswith(Pin+Obr): nat=Bln[:]                                   # logical input (event)
        elif expr.startswith(Key+Obr): nat=Bln[:]                                  # character key (event)   
        elif expr[0]==Quote and expr[-1]==Quote : nat=Stt[:]            # quoted text (state) 
        elif isaglitch(expr):                                                                    # begin, end or change
            nat=Bln+Lst                                                                         # a list only if object itself may be a list
            ng=getnature(sv, isaglitch(expr)[1])
            if not Lst[0] in ng: nat=Bln[:]                                                 # else an event
        
        elif expr==Number: nat=Nmbr[:]                                            # by definition           
        elif expr==Delay: nat=Drtn[:]                              
        elif expr==Ewent: nat=Bln[:]
        elif expr==State: nat=Stt[:]
        elif expr==List: nat=Lst[:]
                   
        elif expr.startswith(Special) and expr[1:] in sv.Object:             # copy of existing object
            nat=sv.Object[expr[1:]].nature[:]

        elif expr in sv.Object:                                                               # obtain nature from function                               
            if applied(expr, Cumul) or applied(expr, Steps): nat=Lst[:]  # these functions work element by element
            elif applied(expr, Store): nat=Lst[:]                                      # store is not a function        
            elif Cumul+Obr+expr+Cbr in sv.Object or Steps+Obr+expr+Cbr in sv.Object: nat=Lst[:]

    n=list(set(nt) & set(nat))                                                             # check consistency
    if not n:            
            print("\n", Err_inconsistent_nat)                                          # *** Error in getnature: inconsistent nature ***         
            print(expr, nt, nat)
            raise ReferenceError
    return n

#===================================================== coincide
def coincide(t1, t2):                                                          
    """
    Verifies equality of expressions (within float error range)
    Quotes around strings are ignored
    """
    if t1==t2: return True                                                                  # no difference
    if noquotes(t1)==noquotes(t2): return True                               # (do not move this line)             
    if isnumber(t1): t1=float(t1)                                                        # compare numbers                                 
    if isnumber(t2): t2=float(t2)                                       
    if not type(t1) in [int, float] or \
       not type(t2) in [int, float]: return False                                     # not a number
    if abs(t2-t1)<=FloatPrecision: return True                                  # float error range
    return False
    
#===================================================== nobrackets
def nobrackets(piece):
    """
    remove brackets around a block (recursively if several layers)
    much faster when using the dict   
    """
    result=piece.strip(Space)
    if not result or result[0]!=Obr or result[-1]!=Cbr:
        return result                                             # no brackets found 

    if piece in Dic_brackets:
        return Dic_brackets[piece]                       # retrieve already computed               
    
    first, block,last=findblock(result)                 # determine if it is a bracketed block
    if first==0 and last==len(result):
        result=nobrackets(result[1:-1])                # recurse
    Dic_brackets[piece]=result                          # save result for later                                            
    return result
       
#===================================================== noquotes
def noquotes(piece):
    """
    remove all quotes around a text 
    much faster when using the dict   
    """
    result=piece
    if type(piece) == str:
        if not piece or piece[0]!=Quote or piece[-1]!=Quote:
            return piece                                         # no quotes found
        
        if piece in Dic_quotes:
            return Dic_quotes[piece]                     # retrieve already computed
        
        if not Quote in piece[1:-1]: result=piece[1:-1]  # no inner quotes allowed

        Dic_quotes[piece]=result                        # save result for later                                                             
    return result

#===================================================== changeall
def changeall(piece,old,new):
    """
    replaces all occcurrences even if new ones are formed in the process
    """
    while old in piece: piece=piece.replace(old, new)
    return piece

#===================================================== findlast
def findlast(text, target):
    """
    looks for the last Occurrence of target
    """
    last=-1
    here=text.find(target)
    if here>-1:
        last=here
        there=0
        while there>-1:
            there=text[last+1:].find(target)
            if there>-1: last+=there+1
    return last

#===================================================== noduplicate
def noduplicate(seq):
    """
    List unique elements while preserving order
    stores values in dict for faster lookup
    """
    seen = set()
    seen.clear()                                                     # make sure nothing remains
    return [x for x in seq if not (x in seen or seen.add(x))]

#===================================================== indprint
def indprint(*li):
    """
    print with indentation
    """
    print("     ", " ".join(map(str, li)))
    
#===================================================== root
def root(text):
    """
    returns part of text before first bracket (empty string if none)
    """
    if not text or text.find(Obr)==-1: return ""
    return text[:text.find(Obr)]

#===================================================== fromlist   
def fromlist(sv, expr):
    """
    checks whether expr has form  'root(block)' and is a list and extracts root (list or dict)
    much faster when using the dict sv.Elements 
    """
    if expr[-1]!=Cbr: return ""                                         
    if expr in sv.Elements: return sv.Elements[expr]                  # retrieve already computed 
    root=""
    if Obr in expr:                     
        here, block, there=findblock(expr)        # checks whether expr has form  'root(block)'
        if there==len(expr):
            x=expr[:here]
            if x in sv.Object : root=x                     # do not extract functions      
    sv.Elements[expr]=root
    return root

#===================================================== applied   
def applied(expr, root):
    """
    checks whether expr has form  'root(block)' and extracts block     
    much faster when using the dict   
    """
    if not expr.startswith(root+Obr) or expr[-1]!=Cbr: return ""
    if expr in Dic_applied: return Dic_applied[expr]                  # retrieve already computed     
    applied=""
    here, block, there=findblock(expr)          # checks whether expr has form  'root(block)'
    if there==len(expr):
        applied=block
        Dic_applied[expr]=block                                     
    return applied

#===================================================== findblock
def findblock(piece):
    """
    find first block enclosed in corresponding brackets (ignores internal blocks)
    returns a t-uplet with position-1, block (without brackets) and closing bracket position+1
    returns (-1,"",-1) if no block found
    much faster when using the dict   
    """
    if piece in Dic_blocks: return Dic_blocks[piece]
    if not Obr in piece:
        Dic_blocks[piece]=(-1,"",-1)
        return -1,"",-1                    
    level=0                                           # bracket level
    quot=0                                           # quote level
    for here,c in enumerate(piece):
        if c==Quote: quot=1-quot        # ignore anything between quotes
        if quot==0:
            if c==Crlf :                             # end of line: check balance
                if level!=0:
                    print("\n", Err_unbalanced_brackets)             
                    print(piece)
                    raise ReferenceError
            if c==Cbr:                              # close block
                level-=1
                if level==0:                        # ignore inner blocks
                    Dic_blocks[piece]=(position-1, piece[position:here], here+1)
                    return position-1, piece[position:here], here+1  # block found           
            if c==Obr:                             # open block 
                level+=1
                if level==1:                        # first level brackets only
                    position=here+1           # store first position
    if level!=0:
        print("\n", Err_unbalanced_brackets)             
        print(piece)
        raise ReferenceError
    Dic_blocks[piece]=(-1,"",-1)
    return -1,"",-1
           
#===================================================== isnumber
def isnumber(s):
    """
   General Boolean test for for a floating point value
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
    except TypeError:
        return False

#===================================================== seconds
def seconds(ob):
    """
    converts a duration into seconds - allows concatenated times (e.g. 1h 30mn)
    """
    if not ob or not isinstance(ob, str) : return None                # ignore non string
    obj=ob.strip(Space)    
    for unit in Time_unit_list:                                                      
        if unit in obj[:-len(unit)]:                                                  # unit not at end: cut after unit
            here=obj.find(unit)
            t1=obj[:here+len(unit)]
            t2=obj[len(t1):]
            s1=seconds(t1)                                                           # recurse on pieces
            s2=seconds(t2)
            if not (s1 is None or s2 is None): return s1+s2           # concatenate 
            return None
    obj=obj.replace(Space,"")                                                   # eliminate all spaces        
    if not obj : return None  
    if obj[-len(Unit_ms):] == Unit_ms and isnumber(obj[:-len(Unit_ms)]): return float(obj[:-len(Unit_ms)])*0.001  
    if obj[-len(Unit_sec):] == Unit_sec and isnumber(obj[:-len(Unit_sec)]): return float(obj[:-len(Unit_sec)])  
    if obj[-len(Unit_min1):] == Unit_min1 and isnumber(obj[:-len(Unit_min1)]): return float(obj[:-len(Unit_min1)])*60 
    if obj[-len(Unit_min2):] == Unit_min2 and isnumber(obj[:-len(Unit_min2)]): return float(obj[:-len(Unit_min2)])*60
    if obj[-len(Unit_hour):] == Unit_hour and isnumber(obj[:-len(Unit_hour)]): return float(obj[:-len(Unit_hour)])*3600 
    if obj[-len(Unit_week):] == Unit_week and isnumber(obj[:-len(Unit_week)]): return  float(obj[:-len(Unit_week)])*7*24*3600  
    if obj[-len(Unit_day):] == Unit_day and isnumber(obj[:-len(Unit_day)]): return float(obj[:--len(Unit_day)])*24*3600
    return None

#===================================================== isduration
def isduration(obj):
    """
    Check if name is a duration
    """
    return seconds(obj) is not None

###=================================================== noduplicates
##def noduplicates(li):
##    """
##    Remove duplicates while preserving order   
##    """
##    nodup=[]
##    for x in li:
##        if not x in nodup: nodup+=[x]    
##    return nodup

#===================================================== detectlist
def detectlist(exprs):                                                    
    """
    finds if an expression is a list, detecting comma outside brackets or quotes
    """
##    print("xx detectlist", exprs)
    if not type(exprs) == str: return False
    expr=nobrackets(exprs)                                                                                                                      
    while Quote in expr:                                        # excise parts between quotes 
        here=expr.find(Quote)
        there=expr[here+1:].find(Quote)
        if there==-1:
            print("\n", Err_unbalanced_quotes)                          
            print (expr)
            raise ReferenceError
        expr=expr[:here]+expr[here+there+2:]
    if Obr in expr:                                                 # ignore parts between brackets
        here, block, there=findblock(expr)
        if Comma in expr[:here]:                            # look for comma before block 
##            print("xxxx", exprs, "is a list")
##            print(exprs, splitlist(exprs))
            return True
        elif expr[there:] and expr[there:there+1]!=Obr:
            if detectlist(expr[there:]):                     # look for comma after block
##                print("xxxx", exprs, "is a list")
##                print(exprs, splitlist(exprs))
                return True
            return False
        
    if not Obr in expr and not Quote in expr:
##        if (Comma in expr): print("xxxx", exprs, "is a list")
        if (Comma in expr):
##            print(exprs, splitlist(exprs))
            return True      
    return False

#===================================================== splitlist
def splitlist(exprs, quotes=False):                                 
    """
    splits an expression into a list, respecting brackets and quotes
    """
##    print("xxxx splitlist", exprs)
    expr=exprs
    if not expr: return []
    if not type(expr) == str: return None
    if not Obr in expr and not Quote in expr:      # neither brackets nor quotes
        li=expr.split(Comma)                         
        li=[x.strip(Space) for x in li]             
        if li[-1]=='': li=li[:-1]                                    # avoid empty element                         
##        print("xxxx simple -->", li)
        return li
    # explore sequentially            
    quotelevel=0
    bracketlevel=0
    li=[]
    elt=""
    for c in expr:
        if c==Obr:
            elt+=c                                     # build string from chars
            bracketlevel+=1                      # up bracket level
        elif c==Cbr:
            elt+=c
            bracketlevel+=-1                     # down bracket level       
        elif c==Quote:
            if bracketlevel>0 or quotes: elt+=c   
            quotelevel=1-quotelevel         # quote/unquote
        elif c==Comma and quotelevel==0 and bracketlevel==0:
            li+=[elt]                                   # store string if level 0
            elt=""
        else: elt+=c
    if elt: li+=[elt]                                 # for print 
##    print("xxxx quotes or brackets -->", li)
    return li

#===================================================== makekey
def makekey(mykey):
    """
    converts key into a string, make sure integer keys have no decimal point         
    """
    ky=mykey
    if isnumber(ky): ky=float(ky)
    if type(ky)==float and int(ky)==ky: ky=int(ky)
    return str(ky)

#===================================================== isdictkey
def isdictkey(sv, mykey, dictname):
    """
    verifies if mykey is a key to Whand dictionary, returns True/False         
    """
    if not dictname in sv.Object: return False
    li=sv.Object[dictname].value
    if li is None: return False
    if type(li)!=list:
##        print("\n", "*** Anomaly: illegal dict value ***")
        print("\n", Anom_illegal_dict_val)                              
        print(dictname, "=", li)
        raise ReferenceError
    ky=dictname+Obr+mykey+Cbr    
    for elt in li:                                    
        if elt==ky: return True              
    return False

#===================================================== parentdir
def addparentdir(name):
    """
    verifies if name refers to parent directory '..\' and returns appropriate name         
    """
    if name.startswith("..\\") or name.startswith("../"): return os.path.join(os.pardir, name[3:])          
    return name

#===================================================== logic
def logic(tup, time):
    """
    determines whether an onoff tuple is true by checking with time. v2.00
    corrected v2.025
    """
    st=False
    if tup==(None, None): return None    # v2.034
    if tup:                                 # empty tuple means False
        ontime=tup[0]
        offtime=tup[1]
        if (ontime is not None and ontime<=time) \
           and (offtime is None or offtime>time): st=True
    return st

#===================================================== istrue
def istrue(nod, time):
    """
    determines whether a Boolean is true by checking on and off times in value
    time is the Current_time. Nod is considered already false at exactly off time
    Use epsilon to delay off time when needed
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
    list of occurrences is limited to Max_occur_list
    """
    nod.count+=1
    if len(nod.occur)>=Max_occur_list:
        nod.occur=nod.occur[-Max_occur_list+1:]
    nod.occur+=[newtime]
   
#===================================================== setstatus
def setstatus(nod, st, time):
    """
    Sets the status of a Boolean by adjusting on and off times in value
    time is the Current_time.
    Also adjust haschanged, lastchange 
    Does nothing if status is already st
    """
    if nod.nature!=Bln or not (nod.value is None or type(nod.value)==list):
        print("*** Node anomaly in nd.setstatus: should be Bln ***\n-->", nod.content())
        raise ReferenceError
    if not nod.value:
        nod.value=[(None, None)]                          # means False  
    onoff=nod.value[0]                                  # check status

    if logic(onoff, time):                                  #
        if st: return False                                   # no change needed
    else:
        if not st: return False                             # no change needed        
        
    ontime=onoff[0]
    offtime=onoff[1]
    if st:                                                           # means True      
        nod.value=[(time, None)]                     # onset
    else:
        nod.value=[(ontime, time)]                   # offset
    nod.lastchange=time                                # indicates that value (status) has changed
    nod.haschanged=True
    return True
    
###===================================================== main
if __name__== "__main__":
##    print (findblock(' anything " )((xx" (findblock test: (19 and 54) is ok) "azerty" '))
##    print(splitlist('aha(1),"a,b,c",x("alpha",5)(2), def, "g()", h'))
    indprint(*range(5))






