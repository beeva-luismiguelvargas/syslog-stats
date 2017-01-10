"""
Remote syslog client.

Works by sending UDP messages to a remote syslog server. The remote server
must be configured to accept logs from the network.

License: PUBLIC DOMAIN

For more information, see RFC 3164.
"""

import socket
import json
import datetime
from time import sleep


class Facility:
  "Syslog facilities"
  KERN, USER, MAIL, DAEMON, AUTH, SYSLOG, \
  LPR, NEWS, UUCP, CRON, AUTHPRIV, FTP = range(12)

  LOCAL0, LOCAL1, LOCAL2, LOCAL3, \
  LOCAL4, LOCAL5, LOCAL6, LOCAL7 = range(16, 24)

class Level:
  "Syslog levels"
  EMERG, ALERT, CRIT, ERR, \
  WARNING, NOTICE, INFO, DEBUG = range(8)

class Syslog:
  """A syslog client that logs to a remote server.
  """
  def __init__(self,
    host="52.169.115.99",
    port=5140,
    facility=Facility.USER):
    self.host = host
    self.port = port
    self.facility = facility
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def send(self, message, level, hostnumber):
    "Send a syslog message to remote host using UDP."
    # data = "<%d> %s" % (level + self.facility*8, message)
    data = "<%d>%s %s %s" % (level + self.facility*8, datetime.datetime.now().strftime("%b %d %H:%M:%S"), "hostname{}".format(hostnumber), "monitoring-agent: "+message)
    self.socket.sendto(data, (self.host, self.port))
    print data

if __name__ == "__main__":
    log = Syslog()
    with open('stats.json') as data_file:
        data = json.load(data_file)

    serialized_data = json.dumps(data[0])

    log.send(serialized_data, Level.INFO, 0)


#
#
#
# class Syslog:
#   """A syslog client that logs to a remote server.
#   """
#   def __init__(self,
#     host="52.169.115.99",
#     port=5140,
#     facility=Facility.DAEMON):
#     self.host = host
#     self.port = port
#     self.facility = "monitoring-agent"
#     self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#
#   def send(self, message, level):
#     # "Send a syslog message to remote host using UDP."
#     # hosts = [ "10.0.0.20" , "10.0.0.21", "10.0.0.22"]
#     # self.socket.sendto(message, (random.choice(hosts), self.port))
#     self.socket.sendto(message, ("10.0.0.20", self.port))
#
#
# if __name__ == "__main__":
#     message = 'monitoring-agent: {"province": "BI", "cpu_times": {"idle": 87.3, "user": 10.6, "iowait": 0.3, "softirq": 0.0, "irq": 0.0, "steal": 0.0, "system": 1.7, "nice": 0.0}, "mem": {"swap": {"total": 16802377728, "percent": 0.0, "free": 16802377728, "used": 0}, "virtual": {"available": 8077099008, "cached": 4342235136, "used": 6417403904, "buffers": 353525760, "inactive": 2578071552, "active": 7985508352, "shared": 1613926400, "total": 16454807552, "percent": 50.9, "free": 5341642752}}, "city": "Bilbao", "processes": 297, "network": {"packets_recv": 1488, "packets_sent": 690, "bytes_sent": 143150, "name": "enp0s25", "bytes_recv": 1613626}, "io_disk": {"write_bytes": 622592, "read_count": 0, "write_count": 40, "read_time": 0, "read_bytes": 0, "disk_id": "sda6", "write_time": 368}, "disk0": {"used": 144438824960, "name": "tmp", "percent": 89.8, "free": 16467689472, "path": "/tmp", "total": 169542426624}, "disk1": {"used": 144438824960, "name": "opt", "percent": 89.8, "free": 16467689472, "path": "/opt", "total": 169542426624}, "disk2": {"used": 144438824960, "name": "root", "percent": 89.8, "free": 16467689472, "path": "/", "total": 169542426624}, "location": "43.262437,-2.907181", "cpu": 12.7, "store": "Zumarkalea"}'
#     log = Syslog()
#     for i in range(0,360):
#         for j in range(0,100):
#             datos = "<%d>%s %s %s" % (14, now.strftime("%b %d %H:%M:%S"), "range{}".format(i), message)
#             log.send(datos, Level.INFO)
#             sleep(0.002)
