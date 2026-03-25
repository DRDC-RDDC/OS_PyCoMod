from abc import ABC, abstractmethod

import heapq
import numpy as np
import pandas as pd

from .elements import (BuildingBlock, VirtualBuildingBlock, SimTime, SimDate, RunInfo,
                              Pool, Flow, Parameter, Equation, Step, Impulse, Event, Process, Delay, Time, Date, TimeStep)



        

# Class for building and running the model
class Model(ABC):

    def __init__(self, *args, **kwargs):

        # Time info
        self._t = SimTime(0, parent=self)
        self._date = SimDate(parent=self)
        self._tunit = RunInfo(np.timedelta64(1, 'D'), parent=self)

        # Run info
        self._dt = RunInfo(1, parent=self)
        self._end = RunInfo(365, parent=self)
        self._reps = RunInfo(100, parent=self)

        # Model elements
        self._parameters = []
        self._equations = []
        self._flows = []
        self._pools = []
        self._processes = []
        
        self._external = [] #for external elements
        
        #self._next_uid = 1 #unique ids used for pool members


        # Sub-models
        self._models = []

        # Available
        self._available = {}
        
        # Event messages
        self._messages = {}

        # Output
        self._out = []  # Elements to track for output
        self._output = None  # Output from run
        self._output_mc = None  # Output from mc runs


        # Event queue for discrete events
        self._event_queue = []

        # Setup
        a = self.build(*args, **kwargs)
        
        if a != None:
            self.set_available(a)


    # def _get_uid(self):
        # uid = self._next_uid
        # self._next_uid += 1
        
        # return uid

    # def _get_uids(self, n):
        # uids = [self._next_uid + i for i in range(n)]
        # self._next_uid += n
        # return uids


    # Read-only properties
    @property
    def t(self):
        return self._t

    @property
    def date(self):
        return self._date
        
    @property
    def tunit(self):
        return self._tunit

    @property
    def dt(self):
        return self._dt

    @property
    def end(self):
        return self._end

    @property
    def reps(self):
        return self._reps

    @property
    def out(self):
        return self._out

    def set_output(self, *args):
        self._out = list(args)

    @abstractmethod
    def build(self):
        # Implemented by sub-class
        pass
        
    def set_available(self, names, output=None ):
        
        # if output is None, default is to include all elements in output
        if output == None:
            self._out = []
        
        # self is not needed in the dict
        if 'self' in names:
            del names['self']
        
        for key, value in names.items():
            if isinstance(value, BuildingBlock) or isinstance(value, Model) or isinstance(value, Process):
                value.name = key
                
                if output == None:
                    self._out.append(key)
        
        self._available = names | self._available
        
        if output != None:
            self._out = [o.name for o in output]
        
        
    def __getattr__(self, name):
        return self._available[name]
    


    def connect(self, **kwargs):
        for name in kwargs:
            getattr(self, name).connect(kwargs[name])
            

    # element creation functions
    def pool(self, value=1, allow_neg=False, pool_type='float', name=None, external=False):
        
        if external:
            
            e = Pool(value, allow_neg, pool_type, parent=self)
            
            v = VirtualBuildingBlock(Pool)
            v.connect(e)
            
            self._external.append(v)
            
            return v
            
        else:
            e = Pool(value, allow_neg, pool_type, parent=self)
            self._pools.append(e)
            
            if name != None:
                self._available[name] = e
                self._out.append(name)
            
            return e
        
    # def flow(self, rate_func=lambda: 1, src=None, dest=None, discrete=False):
        # e = Flow(rate_func, src, dest, discrete)
        # self._flows.append(e)
        # return e
        
    def flow(self, *args, **kwargs):
        # decorator without parameters or call with flow function but no parameters
        # a flow without src or dest args is useless, but syntactically allowed
        if len(args)==1 and len(kwargs)==0 and callable(args[0]):
            e = Flow(args[0], parent=self)
            self._flows.append(e)
            return e
            
        # non-decorator call with flow function and optional parameters
        elif len(args)==1 and len(kwargs)>0 and callable(args[0]):
            
            src = None
            dest = None
            discrete = False
            stochastic = False
            variance = None
            when = None
            limit = None
            name = None
            
            
            if 'src' in kwargs:
                src = kwargs['src']
            if 'dest' in kwargs:
                dest = kwargs['dest']
            if 'discrete' in kwargs:
                discrete = kwargs['discrete']
            if 'stochastic' in kwargs:
                stochastic = kwargs['stochastic']
            if 'variance' in kwargs:
                variance = kwargs['variance']
            if 'when' in kwargs:
                when = kwargs['when']
            if 'limit' in kwargs:
                limit = kwargs['limit']
            if 'name' in kwargs:
                name = kwargs['name']
            
            
            e = Flow(args[0], src, dest, discrete, stochastic, variance, when, limit, parent=self)
            self._flows.append(e)
            
            if name != None:
                self._available[name] = e
                self._out.append(name)
            
            return e
        
        # else assume decorator with params
        else:
            src = None
            dest = None
            discrete = False
            stochastic = False
            variance = None
            when = None
            limit = None
            name = None
            
            if 'src' in kwargs:
                src = kwargs['src']
            if 'dest' in kwargs:
                dest = kwargs['dest']
            if 'discrete' in kwargs:
                discrete = kwargs['discrete']
            if 'stochastic' in kwargs:
                stochastic = kwargs['stochastic']
            if 'variance' in kwargs:
                variance = kwargs['variance']
            if 'when' in kwargs:
                when = kwargs['when']
            if 'limit' in kwargs:
                limit = kwargs['limit']
            if 'name' in kwargs:
                name = kwargs['name']
                
            def inner(rate_func):
                e = Flow(rate_func, src, dest, discrete, stochastic, variance, when, limit, parent=self)
                self._flows.append(e)
                
                if name != None:
                    self._available[name] = e
                    self._out.append(name)
                
                return e
                
            return inner
        
            
            
    def parameter(self, value=1, name=None):
        e = Parameter(value, parent=self)
        self._parameters.append(e)
        
        if name != None:
            self._available[name] = e
            self._out.append(name)
        
        return e
        
    def equation(self, eq_func=lambda: 1, name=None):
        e = Equation(eq_func, parent=self)
        self._equations.append(e)
        
        if name != None:
            self._available[name] = e
            self._out.append(name)
        
        return e
        
    def step(self, values, times, default=0, name=None):
        e = Step(values, times, default, parent=self)
        self._equations.append(e)
        
        if name != None:
            self._available[name] = e
            self._out.append(name)
        
        return e       
     
    def impulse(self, values, times, name=None):
        e = Impulse(values, times, parent=self)
        self._equations.append(e)
        
        if name != None:
            self._available[name] = e
            self._out.append(name)
        
        return e

    def submodel(self, m, name=None):
        #m._event_queue = self._event_queue
        #m._t = self._t
        #m._date = self._date 
        
        self._models.append(m)

        if name != None:
            self._available[name] = m
            self._out.append(name)
        
        return m


    #def process(self, routine=lambda:1, args=None, time=None, priority=0):
    def process(self, *args, **kwargs):
        # decorator without parameters or call with process function but no parameters
        if len(args)==1 and len(kwargs)==0 and callable(args[0]):
            e = Process(args[0], parent=self)
            self._processes.append(e)
            return e
            
        # non-decorator call with process function and optional parameters
        elif len(args)==1 and len(kwargs)>0 and callable(args[0]):
            
            proc_args = () # this must be an error, conflicts with *args above!!!!!!
            start = None
            priority = 0
            name = None
            
            if 'args' in kwargs:
                proc_args = kwargs['args']
            if 'start' in kwargs:
                start = kwargs['start']
            if 'priority' in kwargs:
                priority = kwargs['priority']
            if 'name' in kwargs:
                name = kwargs['name']
            
            e = Process(args[0], proc_args, start, priority, parent=self)
            self._processes.append(e)
            
            if name != None:
                self._available[name] = e
                self._out.append(name)
            
            return e
        
        # else assume decorator with params
        else:
            proc_args = ()
            start = None
            priority = 0
            name = None
            
            if 'args' in kwargs:
                proc_args = kwargs['args']
            if 'start' in kwargs:
                start = kwargs['start']
            if 'priority' in kwargs:
                priority = kwargs['priority']
            if 'name' in kwargs:
                name = kwargs['name']
                
            def inner(routine):
                e = Process(routine, proc_args, start, priority, parent=self)
                self._processes.append(e)
                
                if name != None:
                    self._available[name] = e
                    self._out.append(name)
                    
                
                return e
                
            return inner
        


    def _push_event(self, event):
        
        #assert event.time >= self.t(), "Event time must be greater than or equal present simulation time."

        if event.time >= self.t():
            heapq.heappush(self._event_queue, event)
        else:
            print("Warning: Event time is less than current simulation time. Event dropped.")



    def _pop_event(self):
        return heapq.heappop(self._event_queue)
        
        

    # process wait types
    


    def wait_step(self, steps = 1):
        
        return TimeStep(steps)

    def wait_time(self, time):
        
        return Time(time)
        
        
    def wait_sim_start(self):
        
        return self.wait_time(self.t.init_value)
        
        
    def wait_date(self, date):
        
        return Date(date)
        
    def wait_delay(self, delay):
        
        return Delay(delay)
        
    def wait_condition(self, condition):
        
        def cond_routine():
            
            while True:
                yield TimeStep()
                
                if condition():
                    break
                    
        return Event(cond_routine,  parent=self)



    def get_start_event(self, start):
        
        def routine():
            yield start
            return str(start)
            
        return Event(routine,  parent=self)



    def wait_any(self,*args):
        
        ev = Event(lambda: 0,  parent=self)
        
        def any_routine():
            for a in args:
                if isinstance(a, Event):
                    a.origin = ev
                    a.start(Delay(0))
                else:
                    a = self.get_start_event(a)
                    a.origin = ev
                    a.start(Delay(0))
                    
            x = yield
            
            return x
            
        ev.routine = any_routine
        
        return ev


    def wait_all(self,*args):
        
        ev = Event(lambda: 0,  parent=self)
        
        def all_routine():
            for a in args:
                if isinstance(a, Event):
                    a.origin = ev
                    a.start(Delay(0))
                else:
                    a = self.get_start_event(a)
                    a.origin = ev
                    a.start(Delay(0))
            
            x = []
            for a in args:
                y = yield
                x.append(y)
            
            return x
            
        ev.routine = all_routine
        
        return ev

    def wait_sequence(self,*args):
        
        ev = Event(lambda: 0,  parent=self)
        
        def seq_routine():
            
            x = []
            
            for a in args:
                if not isinstance(a, Event):
                    a = self.get_start_event(a)
                
                y = yield a
                x.append(y)
            
            return x
            
        ev.routine = seq_routine
        
        return ev



    def wait_message(self, message):
        
        def msg_routine():
            
            x = yield
            
            return x
            
        ev = Event(msg_routine,  parent=self)
        
        self.register_message(message, ev)
        
        return ev
        
    
    def register_message(self, message, event):
        
        if message not in self._messages:
            
            self._messages[message] = []
            
        self._messages[message].append(event)
        
        
        
        
    def send_message(self, message, value=None):
        
        if message in self._messages:
            
            for ev in self._messages[message]:
                
                try:
                    ev.resume(value)
                    
                except StopIteration as e:
                    pass
                
            self._messages[message] = []    
        
            


    # def _register(self):
        # # Get all attributes that are an instance of BuildingBlock and
        # # organize them into lists

        # elements = [x for x in self.__dict__.values()
                    # if isinstance(x, (BuildingBlock, Model))]

        # for e in elements:
            # if isinstance(e, Sample):
                # self._samples.append(e)
            # #elif isinstance(e, Parameter):
            # #    self._parameters.append(e)
            # #elif isinstance(e, Equation):
            # #    self._equations.append(e)
            # #elif isinstance(e, Flow):
            # #    self._flows.append(e)
            # #elif isinstance(e, Pool):
            # #    self._pools.append(e)
            # #elif isinstance(e, Model):
            # #    self._models.append(e)
                # #all sub-models share the root event queue
            # #    e._event_queue = self._event_queue



    # Set any initial conditions for the model
    def _init_cond(self, init):
        # Recursively apply initial conditions
        for key, value in init.items():
            if key == 'out':
                # Store elements of this model to be tracked for output
                self._out = value
            elif key in ['dt', 't', 'tunit', 'end', 'date', 'reps']:
                # If time and run info, push init to submodels
                self._push_init(key, value)
            else:
                # Set initial condition
                e = getattr(self, key)

                # If it's a model
                if isinstance(e, Model):
                    e._init_cond(value)

                # If it's an element
                else:
                    e.init_cond(value)

    # # Set the run and model initial conditions from a dictionary
    # def set_init(self, init):
        # self._init_cond(init['run'])
        # self._init_cond(init['model'])




    def set_init(self, init, key=None):
        
        if key is None:
        
            #init run variables
            self.t.init_cond(init['run']['t'][0])
            self.date.init_cond(np.datetime64(init['run']['date'][0]))
            self.tunit.init_cond(np.timedelta64(1,init['run']['tunit'][0]))
            self.dt.init_cond(init['run']['dt'][0])
            self.end.init_cond(init['run']['end'][0])
            self.reps.init_cond(init['run']['reps'][0])
        
            key = 'model'

        for k, v in init[key].items():
            # if it's a sub-model reference, init the sub-model
            if len(v) == 1 and type(v[0]) == str and v[0][0] == '<':
                sub_key = v[0][1:-1] # strip the <> from the key name
                getattr(self, k).set_init(init, sub_key)
                
            # # if it's the output list    
            # elif k == 'out':
                # self._out = v  
                
            # else it's a regular init value (or array)
            else:
                if len(v) == 1:
                    v = v[0]
                    
                getattr(self, k).init_cond(v)


    # Get the initial condition dict for this model
    def get_init(self, d=None, key=None):

        if d is None:
            d = {}
            # create run dict
            d['run'] = {}
            d['run']['t'] = [self.t()]
            d['run']['date'] = [str(self.date())]
            d['run']['tunit'] = [np.datetime_data(self.tunit())[0]]
            d['run']['dt'] = [self.dt()]
            d['run']['end'] = [self.end()]
            d['run']['reps'] = [self.reps()]
            
        if key is None:
            key = 'model'
            
        # Create model dict
        d[key] = {}
        
        elements = [(k, v) for k, v in self._available.items()
                    if isinstance(v, (Pool, Parameter, Model))]

        for k, v in elements:
            if isinstance(v, Model):
                next_key = key + '.' + k
                d[key][k] = ['<' + next_key + '>']
                v.get_init(d, next_key)
            else:
                if type(v()) == np.ndarray:
                    d[key][k] = v()
                else:
                    d[key][k] = [v()]

        # # Add output tracking
        # if self.out is None:
            # d[key]['out'] = [None]
        # else:
            # d[key]['out'] = self.out

        return d


    def write_excel_init(self, file=None):

        if file is None:
            file = 'init.xlsx'

        d = self.get_init()

        with pd.ExcelWriter(file) as writer:
            for k, v in d.items():
                
                # Get max num rows
                rows = max([len(x) for x in v.values()])

                # Normalize column lengths
                for j in v.keys():
                    add = rows - len(v[j])
                    if add > 0:
                        v[j] = np.append(v[j], [None]*add)
                
                df = pd.DataFrame.from_dict(v)
                df.to_excel(writer, sheet_name=k, index=False)


    def read_excel_init(self, file, sheet=None):
        # If file is a string (first call), read the file
        if type(file) is str:
            file = pd.read_excel(file, None)
            
        d = {}
        
        # for each sheet df
        for k, df in file.items():
            
            d[k] = {}
            
            # for each column
            for n in df.columns:
            
                c = [x for x in df[n] if not pd.isna(x)]
          
                d[k][n] = c

        #self.set_init(d)
        return d


    # # Get the run init settings
    # def _get_run_init(self):
        # # Add run settings
        
        # d = {}
        # d['t'] = self.t()
        # d['date'] = self.date()
        # d['tunit'] = self.tunit()
        # d['dt'] = self.dt()
        # d['end'] = self.end()
        # d['reps'] = self.reps()

        # return d

    # def get_init(self):
        
        # self._reset()
        
        # d = {}

        # d['run'] = self._get_run_init()
        # d['model'] = self._get_model_init()

        # return d

    # Get dataframes representing initial conditions for the model
    def _get_init_df(self, d=None, key=None):

        self._reset()

        # If this is the root, create the dict and add run settings
        if d is None:
            d = {}

            # Add run settings
            d['run'] = {}
            d['run']['t'] = [self.t()]
            d['run']['date'] = [self.date()]
            d['run']['tunit'] = [self.tunit()]
            d['run']['dt'] = [self.dt()]
            d['run']['end'] = [self.end()]
            d['run']['reps'] = [self.reps()]

            d['run'] = pd.DataFrame.from_dict(d['run'])

        # If this is the root, set the key to 'model'
        if key is None:
            key = 'model'

        # Create dict
        d[key] = {}

        # Add all elements to the dict
        elements = [(k, v) for k, v in self._available.items()
                    if isinstance(v, (Pool, Parameter, Model))]
        for k, v in elements:
            if isinstance(v, Model):
                next_key = key + '.' + k
                d[key][k] = [next_key]
                v._get_init_df(d, next_key)
            else:
                if type(v()) == np.ndarray:
                    d[key][k] = v()
                else:
                    d[key][k] = [v()]

        # Add output tracking
        if self.out is None:
            d[key]['out'] = [None]
        else:
            d[key]['out'] = self.out

        # Get max num rows
        rows = max([len(x) for x in d[key].values()])

        # Normalize column lengths
        for k in d[key].keys():
            add = rows - len(d[key][k])
            if add > 0:
                d[key][k] = np.append(d[key][k], [None]*add)

        # Convert to dataframe
        d[key] = pd.DataFrame.from_dict(d[key])

        return d

    # # Write an excel file containing initial conditions for the model
    # def write_excel_init(self, filename=None):
        # d = self._get_init_df()

        # if filename is None:
            # filename = 'init.xlsx'

        # with pd.ExcelWriter(filename) as writer:
            # for k, v in d.items():
                # v.to_excel(writer, sheet_name=k, index=False)

    # Set initial condition and push to submodels
    def _push_init(self, key, value):
        getattr(self, key).init_cond(value)
        for m in self._models:
            m._push_init(key, value)

    # UPDATE FUNCTIONS

    def _add_flows(self):

        # Recurse through sub-models
        for m in self._models:
            m._add_flows()

        # Add flows to pools
        for e in self._flows:
            e.add_flows()

    def _update_pools(self):

        # Recurse through sub-models
        for m in self._models:
            m._update_pools()

        # Update pools (in order)
        for e in self._pools:
            e.update()
            e.save_hist()

    def _update_equations(self):

        # Recurse through sub-models
        for m in self._models:
            m._update_equations()

        # Update equations (in order)
        for e in self._equations:
            e.update()
            e.save_hist()

    def _update_parameters(self):
        # Recurse through sub-models
        for m in self._models:
            m._update_parameters()

        # Duplicate existing parameter value (only updated by events)
        for e in self._parameters:
            e.update_value(e.value)
            e.save_hist()


    def _update_flows(self):

        # Recurse through sub-models
        for m in self._models:
            m._update_flows()

        # Update flows (order independent)
        for e in self._flows:
            e.update()
        for e in self._flows:
            e.save_hist()

    def _update_time(self, t):
        
        # Recurse through sub-models
        #for m in self._models:
        #    m._update_time(t)

        # # add the new time record without incrementing dt
        # self.t.update(0)
        # self.t.save_hist()
        
        # # update any between timestep events
        # self._update_events()
        
        # # Update time info after all events
        # self.t.push_value(self.t(-2) + self.dt())
        
        #self.t.update(t)
        #self.t.save_hist()
        
        self.t.push_value(t)

        # update sim date
        #self.date.update(self.dt(), self.tunit())
        #self.date.save_hist()



    #update events until t_next
    def _update_events(self, t_next):
        
        while len(self._event_queue) > 0 and self._event_queue[0].time <= t_next:
            #e = heapq.heappop(self._event_queue)
            e = self._pop_event()
            #self.t.push_value(e.time)
            self._update_time(e.time)
            e.run()
                


    # # Regular update sequence
    # def _update_regular(self):

        # self._add_flows()
        # self._update_pools()
        
        
        
        # self._update_equations()
        # self._update_flows()

    def _update(self):
        
        t_next = self.t() + self.dt()
        
        # update events (events update values in place)
        self._update_events(t_next)
        
        #self._update_parameters()
        
        self._update_time(t_next)
        
        self._update_equations()
        
        self._update_flows()
        
        self._add_flows()
        
        self._update_pools()
        




    # # Update pass for all model elements
    # def _update(self):

        # # Update time
        # self._update_time()

        # # Update model elements
        # self._update_regular()

    def _reset_pools(self):

        # Recurse through sub-models
        for m in self._models:
            m._reset_pools()

        # Reset pools
        for e in self._pools:
            e.reset()

    def _reset_parameters(self):

        # Recurse through sub-models
        for m in self._models:
            m._reset_parameters()

        # Reset parameters
        for e in self._parameters:
            e.reset()

    # def _reset_samples(self):

        # # Recurse through sub-models
        # for m in self._models:
            # m._reset_samples()

        # # Reset samples
        # for e in self._samples:
            # e.reset()

    def _reset_equations(self):

        # Recurse through sub-models
        for m in self._models:
            m._reset_equations()

        # Reset samples
        for e in self._equations:
            e.reset()


    def _reset_flows(self):

        # Recurse through sub-models
        for m in self._models:
            m._reset_flows()

        # Reset samples
        for e in self._flows:
            e.reset()

    # def _reset_time(self):

        # # Recurse through sub-models
        # for m in self._models:
            # m._reset_time()

        # self.t.reset()
        # self.date.reset()
        
    def _reset_run(self, sim_time=None, sim_date=None, sim_tunit=None, sim_dt=None, sim_end=None, sim_reps=None, event_queue=None, messages=None):

        self._event_queue = []
        self._messages = {}
        self.t.reset()
        
        # get/set all global run objects
        
        # time
        if sim_time == None:
            sim_time = self._t
        else:
            self._t = sim_time
        
        # date
        if sim_date == None:
            sim_date = self._date
        else:
            self._date = sim_date
        
        # time unit
        if sim_tunit == None:
            sim_tunit = self._tunit
        else:
            self._tunit = sim_tunit
        
        # dt
        if sim_dt == None:
            sim_dt = self._dt
        else:
            self._dt = sim_dt
        
        # end
        if sim_end == None:
            sim_end = self._end
        else:
            self._end = sim_end
        
        # reps
        if sim_reps == None:
            sim_reps = self._reps
        else:
            self._reps = sim_reps
        
        # event queue
        if event_queue == None:
            event_queue = self._event_queue
        else:
            self._event_queue = event_queue
        
        # messages
        if messages == None:
            messages = self._messages
        else:
            self._messages = messages
        
        
        # push root model run objects to all children
        for m in self._models:
            m._reset_run(sim_time, sim_date, sim_tunit, sim_dt, sim_end, sim_reps, event_queue, messages)
        
        
    def _reset_processes(self):
        # Recurse through sub-models
        for m in self._models:
            m._reset_processes()
           
        for e in self._processes:
            e.reset()

    def _reset_output(self):
        self._output = None

    def _reset_output_mc(self):
        self._output_mc = None


    def _reset_messages(self):
        self._messages = {}
        

    # Reset all model elements to initial conditions
    def _reset(self):

        # Empty event queue
        #self._event_queue = []

        # Reset model
        self._reset_run()
        self._reset_output()

        # Reset all elements
        self._reset_pools()
        self._reset_parameters()
        self._reset_equations()
        self._reset_flows()
        self._reset_processes()
        



    # Save all output
    def _save_output(self):
        self._output = {}
        for key in self.out:
            e = getattr(self, key)
            #key = e.name

            if isinstance(e, BuildingBlock):
                #self._output[key] = getattr(self, key).get_hist()
                self._output[key] = e.get_hist()
            elif isinstance(e, Model):
                self._output[key] = e._save_output()

        return self._output


    # def start_process(self, event, delay=0):
        # if delay > 0:
            # event.time = self.t() + delay
            # heapq.heappush(self._event_queue, event)
        # else:
            # event.run()
        

    # Do a run
    def _run(self, end=None, dt=None, tunit=None, start_time=None,
             start_date=None, init=None):

        # First apply initial conditions from init dict
        if init is not None:
            # if init is a string, assume it's an excel init file
            if type(init) == str:
                init = self.read_excel_init(init)
                self.set_init(init)
            # else assume it's an init dict
            else:
                self.set_init(init)

        # Override for any of the following run parameters
        if end is not None:
            self.end.init_cond(end)

        if dt is not None:
            self.dt.init_cond(dt)

        if tunit is not None:
            self.tunit.init_cond(np.timedelta64(1, tunit))

        if start_time is not None:
            self.t.init_cond(start_time)

        if start_date is not None:
            self.date.init_cond(np.datetime64(start_date))

        # Number of sim steps
        n = int(self.end()/self.dt())

        # Reset after applying initial conditions
        self._reset()

        # For each time step update everything
        for i in range(n):

            # Update model elements
            self._update()

        
        self._update_parameters()

        # Save output
        self._save_output()



    # Get the time series of values for this element as a numpy array (using time steps)
    def get_time_series(self, value_hist, time_hist):
        v = value_hist[0]
        
        t = time_hist[0]
        
        ts = [v]
        
        i = 1
        
        while t <= self.end():
            
            t += self.dt()
            
            if i >= len(time_hist) or t < time_hist[i]:
                ts.append(v)
            else:
                v = value_hist[i]
                i += 1
                ts.append(v)
    
        return ts 
            

    def get_mc_xtimes(self):
        t = self.t.init_value
        
        xtimes = [t]
        
        while t <= self.end():
            t += self.dt()
            
            xtimes.append(t)
            
        return xtimes
        
    def get_mc_xdates(self):
        
        xtimes = self.get_mc_xtimes()
        
        return [self.date() + t * self.tunit() for t in xtimes]

    # Create container for mc output based on output from first replication
    def _init_output_mc(self, output):
        output_mc = {}
        for k, v in output.items():
            #if not isinstance(v, dict):
            if 'values' in v and 'times' in v:
                output_mc[k] = {}
                output_mc[k]['mc_values'] = np.array([self.get_time_series(v['values'], v['times'])])
                output_mc[k]['mc_times'] = self.get_mc_xtimes()
                output_mc[k]['mc_dates'] = self.get_mc_xdates()
                
                
            else:
                output_mc[k] = self._init_output_mc(v)

        return output_mc

    # Append output from subsequent replications to the mc output
    def _append_output_mc(self, output_mc, output):
        for k, v in output.items():
            #if not isinstance(v, dict):
            if 'values' in v and 'times' in v:
                output_mc[k]['mc_values'] = np.append(output_mc[k]['mc_values'], np.array([self.get_time_series(v['values'], v['times'])]), axis=0)
            else:
                self._append_output_mc(output_mc[k], v)

    # Save output from MC runs
    def _save_output_mc(self):
        if self._output_mc is None:
            self._output_mc = self._init_output_mc(self._output)
        else:
            self._append_output_mc(self._output_mc, self._output)

    # Monte carlo runs
    def _run_mc(self, reps=None, end=None, dt=None, tunit=None,
                start_time=None, start_date=None, init=None):
        # First apply initial conditions from init dict
        if init is not None:
             # if init is a string, assume it's an excel init file
            if type(init) == str:
                init = self.read_excel_init(init)
                self.set_init(init)
            # else assume it's an init dict
            else:
                self.set_init(init)

        # Override for any of the following run parameters
        if reps is not None:
            self.reps.init_cond(reps)

        # Override for any of the following run parameters
        if end is not None:
            self.end.init_cond(end)

        if dt is not None:
            self.dt.init_cond(dt)

        if tunit is not None:
            self.tunit.init_cond(np.timedelta64(1, tunit))

        if start_time is not None:
            self.t.init_cond(start_time)

        if start_date is not None:
            self.date.init_cond(np.datetime64(start_date))



        # Reset mc output
        self._reset_output_mc()

        # Run all reps and save mc output
        for n in range(int(self.reps())):
            self._run()
            self._save_output_mc()
            
            print("Done {n} / {N}".format(n=n+1, N=self.reps()))


