#!/usr/bin/env ruby

require 'rubygems'
require 'json'
require 'excon'
require 'csv'

tl_host = "localhost"
tl_port = "50000"

def parse_data(data)
  parsed_data = {}
  current_set = {}

  data.downcase!
  data.gsub!(":", "")

  csv = CSV.parse(data, " ")

  csv.each_with_index do |item, i|
    item.each_with_index do |x, y|
      if y == 0
        @current_thing = x
      else
        if i.even?
          current_set.store(@stat, nil)
        else
          current_set.store(csv[i-1][y], x)
        end
      end
    end

    parsed_data.store(@current_thing, current_set)
    current_set = {}
  end

  parsed_data
end

def test
  data = File.read("./netstatdata0")
  puts parse_data(data).inspect
end

def main
  data = File.read("/proc/net/snmp")

  json = {
    "plugin_id" => "proc_net_snmp",
    "tags" => ["tcp", "networking"],
    "data" => parse_data(data)
  }.to_json

  response = Excon.post("http://#{tl_host}:#{tl_port}", :body => json)
end

main
#test