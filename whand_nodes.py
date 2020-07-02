from whand_parameters import *  # options, constants
from whand_operators import *   # from... import because module only contains constants

#===================================================== Node
Attributelist=[Name, Value, 'pointer', Count, 'nature', 'reuse', 'isunstable', 'isdefined', 'isfunction', 'isdict', 'isuserfunc', 'isvirtual', \
               'isuserdef', 'issolved', 'isnew', 'isexpression', 'isdelayed', 'arguments', 'clauses', 'causes', \
               'effects', Occur, Display, Lastchange, 'haschanged', 'once']
                # this list is used to copy a node

class Node:
    """
    Definition of a node
    """
    # -------------------------------------------------------------------------------------------- __init__
    def __init__(self):
        """
        Definition of data structure and default values
        Values may have one of the following nature:
        Bln: true/false (Boolean). Initialized to false unless otherwise specified
        Nmbr: any floating point or integer value (number). Initialized to zero unless otherwise specified
        Drtn: a number followed by some time unit (duration). Internally converted to seconds (see function seconds)
        Stt: any string of text (state). May need quotes
        Lst: variable names separated by commas with or without brackets (list (of lists))
        """
        self.name=""                                                        # name of object (used also in Object[name])
        self.value=None                                                   # None until affected
        self.pointer=0                                                      # for lists: internal pointer used with nexxt
        self.count=0                                                        # for Booleans: number of occurrences
        self.reuse=None                                                 # indicates reuse of changed value within a time step
        self.isunstable=False                                           # indicates effect of changed value within a time step
        self.nature=All_natures[:]                                    # list of Bln[0], Nmbr[0], Drtn[0], Lst[0], Stt[0] reduced when determined
        self.isdefined=False                                            # True for objects with explicit definitions in program       
        self.isfunction=False                                           # defined objects with brackets such as functions or list elements:       
        self.isdict=False                                                  # differentiates dictionaries from lists
        self.isuserfunc=False                                          # a user-defined function without its brackets
        self.isvirtual=False                                              # arguments of a function that are never defined (after instancing)
        self.isuserdef=False                                           # instance of a user-defined function (with real arguments)
        self.issolved=False                                              # indicates a user-defined function that has been solved
        self.isnew=False                                                  # indicates an object created during user function solve
        self.isexpression=False                                       # internal object created as a proxy for formulas
        self.isdelayed=False                                            # Boolean with onset/offset delayed by some duration
        self.arguments=[]                                               # temporary storage for function arguments (before parsing into tree)
        self.clauses=[]                                                     # when ... value list of trees for each object
        self.equivalent=None                                          # receives assignment without when
        self.causes=[]                                                      # objects involved in immediate definition
        self.effects=[]                                                      # objects affected by self
        self.occur=[]                                                       # list of begin instants for Booleans (limited by Max_occur_list)
        self.lastchange=None                                         # last time of change 
        self.haschanged=False                                       # used as a flag until processed
        self.once=False                                                   # used to prevent repeated updating during a time step e.g. in next
        self.display=False                                               # indicates output to screen

    # -------------------------------------------------------------------------------------------- content
    def content(self):
        """
        Returns a string with values of main attributes of a node
        """
        text= ""
        text+=self.name+ " "
        text+=str(self.nature)+  " "
        if self.isdefined: text+="defined "
        if self.isdict: text+="dict "
        if self.isfunction and not self.isdict: text+="function "
        if self.isexpression: text+="expression "
        if self.isdelayed: text+="delayed "
        text+="= "+  str(self.value)
        text+=" changed at "+ str(self.lastchange)
        return text
        
# -------------------------------------------------------------------------------------------- copynode
def copynode(nod,dup):
    """
    makes dup identical to nod (dup must already exist)
    lists are copied by value not by ref
    """
##    nom=dup.name
    for attr in Attributelist:
        if attr!= Name:                                   
            x=getattr(nod, attr)
            y=x if type(x)!=list else x[:]                    #make a copy by value
            setattr(dup, attr, y)
##    dup.name=nom
    return dup

# -------------------------------------------------------------------------------------------- copynode2
def copynode2(nod,dup):
    """
    copies only essential elements of nod into dup (faster)
    """
    x=nod.value
    dup.value=x if type(x)!=list else x[:]
    dup.lastchange=nod.lastchange          
    dup.nature=nod.nature[:]
    dup.isdelayed=nod.isdelayed               
    dup.occur=nod.occur[:]
    dup.pointer=nod.pointer
    dup.count=nod.count
    return dup

