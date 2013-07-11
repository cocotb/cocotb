#!/usr/bin/env python

import sys

f= sys.argv[1]

for line in open(f, 'r'):

    define_start = line.find('define')
    if define_start != -1:
        data = line[define_start:].split()
        if data[1].startswith('vpi') or data[1].startswith('cb'):
            try:
                name = data[1]
                value = eval(data[2])
            except:
                pass
            print "{\"%s\", %d}," % (name, value)

print '{(long)NULL, (long)NULL}'
