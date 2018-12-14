#!/usr/bin/env python

import os
import cocotb

def main():
    print(os.path.join(os.path.dirname(cocotb.__file__),'share'))

if __name__ == "__main__":
    main()

