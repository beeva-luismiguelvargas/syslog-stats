import random
import psutil
import json
import time
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

def main(argv):

    if len(argv) == 2:
        ndata = int(argv[1])
    else:
        ndata = 100

    paths = []
    paths.append({"name": "root", "path": "/"})
    paths.append({"name": "opt", "path": "/opt"})
    paths.append({"name": "tmp", "path": "/tmp"})

    message = []
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


    mem_virtual_data_used = mem_virtual_data.used

    for i in range(ndata):

        cpu_percent_data = max(min(round(random.uniform(-5, 5) + cpu_percent_data, 1), 100), 0.1)
        cpu_percent_json = measures["cpu"].update_and_get(cpu_percent_data)
        cpu_times_percent_json = {
            "user": measures["cpu.user"].update_and_get(cpu_times_percent_data.user),
            "system": measures["cpu.system"].update_and_get(cpu_times_percent_data.system),
            "idle": measures["cpu.idle"].update_and_get(cpu_times_percent_data.idle),
            "nice": measures["cpu.nice"].update_and_get(cpu_times_percent_data.nice),
            "irq": measures["cpu.user"].update_and_get(cpu_times_percent_data.irq),
            "softirq": measures["cpu.user"].update_and_get(cpu_times_percent_data.softirq),
            "iowait": measures["cpu.user"].update_and_get(cpu_times_percent_data.iowait),
            "steal": measures["cpu.user"].update_and_get(cpu_times_percent_data.steal),
        }

        mem_virtual_data_used = max(min(random.randint(-5000, 5000) + mem_virtual_data_used, mem_virtual_data.total), 0)
        mem_virtual_data_free = min(mem_virtual_data.total - mem_virtual_data.cached - mem_virtual_data_used, 0)
        mem_json = {
            "virtual": {
                "total": measures["mem.virtual.total"].update_and_get(mem_virtual_data.total),
                "used": measures["mem.virtual.used"].update_and_get(mem_virtual_data.used),
                "cached": measures["mem.virtual.cached"].update_and_get(mem_virtual_data.cached),
                "free": measures["mem.virtual.free"].update_and_get(mem_virtual_data_free),
                "available": measures["mem.virtual.available"].update_and_get(mem_virtual_data.available),
                "percent": measures["mem.virtual.percent"].update_and_get(mem_virtual_data.percent),
                "active": measures["mem.virtual.active"].update_and_get(mem_virtual_data.active),
                "inactive": measures["mem.virtual.inactive"].update_and_get(mem_virtual_data.inactive),
                "buffers": measures["mem.virtual.buffers"].update_and_get(mem_virtual_data.buffers),
                "shared": measures["mem.virtual.shared"].update_and_get(mem_virtual_data.shared),
            },
            "swap": {
                "total": measures["mem.swap.total"].update_and_get(mem_swap_data.total),
                "used": measures["mem.swap.used"].update_and_get(mem_swap_data.used),
                "free": measures["mem.swap.free"].update_and_get(mem_swap_data.free),
                "percent": measures["mem.swap.percent"].update_and_get(mem_swap_data.percent),
            }
        }

        io_json = []
        for k in io_data:
            if k == 'enp0s25':
                io_json = [{
                    "name": k,
                    "bytes_sent": measures[k + ".bytes_sent"].update_and_get(random.randint(0, 90000)),
                    "bytes_recv": measures[k + ".bytes_recv"].update_and_get(random.randint(0, 90000)),
                    "packets_sent": measures[k + ".packets_sent"].update_and_get(random.randint(0, 1000)),
                    "packets_recv": measures[k + ".packets_recv"].update_and_get(random.randint(0, 1000)),
                }]
        paths_json = []
        for idx, p in enumerate(paths):
            current_path = paths[idx]
            current_path_data = paths_data[idx]

            path_name = current_path["name"]
            path = current_path["path"]
            paths_json.append({
                "name": path_name,
                "path": path,
                "total": measures[path_name + ".total"].update_and_get(current_path_data.total),
                "used": measures[path_name + ".used"].update_and_get(current_path_data.used),
                "free": measures[path_name + ".free"].update_and_get(current_path_data.free),
                "percent": measures[path_name + ".percent"].update_and_get(current_path_data.percent)
            })
        io_disk_json = []
        for k in io_disk_data:
            if k == 'sda6':
                io_disk_json = [{
                    "disk_id": k,
                    "read_count": measures[k + ".read_count"].update_and_get(io_disk_data[k].read_count),
                    "write_count": measures[k + ".write_count"].update_and_get(io_disk_data[k].write_count),
                    "read_bytes": measures[k + ".read_bytes"].update_and_get(random.randint(0, 90000)),
                    "write_bytes": measures[k + ".write_bytes"].update_and_get(random.randint(0, 90000)),
                    "read_time": measures[k + ".read_time"].update_and_get(io_disk_data[k].read_time),
                    "write_time": measures[k + ".write_time"].update_and_get(io_disk_data[k].write_time)
                }]
        process_json = measures["process"].update_and_get(max(min(random.randint(-20, 20) + process_data, 1000), 0))

        # store_id = random.randint(0,2)
        store_id = 0

        if (store_id == 0):
            latitude = 40.471032
            longitude = -3.686893
            province = 'M'
            city = 'Madrid'
            store = 'Vasconcelos'

        if (store_id == 1):
            latitude = 39.469215
            longitude = -0.373368
            province = 'V'
            city = 'Valencia'
            store = 'Lloria'

        if (store_id == 2):
            latitude = 43.262437
            longitude = -2.907181
            province = 'BI'
            city = 'Bilbao'
            store = 'Zumarkalea'

        location = "{},{}".format(latitude, longitude)

        io_disk = io_disk_json.pop()
        ndata = io_json.pop()
        path1 = paths_json.pop()
        path2 = paths_json.pop()
        path3 = paths_json.pop()

        message.append({
            "cpu": cpu_percent_json,
            "cpu_times": cpu_times_percent_json,
            "mem": mem_json,
            "disk0": path1,
            "disk1": path2,
            "disk2": path3,
            "io_disk": io_disk,
            "network": ndata,
            "processes": process_json,
            "location": location,
            "province": province,
            "city": city,
            "store": store
        })
        # sleep (0.005)

    with open('stats.json', 'w') as outfile:
        json.dump(message, outfile)

if __name__ == "__main__":
    main(sys.argv)


