#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pdb import set_trace
import sys
import argparse
import os
# from ualog import Log


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    try:
        parser.add_argument('-e',
                            dest="err",
                            required=True,
                            metavar="",
                            default="",
                            help="-e <file.err>")
        parser.add_argument('-o',
                            dest="hou",
                            required=True,
                            metavar="",
                            help="-o <file.html outputl>")
        parser.add_argument('-i',
                            dest="hin",
                            required=True,
                            metavar="",
                            help="[-i <file html input>")
        args = parser.parse_args()
        os.system(
            f"tidy -config cnf/tidy.cnf -file {args.err} -output {args.hou} {args.hin}")
        #
        with open(args.err) as f:
            txt = f.read()
        if txt.strip() == '':
            os.remove(args.err)

    except Exception as e:
        print(e)
        sys.exit(1)