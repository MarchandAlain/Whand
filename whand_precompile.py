# -*- coding: ISO-8859-1 -*-
import os                                       # for os.exit()
import string
from whand_parameters import * # options, constants
from whand_operators import *   # module only contains constants: Keywords, standard lists and error messages
from whand_tools import *          # useful procedures 
import whand_io as io                  #  I/O module for drivers. Required for includes
import whand_sharedvars as sp    # for tests

#====================================================================== precompile
def precompile(sv, prog):
    """
    Precompile Whand script: cleanup, develop abbreviated syntax, add included files
    and convert to canonic form 'name: when condition: value'
    called by whand_V2 (main)
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
            NB. sv is used to store a separate dict of strings sv.Strings for each program unit, temporary (use and clear a common variable instead?)
        prog: a string containing the text of a script
    Returns
    --------
        text: a string in canonic form but no parsing        
    """
    verbose=('prc' in Debog)

    # prepare text and add includes
    if verbose: print("\nPreparing text.")
    piece=prepare(sv, prog)
    
    # canonic form
    if verbose: print("\nArranging canonic form..")
    can=canonic(piece)
   
    # replace spaces with brackets and restore strings in names 
    if verbose: print("\nAdjusting names..")
    lines=adjust_names(sv, can)

    # separate arguments for , show and unused 
    text=cut_showunused(lines)           
    return text
        
#===================================================== prepare
def prepare(sv, prog):
    """
    prepare and cleanup program read by whand_io readscriptfile
    add includes (pieces of program stored on file), protect quoted strings from modification,
    check tabs, spaces, brackets and double quotes
    n.b. chars have been filtered, comments removed and lines fused in readscriptfile
    called by precompile
    Parameters
    ------------
        sv: an instance of the spell class (whole interpretable unit) from whand_sharedvars.py
            NB. sv is used to store a separate dict of strings sv.Strings for each program unit (maybe use a common variable instead?)
        prog: a string containing the text of a script, lines separated by CR+LF to be printable
    Returns
    --------
        prog: a string representing cleaned up script        
    """
    done=False                                                                # to repeat processing after each include
    prog=Crlf+Lf+prog                                                    # in case an include is on first line
    while not done:                                                          # iterate after each include
        done=True
        # check number of quotes and save strings
        for lig in prog.split(Crlf):
            if not verify_balance(lig, Quote, Quote):
                print("\n", Err_unbalanced_quotes)                # Fatal error: unbalanced quotes
                print(lig)
                raise ReferenceError
        prog=save_strings(sv, prog)   # replace strings with a key for protection (keywords inside strings must not be parsed)
                                                   # code is storage key, e.g.  §Chain3§ and dict sv.Strings[code] is string content 
        
        # check number of brackets (ignores those within quotes)   
        for lig in prog.split(Crlf):
            if not verify_balance(lig, Obr, Cbr):
                print("\n", Err_unbalanced_brackets)              # Fatal error: unbalanced brackets
                print(lig)
                raise ReferenceError
            
        # remove extra spaces and Line Feeds       
        prog=white_strip(prog)                                           # remove whitespaces before and after lines
        prog=change_all(prog, Crlf+Lf+Crlf,Crlf)                  # remove empty lines 
        prog=prog.replace(Lf,'')                                         # remove line feeds (leave only carriage returns)
        prog=change_all(prog, Space+Space, Space)           # remove multiple spaces (outside strings)

        # process includes (pieces of program stored on file)
        prog2=substitute_includes(sv, prog)                       # substitute includes once and cleanup again if changed
        if prog2!=prog:
            done=False                                                       # iterate cleanup if new include
            prog=prog2
        
    # check that there is a program    
    if len(prog.replace(Crlf,''))<2: 
        print("\n", Err_empty_prog)                                   # Fatal error: program script is empty                                  
        raise ReferenceError

    return prog
   
#===================================================== save_strings
def save_strings(sv, prog): 
    """
    replace and store strings in sv.Strings dictionary
    because keywords inside strings must not be parsed
    strings are restored after compile
    called by prepare
    Parameters
    ------------
        sv: an instance of the spell class (whole interpretable unit) from whand_sharedvars.py
            NB. a separate, temporary dict of strings sv.Strings is used for each program unit (maybe use a common variable instead?)
        prog: a string containing the text of a script, lines separated by CR+LF to be printable
    Returns
    --------
        prog: a string containing the text of a script        
    """
    count=0                                                                 # number of strings
    while Quote in prog:
        here=prog.find(Quote)                                       # find opening quote
        there=prog.find(Quote, here+1)                          # find next quote (closing quote)
        if there<0:
            print(Err_unfinished_string)                            # Fatal error: End of File while parsing string                                 
            print(prog[here+1:])                                       # should not occur if quotes are balanced 
            raise ReferenceError
        count+=1
        code=Chain+str(count)                                       # storage key, e.g.  `Chain3`
        while code in sv.Strings:
            count+=1
            code=Chain+str(count)                                       # storage key, e.g.  `Chain3`           
        sv.Strings[code]=prog[here+1:there]                    # save string in a dictionary 
        prog=prog[:here]+Special+code+Special+prog[there+1:]  # replace with storage key
    return prog

#===================================================== verify_balance
def verify_balance(line, osep, csep):
    """
    verify balance of opening (osep) and closing (csep) separators in a line
    e.g. number of quotes or brackets
    called by prepare
    Parameters
    ------------
        line: a string from a script
        osep: opening separator (e.g. '(' )
        csep: closing separator   (e.g. ')' )
    Returns
    --------
        a Boolean: False if separators do not match       
    """
    ocount=0                                                                                 # number of opening separators
    ccount=0                                                                                 # number of closing separators
    for c in line:
        if c==osep: ocount+=1
        if c==csep: ccount+=1
    if osep==csep:                                                                           # same separator (e.g. " ): check parity 
        if ocount%2!=0: return False         
    elif ocount!=ccount: return False                                              # numbers must match 
    return True

#===================================================== white_strip  
def white_strip(prog):           
    """
    remove leading and trailing spaces and tabs
    assume carriage returns (Crlf) are followed by line feeds (Lf)
    called by prepare
    Parameters
    ------------
        prog: a string containing the text of a script
    Returns
    --------
        text: a string        
    """
    text=""                                                                          # to build result
    buff=""                                                                         # temporary storage for whitespaces
    middle=False
    for char in prog:
        if char==Lf and not middle: continue                         # Lf will be added after CR
        elif char==Crlf:                                                          # ignore buffer at end of line
            middle=False
            text+=Crlf+Lf
            buff=""
        elif char!=Space and char!=Tab and char!=Lf: 
            middle=True                                                         # start at the first non whitespace
            text+=buff+char                                                   # use and empty buffer
            buff=""
        elif middle:                                                                # keep whitespaces in the middle
            buff+=char
    return text
#===================================================== substitute_includes  
def substitute_includes(sv, prog):           
    """
    insert file content to replace include line. These syntaxes are allowed:
    include(my_module.txt)       include("my_module.txt")
    include my_module.txt        include "my_module.txt"
    include (my_module.txt)      include ("my_module.txt")
    called by prepare
    Parameters
    ------------
        sv: an instance of the spell class (whole interpretable unit) from whand_sharedvars.py
            NB. a separate, temporary dict of strings sv.Strings is used for each program unit (maybe use a common variable instead?)
        prog: a string containing the text of a script, lines separated by CR+LF to be printable
    Returns
    --------
        prog: a string containing the text of a script        
    """
    for osep,csep in [(Space, Crlf),(Obr, Cbr)]:         # various separators allowed
        # look for includes at the start of a line
        here=prog.find(Crlf+Include+osep) 
        if here>-1:
            there=prog.find(csep, here+1)
            if there==-1:                                          # no closing separator
                print("\n", Err_syntax)                         # Fatal error: no ending separator                                   
                raise ReferenceError
            
            # extract line and check end after closing separator
            eol=prog.find(Crlf, here+1)                    # find next end of line
            if eol==-1: eol=len(prog)+1
            line=prog[here:eol]                                # line containing the include
            txt=line
            if osep==Obr:
                txt=line[:-1]
                if here+len(txt)!=there:                        # check length
                        print("\n", Err_syntax_extra_chars) # Fatal error: illegal characters at end of line                                   
                        print([line])
                        raise ReferenceError

            # extract filename, maybe between brackets
            name=txt[len(Crlf+Include+osep):]        
            if name.startswith(Obr): name=name[1:]
            if name.endswith(Cbr): name=name[:-1]
            name=name.strip(Space)
            if name.startswith(Special+Chain): name=sv.Strings[name[1:-1]]   # restore string
            name=addparentdir(name)                            # add path

            # read file content
            newlines=""
            try:
                newlines=io.readscriptfile(name)                # read include file via whand_io module

            except IOError:
                print(Err_404)                                            # Fatal error: File not found
                print(str([name])[1:-1])                               # display all chars
                raise ReferenceError

            # insert text replacing include line
            prog=prog.replace(line[1:], newlines)             # keep initial Crlf
            break                                                            # stop looking for separators
    return prog
    
#===================================================== canonic
def canonic(prog): 
    """
    reshape program into canonic form. 
    uses functions from whand_tool module
    called by precompile
    Parameters
    ------------
        prog: a string containing the text of a script, lines separated by CR+LF to be printable
    Returns
    --------
        text: a string in canonic form without any parsing        
    """
    verbose=('cnn' in Debog)
    # replace synonyms (see Alphachangelist in whand_operators.py)
    for old, new in Alphachangelist:                                      
        prog=alphachange(prog, old, new)                             
 
    # separate lines beginning with when and until
    lines=cut_when(prog)

    # detect names, fill in implicit true and false after when and until
    lines=complete_clauses(lines)
    
    # cut at colons, but keep colons. These colons precede values.
    lines=cut_values(lines)
    
    # fill in start and change conditions where needed
    lines=complete_cond(lines)

    # finish filling in and check structure
    lines=finalize_conds(lines)

    # reconstruct text and remove temporary codes
    text= Crlf.join(lines)
    text=text.replace(Definition,"")        # n.b. does not remove equivalence codes

    if verbose: print("\nCanonic:\n"+text)    # strings still under protected form
    return text

#===================================================== alphachange
def alphachange(prog, old, new):
    """
    change an alphabetic keyword into a synonym
    keywords are detected when contiguous to separators from list Symb, but not if they are part of other names
    Symb=[Plus, Minus, Mult, Div, Equal, Nequal, Greater, Smaller, Col, Obr, Cbr, Crlf, Space, Tabul, Tab, Mline, Comma, Space]
    called by canonic
    Parameters
    ------------
        prog: a string containing the text of a script
        old: an alphabetic keyword to be replaced
        new: the alphabetic keyword replacing it
    Returns
    --------
        pr: a string with synonyms replaced        
    """
    pr=Space+prog+Space                                                              # add spaces around prog
    for osep in Symb:
        # special case: print function
        pr=pr.replace(osep+Print+Obr, osep+Tell+Obr)                 # substitute
        pr=pr.replace(osep+Print+Space+Obr, osep+Tell+Obr)                 # substitute
        for csep in Symb:           
            pr=pr.replace(osep+old+csep, osep+new+csep)                 # substitute
    return pr[1:-1]                                                                           # remove spaces around prog                                               

#===================================================== cut_when
def cut_when(prog): 
    """
    Separate words when and until and cut lines into different fields:
    - name
    - clause preceded by 'when' or 'until'
    called by canonic
    Parameters
    ------------
        prog: a string containing the text of a script
    Returns
    --------
        lines: a list of names or clauses        
    """
    # add spaces as separators
    for word in [When, Until]:
        prog=prog.replace(word+Obr, word+Space+Obr)                     # add space after word and before bracket
        for preced in [Crlf, Col, Cbr]:
            prog=prog.replace(preced+word, preced+Space+word)        # add space before word
    # add Crlf and cleanup spaces
    prog=prog.replace(Space+When+Space, Crlf+When+Space)    # cut before when 
    prog=prog.replace(Space+Until+Space, Crlf+Until+Space)       # cut before until 
    prog=change_all(prog, Space+Crlf, Crlf)                                    # remove trailing spaces
    prog=change_all(prog, Crlf+Crlf, Crlf)                                       # remove empty lines
    prog=prog.strip(Crlf)                                                               # remove empty first or last line
    # cut lines
    lines=prog.split(Crlf)                                                               # cut lines
    return lines

#===================================================== complete_clauses
def complete_clauses(lines):
    """
    fill in clause preceded by 'when' or 'until' with ':true' or ':false'
    identify lines containing a name (definition)
    called by canonic
    Parameters
    ------------
        lines: a list of names or clauses        
    Returns
    --------
        lines: a list of names or clauses        
    """
    for num, lig in enumerate(lines):       
        if lig.startswith(Until+Space):
            lines[num]=lig.replace(Until,When)                                # until is equivalent to when
            if  not Col in lig:
                lines[num]=lines[num]+Col+Faux                             # fill in default value ':false'        
        elif lig.startswith(When+Space):
            if not Col in lig:                                                            # fill in default value ':true'      
                lines[num]=lig+Col+Vrai
        else:                                                                                  # start a new definition
            lin=Definition+lig                                                         # mark definition at beginning of line
            lin=lin.rstrip(Col)                                                           # remove column at end (before when)
            lines[num]=lin.rstrip(Space)                                           # remove trailing spaces
    return lines

#===================================================== cut_values
def cut_values(lines):
    """
    cut at colons to extract value, fill in implicit 'true'
    called by canonic
    Parameters
    ------------
        lines: a list of names or clauses        
    Returns
    --------
        lines: a list of names or clauses        
    """
    text= Crlf.join(lines)+Crlf                                                 # join lines again adding emptly line at end   
    text=text.replace(Col, Crlf+Col)                                        # end of line at colon
    text=change_all(text, Crlf+Col+Space, Crlf+Col)                # remove leading spaces
    text=change_all(text, Crlf+Col+Crlf, Crlf+Col+Vrai+Crlf)    # fill in isolated colons with 'true'
    text=text[:-len(Crlf)]                                                        # remove emptly line at end
    lines=text.split(Crlf)                                                         # cut lines again
    return lines

#===================================================== complete_cond
def complete_cond(lines):
    """
    fill in implicit conditions: equivalences are replaced with 'when start' and 'when change' conditions
    values involving 'change' are a special case. They need an extra end condition because change is transient
    equivalences are tagged with special code Equal+Special in prevision of future developments
    called by canonic
    Parameters
    ------------
        lines: a list of names, conditions or values        
    Returns
    --------
        lines: a list of names, conditions or values        
    """
    count=-1                                                                      # this is a check for both conditions and values
    for num, lig in enumerate(lines):
        if lig.startswith(Definition):                                           # starts a new definition                                   
            count=0                                                                 # zero check
            nam=lig[len(Definition):]                                         # get object name 
        else:
            if count==-1:
                print(Err_missing_name)             # syntax error: missing name or too many values (fatal error)
                print(lig)
                raise ReferenceError
            count+=1                                                             # count lines after definition
            if count==1 and not lig.startswith(When):                # a value without when condition is an equivalence
                lines[num-1]=Definition+Equal+Special+lines[num-1][len(Definition):]    # tag equivalence with special definition mark    
                if lig.startswith(Col+Change+Space) or \
                           (lig.startswith(Col+Change+Obr) and lig.endswith(Cbr)):  # look for a 'change' value
                        obj=lig[len(Col+Change):]                           # get change argument                                                                                                                 
                        lines[num]=When+Space+Change+obj+Crlf+Col+Vrai+Crlf       # fill in 'true' (no begin for change)                            
                        lines[num]+=When+Space+nam \
                                 +Plus+Epsilon+Div+"4"+Crlf+Col+Faux            # end condition delayed by epsilon/4 (new clause)                   
                else:                                                                 # it is not a 'change' value
                    lines[num]=When+Space+Start+Crlf+lig+Crlf                               # fill in 'start' condition
                    lines[num]+=When+Space+Change+Obr+lig[1:]+Cbr+Crlf+lig       # fill in 'change' condition (new clause)
    # update line structure
    text= Crlf.join(lines)                                                       # join, then split again to create extra lines
    lines=text.split(Crlf)
    return lines

#===================================================== finalize_conds
def finalize_conds(lines):
    """
    fill in definitions
    complement empty definitions with 'when start: true'
    Verify there is no value without object name
    called by canonic
    Parameters
    ------------
        lines: a list of names, conditions or values        
    Returns
    --------
        lines: a list of names, conditions or values        
    """
    bad=""
    count=-1
    for num, lig in enumerate(lines):
        if lig.startswith(Definition):                                        # it is a definition
            if count==0:                                                        # complete preceding empty definition with 'when start: true'
                lines[num]=When+Space+Start+Crlf+Col+Vrai+Crlf+lig
            count=0
        else:
            count=1                                                              # found at least one clause
        if lig==Definition+Equal+Special:                            # missing name
            print(Err_missing_name)                                      # syntax error: missing name or too many values (fatal error)
            if num>0:
                print(lines[num-1])
            raise ReferenceError
    if count==0:                                                               # complete empty definition on last line
            lines[-1]=lines[-1]+Crlf+When+Space+Start+Crlf+Col+Vrai
                   
    # update line structure
    text= Crlf.join(lines)                                                     # join, then split again to create extra lines
    lines=text.split(Crlf)
    return lines

#===================================================== adjust_names
def adjust_names(sv, text): 
    """
    in defined names:
    replace spaces with brackets
    restore strings 
    cleanup spaces
    called by precompile
    Parameters
    ------------
        sv: an instance of the spell class (program unit) from whand_sharedvars.py
            NB. sv is used to store a separate dict of strings sv.Strings for each program unit, temporary (use and clear a common variable instead?)
        text: a string in canonic form
    Returns
    --------
        lines: a list of lines        
    """
    verbose=('adn' in Debog)
    lines=text.split(Crlf)                                                                  # work line-by-line
    for num, lig in enumerate(lines):
        if not lig.startswith(When) and not lig.startswith(Col):            # look for names
            
            # change Spaces into brackets
            lig=lig.strip(Space)                                                           # remove leading and trailing spaces
            lig=unspace(lig, [Obr, Cbr, Comma])                                 # remove spaces before and after separators
            nbspaces=0               
            while Space in lig:                                                            # change Spaces into brackets
                nbspaces+=1
                here=lig.rfind(Space)                                                   # start replacing from the right                
                # some ambiguities cannot be properly solved (e.g. show count X, count Y)                    
                lig=lig[:here]+Obr+lig[here+1:]+Cbr                            # enclose in brackets everything that follows the last space
            if nbspaces>1:                                                                # final structure may not be what was intended (e.g lists)
                warn(Warn_multiple_spaces+"      "+lig+Crlf)               # Warning: multiple spaces. Brackets may help disambiguate                 

            # restore strings in defined names          
            while Special+Chain in lig:
                code=""
                there=-1
                here=lig.find(Special+Chain)                                      # look for first delimiter
                there=lig.find(Special, here+1)                                   # look for second delimiter
                if there>-1:
                    code=lig[here+len(Special+Chain):there]                # extract text  
                    code=Chain+code
                    lig=lig[:here]+Quote+sv.Strings[code]+Quote+lig[there+1:]  # replace
                else:
                    print(Anom_string_key)                                         # *** String anomaly ***
                    raise ReferenceError                
            lines[num]=lig                                                              # store modified line

    return lines

#===================================================== unspace
def unspace(text, op_list): 
    """
    remove spaces around specific chars
    called by adjust_names
    Parameters
    ------------
        text: a string
        op_list: a list of strings to be stripped from spaces
    Returns
    --------
        text: a string        
    """
    if Space in text:
        for op in op_list:
            text=change_all(text,Space+op, op)                                  # remove spaces before op
            text=change_all(text,op+Space, op)                                  # remove spaces after op 
    return text

#====================================================================== cut_showunused
def cut_showunused(lines):                      
    """
    develop lists into several lines for , Show and Unused
    preserve text between quotes
    called by precompile
    Parameters
    ------------
        lines: a list of lines in canonic form
    Returns
    --------
        text: a string        
    """
    clau=When+Space+Start+Crlf+Col+Vrai                    # 'when start: true'
    newlines=[]
    for l, lig in enumerate(lines):
        found=""
        for root in [Show, Unused]:                                   # look for form 'root(...)'         
            if lig.startswith(root+Obr) and lig[-len(Cbr):]==Cbr:  
                found=root
                break                                                           # roots are mutually exclusive
        if found:                                                              # maybe need to split
            block=lig[len(found+Obr):-len(Cbr)]                 # extract argument                 
            elts=splitlist(block)                                           # look for commas outside brackets and split argument
            for e in elts[:-1]:                                                # repeat for each argument except last
                newlines+=[found+Obr+e+Cbr]+[clau]         # create name 'root(...)' and clause
            newlines+=[found+Obr+elts[-1]+Cbr]               # clause for last argument already exists
        else:
            newlines+=[lig]                                                # store line without change
    text= Crlf.join(newlines)
    return text

###===================================================== main (tests)
if __name__== "__main__":

# test white_strip
    test=white_strip("\n\r \t \t a \ta\t \t \r\n")
##    print((test,))
    assert(test=="\n\ra \ta\n\r")
    
# test cut_showunused
    lines=["show(a,b)", "when start\n:true", "unused(c,d)", "when start\n:true"]
    test=cut_showunused(lines)                                  
##    print((test,))
    assert(test=='show(a)\nwhen start\n:true\nshow(b)\nwhen start\n:true\nunused(c)\nwhen start\n:true\nunused(d)\nwhen start\n:true')
    
# try precompiling scripts/essai.txt and print result
    sv=sp.spell()
    try:
        name="../scripts/essai.txt"                                     
        tout=io.readscriptfile(name)
        prog=precompile(sv, tout)
        print(Crlf+"============================================")
        print(prog)
        
    except ReferenceError:
        print("\n---  PROCESS ABORTED  ---")
        print(Crlf+"============================================"+Crlf)

    

