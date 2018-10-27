#!/usr/bin/env python

import os
import cocotb

def main():
    print(os.path.dirname(os.path.dirname(cocotb.__file__)))

if __name__ == "__main__":
    main()

