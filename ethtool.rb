#!/usr/bin/env ruby

require 'rubygems'
require 'json'
require 'excon'

tl_host = "localhost"
tl_port = "50000"

def test
  data = File.read("./ethtooltestdata0")
  puts parse_stats(data).inspect

  data = File.read("./ethtooltestdata1")
  puts parse_stats(data).inspect
end

def main
  stats = {}

  ifaces = `grep ':' /proc/net/dev | awk -F\\: '{print $1}' | sed -e s/\\ //g`.split

  ifaces.each do |iface|
    unless iface == "lo"
      data = `ethtool -S #{iface}`
      p = parse_stats(data)
      stats.store(iface, p)
    end
  end

  json = {
    "plugin_id" => "ethtool_statistics",
    "tags" => ["interface", "networking"],
    "data" => stats
  }.to_json

  response = Excon.post("http://#{tl_host}:#{tl_port}", :body => json)
end

def parse_stats(data)
  parsed_stats = {}

  data.each do |line|
    unless line == "NIC statistics:\n"
      split_line = line.gsub(" ", "").strip.split(":")

      if split_line.length == 3
        parsed_stats.store(split_line[0], {split_line[1], split_line[2]})
      elsif split_line.length == 2
        parsed_stats.store(split_line[0], split_line[1])
      end

    end
  end

  parsed_stats
end

main
#test