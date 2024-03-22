# -*- coding: ISO-8859-1 -*-
from whand_parameters import *      # options, constants
from whand_tools import *               # common functions
import whand_precompile as pc       # for tests
import whand_sharedvars as sp        # for tests
import whand_io as io                      # for tests
from functools import lru_cache       # cache decorator for speedup

#======================================================= compile
def compile(sv, prog):
    """
    full compilation: convert text from precompile section to a list of trees
    nodes for current script are created in sv instance of class Spell
    build the trees, solve user functions, check structure
    identify causes and effects
    adapt clauses to variability of objects
    infer nature of objects
    called by whand_V2 (main) 
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        prog: a string containing the text of a script
    Returns
    --------
        all information is directly stored in sv
    """
    build_script(sv, prog)                                           # basic construction of the program tree
    user_functions(sv)                                                # identify and solve user function calls
  #print(reconstruct(sv))
    link_list_change(sv)                                              # create clauses for deep list changes
    decompose_expressions(sv)                                  # decompose expressions with intermediate variables
    change_glitch(sv)                                                 # adjust conditions for glitches
  #print(reconstruct(sv))
    causes_and_effects(sv)                                         # identify causes and effects
    last_changes(sv)                                                  # correct subscript structure 
    verifications(sv)                                                   # sanity control
  #print(reconstruct(sv))
    variability(sv)                                                      # adapt clauses to variability of constant and volatile objects
    determine_nature(sv)                                          # infer nature of variables and expressions
    make_lists(sv)


#=====================================================
#                      BASIC CONSTRUCTION OF THE PROGRAM TREE
#===================================================== build_script
def build_script(sv, prog):
    """
    basic construction of the program tree:
    create useful standard nodes, create defined objects
    parse script into tree structure and manage special cases
    called by compile
    Parameters
    -------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    ---------
        all information is directly stored in sv
    """
    predefined(sv)                                          # initialize useful nodes
    lines=prog.split(Crlf)                                 # transform program into a list of lines
    
    make_defined(sv, lines)                            # identify names and functions and create nodes
    make_values(sv, lines)                              # store conditions and values   
    store_function_args(sv)                            # process function arguments
    
    traverse(sv, tree_build)                             # parse script into trees
    adjust_store_list(sv)                                 # make store argument into a list

#===================================================== predefined
def predefined(sv):
    """
    creates and initializes useful standard nodes
    Start +[Vrai, Faux, Epsilon, Empty] as listed in Fixed (in whand_operators.py)
    Booleans (events) are initialized using set_status
    Start is not initialized here (delayed event)
    called by build_script
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for nam in Fixed+[Start]:   
        nod=add_object(sv, nam)                                    # create object
        nod.nature=Bln[:]                                                # default nature for Vrai, Faux, Start     

    sv.Object[Epsilon].nature=Drtn[:]                              # epsilon is a delay
    sv.Object[Empty].nature=Lst[:]                                  # empty is a list
 
    set_status(sv.Object[Vrai], True, 0)                            # true
    set_status(sv.Object[Faux], False, 0)                          # false
    sv.Object[Epsilon].value=str(Epsilon_time)+ 's'         # brief delay
    sv.Object[Empty].value=[]                                        # empty list

    nam==Always                                                        # create 'Always' event
    nod=add_object(sv, nam)   
    nod.value=sv.Object[Vrai].value
    nod.nature=Bln[:]

    # prepare start object
    nod=sv.Object[Start]                                                        
    nod.value=[(0, Glitch_time)]
    nod.isdelayed=True
    nod.occur=[0]
    nod.count=1
    nod.lastchange=0
   
#===================================================== add_object
def add_object(sv, name):  
    """
    add new object 'name' without linking it
    object is not created if object already exists
    update sv.Object and sv.Object_list
    sv.Object is a dict containing all objects
    sv.Object_list is a list of names defined objects in order of appearance and additional objects
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        name: a string
    Returns
    --------
        nod: the object
        all other information is directly stored in sv
    """
    if name in sv.Object:                                        
        return sv.Object[name]                                     # do not create 
    else:
        nod=nd.Node()                                                # create object
        sv.Object[name]=nod                                       # add name to object dict (not ordered) 
        sv.Object_list.append(name)                             # add name to object list (ordered)                         
        nod.name=name                                             # object name
        return nod

#===================================================== make_defined
def make_defined(sv, lines):
    """
    create defined nodes for lines containing object names
    identify functions, user-defined functions and primed arguments
    sv.Object is a dict containing all objects (see add_object)
    sv.Object_list is a list of names of defined objects in order of appearance and additional objects
    called by create_defined
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        lines: a list of script lines in canonic form
    Returns
    --------
        all other information is directly stored in sv
    """
    for num, lig in enumerate(lines):                                  # browse program lines  
        if not lig.startswith(When) and not lig.startswith(Col):  # neither condition nor value -> defined name

        # remove equivalence codes but keep track of them (not yet exploited)
            equiv=None                                                     
            if lig.startswith(Equal+Special):                                        
                lig=lig[len(Equal+Special):]                            # remove equivalence code             
                equiv=lig                                                      # flag object for equivalence
                lines[num]=lig                                              # store abridged line

        # detect duplicate names 
            if lig in sv.Object:                                              
                print("\n", Err_redef_name)                            # *** Error: Node is already defined ***                             
                print(lig)
                raise ReferenceError
            
         # create nodes while preserving the order           
            nod=add_object(sv, lig)                                    # create object
            nod.isdefined=True                                          # flag object as defined
            nod.equivalent=equiv                                      # equivalence flag

        # detect functions and create root node. Save arguments
            here, argtext, last=findblock(lig)                       # find bracketed expression
            if argtext:                                                         # create root for function or dict
                make_root(sv, lig, lig[:here], argtext.strip(Space))

        # verify syntax
            verify_name_syntax(sv, lig, here, argtext, last)

#===================================================== make_root
def make_root(sv, lig, fun, argtext):
    """
    create defined nodes for root of a function or dict (list made of separate elements)
    identify user-defined functions and primed arguments
    sv.Object is a dict containing all objects (see add_object)
    sv.Object_list is a list of names defined objects in order of appearance and additional objects
    called by make_defined
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        fun: a string containing the name of a function
        argtext: a string with arguments of a function or dict
    Returns
    --------
        all information is directly stored in sv
    """
    if not fun in sv.Object:                                          # new function or dict
        nod=add_object(sv, fun)                                   # create node for function root
        nod.isdefined=True                                          # flag object as defined
        nod.isfunction=True                                         # flag object as function
        nod.nature=Lst[:]

        # examine arguments to identify user-defined function or dict
        if detect_user_function(argtext):
            nod.isuserfunc=True                                     # a user-defined function
        else:                     
            nod.isdict=True                                             # a new dict

        # store arguments (first argument for a dict)
        nod.arguments=[argtext]                                     
        
    else:                                                                     # fun already exists
        # add arguments for a dict, not for a user-defined function           
        nod=sv.Object[fun]
        if nod.isuserfunc:
            print("\n", Err_redef_name)                            # *** Error: Node is already defined ***                             
            print(lig)
            raise ReferenceError
        nod.arguments+=[argtext]                                # add arguments to existing dict

#===================================================== detect_user_function
def detect_user_function(argtext):
    """
    verify whether function arguments end with a prime (') --> user-defined-function
    called by make_root
    Parameters
    ------------
        argtext: a string representing arguments of a function or dict
    Returns
    --------
        a Boolean: True for a user-defined-function, False otherwise
    """
    arglist=argtext.split(Comma) if Comma in argtext else [argtext]         
    if is_primed(arglist[0]):                                           # a user-defined function
        for x in arglist:
            if not is_primed(x):
                print("\n*** Error in user-defined function: all args must be prime ***")
                print(name)
                raise ReferenceError
    else: return False                                               # a dict        
    return True

#===================================================== is_primed
def is_primed(nam):
    """
    identify elements of a user-defined function by their name
    Parameters
    ------------
        nam: a string, the name of an object
    Returns
    --------
        a Boolean: True if nam ends with Prime or if nam is a subscripted Prime variable
    """
    if nam.endswith(Prime): return True
    first, block, last=findblock(nam)                             # identify root
    if block and nam[:first].endswith(Prime): return True
    return False

#===================================================== make_values
def make_values(sv, lines):
    """
    add conditions and values to defined nodes (without parsing)
    called by make_defined
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        lines: a list of script lines in canonic form
    Returns
    --------
        all information is directly stored in sv
    """
    for num, lig in enumerate(lines):                                            # browse program lines

    # process conditions and values
        if  lig.startswith(When):                                                      # conditions (unprocessed) 
            clau=no_brackets(lig[len(When):].strip(Space))                # no surrounding spaces or brackets
        elif  lig.startswith(Col):                                                       # values (unprocessed. Normally, clau has been defined)
            if clau is not None:
                vlu=no_brackets(lig[len(Col):].strip(Space))                     # no surrounding spaces or brackets
                nod.clauses+=[((clau, None, None), (vlu, None, None))] # store into list of doublets (condition, value)
                clau=None                                                                # only one value per clause
            else:
                print("\n", Err_empty_name)
                print(lig)
                raise ReferenceError

    # process object names
        else:                                                                                  # neither condition nor value -> defined name
            nod=sv.Object[lig]
            if nod.equivalent:                                        
                nod.equivalent=lines[num+2][len(Col):]                     # equivalent value is two lines down 

#===================================================== verify_name_syntax
def verify_name_syntax(sv, name, here, argtext, last):
    """
    control validity of a declared name
    called by make_defined
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        name: a string with the name of an object or a function
        here: a number giving the position of argument text in lig
        argtext: a string with arguments of a function or dict
    Returns
    --------
        raise syntax error
    """
    if name.find(Equal)!=-1:                                                        # "=" is not allowed in names
        print("\n", Err_equal_in_name, "\n", name)                         # *** Illegal character in name: "+ Equal +" ***                              
        raise ReferenceError

    if not name or here==0:                                                       # name may not start with a bracket
        print("\n", Err_empty_name)                                              # *** Syntax error: empty name ***  
        print(name)
        if num>2:                                                                         # common source of empty name error
            print(Help_continuation+Mline+"' ):")                           # you may have meant (with continuation character '"+Mline):
            print(lines[num-3].strip(Space)+Col, Mline, Crlf, name)  # suggested correction
        raise ReferenceError

    if argtext:                                                                             # name is a function or a dict
        fun=name[:here]
        if fun in Internal_Functions:                                          
            print("\n", Err_redef_internal_func)                                # *** Error: You cannot define an internal function ***                            
            print(fun, "in", fun+Obr+argtext+Cbr)
            raise ReferenceError
        
        if name[last:]:                                                                   # name must end with closing bracket after args
            print("\n", Err_text_after_args)                                       # *** Syntax error: text found after arguments ***                              
            print(name)
            raise ReferenceError
            
#===================================================== store_function_args
def store_function_args(sv):
    """
    reprocess functions to put list of args (text) in clause under function/list name (root)
    create a start clause with a list of all arguments for a user-defined function
    or a list of all elements for a dict
    called by build_script
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for name in sv.Object_list:                                                     # browse list of objects
        nod=sv.Object[name]
        if nod.isfunction:                                                              # either a dict or a user defined function
            vlu=""
            if nod.isdict:                                                                  # a dict
                root=name+Obr
                tail=Cbr+Comma
                for arg in nod.arguments:                                         # extract each element
                    vlu+=root+arg+tail                                              # element with root and brackets, comma to indicate list
            else:                                                                             # a user-defined function
                vlu+=nod.arguments[0]+Comma                              # element with comma to indicate list  
            if len(nod.arguments)>1: vlu=vlu[:-1]                            # remove trailing comma if >1 element 
            nod.clauses=[((Start, None, None), (vlu, None, None))]   # create clause
                
#===================================================== traverse
def traverse(sv, func):
    """
    traverse the whole program to apply func to all conditions and values 
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        func: a function that modifies triplets, often recursively
    Returns
    --------
        all information is directly stored in sv
    """
    for nam in sv.Object_list:                                      # scan all objects
        sv.Current_clause=nam                                    # make name available throughout
        nod=sv.Object[nam]
        for i, (c,v) in enumerate(nod.clauses):                # search clauses
            k=func(sv, c)                                                # reprocess condition
            w=func(sv, v)                                               # reprocess value
            nod.clauses[i]=(k,w)                                      # store result

#============================= tree_build
def tree_build(sv, piece):
    """
    develop the program tree by parsing conditions and clauses
    conditions and clauses are initially of the form (expression, None, None)
    parse expression for operators and build a tree of triplets, recursively
    triplets generally have form (op, b1, b2) with op: string, b1, b2: triplets
    lists have special form  (Comma, b1: list of triplets, b2: None)
    subscripts have form  (Special, root: triplet, args: triplet)
    leaves have form (name, None, None) with name from sv.Object_list
    parsing occurs according to brackets and priorities defined in Priority_groups
    operators with same priority are parsed in reversed order of appearance
    corresponding to non-reversed order of execution (deep ops come first)
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string expression with names and operators.
    Returns
    --------
        a triplet
    """
    if piece==None: return None    
    # process various string expressions (or triplets without args for conditions and values)
    piece=piece[0].strip(Space) if type(piece)==tuple else piece.strip(Space)  # convert to string                                                 
    alphabetic=Alphakwords+sv.Object_list
    
    # empty expression
    if not piece: return None

    # a string between quotes
    if piece[0]==Quote and piece[-1]==Quote: return (piece, None, None)  # return string as a leaf
    
    # a protected string: restore without further parsing   
    key=piece.strip(Special)                                         
    if key in sv.Strings: return (Quote+sv.Strings[key]+Quote, None, None) # return string as a leaf

    # a bracketed expression: parse from outer ones on, RECURSIVE
    if key in sv.Blocks: return (Obr, tree_build(sv, sv.Blocks[key]), None)

    piece=save_bracketed(sv, piece)                                              # protect outer bracketed expressions from parsing
    piece=Space+piece+Space                                                     # add Spaces to help detect alphabetic keys    
    
    # PARSE by operator priority and descending order of position           
    for op_group in Priority_groups+[sv.Object_list]:                      # ops by priority groups
        op_list=find_op(sv, piece, op_group, alphabetic)                  # detect operators of this group

        for o, op in op_list:                                                             # found ops from this group in reverse order of occurrence

        # process comma operator            
            if o==Comma and o in piece: return make_list(sv, piece)  # list will be linear (not a tree). Build RECURSIVE           

        # process unary functions and defined objects (all unary operators are alphabetic)
            if o in Unary or o in sv.Object:                                         # unary operators  (non space-delimited)
                if piece.startswith(op):                                                 # operator must be at the start (space-delimited)
                    res=make_unary(sv, piece, o, op)
                    if res and (not res[1] or o in [Begin, End]):
                        return special_unary(sv, res)                                # process special case 
                    return res
                
        # process binary operators (always lower priority than unary). Build RECURSIVE
            elif op in piece:
                res=make_binary(sv, piece, o, op)                               # binary operators (space-delimited)
                if res and (not res[1] or o==Isnot):
                    return special_binary(sv, res)                                  # process special case 
                return res

    # process other (args and doubly) subscripted objects. Build RECURSIVE
    piece=piece.strip(Space)
    if Special+Bloc in piece: return make_subscripted(sv, piece)     # the object is subscripted / has args

    # when all operators have been processed, only leaves remain
    return make_leaf(sv, piece)

#===================================================== save_bracketed
def save_bracketed(sv, lig): 
    """
    Replace and store bracketed expressions in sv.Blocks dictionary
    Processes one line. Removes only external blocks
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        lig: a string, part of a line of script 
    Returns
    --------
        lig: a string where bracketed blocks are replaced by a code 
    """
    here,block,last=findblock(lig)                                       # find external bracketed block
    while here>-1:                                                             # brackets found
        before=lig[:here].strip(Space)
        after=lig[last:].strip(Space)
        code=Bloc+str(len(sv.Blocks))                                   # make new storage key, e.g.  §Block2§
        sv.Blocks[code]=no_brackets(lig[here+1:last-1])         # don't care if block already exists
        lig=before+Space+Special+code+Special+Space+after  # replace with key
        here,block,last=findblock(lig)                                    # continue analysis
    return lig

#===================================================== find_op
def find_op(sv, piece, op_group, alphabetic):
    """
    locate operators in a string, in decreasing order of position
    allowing for different operators
    positions are only used by whole_operators
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string, part of a line of script
        op_group: a list of operators of same priority
        alphabetic: the list of operators that need to be separated by spaces
    Returns
    --------
        op_list: a list of tuples (operator, operator enclosed in spaces if needed)
    """
    op_positions=[]
    for o in op_group:
        op=Space+o+Space if o in alphabetic else o                  # separate alphabetic with spaces
        here=-1
        while op in piece[here+1:]:                               # while (here:=piece.find(op, here+1))>-1:  Python 3.8
            here=piece.find(op, here+1)
            op_positions.append((here, o, op))
    if len(op_positions)>1: op_positions.sort(key=lambda x: -x[0])  # sort list in descending order of position
    
    op_list=whole_operators(piece, op_positions)                     # do not split   <=    >=   or   !=  
    return op_list

#===================================================== whole_operators
def whole_operators(piece, op_positions):
    """
    prevent splitting of operators, e.g. "<=" into "=" and "<"
    called by find_op
    Parameters
    ------------
        piece: a string, part of a line of script
        op_positions: a list of tuples (positions, operator, operator enclosed in spaces if needed)
    Returns
    --------
        op_list: a list of tuples (operator, operator enclosed in spaces if needed) without position
    """
    op_list=[]
    if op_positions:                                                                   # remove overlapping elements (e.g. "<=", "!=" vs. "=", "<")
        last=len(piece)                                                                # initialization
        lastop=""                                                                       # previous op
        for here, o, op in op_positions:                                       # scan list
            if last-here>1:                                                            # no overlap: store and continue
                op_list.append((o,op)) 
                lastop, last = o, here
            elif o.endswith(lastop):                                               # consecutive overlapping ops (2 chars max)                                             
                if op_list: op_list.pop()                                            # remove shorter op
                op_list.append((o,op))                                            # keep operator, without and with space 
                lastop, last = o, here                                              # store larger op as previous
    return op_list
                        
#===================================================== make_list
def make_list(sv, piece):                  
    """
    build a triplet from a list. List is linear (not a tree) but made of triplets
    called by tree_build, calls tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string containing part of a script
    Returns
    --------
        res: a triplet (Comma, [list], None)
    """
    li=[tree_build(sv,x) for x in piece.split(Comma)]                    # process each element RECURSIVE
    res=(Comma, li, None)                                                        # triplet for a list: (",", [list of elements], None)
    return res

#===================================================== make_unary
def make_unary(sv, piece, o, op):
    """
    build a triplet for a unary operator
    called by tree_build, calls tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string containing part of a script
        o: an operator
        op: the same operator enclosed in spaces if alphabetic
    Returns
    --------
        res: a triplet (root, triplet, None)
    """
    there=len(op)                                                                     # start position of last part
    # if the object is subscripted / has args
    if piece[there:].startswith(Special+Bloc):                 
        here=piece[there+1:].find(Special)                                   # find ending delimiter
        key=piece[there+1:there+here+1]                                   # extract key for the block
        if piece[there+here+2:].strip(Space):                                # something after the block (some other subscript)
            first=(o, tree_build(sv, sv.Blocks[key]), None)               # Build block RECURSIVE 
            last=tree_build(sv, piece[there+here+2:])                     # build other subscript RECURSIVE
            res=(Special, first, last)                                                # code for a subscripted object
        else:
            res=(o, tree_build(sv, sv.Blocks[key]), None)                 # Build block RECURSIVE
        return res
    # the object is not subscripted but may have parts separated by space
    if Space in piece.strip(Space): return (o, tree_build(sv, piece[there:]), None)  # Build RECURSIVE
    return make_leaf(sv, piece.strip(Space))

#===================================================== special_unary
def special_unary(sv, tree):                                
    """
    correct a triplet for a unary operator without operand
    ignore simple objects
    solve a common error: begin(any( )), end(any( )), begin(all( )), end(all( ))
    by switching order of operators: any(begin()), any(end()), etc.
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet (root, None, None)
    Returns
    --------
        a triplet (root, triplet, None)
    """
    o=tree[0]
    if o==Old:                                                                       # special case: 'old' without argument
        return (Old, tree_build(sv, sv.Current_clause), None)      # recover object name
    
    elif o == All:                                                                      # without args for show
        return tree
    
    elif o in [Begin, End]:                                                          # begin(any( )), end(any( )), begin(all( )), end(all( ))
        A=tree[1]
        if A and A[0] in [Any, All]:                                               # switch operators
            sw= (A[0], (o, A[1], None), None)
            warn("\n"+Warn_switch_any_all+ \
            " '"+tree_join(tree)+"' --> '"+tree_join(sw)+"'") # here tree_join recreates a name for display only
            # *** Warning: compiler replaced ... ***  
            return sw
        
    elif o in Unary and not o in sv.Object:                                # redefined internal function without args is ok
        print(Err_missing_args)                                                   # *** Error: missing argument ***
        print(o, "???", sv.Current_clause)
        raise ReferenceError        
    return tree

#===================================================== make_binary
def make_binary(sv, piece, o, op):                                
    """
    build a triplet for a binary operator
    starts at last occurrence of operator
    solves unary uses of operators, e.g. Minus, Pick, Sort
    called by tree_build, calls tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string containing part of a script
        o: an operator
        op: the same operator enclosed in spaces if alphabetic
    Returns
    --------
        a triplet (root, triplet1, triplet2)
    """
    here=piece.rfind(op)                                                          # look for last occurrence
    there=here+len(op)
    t1=piece[:here].strip(Space)                                                # first term (sometimes omitted)
    t2=piece[there:].strip(Space)                                               # second term must be present
    if not t2:     
        print("\n", Err_op_syntax, o)                                           # *** Syntax error in operator ***
        print("      ", piece)
        raise ReferenceError
    first=tree_build(sv, t1)                                                      # process each term RECURSIVE
    second=tree_build(sv, t2)
    return (o, first, second)                                   

#===================================================== special_binary
def special_binary(sv, tree):                                
    """
    analyze tree to solve unary cases of binary operators
    minus plain numbers and durations x are replaced by -x
    minus other expressions B are replaced by -1 * B (valid for both numbers and durations)
    unary pick or sort are applied to the two identical arguments
    a trick to circumvent problems of empty lists with operator isnot
    replace 'X is not empty' with 'empty within X'  (it is true if X is not empty)
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet representing a unary use of a binary operator (op, None, triplet2)
    Returns
    --------
        res: a triplet with the binary operator solved (op, triplet1, triplet2)
    """
    o, A, B=tree
    # solve unary minus
    if o==Minus:
        x,y,z=B
        if isnumber(x) or isduration(x): return ('-'+x, None, None)  # just insert '-' prefix to numbers and durations
        return (Mult, ('-1', None, None), B)                 # replace with -1 * B
    
    # solve unary pick and sort
    if o in [Pick, Sort]:
        return (o, B, B)

    if o==Isnot:
        if B==(Empty, None, None): return (Within, B, A)
        return tree
    
    print(Err_missing_args)                             # *** Error: missing argument ***
    print("???", o, tree_join(B))
    raise ReferenceError
    
#===================================================== make_subscripted
def make_subscripted(sv, piece):
    """
    build a triplet for a subscript
    allow implicit multiply, e.g. '3.14(r*r)'
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string containing part of a script
        o: an operator
        op: the same operator enclosed in spaces if alphabetic
    Returns
    --------
        res: a triplet (operator, triplet1, triplet2)
    """
    here=piece.find(Special+Bloc)                                            # find beginning delimiter (always present)
    prefix=piece[:here].strip(Space)                                           # extract prefix (if any) for implicit multiply
    tail=piece[here:]
    there=tail[1:].find(Special)                                                  # find ending delimiter
    key=tail[1:there+1]                                                            # extract key for the block
    
    if tail[there+2:]:                                                                 # something after the block (some other subscript)
        first=tree_build(sv, sv.Blocks[key])                                  # Build RECURSIVE
        last=tree_build(sv, tail[there+2:])                                    # Build RECURSIVE
        return(Special, first, last)                                                # op for a subscripted object
        
    if isnumber(prefix):                                                            # implicit multiply
        last=tree_build(sv, sv.Blocks[key])                                  # Build RECURSIVE
        return(Mult, (prefix, None, None), (Obr, last, None))
        
    last=tree_build(sv, sv.Blocks[key])                                      #  Build RECURSIVE
    return(Special, (prefix, None, None), last)                           # op for a subscripted object

#===================================================== make_leaf
def make_leaf(sv, piece):
    """
    build a simple triplet, allowing for implicit multiplication
    called by tree_build
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        piece: a string containing part of a script
        o: an operator
        op: the same operator enclosed in spaces if alphabetic
    Returns
    --------
        res: a triplet, (name, None, None) or ('*', (number, None, None), triplet2)
    """
    here=piece.find(Space)                                         
    if isduration(piece):
        piece=piece.replace(Space,'')                                   # eliminate spaces from durations
    elif here>0:                                                                # look for implicit multiply with space
        if isnumber(piece[:here]):                                        # a number times a name
            return (Mult, (piece[:here], None, None), (piece[here+1:], None, None))
        print(Err_space_in_name, piece)                              # error space in name
        raise ReferenceError
    else:                                                                          # look for implicit multiply without space
        here=0
        while isnumber(piece[:here+1]) and here<len(piece)-1: 
            here+=1                                                           # get longest numerical value
        if here>0 and not isnumber(piece):                        # a number times a name
            return (Mult, (piece[:here], None, None), (piece[here:], None, None))   
    return (piece, None, None)                                        # triplet for a leaf

#===================================================== adjust_store_list
def adjust_store_list(sv):
    """
    verify that all values for a store operator are lists and transform them if necessary
    because nature of args must be consistent
    e.g. (',', [('"Hello world"', None, None), None], None)
    called by build_script
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for nam in sv.Object_list:                                      # explore objects
        if applied(nam, Store):                                      # look for Store objects
            nod=sv.Object[nam]
            for i, (c,v) in enumerate(nod.clauses):            # look for values in clauses
                if v[0]!=Comma:                                       # not a list
                    v=(Comma, [v], None)                          # make it a list
                    nod.clauses[i]=(c,v)                               # save clause
    
#=====================================================        
#                        RESOLUTION OF USER-DEFINED FUNCTIONS
#===================================================== user_functions
def user_functions(sv):
    """
    solve user_function calls. Each call is replaced with a list element
    elements are declared with similar clauses
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    make_user_functions(sv)                        # make all user function args local
    solve_user_calls(sv)                                # identify and unify user functions
    clean_user_functs(sv)                             # replace user functions with lists

#===================================================== make_user_functions
def make_user_functions(sv):
    """
    identify arguments of user-defined functions and make them virtual and local.
    replace them throughout clauses
    called by user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    # browse user-defined functions 
    user_functions_info=[]
    for nam in list(sv.Object_list):      # list of objects may be modified in the loop  - maintain order of definitions
        
        # finish processing function when a non primed object is encountered
        if not is_primed(nam): user_functions_info =make_local_links(sv, user_functions_info)
        
        # make arguments local in function definition
        if sv.Object[nam].isuserfunc:
            argu_list = get_arg_list(sv, nam)
            user_functions_info, local_arg_list \
                               = make_args_local(sv, nam, argu_list)

        # process accessory variables (primed) of current function          
        elif is_primed(nam): user_functions_info, argu_list, local_arg_list \
                               = add_accessory_variable(sv, nam, argu_list, local_arg_list, user_functions_info)

    # finish processing function when all objects have been browsed        
    make_local_links(sv, user_functions_info)
    
#===================================================== get_arg_list
def get_arg_list(sv, nam):
    """
    retrieve list of user-defined function arguments from function root clauses
    called by make_user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, the name of a user-defined function
    Returns
    --------
        argu_list: a list of argument names
    """
    cond, value=sv.Object[nam].clauses[0]                                 # in first clause: (condition, value), value is a node with list of args
    if type(value)!=tuple or value[0]!=Comma or not value[1]:    # expecting (',', [(argname1, None, None), (argname2, None, None)...], None)
        print("\n", Anom_no_args)                                               # *** Anomaly: cannot find function arguments ***                             
        print(nam)
        raise ReferenceError
    argu_list = [x[0] for x in value[1] if x is not None]                 # extract just the names
    return argu_list

#===================================================== make_args_local
def make_args_local(sv, nam, argu_list):    
    """
    change name of arguments by prefixing them with function root name + Dot
    build function names with nonlocal and local arguments
    called by make_user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, the name of a user-defined function
        argu_list: a list of argument names
    Returns
    --------
        user_functions_info: a list of [(nam, full_function_name, local_function_name, argu_list, local_arg_list), ...]
        local_arg_list: a list of renamed arguments
    """
    prefix=nam+Dot
    local_arg_list=[prefix+arg for arg in argu_list]
    full_function_name=nam+Obr+",".join(argu_list)+Cbr
    local_function_name=nam+Obr+",".join(local_arg_list)+Cbr
    
    for nm in local_arg_list:                                         # names of new nodes
        add_object(sv, nm)                                            # create node
        sv.Object[nm].isvirtual=True                              # make arg virtual

    user_functions_info=[(nam, full_function_name, local_function_name, argu_list, local_arg_list)]
    return user_functions_info, local_arg_list

#===================================================== add_accessory_variable
def add_accessory_variable(sv, accessory_name, argu_list, local_arg_list, user_functions_info):
    """
    add an accessory (primed)  variable to a user-defined function
    called by make_user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        accessory_name: a string, the name of a user-defined function
        argu_list: a list of arguments
        local_arg_list: a list of renamed arguments
        user_functions_info: list updated with accessory variable name and local name
    Returns
    --------
        user_functions_info: a list of [(accessory_name, full_function_name, local_function_name, argu_list, local_arg_list), ...]
    """
    if not user_functions_info:
        print("\n", Err_accessory, accessory_name)                     # "\n*** Error: accessory variable is not part of a function definition ***"
        raise ReferenceError
    if accessory_name in argu_list:                                        
        print("\n", Err_redef_name, accessory_name)                  # *** Error: Node is already defined ***
        raise ReferenceError
    func_name=user_functions_info[0][0]
    local_name=func_name+Dot+accessory_name                  # local name for accessory variable
    argu_list+=[accessory_name]
    local_arg_list+=[local_name]
    user_functions_info+=[(func_name, accessory_name, local_name, argu_list, local_arg_list)]  # add accessory variable
    return user_functions_info, argu_list, local_arg_list

#===================================================== make_local_links
def make_local_links(sv, user_functions_info):                        
    """
    create local objects and link local references for user function calls  
    called by make_user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        user_functions_info: a list of [(nam, full_function_name, local_function_name, argu_list, local_arg_list), ...]
    Returns
    --------
        user_functions_info: the list is empty after processing
    """
    if not user_functions_info: return []

    # save local argument list    
    li=[(x, None, None) for x in user_functions_info[-1][-1]]                    # rewrite local_arg_list as triplets
    nam=user_functions_info[0][0]
    sv.Object[nam].clauses=[((Start, None, None), (Comma, li, None))]  # store local_arg_list (needed for get_virtual_arg_list)

    # create local function objects with arguments 
    for funcname, full_function_name, local_function_name, argu_list, local_arg_list in user_functions_info:
        add_object(sv, local_function_name)                                           # create object for local function name 
        nd.copy_node(sv,full_function_name, sv.Object[local_function_name])     # copy object attributes
        
        # recompute clauses to make them local
        sv.Object[local_function_name].clauses=[]                                   # clear all clauses
        changes=dict(zip(argu_list, local_arg_list))
        for i, (c,v) in enumerate(sv.Object[full_function_name].clauses):    # old clauses
            k=substitute(c, argu_list, changes)                                           # modify all names in condition
            w=substitute(v, argu_list, changes)                                          # modify all names in value
            sv.Object[local_function_name].clauses+=[(k,w)]                      # add this clause
        sv.Object[local_function_name].isuserdef=True                           # mark this object for later destruction
        
    # remove nonlocal function object
    for info in user_functions_info:
        eliminate(sv, info[1])                                                                  # remove full_function_name from object dict and list
    user_functions_info=[]                                                                   # clear user_function_info
    return user_functions_info                           

#===================================================== substitute
def substitute(tree, old_list, changes):
    """
    recursively replace text or triplets in a tree without changing tree structure or order
    called by make_local_links and solve_user_calls
    Parameters
    ------------
        tree: a triplet
        old_list: a list of strings or triplets to be changed
        change: a dict made from old_list and replacements
    Returns
    --------
        res: a triplet where all terms have been changed
    """
    if not tree: return None
    o,A,B=tree    
    if o==Comma:                                                        # special case: lists                               
        li=[substitute(x, old_list, changes) for x in A]
        return (Comma, li, None)
    
    if tree in old_list:                                                     # replace tree (maybe not hashable)
        return changes[tree]
    
    if (o, None, None)  in changes:                               # replace a branch
        res=changes[(o, None, None)]
        if res[1] or res[2]:                                                # new tree replaces old tree
            return res
        return (res[0], tree[1], tree[2])                              # new op replaces old op
 
    if o in changes: o=changes[o]  
    return (o, substitute(A, old_list, changes), substitute(B, old_list, changes))  #  RECURSIVE

#===================================================== eliminate
def eliminate(sv, nam):                        
    """
    completely remove objects   
    called by make_local_links
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, object name
    Returns
    --------
        all information is directly stored in sv
    """
    del sv.Object[nam]                                                                  # from sv.Object dictionary
    sv.Object_list.remove(nam)
        
#===================================================== solve_user_calls
def solve_user_calls(sv, tree=Special, user_set=set([])):
    """
    identify and solve user function calls. These calls do not have a real definition
    but may appear in definitions of defined objects
    use get_subtree_list to identify these objects
    process whole program if tree=Special
    recursively replaces user function calls with their definition
    replaces virtual arguments with real ones
    real_arg_list is a list of arguments as triplets:
    - a single value or list name
    - an expression
    - a list of elements
    called by make_user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet representing an expression or Special for the whole program
        user_set: a set of user-defined function names for faster lookup
    Returns
    --------
        all information is directly stored in sv
    """
    # traverse program
    if tree==Special: 
        user_set=set([x for x in sv.Object_list if sv.Object[x].isuserfunc])           # create list of user-defined function names
        for nam in list(sv.Object_list):                                                             # explore only currently defined objects (more to come)
            for pair in sv.Object[nam].clauses:                                                  # solve user function calls in clauses
                make_real_clauses(sv, pair, user_set)
        return            

    # analyze a tree
    if not tree: return
    user_call=tree_join(tree)                                                                         # calculate a name for the tree
    if not(user_call in sv.Object and (sv.Object[user_call].issolved or sv.Object[user_call].isuserdef)):        
        if user_call in sv.Object:                                                                    # get or create object
            nod=sv.Object[user_call]
        else:
            nod=add_object(sv, user_call)                                                       # create object
            nod.isnew=True                                                                           # allow expression processing
             
        # get virtual args and name of user function
        if tree[0] in user_set and tree[1]:                                                        
            fun=tree[0]
            local_arg_list, local_function_name, accessories=get_virtual_arg_list(sv, fun)  
                
            # get and verify real arguments
            real_arg_list = get_real_arg_list(tree, local_arg_list, accessories)
            
            # create accessory variables
            real_arg_list, real_arg_names = make_accessory(sv, fun, user_call, accessories, real_arg_list)
               
            # substitute real clauses
            make_user_clauses(sv, user_set, local_function_name, local_arg_list, accessories, real_arg_list, real_arg_names)

    if tree[1] or tree[2]:                                                                            # process tree branches
        if tree[0]==Comma:
            for t in tree[1]:
                solve_user_calls(sv, t, user_set)                                               # recurse to analyze each list element
        else:
            solve_user_calls(sv, tree[1], user_set)                                          # recurse to analyze each branch  
            solve_user_calls(sv, tree[2], user_set)

#===================================================== make_real_clauses
def make_real_clauses(sv, pair, user_set):
    """
    substitute real arguments in conditions and values of real function call
    used in solve_user_calls and make_user_clauses
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        pair: a tuple of condition and value
        user_set: a set of user-defined function root names as strings
    Returns
    --------
        all information is directly stored in sv
    """
    for x in pair:
        for cause in get_subtree_list(sv, x):                                    # n.b. there may be duplicates 
            solve_user_calls(sv, cause, user_set)                               # analyze each object RECURSIVE

#===================================================== get_subtree_list
def get_subtree_list(sv, tree):            
    """
    find list of subtrees found in a tree expression (recursive)
    does not explore conditions and values
    used in solve_user_calls
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet representing an expression
    Returns
    --------
        res: a list of subtrees
    """
    if not tree: return []
    O, A, B = tree
    if not A and not B:                                                                          # any leaf 
        res=[tree]                                                                                   # just extract tree       
    elif O in sv.Object and sv.Object[O].isfunction:                                # form: root(args)
        res=[tree]                                                                                   # just extract tree        
    elif O==Comma:                                                                            # a list
        res=[]                                                                                         # list comprehension does not work here 
        for t in A:                                                                                   # process each element
            res+=get_subtree_list(sv, t)                                                     # RECURSIVE
    else:                                                                                               # some expression with internal ops
        res=get_subtree_list(sv, A)+get_subtree_list(sv, B)                        # RECURSIVE

    li=[]                                                                                               # remove duplicates (the hard way) because
    li=[r for r in res if not r in li]                                                           # there may be non hashable terms
    return li                                                                                             

#===================================================== get_subtree_names
def get_subtree_names(sv, tree):            
    """
    convert trees from get_subtree_list to object names
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet representing an expression
    Returns
    --------
        res: a list of subtree names
    """
    return [tree_join(x) for x in get_subtree_list(sv, tree)]

#===================================================== get_virtual_arg_list
def get_virtual_arg_list(sv, nam):
    """
    get virtual arguments and defined name for a function from object
    used in solve_user_calls
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, the root name of a user-defined function
    Returns
    --------
        local_arg_list: a list of arguments and accessory variable names
        local_function_name: 
        accessories: a list of accessory variable names
    """
    # get user function instances
    c, vlist=sv.Object[nam].clauses[0]                                                    # first clause: condition, value: a node with list of args
    if vlist:
        op,A,B=vlist                                                # expected (',', [(argname1, None, None), (argname2, None, None)...], None)
    local_arg_list=[]
    accessories=[]
    local_function_name=nam+Obr                                                      # re-build local definition 
    for t in A:
        if t is not None:                                               
            local_arg=t[0]                                                                          # argument name
            local_arg_list+=[(local_arg, None, None)]
            if not sv.Object[local_arg].isvirtual:
                accessories+=[local_arg]
            else:
                local_function_name+=local_arg if local_function_name==nam+Obr else Comma+local_arg
    local_function_name+=Cbr
    return local_arg_list, local_function_name, accessories   
  
#===================================================== get_real_arg_list
def get_real_arg_list(tree, local_arg_list, accessories):
    """
    get and check real arguments for a user-function call
    used in solve_user_calls
    Parameters
    ------------
        tree: a triplet representing the call
        local_arg_list: a list of arguments and accessory variable names
        accessories: a list of accessory variable names
    Returns
    --------
        real_arg_list: a list of arguments as triplets
    """
    # get and split arguments
    real_arg_list=[tree[1]]                                                                 # value or expression
    arg_list = local_arg_list[:-len(accessories)] if accessories else local_arg_list
    if tree[1][0]==Comma and len(arg_list)>1:                                  # if multiple arguments
        real_arg_list=tree[1][1]                                                           # split the real list
    real_arg_list=list(real_arg_list)                                                    # make sure it is a copy and not the original within tree
    
    # verify number of arguments
    if len(arg_list)!=len(real_arg_list) and len(funcargs)!=1:           
        print("\n", Err_nb_args)                                                       # *** Error: Wrong number of arguments                          
        print(tree_join(tree), "-->", fun+str(arg_list))
        print(len(real_arg_list), "<>", len(arg_list) )
        raise ReferenceError
    
    return real_arg_list
        
#===================================================== make_accessory
def make_accessory(sv, fun, expr, accessories, real_arg_list):
    """
    create real names for accessory variables after prefixing them with real function call
    e.g. function.arg1.arg2.accessory
    used in solve_user_calls
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        fun: a string, user_function name
        expr: a string, user function call with arguments
        accessories: a list of accessory variable names
        real_arg_list: a list of arguments as triplets
    Returns
    --------
        real_arg_list: a list of arguments and accessories as triplets
        real_arg_names: a list of argument and accessory names
    """
    real_arg_names=[expr]                                                                    # insert dots in user function call
    temp=expr
    temp=temp.replace(Obr, Dot)
    temp=temp.replace(Cbr, Dot)
    temp=temp.replace(Comma, "")
    
    for acc in accessories:
        real_acc_name=temp+acc[len(fun)+1:]                                        # extract accessory name (primed)
        real_arg_list+=[(real_acc_name, None, None)]                              # add to list of triplets    
        real_arg_names+=[real_acc_name]                                              # add to list of names
        add_object(sv, real_acc_name)                                                    # create object for real accessory  
        nd.copy_node(sv, acc, sv.Object[real_acc_name])                          # copy object attributes
        
    return real_arg_list, real_arg_names                                                 # return lists
               
#===================================================== make_user_clauses
def make_user_clauses(sv, user_set, local_function_name, local_arg_list, accessories, real_arg_list, real_arg_names):
    """
    create clauses for real function call
    used in solve_user_calls
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        real_arg_names: a list of real argument and accessory names
        local_function_name: a string
        accessories: a list of accessory variable names
        local_arg_list: a list of arguments as triplets from function definition
        real_arg_list: a list of real arguments as triplets
        user_set: a set of user-defined function root names as strings
    Returns
    --------
        all information is directly stored in sv
    """
    for real_arg, local_arg in zip(real_arg_names, [local_function_name]+accessories):
        nod=sv.Object[real_arg]
        clauselist=sv.Object[local_arg].clauses                                    # get virtual definition clauses
        changes=dict(zip(local_arg_list, real_arg_list))
        nod.clauses=[ (substitute(cond, local_arg_list, changes), substitute(vlu, local_arg_list, changes)) \
                        for cond, vlu in clauselist ]
        nod.isnew=False                                                                   # forbid expression processing
        nod.issolved=True                                                                # avoid reprocessing name
        nod.isdefined=True                                                              # apparently needed later (runtime?): could try issolved instead
        nod.isuserdef=False                                                              # avoids virtual tagging and destruction

        # recursively explore name and clauses for compound function
        for pair in nod.clauses:                                                          # look for more
            make_real_clauses(sv, pair, user_set)

#===================================================== clean_user_functs
def clean_user_functs(sv):                        
    """
    completely remove virtual objects   
    called by user_functions
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    markvirtual(sv)                                                                       # identify virtual objects 
    finalize_user_functions(sv)                                                      # transform user functions into dict
    for nam in list(sv.Object_list):                                                  # remove virtual objects
        nod=sv.Object[nam]
        if nod.isvirtual: eliminate(sv, nam)

#===================================================== markvirtual
def markvirtual(sv):
    """
    tag objects as virtual for removal. Iterate until no more change
    procedure is iterative instead of recursive because there may be cycles
    .isuserfunc: identifies user function roots
    .isvirtual: identifies local user function arguments to be removed                            
    .isuserdef: identifies user function definitions to be removed
    called by clean_user_functs
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    chg=True
    while chg:                                                                      # loop until no more change
        chg=False
        for nam in sv.Object_list:
            nod=sv.Object[nam]
            if not nod.isvirtual and not nod.isuserfunc:            # neither virtual nor root
                virtual = nod.isuserdef                                      # definition tagged in make_user_links

                if not virtual:
                    for pair in nod.clauses:                                  # tag objects with virtual causes
                        for x in pair:                                              # conditions and values
                            for cau in get_subtree_names(sv, x):       # all causes
                                if cau in sv.Object and (sv.Object[cau].isvirtual or sv.Object[cau].isuserdef):
                                     virtual=True
                    
                    here, block, there=findblock(nam)                # detect functions of virtual objects
                    if block in sv.Object and (sv.Object[block].isvirtual or sv.Object[block].isuserdef):
                        virtual=True

                if virtual:
                    chg=True
                    nod.isvirtual=True                                      # tag virtual args
            
#===================================================== finalize_user_functions
def finalize_user_functions(sv):
    """
    converts user functions into lists
    starts with building subscripts from instances
    called by clean_user_functs
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    real_object_names=[nam for nam in sv.Object_list if not sv.Object[nam].isvirtual]
    for nam in real_object_names:                           # new objects will be added
        nod=sv.Object[nam]
        if nod.isuserfunc:                                           # nam is a function root
            
            li=[]
            for nm in real_object_names:                     # scan objects in order of declaration
                block=applied(nm, nam)                       # extract arguments if any
                if block:                                                 # object nm is an instance of function nam
                    add_object(sv, block)                         # create a node from subscript
                    li+=[(nm, None, None)]                     # make a list of instances

            if not li:                                                    # function not used
                warn("\n"+Warn_never_applied+"\n"+nam)   # *** Warning: function", nam, "is never applied ***                           
                nd.copy_node(sv, Faux, nod)                   # re-initialize node
                nod.isvirtual=True                                 # mark node for removal

            nod.clauses=[(Starttree, (Comma, li, None))] # put list of instances into value
    
            nod.isdict=True                                         # it is now and ordinary list
            nod.isdefined=True
            nod.isuserfunc=False
            nod.nature=Lst[:]

#=====================================================
#                          DETECTION OF DEEP CHANGES IN LISTS
#===================================================== link_list_change
def link_list_change(sv):
    """
    creates clauses for deep changes in lists
    works only for static lists that do not change elements
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for name in sv.Object_list:                                                      # use list of objects
        nod=sv.Object[name]
        if nod.isfunction:                                                               # either a "dict" or a user defined function    
            chg=Change+Obr+name+Cbr
            if find_tree(sv, (Change, (name, None, None), None)):      # look for change(list)
                add_object(sv, chg)                                                   # create change(list) object
                clau=((Plus, (chg, None, None), (str(Change_time)+"s", None, None)),(Faux, None, None))
                if not clau in sv.Object[chg].clauses:                          # clause to reset change
                    sv.Object[chg].clauses+=[clau]
                for block in nod.arguments:
                    clau=((Change, (name+Obr+block+Cbr, None, None), None),(Vrai, None, None))  # link change
                    if not clau in sv.Object[chg].clauses:
                        sv.Object[chg].clauses+=[clau]

#===================================================== find_tree
def find_tree(sv, subtree, tree=Special):
    """
    looks for subtree in program clauses and returns true if found
    recursive
    called by link_list_change
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        subtree: a triplet representing an expression
    Returns
    --------
        a Boolean: True if subtree was found
    """
    if tree is None: return False
     # scan all program
    if tree==Special:
        for nam in sv.Object_list:                                                 
            nod=sv.Object[nam]
            for c,v in nod.clauses:                                                  # scan clauses
                if find_tree(sv, subtree, c): return True                      # recurse on condition
                if find_tree(sv, subtree, v): return True                      # recurse on condition
        return False

    # explore a branch    
    if tree==subtree: return True
    O,A,B=tree                                                                          
    if O==Comma:                                                                    # special case: list
        for x in A:
            if find_tree(sv, subtree, x): return True                          # recurse on each element
    else:
        if find_tree(sv, subtree, A): return True                             # recurse on first term
        if find_tree(sv, subtree, B): return True                             # recurse on second term
    return False

#=====================================================
#                             DECOMPOSITION OF EXPRESSIONS
#===================================================== decompose_expressions
def decompose_expressions(sv):
    """
    explore all program to create a cache for expressions
    each expression gets reduced to one single operation
    iterate until no more change
    called by compile
    Parameters
    -------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    ---------
        all information is directly stored in sv
    """    
    done=False                                                                          # iterate until no more change        
    while not done:
        done=True                                                                       # set to False whenever there is a change                                                             
        # build expressions from clauses
        for nam in list(sv.Object_list):                                            # list is modified in loop: use a copy
            nod=sv.Object[nam]
            li=[]
            for c,v in nod.clauses:                                                   # explore clauses                    
                k,w=c,v                                                                    # copy of condition and value (may change)
                
            # cache condition            
                if k:
                    if not (k[0] in [Always, Start]+Glitch_list):               # add 'begin' except for [Begin, End, Change, Always, Start]
                        k=(Begin, k, None)                                           
                    k=(k[0], create_expression(sv, k[1]), None)             # skip one level
                    if k!=c: done=False                                              # a change has occurred
                    
            #cache value      
                if w and tree_join(w)!=nam:                                       # do not create circular ref  
                    if w[0] in Glitch_list:                                             # do not cache [Begin, End, Change]   
                        w=(w[0], create_expression(sv, w[1]), None)                        
                    elif w[0]==Comma:
                        w=create_expression(sv, w)                              # process list                                                                                    
                    elif ( w[1] and ( w[1][1] or w[1][2]) ) or \
                           ( w[2] and ( w[2][1] or w[2][2]) ):                    # do not cache a single operation                                                                                        
                                 w=(w[0], create_expression(sv, w[1]), create_expression(sv, w[2]))         
                    if w!=v: done=False                                             # a change has occurred
            # store result
                li+=[(k,w)]                                                               # store one clause
                        
            nod.clauses=li                                                             # store list of clauses
            
#===================================================== create_expression
def create_expression(sv, tree):
    """
    create a cache for an expression by reducing it to a single operation
    recursive call to create and link new expression names
    update object dict and object clauses
    called by decompose_expressions
    Parameters
    -------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a triplet or None
    Returns
    ---------
        a triplet (name, None, None) or None
        updates clauses, sv.Object and sv.Object_list 
    """    
    if not tree: return None                                                         # nothing to do
    o,A,B=tree

    if o==Obr:                                                                           # bracketed expression: remove brackets 
        return create_expression(sv, A)                                          # RECURSIVE

    nam=tree_join(tree)
    verify_expression(tree, nam)                                                 # check name validity 

    if nam in sv.Object and not sv.Object[nam].isnew:                # don't replace existing name unless new user call
        nod=sv.Object[nam]                                                        # use old name 
        return (nam, None, None)                                                # replace expression with name 
        
    nod=add_object(sv, nam)                                                    # create object (unless new user call)
    nod.isexpression=True
    nod.isnew=False                                                                 # process only once
        
    # link expression (only for new nodes)
    if o==Comma:                                                                   # special case: list: clause for each changing element
        li=[]
        for t in A:
            exprs=create_expression(sv, t)                                     # RECURSIVE
            if exprs: li=li+[exprs]
        vlu=(Comma, li, None)                                                   # list of elements 
        nod.clauses=[(Starttree,vlu)]                                           # start clause for whole list  ((Start, None, None), (Comma, li, None))                      
        for t in li:                                                                       # each term is a triplet
            if t and not is_fixed(t[0]):
                add_change_clause(sv, nod, t, vlu)

        return (nam, None, None)                                               # name for the list

    # some sort of expression except a list
    exprsA=create_expression(sv, A)
    exprsB=create_expression(sv, B)
    vlu=(o, exprsA, exprsB)                                                        # reduce to a simple operation between two expressions 

    # make start clauses, and change clause for non-fixed objects (do not repeat 'change')
    nod.clauses=[(Starttree, vlu)]                                               # ((Start, None, None), vlu)  
    if o in sv.Object and not is_fixed(o):
        add_change_clause(sv, nod, (o, None, None), vlu)
    if A and not is_fixed(A[0]):
        add_change_clause(sv, nod, exprsA, vlu)
    if B and B!=A and not is_fixed(B[0]):
        add_change_clause(sv, nod, exprsB, vlu)
        
    if o==Since:                                                                       # special case: conditions for "since"                                                                               
        pl=create_expression(sv, (Plus, exprsB, exprsA))                # RECURSIVE                               
        nod.clauses[-1]=((Change, pl, None), vlu)                        # when change(event+delay): (Since, exprsA, exprsB)        
        add_change_clause(sv, nod, exprsB, vlu)                          # when change(event)...
        # n.b. changing delay during 'since' should have no effect
        
    return (nam, None, None)                                                      # replace expression with name 
        
#===================================================== verify_expression
def verify_expression(tree, nam):
    """
    test the validityof a name to be used as an expression
    called by create_expression
    Parameters
    -------------
        tree: a triplet
        nam: a string derived from the triplet by tree_join 
    Returns
    ---------
        raises an error if not correct
    """
    o, A, B=tree
    if o in Internal_Functions and not A and not B:
            print("\n", Err_no_arg)                                                     # *** Syntax error: function without arguments ***                         
            print(o)
            print(nam)
            raise ReferenceError
        
    if Space in nam:                                                                      # expressions should not contain spaces
        bad=False
        inside=False
        for c in nam:                                                                       # check all spaces are inside quotes
            if c==Quote: inside=not inside
            if c==Space and not inside: bad=True
        if bad:
            print("\n", Err_space_in_name)                                         # *** Syntax error: incorrect expression ***                     
            print(nam, Col)
            print(tree)
            raise ReferenceError

#===================================================== is_fixed
@lru_cache
def is_fixed(nam):
    """
    test whether object may change. Fixed: [Vrai, Faux, Epsilon, Empty]
    called by create_expression
    Parameters
    -------------
        nam: a string derived from the triplet by tree_join 
    Returns
    ---------
        True if object cannot change, False otherwise
    """
    if nam is None: return True
    if nam==Controlpanel: return True
    if nam in Fixed: return True
    if isnumber(nam): return True
    if isduration(nam): return True
    if Obr in nam:                        # skip tests for function
        if applied(nam, Load): return True
        if applied(nam, Show): return True
        if applied(nam, Unused): return True
    return False
        
#===================================================== add_change_clause
def add_change_clause(sv, nod, tree, vlu):
    """
    adds a change clause for dependent object
    object nod takes value vlu for each change in cond
    called by create_expression
    Parameters
    -------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object
        tree: a triplet corresponding to an expression
        tree: a triplet (expression_name, None, None)
        vlu: a triplet
    Returns
    ---------
        all information is directly stored in sv
    """
    clau=((Change, tree, None), vlu)  
    if not clau in nod.clauses: nod.clauses+=[clau]                 # avoid duplicates
    
#===================================================== change_glitch
def change_glitch(sv):
    """
    modifies conditions involving glitch cached objects to 'change' instead of 'begin' or 'end'  
    e.g. ('begin', ('end(t)', None, None), None) to ('change', ('end(t)', None, None), None)
    so that they may be correctly involved in a delayed effect (see 'test abchange.txt')
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for nod in sv.Object.values():
        for i, (c,v) in enumerate(nod.clauses):
            if c and c[1] and is_glitch(c[1][0]):                            # only for conditions 
                c=(Change, c[1], c[2])
                nod.clauses[i]=(c,v)

#=====================================================
#                                 LINK CAUSES AND EFFECTS
#===================================================== causes_and_effects
def causes_and_effects(sv):
    """
    extract first order causes and effects
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        .causes: a list directly stored in sv
        .effects: a list directly stored in sv
    """
    find_causes(sv)                                      # identify immediate causes
    find_effects(sv)                                      # identify effects

#===================================================== findcauses
def find_causes(sv):
    """
    extract causes from program using get_subtree_names
    returns for each object a list of first order causes, excluding object itself
    called by causes_and_effects
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        a list is directly stored in sv.Object[name].causes
    """
    for nam in sv.Object_list:
        nod=sv.Object[nam]
        nod.causes=[]
        # make name a cause for count(name) and show(name) - needed for display
        counted=applied(nam, Count)                            
        if counted: nod.causes=[counted]
        showed=applied(nam, Show)
        if showed: nod.causes+=[showed]
        # ordinary causes
        found=nod.causes                                                   
        for (c,v) in nod.clauses:
            found+=get_subtree_names(sv, c)                 # objects in condition
            found+=get_subtree_names(sv, v)                 # objects in value
        nod.causes=unique(found)                               # remove duplicates, keeping order
        if nam in nod.causes: nod.causes.remove(nam) # exclude self
        
#===================================================== relations
def unique(li):
    """
    remove duplicates from a list of hashables, keeping order
    Parameters
    ------------
        li: a list
    Returns
    --------
        list without duplicates
    """
    seen = set()
    seen_add = seen.add
    return [x for x in li if not (x in seen or seen_add(x))]

#===================================================== find_effects
def find_effects(sv):
    """
    extract effects from program using .causes
    called by causes_and_effects
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        a list is directly stored in sv.Object[name].effects
    """    
    for eff in sv.Object_list:
        nod=sv.Object[eff]
        for nam in nod.causes:                                          # look for causes
            if not eff in sv.Object[nam].effects: sv.Object[nam].effects+=[eff]

#=====================================================
#                                               SANITY CHECKS
#===================================================== verifications
def verifications(sv):
    """
    sanity controls. Special chars for internal use should have been removed.
    all functions must be defined.
    similar names possibly due to typing errors yield a warning message
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        no change in sv. Error or warning messages only
    """
    verif_no_special(sv)                            # check no special character remains (fatal error) 
    verif_functions(sv)                              # check if all functions are defined (fatal error)
    verif_similar_names(sv)                       # check similar names for typing errors (warning)
    verif_stochastic(sv)                             # make sure stochastic objects are not used in expressions
    verif_unused(sv)                                 # check physical and logical configurations match       

#===================================================== verif_no_special
def verif_no_special(sv):
    """
    verify that all special characters have been processed
    an error here means there is an attempt to use an unknown function
    called by verifications
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        no change in sv. Error message only
    """
    prog=reconstruct(sv)                                             # rebuild prog text
    for lig in prog.split(Crlf):                                        # analyze lines
        if Special in lig:                                                 # this char is not allowed
            print("\n", Err_unknown_funct)                      # *** Error: unknown function ***                     
            print(lig)
            here=lig.find(Special)                                    # create explicit error message
            there=lig[here+1:].find(Special)
            block=lig[here+1:here+there+1]
            la=lig[:here-1].rfind(Space)
            lig= lig[:la]+" <"+lig[la+1:here+there+4]+">"+lig[here+there+4:]
            if block in sv.Blocks:
                lig=lig.replace(Space+Special+block+Special, Obr+sv.Blocks[block]+Cbr)
            print(lig)
            raise ReferenceError

#===================================================== verif_functions
def verif_functions(sv):
    """
    verify that subscripted objects are defined
    link change if needed
    called by verifications
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        no change in sv. Error message only
    """
    for nam in sv.Object_list:
        nod=sv.Object[nam]
        root=fromlist(sv, nam)                                      # only objects, not internal functions
        if root and not sv.Object[root].isdefined:                                                  
            print("\n", Err_unknown_funct)                      # *** Error: unknown function ***                     
            print(nam)
            raise ReferenceError
            
#===================================================== verif_similar_names
def verif_similar_names(sv):
    """
    compare object names to detect typing errors         
    detects names that differ by case, by last character or by added character
    called by verifications
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        no change in sv. Warning message only
    """
    ok=True
    names=[os.path.normcase(n) for n in sv.Object_list]         # list names without case
    names.sort()                                                                    # facilitate compare one to the next
    for i, n in enumerate(names[:-1]):                                     # scan whole list
        a,b=n[:-1], names[i+1][:-1]                                           # names minus last char
        c=names[i+1][-1]                                                        # last char in full name
        d=n[-1]                                                                      # last char in full name
        if len(a)>1 and (c <"0" or c>"9") and (d <"0" or d>"9") and a[-1]!=Underscore and b in [a, n]:
            if ok:
                print("")
                ok=False
            warn("\n"+Warn_typing_risk+"\n'"+n+"' / '"+names[i+1]+"'")    # *** Warning: risk of typing error in '"+n+"' or '"+names[i+1]+"' ***                         
            
    if not ok: print("")
            
#===================================================== verif_stochastic
def verif_stochastic(sv, tree=Special):
    """
    make sure stochastic objects are not used in conditions or expressions
    recursively explores all program
    called by verifications
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    err=""
    if tree==Special:                                                                    # explore all program
        for nod in sv.Object.values():
            for c,v in nod.clauses:
                
                # explore conditions
                A=c[1]                                                  
                if A:
                    for sto in Stochastic: 
                        if applied(A[0], sto):                                            # fatal error
                            err+="\n"+Err_not_allowed_cond+"\n     "+sto+ "-->" + A[0]  # *** Syntax error: operator not allowed in a condition ***
                    if applied(A[0], Call):                                               # verify volatile calls
                        for y in Volatile_calls:
                            if A[0].startswith(Call+Obr+Quote+y+Obr):     # fatal error               
                                err+="\n"+Err_not_allowed_cond+"\n     "+y+ "-->"+ A[0]  # *** Syntax error: operator not allowed in a condition ***
                                
                # explore values
                verif_stochastic(sv, tree=v)
                
        if err:
            print(err)
            raise ReferenceError
        
    else:                                                                                      # explore a single object
        op,A,B=tree                                                
        if op==Comma and A:                                                      # a list: recursively explore each element
            for x in A:
                if x: verif_stochastic(sv, tree=x)
        else:
            for x in [A, B]:
                if x:
                    for sto in Stochastic: 
                        if applied(x[0], sto):                                            # fatal error
                            err+="\n"+Err_not_allowed_expr+"\n     "+sto+ "-->"+ tree_join(tree)  # *** Syntax error: operator not allowed in an expression ***
                    if applied(x[0], Call):                                               # verify volatile calls
                        for y in Volatile_calls: 
                            if x[0].startswith(Call+Obr+Quote+y+Obr):     # fatal error               
                                err+="\n"+Err_not_allowed_expr+"\n     "+y+ "-->"+tree_join(tree)  # *** Syntax error: operator not allowed in an expression ***
                    verif_stochastic(sv, tree=x)                                     # recursively explore each term
                     
        if err:
            print(err)
            raise ReferenceError
        
#===================================================== verif_unused
def verif_unused(sv):
    """
    checks references to inputs or outputs declared as unused (fatal error)
    object should have no effect except to name a pin or an output
    and no cause except to name an output
    called by verifications
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        no change in sv. Error message only
    """
    if Unused in sv.Object and sv.Object[Unused].value:            # check presence and integrity of unused list
        unusedlist=[applied (x, Unused) for x in sv.Object[Unused].value]
        for nam in unusedlist:                                                    # check each unused declaration
            nod=sv.Object[nam]
            if sv.Namedpinlist.get(nam)==[nod.effects]: continue  # pin is just named
            elif applied(nam, Output):
                if len(nod.effects)==1:                                            # only effect is output list
                    if len(nod.causes)<=2: continue
                    if len(nod.causes)<=4 and Faux in nod.causes and Ewent in nod.causes: continue  # allow 'take event'
            elif nod.causes or nod.effects:                                    # object should have no cause and no effect
                print(Err_unused_obj)                       
                print(str(nam))
                sv.Current_clause=None, None, None
                raise ReferenceError
        
#=====================================================
#                                   ADJUST CLAUSES FOR VARIABILITY  
#===================================================== variability
def  variability(sv):
    """
    adapt clauses to the variability of objects
    simplify constant clauses, identify volatile objects for permanent monitoring
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    unchanging(sv)                          # remove change clause for constants 
    make_volatiles(sv)                       # create list of volatile objects and make their clause Always

#===================================================== unchanging
@lru_cache
def unchanging(sv):                             
    """
    remove clauses "change" "begin" or "end" concerning constants
    plain numbers, plain durations, Fixed objects, objects Load
    ignore self-referring conditions: 'object when change(object)'
    do not consider Booleans with value 'true' as constants
    completed by removechangeconst after initialization
    called by variability
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    for nod in sv.Object.values():
        clauselist=[]                                                    # initialize new clause list 
        for cond, vlu in nod.clauses:
            if cond[0]==Change:                                  # look for change condition
                if is_fixed(cond[1][0]): continue                # ignore clause   
                if cond[1][0]==nod.name: continue         # ignore clause   
            clauselist+=[(cond, vlu)]                              # accept clause
        nod.clauses=clauselist          

#===================================================== make_volatiles
def make_volatiles(sv):
    """
    create list of volatile (time-dependent) objects and make their clause Always
    so that they will be scanned and updated continuously
    applies to pointer, lasted, Itis
    called by variability
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
    """
    sv.Volatile=[]      
    for nam in sv.Object_list:
        for op in [Pointer, Lasted, Itis]:
            if applied(nam, op):                        # extract argument            
                vlu=(op, (applied(nam, op), None, None), None)
                sv.Object[nam].clauses=[((Always, None, None), vlu)]
                if op in [Lasted, Itis]: sv.Volatile+=[nam]
                break                                         # no need to check other op
            
#=====================================================
#                                      NATURE (TYPE) INFERENCE
#===================================================== determine_nature
def determine_nature(sv):
    """
    perform type inference (nature) of all expressions and objects
    nature is a list of Nmbr, Drtn, Bln, Stt or Lst (n.b. easier if nature was a set)
    the aim is to reduce the list to exactly one element
    loop until total number of possible natures stops decreasing
    even when only one nature is possible, work on clauses (recursively)
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        all information is directly stored in sv
     """
    # initialize object natures
    tot=totalize_natures(sv)
    prev=tot+1                                                                        # prev is keeping track of last score
    done=False

    # loop until done    
    while not done:                                                                  # loop until score does not progress + 1 loop
        for nam in list(sv.Object_list):                                          # some virtual objects may be added in the process
            nod=sv.Object[nam] 
            natres=get_nature(sv, nam, nod.nature)                       # get current or obvious nature

            # identify roots as lists
            get_list_nature_from_elements(sv, nam)
            
            # explore conditions and values
            find_nature_from_clauses(sv, nod, nam, natres)          # lots of work here

        # recompute total        
        tot=totalize_natures(sv)
        done=(tot==prev)                                                        # done is True if no progress
        
        # remove extra natures
        prev, done=simplify_nature(sv, tot, done)                     

    # eliminate extra nodes created by infer_nature    
    for nam in list(sv.Object_list):                                          
        if sv.Object[nam].isvirtual: eliminate(sv, nam)

#===================================================== totalize_natures
def totalize_natures(sv):
    """
    initialize nature of expressions and objects where it is explicit
    assign all possible natures otherwise
    compute total number of possible natures for all objects initially
    called by determine_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        tot: total number of possible natures for all objects
        nature information is directly stored in sv
     """
    tot=0                                                                            
    for nod in sv.Object.values():
        tot+=len(nod.nature)
    return tot

#===================================================== get_list_nature_from_elements
def get_list_nature_from_elements(sv, nam):
    """
    identify a list when its name is subscripted to extract an element
    called by determine_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nam: a string, an object name
    Returns
    --------
        nature information is directly stored in sv
     """
    piece=nam
    while Obr in piece:                                                           # look for last bracketed block
        first, block, last=findblock(piece)                                  # first block
        prev=0                                                                        # position of end of block
        size=0                                                                         # size of block+parentheses
        while block:
            size=len(block)+2                                                    # memorize size of block+parentheses
            prev+=last                                                              # memorize position of end of block
            piece=piece[last:]                                                     # explore after end of block
            first, block, last=findblock(piece)
        piece=nam[:prev-size]                                                 # remove last block 
        if piece in sv.Object:                                                    # part before last block is a list
            sv.Object[piece].nature=Lst[:]
        
#===================================================== find_nature_from_clauses
def find_nature_from_clauses(sv, nod, nam, natres):
    """
    assign Bln nature to conditions
    determine nature of values and parts thereof (recursively)
    identify delayed object
    called by determine_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        nod: an object of class Node (from sv.Object dict)
        nam: a string, the name of nod
        natres: a list of possible natures of nod
    Returns
    --------
        nature information is directly stored in sv
     """
    found=set(natres)                                                      # possible natures of nod
    for c,v in nod.clauses:                                                
        sv.Current_clause=(nam, c, v)                                 # info in case of bug 

        # force Boolean nature on condition        
        expr=tree_join(c)                                                     # name of condition                                                  
        if expr in sv.Object:
            sv.Object[expr].nature=Bln[:]
            sv.Object[expr].once=True
        if c[0]!=Change:                                                     # repeat on subcondition begin or end, not change
            subexpr=tree_join(c[1]) 
            if subexpr in sv.Object:
                sv.Object[subexpr].nature=Bln[:]
                sv.Object[subexpr].once=True

        # determine nature of value            
        expr=tree_join(v)                                                     
        natval=sv.Object[expr].nature[:] if expr in sv.Object else All_natures[:]  # initialize nature

        natval=infer_nature(sv, v, natval)                             # lots of work done here
        
        # check compatibility with object nature
        update_nature(sv.Object[expr], list(found), natval)
        found=sv.Object[expr].nature

    # update nature of object if necessary
    if len(found)<len(nod.nature): nod.nature=list(found)

#===================================================== update_nature
def update_nature(nod, result, hint):
    """
    update nod.nature by combining hint and result
    called by find_nature_from_clauses and infer_nature
    Parameters
    ------------
        nod: an object of class Node (from sv.Object dict)
        result: a list of possible natures of nod
        hint: a list of possible natures of nod
    Returns
    --------
        nature information is directly stored in nod
     """
    result=list(set(result) & set(hint)& set(nod.nature))                                        
    if nod.nature and not result:                                                           
        print("\n", Err_conflict_nat)                                                     # ***Error: nature conflict ***
        print(nod.name+Col, result, hint)
        if nod.once: print("condition must be an event")
        raise ReferenceError
    if len(result)<len(nod.nature): nod.nature=result                             

#===================================================== infer_nature
def infer_nature(sv, tree, hint):
    """
    identify nature of an object or expression, and parts thereof (recursively)
    nature is a list to be reduced to a single element (n.b. easier if nature was a set)
    combine information from multiple sources
    uses get_nature, which works on a name, not a tree
    called by find_nature_from_clauses
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: a tree expression
        hint: a list of possible natures
    Returns
    --------
        result: a list of possible natures
        more nature information is directly stored in sv
    """
    if not tree: return []                                                                 # empty tree: no nature
    O, A, B=tree                                                                           # decompose tree   
    if O==Obr: return infer_nature(sv, A, hint)                               # skip brackets and recurse

    # look for obvious nature
    expr=tree_join(tree)                                                                  # compute name of object
    nod=get_object(sv, expr)        
    result=get_nature(sv, expr, nod.nature)                                     # nature may be obvious
    update_nature(nod, result, hint)                                              # check compatibility and store nature

    # more info from operator and operands (recursively), even if we have already found result 
    if O in Allowed and (A or B):                                                   # constraints on operations
        nodA=get_object(sv, tree_join(A))                                         # get or create operands
        nodB=get_object(sv, tree_join(B))
        exprsA, oldnatA= nodA.name, nodA.nature
        exprsB, oldnatB= nodB.name, nodB.nature

        # use info from event lists       
        evlis=[]
        if O in [Any, All]:                                                                 # first arg is an event list
            result, newnatA, newnatB=Bln[:], Lst[:], []
            evlis=nodA.value                                                            # extract list of elements                    
        elif O == Pick:                                                                    # second arg is an event list
            result, newnatA, newnatB=Lst[:], Lst[:], Lst[:]
            evlis=nodB.value                                                            # extract second list
            
        if evlis:
            for z in evlis:                                                                   # make elements events
                if z in sv.Object: sv.Object[z].nature=Bln[:]                    
        else:
            # use info from operator
            newnatA, newnatB, more=combine(sv, nod, O, oldnatA, oldnatB, result) # find possible combinations
            result=list(set(result) & set(more))                                    # check result compatibility
            
        nodA.nature=list(set(oldnatA) & set(newnatA))        
        nodB.nature=list(set(oldnatB) & set(newnatB))                     # newnatB may be empty

    return result
    
#===================================================== get_object
def get_object(sv, expr):
    """
    extract object by name from sv.Object or create it
    initialize its nature
    called by infer_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        expr: a string the name of an object or expression
    Returns
    --------
        nod: an object from sv.Object
     """
    if expr in sv.Object:     
        nod=sv.Object[expr]                                                          # object exists
    else:                    
        nod=add_object(sv, expr)                                                   # create node for intermediate expression
        nod.isvirtual=True                                                              # temporary node
    return nod

#===================================================== combine
def combine(sv, nod, O, oldnatA, oldnatB, oldnatres):
    """
    combine natures oldnatA and oldnatB using O and nature of result (if known)
    returns nature of operands and result, or []
    called by infer_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        O: a string, an operator
        oldnatA: a list of possible natures for operand1
        oldnatB: a list of possible natures for operand2
        oldnatres: a list of possible natures for result
    Returns
    --------
        list(newnatA): a list of possible natures for operand1
        list(newnatB): a list of possible natures for operand2
        list(newnatres): a list of possible natures for result
    """
    newnatA, newnatB, newnatres = set(), set(), set()
    oldsetA, oldsetB, oldsetres=set(oldnatA), set(oldnatB), set(oldnatres)
    
    for allowA, a1, allowB, a2, allowres in Allowed[O]:                                   # test compatibility of hypotheses
        # simple operands without distributivity
        setA=set(allowA) & oldsetA                                                       
        setB=set(allowB) & oldsetB
        setres=set(allowres) & oldsetres             
        if (setres and setA and (setB or O in Unary)):                                       # hypothesis is valid
            newnatA.update(setA)                                                                    # add to list of possible natures
            newnatB.update(setB)
            newnatres.update(setres)

        # left distributivity (add list as a possible nature)    
        if not (O in Non_distributive1) and Lst[0] in oldnatA and Lst[0] in oldnatres: 
            newnatA.add(Lst[0])                                                                                
            newnatB.update(setB)                                                                   
            newnatres.add(Lst[0])

        # right distributivity (add list as a possible nature)      
        if not (O in Non_distributive2) and not (O in Unary) \
                                        and Lst[0] in oldnatB and Lst[0] in oldnatres:                  
            newnatA.update(setA)
            newnatB.add(Lst[0])
            newnatres.add(Lst[0])
    
    # check compatibility
    if not (newnatres and newnatA and (newnatB or O in Unary)):  
        print("\n", Err_incomp_nat)                                                                 # ***Error: incompatible nature ***                         
        print(O, oldnatA, oldnatB)
        if nod.once: print("condition must be an event:", nod.name)
        raise ReferenceError
    
    return list(newnatA), list(newnatB), list(newnatres)
    
#===================================================== simplify_nature
def simplify_nature(sv, tot, done):
    """
    remove extra natures when possible
    if there is no indication that an object is a list instead of a specific nature
    if there is no clear nature but state is possible 
    called by determine_nature
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tot: total of possible natures for all objects
        done: True if there was no progress in last iteration
    Returns
    --------
        prev: updated total of possible natures for all objects
        done: False if progress can still be made
        nature information is directly stored in sv
     """
    prev=tot
    # one pass to get rid of list nature
    if done:                                                                        
        for nod in sv.Object.values():
            if len(nod.nature)==2 and Lst[0] in nod.nature:    # not a list unless proved otherwise
                nod.nature.remove(Lst[0])
                prev-=1
                done=False                                                     # continue search 

    # one pass to infer a state
    if done:                                                                       
        for nod in sv.Object.values():
            if len(nod.nature)>1 and Stt[0] in nod.nature:      # a state unless proved otherwise 
                prev-=len(nod.nature)-1
                nod.nature=Stt[:]
                done=False                                                    # continue search 

    return prev, done

#=====================================================
#                                                    USEFUL LISTS
#===================================================== make_lists
def make_lists(sv):
    """
    build various useful lists
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    
    mark_delayed(sv)                      # identify delayed objects
    make_pin_list(sv)                         # detect and initialize inputs (to false) 
    make_old_list(sv)                      # create a list of used old/old 
    
#===================================================== mark_delayed
def mark_delayed(sv):
    """
    identify all delayed objects
    called by make_lists
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    for nod in sv.Object.values():
        if nod.nature==Bln:                           
            for c,v in nod.clauses:                            # need to check each clause
                if v and v[0]==Plus or v[0] in Glitch_list:
                    nod.isdelayed=True                                              

#===================================================== make_pin_list 
def make_pin_list(sv):
    """
    Identify inputs in use and related identities
    Identify outputs in use
    Pinlist is a list of pin names (e.g. "pin(3)") or key names (e.g. 'key("a")')
    Use slicing [len(Pin)+1:-1] to get number from name
    Pinstate is a dict from pin name to pin status (on/off times)
    Namedpinlist is a dict from pin name to equivalent name,
    Naming is used to easily identify pin function
    called by make_lists
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    sv.Pinstate.clear()                                     
    li=[]
    for nam in sv.Object_list:                                                    # browse objects                                                                      
        if  applied(nam, Key):                                                     # detect keys              
            sv.Pinlist+=[nam]
        elif applied(nam, Pin) and isnumber(nam[len(Pin)+1:-1]): # detect pins
            sv.Pinlist+=[nam]
            li+=[x for x in sv.Object[nam].effects if not x in li]     # list effects of pins (to look for named pins)
        elif applied(nam, Output) and isnumber(nam[len(Output)+1:-1]): # detect outputs
            sv.Outlist+=[nam]
            
    for nam in sv.Pinlist:                                                                                    
        sv.Pinstate[nam]=Faux                                                  # initialize to false                                          
        sv.Object[nam].clauses=[((Always, None, None),(nam, None, None))] # make sure pin is regularly scanned
        
    for nam in li:                                                                    # browse list of effects to find equivalent names                                                                              
        if not applied(nam, Count):        
            for pi in sv.Pinlist:                                                         # create Namedpinlist                                                                                       
                if pi.startswith(Pin):                                                   # (not for keys) 
                    ok=True
                    for c,v in sv.Object[nam].clauses:
                        # condition must be start or change(pin)
                        if c!=(Start, None, None) and c!=(Change, (pi, None, None), None): ok=False                    
                        # value must be pin with numerical index
                        if not (v and v[0]==Pin and tree_join(v)==pi): ok=False
                    if ok:
                        sv.Namedpinlist[pi]=nam                                # found equivalent name

#===================================================== make_old_list 
def make_old_list(sv, tree=Special):
    """
    make a list of objects for function old/old with tree search
    explore clauses and recurse on all terms
    called by make_lists
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    if tree==Special:                                                          # explore all tree  
        sv.Old_list=[]                                                       
        for nod in list(sv.Object.values()):                              # list may change during recursion
            for (c,v) in nod.clauses:
                make_old_list(sv, c)
                make_old_list(sv, v)
    elif tree:                                                                       # recursively explore branches
        op,A,B=tree
        if not A and not B: return                                         # ignore leaf
        if op==Comma:                                                       # special case: list
            for x in A:
                make_old_list(sv, x)                                        # process each element
        elif op!=Old:                                                          # process deeper branches
            make_old_list(sv, A)
            make_old_list(sv, B)
        else:                                                                        # 'old' detected: add object
            if not A[0] in sv.Old_list: sv.Old_list+=[A[0]]      # normally only a leaf
            nam=Old+Obr+A[0]+Cbr                                  # create object if necessary
            add_object(sv, nam)

#===================================================== last_changes
def last_changes(sv):                                                   
    """
    reorder subscripted operator
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        information is directly stored in sv
    """
    traverse(sv, correct_subscript)

#===================================================== correct_subscript
def correct_subscript(sv, tree):                                               
    """
    correct subscript structure e.g. cumul(L)(0) 
    called by last_changes
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
        tree: an object triplet or None
    Returns
    --------
        O: an operator
        A, B: triplets, representing the operands
    """
    if not tree or tree[0]!=Special: return tree
    O, A, B=tree                                                           # subscripting ( e.g. cumul(L)(0) )                                                                
    O=tree_join(A)                                                       # make operator from first term 
    A, B = B, None                                                       # make subscript from second term
    return O, A, B

#===================================================== reconstruct
def reconstruct(sv):
    """
    reconstruct program from tree
    called by compile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
    Returns
    --------
        prog: a string representing the reconstructed program
    """
    prog=""
    for nam in sv.Object_list:
        nod=sv.Object[nam]
        if nam and nam[0]!=Special:                       # ignore special objects (copies, etc.)
            prog+=nam+Col+Space
            for (c,v) in nod.clauses:
                prog+=Space+Space+Space+Space+When+Space+tree_join(c)+Col+Space+tree_join(v)+Crlf
            if not prog.endswith(Crlf): prog+=Crlf
    return prog

#===================================================== test_substitute
def test_substitute():
    old=list('abcdefghij')
    new=list('ABCDEFGHIJ')
    tree=('c', None, None)
    tree=('b', tree, None)
    tree=('a', None, tree)
    tree=('d', (Comma, [tree, tree], None), None)
    change=dict(zip(old, new))
    res=substitute(tree, old, change)
    print(res)
    assert( res==('D', (',', [('A', None, ('B', ('C', None, None), None)), ('A', None, ('B', ('C', None, None), None))], None), None) )

    old= [("random_pair.N'", None, None), ("random_pair.L'", None, None), ("random_pair.source'", None, None), ("random_pair.nature_hint'", None, None)]
    new= [('5', None, None), ("random_pair.5L'", None, None), ("random_pair.5source'", None, None), ("random_pair.5nature_hint'", None, None)]
    tree= ('ramp', ('+', ("random_pair.L'", ('1', None, None), None), ("random_pair.L'", ('2', None, None), None)), None)
    res=substitute(tree, old, new)
    print(res)

###===================================================== __main__ (tests)
if __name__== "__main__":
    import sys
    sys.exit()
    
    sv=sp.spell()
    try:
        tout=io.readscriptfile("../scripts/test.txt")                   # try precompiling a script and print result            
        print("============================================ Original script")
        print(tout)
        prog=pc.precompile(sv, tout)
        print("============================================ Canonic script\n")     
        print(prog)     
        compile(sv, prog)
        
    except ReferenceError:
        if type(sv.Current_clause)==tuple:
            nam, c, v = sv.Current_clause       
            sv.Current_clause=nam+Col+Space+When+Space+tree_join(c)+Col+Space+tree_join(v)       
        print(sv.Current_clause)
        print("\n---  PROCESS ABORTED  ---")
        
    print("\n============================================ Reconstructed script\n")
    print(reconstruct(sv))
##    input(Press_enter)                







