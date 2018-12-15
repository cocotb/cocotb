#!/usr/bin/env python

import os
import sys
import cocotb
import argparse
import pkg_resources


class PrintAction(argparse.Action):
    def __init__(self, option_strings, dest, text=None, **kwargs):
        super(PrintAction, self).__init__(option_strings, dest, nargs=0, **kwargs)
        self.text = text

    def __call__(self, parser, namespace, values, option_string=None):
        print(self.text)
        parser.exit()

def main():

    share_dir = os.path.join(os.path.dirname(cocotb.__file__),'share')
    prefix_dir = os.path.dirname(os.path.dirname(cocotb.__file__))
    makefiles_dir = os.path.join(os.path.dirname(cocotb.__file__),'share', 'makefiles')
    version = pkg_resources.get_distribution('cocotb').version

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--prefix', help='echos the package-prefix of cocotb', action=PrintAction, text=prefix_dir)
    parser.add_argument('--share', help='echos the package-share of cocotb', action=PrintAction, text=share_dir)
    parser.add_argument('--makefiles', help='echos the package-makefiles of cocotb', action=PrintAction, text=makefiles_dir)
    parser.add_argument('-v', '--version', help='echos version of cocotb', action=PrintAction, text=version)
    
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

if __name__ == "__main__":
    main()

