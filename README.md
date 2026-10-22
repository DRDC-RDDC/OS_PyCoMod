# OS_PyCoMod

## HTML export (`html` branch)

This branch adds `pcm.export_to_html`, which turns a PyCoMod model into a single standalone HTML file that runs in any browser without Python. The model's equations, flows and processes are translated to JavaScript, and the page provides a Bokeh-based interface for editing inputs, running single or Monte Carlo simulations (with percentile bands), saving and loading inputs, and exporting results as CSV or PNG. Supported features include stochastic flows, step and impulse functions, nested sub-models, and discrete-event processes (waits, conditions and messages).

To get started, install the branch and export a model:

    pip install git+https://github.com/DRDC-RDDC/OS_PyCoMod.git@html

```Python
import pycomod as pcm

pcm.export_to_html(model=MyModel(), filename='my_model.html',
                   title='My Model', help_text='# Notes shown in the Help tab')
```

Ready-made scripts are in [examples/](examples/) (e.g. `python examples/sir_export.py`), with their generated HTML alongside, and tests can be run with `pytest tests`.

## Introduction

PyCoMod is a Python package for building and running compartment models derived from systems of differential equations such as the Susceptible-Infectious-Recovered (SIR)model of infectious diseases.

The project is being released under Open Science (OS), an initiative of the Government of Canada to make the research products of federal scientists open to the public. PyCoMod was developed by scientists in the Centre for Operational Research and Analysis (CORA) within Defence Research and Development Canada (DRDC) in order to model the spread of COVID-19 in specific populations of interest to the Canadian Armed Forces.

The primary developers and contributors to this work are:
 - Mr. Stephen Okazawa
 - Ms. Josée van den Hoogen
 - Dr. Steve Guillouzic

The contents of this readme have also been published as a DRDC reference document: [Okazawa, S., van den Hoogen, J., and Guillouzic, S., PyCoMod (Python Compartment Modelling) Programming reference. DRDC-RDDC-2023-D111](https://pubs.drdc-rddc.gc.ca/BASIS/pcandid/www/engpub/DDW?W%3DSYSNUM=817298&r=0).

PyCoMod is composed of a set of Python classes:
 - model element classes (pools, flows, parameters, equations, and random samples) are used to define the behavior of the system;
 - a model class is used to contain these elements as well as nested sub-models;
 - a run manager class is used to keep track of various models, initial conditions, and saved output; and
 - a plotter class is used for visualizing the results of model runs.

Internally, the package implements a numerical differential equation solver to solve the system of equations in discrete time-steps and to generate time series output for the state of the system. PyCoMod also allows discrete stochastic flow equations to be created, and the model can be automatically run repeatedly to conduct Monte Carlo simulations and plot the distribution of model outputs.

## Installation

To install PyCoMod to your local Python environment (requires Git version control system), run the following from the command line:

    pip install git+https://github.com/DND-DRDC-RDDC/OS_PyCoMod.git

To install PyCoMod in [Google Colab](https://colab.research.google.com), run the following in a code cell:

    ! pip install git+https://github.com/DND-DRDC-RDDC/OS_PyCoMod.git

After installing the package, import PyCoMod into your code.

```Python
import pycomod as pcm
```

The examples that follow were tested in [Google Colab](https://colab.research.google.com) and assume that PyCoMod has been installed and imported as above using the abreviated name *pcm*.

## A simple SIR model example

The susceptible-infectious-recovered (SIR) model of disease spread consists of the three compartments (S, I and R), and two flows that move individuals from susceptible to infectious and from infectious to recovered.
<p align="center">
  <img width="300" height="100" src="https://user-images.githubusercontent.com/86330428/127037594-8d7fe2ad-0143-4a0b-bccc-5fdb11f7c699.png">
</p>



The flow of individuals from S to I is given by the rate

<img src="https://render.githubusercontent.com/render/math?math=F_{si}=bS\frac{I}{N}">

where *b* is the transmission rate and *N* is the total population, <img src="https://render.githubusercontent.com/render/math?math=S%2BI%2BR">.

The flow of individuals from I to R is given the rate

<img src="https://render.githubusercontent.com/render/math?math=F_{ir}=gI">

where *g* is the recovery rate.

This produces the following system of differential equations:

<img src="https://render.githubusercontent.com/render/math?math=\frac{dS}{dt}=-bS\frac{I}{N}">

<img src="https://render.githubusercontent.com/render/math?math=\frac{dI}{dt}=bS\frac{I}{N}-gI">

<img src="https://render.githubusercontent.com/render/math?math=\frac{dR}{dt}=gI">

Given a population of size 100, where 5 individuals are infected (I) and the remaining 95 individuals are susceptible (S), we can model this system in PyCoMod with the following code:

```python
class SimpleSIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool(95)
        self.I = pcm.Pool(5)
        self.R = pcm.Pool(0)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Parameters
        self.b = pcm.Parameter(0.2)
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(lambda: self.b() * self.S() * self.I() / self.N(),
                            src=self.S, dest=self.I)
        self.Fir = pcm.Flow(lambda: self.g() * self.I(),
                            src=self.I, dest=self.R)

        # Output
        self.set_output('S', 'I', 'R')
```

The first two lines begin the definition of a custom class inheriting properties from the PyCoMod *Model* class and overrides the model's *_build* function to define the elements of this simple SIR model. In this case, we create the three population compartments (S,I,R) using the PyCoMod *Pool* class and specify the initial value of each pool. We define the value *N* (the total population) as a PyCoMod *Equation*. Equations are defined by a function referencing other model elements; lambda functions are syntactically compact for this purpose. To obtain the value of a model element, we call the object by adding open and close parentheses *( )*; for example, the current number of susceptible individuals is obtained by `self.S()`. Using the PyCoMod *Parameter* class we create and specify values for the model's parameters: transmission rate, *b*, and recovery rate, *g*. Next, we define the movement between the compartments using PyCoMod's *flow* class; flows are defined by a function, similar to the *Equation* class. In this case, the flow functions correspond to the rate equations, *Fsi* and *Fir*, defined above. Flows must also specify a source pool and a destination pool. Note that when specifying source and destination pools, we reference the pool object itself rather than calling it (e.g. `src=self.S`, not `src=self.S()`). A final step in specifying the model is to let PyCoMod know which outputs we want to capture for analysis. This is done by calling the model's *set_output* method and providing the names of the model elements that we want to track.

Having defined the *SimpleSIR* model class, we can now create an instance of it, let's call it *m*.

```Python
m = SimpleSIR()
```

We use another PyCoMod class called a *RunManager* to run it. The run manager keeps track of multiple models, run settings and output so that batches of runs can be automated. First we create an instance of the run manager.

```Python
mgr = pcm.RunManager()
```

Now we can tell the run manager to run the *SimpleSIR* model. We can supply run settings (such as the duration in this example), and we must provide a label as a key to access the run results later.

```Python
mgr.run(m, duration=150, label='My run')
```

Finally, we can plot the results of the run using the PyCoMod *Plotter*.  First we create an instance of the plotter, which creates a Matplotlib Figure, and then we can plot outputs from the run on the figure axes.

```Python
plt = pcm.Plotter(title='SIR Time Series', ylabel='Population', fontsize=14)
plt.plot(mgr['My run'], 'S', color='blue', label='S')
plt.plot(mgr['My run'], 'I', color='orange', label='I')
plt.plot(mgr['My run'], 'R', color='green', label='R')
plt.plot(mgr['My run'], 'S + I + R', color='black', label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/125519680-4f964905-8c1b-4565-acf9-fac73ea403f4.png)

Each call to the plotter's *plot* method must specify a run and an output. The run is identified by indexing the run manager with the label that we specified when we ran the model. The output must be one of the outputs that was specified in the model using *set_output*. Outputs can be summed together in a plot, e.g. *S + I + R* in the last line, above.

Note that the examples that follow are meant to provide simple demonstrations of the features of PyCoMod; they are not necessarily appropriate models for real situations.

## How to add model elements
To incorporate additional model elemets, such as compartments, parameters, or rates, you need only define the model elements as pool, parameter, or flow respectively. For example, to expand on the SIR model above to incorporate the exposed compartment (E), representing a delay from time of infection to infectiousness, we can generate the SEIR compartment model as follows, where <img src="https://render.githubusercontent.com/render/math?math=a^{-1}"> is the time from E to I: 

```python
class SimpleSEIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool(95)
        self.E = pcm.Pool(0)
        self.I = pcm.Pool(5)
        self.R = pcm.Pool(0)

        # Equations
        self.N = pcm.Equation(
                lambda: self.S() + self.E() + self.I() + self.R())

        # Parameters
        self.b = pcm.Parameter(0.2)
        self.a = pcm.Parameter(0.1)
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fse = pcm.Flow(lambda: self.b() * self.S() * self.I() / self.N(),
                            src=self.S, dest=self.E)
        self.Fei = pcm.Flow(lambda: self.a() * self.E(),
                            src=self.E, dest=self.I)
        self.Fir = pcm.Flow(lambda: self.g() * self.I(),
                            src=self.I, dest=self.R)

        # Output
        self.set_output('S', 'E', 'I', 'R')


# Instantiate model
m = SimpleSEIR()

# Run model
mgr.run(m, duration=150, label='My run')

# Plot results
plt = pcm.Plotter(title='SEIR Time Series', ylabel='Population', fontsize=14)
plt.plot(mgr['My run'], 'S', color='blue', label='S')
plt.plot(mgr['My run'], 'E', color='red', label='E')
plt.plot(mgr['My run'], 'I', color='orange', label='I')
plt.plot(mgr['My run'], 'R', color='green', label='R')
plt.plot(mgr['My run'], 'S + I + R', color='black', label='Total')

```

Note that the run manager does not need to be defined here because it was already defined for the SimpleSIR model above.


## Stochastic model elements

In PyCoMod, we can also introduce stochastic model elements and run Monte Carlo simulations. For example, two improvements to the simple SIR model would be to sample the transmission rate from a distribution reflecting the uncertainty in this parameter, and to make the flows stochastic and discrete. We show these changes below in a new model class called *MonteCarloSIR*.

```Python
import numpy as np
rng = np.random.default_rng()

class MonteCarloSIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool(95)
        self.I = pcm.Pool(5)
        self.R = pcm.Pool(0)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Transmission rate parameters
        self.b_m = pcm.Parameter(0.2)
        self.b_s = pcm.Parameter(0.05)

        # Transmission rate random sample
        self.b = pcm.Sample(lambda: rng.normal(self.b_m(), self.b_s()))

        # Recovery rate parameter
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(
                lambda: rng.binomial(self.S(), self.b() * self.I() / self.N()),
                src=self.S, dest=self.I)
        self.Fir = pcm.Flow(
                lambda: rng.binomial(self.I(), self.g()),
                src=self.I, dest=self.R)

        # Output
        self.set_output('S','I','R')


m2 = MonteCarloSIR()
```

The first lines, above, import numpy and initialize its random number generator (RNG). We now specify the transmission rate with two parameters, a mean value *b_m* and a standard deviation *b_s*. Then we create the transmission rate *b* as a PyCoMod *Sample*, defined by a lambda function that calls numpy's normal RNG, passing *b_m* and *b_s* as parameters. This will resample the transmission rate from the normal distribution at the start of each model run.

The flow *Fsi* has been updated such that, rather than being a deterministic rate, each susceptible person has a probability of remaining susceptible or being infected based on the number of infected people in the population and the transmission rate. Therefore, we use the binomial RNG to generate a discrete, random number of new infections that will move from the susceptible population to the infectious population: `rng.binomial(self.S(), self.b()*self.I()/self.N())`. The flow *Fir* has similarly been updated such that each infected person has a probability of recovering (or not) in each time step, again using the binomial RNG to generate a discrete, random number of people to move from the infectious population to the recovered population.

Lastly, we create an instance of the new model and call it *m2*. These modifications produce the same average behavior as the deterministic model, but introduce variability based on the uncertainty in the transmission rate and the randomness of transmission events.

We can now run the model in Monte Carlo mode using the run manager's *run_mc* method, passing the number of replications (reps) in the run settings, and giving the run a new label.

```Python
mgr.run_mc(m2, duration=150, reps=100, label='My run - mc')
```

We can plot the results of a Monte Carlo run using the plotter's *plot_mc* function. The optional *interval* parameter specifies the percentile range from the distribution of outputs to be displayed. An interval of 50 means the middle 50% of the distribution, or the inter-quartile range. An interval of 90 would display the region from the 5th to 95th percentile.

```Python
plt = pcm.Plotter(title='SIR Time Series - Monte Carlo', ylabel='Population',
                  fontsize=14)
plt.plot_mc(mgr['My run - mc'], 'S', color='blue', interval=50, label='S')
plt.plot_mc(mgr['My run - mc'], 'I', color='orange', interval=50, label='I')
plt.plot_mc(mgr['My run - mc'], 'R', color='green', interval=50, label='R')
plt.plot_mc(mgr['My run - mc'], 'S + I + R', color='black', interval=50,
            label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/125520231-accec0af-5762-4c4e-9002-7b179df6089f.png)


## Nested models and model initialization

PyCoMod models support nesting, so any PyCoMod model can be used as an element inside another model. For example, if we have two sub-populations with different transmission dynamics and a certain degree of mixing between them, we can create a new model, *MixSIR*, that contains two instances of the *MonteCarloSIR* model defined previously.

```Python
class MixSIR(pcm.Model):

    def build(self):

        # Sub models
        self.GrpA = MonteCarloSIR()
        self.GrpB = MonteCarloSIR()

        # Transmission parameter between groups
        self.b_mix = pcm.Parameter()

        # Cross-infection flows
        self.Fsi_GrpA = pcm.Flow(
                lambda: rng.binomial(self.GrpA.S(),
                                     self.b_mix() * self.GrpB.I()
                                                  / self.GrpB.N()),
                src=self.GrpA.S, dest=self.GrpA.I)
        self.Fsi_GrpB = pcm.Flow(
                lambda: rng.binomial(self.GrpB.S(),
                                     self.b_mix() * self.GrpA.I()
                                                  / self.GrpA.N()),
                src=self.GrpB.S, dest=self.GrpB.I)

        # Output
        self.set_output('GrpA','GrpB')


m3 = MixSIR()
```

In the code above, the two sub-populations, *GrpA* and *GrpB*, are both defined as instances of the *MonteCarloSIR* model. Each group behaves internally as before according to its parameters and initial conditions, but we introduce the possibility of cross-infection between these groups. The cross-infections occur with a different transmission rate, *b_mix*, defined as a parameter in the *MixSIR* model and initialized below. The cross-infection flows result in new infections within each group caused by the infectious population in the other group. Note that in order to save the output from a sub-model, the sub-model must be listed in the parent model's output list: `self.set_output('GrpA','GrpB')`; then all elements of the sub-model will be accessible when plotting.

While *GrpA* and *GrpB* are the same model, we will supply them with different parameter values and initial conditions. Previously, we specified these values while defining the model, but it is often preferable to separate model inputs from the model itself. Therefore, we can supply the inputs for the model at run-time using a Python dictionary. For the *MixSIR* model, above, the initialization dictionary would look something like *init* below.

```Python
init_GrpA = {'S': 95, 'I': 5, 'R': 0, 'b_m': 0.2, 'b_s': 0.05, 'g': 0.1}
init_GrpB = {'S': 30, 'I': 0, 'R': 0, 'b_m': 0.3, 'b_s': 0.05, 'g': 0.1}
init_model = {'b_mix': 0.05, 'GrpA': init_GrpA, 'GrpB': init_GrpB}
init_run = {'reps': 100, 'end': 150}
init = {'run':init_run, 'model':init_model}
```

The initialization dictionary consists of two entries: *run* contains a dictionary of run inputs, and *model* contains a dictionary of model inputs. In this case, the supplied run inputs are *reps* and *end*. The model parameters dictionary contains keys corresponding to the names of the model elements, and values to be used to initialize that element. The only model elements that accept input are pools, parameters, and sub-models. The entry value for a pool is the initial population of the pool. The entry value for a parameter is the parameter's value which is a constant. To initialize a sub-model, such as *GrpA* above, the entry value is another dictionary designed to initialize the sub-model, `init_GrpA = {'S': 95, 'I': 5, 'R': 0, 'b_m': 0.2, 'b_s': 0.05, 'g': 0.1}`. Hence, nested models are initialized with equivalently nested dictionaries. In this example, *GrpA* is given the same initialization values as in the *MonteCarloSIR* model while *GrpB* is a smaller population (size 30) with a higher mean transmission rate, but with no initial infections.

We can then execute a run using the dictionary to initialize the model.

```Python
mgr.run_mc(m3, init=init, label='My run - mix')
```

And we can then plot what happens to *GrpA*.

```Python
plt = pcm.Plotter(title='SIR Time Series - Monte Carlo - GrpA',
                  ylabel='Population', fontsize=14)
plt.plot_mc(mgr['My run - mix'], 'GrpA.S', color='blue',
            interval=50, label='S')
plt.plot_mc(mgr['My run - mix'], 'GrpA.I', color='orange',
            interval=50, label='I')
plt.plot_mc(mgr['My run - mix'], 'GrpA.R', color='green',
            interval=50, label='R')
plt.plot_mc(mgr['My run - mix'], 'GrpA.S + GrpA.I + GrpA.R', color='black',
            interval=50, label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/125534046-615c52ce-7740-432c-ac19-3d233a9dda32.png)

And *GrpB*.

```Python
plt = pcm.Plotter(title='SIR Time Series - Monte Carlo - GrpB',
                  ylabel='Population', fontsize=14)
plt.plot_mc(mgr['My run - mix'], 'GrpB.S', color='blue',
            interval=50, label='S')
plt.plot_mc(mgr['My run - mix'], 'GrpB.I', color='orange',
            interval=50, label='I')
plt.plot_mc(mgr['My run - mix'], 'GrpB.R', color='green',
            interval=50, label='R')
plt.plot_mc(mgr['My run - mix'], 'GrpB.S + GrpB.I + GrpB.R', color='black',
            interval=50, label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/125534082-e84971f1-3436-4dda-b431-31ae293f42ba.png)

Note in the above code that to specify the output we want to plot in a nested model, we use dot-notation to navigate the sub-models. E.g. *GrpB.S* plots the susceptible population within *GrpB*.

### Initialization files

Initialization dictionaries are useful when we want to set up the model in Python code, but it is often practical to contain the initialization data in a file. This allows different model setups to be saved and edited by hand. For this purpose, PyCoMod models can also be initialized from an Excel file. The Excel file template to initialize a particular model can be generated by the model itself by calling *write_excel_init* and providing a file name.

```Python
m3.write_excel_init('init_mix.xlsx')
```

In Google Colab, the initialization file will be written to the temporary session storage and can be downloaded, modified and re-uploaded. In a local Python environment, the file is written to local storage.

The Excel initialization file is structured in a similar way to the initialization dictionary. The first tab contains run inputs, the second tab contains the top-level model inputs, and subsequent tabs contain sub-model inputs if sub-models are present. In this case, there are four tabs.

![excel_tabs](https://user-images.githubusercontent.com/86741975/217639740-53b8d062-1c24-4f05-8e7f-2ffd29ac68a0.PNG)

The *run* tab always consist of the following settings:
 - *t* - the initial simulation time (usually 0)
 - *date* - the initial simulation date
 - *dt* - the simulation time step
 - *end* - the simulation end time
 - *reps* - the number of replications for Monte Carlo runs

![run_inputs](https://user-images.githubusercontent.com/86741975/217640283-c0d11c44-e805-4133-ad23-3f7192ce3de2.PNG)

The *model* tab contains the initialization inputs for the elements of the top-level model. In this case, they are *GrpA*, *GrpB*, and *b_mix*.

![model_inputs](https://user-images.githubusercontent.com/86741975/217640524-24f560a6-34b4-4f13-a1ca-ac50112aaec5.PNG)

We can edit the value for the *b_mix* parameter here to affect the rate of cross infections between the two groups.

Because *GrpA* and *GrpB* are sub-models, the value under these labels is the name of the tab that contains the initialization data for that sub-model. So under *GrpA*, the value is *model.GrpA* which is the name of the third tab. It should not be necessary to change the sheet name entry under a sub-model. In the *model.GrpA* tab we find the inputs for the elements of the *GrpA* sub-model: *S*, *I*, *R*, *b_m*, *b_s*, and *g*.

![image](https://user-images.githubusercontent.com/86741975/219801517-87655834-f26e-4d0a-920c-f944dcb7f607.png)

The same applies to the *GrpB* sub-model. Each tab also contains an *out* entry which is used to list the outputs for the model or sub-model. This has the same function as calling *set_output* within the model definition. Recall that the outputs of a sub-model will only be saved if the parent model includes the sub-model in its output list. 

We can edit the values in the Excel file, for example, by changing b_mix to 0.025 (cutting the transmission rate between the two populations in half) and then save it.

In Google Colab, we then have to upload the edited file to session storage.

Now we can run the model using the Excel file to initialize it.

```Python
mgr.run_mc(m3, init='init_mix.xlsx', label='My run - mix - xls')
```

Viewing the run output is the same as before.


## Dynamic model parameters
It is often necessary to adjust model parameters over time. In general this can be accomplished using PyCoMod equations. For example, we might want to modify the *SimpleSIR* model to make the transmission rate decay over time, reflecting increasing adherence to public health measures. So we could replace the parameter *b* with an equation implementing an exponential decay.

```Python
class ModSIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool(95)
        self.I = pcm.Pool(5)
        self.R = pcm.Pool(0)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Parameters
        self.b = pcm.Equation(lambda: 0.2 * (0.98)**self.t())
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(lambda: self.b() * self.I() * self.S() / self.N(),
                            src=self.S, dest=self.I)
        self.Fir = pcm.Flow(lambda: self.g() * self.I(),
                            src=self.I, dest=self.R)

        # Output
        self.set_output('S', 'I', 'R', 'b')


m4 = ModSIR()
```

Note that the current simulation time can be accessed by calling the special variable *self.t*. We can view the modified transmission rate over time by adding *b* to the list of outputs, running the model and then plotting it.

```Python
mgr.run(m4, duration=150, label='Mod SIR')

plt = pcm.Plotter(title='Dynamic transmission rate',
                  ylabel='Value', fontsize=14)
plt.plot(mgr['Mod SIR'], 'b', color='blue', label='Transmission rate')
```

![image](https://user-images.githubusercontent.com/86741975/126204950-020d616b-22a4-45b7-94fd-88c2fcbd1108.png)


Sometimes we want a parameter to change to specific values at specific times, in other words, a step function. It is possible to implement a step function as a PyCoMod equation, but this is not trivial. As this is is a common requirement in modelling and simulation, PyCoMod provides a built-in equation sub-class called *step*. For example, we can change the *ModSIR* model such that the transmission rate increases and decreases at certain times, reflecting specific measures coming into and out of force.


```Python
self.b = pcm.Step([0.2, 0.13, 0.2], [0, 7, 21])
```

When initializing the PyCoMod *step* object, we provide a list of values and a corresponding list of times. In this case, the transmission rate is initially 0.2 at time 0, it then reduces to to 0.13 on day 7 for a period of two weeks, after which it returns to 0.2. Note that the default time unit in PyCoMod is 1 day.

![image](https://user-images.githubusercontent.com/86741975/126210132-60da1f39-f562-494c-8282-a25a3783157e.png)


In the above examples, the numerical constants used to define *b* could be replaced with PyCoMod parameters which would register them as model inputs allowing them to be adjusted via an initialization dictionary or initialization file. This is the advantage of using parameters rather than literals in a model.

In the case of the *step* function, we need two vectors, and PyCoMod parameters support vector inputs. So we can create a parameter *b_v* for the values of the transmission rate, and a parameter *b_t* for the times at which they will be applied.


```Python
self.b_v = pcm.Parameter([0.2, 0.13, 0.2])
self.b_t = pcm.Parameter([0, 7, 21])
self.b = pcm.Step(self.b_v(), self.b_t())
```
The initialization dictionary for this model would then specify lists for the values of *b_v* and *b_t*.

```Python
init_mod = {'S': 95, 'I': 5, 'R': 0, 'b_v': [0.2, 0.13, 0.2],
            'b_t': [0, 7, 21], 'g': 0.1}
```

If we create an Excel initialization file for this model, we will see two vector inputs for the parameters *b_v* and *b_t*.

![image](https://user-images.githubusercontent.com/86741975/126209560-0027f6d4-5b18-4a6f-bd08-062a64975d36.png)

Whichever method is used, we can now edit the timing and magnitude of changes to the transmission rate. The size of the vector is not restricted to the initial dimension of three in this example. More values and times can be added so long as there is always a corresponding time for each value.

The PyCoMod *impluse* is another type of dynamic value similar to *step*. Impulse generates specified values at specified times, but only at those times. In other words the impulse value is held only for the timestep that contains the impulse time, otherwise it returns 0 or an optional default value. For example, the transmission rate in our model could be 0.2 under normal circumstances, but on certain dates there may be events that are expected to result in elevated transmission.


```Python
self.b = pcm.Impulse([0.5, 0.5, 0.5], [10, 25, 45], 0.2)
```

When initializing a PyCoMod *impulse* object, we provide a list of impulse values, a list of impulse times, and an optional default value. In this case, it produces an elevated transmission rate of 0.5 on days 10, 25 and 45, but it otherwise produces the nominal rate of 0.2.

![image](https://user-images.githubusercontent.com/86741975/126553442-feb00813-bec3-44f7-a5f2-fbbbef562e5a.png)

The same approach as described above can be used to set these values using an initialization dictionary or Excel file.



## Initial flows

In some cases, it may be useful to incorporate flows into establishing the initial state of the system. For example, we may not know that there are exactly 5 initial infections in the population, as in the preceding examples. Instead, we may only know that there is a 5% chance that any given person is infected, based on some larger population statistics. To model this situation, we can place the entire population in the S compartment, and use a stochastic initial flow to move a random number of them to the infectious compartment based on aforementioned 5% probability.


```Python
class MonteCarloSIR2(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool(100)
        self.I = pcm.Pool(0)
        self.R = pcm.Pool(0)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Transmission rate parameters
        self.b_m = pcm.Parameter(0.2)
        self.b_s = pcm.Parameter(0.05)

        # Transmission rate random sample
        self.b = pcm.Sample(lambda: rng.normal(self.b_m(), self.b_s()))

        # Recovery rate parameter
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(
                lambda: rng.binomial(self.S(), 
                                     self.b() * self.I() / self.N()),
                src=self.S, dest=self.I)
        self.Fir = pcm.Flow(
                lambda: rng.binomial(self.I(), self.g()),
                src=self.I, dest=self.R)

        # Initial flow
        self.Pi = pcm.Parameter(0.05)
        self.Fsi_init = pcm.Flow(lambda: rng.binomial(self.S(), self.Pi()),
                                 src=self.S, dest=self.I, init=True)

        # Output
        self.set_output('S','I','R')


m5 = MonteCarloSIR2()
```

In the above code, note that the S pool is initialized to contain the whole population, and I and R are empty. Toward the end of the model definition, we have added a parameter *Pi*, for the 5% probability of initial infection, and the initial flow *Fsi_init*. This flow uses a binomial RNG to move a random number of individuals from S to I using the probability *Pi*. To flag this flow as an initial flow, we set the optional *init* parameter to *True*. This flow will now only be executed once at the start of each run.

If we run this model, we can see that the initial state of the system is now uncertain, and there is more variability in the outcome compared to the first *MonteCarloSIR* model.

```Python
mgr.run_mc(m5, duration=150, reps=100, label='My run - mc2')

plt = pcm.Plotter(title='SIR Time Series - Monte Carlo',
                  ylabel='Population', fontsize=14)
plt.plot_mc(mgr['My run - mc2'], 'S', color='blue',
                interval=50, label='S')
plt.plot_mc(mgr['My run - mc2'], 'I', color='orange',
                interval=50, label='I')
plt.plot_mc(mgr['My run - mc2'], 'R', color='green',
                interval=50, label='R')
plt.plot_mc(mgr['My run - mc2'], 'S + I + R', color='black',
                interval=50, label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/126559095-829eb933-08dc-442d-8e4e-60278e04e676.png)


# Vectorization
In PyCoMod, the values held by model elements can be vectors. As with vector parameters introduced previously, all vectors can be initialized with a list of values and are stored internally as [numpy](https://numpy.org/) arrays. This means that many mathemetical operations are seemlessly compatible with vector values. Numpy's RNG functions are also compatible with vector input. In many cases a model developed for scalar values will be compatible with vector values with little or no changes. This feature is useful for modelling multiple isolated or semi-isolated populations in parallel, such as a training setting in which students are divided into parallel cohorts. Note that a familiarity with how [numpy](https://numpy.org/) handles vectors in mathematical expressions is necessary to build vectorized models.

For example, we can vectorize the *MonteCarloSIR2* model from the previous section simply by changing the pool initial values to lists. In this case, the susceptible population is initialized to 10 cohorts of 10 people, and the infectious and recovered populations are initialized to 10 empty cohorts each. Note that the S, I and R pools must all have the same number of cohorts. The rest of model implicitly accomodates the vectorized populations. So rather than a single SIR model of 100 people, we have 10 parallel SIR models of 10 people each.

```Python
class VecSIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool([10] * 10)
        self.I = pcm.Pool([0] * 10)
        self.R = pcm.Pool([0] * 10)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Transmission rate parameters
        self.b_m = pcm.Parameter(0.2)
        self.b_s = pcm.Parameter(0.05)

        # Transmission rate random sample
        self.b = pcm.Sample(lambda: rng.normal(self.b_m(), self.b_s()))

        # Recovery rate parameter
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(
                lambda: rng.binomial(self.S(), self.b() * self.I() / self.N()),
                src=self.S, dest=self.I)
        self.Fir = pcm.Flow(
                lambda: rng.binomial(self.I(), self.g()),
                src=self.I, dest=self.R)

        # Initial flow
        self.Pi = pcm.Parameter(0.05)
        self.Fsi_init = pcm.Flow(lambda: rng.binomial(self.S(), self.Pi()),
                                 src=self.S, dest=self.I, init=True)

        # Output
        self.set_output('S','I','R')


m6 = VecSIR()
```

If we plot the result, we can see the protective effect of dividing the population into isolated cohorts. Note that when we plot a model output that is vectorized, the sum of the vector is shown on the figure.

```Python
mgr.run_mc(m6, duration=150, reps=100, label='My run - vec')

plt = pcm.Plotter(title='SIR Time Series - Monte Carlo',
                  ylabel='Population', fontsize=14)
plt.plot_mc(mgr['My run - vec'], 'S', color='blue',
            interval=50, label='S')
plt.plot_mc(mgr['My run - vec'], 'I', color='orange',
            interval=50, label='I')
plt.plot_mc(mgr['My run - vec'], 'R', color='green',
            interval=50, label='R')
plt.plot_mc(mgr['My run - vec'], 'S + I + R', color='black',
            interval=50, label='Total')
```

![image](https://user-images.githubusercontent.com/86741975/126799974-76c533de-726e-4569-9e7b-e32c3717a3ac.png)

However, it is usually not realistic to assume that populations are perfectly isolated, so we can introduce a potential for spread between cohorts. At the end of the model definition, we add the parameter *b_mix* which is the smaller rate of transmission between cohorts (one tenth the nominal transmission rate within cohorts), and we add the flow *Fsi_mix* which creates new infections within each cohort as a result of mixing between cohorts. When a susceptible person is in a mixed setting (e.g. a hallway where cohorts share the same space), the probability that they encounter an infectious person is given by the total proportion of infectious people, hense the modified term *self.I().sum()/self.N().sum()* appears in the flow equation. The addition of *.sum()* returns the sum of the vector, in other words, the sum across the cohorts.

```Python
class VecSIR(pcm.Model):

    def build(self):
        # Pools
        self.S = pcm.Pool([10] * 10)
        self.I = pcm.Pool([0] * 10)
        self.R = pcm.Pool([0] * 10)

        # Equations
        self.N = pcm.Equation(lambda: self.S() + self.I() + self.R())

        # Transmission rate parameters
        self.b_m = pcm.Parameter(0.2)
        self.b_s = pcm.Parameter(0.05)

        # Transmission rate random sample
        self.b = pcm.Sample(lambda: rng.normal(self.b_m(), self.b_s()))

        # Recovery rate parameter
        self.g = pcm.Parameter(0.1)

        # Flows
        self.Fsi = pcm.Flow(
                lambda: rng.binomial(self.S(), self.b() * self.I() / self.N()),
                src=self.S, dest=self.I)
        self.Fir = pcm.Flow(
                lambda: rng.binomial(self.I(), self.g()),
                src=self.I, dest=self.R)

        # Initial flow
        self.Pi = pcm.Parameter(0.05)
        self.Fsi_init = pcm.Flow(lambda: rng.binomial(self.S(), self.Pi()),
                                 src=self.S, dest=self.I, init=True)

        # Mixing
        self.b_mix = pcm.Parameter(0.02)
        self.Fsi_mix = pcm.Flow(
                lambda: rng.binomial(self.S(),
                                     self.b_mix() * self.I().sum()
                                                  / self.N().sum()),
                src=self.S, dest=self.I)

        # Output
        self.set_output('S','I','R')


m6 = VecSIR()
```

If we plot the output, we can see the effect of the limited degree of mixing between cohorts.

![image](https://user-images.githubusercontent.com/86741975/126808083-e8e14f63-fb70-4954-b5c4-a2ae71675b49.png)






<!--

# Execution order


# Common pitfalls

In some cases, compartment models can experience unexpected errors caused by multiple flows exiting the same pool, especially if one or more of the flows is relatively large. For example, imagine that a certain number of people will be vaccinated on certain date. A very simple way to model this is to add a new flow that moves the specified number of people from S to R on that date. However, it is possible that the sum of the vaccination flow (from S to R) and the regular infection flow (from S to I) will exceed the total population in the susceptible pool. This will cause the S pool to have a negative value, and the total population in I and R will exceed the initial total population in the model.

Multinomial distribution as alternate fix.

-->










