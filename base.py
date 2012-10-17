#!/usr/bin/env python

import os
import re

from collections import defaultdict
from subprocess import Popen, PIPE

from tenderloin.plugin import TenderloinPlugin


class BasePlugin(TenderloinPlugin):
    def __init__(self, *args, **kwargs):
        self.prev_cpu = {}
        self.prev_diskstats = {}
        super(BasePlugin, self).__init__(*args, **kwargs)

    def fmt(self, f):
        return "%.2f" % f

    def rateof(self, a, b):
        a = float(a)
        b = float(b)

        try:
            return (b - a) / self.interval if (b - a) != 0 else 0
        except ZeroDivisionError:
            if a:
                return -a
            return b

    def get_cpu(self):
        cpudata = defaultdict(dict)
        cur_cpu = {}
        to_read = "/proc/stat"
        wanted = [
            "user",
            "nice",
            "system",
            "idle",

            "iowait",
            "irq",
            "softirq"
        ]

        if os.path.exists(to_read):
            jiffy = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

            with open(to_read, "r") as f:
                for line in f:
                    if line.startswith("cpu"):
                        fields = line.split()
                        cur_cpu[fields[0]] = fields[1:len(wanted) + 1]
                    else:
                        break

            if self.prev_cpu:
                for cpu in cur_cpu:
                    if cpu in self.prev_cpu:
                        for fld_idx in xrange(len(wanted) + 1):
                            try:
                                prev = float(self.prev_cpu[cpu][fld_idx])
                                cur = float(cur_cpu[cpu][fld_idx])
                                cpudata[cpu][wanted[fld_idx]] = ((cur - prev) / self.interval * 100 / jiffy)
                            except ZeroDivisionError:
                                if prev:
                                    cpudata[cpu][wanted[fld_idx]] = -prev
                                else:
                                    cpudata[cpu][wanted[fld_idx]] = cur
                            except IndexError:
                                continue
                self["cpu"] = cpudata
            self.prev_cpu = cur_cpu
        else:
            self["cpu"] = {}

    def get_diskstats(self):
        diskstats = defaultdict(dict)
        cur_diskstats = defaultdict(dict)
        to_read = "/proc/diskstats"

        if os.path.exists(to_read):
            stat_fields = [
                "rd",
                "rd_m",
                "rd_s",
                "rd_t",
                "wr",
                "wr_m",
                "wr_s",
                "wr_t",
                "running",
                "use",
                "aveq"
            ]
            r1 = re.compile("[a-z]d[a-z]$")

            with open(to_read, "r") as f:
                for line in f:
                    fields = line.strip().split()
                    device = fields[2]
                    fields = fields[3:]

                    if not r1.match(device):
                        continue

                    for pos in xrange(len(fields)):
                        cur_diskstats[device][stat_fields[pos]] = float(fields[pos])

            if self.prev_diskstats:
                for device in cur_diskstats:
                    if device in self.prev_diskstats:
                        try:
                            avg_req_sz = ((cur_diskstats[device]["rd_s"] -
                                           self.prev_diskstats[device]["rd_s"]) +
                                          (cur_diskstats[device]["wr_s"] -
                                           self.prev_diskstats[device]["wr_s"])) /\
                                               ((cur_diskstats[device]["rd"] +
                                                 cur_diskstats[device]["wr"]) -
                                                (self.prev_diskstats[device]["rd"] +
                                                 self.prev_diskstats[device]["wr"]))
                        except ZeroDivisionError:
                            avg_req_sz = 0

                        try:
                            avg_queue_sz = (cur_diskstats[device]["aveq"] -
                                            self.prev_diskstats[device]["aveq"]) /\
                                            1000
                        except ZeroDivisionError:
                            avg_queue_sz = 0

                        try:
                            avg_wait = ((cur_diskstats[device]["rd_t"] -
                                         self.prev_diskstats[device]["rd_t"]) +
                                        (cur_diskstats[device]["wr_t"] -
                                         self.prev_diskstats[device]["wr_t"])) /\
                                             ((cur_diskstats[device]["rd"] -
                                               self.prev_diskstats[device]["rd"]) +
                                              (cur_diskstats[device]["wr"] -
                                               self.prev_diskstats[device]["wr"]))
                            avg_wait = avg_wait if avg_wait > 0 else 0
                        except ZeroDivisionError:
                            avg_wait = 0

                        try:
                            avg_read_wait = (cur_diskstats[device]["rd_t"] -
                                             self.prev_diskstats[device]["rd_t"]) /\
                                                 (cur_diskstats[device]["rd"] -
                                                  self.prev_diskstats[device]["rd"])
                        except ZeroDivisionError:
                            avg_read_wait = 0

                        try:
                            avg_write_wait = (cur_diskstats[device]["wr_t"] -
                                              self.prev_diskstats[device]["wr_t"]) /\
                                                  (cur_diskstats[device]["wr"] -
                                                   self.prev_diskstats[device]["wr"])
                        except ZeroDivisionError:
                            avg_write_wait = 0

                        util = self.rateof(self.prev_diskstats[device]["use"],
                                           cur_diskstats[device]["use"])

                        try:
                            svctime = util / self.rateof((self.prev_diskstats[device]["rd"] +
                                                          self.prev_diskstats[device]["wr"]),
                                                         (cur_diskstats[device]["rd"] +
                                                          cur_diskstats[device]["wr"]))
                        except ZeroDivisionError:
                            svctime = 0

                        diskstats[device] = {
                            "reads_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["rd"],
                                                                     cur_diskstats[device]["rd"])),
                            "writes_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["wr"],
                                                                      cur_diskstats[device]["wr"])),
                            "read_merges_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["rd_m"],
                                                                           cur_diskstats[device]["rd_m"])),
                            "write_merges_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["wr_m"],
                                                                            cur_diskstats[device]["wr_m"])),
                            "read_kilobytes_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["rd_s"],
                                                                              cur_diskstats[device]["rd_s"]) / 2),
                            "write_kilobytes_per_second": self.fmt(self.rateof(self.prev_diskstats[device]["wr_s"],
                                                                               cur_diskstats[device]["wr_s"]) / 2),
                            "ios_in_progress": self.fmt(cur_diskstats[device]["running"] / self.interval),
                            "average_request_size": self.fmt(avg_req_sz),
                            "average_queue_size": self.fmt(avg_queue_sz / self.interval),
                            "average_wait": self.fmt(avg_wait),
                            "average_read_wait": self.fmt(avg_read_wait),
                            "average_write_wait": self.fmt(avg_write_wait),
                            "svctime": self.fmt(svctime),
                            "util": self.fmt(util / 10)
                        }
                self["diskstats"] = diskstats
            self.prev_diskstats = cur_diskstats

    def get_loadavg(self):
        to_read = "/proc/loadavg"

        if os.path.exists(to_read):
            with open(to_read, "r") as f:
                fields = f.read().strip().split()

            procs = fields[3].split("/")
            self["loadavg"] = {
                "shortterm": fields[0],
                "midterm": fields[1],
                "longterm": fields[2],
                "processes": {
                    "scheduled": procs[0],
                    "total": procs[1]
                }
            }

    def get_meminfo(self):
        self["meminfo"] = {}
        to_read = "/proc/meminfo"

        if os.path.exists(to_read):
            with open(to_read, "r") as f:
                for line in f:
                    lhs, rhs = line.split(":")
                    lhs = lhs.replace("(", "_").replace(")", "").lower()
                    self["meminfo"][lhs] = rhs.strip().split()[0]

                self["meminfo"]["memused"] = (int(self["meminfo"]["memtotal"]) -
                                              (int(self["meminfo"]["memfree"]) +
                                               int(self["meminfo"]["buffers"]) +
                                               int(self["meminfo"]["cached"])))
                self["meminfo"]["swapused"] = (int(self["meminfo"]["swaptotal"]) -
                                               int(self["meminfo"]["swapfree"]))

    def get_netproto(self):
        self["netproto"] = {}
        to_read = "/proc/net/snmp"

        if os.path.exists(to_read):
            with open(to_read, "r") as f:
                for line in f:
                    fields = line.split()
                    proto = fields[0].lower().rstrip(":")

                    if not proto in self["netproto"].keys():
                        keys = [fld.lower() for fld in fields[1:]]
                        self["netproto"][proto] = {}
                    else:
                        self["netproto"][proto] = dict(zip(keys, tuple(fields[1:])))

    def get_networkinterface(self):
        self["networkinterface"] = {}
        to_read = "/proc/net/dev"

        if os.path.exists(to_read):
            with open(to_read, "r") as f:
                output = f.readlines()
                output.pop(0)
                keys = output[0].replace("|", " ").split()[1:]
                recv_keys = tuple(keys[0:8])
                xmit_keys = tuple(keys[8:])

                for line in output[1:]:
                    (iface, fields) = line.strip().split(":")
                    self["networkinterface"][iface] = {}
                    fields = fields.split()
                    recv_tup = tuple(fields[0:8])
                    xmit_tup = tuple(fields[8:])
                    self["networkinterface"][iface]["recv"] = dict(zip(recv_keys, recv_tup))
                    self["networkinterface"][iface]["xmit"] = dict(zip(xmit_keys, xmit_tup))

    def get_openfiles(self):
        self["openfiles"] = {}
        to_read = "/proc/sys/fs/file-nr"

        if os.path.exists(to_read):
            with open(to_read, "r") as f:
                fields = f.read().split()

            self["openfiles"] = {
                "count": int(fields[0]) - int(fields[1]),
                "max": fields[2]
            }

    def get_tcpudp(self):
        self["tcpdudp"] = {}
        proc = Popen(["/bin/ss -tuna"], stdout=PIPE, stderr=PIPE, shell=True)
        output = proc.communicate()[0].splitlines()
        if proc.returncode == 0:
            output.pop(0)
            for line in output:
                fields = line.split()
                proto = fields[0]

                if proto == "tcp":
                    state = fields[1].lower()
                    self["tcpudp"][proto].setdefault(state, 0)
                    self["tcpudp"][proto][state] += 1
                else:
                    self["tcpudp"].setdefault(proto, 0)
                    self["tcpudp"][proto] += 1

    def df(self, cmd):
        data = {}
        r1 = re.compile("^/(dev/i)")
        proc = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
        output = proc.communicate()[0].splitlines()
        if proc.returncode != 0:
            return {}

        output.pop(0)
        for line in output:
            fields = line.split()
            key = r1.sub("", fields[0])
            data[fields[5]] = {
                "total": fields[1],
                "used": fields[2],
                "available": fields[3],
                "percent_used": fields[4].replace("-", "0").replace("%", ""),
                "device": key
            }

            return data

    def get_df(self):
        cmd = "df -Pl"
        excludefs = [
            "debugfs",
            "devtmpfs",
            "ecryptfs",
            "iso9660",
            "none",
            "ramfs",
            "romfs",
            "squashfs",
            "simfs"
            "udf",
            "unknown",
            "tmpfs"
        ]
        data = {}
        blocks_cmd = "%s -x %s" % (cmd, " -x ".join(excludefs))
        inodes_cmd = "%s -i -x %s" % (cmd, " -x ".join(excludefs))

        blocks = self.df(blocks_cmd)
        for key in blocks:
            data.setdefault(key, {})
            data[key]["device"] = blocks[key]["device"]
            del blocks[key]["device"]
            data[key]["blocks"] = blocks[key]

        inodes = self.df(inodes_cmd)
        for key in inodes:
            data.setdefault(key, {})
            del inodes[key]["device"]
            data[key]["inodes"] = inodes[key]

        self["df"] = data

    def get_data(self):
        self.get_cpu()
        self.get_loadavg()
        self.get_df()
        self.get_diskstats()
        self.get_meminfo()
        self.get_netproto()
        self.get_networkinterface()
        self.get_openfiles()
        self.get_tcpudp()

plugin = BasePlugin("base", tags=["graphite", "system"])
plugin.loop()
