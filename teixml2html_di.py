#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from teixml2html import Xml2Html

__date__ = "15-15-2020"
__version__ = "0.0.1"
__author__ = "Marta Materni"


def do_mauin(xml, html, tagsd,tagsi, conf, deb=False):
    xt=Xml2Html(xml, html, tagsd, conf, deb)
    xt.write_html()
    xt=Xml2Html(xml, html, tagsi, conf, deb)
    xt.write_html()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    if len(sys.argv) == 1:
        print("release: %s  %s" % (__version__, __date__))
        parser.print_help()
        sys.exit()
    parser.add_argument('-d',
                        dest="deb",
                        required=False,
                        action="store_true",
                        default=False,
                        help="[-d ](abilita debug)")
    parser.add_argument('-td',
                        dest="tagd",
                        required=True,
                        default="",
                        metavar="",
                        help="-t <file_hml_tags_dipl.csv>")
    parser.add_argument('-ti',
                        dest="tagi",
                        required=True,
                        default="",
                        metavar="",
                        help="-t <file_hml_tags_interr.csv>")
    parser.add_argument('-c',
                        dest="cnf",
                        required=True,
                        metavar="",
                        help="-c <file_conf.json")
    parser.add_argument('-i',
                        dest="xml",
                        required=True,
                        metavar="",
                        help="-i <file_in.xml>")
    parser.add_argument('-o',
                        dest="html",
                        required=True,
                        metavar="",
                        help="-o <file_out.html>")
    args = parser.parse_args()
    if args.html == args.xml:
        print("Name File output errato")
        sys.exit(0)
    do_mauin(args.xml, args.html, args.tagd,args.tagi, args.cnf, args.deb)