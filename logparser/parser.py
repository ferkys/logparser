import time
import click
import dask.dataframe as dd
from distributed import Client

from . import config
from . import makefake as mf


HELP_TAIL = 'Never end execution. Launch report each N seconds (--sleep-seconds option).'
HELP_FOLDER = 'Looks for a pattern inside a folder, print report, and terminate execution.'
HELP_SECONDS = 'Number of seconds to look back for connections in the past. Default = 3600 (1 hour).'
HELP_SLEEP_SECONDS = 'Applies to "--tail" mode. Number of seconds to re-execute the report. Default = 3600 (1 hour).'
HELP_GROUPING_SECONDS = (
        'The process calculate aggregates as an intermediate calculation. Specified the period length '
        'for the aggregation'
)


@click.command()
@click.option('--tail', 'mode', flag_value='tail', default=False, help=HELP_TAIL)
@click.option('--folder', 'mode', flag_value='folder', default=True, help=HELP_FOLDER)
@click.option('--seconds', default=3600, help=HELP_SECONDS)
@click.option('--grouping-seconds', default=1200, help=HELP_GROUPING_SECONDS)
@click.option('--sleep-seconds', default=3600, help=HELP_SLEEP_SECONDS)
@click.argument('location', nargs=1)
@click.argument('host-from', nargs=1)
@click.argument('host-to', nargs=1)
def parser(mode, seconds, grouping_seconds, sleep_seconds, location, host_from, host_to):
    '''
    Looks for files matching an specified pattern LOCATION, parse them and print:


     - Server that received maximum number of connections.


     - Number of connections generated from HOST_FROM.

     - Number of connections received from HOST_TO.


     Sample execution:

     logparser --tail '/tmp/connections*.log' sierra Delta
    '''
    timestamp_now = int(time.time())
    client = Client()

    config.set_option('logparser.host_from', host_from)
    config.set_option('logparser.host_to', host_to)
    config.set_option('logparser.timestamp_now', timestamp_now)
    config.set_option('logparser.timestamp_before', timestamp_now - seconds)
    config.set_option('logparser.seconds', seconds)
    config.set_option('logparser.grouping_seconds', grouping_seconds)
    config.set_option('logparser.location', location)

    if mode == 'folder':
        try:
            df = dd.read_csv(location, sep=' ')
            df.columns = ['ts', 'from', 'to']
            parse_log_dataframe(client, df, timestamp_now)
        except OSError as e:
            click.echo("No log files found!")

    elif mode == 'tail':
        while True:
            # first report to execute
            df = dd.read_csv(location, sep=' ')
            df.columns = ['ts', 'from', 'to']
            parse_log_dataframe(client, df, int(time.time()))
            time.sleep(sleep_seconds)

    else:
        raise("This should never happen! Unimplemented option {}".format(mode))

    client.close()

@click.command()
@click.argument('location', nargs=1)
def makefake(location):
    '''
    Generate a test file specified by LOCATION.

    Sample command:

        logparser-make /tmp/connections.4.log
    '''
    mf.make_fake_file(location)

def parse_log_dataframe(client, df, timestamp):
    '''
    Do the real work. The algorithm is something like:

    -----------
    |Big Files| filtering last N    -----------
    |         | seconds of data     | filtered |  group data      ----------
    |         | ----------------->  |  data    | ------------->   | small  |
    |         |                     |          |                  | data   | ----> calculations
    -----------                     ----------                    ----------


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
    '''
    seconds = config.get_option('logparser.seconds')
    grouping_seconds = config.get_option('logparser.grouping_seconds')
    location = config.get_option('logparser.location')
    pin_server = config.get_option('logparser.host_to')
    pin_host = config.get_option('logparser.host_from')

    # Distributed reading of log files
    ts_start = timestamp - seconds
    df = dd.read_csv(location, sep=' ')
    df.columns = ['ts', 'from', 'to']

    # First of all filter data we are not going to use
    df = df[(df.ts >= ts_start) & (df.ts <= timestamp)]

    if len(df) > 0:
        # Group data based on timestamp. Create column to group by, aggregate
        # and then keep that operations on the cluster, so we don't have to
        # repeat them for subsequent operations.
        df['grouped_ts'] = df.map_partitions(
            lambda x: (timestamp - x.ts) // grouping_seconds
        )
        df = df.groupby(['grouped_ts', 'from', 'to']).count()
        df = df.reset_index()
        df = client.persist(df)


        # Perform calculations
        list_connected_to = df[df.to == pin_server]['from'].unique().compute().tolist()
        list_connected_from = df[df['from'] == pin_host]['to'].unique().compute().tolist()
        max_connections = (
            df[['to', 'ts']].groupby('to')
               .sum()
               .reset_index()
               .map_partitions(
                lambda x: x.sort_values(by='ts', ascending=False).iloc[0]
            )
        )

        # report results
        click.echo("Report results")
        click.echo("--------------\n")
        click.echo("* Server that received more connections:")
        click.echo(max_connections.compute().to_string())
        click.echo("")
        click.echo("* List of connected hosts to {}".format(pin_server))
        click.echo("")
        click.echo(', '.join(list_connected_to))
        click.echo("")
        click.echo("* List of connections from {}".format(pin_host))
        click.echo(', '.join(list_connected_from))
    else:
        click.echo("No data in last {} seconds".format(seconds))

