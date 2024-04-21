# -*- coding: ISO-8859-1 -*-
"""
Whand language: Alain Marchand V1 of dec 2012-2015 ; V2 of 2016.
This is the language module. Can be translated if needed
Keywords are defined to prevent misspelling
and to allow change in syntax if needed
"""
# Reserved character and special codes
Special=chr(96)   # inverted single quote
Accented={'é':'e', 'è':'e', 'ê':'e', 'à':'a', 'ù':'u', 'ü':'u', 'ï':'i', 'î':'i', 'ô':'o', 'ç':'c'}
Definition=Special+"Name"+Special
Chain="Chain"
Bloc="Bloc"
Garde="Keep"

# global constants  (with Capital in name)
When, Or_when, Until, Or_until, And, Or, Find, Listfind, Isin, Within, Is, Isnot, Plus, Minus, Mult, Div, Equal, Nequal, Greater, Smaller, Grequal, Smequal, \
                      Order, Sequence, Col, Obr, Cbr, Crlf, Lf, Space, Tabul, Underscore, Tab, Mline, Comma, Quote, Dot, Prime, Hash\
          =  "when", "or when", "until", "or until", "and", "or", "find", "listfind", "isin", "within", "is", "isnot", "+", "-", "*", "/", "=", "!=", ">", "<", \
                       ">=", "<=", "order", "sequence", ":", "(", ")","\n", "\r", " ", "    ", "_", "\t", chr(92), ",",'"',".", "'", "#" 
Vrai, Faux, Always, Epsilon, Empty, Add, Value, Name, Pin, Key, Output, Display, Touch, Dialog, Start, Exit, \
                  Cumul, Steps, Sqrt, Intg, Absv, Load, Store, Image, Have, Pointer, Text, Call, Close, Print, Screen, Be, Novalue \
        ="true","false", Special+"always", "epsilon", "empty", "add", "value", "name", "pin", "key", "output", \
                "display", "touch", "dialog", "start", "exit", "cumul", "steps", "sqrt", "intg", "absv", "load", "store", \
                 "image", "have", "pointer", "text", "call", "close", "print", "screen", "be", "novalue"
Not, Any, All, Next, Pick, Begin, End, To, Inter, Change, Lastchange, Count, Since, Lasted, Occur, \
     Ramp, Sort, Proba, Old, Measure, Command, Read, Write, Match, Hasvalue, Controlpanel \
         ="not", "any", "all", "next", "pick", "begin", "end", "to", "inter", "change", "lastchange", "count", "since", "lasted", "occur", \
         "ramp", "sort", "proba", "old", "measure", "command", "read", "write", "match", "hasvalue", "controlpanel"
Logd, Powr, Shuffle, Alea, Itis, Ewent, Number, Time, Delay, State, List, Tell, Blind, Show, Include, Unused, Testerror \
        = "logd", "powr", "shuffle", "alea", "itis", "event", "number", "time", "delay", "state", "list", \
            "tell", "blind", "show", "include", "unused", "testerror"                                        
Wday=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]         
Month=["january", "february", "march", "april", "may", "june", "july", \
             "august","september", "october", "november", "december"]         
Mndays=[31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]         

Time_is, Day_is, Date_is, Week_is="time is", "day is", "date is", "week is"  
Is_in="is in"                                             
Is_not="is not"
It_is="it is"
Starttree=(Start, None, None)
Begintrue=Begin+Obr+Vrai+Cbr
Store_screen=Store+Obr+Screen+Cbr
WFalse=When+Space+Faux+Col
IsEmpty="is "+Empty
MatchEmpty=Match+Space+Empty

# Synonyms
Alphachangelist=[(Is_in, Isin),(Is_not, Isnot),(It_is, Itis), (Or_when, When), (Or_until, Until) \
                 , (Print, Store_screen), (Be, WFalse), (IsEmpty, MatchEmpty)]  

# operator categories
Selectors=[All, Any, Next]
Internal_Functions = [Begin, End, Change, Lasted, Inter, Count, Occur, Ramp, Proba, Hasvalue, \
                      Not, Pin, Key, Measure, Read, Touch, Name, Logd, Shuffle, Alea, Cumul, Steps, Order, Sequence, \
                      Sqrt, Intg, Absv, Load, Image, Have, Old, Pointer, Text,Tell, Itis, Time, Call, Value, Novalue]  
Comparators = [Within, Is, Isnot, Isin, Nequal, Grequal, Smequal, Equal, Greater, Smaller, Match, Since]
Operators = [Plus, Minus, Mult, Div,  Add, Powr, Find, Listfind, To, Pick, Sort]                                    
Basic_operators=Comparators+[And, Or, Not, Comma, Vrai, Faux]+Operators
##Effective=[Exit, Call, Output, Command, Write, Store, Display, Dialog, Print]
Outputs=[Output, Write, Store, Command]

Fixed=[Vrai, Faux, Epsilon, Empty]          # internally defined
Glitch_list=[Begin, End, Change]

Alphakwords = [Add, And, Find, Listfind, Is, Isnot, Isin, Match, Or, Pick, \
                           Powr, Show, Since, Sort, Order, Sequence, To, Until, Unused, When, Within] \
                          +Fixed+Selectors+Internal_Functions                       # must be separated from names 

Symb=set([Plus, Minus, Mult, Div, Equal, Nequal, Greater, Smaller, \
                     Col, Obr, Cbr, Crlf, Space, Tabul, Tab, Mline, Comma, Space])   # may be stuck to names 

# operator characteristics
Binary=set(Comparators+Operators+[And, Or])
Unary=set(Selectors+Internal_Functions+[Obr])
Priority_groups = [[Or, And], Comparators, [Comma], [Add, Find, Listfind, To, Pick, Sort], \
                   [Plus, Minus], [Mult, Div], [Powr], [All, Any], \
                   Internal_Functions, [Next]]

# convert to set for faster search
Internal_Functions = set(Internal_Functions)
Comparators = set(Comparators)
Operators = set(Operators)                                    
Basic_operators=set(Basic_operators)

# Functions whose result may vary without explicit cause
# not to be used in conditions or expressions
Stochastic={Next, Proba, Shuffle, Alea, Tell}               

# TIME UNITS
Unit_sec= "s" 
Unit_hour= "h"
Unit_week= "wk"
Unit_ms= "ms"
Unit_min1= "mn"
Unit_min2= "min"
Unit_day= "day"
Time_unit_list=[Unit_ms, Unit_sec, Unit_min1, Unit_min2, Unit_hour, Unit_day, Unit_week]   # beware of ms/s order for correct parsing  
Time_unit_duration= {Unit_ms: 0.001, Unit_sec: 1, Unit_min1: 60, Unit_min2: 60,
                     Unit_hour: 3600, Unit_day: 24*3600, Unit_week: 7*24*3600}

# Natures (Booleans are events, new nature Stt created for states in V2)
Nmbr, Drtn, Bln, Stt, Lst = ["nmbr"], ["drtn"], ["bln"], ["stt"], ["lst"]
All_natures=Nmbr+ Drtn+ Bln+ Stt+ Lst

Allowed={}              #    {(nature1, attribute1, nature2, attribute2, nature_result, attribute_result)}
Allowed[Plus]=[(Bln, Value, Drtn, Value, Bln)]                 # delayed instant stored in Value until true moved here v1_61
Allowed[Plus]+=[(Nmbr, Value, Nmbr, Value, Nmbr)]      # math operators  
for op in [Minus, Mult, Div, Powr]:                                             # modif 
    Allowed[op]=[(Nmbr, Value, Nmbr, Value, Nmbr)]       # math operators
for op in [Minus, Plus]:                                                                    # duration operators
    Allowed[op]+=[(Drtn, Value, Drtn, Value, Drtn)]
for op in [Mult, Div]:                                                                        # duration operators
    Allowed[op]+=[(Drtn, Value, Nmbr, Value, Drtn)]         # scale durations
for op in [And, Or]:
    Allowed[op]=[(Bln, Value, Bln, Value, Bln)]                 # Boolean operators
for op in [Order, Sequence]:
    Allowed[op]=[(Lst, Value, [], None, Bln)]                    # Instant operators 
for op in [Nequal, Grequal, Smequal, Equal, Greater, Smaller]:    
    Allowed[op]=[(Nmbr, Value, Nmbr, Value, Bln)]          # math comparators
    Allowed[op]+=[(Drtn, Value, Drtn, Value, Bln)]          # duration comparators
for op in [Nequal, Equal]:    
    Allowed[op]+=[(Bln, Value, Bln, Value, Bln)]                # compare truth value of Bln
    Allowed[op]+=[(Stt, Value, Stt, Value, Bln)]                  # state comparators
    
Allowed[Not]=[(Bln, Value, [], None, Bln)]                           # negate Boolean

Allowed[Special] = [(Lst, Value, All_natures, Value, All_natures)]  # subscripting a list 

Allowed[Find]  =[(Lst, Value, Bln, Value, Nmbr)]                  # search list for a Boolean   
Allowed[Find]+=[(Lst, Value, Nmbr, Value, Nmbr)]             # search list for a number
Allowed[Find]+=[(Lst, Value, Drtn, Value, Nmbr)]                # search list for a duration
Allowed[Find]+=[(Lst, Value, Stt, Value, Nmbr)]                   # search list for a state

Allowed[Listfind]=[(Lst, Value, Lst, Value, Nmbr)]               # search list for a list

Allowed[Isin] =[(Nmbr, Value, Lst, Value, Bln)]                   # search list for a number 
Allowed[Isin]+=[(Bln, Value, Lst, Value, Bln)]                       # search list for a Boolean
Allowed[Isin]+=[(Drtn, Value, Lst, Value, Bln)]                     # search list for a duration
Allowed[Isin]+=[(Stt, Value, Lst, Value, Bln)]                        # search list for a state   
# Allowed[Isin]+=[(Stt, Value, Stt, Value, Bln)]                    # search string for a state (not yet implemented)

Allowed[Count]=[(Lst, Value, [], None, Nmbr)]                    # count objects in lists
Allowed[Count]+=[(Bln, Count, [], None, Nmbr)]                 # count occurrences of a Boolean
Allowed[Proba]=[(Nmbr, Value, [], None, Bln)]                   # returns a Boolean with specified probability
Allowed[Since]=[(Drtn, Value, Bln, Value, Bln)]                   
Allowed[Lasted]=[(Bln, Value, [], None, Drtn)]                     
Allowed[Inter]=[(Bln, Occur, [], None, Drtn)]                        

for op in [Name]:
    Allowed[op]=[(All_natures, op, [], None, Stt)]                            # name as a string
for op in [Begin, End]:
    Allowed[op]=[(Bln, Value, [], None, Bln)]                                         
#    Allowed[op]+=[(Lst, Value, [], None, Lst)]                              # forbidden: use 'any' instead
for op in [Change]:                                                                
    Allowed[op]=[(All_natures, Lastchange, [], None, Bln)]             # any nature of variable        
    
for op in [Is, Isnot]:
##    Allowed[op]=[(Bln, Value, Bln, Value, Bln)]                            # use Equal instead                     
    Allowed[op]=[(Nmbr, Value, Nmbr, Value, Bln)]               
    Allowed[op]+=[(Drtn, Value, Drtn, Value, Bln)]                    
    Allowed[op]+=[(Stt, Value, Stt, Value, Bln)]                    
    
for op in [Match]:                                                                          
    Allowed[op]=[(Lst, Value, Lst, Value, Bln)]                       

for op in [Occur]:
    Allowed[op]=[(Bln, op, [], None, Lst)]                                       
    Allowed[op]+=[(Lst, op, [], None, Stt)]                      # trick to prevent distributivity (use 'any' instead)                 

for op in [Pick, Sort]:                                                                            
    Allowed[op]=[(Lst, Value, Lst, Value, Lst)]                                      

for op in [Cumul, Steps]:
    Allowed[op]=[(Nmbr, Value, [], None, Lst)]                    # implemented as elemental, through distributivity
    Allowed[op]+=[(Drtn, Value, [], None, Lst)]                    # implemented as elemental, through distributivity
#    Allowed[op]+=[(Stt, Value, [], None, Lst)]                     # concatenation/split, to be implemented
    
for op in [Add]:                                                                            # works with all natures                                                                                        
    Allowed[op]  =[(Lst, Value, Lst, Value, Lst)]                       
    Allowed[op]+=[(Lst, Value, Nmbr, Value, Lst)]                       
    Allowed[op]+=[(Lst, Value, Drtn, Value, Lst)]                       
    Allowed[op]+=[(Lst, Value, Bln, Value, Lst)]                                          
    Allowed[op]+=[(Lst, Value, Stt, Value, Lst)]                                          
    Allowed[op]+=[(Nmbr, Value, Lst, Value, Lst)]                     
    Allowed[op]+=[(Drtn, Value, Lst, Value, Lst)]                     
    Allowed[op]+=[(Bln, Value, Lst, Value, Lst)]                                      
    Allowed[op]+=[(Stt, Value, Lst, Value, Lst)]                                      
    
for op in [Any, All]:
    Allowed[op]=[(Lst, Value, [], None, Bln)]                                    # list to Boolean   
Allowed[Within]=[(Lst, Value, Lst, Value, Bln)]

Allowed[Next]=[(Lst, Value, [], None, All_natures)]                       # list (does not specify nature of result)

Allowed[Hasvalue]=[(All_natures, Value,  [], None, Bln)]             # detects that value is not None

Allowed[To]=[(Bln, Occur, Bln, Occur, Drtn)]                         # difference of instants is duration 
Allowed[Mult]+=[(Nmbr, Value, Drtn, Value, Drtn)]              # multiply durations
Allowed[Div]+=[(Drtn, Value, Drtn, Value, Nmbr)]                # divide durations
Allowed[Sqrt]=[(Nmbr, Value, [], None, Nmbr)]                    # square root of number
Allowed[Logd]=[(Nmbr, Value, [], None, Nmbr)]                   # decimal log of number  
Allowed[Intg]=[(Nmbr, Value, [], None, Nmbr)]                     # integer of number
Allowed[Absv]=[(Nmbr, Value, [], None, Nmbr)]                   # absolute value of number
Allowed[Ramp]=[(Nmbr, Value, [], None, Lst)]                   # list of consecutive integers, starting with 1
Allowed[Alea]=[(Nmbr, Value, [], None, Lst)]                     # list of random float values from 0 to less than 1  
Allowed[Measure]=[(Nmbr, Value, [], None, Nmbr)]          # analog input on demand  
Allowed[Read]=[(Nmbr, Value, [], None, Stt)]                   # text input on demand  
Allowed[Touch]=[(Lst, Value, [], None, Lst)]                      # touchscreen input on demand  
Allowed[Load]=[(Stt, Value, [], None, Lst)]                       # takes a filename, gives a list      
Allowed[Have]=[(Lst, Value, [], None, Lst)]                       # returns list of objects with given attribute     
Allowed[Old]=[(Nmbr, Value, [], None, Nmbr)]             # keeps old value    
Allowed[Old]+=[(Drtn, Value, [], None, Drtn)]               # keeps old value    
Allowed[Old]+=[(Stt, Value, [], None, Stt)]                     # keeps old value    
Allowed[Old]+=[(Lst, Value, [], None, Lst)]                    # keeps old value 
Allowed[Old]+=[(Bln, All, [], None, Bln)]                         # keeps old value 
Allowed[Value]=[(Nmbr, Value, [], None, Nmbr)]              # gets value    
Allowed[Value]+=[(Drtn, Value, [], None, Drtn)]                # gets value 
Allowed[Value]+=[(Stt, Value, [], None, Stt)]                     # gets value     
Allowed[Value]+=[(Lst, Value, [], None, Lst)]                     # gets value  
Allowed[Value]+=[(Bln, All, [], None, Bln)]                         # gets value 
Allowed[Text]=[(Nmbr, Value, [], None, Stt)]                     # converts value to text  
Allowed[Text]+=[(Bln, Value, [], None, Stt)]                       # converts value to text    
Allowed[Text]+=[(Stt, Value, [], None, Stt)]                        # converts value to text    
Allowed[Text]+=[(Drtn, Value, [], None, Stt)]                     # converts value to text    
Allowed[Text]+=[(Lst, Value, [], None, Stt)]                        # converts value to text    
Allowed[Pointer]=[(Lst, Pointer, [], None, Nmbr)]                            
Allowed[Shuffle]=[(Lst, Value, [], None, Lst)]                      # shuffle lists  
Allowed[Itis]=[(Drtn, Value, [], None, Bln)]                        # absolute time event   
Allowed[Itis]+=[(Nmbr, Value, [], None, Bln)]                     # absolute time event   
Allowed[Itis]+=[(Stt, Value, [], None, Bln)]                          # absolute time event   
Allowed[Time]=[(Bln, Value, [], None, Drtn)]                          # absolute time event   
Allowed[Tell]=[(All_natures, Value, [], None, All_natures)]
Allowed[Call]=[(All_natures, Value, [], None, All_natures)]       # external function   

Non_distributive1=[]                                                                         # list operators do not distribute 
Non_distributive2=[]                                                                         # differentiating left and right 
for op in list(Allowed.keys()):
    for nat1, a1, nat2, a2, natres in Allowed[op]:
        if (Lst[0] in nat1): Non_distributive1+=[op] 
        if (Lst[0] in nat2): Non_distributive2+=[op]
Non_distributive1+=[Load, Store, Print]                                        

# ERROR MESSAGES                
# tools
Anom_text_after_block="*** Anomaly: text found after block ***"
Err_invalid_nat="*** Syntax error: invalid nature for '"
Err_inconsistent_nat="*** Error in get_nature: inconsistent nature ***"
Err_unbalanced_brackets="*** Error: unbalanced brackets ***"
Err_unbalanced_quotes="*** Error: unbalanced quotes ***"
Anom_illegal_dict_val="*** Anomaly: illegal dict value ***"
# precompile
Anom_string_key="*** String anomaly ***"
Err_illegal_special="*** Illegal character in program: "+ Special +" ***"
Err_illegal_char="*** Illegal character in program ***"
Err_missing_name="*** Syntax error: missing name or too many values ***"
Err_empty_prog="*** Error: program script is empty ***"
Err_unfinished_string="*** Error: End of File encountered while parsing string ***"
Err_syntax="*** Syntax error ***"
Err_syntax_extra_chars="*** Syntax error: illegal characters at end of line ***"
Err_404="*** File not found ***"         # also in runtime
Warn_multiple_spaces="*** Warning: multiple spaces. Brackets may help disambiguate ***\n" \
# compile
Err_empty_name="*** Syntax error: empty name ***"
Help_continuation="--> you may have meant (with continuation character '"
Err_redef_internal_func="*** Error: You cannot define an internal function ***"
Err_text_after_args="*** Syntax error: text found after arguments ***"
Err_equal_in_name="*** Illegal character in name: "+ Equal +" ***"
Err_redef_name="*** Error: Node is already defined ***"
Err_missing_op="*** Syntax error: expecting operator ***"
Warn_switch_any_all="*** Warning: compiler made the following substitution ***"
Anom_no_args="*** Anomaly: cannot find function arguments ***"
Err_nb_args="*** Error: wrong number of arguments ***"
Err_missing_args="*** Error: missing argument ***"
Err_no_arg="*** Syntax error: function without arguments ***"
Err_accessory="*** Error: accessory variable is not part of a function definition ***"
Err_space_in_name="*** Syntax error: incorrect expression ***"
Err_op_syntax="*** Syntax error in operator ***"
Err_unknown_funct="*** Error: unknown function ***"
Anom_two_in_brackets="*** Anomaly: two objects in the same brackets ***"
Err_incomp_nat="*** Error: incompatible nature ***"
Err_conflict_nat="*** Error: nature conflict ***"
Err_unknown_object="*** Error: unknown object ***"
Anom_non_string_op="*** Anomaly: non string operator ***"
Err_not_allowed_cond="*** Syntax error: operator not allowed in a condition ***"
Err_not_allowed_expr="*** Syntax error: operator not allowed in an expression ***"
Warn_anom_clauses="*** Warning: anomaly detected in clauses of ***"
Warn_neverdef="*** Warning:  following term(s) are never defined ***"
Warn_never_applied="*** Warning: function is never applied ***"
Warn_typing_risk="*** Warning: risk of typing error ***"
# controlpanel
Label_global_start="     Global start    "
Label_global_fast="   SPEED  x "
Label_global_slow="     Global SLOW    "
Label_global_stop="     Global stop    "
Label_restart="    New session    "
Label_start="press Start when ready "
Label_pause_quit="   Pause/Quit   "
Label_resume="Resume"
Label_closed=" Ended "
Label_run="running "
Warn_pause="\n*** Program interrupted ***"
Warn_resume="***  Program resumed    ***"
Warn_noclose="\n*** Direct window closure is disabled. Use 'Global stop' button ***\n"
Err_key="*** Error: undefined node ***"
# runtime
Err_nb_recurse="*** Error: recursive evaluation count exceeded ***"
Anom_call_struct="*** Anomaly in call structure ***"
Anom_previous="*** Anomaly: previous value not available ***"
Anom="*** Anomaly ***   "
Anom_attrib="*** Anomaly: wrong attribute ***"
Anom_deep_get="*** Anomaly in deep_get: incorrect object ***"
Anom_offset="*** Anomaly in offset ***"
Anom_comput="*** Anomaly computing ***   "
Anom_logic="*** Anomaly in rt.op: not a Bln logic value ***   "
Anom_setv_logic="*** Anomaly in rt.setv: not a Bln logic value ***   "
Anom_setv_nat="*** Anomaly in rt.setv: unknown nature ***   "
Anom_find="*** Anomaly Find: non Bln in list"
Anom_isin="*** Anomaly Isin: non Bln in list"
Anom_bufstore="*** Anomaly in bufstore: not a list:"
Warn_circular="*** Warning: probable circular dependencies ***"
Warn_multi_update="*** Warning: multiple updating ***"
Warn_Heterogeneous="*** Warning: cannot work with heterogeneous lists ***"
Warn_empty_ramp="*** Warning: empty ramp ***"
Warn_null_index="*** Warning: null index in list ***   "
Warn_div_zero="*** Warning: divide by zero ***   "
Warn_sqrt_neg="*** Warning: sqrt of negative number ***   "
Warn_invalid_nb="*** Warning: invalid number ***   "
Warn_log_neg="*** Warning: log10 of null or negative number ***   "
Warn_compute_power="*** Warning: cannot compute power ***   "
Warn_empty_alea="*** Warning: empty alea ***   "
Warn_unstable="Unstable condition:"
Should_be_list="should be a list but is"
Err_arg_nat="*** Error: wrong argument nature ***   "
Err_ambig_op="*** Error: Operation is ambiguous ***   "
Err_imposs_oper="*** Error: impossible operation ***"
Err_no_open="*** Unable to open file ***   "
End_prog="*** End of program ***"        # also in controlpanel
Err_switch_operands="*** Syntax error: Please switch operands ***"
# initial
Err_ask_nature="*** Indeterminate nature: Please add a '"+Be+"' instruction \n     with "+Ewent+", "+Number+", "+Delay+", "+ State + " or "+ List + " to following objects ***"
Warn_no_exit="*** Warning: program without exit condition ***"
Warn_iterations="*** Warning: too many iterations, probable circular dependencies ***"
Warn_no_value_at_start="*** Warning:  following objects have no value at start ***"
# main
Err_unused_obj="*** Error in 'unused' declaration : object does not exist ***"
Err_unused_config="*** Configuration/Script mismatch: this i/o is declared as 'unused' ***"
Err_Val="\n*** Error in value *** "                         
Err_no_source="*** Error: source or configuration file not found ***"
Err_yoked="*** Error: invalid yoke master number ***"
Err_abort="\n---  PROCESS ABORTED  ---"
Press_enter="\n>> Press Enter to quit"
# io
Warn_empty_line="\n*** Warning: File contains empty lines ***"
Err_io_number="\n*** Error in input or output number ***"
Err_config="\n*** Configuration error ***"
Err_create="\n*** Unable to create"
Prompt_script_list="Select file containing script list (Ctrl-C to finish) ? "
Prompt_data_file="\nSelect file to output results ? "
Prompt_file_exist="File exists: overwrite (Y/N) ? "
Msg_continue="*** Continue ***\n"
Msg_end_box="*** Terminating box"
Msg_pause="\n***  Pause   ***"
Msg_runfile="\nUsing run file name:"

# predefined colors from tkinter
Tkinter_colors= ["alice blue", "AliceBlue", "antique white", "AntiqueWhite", \
"AntiqueWhite1", "AntiqueWhite2", "AntiqueWhite3", "AntiqueWhite4", \
"aquamarine", "aquamarine1", "aquamarine2", "aquamarine3", \
"aquamarine4", "azure", "azure1", "azure2", "azure3", "azure4", \
"beige", "bisque", "bisque1", "bisque2", "bisque3", "bisque4", \
"black", "blanched almond", "BlanchedAlmond", "blue", "blue violet", "blue1", \
"blue2", "blue3", "blue4", "BlueViolet", "brown", "brown1", "brown2", \
"brown3", "brown4", "burlywood", "burlywood1", "burlywood2", "burlywood3", \
"burlywood4", "cadet blue", "CadetBlue", "CadetBlue1", "CadetBlue2", \
"CadetBlue3", "CadetBlue4", "chartreuse", "chartreuse1", "chartreuse2", \
"chartreuse3", "chartreuse4", "chocolate", "chocolate1", "chocolate2", \
"chocolate3", "chocolate4", "coral", "coral1", "coral2", \
 "coral3", "coral4", "cornflower blue", "CornflowerBlue", "cornsilk", \
 "cornsilk1", "cornsilk2", "cornsilk3", "cornsilk4", "cyan", \
 "cyan1", "cyan2", "cyan3", "cyan4", "dark blue", \
 "dark cyan", "dark goldenrod", "dark gray", "dark green", "dark grey", \
 "dark khaki", "dark magenta", "dark olive green", "dark orange", "dark orchid", \
 "dark red", "dark salmon", "dark sea green", "dark slate blue", "dark slate gray", \
 "dark slate grey", "dark turquoise", "dark violet", "DarkBlue", "DarkCyan", \
 "DarkGoldenrod", "DarkGoldenrod1", "DarkGoldenrod2", "DarkGoldenrod3", "DarkGoldenrod4", \
 "DarkGray", "DarkGreen", "DarkGrey", "DarkKhaki", "DarkMagenta", \
 "DarkOliveGreen", "DarkOliveGreen1", "DarkOliveGreen2", "DarkOliveGreen3", "DarkOliveGreen4", \
 "DarkOrange", "DarkOrange1", "DarkOrange2", "DarkOrange3", "DarkOrange4", \
 "DarkOrchid", "DarkOrchid1", "DarkOrchid2", "DarkOrchid3", "DarkOrchid4", \
 "DarkRed", "DarkSalmon", "DarkSeaGreen", "DarkSeaGreen1", "DarkSeaGreen2", \
 "DarkSeaGreen3", "DarkSeaGreen4", "DarkSlateBlue", "DarkSlateGray", "DarkSlateGray1", \
 "DarkSlateGray2", "DarkSlateGray3", "DarkSlateGray4", "DarkSlateGrey", "DarkTurquoise", \
 "DarkViolet", "deep pink", "deep sky blue", "DeepPink", "DeepPink1", \
 "DeepPink2", "DeepPink3", "DeepPink4", "DeepSkyBlue", "DeepSkyBlue1", \
 "DeepSkyBlue2", "DeepSkyBlue3", "DeepSkyBlue4", "dim gray", "dim grey", \
 "DimGray", "DimGrey", "dodger blue", "DodgerBlue", "DodgerBlue1", \
 "DodgerBlue2", "DodgerBlue3", "DodgerBlue4", "firebrick", "firebrick1", \
 "firebrick2", "firebrick3", "firebrick4", "floral white", "FloralWhite", \
 "forest green", "ForestGreen", "gainsboro", "ghost white", "GhostWhite", \
 "gold", "gold1", "gold2", "gold3", "gold4", \
 "goldenrod", "goldenrod1", "goldenrod2", "goldenrod3", "goldenrod4", \
 "gray", "gray0", "gray1", "gray10", "gray100", \
 "gray11", "gray12", "gray13", "gray14", "gray15", \
 "gray16", "gray17", "gray18", "gray19", "gray2", \
 "gray20", "gray21", "gray22", "gray23", "gray24", \
 "gray25", "gray26", "gray27", "gray28", "gray29", \
 "gray3", "gray30", "gray31", "gray32", "gray33", \
 "gray34", "gray35", "gray36", "gray37", "gray38", \
 "gray39", "gray4", "gray40", "gray41", "gray42", \
 "gray43", "gray44", "gray45", "gray46", "gray47", \
 "gray48", "gray49", "gray5", "gray50", "gray51", \
 "gray52", "gray53", "gray54", "gray55", "gray56", \
 "gray57", "gray58", "gray59", "gray6", "gray60", \
 "gray61", "gray62", "gray63", "gray64", "gray65", \
 "gray66", "gray67", "gray68", "gray69", "gray7", \
 "gray70", "gray71", "gray72", "gray73", "gray74", \
 "gray75", "gray76", "gray77", "gray78", "gray79", \
 "gray8", "gray80", "gray81", "gray82", "gray83", \
 "gray84", "gray85", "gray86", "gray87", "gray88", \
 "gray89", "gray9", "gray90", "gray91", "gray92", \
 "gray93", "gray94", "gray95", "gray96", "gray97", \
 "gray98", "gray99", "green", "green yellow", "green1", \
 "green2", "green3", "green4", "GreenYellow", "grey", \
 "grey0", "grey1", "grey10", "grey100", "grey11", \
 "grey12", "grey13", "grey14", "grey15", "grey16", \
 "grey17", "grey18", "grey19", "grey2", "grey20", \
 "grey21", "grey22", "grey23", "grey24", "grey25", \
 "grey26", "grey27", "grey28", "grey29", "grey3", \
 "grey30", "grey31", "grey32", "grey33", "grey34", \
 "grey35", "grey36", "grey37", "grey38", "grey39", \
 "grey4", "grey40", "grey41", "grey42", "grey43", \
 "grey44", "grey45", "grey46", "grey47", "grey48", \
 "grey49", "grey5", "grey50", "grey51", "grey52", \
 "grey53", "grey54", "grey55", "grey56", "grey57", \
 "grey58", "grey59", "grey6", "grey60", "grey61", \
 "grey62", "grey63", "grey64", "grey65", "grey66", \
 "grey67", "grey68", "grey69", "grey7", "grey70", \
 "grey71", "grey72", "grey73", "grey74", "grey75", \
 "grey76", "grey77", "grey78", "grey79", "grey8", \
 "grey80", "grey81", "grey82", "grey83", "grey84", \
 "grey85", "grey86", "grey87", "grey88", "grey89", \
 "grey9", "grey90", "grey91", "grey92", "grey93", \
 "grey94", "grey95", "grey96", "grey97", "grey98", \
 "grey99", "honeydew", "honeydew1", "honeydew2", "honeydew3", \
 "honeydew4", "hot pink", "HotPink", "HotPink1", "HotPink2", \
 "HotPink3", "HotPink4", "indian red", "IndianRed", "IndianRed1", \
 "IndianRed2", "IndianRed3", "IndianRed4", "ivory", "ivory1", \
 "ivory2", "ivory3", "ivory4", "khaki", "khaki1", \
 "khaki2", "khaki3", "khaki4", "lavender", "lavender blush", \
 "LavenderBlush", "LavenderBlush1", "LavenderBlush2", "LavenderBlush3", "LavenderBlush4", \
 "lawn green", "LawnGreen", "lemon chiffon", "LemonChiffon", "LemonChiffon1", \
 "LemonChiffon2", "LemonChiffon3", "LemonChiffon4", "light blue", "light coral", \
 "light cyan", "light goldenrod", "light goldenrod yellow", "light gray", "light green", \
 "light grey", "light pink", "light salmon", "light sea green", "light sky blue", \
 "light slate blue", "light slate gray", "light slate grey", "light steel blue", "light yellow", \
 "LightBlue", "LightBlue1", "LightBlue2", "LightBlue3", "LightBlue4", \
 "LightCoral", "LightCyan", "LightCyan1", "LightCyan2", "LightCyan3", \
 "LightCyan4", "LightGoldenrod", "LightGoldenrod1", "LightGoldenrod2", "LightGoldenrod3", \
 "LightGoldenrod4", "LightGoldenrodYellow", "LightGray", "LightGreen", "LightGrey", \
 "LightPink", "LightPink1", "LightPink2", "LightPink3", "LightPink4", \
 "LightSalmon", "LightSalmon1", "LightSalmon2", "LightSalmon3", "LightSalmon4", \
 "LightSeaGreen", "LightSkyBlue", "LightSkyBlue1", "LightSkyBlue2", "LightSkyBlue3", \
 "LightSkyBlue4", "LightSlateBlue", "LightSlateGray", "LightSlateGrey", "LightSteelBlue", \
 "LightSteelBlue1", "LightSteelBlue2", "LightSteelBlue3", "LightSteelBlue4", "LightYellow", \
 "LightYellow1", "LightYellow2", "LightYellow3", "LightYellow4", "lime green", \
 "LimeGreen", "linen", "magenta", "magenta1", "magenta2", \
 "magenta3", "magenta4", "maroon", "maroon1", "maroon2", \
 "maroon3", "maroon4", "medium aquamarine", "medium blue", "medium orchid", \
 "medium purple", "medium sea green", "medium slate blue", "medium spring green", "medium turquoise", \
 "medium violet red", "MediumAquamarine", "MediumBlue", "MediumOrchid", "MediumOrchid1", \
 "MediumOrchid2", "MediumOrchid3", "MediumOrchid4", "MediumPurple", "MediumPurple1", \
 "MediumPurple2", "MediumPurple3", "MediumPurple4", "MediumSeaGreen", "MediumSlateBlue", \
 "MediumSpringGreen", "MediumTurquoise", "MediumVioletRed", "midnight blue", "MidnightBlue", \
 "mint cream", "MintCream", "misty rose", "MistyRose", "MistyRose1", \
 "MistyRose2", "MistyRose3", "MistyRose4", "moccasin", "navajo white", \
 "NavajoWhite", "NavajoWhite1", "NavajoWhite2", "NavajoWhite3", "NavajoWhite4", \
 "navy", "navy blue", "NavyBlue", "old lace", "OldLace", \
 "olive drab", "OliveDrab", "OliveDrab1", "OliveDrab2", "OliveDrab3", \
 "OliveDrab4", "orange", "orange red", "orange1", "orange2", \
 "orange3", "orange4", "OrangeRed", "OrangeRed1", "OrangeRed2", \
 "OrangeRed3", "OrangeRed4", "orchid", "orchid1", "orchid2", \
 "orchid3", "orchid4", "pale goldenrod", "pale green", "pale turquoise", \
 "pale violet red", "PaleGoldenrod", "PaleGreen", "PaleGreen1", "PaleGreen2", \
 "PaleGreen3", "PaleGreen4", "PaleTurquoise", "PaleTurquoise1", "PaleTurquoise2", \
 "PaleTurquoise3", "PaleTurquoise4", "PaleVioletRed", "PaleVioletRed1", "PaleVioletRed2", \
 "PaleVioletRed3", "PaleVioletRed4", "papaya whip", "PapayaWhip", "peach puff", \
 "PeachPuff", "PeachPuff1", "PeachPuff2", "PeachPuff3", "PeachPuff4", \
 "peru", "pink", "pink1", "pink2", "pink3", \
 "pink4", "plum", "plum1", "plum2", "plum3", \
 "plum4", "powder blue", "PowderBlue", "purple", "purple1", \
 "purple2", "purple3", "purple4", "red", "red1", \
 "red2", "red3", "red4", "rosy brown", "RosyBrown", \
 "RosyBrown1", "RosyBrown2", "RosyBrown3", "RosyBrown4", "royal blue", \
 "RoyalBlue", "RoyalBlue1", "RoyalBlue2", "RoyalBlue3", "RoyalBlue4", \
 "saddle brown", "SaddleBrown", "salmon", "salmon1", "salmon2", \
 "salmon3", "salmon4", "sandy brown", "SandyBrown", "sea green", \
 "SeaGreen", "SeaGreen1", "SeaGreen2", "SeaGreen3", "SeaGreen4", \
 "seashell", "seashell1", "seashell2", "seashell3", "seashell4", \
 "sienna", "sienna1", "sienna2", "sienna3", "sienna4", \
 "sky blue", "SkyBlue", "SkyBlue1", "SkyBlue2", "SkyBlue3", \
 "SkyBlue4", "slate blue", "slate gray", "slate grey", "SlateBlue", \
 "SlateBlue1", "SlateBlue2", "SlateBlue3", "SlateBlue4", "SlateGray", \
 "SlateGray1", "SlateGray2", "SlateGray3", "SlateGray4", "SlateGrey", \
 "snow", "snow1", "snow2", "snow3", "snow4", \
 "spring green", "SpringGreen", "SpringGreen1", "SpringGreen2", "SpringGreen3", \
 "SpringGreen4", "steel blue", "SteelBlue", "SteelBlue1", "SteelBlue2", \
 "SteelBlue3", "SteelBlue4", "tan", "tan1", "tan2", \
 "tan3", "tan4", "thistle", "thistle1", "thistle2", \
 "thistle3", "thistle4", "tomato", "tomato1", "tomato2", \
 "tomato3", "tomato4", "turquoise", "turquoise1", "turquoise2", \
 "turquoise3", "turquoise4", "violet", "violet red", "VioletRed", \
 "VioletRed1", "VioletRed2", "VioletRed3", "VioletRed4", "wheat", \
 "wheat1", "wheat2", "wheat3", "wheat4", "white", \
 "white smoke", "WhiteSmoke", "yellow", "yellow green", "yellow1", \
 "yellow2", "yellow3", "yellow4", "YellowGreen"]


