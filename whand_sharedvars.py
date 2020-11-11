from whand_parameters import *                                             # options, constants
import whand_io as io                   # needed to clear interrupt buffer 

#===================================================== class spell
class spell:
    def __init__(self):
        # Debugging options
        self.Graphic=False
        self.Do_tests=False
        self.Begin_trace=0                                             # start time for debug

        self.Strings={}                       # strings are stored and their content is not parsed
        self.Blocks={}                        # parsing of blocks is delayed until bloc has been isolated
        self.Keep={}                          # to be preserved, not parsed (list elements)
        self.Object={}                       # all nodes except those created in getvalue
        self.Object_list=[]                 # list of nodes (except temporary), with order preserved
        self.Pinlist=[]                        # list of pin inputs
        self.Namedpinlist={}             # dic of pin input equivvalents 
        self.Pinstate={}                     # dict from name to input state
        self.Outlist=[]                       # list of declared outputs
        self.Boxnumber=0                # to run parallel scripts
        self.Nodestore=[]                 # a cyclic list of temporary nodes  
        self.Elements={}                   # a dict of dict elements 
        self.Nodebufsize=10            # pointer to temporary nodes. Arbitrary value, not clear how deep is needed ??? v340
        self.Visible=[]
        self.interface=None
        self.Indent=""
        self.Current_time=0
        self.Current_clause="", None, None       
        self.Eval_depth=0
        self.Buff={}
        self.Delayed_objects=[]                                 
        self.delayed_list=[]
        self.Active_list=[]                                          
        self.Idem_list=[]                                            
        self.Volatile=[]                    # list of objects that need to be always updated 
        self.Stochastic=[]                # list of objects that change value 
        self.Condition=[]                
        self.Condition_number={}   
        self.Glitches={}                   # dict of existing dependent glitches for immediate updating 
        self.Allow_dic={}                  
        self.Save_value={}               
        self.All_conditions={}
        self.slaveto=0                    # for yoked scripts
        self.masterto=[]                 # for yoked scripts
        self.Counter=0                   # development tool to improve performance
        self.t0=0                            # development tool: timing initialization 

    #=============================================
    def clear_all(self):
        self.Strings.clear()                       # strings are stored and their content is not parsed
        self.Blocks.clear()                        # parsing of blocks is delayed until bloc has been isolated
        self.Keep.clear()                          # to be preserved, not parsed (list elements)
        self.Object.clear()                       # all nodes except those created in getvalue
        self.Pinstate.clear()
        self.Elements.clear()                   # a dict of dict elements 
        self.Buff.clear()
        self.Namedpinlist.clear()             # dic of pin input equivvalents  
        self.Nodebufsize=10            # pointer to temporary nodes. Arbitrary value, not clear how deep is needed ??? 
        self.interface=None
        self.Indent=""
        self.Current_time=0
        self.Current_clause="", None, None       
        self.Eval_depth=0
       
        self.Visible[:]=[]                         # modif followng lists 
        self.Nodestore[:]=[]                 # a cyclic list of temporary nodes  
        self.Object_list[:]=[]                 # list of nodes (except temporary), with order preserved
        self.Pinlist[:]=[]                        # list of pin inputs
        self.Outlist[:]=[]                        # list of pin outputs
        self.Delayed_objects[:]=[]                                  
        self.delayed_list[:]=[]
        self.Active_list=[]                                          
        self.Idem_list[:]=[]                   
        self.Volatile[:]=[]                    # list of objects that need to be always updated
        self.Stochastic=[]
        self.Condition=[]                      
        self.Condition_number.clear()   
        self.Glitches.clear()                   # dict of existing dependent glitches for immediate updating 
        self.Allow_dic.clear()                  
        self.Save_value.clear()            
        self.All_conditions.clear()        
        self.slaveto=0                    # for yoked scripts
        self.masterto=[]                 # for yoked scripts
        
        self.Counter=0                   # development tool to improve performance
        self.t0=0                            # development tool: timing initialization 

        io.clearbuffer(self)          # clear interrupt buffer for pins 

