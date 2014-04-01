#!/usr/bin/env python

import glob
import re
import socket

from tenderloinplugin import TenderloinPlugin


class HaproxyPlugin(TenderloinPlugin):
    def col2stat(self, idx):
        try:
            ret = {
                0: 'vip_name', 1: 'backend_name', 2: 'queue_cur',
                3: 'queue_max', 4: 'sessions_cur', 5: 'sessions_max',
                6: 'sessions_limit', 7: 'sessions_total', 8: 'bytes_in',
                9: 'bytes_out', 10: 'denied_req', 11: 'denied_resp',
                12: 'errors_req', 13: 'errors_conn', 14: 'errors_resp',
                15: 'warnings_retr', 16: 'warnings_redis', 17: 'server_status',
                18: 'server_weight', 19: 'server_active', 20: 'server_backup',
                21: 'server_check', 22: 'server_down', 23: 'server_lastchange',
                24: 'server_downtime', 25: 'queue_limit', 29: 'server_throttle',
                30: 'sessions_lbtotal', 32: 'session_type', 33: 'session_rate_cur',
                34: 'session_rate_limit', 35: 'session_rate_max', 36: 'check_status'
            }[idx]
        except KeyError:
            ret = None

        return ret

    def stats_sockets(self):
        for config in glob.glob("/etc/haproxy/*"):
            with open(config, "r") as f:
                for line in f:
                    l = line.strip().split()
                    if l:
                        if l[0] == "stats" and l[1] == "socket":
                            yield l[2]

    def read_socket(self, sock_path):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(sock_path)
            sock_data = []
            data = ''

            sock.send('show stat\n')

            while True:
                data = sock.recv(1024)
                if not data:
                    break
                sock_data.append(data)
        except socket.error:
            return []

        sock.close()

        return ''.join(sock_data).strip('\n').splitlines()

    def get_data(self):
        r1 = re.compile("^(#|$)")
        stat = {}
        for sock_path in self.stats_sockets():
            for line in self.read_socket(sock_path):
                if r1.match(line):
                    continue

                lary = line.split(",")

                for i in xrange(0, len(lary) - 1):
                    if lary[i]:
                        stat.update({self.col2stat(i): lary[i]})

                vn = stat["vip_name"]
                bn = stat["backend_name"]

                if not self.__contains__(vn):
                    self[vn] = {}

                for k, v in stat.items():
                    self[vn].setdefault(bn, {})
                    self[vn][bn][k] = v


plugin = HaproxyPlugin("haproxy", tags=["graphite"])
plugin.loop()
