#!/usr/bin/env ruby

require 'rubygems'
require 'json'
require 'excon'

tl_host = "localhost"
tl_port = "50000"

file_path = "/proc/net/bonding/*"
#file_path = "./bond[0,1]" # for testing

files = Dir.glob(file_path)

data = {}

if files
  files.each do |file|

    file_data = {}

    File.readlines(file).each do |line|
      key, value = line.split(': ', 2)
      if key && value

        clean_key = key.downcase.gsub(' ', '_').gsub('(', '').gsub(')', '')

        file_data.store(clean_key, value.downcase.strip)
      end
    end

    data.store(File.basename(file), file_data)
  end
end

json = {
  "plugin_id" => "bonded_interfaces",
  "tags" => ["bond", "interface", "networking"],
  "data" => data
}.to_json

response = Excon.post("http://#{tl_host}:#{tl_port}", :body => json)

