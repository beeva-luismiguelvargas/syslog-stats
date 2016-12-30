#!/usr/bin/env python

from logging.handlers import SysLogHandler
import ConfigParser
import os
import time
import psutil
import logging
import socket
import json
import threading
import math
import sys


def time_in_ms():
    return long(math.floor(time.time() * 1000))


"""
    DeltaMeter provides an easy way to compute metric increments.
"""
class DeltaMeter():
    def __init__(self, init_value=0L):
        self.last_update = time_in_ms()
        self.last = long(init_value)

    def update_and_get(self, value):
        v = long(value)
        delta = abs(v - self.last)
        self.last = v
        return delta

"""
    SimpleMeter is a simple typed meter. You can use it when you need cast a string -> my_type
"""
class SimpleMeter():
    def __init__(self, _type, init_value):
        self.last_update = time_in_ms()
        self.last = _type(init_value)
        self.type = _type

    def update_and_get(self, value):
        self.last = self.type(value)
        return self.last

"""
    TaskThread is a simple thread scheduler. It's call the run method every XX seconds.
"""
class TaskThread(threading.Thread):

    def __init__(self, interval):
        threading.Thread.__init__(self)
        self.finished = threading.Event()
        self.interval = interval

    def set_interval(self, interval):
        self.interval = interval

    def shutdown(self):
        self.finished.set()

    def run(self):
        while 1:
            if self.finished.isSet():
                return
            self.task()

            # sleep for interval or until shutdown
            self.finished.wait(self.interval)

    def task(self):
        pass

"""
    AReporter is the base class for all reporters.
    It handles the following operations:
        - register the metrics
        - collect data
        - process data
        - flush every XX seconds
"""
class AReporter(TaskThread):

    def __init__(self, app_name, syslog_host, syslog_hostname, syslog_port, interval):
        super(AReporter, self).__init__(interval)
        self.app_name = app_name
        self.syslog_host = syslog_host
        self.syslog_port = syslog_port
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.INFO)

        f = ContextFilter()
        self.logger.addFilter(f)

        syslog = SysLogHandler(address=(self.syslog_host, self.syslog_port))
        formatter = logging.Formatter("%(asctime)s {1} {0}: %(message)s".format(self.app_name, syslog_hostname), datefmt='%b %d %H:%M:%S')
        syslog.setFormatter(formatter)

        self.logger.addHandler(syslog)

        self.measures = {}

    def prestart(self):
        self.collect()
        self.register()

    def collect(self):
        pass

    def register(self):
        pass

    def task(self):
        try:
            start = AReporter.time_in_s()
            self.collect()
            took = AReporter.time_in_s() - start

            # if collecting data is taking too long we're
            # skipping the current step and try after
            if took > self.interval:
                self.logger.error("collecting data take too long")
            else:
                data = self.process()

                if not isinstance(data, list):
                    to_push = [data]
                else:
                    to_push = data

                for d in to_push:
                    m = d
                    # m = {
                    #     "m": {
                    #         self.app_name: d
                    #     },
                    #     "message": "Report "+ (' & '.join(key for key, value in d.items())) +" metrics"
                    # }
                    # print json.dumps(m)
                    self.logger.info(json.dumps(m))

        except Exception as e:
            # raise e
            self.logger.error("Error during report processing:" + e.message)
            # reset the reporter
            self.prestart()

    @staticmethod
    def time_in_s():
        return long(math.floor(time.time()))


class SystemReporter(AReporter):

    def __init__(self, syslog_host, syslog_hostname, syslog_port, interval, paths, latitude, longitude, province, city, store):
        super(SystemReporter, self).__init__("monitoring-agent", syslog_host, syslog_hostname, syslog_port, interval)
        self.paths = paths

        # attributes
        self.io_data = None
        self.cpu_percent_data = None
        self.paths_data = None
        self.mem_virtual_data = None
        self.mem_swap_data = None
        self.io_disk_data = None
        self.process_data = None
        self.latitude_data = latitude
        self.longitude_data = longitude
        self.province_data = province
        self.city_data = city
        self.store_data = store

    def register(self):
        super(SystemReporter, self).register()
        network_interfaces = [ni for ni in psutil.net_io_counters(pernic=True)]
        for network_interface in network_interfaces:
            self.measures[network_interface + ".bytes_sent"]   = DeltaMeter(self.io_data[network_interface].bytes_sent)
            self.measures[network_interface + ".bytes_recv"]   = DeltaMeter(self.io_data[network_interface].bytes_recv)
            self.measures[network_interface + ".packets_sent"] = DeltaMeter(self.io_data[network_interface].packets_sent)
            self.measures[network_interface + ".packets_recv"] = DeltaMeter(self.io_data[network_interface].packets_recv)
            self.measures[network_interface + ".errin"]        = DeltaMeter(self.io_data[network_interface].errin)
            self.measures[network_interface + ".errout"]       = DeltaMeter(self.io_data[network_interface].errout)
            self.measures[network_interface + ".dropin"]       = DeltaMeter(self.io_data[network_interface].dropin)
            self.measures[network_interface + ".dropout"]      = DeltaMeter(self.io_data[network_interface].dropout)

        self.measures["cpu"]                   = SimpleMeter(float, self.cpu_percent_data)
        self.measures["mem.virtual.total"]     = SimpleMeter(long, self.mem_virtual_data.total)
        self.measures["mem.virtual.available"] = SimpleMeter(long, self.mem_virtual_data.available)
        self.measures["mem.virtual.percent"]   = SimpleMeter(float, self.mem_virtual_data.percent)
        self.measures["mem.virtual.used"]      = SimpleMeter(long, self.mem_virtual_data.used)
        self.measures["mem.virtual.free"]      = SimpleMeter(long, self.mem_virtual_data.free)
        self.measures["mem.virtual.active"]    = SimpleMeter(long, self.mem_virtual_data.active)
        self.measures["mem.virtual.inactive"]  = SimpleMeter(long, self.mem_virtual_data.inactive)
        self.measures["mem.virtual.buffers"]   = SimpleMeter(long, self.mem_virtual_data.buffers)
        self.measures["mem.virtual.cached"]    = SimpleMeter(long, self.mem_virtual_data.cached)
        self.measures["mem.swap.total"]        = SimpleMeter(long, self.mem_swap_data.total)
        self.measures["mem.swap.used"]         = SimpleMeter(long, self.mem_swap_data.used)
        self.measures["mem.swap.free"]         = SimpleMeter(long, self.mem_swap_data.free)
        self.measures["mem.swap.percent"]      = SimpleMeter(float, self.mem_swap_data.percent)
        self.measures["mem.swap.sin"]          = SimpleMeter(long, self.mem_swap_data.sin)
        self.measures["mem.swap.sout"]         = SimpleMeter(long, self.mem_swap_data.sout)

        disks = [disk for disk in psutil.disk_io_counters(perdisk=True)]
        for disk in disks:
            self.measures[disk + ".read_count"]  = DeltaMeter(self.io_disk_data[disk].read_count)
            self.measures[disk + ".write_count"] = DeltaMeter(self.io_disk_data[disk].write_count)
            self.measures[disk + ".read_bytes"]  = DeltaMeter(self.io_disk_data[disk].read_bytes)
            self.measures[disk + ".write_bytes"] = DeltaMeter(self.io_disk_data[disk].write_bytes)
            self.measures[disk + ".read_time"]   = DeltaMeter(self.io_disk_data[disk].read_time)
            self.measures[disk + ".write_time"]  = DeltaMeter(self.io_disk_data[disk].write_time)

        for idx, path_data in enumerate(self.paths_data):
            path = self.paths[idx]
            path_name = path["name"]
            path_data = psutil.disk_usage(path["path"])
            self.measures[path_name + ".total"]   = SimpleMeter(long, path_data.total)
            self.measures[path_name + ".used"]    = SimpleMeter(long, path_data.used)
            self.measures[path_name + ".free"]    = SimpleMeter(long, path_data.free)
            self.measures[path_name + ".percent"] = SimpleMeter(float, path_data.percent)

        self.measures["process"] = SimpleMeter(int, self.process_data)

    def collect(self):
        super(SystemReporter, self).collect()
        self.io_data = psutil.net_io_counters(pernic=True)
        self.cpu_percent_data = psutil.cpu_percent(interval=None)
        self.mem_virtual_data = psutil.virtual_memory()
        self.mem_swap_data = psutil.swap_memory()
        self.paths_data = [psutil.disk_usage(p["path"]) for p in self.paths]
        self.io_disk_data = psutil.disk_io_counters(perdisk=True)
        self.process_data = len(psutil.pids())

    def process(self):
        cpu_data = self.measures["cpu"].update_and_get(self.cpu_percent_data)
        mem_data = {
            "virtual": {
                "total": self.measures["mem.virtual.total"].update_and_get(self.mem_virtual_data.total),
                "available": self.measures["mem.virtual.available"].update_and_get(self.mem_virtual_data.available),
                "percent": self.measures["mem.virtual.percent"].update_and_get(self.mem_virtual_data.percent),
                "used": self.measures["mem.virtual.used"].update_and_get(self.mem_virtual_data.used),
                "free": self.measures["mem.virtual.free"].update_and_get(self.mem_virtual_data.free),
                "active": self.measures["mem.virtual.active"].update_and_get(self.mem_virtual_data.active),
                "inactive": self.measures["mem.virtual.inactive"].update_and_get(self.mem_virtual_data.inactive),
                "buffers": self.measures["mem.virtual.buffers"].update_and_get(self.mem_virtual_data.buffers),
                "cached": self.measures["mem.virtual.cached"].update_and_get(self.mem_virtual_data.cached),
            },
            "swap": {
                "total": self.measures["mem.swap.total"].update_and_get(self.mem_swap_data.total),
                "used": self.measures["mem.swap.used"].update_and_get(self.mem_swap_data.used),
                "free": self.measures["mem.swap.free"].update_and_get(self.mem_swap_data.free),
                "percent": self.measures["mem.swap.percent"].update_and_get(self.mem_swap_data.percent),
                "sin": self.measures["mem.swap.sin"].update_and_get(self.mem_swap_data.sin),
                "sout": self.measures["mem.swap.sout"].update_and_get(self.mem_swap_data.sout),
            }
        }

        network_data = []
        for k in self.io_data:
            if k == 'enp0s25':
                network_data = [{
                    "name": k,
                    "bytes_sent": self.measures[k + ".bytes_sent"].update_and_get(
                        self.io_data[k].bytes_sent),
                    "bytes_recv": self.measures[k + ".bytes_recv"].update_and_get(
                        self.io_data[k].bytes_recv),
                    "packets_sent": self.measures[k + ".packets_sent"].update_and_get(
                        self.io_data[k].packets_sent),
                    "packets_recv": self.measures[k + ".packets_recv"].update_and_get(
                        self.io_data[k].packets_recv),
                    "errin": self.measures[k + ".errin"].update_and_get(self.io_data[k].errin),
                    "errout": self.measures[k + ".errout"].update_and_get(self.io_data[k].errout),
                    "dropin": self.measures[k + ".dropin"].update_and_get(self.io_data[k].dropin),
                    "dropout": self.measures[k + ".dropout"].update_and_get(self.io_data[k].dropout),
                }]

        paths = []
        for idx, p in enumerate(self.paths):
            current_path = self.paths[idx]
            current_path_data = self.paths_data[idx]

            path_name = current_path["name"]
            path = current_path["path"]
            paths.append({
                "name"   : path_name,
                "path"   : path,
                "total"  : self.measures[path_name + ".total"].update_and_get(current_path_data.total),
                "used"   : self.measures[path_name + ".used"].update_and_get(current_path_data.used),
                "free"   : self.measures[path_name + ".free"].update_and_get(current_path_data.free),
                "percent": self.measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            })

        io_disks = []
        for k in self.io_disk_data:
            if k == 'sda6':
                io_disks = [{
                    "disk_id"    : k,
                    "read_count" : self.measures[k + ".read_count"].update_and_get(self.io_disk_data[k].read_count),
                    "write_count": self.measures[k + ".write_count"].update_and_get(self.io_disk_data[k].write_count),
                    "read_bytes" : self.measures[k + ".read_bytes"].update_and_get(self.io_disk_data[k].read_bytes),
                    "write_bytes": self.measures[k + ".write_bytes"].update_and_get(self.io_disk_data[k].write_bytes),
                    "read_time"  : self.measures[k + ".read_time"].update_and_get(self.io_disk_data[k].read_time),
                    "write_time" : self.measures[k + ".write_time"].update_and_get(self.io_disk_data[k].write_time)
                }]

        process_total = self.measures["process"].update_and_get(self.process_data)

        latitude = self.latitude_data
        longitude = self.longitude_data

        province = self.province_data
        city = self.city_data
        store = self.store_data

        location = "{},{}".format(latitude, longitude)

        io_disk = io_disks.pop()
        ndata = network_data.pop()
        path1 = paths.pop()
        path2 = paths.pop()
        path3 = paths.pop()

        messages = []
        messages.append({
            "cpu": cpu_data,
            "mem": mem_data,
            "disk": path1,
            "disk": path2,
            "disk": path3,
            "io_disk": io_disk,
            "network": ndata,
            "processes": process_total,
            "location": location,
            "province": province,
            "city": city,
            "store": store
        })

        # for io_disk in io_disks:
        #     messages.append({"io_disk": io_disk})
        #
        # for path in paths:
        #     messages.append({"disk": path})
        #
        # for ndata in network_data:
        #     messages.append({"network": ndata})

        return messages


class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

#########################################
def main(argv):
    print "Starting the monitoring agent..."

    current_path = os.path.dirname(os.path.realpath(__file__))

    main_config = ConfigParser.RawConfigParser()
    if len(argv) == 2:
        main_config.read(current_path + '/perfstats-to-syslog{}.cfg'.format(argv[1]))
    else:
        main_config.read(current_path + '/perfstats-to-syslog.cfg')

    syslog_host = main_config.get('syslog', 'host')
    syslog_hostname = main_config.get('syslog', 'hostname')
    syslog_port = main_config.getint('syslog', 'port')
    interval_in_sec = main_config.getint('syslog', 'pollingInSec')
    latitude = main_config.get('general', 'latitude')
    longitude = main_config.get('general', 'longitude')
    province = main_config.get('general', 'province')
    city = main_config.get('general', 'city')
    store = main_config.get('general', 'store')

    paths = []
    reporters = []
    if main_config.has_option("general", "paths"):
        for p in main_config.get('general', 'paths').split(","):
            parts = p.split(":")
            name = parts[0]
            path = parts[1]
            paths.append({"name": name, "path": path})

    reporters.append(SystemReporter(syslog_host, syslog_hostname, syslog_port, interval_in_sec, paths, latitude, longitude, province, city, store))

    for reporter in reporters:
        reporter.daemon = True
        reporter.prestart()
        reporter.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv)
