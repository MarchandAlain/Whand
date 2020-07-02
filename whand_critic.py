# this module contains verification functions to avoid 
# temporal collisions leading to unpredictable results
from whand_parameters import *   # options, constants
from whand_tools import *

Verbose=False

##===================================================== variable
def variable(sv, cau):
    """
    verifies that cau is not a constant
    """
    ok=True
    if isnumber(cau): ok=False
    if cau in Fixed: ok=False
    if isduration(cau): ok=False    
    if cau in [Ewent, Number, Time, State, List]: ok=False
    return ok

##===================================================== link_effect
def link_effect(sv, cau, eff, effect):
    """
    compute immediate effects from one cause
    """
    if eff!=cau and variable(sv, cau):
            if not cau in effect: effect[cau]=[]                                 # create key for cause if needed               
            if not eff in effect[cau]:                                                 # avoid duplicates
                effect[cau]+=[eff]                                                    # add effect to dictionary
    return effect

##===================================================== build_effects
def build_effects(sv):
    """
    compute immediate effects of all objects as a dictionary
    uses conditions as causes
    uses values as causes
    ignore copies and constants
    """
    effect={}
    effect.clear()                                                                                          # erase dictionary 
    for eff in sv.Object:
        if not eff.startswith(Special) and not eff in Fixed+[Start] \
                                   and not isnumber(eff) and not isduration(eff):       # ignore copies and constants
            if Verbose: print(eff,":")

            # first link list element to its parent list
            here, block, there=findblock(eff)                                                   # detect list elements
            if here and there==len(eff) and eff[:here] in sv.Object:                  # found a root in object dict
                if not eff in effect: effect[eff]=[]                                                 # create key for effect if needed
                if not eff[:here] in effect: effect[eff]+=[eff[:here]]                      # link element to root list
                
            # then link argument to Boolean function instance
            cau=applied(eff, Idem)+applied(eff, Begin)+applied(eff, End)+applied(eff, Change) \
                 +applied(eff, Not)+applied(eff, All)+applied(eff, Any)              # argument is the cause
            if cau:                                                                                              # a Boolean function instance
                effect[cau]=[eff]                                                                         # link argument                                    
            else:                                                                                                # not a Boolean function instance
                nod=sv.Object[eff]
                for c,v in nod.clauses:                                                                 # browse object definition
                    if Verbose: print("         ",c,"  ",v)
                    
                    # work on conditions as causes (condition based on a single event)
                    if c[0] ==Always:
                        cau=eff
                        effect=link_effect(sv, cau, eff, effect)
                    elif c[0]==Start:
                        cau=Start
                        effect=link_effect(sv, cau, eff, effect)
                    else:                                                                                         # c[0] is begin, end or change
                        # make an indirect link through treejoin(c) if it is in sv.Object
                        cau1=treejoin(c)
                        if cau1 in sv.Object:
                            effect=link_effect(sv, cau1, eff, effect)
                            cau2=c[1][0]
                            effect=link_effect(sv, cau2, cau1, effect)
                        else:
                            cau=c[1][0]                                                                   
                            # avoid loops and constant causes
                            effect=link_effect(sv, cau, eff, effect)

                    # work on values as causes
                    if v[0]==Comma:                                                                      # in a list, each element is a cause
                        causelist=v[1]
                    elif v[0] in sv.Object:                                                                 # not a list, a simple object
                        causelist=[(v[0], None, None)]
                    else:                                                                                          # an operation or function
                        causelist=[v[1]]
                        if v[2]: causelist+=[v[2]]                                                       # consider all terms
                    if Verbose: print("     causelist", causelist)
                    if causelist:
                        for tree in causelist:
                            if Verbose: print("               cause", tree)
                            cau=tree[0]                                                                      # extract name 
                            if eff!=cau:
                                if not cau in effect: effect[cau]=[]                        # create key for cause               
                                if not eff in effect[cau]:
                                    effect[cau]+=[eff]                                            # add effect to dictionary

    # print dictionary of effects
    if Verbose:
        print("\nEffects:")
        for cau in effect:
            print(cau+":", effect[cau])
        print()

    return effect                                                                                       # return dict of effects

##===================================================== maketime
def maketime(todo, li, offset, par):
    """
    returns timing with offset and identify parent cause
    avoid repeating time from same parent
    """
    res=todo[:]                                                                      # prior timing of object
    for t in li:                                                                          # timings of cause
        tim=t[0]+"+"+offset if offset else t[0]                         # incorporate delay
        ti=tim.split("+")
        ti.sort(reverse=True)
        tim="+".join(ti)
        if not (tim, par) in res:                                               # add timing if new
            res+=[(tim, par)]                                                      # build timing list
    return res

##===================================================== moretime
def moretime(nom, v, timing):
    """
    verifies timing overlap with value
    adds intersection to timing of object
    """
    res=timing[nom]                                                               # prior timing of object
    op, A, B=v
    for u in [op, A[0] if A else None, B[0] if B else None]:       # check all components of value
        if u in timing:
            ti=[x[0] for x in res]                                                   # prior times
            for t, par in timing[u]:                                               # find intersection
                if t!=par and t in ti and not (t, par) in res:
##                    for par2 in [c for (l,c) in res if l==t]:
##                       if not par2.startswith(par) and not par.startswith(par2) \
##                          and not applied(par, Idem)+applied(par2, Idem)+applied(nom, Idem) \
##                          and not applied(par, End)+applied(par2, End):
                    
                            print("******", nom+":", (t,par))
##                            print(res)
##                            print(vlu)
##                            os._exit(1)                                                   # stop to debug
                            res+=[(t, par)]
    return res

##===================================================== count
def count(times, cau):
    """
    Verifies how many times cause has contributed to timing
    """
    counter=0
    for (t,c) in times:                                                             # timings of object
        if c==cau: counter+=1
    return counter

##===================================================== criticize
def criticize(sv):
    """
    Analyse program for possible collisions
    effect is a dictionary of direct effects (list) of events
    the script is explored recursively, starting from 'start'
    """
    effect=build_effects(sv)
    timing={}
    timing.clear()                                                                 # erase dictionary
    seeds=[Start]+[x for x in sv.Object if applied(x, Pin) or applied(x, Key)]
    for name in seeds:
        if Verbose: print(">>>> seed:", name)
        timing[name]=[(name, name)]                                  # timing information
        parent=name
        timing, effect=find_timing(sv, name, name, effect, timing, seeds)
    # analysis is complete            
    print()
    timelist=list(zip(list(timing.keys()), list(timing.values())))
    for name, li in timelist:
        if sv.Object[name].nature!=Lst:                                    # ignore lists
            ti=[x[0] for x in li]
            cau=[x[1] for x in li]
            for i in range(len(ti)):                                               # compare pairs of times
                for j in range(len(ti)-i-1):
                    if ti[i]==ti[i+j+1] and cau[i+j+1] and cau[i]!=cau[i+j+1]:
                        bad=True                                                    # verify if it is a true collision
                        tim, cau1, cau2=ti[i], cau[i], cau[i+j+1]
                        if tim in seeds: bad=False
                        if applied(cau1, Idem) or applied(cau2, Idem): bad=False
                        if applied(name, cau1) or applied(name, cau2): bad=False
                        if bad:                                                         # verify if it has consequences
                            bad=False
                            for eff in effect[name]:
                                tix=[x[0] for x in timing[eff]]
                                if tim in tix: bad=True
                            if bad:
                                warn("\n*** BEWARE OF RACE CONDITION (unreliable behavior) ***\n"+name \
                                  +":\n    "+cau[i]+" --> "+ ti[i]+ "\n     "+cau[i+j+1]+ " --> "+ ti[i+j+1], fatal=Fatal_race)
        
##===================================================== find_timing
def find_timing(sv, nom="", parent="", effct={}, timg={}, seeds=[]):
    """
    Analyse program for possible collisions
    effect is a dictionary of direct effects (list) of events
    the script is explored recursively, starting from 'start'
    """
    effect=dict(effct)
    timing=dict(timg)
    max_depth=5
    if Verbose: print(">>", nom)
    prev=timing[nom] if nom in timing else []
    nod=sv.Object[nom]                                                         # this is the effect
    if nod.clauses:                                                                   # examine all clauses for values 
        for c,v in nod.clauses:                                                   # look for delayed expressions
            if Verbose: print("      clause:", c,v)
            offset=""
            cau=parent           
##                if c[0]==Change and c[1][0]==treejoin(v):              # try to
##                    pass                                                                     # ignore tracking value
##                else:
            if v[0]==Since: v=(Plus, v[2], v[1])                             # change Since into Plus 
            if v[0]==Plus and sv.Object[v[1][0]].nature==Bln:                                        
                offset=v[2][0]                                                        # duration added
                cau=v[1][0]                                                            # event
                if cau in timing:                                                      # use cause to compute delayed time
                    timing[nom]=maketime(timing[nom], timing[cau], offset, cau)
                    if Verbose: print("timing("+nom+"):", timing[nom])
            else:                                                                           # not delayed
                if c[0]==Always:
                    cau=nom
                else:
                    cau=Start if c[0]==Start else c[1][0]                  # begin, end or change
                if cau in timing:                                                      # same timing as the condition 
                    timing[nom]=maketime(timing[nom], timing[cau], "", cau)
                    if Verbose: print("timing("+nom+"):", timing[nom])
                # verify timing of condition and value and add value timing to condition if overlap
##                    timing[nom]=moretime(nom, v, timing)

    if nom in effect and (nom in seeds or timing[nom]!=prev):
        if Verbose: print("next("+nom+"):", effect[nom])
        for eff in effect[nom]:                                                   # follow all next effects
            if not eff in timing: timing[eff]=[]                             # create timing key for object
            if applied(nom, eff):                                                  # list element
                if nom in timing and timing[nom]:
                    timing[eff]+=[x for x in timing[nom] if not x in timing[eff]]
            elif nom in timing and timing[nom]:                        # avoid infinite loop   
                if count(timing[eff], nom)<max_depth:               # needed to stop recursion
                    timing, effect=find_timing(sv, eff, nom, effect, timing, seeds)               # RECURSE HERE

    return timing, effect

###===================================================== main
if __name__== "__main__":
    print("whand_critic.py: syntax is correct")





