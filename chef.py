#!/usr/bin/env python

import json
from subprocess import Popen, PIPE

from tenderloin.plugin import TenderloinPlugin


class ChefPlugin(TenderloinPlugin):
    def get_data(self):
        proc = Popen(["ohai"], stdout=PIPE, stderr=PIPE, shell=True)
        output = proc.communicate()[0]
        if proc.returncode != 0:
            self["ohai"] = {}
        else:
            self["ohai"] = json.loads(output)

f = ChefPlugin("chef")
f.loop()
