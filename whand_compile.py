# -*- coding: ISO-8859-1 -*-
from whand_parameters import *   # options, constants
from whand_tools import *
import whand_precompile as pc
import whand_sharedvars as sp    # for tests

#==================== precompile section was working on text. Now program becomes a tree
#===================================================== predefined
def predefined(sv):
    """
    creates and initializes useful standard nodes
    [Vrai, Faux, Start, Epsilon, Empty] as listed in Fixed
    """
    for nom in Fixed+[Start]:   
        nod=add_object(sv, nom)                    # create object
        nod.nature=Bln[:]                                 # default nature for Vrai, Faux, Start     

    sv.Object[Epsilon].nature=Drtn[:]            # epsilon is a delay
    sv.Object[Empty].nature=Lst[:]                # empty is a list

    setstatus(sv.Object[Vrai], True, 0)            # true
    setstatus(sv.Object[Faux], False, 0)          # false
    sv.Object[Epsilon].value=str(Epsilon_time)+ 's'   # brief delay
    sv.Object[Empty].value=[]                       # empty list
    
#===================================================== create_defined
def create_defined(sv, prog):
    """
    create defined nodes, argument list for functions, elements, clauses
    identifies lines containing object names
    looks for subscripts
    sv.Object is a dict containing all objects
    sv.Object_list is a list containing defined objects in order of appearance and other added objects
    """
    verbose=('crd' in Debog)
    lines=prog.split(Crlf)                          # transform program into a list of lines
    if lines:
        keepcount=0                                  # used later in a key for a dict of lines containing functions
        for num, lig in enumerate(lines):    # process line by line
            lig=lig.strip(Space)                     # remove extra spaces
            
# process object names
            if not lig.startswith(When) and not lig.startswith(Col):                 # neither condition nor value -> defined name

# first remove equivalence codes but keep track of them (not yet exploited)
                if verbose: print("Analyzing line", lig)
                isequiv=None                                                    # retrieve equivalents 
                if lig.startswith(Equal+Special):                                        
                    lig=lig[len(Equal+Special):]                            # remove equivalence code             
                    isequiv=lines[num+2][len(Col):]                     # equivalent value, two lines down 
##                    print("xxxx equiv to", lig, "-->", isequiv)
##                if lig.startswith(Special+Any+Special+Equal+Special):       
##                    lig=Special+Any+Special+lig[len(Special+Any+Special+Equal+Special):]    
##                    isequiv=lines[num+2][len(Col):]                     # equivalent name + user-defined function 
##                    print("xxxx equiv to", lig, "-->", isequiv)

# is it a subscripted name?
                here, block, last=findblock(lig)                                        # find brackets
                if not lig or here==0:                                                       # name may not start with a bracket
                    print("\n", Err_empty_name)                                        # *** Syntax error: empty name ***  
                    print(lig)
                    if num>2:                                                                     # common source of empty name error
                        print(Help_continuation+Mline+"' ):")                     # you may have meant (with continuation character '"+Mline):
                        print(lines[num-3].strip(Space)+Col, Mline, Crlf, lig) # suggested correction
                    raise ReferenceError

# detect list elements and functions
                code=lig                                                                          # name is entire line or only root                                                                           
                is_function=False
                is_user_func=False
                if here>0:                                                                         # function/list element found with form: root(args)
                    is_function=True                                                          # flag
                    code=lig[:here]                                                            # extract function/list name, i.e. root
                    if code in Internal_Functions:                                          
                        print("\n", Err_redef_internal_func)   # *** Error: You cannot define '"+code+"' because it is an internal function ***                            
                        print(code)
                        print(lig)
                        raise ReferenceError
                    
                    if lig[last:]:                                                                    # name must end with closing bracket after args
                        print("\n", Err_text_after_args)                                 # *** Syntax error: text found after arguments ***                              
                        print(lig)
                        raise ReferenceError
                    
                    args=[lig[len(code)+1:-1]]
                    if detectlist(args[0]):
                        args=args[0].split(Comma)
                    if isprime(args[0]):
                        for x in args:
                            if not isprime(x):
                                print("\n*** Error in user-defined function: all args must be prime ***")
                                print(lig)
                                raise ReferenceError
                        is_user_func=True                                                    # flag to be stored in .isuserfunc
                        if verbose: print(code, "is a user defined function")

# check syntax: "=" is not allowed in names
                if code.find(Equal)!=-1:
                    print("\n", Err_equal_in_name)                                    # *** Illegal character in name: "+ Equal +" ***                              
                    print(code)
                    raise ReferenceError

# store name if new
                if not code in sv.Object:                                                   # new name not in object dict
                    nod=add_object(sv, code)                                           # create object
                    nod.isdefined=True                                                      # flag object as defined   
                    nod.isfunction=is_function                                           # function or list used with brackets (args or subscripts)
                    if code==lig: nod.once=True                                       # verify list is not redefined as dict
                    nod.isuserfunc=is_user_func                                         # retrieve flag for user-defined function (root) 
                    if not is_function: nod.equivalent=isequiv                    # save equivalent for whole names only          
                    if verbose: print("creating node", sv.Object[code].name, ", function", sv.Object[code].isfunction, sv.Object[code].arguments)
                    
                else:                                                                                # name already known: only allowed if code is root
                    nod=sv.Object[code]                                                  # get object from dict (may be root)
                    if nod.name==lig or code==lig or nod.once \
                       or is_user_func or nod.isuserfunc:  # 1) full name  2) defined dict  3) redefined list as dict  4,5) redefined user func
                        print("\n", Err_redef_name)                                     # *** Error: Node is already defined ***                                    
                        print(lig)
                        raise ReferenceError

# create a new element if object is subscripted         
                if is_function:                                                                  # process function arguments
                    if lig in sv.Object:                                                        # element is already defined 
                        print("\n", Err_redef_name)                                     # *** Error: Node is already defined ***                             
                        print(lig)
                        raise ReferenceError
                    
                    code=block.strip(Space)                                            # text between brackets 
                    keepcount+=1                                                           # protect element name
                    text=Garde+str(keepcount)                                       # make new storage key
                    sv.Keep[text]=lig                                                        # save whole name
                    nod.arguments+=[(code, Special+text+Special),]     # save raw arguments and dict key to whole line
                    if verbose: print("fff", nod.name, nod.isfunction, nod.arguments)
                    
                    nod=add_object(sv, lig)                                             # create object for element
                    nod.isdefined=True                                                   # flag object as defined 
                    nod.equivalent=isequiv                                             # save equivalent for element               
                    if verbose: print("creating element", sv.Object[lig].name, sv.Object[lig].isfunction, sv.Object[lig].arguments)

# process conditions and values        
            elif  lig.startswith(When):                                                   # conditions (unprocessed) 
                clau=lig[len(When):].strip(Space)                                   # no surrounding spaces or brackets
                clau=nobrackets(clau)
            elif  lig.startswith(Col):                                                       # values (unprocessed)
                vlu=lig[len(Col):].strip(Space)                                        # no surrounding spaces or brackets
                vlu=nobrackets(vlu)
                nod.clauses+=[((clau, None, None), (vlu, None, None))] # store in list of doublets (condition, value)
                if verbose: print("clauses of", nod.name, Col, nod.clauses)

# reprocess functions to put list of args (text) in value under function/list name (root)
# value contains a list of all uses of the user-defined function, or all elements of the list
        for name in sv.Object_list:                                                    # use list of objects
            nod=sv.Object[name]
            if nod.isfunction:                                                              # either a "dict" or a user defined function    
                if not nod.isuserfunc: nod.isdict=True                         # a "dict" is a list defined element by element
                vlu=""
                for block, lig in nod.arguments:                                   # extract each element
                    if nod.isdict:                                                             # a "dict"
                        vlu+=name+Obr+block+Cbr+Comma                # element with root and brackets, comma to indicate list
                    else:                                                                          # a user-defined function
                        vlu+=block+Comma                                            # element with comma to indicate list  
                if len(nod.arguments)>1: vlu=vlu[:-1]                           # remove trailing comma if >1 element 
                nod.clauses+=[((Start, None, None), (vlu, None, None))] # create clause
                if verbose: print("www", nod.name, nod.clauses)
                
#============================= treebuild
def treebuild(sv, piece=Crlf):
    """
    if piece==Crlf: parse all program
    parse text for operators and builds a tree of triplets, recursively
    triplet of form (op, b1, b2) with op: string and b1, b2: nodes
    every op is stripped from Spaces. Leafs are (name, None, None)
    lists are stored as (op:comma, b1:list of terms and b2: None)
    """
# build all program
    verbose=('trb' in Debog)
    if piece==Crlf:                                                                       # recognized as an invalid value for a piece                                                       
        if verbose: print("Building tree...")   
        for nom in sv.Object_list:                                                  # get each defined object (preserves order)
            nod=sv.Object[nom]
            if verbose: print(Crlf, nod.name, Col)
            for num, (c, v) in enumerate(nod.clauses):                    # objects always have clauses after precompile
                clau,a,b=c                                                                 # c: condition triplet
                vlu,d,e=v                                                                   # v: value triplet
                c=treebuild(sv, clau)                                                 # *** recursive call with condition ***
                v=treebuild(sv, vlu)                                                   # *** recursive call with value ***
                nod.clauses[num]=(c,v)
                if verbose: print("building:", nom, (c,v))
        if verbose:                                                                         # display functions for debugging
            print("\Functions/lists:")
            for nod in list(sv.Object.values()):
                if nod.isfunction:                                                       # any defined object of form: root(args)
                    print(nod.name, nod.arguments, Col)
                    if nod.clauses:
                        print("     -->", nod.clauses)
                print()
    else:
# process some expression
        piece=piece.strip(Space)                                                      
        if not piece:                                                                          # empty expression
            return None
        if verbose: indprint ("  building", piece)
        sv.Indent+="    "                                                                  # formatting for debugging  

    # a string between quotes
        if piece[0]==Quote and piece[-1]==Quote:                         # process strings (no further parsing)
            sv.Indent=sv.Indent[:-4]                                                   # formatting for debugging
            return (piece, None, None)                                              # return string as a leaf
        
        code=piece.strip(Special)                                                    # get dict key
    # a protected string    
        if code in sv.Strings:                                                            # process strings (no further parsing)
            sv.Indent=sv.Indent[:-4]
            return (Quote+sv.Strings[code]+Quote, None, None)

    # a bracketed expression
        if code in sv.Blocks:                                                             # parse bracketed expressions from outer ones on
            res= (Obr, treebuild(sv, nobrackets(sv.Blocks[code])), None)  # *** recursive call within brackets ***
            sv.Indent=sv.Indent[:-4]                                                   # formatting for debugging
            return res  

    # an argument list     
        if code in sv.Keep:                                                                 # process argument list (no further parsing)
            sv.Indent=sv.Indent[:-4]
            return (sv.Keep[code], None, None)        
        
        piece=savebrackets(sv, piece)                                              # protect outer bracketed expressions from parsing
        
    # prepare to parse all operators by priority and descending order of position           
        piece=Space+piece+Space                                                   # add Spaces to help detect alphabetic keys    
        user=[o.name for o  in list(sv.Object.values()) if o.isdefined] # list of user defined names  
        for group in Priority_groups+[user]:                                      # ops by priority
            poslist=[]
            for o in group:
                op=Space+o+Space if o in Alphakwords+user else o   # separate alphabetic with spaces
                here=-1
                while op in piece[here+1:]:                                             # make a list of ops of same priority and their position
                    here=piece.find(op, here+1)
                    poslist.append((here, o, op))
            if len(poslist)>1: poslist.sort(key=lambda x: -x[0])             # sort list in descending order of position

            oplist=[]
            if poslist:                                                                              # remove overlapping elements (e.g. "<=", "!=" vs. "=", "<")
                last=len(piece)                                                                 # initialization
                lastop=""                                                                         # previous op
                for here, o, op in poslist:                                                 # scan list
                    if abs(here-last)<2:                                                      # compare consecutive overlapping ops (2 chars max)
                        if len(o)>len(lastop):                                                # only keep op with the greater length
                            if not oplist: oplist.append((o,op))                      # list is still empty 
                            else:
                                oplist.pop()                                                     # remove shorter op
                                oplist.append((o,op))                                      # keep operator, without and with space 
                            lastop=o                                                             # store larger op as previous
                            last=len(o)
                        # no else here: do not store shorter element
                    else:
                        oplist.append((o,op))                                              # no overlap: store and continue
                        lastop=o
                        last=here

            for o, op in oplist:                                                              # list of ops from each group in reverse order of occurrence
    #     process comma operator            
                if o==Comma:                                                               # list will be linear (not a tree)           
                    if o in piece:
                        li=[]
                        t1=piece
                        while o in t1:                                                         # build list from the end
                            here=findlast(t1, o)                                          # find last op and process last element
                            li=[treebuild(sv, t1[here+1:])]+li                       # *** recursive call for one element ***
                            t1=t1[:here]
                        li=[treebuild(sv, t1)]+li                                         # make a list, keeping last elements at the end
                        res=(Comma, li, None)                                         # triplet for a list: (",", [list of elements], None)
                        if verbose: indprint ("        --> result:", res)          # for debugging
                        sv.Indent=sv.Indent[:-4]
                        return res

    #     process unary functions and defined objects. All operators of equal priority are treated in order of occurrence
                if o in Unary+user:                                                        # unary operators  (non space-delimited)
                    here=piece.find(op)                                                  # look for first occurrence (space-delimited if alphabetic)
                    if here==0:                                                                # operator is at the start 
                        if verbose: indprint ("unary operator", o)
                        there=len(op)                                                        # start position of last part
                        if piece[there:].startswith(Special+Bloc):               # if the object is subscripted / has args
                            here=piece[there+1:].find(Special)                    # find ending delimiter
                            code=piece[there+1:there+here+1]                  # extract key for the block
                            if piece[there+here+2:].strip(Space):                 # there is something after the block (some other subscript)
                                first=(piece[:there].strip(Space), treebuild(sv, nobrackets(sv.Blocks[code])), None) # *** recursive call for the block ***
                                last=treebuild(sv, piece[there+here+2:])       # *** recursive call for the other subscript ***
                                res=(Special, first, last)                                  # code for a subscripted object
                            else:
                                res=(piece[:there].strip(Space), treebuild(sv, nobrackets(sv.Blocks[code])), None) # *** recursive call for the block ***
                            if verbose: indprint ("        --> result:", res)
                            sv.Indent=sv.Indent[:-4]
                            return res
                        res=(piece[:len(op)-1].strip(Space), treebuild(sv, piece[there:]), None)    # the object is not subscripted / no args
                        if verbose: indprint ("        --> result:", res)
                        sv.Indent=sv.Indent[:-4]
                        return res
                    
    #     process binary operators (always lower priority than unary)
                elif op in piece:                                                        # binary operators (space-delimited)
                    if verbose: indprint ("operator", o)
                    here=findlast(piece,op)                                        # look for last occurrence
                    there=here+len(op)
                    t1=piece[:here]                                                     # first term (sometimes omitted)
                    t2=piece[there:]                                                   # second term
                    if not t2.strip(Space):                                            # must be present
                        print("\n", Err_op_syntax)                                 # *** Syntax error in operator ***
                        bl=Obr+sv.Blocks[t1[2:-2]]+Cbr if t1[2:-2] in sv.Blocks else t1
                        print("      ", bl, o)
                        raise ReferenceError

                    res= (piece[here:there].strip(Space),treebuild(sv, t1),treebuild(sv, t2))            # *** recursive call for each term ***
                    if verbose: indprint ("        --> result:", res)
                    sv.Indent=sv.Indent[:-4]
                    return res

    #   end of operator parsing

    # process other (args and doubly) subscripted objects
        piece=piece.strip(Space)
        if Special+Bloc in piece:                                        # the object is subscripted / has args
            prefix=""
            tail=piece
            if not piece.startswith(Special+Bloc):
                here=piece.find(Special+Bloc)                     # find beginning delimiter
                prefix=piece[:here].strip(Space)                   # extract prefix
                tail=piece[here:]
            here=tail[1:].find(Special)                                # find ending delimiter
            code=tail[1:here+1]                                        # extract key for the block
            if tail[here+2:].strip(Space):                             # there is something after the block (some other subscript)
                first=treebuild(sv, nobrackets(sv.Blocks[code])) # *** recursive call for the block ***
                last=treebuild(sv, tail[here+2:])                   # *** recursive call for the other subscript ***
                res=(Special, first, last)                                # code for a subscripted object
            else:
                if isnumber(prefix):                                      # implicit multiply
                    last=treebuild(sv, nobrackets(sv.Blocks[code])) # *** recursive call for the block ***
                    res=(Mult, (prefix, None, None), (Obr, last, None))     
                else:    
                    last=treebuild(sv, nobrackets(sv.Blocks[code])) # *** recursive call for the block ***
                    res=(Special, (prefix, None, None), last)     # code for a subscripted object
            if verbose: indprint ("         --> result:", res)
            sv.Indent=sv.Indent[:-4]
            return res

    # when all operators have been processed, only leaves remain
        here=piece.find(Space)                                         
        if isduration(piece):
            piece=piece.replace(Space,'')                            # eliminate spaces from durations
        elif here>0:                                                            # look for implicit multiply with space
            if isnumber(piece[:here]):                                  # a number times a name
                sv.Indent=sv.Indent[:-4]
                return (Mult, (piece[:here], None, None), (piece[here+1:], None, None))
            else:                                                                   # error space in name
                print(Err_space_in_name, piece)
                raise ReferenceError
        else:                                                                       # look for implicit multiply without space
            here=1
            while isnumber(piece[:here]) and here<len(piece): 
                here+=1                                                         # longest numerical value
            here-=1
            if here>0 and not isnumber(piece):                    # a number times a name
                sv.Indent=sv.Indent[:-4]
                return (Mult, (piece[:here], None, None), (piece[here:], None, None))   
        sv.Indent=sv.Indent[:-4]
        return (piece, None, None)                                   # triplet for a leaf

# end of treebuild

#===================================================== savebrackets
def savebrackets(sv, lig): 
    """
    Replace and store bracketed expressions in sv.Blocks dictionary
    Processes one line. Removes only external blocks
    Used in treebuild (recurses for internal blocks)
    """
    verbose=('svb' in Debog)
    here,block,last=findblock(lig)                                        # find external bracketed block
    if here<0:
        return lig                                                                   # no brackets
    while here>-1:                                                               # brackets found
        before=lig[:here].strip(Space)
        after=lig[last:].strip(Space)
        code=""
        for num, (c,expr)  in enumerate(sv.Blocks.items()):    # check if block already exists
            if expr==lig[here+1:last-1]:
                code=c                                                              # use old code
        if not code:                                                                # novel block
            bracketcount=len(sv.Blocks)
            code=Bloc+str(bracketcount)                               # make new storage key, e.g.  §Block2§
            sv.Blocks[code]=lig[here+1:last-1]
        lig=before+Space+Special+code+Special+Space+after  # replace with key
        if verbose: indprint ("making block", [str(code)],":", sv.Blocks[code])
        here,block,last=findblock(lig)                                   # continue analysis
        if verbose: indprint ("  result", lig)
    return lig

#===================================================== adjustments
def adjustments(sv):
    """
    make a number of small modifications and verifications for special cases
    """
    unary_minus(sv)                                # explore all tree for unary minus cases
    unary_pick_sort(sv)                           # explore all tree for unary pick or sort  
    switch_any_all(sv)                              # explore all tree and switch some ops 
    fillidem(sv)                                        # explore all tree for idem without args
    isempty(sv)                                       #  explore all tree to make substitutions         
    adjust_storelist(sv)                            # make sure store applies to a list

#===================================================== unary_minus
def unary_minus(sv, tree=All):
    """
    analyze program to solve unary minus cases (when tree==All) because minus is a binary operator
    recursively analyze subtrees
    plain numbers and durations x are replaced by -x
    other expressions B are replaced by -1 * B (valid for both numbers and durations) 
    """
    verbose=('unm' in Debog)

    func=unary_minus                                                   # prepare for recursivity 
    if tree==All:                                                             # analyze whole program
        for nom in sv.Object_list:                                     # scan all objects
            nod=sv.Object[nom]
            for i, (c,v) in enumerate(nod.clauses):              # search clauses
                k=func(sv, c)                                                # *** recursive call with condition ***
                w=func(sv, v)                                               # *** recursive call with value ***
                nod.clauses[i]=(k,w)
            if verbose: print("unm    ", nod.name, Col, nod.clauses)
    else:                                                                        # analyze a subtree
        if not tree: return None
        if verbose: print("  analyzing", tree)
        o,A,B=tree

        # special case: list: process each element
        if o==Comma:
            if verbose: print("      elements:", A)
            res=[]
            for x in A:                                                         # analyze all elements (triplets) in a list
                res+=[func(sv, x)]                                        # recursively analyze and replace 
                if verbose: print("                   -->", x, res)
            if verbose: print("    result list:", res)
            return (o, res, None)

        # other cases       
        if not A and not B:                                             # simple leaf
            if verbose: print("                   -->", o, (o, None, None))
            return (o, None, None)
        if o!=Minus or A:                                                # not a unary minus: explore deeper
            if verbose: print("                   --> building from", o, A, B)
            return (o, func(sv, A), func(sv, B))                   # recursively analyze and replace
        x,y,z=B                                                               # it is a unary minus. B is the expression having to change sign
        if verbose: print("    unary minus:", tree)
        if not y and not z:                                              # B is a simple expression
            if verbose: print("      leaf:", x)
            if isnumber(x) or isduration(x): return ('-'+x, None, None)  # just insert '-' prefix to numbers and durations
            return (Mult, ('-1', None, None), B)               # replace with -1 * B     
        
        if verbose: print("      expression:", tree)           # B is not a simple expression
        return (Mult, ('-1', None, None), func(sv, B))    # recursively replace with -1 * B                   

#===================================================== unary_pick_sort
def unary_pick_sort(sv, tree=All):
    """
    analyze program to solve unary pick and sort expressions  (when tree==All)
    because pick and sort are binary operators
    recursively analyze subtrees
    fills in first term of the operation with second term
    """
    func=unary_pick_sort                                              # prepare for recursivity 
    if tree==All:                                                             # analyze whole program
        for nom in sv.Object_list:                                    # scan all objects in order
            nod=sv.Object[nom]
            for i, (c,v) in enumerate(nod.clauses):
                k=func(sv, c)
                w=func(sv, v)
                nod.clauses[i]=(k,w)
    else:                                                                         # analyze a subtree
        if not tree: return None
        op,A,B=tree
        if not A and not B:                                               # simple leaf
            return tree
        if op==Comma:                                                  # analyze all elements (triplets) in a list
            li=[]
            for x in A:
                li+=[func(sv, x)]                                           # *** recursive call with list element ***
            return (op, li, None)
        if A or not op in [Pick, Sort]:                               # not a unary pick or sort
            return (op, func(sv, A), func(sv, B))                  # *** recursive call: search deeper ***
        B=func(sv, B)                                                       # *** recursive call: fill in and search deeper ***
        return (op, B, B)                     
        
#===================================================== switch_any_all
def switch_any_all(sv, tree=All):
    """
    Here compiler allows for one type of common user error
    begin(any( )), end(any( )), begin(all( )), end(all( ))
    should be any(begin()), any(end()), etc.
    analyze program to switch order of operators
    recursively explores conditions and values
    issues a warning
    """
    func=switch_any_all                                                 # prepare for recursivity 
    if tree==All:                                                             # analyze whole program
        for nom in sv.Object_list:                                     # scan all objects in order
            nod=sv.Object[nom]
            for i, (c,v) in enumerate(nod.clauses):
                k=func(sv, c)
                w=func(sv, v)
                nod.clauses[i]=(k,w)
    else:                                                                         # analyze a subtree
        if not tree: return None
        op,A,B=tree
        if not A and not B:                                               # simple leaf
            return tree
        if op==Comma:                                                  # analyze all elements (triplets) in a list
            li=[]
            for x in A:
                li+=[func(sv, x)]                                          # *** recursive call with list element ***
            return (op, li, None)
        if not (A and A[0] in [Any, All] and op in [Begin, End]):  # not what we look for   
            return (op, func(sv, A), func(sv, B))                 # *** recursive call: search deeper ***
        else:
            sw=(A[0], (op, func(sv, A[1]), func(sv, A[2])), None)  # *** recursive call: switch and search deeper ***
            warn("\n"+Warn_switch_any_all+ \
            " '"+treejoin(tree)+"' --> '"+treejoin(sw)+"'") # here treejoin recreates a name for display only
            # *** Warning: compiler replaced ... ***  
            return sw

#===================================================== fillidem
def fillidem(sv, tree=None, nam=Crlf):
    """
    analyze program to solve idem without arg
    when idem is used without argument, it refers to the current object
    """
    verbose=('fli' in Debog)
    func=fillidem                                                           # prepare for recursivity 
    if nam==Crlf:                                                           # analyze whole program
        if verbose: print("Looking for idem without arg")
        for nom in sv.Object_list:                                      # scan all objects in order
            nod=sv.Object[nom]
            if verbose: print("  exploring", nam, Crlf, "      ",nod.clauses)
            for i, (c,v) in enumerate(nod.clauses):
                k=func(sv, c, nom)                                      # pass on object name
                w=func(sv, v, nom)
                nod.clauses[i]=(k,w)
            if verbose: print("    ", nom, Col, nod.clauses)
    else:                                                                         # analyze a subtree
        if not tree: return None
        if verbose: print("  analyzing", tree)
        o,A,B=tree

        if o==Comma:                                                    # analyze all elements (triplets) in a list
            if verbose: print("      elements:", A)
            res=[]
            for x in A:
                res+=[func(sv, x, nam)]                               # *** recursive call with list element ***
                if verbose: print("                   -->", x, res)
            if verbose: print("    result list:", res)
            return (o, res, None)

        # other cases       
        if A or B:                                                              # not what we look for   
            if verbose: print("                   decomposing", tree)
            return (o, func(sv, A, nam), func(sv, B, nam))  # *** recursive call: search deeper ***
        
        res=(o, None, None)
        if o==Idem:                                                      
            A=treebuild(sv, nam)                                     # parse object name (e.g. list element)              
            res=(Idem, A, None)                                      # fill in argument              
        if verbose: print("                   -->", res)
        return res

#================================================================== isempty
def isempty(sv):                                                                                  
    """
    Here some tricks to circumvent problems of empty lists with operators is and isnot
    substitute syntax: 'is empty' ; '=empty' with 'match empty'
    'X is not empty' ; 'X !=empty' with 'empty within X'  (it is true if X is not empty)
    result is a Boolean not a list
    """
    reprocess(sv, (Is, Crlf, (Empty, None, None)), (Match, Crlf, (Empty, None, None)))
    reprocess(sv, (Equal, Crlf, (Empty, None, None)), (Match, Crlf, (Empty, None, None)))
    reprocess(sv, (Isnot, Crlf, (Empty, None, None)), (Within, (Empty, None, None), Crlf))
    reprocess(sv, (Nequal, Crlf, (Empty, None, None)), (Within, (Empty, None, None), Crlf))
    
#===================================================== reprocess
def reprocess(sv, old, new, tree=All):
    """
    a tool to modify elements in the program (used in isempty)
    reprocess tree to change some branches from old to new     
    old and new are triplets taken from a list of replacements
    Crlf (never occurs in tree) is used as wildcard to replace any tree element
    only one wildcard is allowed in each substitution
    it may change place in tree during the process
    """
    func=reprocess                                                        # prepare for recursivity 
    if tree==All:                                                             # analyze whole program
        for nom in sv.Object_list:                                     # scan all objects in order
            nod=sv.Object[nom]
            for i, (c,v) in enumerate(nod.clauses):
                k=func(sv, old, new, c)
                w=func(sv, old, new, v)
                nod.clauses[i]=(k,w)
    else:                                                                         # analyze a subtree
        if not tree: return None
        op,A,B=tree
        opold,Aold, Bold=old                                 
        opnew, Anew, Bnew=new
        if opold==Crlf: opold, wildcard=op, op            # wildcard is set to current op
        if Aold==Crlf: Aold, wildcard=A, A                    # wildcard is set to current A
        if Bold==Crlf: Bold, wildcard=B, B                     # wildcard is set to current B
        if opnew==Crlf: opnew=wildcard                      # wildcard is used in replace
        if Anew==Crlf: Anew=wildcard
        if Bnew==Crlf: Bnew=wildcard
        if (op, A, B)==(opold, Aold, Bold): return (opnew, Anew, Bnew)
       
        if not A and not B:                                              # leaf
            return tree
        
        if op==Comma:                                                 # analyze all elements (triplets) in a list
            li=[]
            for x in A:
                li+=[func(sv, old, new, x)]                          # *** recursive call with list element ***
            return (op, li, None)
        
        return (op, func(sv, old, new, A), func(sv, old, new, B))  # *** recursive call: search deeper ***              

#===================================================== adjust_storelist
def adjust_storelist(sv):
    """
    verify that all values for a store operator are lists and transform them if necessary
    because nature of args must be consistent
    e.g. (',', [('"Hello world"', None, None), None], None)
    """
    for nom in sv.Object_list:                                      # explore objects
        if applied(nom, Store):                                      # look for Store objects
            nod=sv.Object[nom]
            for i, (c,v) in enumerate(nod.clauses):           # look for values in clauses
                if v[0]!=Comma:                                        # not a list
                    v=(Comma, [v, None], None)                # make it a list
                    nod.clauses[i]=(c,v)                               # save clause
    
#===================================================== verif_no_special
def verif_no_special(sv):
    """
    verify that all special characters have been processed
    an error here means there is an attempt to use an unknown function
    """
    prog=reconstruct(sv)                                            # rebuild prog text
    for lig in prog.split(Crlf):                                        # analyze lines
        if Special in lig:                                                  # this char is not allowed
            print("\n", Err_unknown_funct)                      # *** Error: unknown function ***                     
            print(lig)
            here=lig.find(Special)                                     # create explicit error message
            there=lig[here+1:].find(Special)
            block=lig[here+1:here+there+1]
            la=findlast(lig[:here-1], Space)
            lig= lig[:la]+" <"+lig[la+1:here+there+4]+">"+lig[here+there+4:]
            if block in sv.Blocks:
                lig=lig.replace(Space+Special+block+Special, Obr+sv.Blocks[block]+Cbr)
            print(lig)
            raise ReferenceError

#===================================================== storeimplicit
def storeimplicit(sv, triplet=All):
    """
    explore whole program tree to find objects without a definition (implicit)
    recursively analyze subtree to create implicit nodes in sv.Object dict
    an implicit node may be a number, a duration, a state (create a leaf)
    or any expression based on an internal or known name (do not create)
    """
    verbose=('sti' in Debog)
    known=set(Basic_operators+Selectors+Internal_Functions+list(sv.Object.keys())+[Obr])

    if not triplet: return                                               # do not process empty triplets
    if triplet == All:                                                      # analyze whole program
        for code in list(sv.Object_list):                           # scan object list. It will change size during the iteration
            nod=sv.Object[code]
            nom=nod.name
            for (c,v) in nod.clauses:                                 # analyze clauses and create nodes
                storeimplicit(sv, c)                                     # *** recursive call with condition ***
                storeimplicit(sv, v)                                     # *** recursive call with value ***
            if verbose: print("unm    ", sti, Col, nod.clauses)
    else:    
        op,t1,t2=triplet                                                    # conditions and values are now triplets
        if not t1 and not t2 :                                            # not an expression 
            if not op in known :                                         # not already defined
                nod=add_object(sv, op)                              # CREATE object
                if verbose: print("iii              ",nod.name)
            return                                                            
        
        if op==Comma:                                                 # analyze all elements in a list
            for t in t1: storeimplicit(sv, t)                         # *** recursive call with list element ***
        elif t1:                                                                 
            storeimplicit(sv, t1)                                        # *** recursive call with first term ***
        if t2:                                                                   
            storeimplicit(sv, t2)                                        # *** recursive call with second term ***

#===================================================== eliminate
def eliminate(sv, nam):                        
    """
    completely remove objects   
    """
    del sv.Object[nam]                                          # from sv.Object dictionary
    while nam in sv.Object_list:                             # from sv.Object_list
        sv.Object_list.remove(nam)
        
#===================================================== treepluck
def treepluck(sv, tree):            
    """
    returns a list of subtrees found in a tree (first level causes only)
    recurses on expressions, but not on causes (no scan of conditions and values)
    used in solve_user_calls
    """
    if not tree: return []
    verbose=('tpl' in Debog)
    if verbose: print("       treepluck", tree)
    O, A, B = tree
    if not A and not B:
        res=[(O, None, None)]                                                                   # add operator/leaf name to list
    else:                                                                                                   # an expression
        if (O in sv.Object) and sv.Object[O].isfunction:                              # any defined object of form: root(args)
            res=[tree]                                                                                   # just extract tree
        elif O==Comma:                                                                            # a list
            li=[]
            for t in A:                                                                                   # process each element
                li+=treepluck(sv, t)                                                                # *** recurse each list element ***      
            res=li           
        else:                                                                                               # some expression with internal ops
            res=treepluck(sv, A)+treepluck(sv, B)                                        # *** recurse terms and regroup lists ***
            
    li=[]                                                                                                    # remove duplicates (the hard way)
    for i, r in enumerate(res): 
        if not r in res[i+1:]: li.append(r)                                                     # there may be unhashable terms
    return li                                                                                             

#===================================================== make_args_local
def make_args_local(sv):
    """
    identify arguments of user-defined functions and make them virtual and local.
    replace them throughout clauses
    works on a copy of object dict
    calls functions substitute and eliminate
    removes old arg names only if not used elsewhere as real objects
    """
    verbose='loc' in Debog
    userfunc=[]
    argus=[]
##    print("sv.Object_list", sv.Object_list)
    for nom in list(sv.Object_list):                                   # list of objects may be modified in the loop  - here maintain order of definitions
        if verbose: print("Makelocal", nom, sv.Object_list) 
        if not nom in sv.Object:                                        # a name has been removed (made local)
            pass
        elif sv.Object[nom].isuserfunc:                              # get user function instances
            if userfunc and nom!=userfunc[0][1]:
                make_local(sv, userfunc)
                userfunc=[]                                                   # end of previous function definition
            c, vlist=sv.Object[nom].clauses[0]                    # first clause: (condition, value), value is a node with list of args
            if verbose: print("\nvlist for", nom, Col, vlist)
            if not vlist or not vlist[1] or vlist[0]!=Comma:   # check form is ok
                print("\n", Err_no_instance)                           # *** Error: cannot find function instances ***                             
                print(nom)
                raise ReferenceError
            A=vlist[1]                                                          # expecting (',', [(argname1, None, None), (argname2, None, None)...], None)
            if verbose: print("A:", A)                                    # list of args [(argname1, None, None), (argname2, None, None)...]

            # rebuild definition name and local definition from args (adding 'root.' prefix to args)
            argus=[]                                                           # list of all args not local 
            localargs=[]                                                     # list of all args made local 
            li=[]                                                                  # list of local triplets
            expr=nom+Obr                                               # start text with 'root('
            localexpr=expr                                                # local text 
            for t in A:                                                         # get each argument 
                if t is not None: 
                    ar=t[0]                                                     # argument name
                    if ar.startswith(nom+Dot): localar=ar     # no change if already local
                    else: localar=nom+Dot+ar                      # add prefix
                    argus+=[ar]                                             # add to list of all args not local 
                    localargs+=[localar]                                # add to list of all args made local 
                    li+=[(localar, None, None)]                     # add to list of local triplets
                    if expr!=nom+Obr:                                  # not first argument 
                        expr+=Comma                                    # prefix with comma  
                        localexpr+=Comma 
                    expr+=ar                                                 # text list, non local 
                    localexpr+=localar                                  # text list, local 
            expr+=Cbr                                                      # close brackets
            localexpr+=Cbr                                               # close brackets
            
            if verbose: print("  processing", expr, argus, "\n  -->", localexpr, localargs)
            
            for nm in localargs:                                          # names of new nodes
                if verbose: print("local arg:", nm)
                add_object(sv, nm)                                       # create node
                sv.Object[nm].isvirtual=True                        # make arg virtual

            userfunc+=[(nom, expr, localexpr, argus, localargs, li)]
            if verbose: print("userfunc:", userfunc)
            
        elif isprime(nom) and not nom in argus:              # process accessory variable
            if not userfunc:
                print("\n*** Error: accessory variable is not part of a function definition ***", nom)
                raise ReferenceError
            funcname=userfunc[0][0]
            localexpr=funcname+Dot+nom                       # local name for accessory variable
            expr=nom
            if verbose: print("creating accessory variable:", localexpr)
            argus+=[expr]
            localargs+=[localexpr]
            li+=[(localexpr, None, None)]                           # add to list of local triplets
            userfunc+=[(funcname, expr, localexpr, argus, localargs, li)]

        else:
            if userfunc and nom!=userfunc[0][1]:
                make_local(sv, userfunc)
                argus=[]
                userfunc=[]                                               # end of function definition
                if verbose: print("userfunc:", userfunc)
            
    if userfunc: make_local(sv, userfunc)
    existing=Fixed[:]+[Start]                                          # detect used objects 
    for nom in sv.Object_list:
        nod=sv.Object[nom]
        if nod.isdefined:
            existing+=[nom]                                              # keep defined objects
            for c,v in nod.clauses:                                       # explore their conditions and values
                existing+=treesearch(sv, c)+treesearch(sv, v)  # also keep their first level causes
            
    for nom in list(sv.Object_list):                                       # remove unused args from object dict and list
        if not nom in existing: 
            if verbose: print('eliminating2', nom)
            eliminate(sv, nom)

##    print("xxxx after elim\n", reconstruct(sv))
   
#===================================================== make_local
def make_local(sv, userfunc):                        
    """
    create local objects and link local references   
    """
    verbose='loc' in Debog
##    print("userfunc", userfunc)
    nom=userfunc[0][0]
    li=userfunc[-1][-1]
    sv.Object[nom].clauses[0]=((Start, None, None), (Comma, li, None))  # create list of localargs (needed for getargs)

    for funcname, expr, localexpr, argus, localargs, li in userfunc:
        if verbose: print("creating:", localexpr)             # make new function or variables
        add_object(sv, localexpr)                                  # create object for text list of local args 
        nd.copynode(sv.Object[expr], sv.Object[localexpr]) # copy object attributes
        sv.Object[localexpr].clauses=[]                         # clear all clauses
        for i, (c,v) in enumerate(sv.Object[expr].clauses): # new clauses
            k=substitute(c, argus, localargs)                   # modify all names in condition
            w=substitute(v, argus, localargs)                  # modify all names in value
            sv.Object[localexpr].clauses+=[(k,w)]           # add this clause 
        sv.Object[localexpr].isuserdef=True                 # mark this object for later destruction

    for funcname, expr, localexpr, argus, localargs, li in userfunc:
        if verbose: print('eliminating1', expr)
        eliminate(sv, expr)                                            # remove old function from object dict and list
    
#===================================================== solve_user_calls
def solve_user_calls(sv, tree=All, userlist=[]):
    """
    identify and solves user function calls
    these calls do not have a real definition
    but may appear in definitions of defined objects
    use treepluck to identify these objects
    processes all program if expr is 'all'
    userlist is a list of user-defined function names
    userdeflist is a list of virtual user definitions: name(args)
    recursively replaces user function calls with their definition
    replaces virtual arguments with real ones
    argnames (real args) may be:
    - a single value or list name
    - an expression
    - a list of elements
    """
    verbose=('suc' in Debog)
    if tree==All: 
        userlist=[x for x in sv.Object_list if sv.Object[x].isuserfunc]                # create list of user-defined function names
        for nom in list(sv.Object_list):                                                             # explore only currently defined objects (more to come)
            for c,v in sv.Object[nom].clauses:                                                   # look for user function calls in clauses
                causelist=treepluck(sv, c)+treepluck(sv, v)                                 # make a list of immediate causes (as trees)
                for cau in causelist:
                    solve_user_calls(sv, cau, userlist)                          # recurse to analyze each object
    else:                                                                                                        # analyze a single cause
        if not tree: return
        expr=treejoin(tree)                                                                             # calculate a name for the tree
        if not(expr in sv.Object and (sv.Object[expr].issolved or sv.Object[expr].isuserdef)):
            
            if not expr in sv.Object:
                nod=add_object(sv, expr)                                                           # create real object
                nod.isnew=True                                                                          # allow expression processing
            else:
                 nod=sv.Object[expr] 
            for fun in userlist:                                                                           # look for user function name
                if applied(expr, fun):                                                                   # expr is a user function call
                    localargs, localexpr, accessories=getargs(sv, fun)                  # get virtual args and name of user function

                    # unify arguments (localargs : virtual, argnames : real)
                    argnames=[tree[1]]                                                                # value or expression
                    if verbose:
                        print('tree:', tree)
                    if tree[1][0]==Comma and len(localargs)>1:                          # virtual arg is a single list
                        argnames=tree[1][1]                                                           # split the list
                    funcargs=localargs[:-len(accessories)] if accessories else localargs[:]
##                    funcargs=[x for x in localargs if not isprime(x[0])]     # virtual args, excluding accessory variables
                    if len(funcargs)!=len(argnames) and len(funcargs)!=1:           # check number of args
                        print("\n", Err_nb_args)                                                       # *** Error: Wrong number of arguments                          
                        print(expr, "-->", fun+str(funcargs))
                        print(len(argnames), "<>", len(funcargs) )
                        raise ReferenceError
                    else:
                        # create accessory variables
                        realargs=[expr]
                        for acc in accessories:
##                            print("acc", acc)
                            realacc=treejoin(tree)
                            realacc=realacc.replace(Obr, Dot)
                            realacc=realacc.replace(Cbr, Dot)
                            realacc=realacc.replace(Comma, Dot)
                            realacc+=acc[len(fun)+1:]
                            if verbose: print('creating:', realacc)
                            add_object(sv, realacc)                                                    # create object for text list of local args 
                            nd.copynode(sv.Object[acc], sv.Object[realacc])             # copy object attributes
                            argnames+=[(realacc, None, None)]
                            realargs+=[realacc]
                        if verbose:
                           print('accessories:', accessories)
                        # substitute real clauses
                        for expr, localexpr in zip(realargs, [localexpr]+accessories):
                            if verbose:
                                print('expr:', expr)
                                print('localexpr:', localexpr)
                                print('localargs:', localargs)
                                print('argnames:', argnames)
                            nod=sv.Object[expr]
                            clauselist=sv.Object[localexpr].clauses                               # get virtual definition clauses
                            newclauselist=[]
                            for cond, vlu in clauselist:
                                c=substitute(cond,localargs,argnames)
                                v=substitute(vlu,localargs,argnames)
                                newclauselist.append((c,v))
                            nod.clauses=newclauselist                
                            nod.isnew=False                                                                   # forbid expression processing
                            nod.issolved=True                                                                # avoid reprocessing name
                            nod.isdefined=True                                                              # apparently needed later (runtime?): could try issolved instead
                            nod.isuserdef=False                                                             # avoids virtual tagging and destruction
                            if verbose:
                                print("clauselist:", clauselist)
                                print("newclauselist:", newclauselist)

                            # recursively explore name and clauses for implicit object and compound function
                            causelist=[]
                            for c,v in newclauselist:                                                         # look for more 
                                causelist+=treepluck(sv, c)+treepluck(sv, v)                    # make a list of immediate causes
                            if verbose: print("causelist", causelist)
                            for cau in causelist:                                                               # n.b. there may be duplicates 
                                expr=treejoin(cau)
                                if not(expr in sv.Object and (sv.Object[expr].issolved or sv.Object[expr].isuserdef)):
                                    if verbose: print("now solving", cau)
                                    solve_user_calls(sv, cau, userlist)                # recurse to analyze each object               
                        break                                                                                        # function name found: break loop
        if tree and (tree[1] or tree[2]):                                                              # process tree branches
            if tree[0]==Comma:
                for t in tree[1]:
                    solve_user_calls(sv, t, userlist)                                # recurse to analyze each list element
            else:
                solve_user_calls(sv, tree[1], userlist)                           # recurse to analyze each branch  
                solve_user_calls(sv, tree[2], userlist)            

#===================================================== substitute
def substitute(tree, oldlist, newlist):
    """
    recursively replace terms (leaves/ops) in a tree
    without changing tree structure or order
    used in solve_user_calls to change argument names
    used in make_args_local and solve_user_calls
    """
    verbose=('sbt' in Debog)
    if not tree: return None
    res=tree[:]
    if verbose:
        print("oldlist", oldlist)
        print("newlist", newlist)
        print("res", res)
    if res in oldlist:                                               # replace a branch
        for num, ol in enumerate(oldlist):              # search list for branch
            if ol==res:
                res=newlist[num]                           # replace with new value at same rank
    elif (res[0], None, None)  in oldlist:                 # replace a branch
        for num, ol in enumerate(oldlist):              # search list for branch
            if ol[0]==res[0]:
                if newlist[num][1] or newlist[num][2]:   # priority to new tree
                    res=newlist[num]
                else:
                    res=(newlist[num][0], res[1], res[2])  # replace with new value at same rank
    o,A,B=res    
    if o==Comma:                                               # special case: lists                               
        li=[]
        for x in A:
            li+=[substitute(x, oldlist, newlist)]         # *** recurse for each element ***
        res=(Comma, li, None)
    else:
        n=o                                                            # not a list
        for num, ol in enumerate(oldlist):              # search list for leaf/op
            if ol==o:
                n=newlist[num]                                 # replace leaf/op with new value at same rank
        res=(n, substitute(A, oldlist, newlist), substitute(B, oldlist, newlist)) # *** recurse operands ***
##    if tree!=res: print("replaced", tree, "with", res)  
    return res  

#===================================================== getargs
def getargs(sv, nom):
    """
    Return virtual arguments and defined name for a function.
    used in solve_user_calls
    """
    # get user function instances
    c, vlist=sv.Object[nom].clauses[0]                                                    # first clause: condition, value: a node with list of args
    if vlist:
        op,A,B=vlist                                                # expected (',', [(argname1, None, None), (argname2, None, None)...], None)
    localargs=[]
    accessories=[]
    localexpr=nom+Obr                                                                        # re-build local definition 
    for t in A:
        if t is not None:                                               
            localar=t[0]                                                                              # argument name
            localargs+=[(localar, None, None)]
##            if isprime(localar):
            if not sv.Object[localar].isvirtual:
                accessories+=[localar]
            else:
                localexpr+=localar if localexpr==nom+Obr else Comma+localar
    localexpr+=Cbr
    return localargs, localexpr, accessories   
  
#===================================================== isprime
def isprime(nom):            
    """
    returns True if nom ends with Prime or if nom is a subscripted Prime variable
    """
    if nom.endswith(Prime): return True
    first, block, last=findblock(nom)                             # identify root
    if block:
        if nom[:first].endswith(Prime): return True
    return False

#===================================================== treesearch
def treesearch(sv, tree):            
    """
    returns a list of objects found in a tree (first level causes only)
    recurses on expressions, but not on causes (no scan of conditions and values)
    used in make_args_local, findcauses, novirtual
    does not modify tree
    """
    if not tree: return []
    verbose=('trs' in Debog)
    if verbose: print("       treesearch", tree)
    O, A, B = tree
    if not A and not B:
        res=[O]                                                                                           # add operator/leaf name to list
    else:                                                                                                    # an expression
        if (O in sv.Object) and sv.Object[O].isfunction:                              # any defined object of form: root(args)
            expr=tree                                                                                   # just extract name (reconstructed)
            res=[treejoin(expr)]                                                                    # extract expression name 
        elif O==Comma:                                                                            # a list
            li=[]
            for t in A:                                                                                   # process each element
                li+=treesearch(sv, t)                                                              # *** recurse each list element ***      
            res=li           
        else:                                                                                               # some expression with internal ops
            res=treesearch(sv, A)+treesearch(sv, B)                                    # *** recurse terms and regroup lists ***     
    return list(set(res))                                                                             # remove duplicates

#===================================================== make_clauses
def make_clauses(sv, name=Special):
    """
    creates start clause for undefined (implicit) objects (not expressions)
    assign object name as start value
    do not modify object that already have clauses
    """
    if name==Special:                                                                             # cannot use 'All' here (valid name)
        for nom in sv.Object_list:                                                              # scan program
            nod=sv.Object[nom]
            if Comma in nom:                                                                     # object is a list 
                li=splitlist(nom)
                for t in li:
                    make_clauses(sv, t)                                                           # *** recurse for each element ***
            else:
                make_clauses(sv, nom)                                                         # *** recurse for each name ***
    elif name in sv.Object:                                                                      # process a single name
        nod=sv.Object[name]
        if not nod.clauses : nod.clauses=[(Starttree, (name, None, None))] # only objects without clauses                        

#===================================================== link_list_change
def findtree(sv, subtree, tree=All):
    """
    looks for subtree in program clauses and returns true if found
    recursive
    """
    if tree is None: return False
    if tree==All:
        for nom in sv.Object_list:                                                  # scan program
            nod=sv.Object[nom]
            claulist=nod.clauses
            for c,v in claulist:                                                          # scan clauses
                if subtree in [c,v]:
                    return True
                if findtree(sv, subtree, c): return True                      # recurse on condition
                if findtree(sv, subtree, v): return True                      # recurse on condition
        return False
    O,A,B=tree                                                                          # explore a branch
    if O==Comma:                                                                    # special case: list
        for x in A:
            if subtree==x: return True
            if findtree(sv, subtree, x): return True                          # recurse on each element
    else:
        if subtree==A: return True
        if subtree==B: return True
        if findtree(sv, subtree, A): return True                             # recurse on first term
        if findtree(sv, subtree, B): return True                             # recurse on second term         

#===================================================== link_list_change
def link_list_change(sv):
    """
    creates clauses for deep changes in lists
    works only for static lists that do not change elements
    """
    for name in sv.Object_list:                                                    # use list of objects
        nod=sv.Object[name]
        if nod.isfunction:                                                               # either a "dict" or a user defined function    
            chg=Change+Obr+name+Cbr
            if findtree(sv, (Change, (name, None, None), None)):   # look for change(list)
                add_object(sv, chg)                                                   # create change(list) object
                add_object(sv, str(Change_time))
                clau=((Plus, (chg, None, None), (str(Change_time)+"s", None, None)),(Faux, None, None))
                if not clau in sv.Object[chg].clauses:                        # clause to reset change
                    sv.Object[chg].clauses+=[clau]
                for block, lig in nod.arguments:
                    clau=((Change, (name+Obr+block+Cbr, None, None), None),(Vrai, None, None))  # link change
                    if not clau in sv.Object[chg].clauses:
                        sv.Object[chg].clauses+=[clau]

#===================================================== expressionsearch
def expressionsearch(sv, tr=All):
    """
    create a cache for expressions
    processes all program if tr==All
    each expression gets reduced to one single operation
    iterate until no more change
    recursive call to create and link new expression names
    uses .isuserfunc and .isuserdef to avoid creating inappropriate expressions
    .isuserfunc marks user-defined function names
    .isuserdef marks a virtual argument which must ultimately disappear
    creates and links expression nodes 
    updates object dict and object clauses
    expects a standard tree object, or None
    returns a standard tree object, or None
    """    
    verbose=('xps' in Debog)
    # process all program
    if tr==All:
        done=False                                                                              # iterate until no more change        
        while not done:
            done=True                                                                           # set to False whenever there is a change                                                             
            if verbose:
                print("\n============================making expressions:\n")
            # build expressions from clauses
            for nom in list(sv.Object_list):                                                   # dict is modified in loop: use a copy
                nod=sv.Object[nom]
                if not nod.isuserdef and not nod.isuserfunc :                 # do not create inappropriate expressions
                    li=[]
                    if verbose: print()
                    if verbose: print(nom, Col)
                    for c,v in nod.clauses:                                                  # explore clauses                    
                        k,w=c,v                                                                    # copy of condition and value (may change)
                        
                    # cache condition            
                        if k:
                            if not (k[0] in [Always, Start]+Glitch_list):             # add 'begin' to condition if not op in [Begin, End, Change, Always]
                                k=(Begin, k, None)                                           
                            k=(k[0], expressionsearch(sv, k[1]), None)           # skip one level
                            if k!=c: done=False                                              # a change has occurred
                            
                    #cache value      
                        if treejoin(w)!=nom:                                                  # do not create circular ref  
                            if w and w[0] in Glitch_list:                                    # do not cache [Begin, End, Change]   
                                if w[1] and (w[1][1] or w[1][2]): w=(w[0], expressionsearch(sv, w[1]), None)                        
                            else:
                                if w:
                                    if w[0]==Comma:
                                        w=expressionsearch(sv, w)                       # process list                                                                                    
                                    else:                                                                                            
                                        if ( w[1] and ( w[1][1] or w[1][2]) ) or \
                                           ( w[2] and ( w[2][1] or w[2][2]) ):            # do not cache a single operation                                                                                        
                                                 w=(w[0], expressionsearch(sv, w[1]), expressionsearch(sv, w[2]))         
                            if w!=v: done=False
                    # store result
                        li+=[(k,w)]                                                                 # store one clause
                        if verbose:
                            print(nom, Col, When, c, Col, v)
                            print("--->", k, Col,w)
                                
                    if li: nod.clauses=li[:]                                                     # store list of clauses
            
        if verbose:                                                                                 # display all objects and clauses
            for nod in list(sv.Object.values()):
                print(Crlf, nod.name, Col)
                print("   ", nod.clauses)
                print()

    #process a single expression, recursively
    else:                                                                                              # expression, not full program 
        if not tr: return None                                                                # nothing to do
        if verbose: indprint(" expression search", treejoin(tr))
        if verbose: indprint("", str(tr))
        sv.Indent="    "+ sv.Indent                                                       # for debugging purposes

        tree=tr[:]                                                                                  # make copy to modify
        o,A,B=tree

        if o==Obr:                                                                               # bracketed expression: skip brackets 
            sv.Indent=sv.Indent[:-4]
            if verbose: indprint(" bracket")
            return expressionsearch(sv, A)                                            # *** recurse without brackets and return ***

        nom=o                                                                                    # e.g.  (,) --> ","
        if A or B:                                                                                  # not a leaf
            nom=treejoin(tree)                                                             # compute expression name if not a leaf
            
        else:                                                                                        # test leaf is legal
            if o in Internal_Functions:
                print("\n", Err_no_arg)                                                     # *** Syntax error: function without arguments ***                         
                print(o)
                print(nom)
                raise ReferenceError

        if Space in nom:                                                                      # expressions should not contain spaces
            bad=False
            inside=False
            for c in nom:                                                                       # check all spaces are inside quotes
                if c==Quote: inside=not inside
                if c==Space and not inside: bad=True
            if bad:
                print("\n", Err_space_in_name)                                       # *** Syntax error: incorrect expression ***                     
                print(nom, Col)
                print(tree)
                raise ReferenceError

        if nom in sv.Object and not sv.Object[nom].isnew:               # don't replace existing name unless new user call
            nod=sv.Object[nom]                                                         # use old name 
            if verbose: indprint(nom, "exists:\n", nod.clauses)
            
        else:                                                                                        # create a new node          
            if verbose: indprint("making", nom)
            nod=add_object(sv, nom)                                                  # create object
            nod.isexpression=True
            nod.isnew=False                                                                 # process only once
            if verbose: indprint(" -->", nod.content(), "expression")
                
            # link expression (only for new nodes)
            if o==Comma:                                                                     # special case: list: clause for each changing element
                li=[]
                for t in A:
                    exprs=expressionsearch(sv, t)                                     # *** recurse for each element ***
                    if exprs: li=li+[exprs]
                vlu=(o, li, None)                                                               # list of elements 
                nod.clauses=[(Starttree,vlu)]                                            # start clause for whole list                         
                for t in li:                                                                           # each term is a triplet
                    if t and not isnumber(t[0]) and not isduration(t[0]) and not t[0] in Fixed:     # these objects never change (but beware of Start)                              
                        cl=((Change, t, None),vlu) if not t[0]==Change else (t,vlu)      # make change clauses from elements to whole list         
                        if not cl in nod.clauses: nod.clauses+=[cl]                # avoid duplicates                            
                if verbose : indprint("value:", str(vlu))
                sv.Indent=sv.Indent[:-4]
                return (nom, None, None)

      # some sort of expression
            exprsA=expressionsearch(sv, A)
            exprsB=expressionsearch(sv, B)
            vlu=(o, exprsA, exprsB)                                                        # reduce to a simple operation between two expressions 
            if verbose : indprint("value:", str(vlu))

        # make start clauses, and change clause for non-fixed objects (do not repeat 'change')
            nod.clauses=[(Starttree,vlu)]                         
            if o in sv.Object and not isnumber(o) and not isduration(o) and not o in Fixed: # Fixed: [Vrai, Faux, Start, Epsilon, Empty]
                nod.clauses+=[((Change, (o, None, None), None),vlu)] if not o==Change else [((o, None, None),vlu)]  
            if A and not isnumber(A[0]) and not isduration(A[0]) and not A[0] in Fixed:                                    
                nod.clauses+=[((Change, exprsA, None),vlu)]  if not A[0]==Change else [(exprsA,vlu)]  
            if B and B!=A and not isnumber(B[0]) and not isduration(B[0]) and not B[0] in Fixed:                                      
                nod.clauses+=[((Change, exprsB, None),vlu)] if not B[0]==Change else [(exprsB,vlu)]
                
            if o==Since:                                                                           # special case: conditions for "since"                                                                               
                pl=expressionsearch(sv, (Plus, exprsB, exprsA))                # event+delay                               
                nod.clauses[-1]=((Change, pl, None), vlu)                         # when change(event+delay): (Since, exprsA, exprsB)        
                nod.clauses+=[((Change, exprsB, None), vlu)] if not B[0]==Change else [(exprsB,vlu)] # when change(event)...
                exprsC=Starttree                                                               
                pl=expressionsearch(sv, (Plus, exprsC, exprsA))                # n.b. changing delay during 'since' should have no effect
                nod.clauses+=[((Begin, pl, None), vlu)]                             # when start+delay: (Since, exprsA, exprsB)   
                
            if verbose:
                indprint("  expression:", nom+Col)
                for clau in nod.clauses:
                    indprint( "    ", When+Space+treejoin(clau[0])+Col+Space+treejoin(clau[1]))

        sv.Indent=sv.Indent[:-4]
        return (nom, None, None)
        
#===================================================== findcauses
def findcauses(sv):
    """
    extract causes from program using treesearch
    returns for each object a list of first order causes
    exclude object itself
    """
    verbose= 'fca' in Debog
    partial= 'cau' in Debog
    if verbose: print("\n============================findcauses:\n")
    
    for nom in sv.Object_list:
        nod=sv.Object[nom]
        nod.causes=[]
        counted=applied(nom, Count)                            # important for display
        if counted: nod.causes=[counted]
        showed=applied(nom, Show)
        if showed: nod.causes+=[showed]
        if verbose: print("    exploring", nom)
        if nod.clauses:                                                     # explicit causes
            for (c,v) in nod.clauses:
                if verbose: print("       ", c,v)
                found=nod.causes
                found+=treesearch(sv, c)                           # objects in condition
                found+=treesearch(sv, v)                           # objects in value
            nod.causes=list(set(found))                            # remove duplicates
            if nom in nod.causes: nod.causes.remove(nom) # exclude self
        
    if verbose or partial:
        print()
        for nod in list(sv.Object.values()):
            print("causes["+nod.name+"]:\n  ", nod.causes)
            
#===================================================== relations
def relations(sv):
    """
    extract effects from program:
    returns for each object a list of immediate effects (itself included)
    """    
    verbose= 'rel' in Debog
    if verbose: print("\n============================RELATIONS:\n")

    for eff in sv.Object_list:
        nod=sv.Object[eff]
        for nom in nod.causes:                             # look for nodes of causes
            if not nom in sv.Object:
                print(Err_unknown_object)
                print (nom)
                raise ReferenceError
            cau=sv.Object[nom]
            if not eff in cau.effects: cau.effects+=[eff]

    if verbose:
        for nom in sv.Object_list:
            nod=sv.Object[nom]
            print("effects["+nom+"]:\n  ", nod.effects)

#===================================================== consequences
def consequences(sv, nom, found=[]):                                                           
    """
    recursively explore possible ultimate effective consequences and return their list
    based on Effective=[Exit, Call, Output, Store, Display, Dialog, Print]
    ignore dict
    """
    if type(nom)==list or not nom in sv.Object: return []                              # stop at lists
    if nom in found: return []                                                                          # avoid duplicates
    more=found+[nom]
    if nom in Effective: return [nom]                                                              # objects with effects        
    for eff in sv.Object[nom].effects:                                                              # explore effects
       if not eff in more:                                                                                  # avoid circularity
            more+=[eff]
            csq=consequences(sv, eff, more)
            more=list(set(more+csq))
    return more

#===================================================== unchanging
def unchanging(sv):                             
    """
    remove clauses "change" "begin" or "end" concerning constants
    plain numbers, plain durations, Fixed objects, Load             
    does not consider Booleans with value 'true' as constants
    completed by removechangeconst after initialization
    """
    for nom in sv.Object_list:
        nod=sv.Object[nom]
        cl=[]                                                      # initialize new clause list 
        for c,v in nod.clauses:
            ok=True
            if c and c[0]==Change:                     # look for change condition
                if c[1]:
                    op=c[1][0]                                # look for constant value
                    if isnumber(op) or isduration(op) or op in Fixed \
                       or applied(op, Load):               
                        ok=False                    
            if ok:
                cl+=[(c , v)]
        nod.clauses=cl[:]                                   # accept clause

#===================================================== findnature
def findnature(sv, tree, hint=All_natures):
    """
    identify nature of a single object or expression, defined by a tree
    nature is a list to be reduced to a single element
    used by determine
    uses getnature, which works on name, not tree
    """
    verbose=('fnt' in Debog)
    if not tree: return []                                                                  # empty tree: no nature
    expr=treejoin(tree)                                                                  # compute name of object
    if verbose: print("\n  findnature:", expr, tree)
    O, A, B=tree                                                                             # decompose tree   
    
    if O==Obr: return findnature(sv, A, hint)                                 # skip brackets

    if expr in sv.Object:
        result=getnature(sv, expr, sv.Object[expr].nature)              # nature may be obvious
        if verbose: print("     for tree",(O,A,B), sv.Object[expr].nature, "getnature returned", result)
        result=list(set(result) & set(hint))                                        # check compatibility
        if verbose: print("            when including", hint, "gives", result)
        if set(sv.Object[expr].nature)!=set(result):
            if verbose: print("         SetG", expr,".nature = ", result)
            sv.Object[expr].nature=result[:]                                       # set new nature
    else:                    
        if verbose: print("    ", expr, "is not in object dict", tree)    # some expressions
        nod=add_object(sv, expr)                                                  # create extra node
        nod.isvirtual=True                                                              # temporary node
        nod.nature=hint[:]
        result=hint[:]

    # more info from operator and operands (recursively), even if we have already found result 
    if O in Allowed and (A or B):                                                    # constraints on operations
        x=treejoin(A)                                                                       # name of operands
        y=treejoin(B)
        n1=All_natures[:] if not x in sv.Object else sv.Object[x].nature[:]  # current nature of operands
        n2=All_natures[:] if not y in sv.Object else sv.Object[y].nature[:]
        if verbose: print("     now combining", x, n1, O, y, n2)
        if O in [Any, All]:                                                                      # use info on event lists
            result=Bln[:]
            nat1=Lst[:]
            nat2=[]
            if x in sv.Object: evlis=sv.Object[x].value                             # extract list of elements
            if evlis:
                for z in evlis:                                                                    # make them events
                    if z in sv.Object: sv.Object[z].nature=Bln[:]
        elif O == Pick:                                                                         # use info on event lists
            result=Lst[:]
            nat1=Lst[:]
            nat2=Lst[:]
            if y in sv.Object: evlis=sv.Object[y].value                            # extract 2nd list of elements
            if evlis:
                for z in evlis:                                                                   # make them events
                    if z in sv.Object: sv.Object[z].nature=Bln[:]
        else:
            nat1, nat2, more=combine(sv, O, n1, n2, result)                # find possible nature combinations
            result=list(set(result) & set(more))                                     # check compatibility
        n1=list(set(n1) & set(nat1))        
        n2=list(set(n2) & set(nat2))
        
        if x in sv.Object:                                                                      # apply new nature to operands
                if verbose: print("             SetX", x+".nature = ", n1)           
                sv.Object[x].nature=n1[:]
        if y in sv.Object:                                                                     # apply new nature to operands
                if verbose: print("             SetY", y+".nature = ", n2)           
                sv.Object[y].nature=n2[:]
           
    if verbose: print("     found nature of", expr, result)
    return result
    
#===================================================== combine
def combine(sv, O, n1, n2, nres):
    """
    combine natures n1 and n2 using O and nature of result (if known)
    returns nature of operands and result, or []
    """
    verbose=('cmb' in Debog)
    li1=n1
    li2=n2
    lires=nres   
    if O in Allowed:# and len(li1)>1 or len(li2)>1 or len(lires)>1:
        if verbose: print("     combine", n1, [O], n2, ">", nres)
        li1=[]
        li2=[]
        lires=[]   
        for nat1, a1, nat2, a2, natres, ar in Allowed[O]:                              # determine the various possibilities
            if verbose: print("           testing", [O], nat1, nat2)
            s1=list(set(nat1) & set(n1))                                                        # test compatibility of hypothesis
            s2=list(set(nat2) & set(n2))
            sres=list(set(natres) & set(nres))             
            if verbose: print("           >>", s1,s2,sres)
            if (sres and s1 and (s2 or O in Unary)):                                      # hypothesis is valid
                li1+=s1                                                                                  # add to list of possible natures
                if not(O in Unary): li2+=s2
                lires+=sres
            if not (O in Non_distributive1) and Lst[0] in n1 and Lst[0] in nres: # allow distributivity on the left
                li1+=Lst                                                                                
                if not(O in Unary): li2+=s2
                lires+=Lst
            if not (O in Non_distributive2) and not (O in Unary) \
                                            and Lst[0] in n2 and Lst[0] in nres:                 # allow distributivity on the right                
                li1+=s1
                li2+=Lst
                lires+=Lst
        
    li1=list(set(li1))                                                                                 # remove duplicates
    li2=list(set(li2))
    lires=list(set(lires))
    if verbose: print("       li1", li1, "li2", li2,"lires", lires)
    if not lires or not li1:  
        print("\n", Err_incomp_nat)                                                          # ***Error: incompatible nature ***                         
        print(n1, n2, O) 
        raise ReferenceError
    return li1, li2, lires
    
#===================================================== determine
def determine(sv):
    """
    identify nature of all expressions and nodes
    Nmbr, Drtn, Bln, Stt, Lst
    loop until total number of possible natures stops decreasing
    also detects delayed objects for later
    """
    verbose=('dtr' in Debog)
    partial=('nto' in Debog)
    tot=0                                                                                  # tot is scoring the number of possible natures
    for nom in sv.Object_list:
        nod=sv.Object[nom]
        if len(nod.nature)!=1:
            if verbose: print("initializing", nom)
            nod.nature=All_natures[:]           # initialize
        tot+=len(nod.nature)
    prev=tot+1                                                                        # prev is keeping track of last score
    done=False
    
    while not done:                                                                  # loop until score does not progress + 1 loop
        if verbose: print("\n*** tot", tot, "prev", prev, "done", done)       
        done=(tot==prev)
        prev=tot
        for nom in list(sv.Object_list):                                             # use copy. Known objects may help determine related objects
            if verbose: print("\nDetermine", nom, Col)
            nod=sv.Object[nom] 
            natres=getnature(sv, nom, nod.nature)                    # current or obvious nature   

            if verbose: print("  exploring clauses of", nom, natres)
            for c,v in nod.clauses:                                                # explore conditions and values
                if verbose: print("\n  clause", (c,v))
                sv.Current_clause=(nom, c, v)
                
                expr=treejoin(c)                                                    # force Boolean nature on condition
                if expr in sv.Object and sv.Object[expr].nature!=Bln:
                    if verbose: print("  forcing event nature on condition", expr, c)
                    sv.Object[expr].nature=Bln[:]
                    if verbose: print("  forcing event nature on condition", expr, c)
                if c[0]!=Change:                                                     # repeat on subcondition begin or end, not change
                    expr=treejoin(c[1]) 
                    if expr in sv.Object and sv.Object[expr].nature!=Bln:
                        if verbose: print("  forcing event nature on condition", expr, c[1])
                        sv.Object[expr].nature=Bln[:]

                expr=treejoin(v)                                                    # reflect new nature on value itself
                x=All_natures[:]
                if expr in sv.Object:
                    x=sv.Object[expr].nature[:]                               # look for nature of value
                if verbose: print("  look for nature of value", v, x)
                x=findnature(sv, v, x)
                if verbose: print("  found nature of value", v, x)
                natres=list(set(natres) & set(x))                          # restrict nature based on value
                if not natres:                                                       # check compatibility with object nature
                        print("\n", Err_conflict_nat)                         # ***Error: nature conflict ***
                        print(nom+Col, natres, x)
                        raise ReferenceError
                if expr in sv.Object and set(natres)!=set(All_natures) and set(sv.Object[expr].nature)!=set(natres):
                    if verbose: print("  reflecting", nom, natres, "in", expr, sv.Object[expr].nature)  
                    sv.Object[expr].nature=natres[:]                  

                # delayed objects   
                if v:
                    if natres==Bln:                                                # mark as delayed     
                        if v[0]==Plus or v[0] in Glitch_list:
                            nod.isdelayed=True                                              
                
            if set(natres)!=set(All_natures) and set(nod.nature)!=set(natres):
                if verbose: print("Setting", nod.name+".nature =", natres)
                nod.nature=natres[:]

            first, block, last=findblock(nom)                             # identify roots as lists
            if block:
                rt=nom[:first]
                if rt in sv.Object:
                    if verbose: print("Setting root", rt+".nature = Lst")
                    sv.Object[rt].nature=Lst[:]
                
        tot=0                                                                           # recompute total
        for nom in sv.Object_list:
            nod=sv.Object[nom]
            tot+=len(nod.nature)
        done=(tot==prev)

        if done:                                                                        # one more pass to remove undetected lists
            for nom in sv.Object_list:
                nod=sv.Object[nom]
                if len(nod.nature)==2 and Lst[0] in nod.nature:
                    nod.nature=[nod.nature[1]] if nod.nature[0]==Lst[0] else [nod.nature[0]]
                    if verbose: print(nom, "is not a list but a", nod.nature[0])
                    done=False                                                     # resume processing 

        if done:                                                                        # one more pass for states
            for nom in sv.Object_list:
                nod=sv.Object[nom]
                if len(nod.nature)>1 and Stt[0] in nod.nature:
                    if verbose: print("making state", nom)
                    nod.nature=Stt[:]
                    done=False                                                    # resume processing 
        
    for nom in list(sv.Object_list):                                       # eliminate extra nodes created by findnature
        nod=sv.Object[nom]   
        if nod.isvirtual: eliminate(sv, nom)
            
    if verbose or partial:                                                       # display results
         print("\nNatures:")
         for nom in sv.Object_list:
            nod=sv.Object[nom]
            print(nod.content())

 #===================================================== cleanuserf
def cleanuserf(sv):                        
    """
    completely remove virtual objects   
    """
    markvirtual(sv)                                                               # hide virtual objects 
    noroot(sv)                                                                      # make functions dict
    for nom in list(sv.Object_list):
        nod=sv.Object[nom]
        if nod.isvirtual: eliminate(sv, nom)

#===================================================== markvirtual
def markvirtual(sv):
    """
    tags objects as virtual for removal
    .isvirtual: identifies local user function arguments                            
    .isuserfunc: identifies user functions
    .isuserdef: identifies user function definitions to be removed
    """
    chg=True
    while chg:                                                                      # loop until no more change
        chg=False
        for nom in sv.Object_list:
            nod=sv.Object[nom]
            if not nod.isvirtual and not nod.isuserfunc:           # neither virtual nor root
                if nod.isuserdef:                                                # tag user function definitions
                    chg=True
                    nod.isvirtual=True
##                    print("VIRTUAL1", nom)

                else:                                                           
                    for c,v in nod.clauses:                                   # tag objects with virtual causes
                        for x in treesearch(sv, c)+treesearch(sv, v):    # all causes
                            if x in sv.Object and (sv.Object[x].isvirtual or sv.Object[x].isuserdef):
                                chg=True
                                nod.isvirtual=True
##                                print("VIRTUAL2", nom)
                if not nod.isvirtual and Obr in nom:                # tag functions of virtual objects   
                    rot=fromlist(sv, nom)                                  # extract root if any 
                    if rot:
                        bl=applied(nom, rot)                              # extract block
                        if bl:                                                         # argument list
                            for x in splitlist(bl, True):                     # extract and check args
                                if x in sv.Object and (sv.Object[x].isvirtual or sv.Object[x].isuserdef):
                                    chg=True
                                    nod.isvirtual=True                      # tag virtual args
##                                    print("VIRTUAL3", nom)
                                    
##    for nom in sv.Object_list:
##            nod=sv.Object[nom]
##            if nod.isvirtual: print("VIRTUAL", nom)
            
#===================================================== noroot
def noroot(sv):
    """
    converts user functions into lists
    starts with building subscripts from instances
    """
    for nom in list(sv.Object_list):
        nod=sv.Object[nom]
        if nod.isuserfunc:                                           # nom is the root
            li=[]
            for nm in sv.Object_list:                            # scan objects in order of declaration
                if not sv.Object[nm].isvirtual:
                    block=applied(nm,nom)                   # extract arguments if any
                    if block:                                             # object nm is an instance of function nom
                        add_object(sv, block)                    # make a node with subscript
                        li+=[(nm, None, None)]                # make a list of instances
                        
            if not li:                                                      # function not used
                warn("\n"+Warn_never_applied+"\n"+nom)   # *** Warning: function", nom, "is never applied ***                           
                nd.copynode(sv.Object[Faux], nod)      # re-initialize node
                nod.isvirtual=True                                 # mark node for removal

            c=Starttree          
            v=(Comma, li, None)                                 # put list of instances into value
            nod.clauses=[(c,v)]
    
            nod.isdict=True                                         # it is now and ordinary list
            nod.isdefined=True
            nod.isuserfunc=False
            nod.nature=Lst[:]

#===================================================== verify_functions
def verify_functions(sv):
    """
    verify that subscripted objects are defined
    link change if needed
    """
    for nom in sv.Object_list:
        nod=sv.Object[nom]
        root=fromlist(sv, nom)                                      # only objects, not internal functions
        if root and not sv.Object[root].isdefined:                                                  
            print("\n", Err_unknown_funct)                      # *** Error: unknown function ***                     
            print(nom)
            raise ReferenceError
##        chg=Change+Obr+root+Cbr
##        if chg in sv.Object:                                            # change(list) exists
##            add_object(sv, str(Change_time))
##            clau=((Plus, (chg, None, None), (str(Change_time), None, None)),(Faux, None, None))
##            if not clau in sv.Object[chg].clauses:            # clause to reset change
##                sv.Object[chg].clauses+=[clau]
##            clau=((Change, (nom, None, None), None),(Vrai, None, None))  # link change
##            if not clau in sv.Object[chg].clauses:
##                sv.Object[chg].clauses+=[clau]
            
#===================================================== add_object
def add_object(sv, nam):  
    """
    Add a new object without linking it
    test if object already exists
    return object
    """
    if nam in sv.Object:                                        
        return sv.Object[nam]                                     # do not create 
    else:
        nod=nd.Node()                                               # create object
        sv.Object[nam]=nod                                       # add name to object dict (not ordered) 
        sv.Object_list.append(nam)                             # add name to object list (ordered)                         
        nod.name=nam                                              # object name
        return nod

#===================================================== insert_node
def insert_node(sv, nam, causelist=[], setto=None, always_update=False):  
    """
    Create a new node and link it if necessary (done once)
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

#===================================================== similarnames
def similarnames(sv):
    """
    compare object names to detect typing errors         
    detects names that differ by case, by last character or by added character
    """
    ok=True
    names=[os.path.normcase(n) for n in sv.Object_list]         # list names without case
    names.sort()                                                                       # facilitate compare one to the next
    for i, n in enumerate(names[:-1]):                                      # scan whole list
        a,b=n[:-1], names[i+1][:-1]                                             # names minus last char
        c=names[i+1][-1]                                                           # last char in full name
        d=n[-1]                                                                           # last char in full name
        if len(a)>1 and (c <"0" or c>"9") and (d <"0" or d>"9") and a[-1]!=Underscore and b in [a, n]:
            if ok:
                print("")
                ok=False
            warn("\n"+Warn_typing_risk+"\n'"+n+"' / '"+names[i+1]+"'")    # *** Warning: risk of typing error in '"+n+"' or '"+names[i+1]+"' ***                         
            
    if not ok: print("")
            
#===================================================== makevolatiles
def makevolatiles(sv):
    """
    create list of volatile (time-dependent) objects and make their clause Always      
    so that they will be scanned and updated continuously
    """
    sv.Volatile=[]      
    for nam in sv.Object_list:
        if applied(nam, Pointer) :                       # always update pointer after next
            vlu=(Pointer, (applied(nam, Pointer), None, None), None)
            sv.Object[nam].clauses=[((Always, None, None), vlu)]
        if applied(nam, Lasted) :                        # monitor lasted
            sv.Volatile+=[nam]
            vlu=(Lasted, (applied(nam, Lasted), None, None), None)
            sv.Object[nam].clauses=[((Always, None, None), vlu)]
            
#===================================================== reconstruct
def reconstruct(sv):
    """
    reconstruct program from tree
    """
    verbose=('rcs' in Debog)
    prog=""
    more=[x for x in sv.Object if not x in sv.Object_list]
    more.sort()
    for code in sv.Object_list+more:
        nod=sv.Object[code]
        nom=nod.name
        if nom and nom[0]!=Special:
            prog+=nom
            prog+=Col+Space+Crlf
            for (c,v) in nod.clauses:
                if verbose:
                    print(nom+Col)
                    print("ccc",c)
                    print("vvv",v)
                prog+=Space+Space+When+Space+treejoin(c)+Col+Space+treejoin(v)+Crlf                     
    return prog

###===================================================== compile
def wcompile(sv, prog):
    predefined(sv)                                  # initialize useful nodes
    create_defined(sv, prog)                  # BUILD NODE TREE STRUCTURE AND RELATIONS
    treebuild(sv)                                      # parse program into a list of trees
    adjustments(sv)                                # make several modifications for special cases
#    storeimplicit(sv)                                # extract implicit nodes
    make_args_local(sv)                          # make all user function args local
    solve_user_calls(sv)                             # identify and unify user functions
    storeimplicit(sv)                                # extract implicit nodes
##    print(reconstruct(sv))
##    for nom in sv.Object_list: print(nom, Col, sv.Object[nom].clauses) 
    cleanuserf(sv)                                    # eliminate user functions
    verif_no_special(sv)                           # make sure no special character remains  
    make_clauses(sv)                               # create clauses for implicit objects
    link_list_change(sv)                            # clauses for deep list changes 
    expressionsearch(sv)                         # again create nodes for expressions                  
    verify_functions(sv)                            # check if all functions are defined 
##    print(reconstruct(sv))
    findcauses(sv)                                   # identify immediate causes
    relations(sv)                                      # identify effects
##    print(reconstruct(sv))
    determine(sv)                                    # identify nature of variables and expressions
    unchanging(sv)                                  # remove test changes for constants
    similarnames(sv)                                # check similar names 
    makevolatiles(sv)                               # create list of volatile objects and make their clause Always

###===================================================== main
if __name__== "__main__":
    sv=sp.spell()
    Debog="nto"    
    try:
        old=open("..\scripts\essai.txt","r")                   # try precompiling a script and print result            
        tout=old.read()+Crlf                         
        old.close()
        print(tout, "============================================\n")
        prog=pc.precompile(sv, tout)
        print(prog, "\n\n============================================")     
        wcompile(sv, prog)
        
    except ReferenceError:
        nom, c, v = sv.Current_clause       
        sv.Current_clause=nom+Col+Space+When+Space+treejoin(c)+Col+Space+treejoin(v)       
        print(sv.Current_clause)
        print("\n---  PROCESS ABORTED  ---")
        
    print("\n============================================\n")
    if Dumps: print(reconstruct(sv))
##    input(Press_enter)                

