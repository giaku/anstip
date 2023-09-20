from asyncio import create_task, get_event_loop, sleep, run, exceptions
import genericpath
import time
from queue import Queue
from aiohttp import ClientSession, TraceConfig, client_exceptions
import numpy as np
import configparser
import sys
import json
import random
from datetime import datetime, timedelta


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def printe(str):
    print(bcolors.FAIL + str + bcolors.ENDC)


def printw(str):
    print(bcolors.WARNING + str + bcolors.ENDC)


async def on_request_start(session, trace_config_ctx, params):
    trace_config_ctx.start = get_event_loop().time()


async def on_request_end(session, trace_config_ctx, params):
    elapsed, url, method, status_code = get_event_loop().time() - trace_config_ctx.start, str(params.url), params.method, params.response.status
    #print("{}".format(params.response))
    print("{}, {}, {}, {}, {}\n{}".format(time.time(), get_event_loop().time() - elapsed, get_event_loop().time(), elapsed, status_code, params.response))  # print data right away in the callback
    q.put([status_code, elapsed])


async def get_response(session, url, method="GET", data=None):
    # print("{}\n".format(url))
    if method.upper() != "POST":
        async with session.get(url) as resp:
            pass
    else:
        async with session.post(url, data) as resp:
            pass


def get_random_date_range(start_date, end_date, delta):
    epoch_start = start_date.timestamp()
    epoch_end = (end_date-delta).timestamp()
    # generate random number between (epoch_start) and (epoch_end-length)
    # convert random number in date and get date1
    date1 = datetime.fromtimestamp(random.randint(epoch_start, epoch_end))
    # get date2
    date2 = date1 + delta
    return "{}/{}".format(date1.strftime("%Y-%m-%d"), date2.strftime("%Y-%m-%d"))

async def main():
    headers = headers_dict
    async with ClientSession(trace_configs=[trace_config], headers=headers) as session:
        # TOTAL TIME MEASUREMENT
        start_time = get_event_loop().time()
        last = int(dim_dict["seconds"])
        distrib = dim_dict["distribution"]
        elements = additional_dict["elements"].split(",")
        min_date = additional_dict["min_date"]
        max_date = additional_dict["max_date"]
        date_format = additional_dict["date_format"]
        if (distrib.lower() != "poisson" and distrib.lower() != "uniform"):
            printe("ERROR - Unknown distribution {}".format(distrib))
            exit(1)
        stress_test_last = start_time + last
        tasks = set()
        count = 0
        print(f'"ts", "ts1", "ts2", "latency", "status"')
        op = req_dict["operation"]  # read from param if GET or POST
        base_url = req_dict["url"]  # read url from input param
        jpath = req_dict["payload"]  # eventually load json in case of http POST
        # csv_output = req_dict["csv"]  # output file for csv data UNUSED
        jcontent = None
        if op == "POST":
            jfile = open(jpath)
            jcontent = json.load(jfile)
            jfile.close()
        rps = int(dim_dict["rps"])  # read rps from input param
        while get_event_loop().time() < stress_test_last:  # replace with loop
            start_inner_loop_time = get_event_loop().time()
            element = random.choice(elements)
            date_range = get_random_date_range(datetime.strptime(min_date, date_format), datetime.strptime(max_date, date_format), timedelta(days=1))
            url = base_url + "&referencetime={}&elements={}".format(date_range, element)
            task = create_task(get_response(session, url, op, jcontent))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            if(distrib.lower() == "poisson"):
                # Poisson
                slept, count = np.random.exponential(1 / rps), count + 1
            else:
                # Uniform
                slept, count = 1 / rps, count + 1
            await sleep(slept - (get_event_loop().time() - start_inner_loop_time))
            # print(f'slept: {slept}')  # print sleeping time
        tot, succ = 0, 0
        for t in tasks:
            try:
                t.exception()
            except exceptions.InvalidStateError or client_exceptions.ServerDisconnectedError:
                pass
        while not q.empty():  # retrieve data from synchronized queue
            pair = q.get()
            q.task_done()
            # print(f'Latency: {pair[1]}, status: {pair[0]}')  # readable format
            # print(f'{pair[1]}, {pair[0]}, {op}, {url}')  # csv format
            if pair[0] == 200:
                succ += 1
            tot += pair[1]
        print(f'Avg Latency: {tot / count}, Success rate: {100 * succ / count}')
        # file.write(f'# Avg Latency: {tot / count}, Success rate: {100 * succ / count}\n')


config = configparser.RawConfigParser()
if len(sys.argv) == 1:
    printe("ERROR - Missing configuration file")
    exit(1)
elif not genericpath.isfile(sys.argv[1]):
    printe("ERROR - Impossible to read configuration file")
    exit(1)
config.read(sys.argv[1])

try:
    req_dict = dict(config.items('REQUEST'))
    dim_dict = dict(config.items('DIMENSIONS'))
    headers_dict = dict(config.items('HEADERS'))
    additional_dict = dict(config.items('ADDITIONAL'))
except configparser.NoSectionError:
    printe("ERROR - Impossible to parse configuration file")
    exit(1)
trace_config = TraceConfig()
trace_config.on_request_start.append(on_request_start)
trace_config.on_request_end.append(on_request_end)

q = Queue()
run(main())
