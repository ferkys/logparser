# logparser

## Install

Just clone the repo:

```bash
git clone
cd logparser
pip install . 
```

## Generate fake data

Installed with the package you should have the `logparser-make` command line utility.
This command is used to generate fake files to test the `logparser` command.

Sample use:

```bash
logparser-make /tmp/connections.1.log
logparser-make /tmp/connections.2.log
logparser-make /tmp/connections.3.log
logparser-make /tmp/connections.4.log
logparser-make /tmp/connections.5.log
```

This will generate five log files of about 286 MB each one.

## Parse logs

Installed with the package you will find the `logparser` command line utility.
It has several options and arguments you can use on the command line:

```
logparser --help
```

```
Usage: logparser [OPTIONS] LOCATION HOST_FROM HOST_TO

  Looks for files matching an specified pattern LOCATION, parse them and
  print:

   - Server that received maximum number of connections.

   - Number of connections generated from HOST_FROM.

   - Number of connections received from HOST_TO.

   Sample execution (NOTE: SINGLE QUOTE FOR LOCATION IS IMPORTANT IN THIS CASE):

   logparser --tail '/tmp/connections*.log' sierra Delta

Options:
  --tail                      Never end execution. Launch report each N
                              seconds (--sleep-seconds option).
  --folder                    Looks for a pattern inside a folder, print
                              report, and terminate execution.
  --seconds INTEGER           Number of seconds to look back for connections
                              in the past. Default = 3600 (1 hour).
  --grouping-seconds INTEGER  The process calculate aggregates as an
                              intermediate calculation. Specified the period
                              length for the aggregation
  --sleep-seconds INTEGER     Applies to "--tail" mode. Number of seconds to
                              re-execute the report. Default = 3600 (1 hour).
  --help                      Show this message and exit.
```

The output will be something like:

```bash
Report results
--------------

* Server that received more connections:
to    Uniform -> Server name
ts       1015 -> Number of connections

* List of connected hosts to Delta

almont, alpine, alta, ambassador, arden, bedford, benedict, beverley, brighton, camden, canon, chalette, clark, clifton, coldwater, cove, crescent, dabney, dayton, della, doheny, elcamino, elm, evelyn, foothill, greenacres, hartford, hillcrest, lapeer, leona, lindacrest, linden, lomavista, maple, mountain, oakhurst, oxford, palm, pamela, peck, pine, reeves, rexford, robertson, rodeo, roxbury, shadowhill, sierra, spaulding, stonewood, summit, sunset, swall, tower, wallace, wetherly

* List of connections from sierra
Alpha, Bravo, Charlie, Delta, Echo, Foxtrot, Golf, Hotel, India, Juliet, Kilo, Lima, Mike, November, Oscar, Papa, Quebec, Romeo, Sierra, Tango, Uniform, Victor, Whisky, Xray, Yankee, Zulu
```

## Processing

    Do the real work. The algorithm is something like:

    -----------
    |Big Files| filtering last N    -----------
    |         | seconds of data     | filtered |  group data      ----------
    |         | ----------------->  |  data    | ------------->   | small  |
    |         |                     |          |  on time         | data   | ----> calculations
    -----------                     ----------    intervals       ----------


    All this done through Dask (http://docs.dask.org/en/latest/), which allows to distribute
    operations on a cluster.
    In this challenge code I just use a local cluster, and tests it with 5 files of around 286 MB
    each one, all together.

    Some considerations:

    - In a production environment a real cluster should be used. I'm just playing here with multiprocessing.
    - Files should be distributed in order to get maximum performance.
    - I'm considering that the number of hosts connected to a single server that you configure on command
      line is not so high. I'm just printing the result to the screen, but would be easy to just output the
      results to files it it's too much.
    - Tested to repartition data on timestamp (almost ordered, so not big effort) and server (much more work
      and shuffle), but for this concrete report the time needed to repartition data was more that the time
      needed to get the report. Also, one of the queries needed would need a partition by host instead
      of server, so probably partitioning by timestamp is good enough.
      In a production environment I would try to have data already partitioned in
      a distributed filesystem. This would imply more time to write logs, but a lot of gain while processing
      them.
      Also tried just to make partitions based on size, but repartition cost was still too
      much.
      
    Some parameters that are specified in command line are important for the performance 
    of the process:
    
     - seconds: Number of seconds to look back for data. The default is 1 hour. More seconds,
       more processing time.
       
     - grouping-seconds: Data is aggregated in an intermediate step. More aggregation will cause
       to hold less data in the whole cluster, as I try to `persist` this grouped data in order to 
       not repeat operations.
       
## Code Modules

- `config.py`: Simple library I like to use to store parameters that will be used along the code. Avoid passing 
    more and more parameters to functions each time you need to add functionality.
- `makefake.py`: Small (and dirty) module to generate some fake data.
- `parse`: Real things happen here. Main entry code for commands. Function `parse_log_dataframe` holds all the 
   logic for parsing data.
     
## Improvements

  - Unit Testing: I usually use `pytest` or `nose`. There are no tests implemented here. Sorry, literally out of time!
  - Make a more real testing by using an hdfs docker image.
  - Also, some more options, if running in a real cluster, could be added, like:
     - Number of workers and cores to be used.
     - Maximum size for partitions (usually dask works well with 100Mb but depends on
       algorithm to be applied on it!).
  - Make a list of functions to be applied on data. In this way I would just `map` on the function list and apply each one 
    of them to data. In this way more reports could be added just by adding new functions. Functions should have all the same signature:
    ```python
    def parse_log_new_function(client, df, timestamp):
      '''
        * client: dask client. Needed if developer needs to repartition, rebalance, etc.
        * df: Read dask dataframe.
        * timestamp: The needed time reference to process data.
      '''
    ```
