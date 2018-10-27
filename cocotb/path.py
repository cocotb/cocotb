#!/usr/bin/env python

import os
import imp

def main():
    print(os.path.dirname(imp.find_module('cocotb')[1]))

if __name__ == "__main__":
    main()
