# -*- coding: ISO-8859-1 -*-
import os                                       # for os.exit()
import string
from whand_parameters import * # options, constants
from whand_operators import *   # module only contains constants: Keywords, standard lists and error messages
from whand_tools import *          # useful procedures 
import whand_io as io                  #  I/O module for drivers. Required for includes
import whand_sharedvars as sp    # for tests

#===================================================== prepare
def prepare(sv,prog):
    """
    prepare and cleanup program:
    add includes, remove comments, protect strings
    check tabs, spaces and double quotes
    returns full text
    """
    verbose=('prp' in Debog)                         # used to print debugging info
##    print([(c,ord(c)) for c in prog])
    if Special in prog:                                          # Special char § is not allowed in script
        prog=prog.replace(Special, "c")           # because of ç
##       print(prog)
##        print("\n", Err_illegal_special)                                      
##        raise ReferenceError

    # comments, includes and continued lines
    prog=nocomment(prog)                              # remove comments (and commented out includes)
    prog=changeall(prog, Tab, Space)               # replace tabs with spaces
    prog=changeall(prog, Mline+Space, Mline) # cleanup continued lines                      
    prog=prog.replace(Mline+Crlf, "")                # fuse continued lines                      
    prog=substitute_includes(sv, prog)              # substitute includes (also applies the previous changes to each include)

    # cleanup format
    prog=remove_accented(prog)                                # convert accented characters 
    prog=prog.replace(Lf,'')                                          # remove line feeds (leave only carriage returns)
    prog.strip(Space)                                                    # remove leading spaces
    prog=changeall(prog, Space+Crlf,Crlf)                   # remove trailing spaces in lines
    prog=changeall(prog, Crlf+Space,Crlf)                   # remove leading spaces in lines
    prog=allowed_chars(prog)                                      # remove special characters v2.603
    lines=[l for l in prog.split(Crlf) if l!="" and l!=Space] # remove empty lines
    prog=Crlf.join(lines)+Crlf                                         # rebuild prog

    # check number of quotes  
    for lig in lines:
        if not checkbalance(lig, Quote, Quote):
            print("\n", Err_unbalanced_quotes)              # Fatal error: unbalanced quotes
            print(lig)
            raise ReferenceError

    prog=savestrings(sv, prog)   # replace strings with a key for protection (keywords inside strings must not be parsed)

    # check number of brackets   
    for lig in prog.split(Crlf):
        if not checkbalance(lig, Obr, Cbr):
            print("\n", Err_unbalanced_brackets)              # Fatal error: unbalanced brackets
            print(lig)
            raise ReferenceError
        
    # check that there is a program    
    prog=changeall(prog, Space+Space, Space)           # remove multiple spaces (outside strings)
    if len(prog.replace(Tab,'').replace(Space,'').replace(Crlf,''))<2: 
        print("\n", Err_empty_prog)                                # Fatal error: program script is empty                                  
        raise ReferenceError

    return prog

#===================================================== substitute_includes  
def substitute_includes(sv, prog):           
    """
    insert file content to replace include line. Following syntaxes are allowed:
    include(my_module.txt)        include("my_module.txt")
    include my_module.txt        include "my_module.txt"
    returns full text
    """  
    prog=changeall(prog, Include+Space+Obr, Include+Obr)  # remove extra spaces
    done=False
    while Include in prog and not done:
        done=True
        for osep,csep in [(Obr, Cbr),(Space, Crlf)]:      # look for includes
            while Include+osep in prog:
                done=False
                here=prog.find(Include+osep) 
                there=prog.find(csep, here+1)
                if there==-1:                                           # no closing separator
                    print("\n", Err_syntax)                         # Fatal error: no ending separator                                   
                    raise ReferenceError
                
                eol=prog.find(Crlf, here+1)                    # find end of line
                if eol==-1: eol=len(prog)+1
                line=prog[here:eol]                                # line containing the include
                txt=line.strip(Space)+Crlf                       # check length 
                if osep==Obr and here+len(txt)-2!=there:                 
                        print("\n", Err_syntax_extra_chars) # Fatal error: illegal characters at end of line                                   
                        print(line)
                        raise ReferenceError

                name=txt[len(Include+osep):-len(csep)]        # remove separators
                if csep!=Crlf: name=name[:-1]
                name=noquotes(name.strip(Space))              # file name
                name=addparentdir(name)                            # add path
                changeall(name, Space+Space, Space)          # remove multiple spaces
                newlines=""
                try:
                    newlines=io.gettextfile(name)+Crlf           # read include file using whand_io module

                except IOError:
                    print(Err_404)                                            # Fatal error: File not found
                    print(str([name])[1:-1])                             # display all chars
                    raise ReferenceError
                
                prog=nocomment(prog.replace(line, newlines))   # remove comments (and commented out includes)
                prog=changeall(prog, Tab, Space)               # replace tabs with spaces
                prog=changeall(prog, Mline+Space, Mline) # cleanup continued lines                      
                prog=prog.replace(Mline+Crlf, Space)         # fuse continued lines                   
    return prog
    
#===================================================== canonic
def canonic(sv, prog): 
    """
    reshape program into canonic form. 
    uses functions from whand_tool module
    returns full text
    """
    verbose=('cnn' in Debog)

    # separate words by adding spaces
    prog=prog.replace(Crlf+When, Crlf+Space+When)        # separate when from previous Crlf
    prog=prog.replace(Col+When, Col+Space+When)         # separate when from previous column
    prog=prog.replace(When+Obr, When+Space+Obr)       # separate when from subsequent bracket
    prog=prog.replace(Cbr+When, Cbr+Space+When)        # separate when from previous bracket

    # replace synonyms
    for old, new in Alphachangelist:                                      
        prog=alphachange(prog, old, new)                             # function from whand_tools module
 
    # separate lines at when and until
    prog=prog.replace(Crlf+Until, Crlf+Space+Until)           # separate until from previous Crlf
    prog=prog.replace(Col+Until, Col+Space+Until)           # separate until from previous column
    prog=prog.replace(Until+Obr, Until+Space+Obr)         # separate until from subsequent bracket
    prog=prog.replace(Cbr+Until, Cbr+Space+Until)           # separate until from previous bracket
    prog=prog.replace(Space+When+Space, Crlf+When+Space)   # cut before when 
    prog=prog.replace(Space+Until+Space, Crlf+Until+Space)       # cut before until 
    prog=changeall(prog, Space+Crlf, Crlf)                         # remove trailing spaces
    prog=changeall(prog, Crlf+Crlf, Crlf)                             # remove empty lines
    prog=prog.strip(Crlf)                                                     # remove empty first or last line

    # fill in implicit elements in lines
    lines=prog.split(Crlf)                                                          # cut lines
    for num, lig in enumerate(lines):       
        # process definitions
        if not lig.startswith(When+Space) and  not lig.startswith(Until+Space):  # any line without when or until starts a new definition
            lines[num]=Definition+lines[num]                            # mark definition
            if lines[num][-1]==Col:
                lines[num]=lines[num][:-1]                                    # remove column at end (before when)
            while lines[num][-1]==Space:
                lines[num]=lines[num][:-1]                                    # remove trailing spaces
                
        # fill in values for until and when
        if lig.startswith(Until+Space):
            lines[num]=lines[num].replace(Until,When)            # until with value is equivalent to when
            if  not Col in lig:
                lines[num]=lines[num]+Col+Faux                       # fill in default value 'false'        
        if lig.startswith(When+Space) and not Col in lig:                         
                lines[num]=lines[num]+Col+Vrai                        # fill in default value 'true'  
    text= Crlf.join(lines)                                                         # join lines again
    
    # cut at columns, but keep columns. These columns precede values.
    text=text+Crlf                                                                 # add empty line at end
    text=text.replace(Col, Crlf+Col)                                      # cut at column
    text=changeall(text, Crlf+Col+Space, Crlf+Col)              # remove leading spaces
    text=changeall(text, Crlf+Col+Crlf, Crlf+Col+Vrai+Crlf) # fill in isolated columns
    text=text[:-len(Crlf)]                                                        # remove emptly line at end
    
    # fill in conditions
    bad=""
    lines=text.split(Crlf)
    count=-1                                                                      # this is a check for both conditions and values
    for num, lig in enumerate(lines):
        if lig.startswith(Definition):                                         # starts a new definition                                   
            count=0                                                               # zero check
            nam=lig[len(Definition):]                                     # get object name 
        else:
            count+=1                                                             # count lines
            if count==1 and not lig.startswith(When):               # a value without when condition
                li=lines[num]                                                    # look for a 'change' value
                obj=""                                                                                                                                   
                if li.startswith(Col+Change+Space) \
                    or li.startswith(Col+Change+Obr):
                                obj=li[len(Col+Change):]                # get object name                                                                                 
                                
                if obj:                                                                                                                                    
                    lines[num]=When+Space+Change+obj+Crlf+Col+Vrai+Crlf       # fill in 'true' (no begin for change)                            
                    lines[num]+=When+Space+nam \
                                 +Plus+Epsilon+Div+"4"+Crlf+Col+Faux            # create an end condition delayed by epsilon/4
                    
                else:                                                                 # it is not a 'change' value
                    lines[num]=When+Space+Start+Crlf+li+Crlf    # fill in 'start' condition
                    lines[num]+=When+Space+Change+Obr+li[1:]+Cbr+Crlf+li       # fill in 'change' condition
                lines[num-1]=Definition+Equal+Special+lines[num-1][len(Definition):]    # tag equivalent with special definition mark    
##                print("xxxx equivalent", lines[num-1], li)
                
    # update line structure
    text= Crlf.join(lines)                                                     # join, then split again to create extra lines
    lines=text.split(Crlf)
    
    # finish filling in and check structure
    count=-1
    for num, lig in enumerate(lines):
        if verbose: print("->",[count], lig)
        if lig.startswith(Definition):                                         # it is a definition
            if count==0:                                                        # complete empty definitions with 'when start: true'
                    lines[num]=When+Space+Start+Crlf+Col+Vrai+Crlf+lines[num]
                    if verbose: print("+++",[count], lines[num])
            count=0
            if lig==Definition:                                               # value without condition or name
                bad+=str([num+2])+Space+lines[num+2]+Crlf
        else:                                                                       # it is a condition or value
            count+=1                                                           # parity check                                                      
            if count==0:
                bad+=str([num+1])+Space+lig+Crlf             # missing name
            elif count>0:
                if count%2==0 and lig.startswith(When):          # condition instead of value
                    bad+=str([num+1])+Space+lig+Crlf
                if count%2==1 and not lig.startswith(When):    # value without condition
                    bad+=str([num+1])+Space+lig+Crlf
                   
    # update line structure
    text= Crlf.join(lines)                                                     # join, then split again to create extra lines
    lines=text.split(Crlf)
    if lines[-1].startswith(Definition):                                    # complete empty definitions on last line
            lines[-1]=lines[-1]+Crlf+When+Space+Start+Crlf+Col+Vrai

    if bad:                                             # anomaly in condition/value structure
        print(Err_missing_name)             # syntax error: missing name or too many values (fatal error)
        print(bad)
        raise ReferenceError

    # update line structure and remove temporary codes
    text= Crlf.join(lines)
    text=text.replace(Definition,"")        # does not remove equivalence codes

    if verbose: print("\nCanonic:\n"+text)    # strings still under protected form
    return text

#===================================================== adjust_names
def adjust_names(sv, text): 
    """
    replace spaces in names with brackets
    cleanup spaces, restore strings
    returns modified text
    """
    verbose=('adn' in Debog)
    lines=text.split(Crlf)                                                                  # work line-by-line
    for num, lig in enumerate(lines):
        if not lig.startswith(When) and not lig.startswith(Col):        # look for names                   
            lig=lig.strip(Space)                                                          # remove leading and trailing spaces
            if Space in lig:                                                                  # only if spaces
                lig=changeall(lig,Space+Obr, Obr)                              # remove spaces before open brackets
                lig=changeall(lig,Cbr+Space, Cbr)                               # remove spaces after close brackets 
                lig=changeall(lig,Obr+Space, Obr)                              # remove spaces after open brackets  
                lig=changeall(lig,Space+Cbr, Cbr)                               # remove spaces before close brackets  
                lig=changeall(lig,Space+Comma, Comma)                 # remove spaces before comma  
                lig=changeall(lig,Comma+Space, Comma)                 # remove spaces after comma  

##                if Obr+Any+Space in lig:                                            
##                    lig=lig.replace(Obr+Any+Space, Obr)                      # changes func(any x,y)  into  §any§func(x,y)
##                    lig=Special+Any+Special+lig

                nbspaces=0
                while Space in lig:                                                        # change Spaces into brackets
                    nbspaces+=1
                    here=findlast(lig, Space)                                         # start replacing from the right
                    
##                    there=lig.find(Comma, here+1)                 # some ambiguities cannot be properly solved (e.g. show count X, count Y)
##                    if there==-1:                                              # stopping at next comma is not a good solution
##                        lig=lig[:here]+Obr+lig[here+1:]+Cbr    # enclose in brackets everything that follows the last space
##                    else:
##                        lig=lig[:here]+Obr+lig[here+1:there]+Cbr+lig[there:]    # enclose in brackets only up to comma
                    
                    lig=lig[:here]+Obr+lig[here+1:]+Cbr                      # enclose in brackets everything that follows the last space
                if nbspaces>1:                                                             # final structure may not be what was intended (e.g lists)
                    warn("*** Warning: multiple spaces. Brackets may help disambiguate ***\n" \
                    +"      "+lig+Crlf)      

            # restore strings            
            while Special+Chain in lig:
                code=""
                there=-1
                here=lig.find(Special+Chain)                                   # look for first delimiter
                there=lig.find(Special, here+1)                                # look for second delimiter
                if there>-1:
                    code=lig[here+len(Special+Chain):there]            # extract text  
                    code=Chain+code
                    lig=lig[:here]+Quote+sv.Strings[code]+Quote+lig[there+1:]
                else:
                    print(Anom_string_key)                # *** String anomaly ***
                    raise ReferenceError
                
            lines[num]=lig                                                                  # store modified line

    text= Crlf.join(lines)
##    print("xxxx precompile text", text)
    return text

#===================================================== nocomment
def allowed_chars(prog):
    """
    remove non printable characters v2.603
    """
    ascii_range=string.printable
    text=""
    for c in prog:
        if c in ascii_range: text+=c
    return text

#===================================================== nocomment
def nocomment(prog):
    """
    remove comments using regular expressions
    """
    mask=re.compile("#.*")                                                             # from # to end of line                           
    comments=mask.findall(prog)                                                  # find comments
    return mask.sub("",prog)

#===================================================== alphachange
def alphachange(prog, old, new):
    """
    change an alphabetic keyword into a synonym
    Symb=separators that may be contiguous to names
    [Plus, Minus, Mult, Div, Equal, Nequal, Greater, Smaller, Col, Obr, Cbr, Crlf, Space, Tabul, Tab, Mline, Comma]
    Space is also allowed as a separator
    """
    pr=Space+prog+Space                                                             # add spaces around prog                         
    for osep in Symb+[Space]:
        for csep in Symb+[Space]:           
            pr=pr.replace(osep+old+csep, osep+new+csep)             # substitute
    return pr[1:-1]                                                                           # remove spaces around prog                                               

#===================================================== checkbalance
def checkbalance(line, oop, cop):
    """
    verify balance of opening (oop) and closing (cop) operators in a line
    e.g. number of quotes and brackets
    """
    ocount=0                                                                                 # number of opening operators
    ccount=0                                                                                 # number of closing operators
    for c in line:
        if c==oop: ocount+=1
        if c==cop: ccount+=1
    if oop==cop:                                                                           # same operator: check parity 
        if ocount%2!=0: return False         
    elif ocount!=ccount: return False
    return True

#===================================================== savestrings
def savestrings(sv, prog): 
    """
    replace and store strings in sv.Strings dictionary
    because keywords inside strings must not be parsed
    returns full text
    """
    count=0                                                                 # number of strings
    while Quote in prog:
        here=prog.find(Quote)                                       # find opening quote
        there=prog.find(Quote, here+1)                        # find next quote (closing quote)
        if there<0:
            print(Err_unfinished_string)                            # Fatal error: End of File while parsing string                                 
            print(prog[here+1:])                                       # should not occur if quotes are balanced 
            raise ReferenceError
        count+=1
        code=Chain+str(count)                                       # storage key, e.g.  §Chain3§
        sv.Strings[code]=prog[here+1:there]                  # save string in a dictionary
        prog=prog[:here]+Special+code+Special+prog[there+1:]  # replace with storage key
    return prog

#====================================================================== hideshowunused
def hideshowunused(sv, text):                      
    """
    develop lists into several lines for Hide, Show and Unused
    preserve text between quotes
    returns modified text
    """
    lines=text.split(Crlf)                                                        # work on a list of lines
    for root in [Hide, Show, Unused]:                       
        newlines=[]
        clau=When+Space+Start+Crlf+Col+Vrai    # 'when start: true'
        for l, lig in enumerate(lines):                                    
            if lig.startswith(root+Obr) and lig[-len(Cbr):]==Cbr:              # requires form 'root(...)'
                block=lig[len(root+Obr):-len(Cbr)]                                  
                elts=splitlist(block, quotes=True)                     # look for commas outside brackets and split into a list 
                for i, e in enumerate(elts):                                 # repeat for each element of list
                    newlines+=[root+Obr+e+Cbr]                      # create name 'root(...)'
                    if i<len(elts)-1:                                               # last clause already exists
                        newlines+=[clau]                                       # create clause
            else:
                newlines+=[lig]                                                 # store new line
        lines=list(newlines)
    text= Crlf.join(lines)
    return text

#====================================================================== precompile
def precompile(sv, prog):
    """
    Precompile Whand script:
    cleanup, develop abbreviated syntax
    and convert to canonic form 'name: when condition: value'
    returns full text (no actual parsing)
    """
    verbose=('prc' in Debog)

    # prepare text
    if verbose: print("\nPreparing text.")
    piece=prepare(sv, prog)
    
    # canonic form
    if verbose: print("\nArranging canonic form..")
    can=canonic(sv, piece)
   
    # replace spaces with brackets
    if verbose: print("\nAdjusting names..")
    text=adjust_names(sv, can)

    # separate arguments for hide, show and unused 
    text=hideshowunused(sv, text)           
    return text
        
###===================================================== main
if __name__== "__main__":
    sv=sp.spell()
    try:
        old=open("..\scripts\essai.txt","r")   # try precompiling a script and print result            
 #       old=open("..\scripts\essai.txt","r", encoding="ascii", errors="surrogateescape")   # try precompiling a script and print result            
        tout=old.read()+Crlf                         
        old.close()
        prog=precompile(sv, tout)
        print(prog)
        print(Crlf+"============================================"+Crlf)
        
        prog=prog.replace(Crlf+When, Crlf+"    "+When)
        prog=prog.replace(Crlf+Col, Col+Space)
##        prog=prog.replace(Special+Any+Special, "function ")  # additional information in result
        prog=prog.replace(Equal+Special, "synonym ")            # additional information in result
        print(prog)

    except ReferenceError:
        print("\n---  PROCESS ABORTED  ---")
        print(Crlf+"============================================"+Crlf)

    
