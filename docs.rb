#!/usr/bin/env ruby
  
require "erb"
require "yaml"

template = File.read(".README.erb")
renderer = ERB.new(template, nil, "-")
File.write("README.md", renderer.result())
