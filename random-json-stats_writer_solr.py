import random
import psutil
import json
import time
import math
import sys
import os
import errno
import argparse
import datetime


JSON_FILE = 'stats.json'
HOSTNAME = 'hostname'
STORE = 0
NDATA = 10
NHOST = 1
INTERVAL = 10


parser = argparse.ArgumentParser(__file__,
                                 description="JSON document writer")

parser.add_argument("--output",
                    "-o",
                    dest="output",
                    default=JSON_FILE,
                    help="The JSON output file")

parser.add_argument("--hostname",
                    "-a",
                    dest="hostname",
                    default=HOSTNAME,
                    help="The host name")

parser.add_argument("--store",
                    "-s",
                    dest="store",
                    type=int,
                    default=STORE,
                    help="The store id: 0 - Vasconcelos (Madrid), 1 - Lloria (Valencia), 2 - Zumarkalea (Vizcaya)")

parser.add_argument("--ndata",
                    "-n",
                    dest="ndata",
                    type=int,
                    default=NDATA,
                    help="Number of documents to generate")

parser.add_argument("--nhost",
                    "-c",
                    dest="nhost",
                    type=int,
                    default=NHOST,
                    help="Number of hosts to simulate")

parser.add_argument("--interval",
                    "-i",
                    dest="interval",
                    type=int,
                    default=INTERVAL,
                    help="Interval between documents tiemstamp in seconds")


def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured


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

def main(argv):

    args = parser.parse_args()

    outfilename = 'stats.json'
    silentremove(outfilename)

    paths = []
    paths.append({"name": "root", "path": "/"})
    paths.append({"name": "opt", "path": "/opt"})
    paths.append({"name": "tmp", "path": "/tmp"})

    measures = {}

    io_data = psutil.net_io_counters(pernic=True)
    cpu_percent_data = psutil.cpu_percent(interval=None)
    cpu_times_percent_data = psutil.cpu_times_percent(interval=None)
    mem_virtual_data = psutil.virtual_memory()
    mem_swap_data = psutil.swap_memory()
    paths_data = [psutil.disk_usage(p["path"]) for p in paths]
    io_disk_data = psutil.disk_io_counters(perdisk=True)
    process_data = len(psutil.pids())

    measures["cpu"] = SimpleMeter(float, cpu_percent_data)
    measures["cpu.user"] = SimpleMeter(float, cpu_times_percent_data.user)
    measures["cpu.system"] = SimpleMeter(float, cpu_times_percent_data.system)
    measures["cpu.idle"] = SimpleMeter(float, cpu_times_percent_data.idle)
    measures["cpu.nice"] = SimpleMeter(float, cpu_times_percent_data.nice)
    measures["cpu.irq"] = SimpleMeter(float, cpu_times_percent_data.irq)
    measures["cpu.softirq"] = SimpleMeter(float, cpu_times_percent_data.softirq)
    measures["cpu.iowait"] = SimpleMeter(float, cpu_times_percent_data.iowait)
    measures["cpu.steal"] = SimpleMeter(float, cpu_times_percent_data.steal)
    measures["mem.virtual.total"] = SimpleMeter(long, mem_virtual_data.total)
    measures["mem.virtual.available"] = SimpleMeter(long, mem_virtual_data.available)
    measures["mem.virtual.percent"] = SimpleMeter(float, mem_virtual_data.percent)
    measures["mem.virtual.used"] = SimpleMeter(long, mem_virtual_data.used)
    measures["mem.virtual.free"] = SimpleMeter(long, mem_virtual_data.free)
    measures["mem.virtual.active"] = SimpleMeter(long, mem_virtual_data.active)
    measures["mem.virtual.inactive"] = SimpleMeter(long, mem_virtual_data.inactive)
    measures["mem.virtual.buffers"] = SimpleMeter(long, mem_virtual_data.buffers)
    measures["mem.virtual.cached"] = SimpleMeter(long, mem_virtual_data.cached)
    measures["mem.virtual.shared"] = SimpleMeter(long, mem_virtual_data.shared)
    measures["mem.swap.total"] = SimpleMeter(long, mem_swap_data.total)
    measures["mem.swap.used"] = SimpleMeter(long, mem_swap_data.used)
    measures["mem.swap.free"] = SimpleMeter(long, mem_swap_data.free)
    measures["mem.swap.percent"] = SimpleMeter(float, mem_swap_data.percent)

    network_interfaces = [ni for ni in psutil.net_io_counters(pernic=True)]
    for network_interface in network_interfaces:
        measures[network_interface + ".bytes_sent"] = DeltaMeter(io_data[network_interface].bytes_sent)
        measures[network_interface + ".bytes_recv"] = DeltaMeter(io_data[network_interface].bytes_recv)
        measures[network_interface + ".packets_sent"] = DeltaMeter(io_data[network_interface].packets_sent)
        measures[network_interface + ".packets_recv"] = DeltaMeter(io_data[network_interface].packets_recv)

    disks = [disk for disk in psutil.disk_io_counters(perdisk=True)]
    for disk in disks:
        measures[disk + ".read_count"] = DeltaMeter(io_disk_data[disk].read_count)
        measures[disk + ".write_count"] = DeltaMeter(io_disk_data[disk].write_count)
        measures[disk + ".read_bytes"] = DeltaMeter(io_disk_data[disk].read_bytes)
        measures[disk + ".write_bytes"] = DeltaMeter(io_disk_data[disk].write_bytes)
        measures[disk + ".read_time"] = DeltaMeter(io_disk_data[disk].read_time)
        measures[disk + ".write_time"] = DeltaMeter(io_disk_data[disk].write_time)

    for idx, path_data in enumerate(paths_data):
        path = paths[idx]
        path_name = path["name"]
        path_data = psutil.disk_usage(path["path"])
        measures[path_name + ".total"] = SimpleMeter(long, path_data.total)
        measures[path_name + ".used"] = SimpleMeter(long, path_data.used)
        measures[path_name + ".free"] = SimpleMeter(long, path_data.free)
        measures[path_name + ".percent"] = SimpleMeter(float, path_data.percent)

    measures["process"] = SimpleMeter(int, process_data)


    if (args.store == 0):
        latitude = 40.471032
        longitude = -3.686893
        province = 'M'
        city = 'Madrid'
        store = 'Vasconcelos'

    if (args.store == 1):
        latitude = 39.469215
        longitude = -0.373368
        province = 'V'
        city = 'Valencia'
        store = 'Lloria'

    if (args.store == 2):
        latitude = 43.262437
        longitude = -2.907181
        province = 'BI'
        city = 'Bilbao'
        store = 'Zumarkalea'

    location = "{},{}".format(latitude, longitude)

    mem_virtual_data_used = mem_virtual_data.used

    actual_time = time.time()

    for host in range(args.nhost):
        for doc in range(args.ndata):

            cpu_percent_data = max(min(round(random.uniform(-5, 5) + cpu_percent_data, 1), 100), 0.1)
            cpu_percent_json = measures["cpu"].update_and_get(cpu_percent_data)
            # cpu_times_percent_json = {
            #     "user": measures["cpu.user"].update_and_get(cpu_times_percent_data.user),
            #     "system": measures["cpu.system"].update_and_get(cpu_times_percent_data.system),
            #     "idle": measures["cpu.idle"].update_and_get(cpu_times_percent_data.idle),
            #     "nice": measures["cpu.nice"].update_and_get(cpu_times_percent_data.nice),
            #     "irq": measures["cpu.user"].update_and_get(cpu_times_percent_data.irq),
            #     "softirq": measures["cpu.user"].update_and_get(cpu_times_percent_data.softirq),
            #     "iowait": measures["cpu.user"].update_and_get(cpu_times_percent_data.iowait),
            #     "steal": measures["cpu.user"].update_and_get(cpu_times_percent_data.steal),
            # }
            cpu_times_percent_user_json = measures["cpu.user"].update_and_get(cpu_times_percent_data.user)
            cpu_times_percent_system_json = measures["cpu.system"].update_and_get(cpu_times_percent_data.system)
            cpu_times_percent_idle_json = measures["cpu.idle"].update_and_get(cpu_times_percent_data.idle)
            cpu_times_percent_nice_json = measures["cpu.nice"].update_and_get(cpu_times_percent_data.nice)
            cpu_times_percent_irq_json = measures["cpu.irq"].update_and_get(cpu_times_percent_data.irq)
            cpu_times_percent_softirq_json = measures["cpu.softirq"].update_and_get(cpu_times_percent_data.softirq)
            cpu_times_percent_iowait_json = measures["cpu.iowait"].update_and_get(cpu_times_percent_data.iowait)
            cpu_times_percent_steal_json = measures["cpu.steal"].update_and_get(cpu_times_percent_data.steal)

            mem_virtual_data_used = max(min(random.randint(-5000, 5000) + mem_virtual_data_used, mem_virtual_data.total), 0)
            mem_virtual_data_free = min(mem_virtual_data.total - mem_virtual_data.cached - mem_virtual_data_used, 0)
            # mem_json = {
            #     "virtual": {
            #         "total": measures["mem.virtual.total"].update_and_get(mem_virtual_data.total),
            #         "used": measures["mem.virtual.used"].update_and_get(mem_virtual_data_used),
            #         "cached": measures["mem.virtual.cached"].update_and_get(mem_virtual_data.cached),
            #         "free": measures["mem.virtual.free"].update_and_get(mem_virtual_data_free),
            #         "available": measures["mem.virtual.available"].update_and_get(mem_virtual_data.available),
            #         "percent": measures["mem.virtual.percent"].update_and_get(mem_virtual_data.percent),
            #         "active": measures["mem.virtual.active"].update_and_get(mem_virtual_data.active),
            #         "inactive": measures["mem.virtual.inactive"].update_and_get(mem_virtual_data.inactive),
            #         "buffers": measures["mem.virtual.buffers"].update_and_get(mem_virtual_data.buffers),
            #         "shared": measures["mem.virtual.shared"].update_and_get(mem_virtual_data.shared),
            #     },
            #     "swap": {
            #         "total": measures["mem.swap.total"].update_and_get(mem_swap_data.total),
            #         "used": measures["mem.swap.used"].update_and_get(mem_swap_data.used),
            #         "free": measures["mem.swap.free"].update_and_get(mem_swap_data.free),
            #         "percent": measures["mem.swap.percent"].update_and_get(mem_swap_data.percent),
            #     }
            # }
            mem_virtual_total_json = measures["mem.virtual.total"].update_and_get(mem_virtual_data.total)
            mem_virtual_used_json = measures["mem.virtual.used"].update_and_get(mem_virtual_data_used)
            mem_virtual_cached_json = measures["mem.virtual.cached"].update_and_get(mem_virtual_data.cached)
            mem_virtual_free_json = measures["mem.virtual.free"].update_and_get(mem_virtual_data_free)
            mem_virtual_available_json = measures["mem.virtual.available"].update_and_get(mem_virtual_data.available)
            mem_virtual_percent_json = measures["mem.virtual.percent"].update_and_get(mem_virtual_data.percent)
            mem_virtual_active_json = measures["mem.virtual.active"].update_and_get(mem_virtual_data.active)
            mem_virtual_inactive_json = measures["mem.virtual.inactive"].update_and_get(mem_virtual_data.inactive)
            mem_virtual_buffers_json = measures["mem.virtual.buffers"].update_and_get(mem_virtual_data.buffers)
            mem_virtual_shared_json = measures["mem.virtual.shared"].update_and_get(mem_virtual_data.shared)

            mem_swap_total_json = measures["mem.swap.total"].update_and_get(mem_swap_data.total)
            mem_swap_used_json = measures["mem.swap.used"].update_and_get(mem_swap_data.used)
            mem_swap_free_json = measures["mem.swap.free"].update_and_get(mem_swap_data.free)
            mem_swap_percent_json = measures["mem.swap.percent"].update_and_get(mem_swap_data.percent)

            # io_json = []
            # for k in io_data:
            #     if k == 'enp0s25':
            #         io_json = [{
            #             "name": k,
            #             "bytes_sent": measures[k + ".bytes_sent"].update_and_get(random.randint(0, 90000)),
            #             "bytes_recv": measures[k + ".bytes_recv"].update_and_get(random.randint(0, 90000)),
            #             "packets_sent": measures[k + ".packets_sent"].update_and_get(random.randint(0, 1000)),
            #             "packets_recv": measures[k + ".packets_recv"].update_and_get(random.randint(0, 1000)),
            #         }]
            for k in io_data:
                if k == 'enp0s25':
                    io_name_json = k
                    io_bytes_sent_json = measures[k + ".bytes_sent"].update_and_get(random.randint(0, 90000))
                    io_bytes_recv_json = measures[k + ".bytes_recv"].update_and_get(random.randint(0, 90000))
                    io_packets_sent_json = measures[k + ".packets_sent"].update_and_get(random.randint(0, 1000))
                    io_packets_recv_json = measures[k + ".packets_recv"].update_and_get(random.randint(0, 1000))

            # paths_json = []
            # for idx, p in enumerate(paths):
            #     current_path = paths[idx]
            #     current_path_data = paths_data[idx]
            #
            #     path_name = current_path["name"]
            #     path = current_path["path"]
            #     paths_json.append({
            #         "name": path_name,
            #         "path": path,
            #         "total": measures[path_name + ".total"].update_and_get(current_path_data.total),
            #         "used": measures[path_name + ".used"].update_and_get(current_path_data.used),
            #         "free": measures[path_name + ".free"].update_and_get(current_path_data.free),
            #         "percent": measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            #     })
            current_path = paths[0]
            current_path_data = paths_data[0]

            path_name = current_path["name"]
            path = current_path["path"]
            disk0_used_json = measures[path_name + ".used"].update_and_get(current_path_data.used)
            disk0_name_json = path_name
            disk0_percent_json = measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            disk0_free_json = measures[path_name + ".free"].update_and_get(current_path_data.free)
            disk0_path_json = path
            disk0_total_json = measures[path_name + ".total"].update_and_get(current_path_data.total)

            current_path = paths[0]
            current_path_data = paths_data[0]

            path_name = current_path["name"]
            path = current_path["path"]
            disk1_used_json = measures[path_name + ".used"].update_and_get(current_path_data.used)
            disk1_name_json = path_name
            disk1_percent_json = measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            disk1_free_json = measures[path_name + ".free"].update_and_get(current_path_data.free)
            disk1_path_json = path
            disk1_total_json = measures[path_name + ".total"].update_and_get(current_path_data.total)

            current_path = paths[0]
            current_path_data = paths_data[0]

            path_name = current_path["name"]
            path = current_path["path"]
            disk2_used_json = measures[path_name + ".used"].update_and_get(current_path_data.used)
            disk2_name_json = path_name
            disk2_percent_json = measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            disk2_free_json = measures[path_name + ".free"].update_and_get(current_path_data.free)
            disk2_path_json = path
            disk2_total_json = measures[path_name + ".total"].update_and_get(current_path_data.total)

            # io_disk_json = []
            # for k in io_disk_data:
            #     if k == 'sda6':
            #         io_disk_json = [{
            #             "disk_id": k,
            #             "read_count": measures[k + ".read_count"].update_and_get(io_disk_data[k].read_count),
            #             "write_count": measures[k + ".write_count"].update_and_get(io_disk_data[k].write_count),
            #             "read_bytes": measures[k + ".read_bytes"].update_and_get(random.randint(0, 90000)),
            #             "write_bytes": measures[k + ".write_bytes"].update_and_get(random.randint(0, 90000)),
            #             "read_time": measures[k + ".read_time"].update_and_get(io_disk_data[k].read_time),
            #             "write_time": measures[k + ".write_time"].update_and_get(io_disk_data[k].write_time)
            #         }]
            for k in io_disk_data:
                if k == 'sda6':
                    io_disk_name_json = k
                    io_disk_read_bytes_json = measures[k + ".read_bytes"].update_and_get(random.randint(0, 90000))
                    io_disk_read_count_json = measures[k + ".read_count"].update_and_get(io_disk_data[k].read_count)
                    io_disk_read_time_json = measures[k + ".read_time"].update_and_get(io_disk_data[k].read_time)
                    io_disk_write_bytes_json = measures[k + ".write_bytes"].update_and_get(random.randint(0, 90000))
                    io_disk_write_count_json = measures[k + ".write_count"].update_and_get(io_disk_data[k].write_count)
                    io_disk_write_time_json = measures[k + ".write_time"].update_and_get(io_disk_data[k].write_time)

            process_json = measures["process"].update_and_get(max(min(random.randint(-20, 20) + process_data, 1000), 0))

            # io_disk = io_disk_json.pop()
            # ndata = io_json.pop()
            # path1 = paths_json.pop()
            # path2 = paths_json.pop()
            # path3 = paths_json.pop()
            doc_time = datetime.datetime.fromtimestamp(actual_time + args.interval*doc).strftime("%Y-%m-%dT%H:%M:%SZ")

            message = {
                "store_location": location,
                "province": province,
                "city": city,
                "store": store,
                "processes": process_json,
                "cpu": cpu_percent_json,
                "cpu_times_user": cpu_times_percent_user_json,
                "cpu_times_system": cpu_times_percent_system_json,
                "cpu_times_idle": cpu_times_percent_idle_json,
                "cpu_times_nice": cpu_times_percent_nice_json,
                "cpu_times_irq": cpu_times_percent_irq_json,
                "cpu_times_softirq": cpu_times_percent_softirq_json,
                "cpu_times_iowait": cpu_times_percent_iowait_json,
                "cpu_times_steal": cpu_times_percent_steal_json,
                "disk0_used": disk0_used_json,
                "disk0_name": disk0_name_json,
                "disk0_percent": disk0_percent_json,
                "disk0_free": disk0_free_json,
                "disk0_path": disk0_path_json,
                "disk0_total": disk0_total_json,
                "disk1_used": disk1_used_json,
                "disk1_name": disk1_name_json,
                "disk1_percent": disk1_percent_json,
                "disk1_free": disk1_free_json,
                "disk1_path": disk1_path_json,
                "disk1_total": disk1_total_json,
                "disk2_used": disk2_used_json,
                "disk2_name": disk2_name_json,
                "disk2_percent": disk2_percent_json,
                "disk2_free": disk2_free_json,
                "disk2_path": disk2_path_json,
                "disk2_total": disk2_total_json,
                "io_disk_name": io_disk_name_json,
                "io_disk_read_bytes": io_disk_read_bytes_json,
                "io_disk_read_count": io_disk_read_count_json,
                "io_disk_read_time": io_disk_read_time_json,
                "io_disk_write_bytes": io_disk_write_bytes_json,
                "io_disk_write_count": io_disk_write_count_json,
                "io_disk_write_time": io_disk_write_time_json,
                "mem_swap_free": mem_swap_free_json,
                "mem_swap_percent": mem_swap_percent_json,
                "mem_swap_total": mem_swap_total_json,
                "mem_swap_used": mem_swap_used_json,
                "mem_virtual_active": mem_virtual_active_json,
                "mem_virtual_available": mem_virtual_available_json,
                "mem_virtual_buffers": mem_virtual_buffers_json,
                "mem_virtual_cached": mem_virtual_cached_json,
                "mem_virtual_shared": mem_virtual_shared_json,
                "mem_virtual_free": mem_virtual_free_json,
                "mem_virtual_inactive": mem_virtual_inactive_json,
                "mem_virtual_percent": mem_virtual_percent_json,
                "mem_virtual_total": mem_virtual_total_json,
                "mem_virtual_used": mem_virtual_used_json,
                "network_bytes_recv": io_bytes_recv_json,
                "network_bytes_sent": io_bytes_sent_json,
                "network_name": io_name_json,
                "network_packets_recv": io_packets_recv_json,
                "network_packets_sent": io_packets_sent_json,
                "host": "{}{}".format(args.hostname,doc),
                "time": doc_time
            }

            with open(args.output, 'a') as outfile:
                json.dump(message, outfile)
                outfile.write("\n");

if __name__ == "__main__":
    main(sys.argv)


