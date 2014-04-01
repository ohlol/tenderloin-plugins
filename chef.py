#!/usr/bin/env python

import json
from subprocess import Popen, PIPE

from tenderloinplugin import TenderloinPlugin


class ChefPlugin(TenderloinPlugin):
    def get_data(self):
        proc = Popen(["ohai -l fatal"], stdout=PIPE, stderr=PIPE, shell=True)
        output = proc.communicate()[0]
        if proc.returncode != 0:
            self["ohai"] = {}
        else:
            try:
                self["ohai"] = json.loads(output)
            except ValueError:
                self["ohai"] = {}

f = ChefPlugin("chef")
f.loop()
