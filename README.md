# Hpguppi_pypeline

Hpguppi_pypeline aims to provide a framework for pipelining the execution of
modular Python scripts, enabling the creation of a custom post-processing pipeline
for the data captured by a hashpipe ([hpguppi_daq](https://github.com/realtimeradio/hpguppi_daq))
instance. The pipeline typically consists of consequetive process calls handled by Python
script 'modules', but each stage's Python script could be standalone and not execute any
process calls.

## Approach

The hpguppi_pypeline is governed by key-value pairs within a [redis hash](https://redislabs.com/ebook/part-1-getting-started/chapter-1-getting-to-know-redis/1-2-what-redis-data-structures-look-like/1-2-4-hashes-in-redis/).
Currently this hash matches the one generated by an [hpguppi_redis_gateway](https://github.com/david-macmahon/rb-hashpipe/tree/master/bin)
instance:
`hashpipe://${hostname}/${instanceID}/`

The post-processing pipeline starts processing the data captured by a hashpipe instance
when the DAQSTATE key's value transitions from 'recording' to anything else.
The stages in the pipeline are determined by the names listed in the POSTPROC key's value.
At each stage, the `run()` is called from a python script with a filename related to 
the stage's name, as listed in the POSTPROC key's value. An artificial stage is inferred
for the hpguppi RAW acquisition with the name `hpguppi`.

The python script for a stage is able to provide the names of 3 keys whose values will be
pre-processed and passed as argument's to its `run()`: a key for INPUTS, ARGUMENTS
and ENVIRONMENT variables. Because the values of keys are just strings, they are
preprocessed by the primary __pypeline__ script and keywords in the strings are replaced
with dynamic values. In this way the inputs of a stage's `run()` can be the outputs
of a previous stage's `run()`: for instance an INPUT key with the value of `hpguppi`
would be pre-processed to replace `hpguppi` with the single filepath (sans `%d{4}.raw`)
of the latest RAW file recorded (which is the output of the artificial `hpguppi` stage).
The primary script also holds some static values which can be received by each stage's
`run()`.

The INPUT and ARGUMENT keys's values can be comma delimited to provide a number of inputs
that must be `run()` for the related stage. The INPUT/ARGUMENT permutations of each
stage are exhausted by the primary __pypeline__ script.

At the end of each stage the primary stage moves on to the next stage if there is another
listed in the POSTPROC key's value, otherwise it rewinds up the list of stages to the
last stage with an input/argument permutation that has not been processed.

Stages can produce more than one output (each `run()` must return a list). The 
permutations of a stage's input argument is exhaustive combination of the INPUT's
references to stages' outputs.

Of course, it may be desired that a stage's list of outputs is input all at once, instead
of sequentially. To this end, and a few other ends, there are syntactical markers on the
keywords within INPUT values that adjust the pre-processing applied.

## Post-processing Pipeline Stages (POSTPROC)

The value of the POSTPROC key space delimits the list of stage-scripts that make up the
post-processing pipeline. Each stage's name listed names the `postproc_stagename.py` script
to be loaded from the directory of the primary `hpguppi_pypeline.py` script.

## Stage Requirements

> An artificial stage is inferred for the hpguppi RAW acquisition with the name 
> `hpguppi`. Its output is the single filepath (sans `%d{4}.raw`) of the
> latest RAW file recorded

Each stage's script is expected to have a `run()` with the following declaration, as
well as the following 4 variables:

```
def run(arg::str, input::list, env::str):
	return outputs::list
```

- PROC_ARG_KEY 	: names the key whose value determine the 1st argument for `run()`
- PROC_INP_KEY 	: names the key whose value determine the 2nd argument for `run()`
- PROC_ENV_KEY 	: names the key whose value determine the 3rd argument for `run()`
- PROC_NAME 		: the display name of the stage

## INPUT Keywords and Modifiers

The values of INPUT keys are preprocessed for the names of previous stages, which are the
only keywords processed. It is assumed that each word (sequence of characters surrounded 
by spaces) is the name of a previous stage. It is possible however, to mark a word as 
'verbatim input' by prefixing the word with `&`, in which case only the ampersand is
removed. Otherwise the occurence of a stage's name is replaced by one of that stage's 
output values (the output values are exhausted across reruns of the referencing stage). To
have that stage's name replaced by its last input, the name can be marked with a prefixed 
`^`. To have the name replaced by all of the stage's outputs (all at once), prefix the
stage's name with `*`.

- `&`: Verbatim input word
- `^`: Input of named-stage's last input
- `*`: Exhaustive input of named-stage's output

Mutliple words in the INPUT value are listed separated by spaces, and multiple input-sets
are separated by commas (`,`).

## ARGUMENT and ENVIRONMENT Keywords

Keywords within the ARGUMENT and ENVIRONMENT keys' values are surrounded by `$`, which
are replaced by values held by the primary script.

- inst: the instanceID that the script is attached to
- hnme: the hostname of the machine
- stem: the stem of the latest RAW dump
- beg: the `time.time()` value produced as DAQSTATE changed to __recording__
- end: the `time.time()` value produced as DAQSTATE changed from __recording__

Mutliple words in the ARGUMENT and ENVIRONMENT values are listed separated by spaces, and
multiple argument-sets are separated by commas (`,`).

## An Example Showcased by the Value of Modules' Keys

`hashpipe_check_status` is used to set the value of key `-k` to `-s`.

Specify the 'postproc_*' names of the modules to be run in the post-processing, in order
	- `hashpipe_check_status -k POSTPROC -s "rawspec turboseti plotter"`

Specify that the input of rawspec (RWS) is the output of hpguppi
	- `hashpipe_check_status -k PPRWSINP -s "hpguppi"`
Specify the environment variables of the rawspec command
	- `hashpipe_check_status -k PPRWSENV -s "CUDA_VISIBLE_DEVICES=0"`
Specify the static arguments of rawspec
	- `hashpipe_check_status -k PPRWSARG -s "-f 14560 -t 16 -S -d /mnt/buf0/rawspec"`

Specify that the input of turboSETI (TBS) is the output of rawspec
	- `hashpipe_check_status -k PPTBSINP -s "rawspec"`
Specify the environment variables of the turboSETI command
	- `hashpipe_check_status -k PPTBSENV -s "CUDA_VISIBLE_DEVICES=0"`
Specify the static arguments of turboSETI
	- `hashpipe_check_status -k PPTBSARG -s "-M 20 -o /mnt/buf0/turboseti/ -g y -p 12 -n 1440"`

Specify that the input of rawspec (RWS) is the output of turboseti and the input of turboseti
	- `hashpipe_check_status -k PPPLTINP -s "turboseti ^turboseti"`

## Development of a Bespoke Pipeline

Development starts with creating a 'stage' in a Python script `postproc_stagename.py`. Setup the names
of the keys required by creating POSTPROC_ARG/INP/ENV_KEY variables (set the value of ARG/ENV_KEY to none if
they are to be ignored). Then create the `run(argstr, inputs, envvar)` function that details the module's
process. Finally ensure that the redis hash has the necessary keys for the module, with appropriate values.

Exemplary modules exist for rawspec and turboSETI as well as some others, within this repository.