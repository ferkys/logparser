import os
import yaml
import time
import random
from itertools import zip_longest
from datetime import datetime


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def write_unordered_file(hosts, filename, timelist, number_elements):
    lines = (
        "{ts} {host} {server}\n".format(
            ts=random.choice(timelist),
            host=random.choice(hosts['hosts']),
            server=random.choice(hosts['servers'])
        )
        for i in range(number_elements)
    )

    with open(filename, 'a') as f:
        f.writelines(lines)


def make_fake_file(location):
    path = os.path.abspath(__file__)
    dir_path = os.path.dirname(path)

    dt = datetime.now()
    now = int(time.mktime(dt.timetuple()))
    print("from {} to {}".format(now - 7200, now))
    timerange = range(now - 7200, now)
    with open(os.path.join(dir_path, 'servers.yaml'), 'r') as f:
        hosts = yaml.load(f)

    intervals = grouper(timerange, 300)
    print("intervales: {}".format(intervals))

    for time_interval in intervals:
        write_unordered_file(hosts, location, time_interval, 500000)