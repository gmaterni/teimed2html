#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
from io import StringIO
import pprint
import re
import sys
import traceback
from lxml import etree
from teixml2lib.txtbuilder import TxtBuilder
from teixml2lib.readtxtconf import read_text_tag
from teixml2lib.readjson import read_json
from teixml2lib.uainput import Inp
from teixml2lib.ualog import Log
import teixml2lib.prndata as pd
from teixml2lib import file_utils as fu
from pdb import set_trace

__date__ = "20-04-2021"
__version__ = "0.2.0"
__author__ = "Marta Materni"


def pp(data,w=40):
    s = pprint.pformat(data, indent=2, width=40)
    return s

inp = Inp()

class Xml2Txt:

    def __init__(self):
        self.log=Log("w")
        self.log.open("log/teixml2txt.log", 0)
        self.logerr = Log("a")
        self.logerr.open("log/teixml2txt.ERR.log", 1)
        self.xml_path = ''
        self.txt_path = None
        self.txt_cfg = None
        self.txt_tag_cfg = None
        self.txt_builder = None
        self.csv_tag_ctrl=""
        self.x_data_dict = {}      
        self.trace = False

    def node_liv(self, node):
        d = 0
        while node is not None:
            d += 1
            node = node.getparent()
        return d - 1

    def clean_key(self, k):
        s = k
        p0 = k.find("{http")
        if (p0 > -1):
            p1 = k.rfind('}')
            if p1 > -1:
                s = k[p1+1:]
        return s

    def node_items(self, nd):
        kvs = nd.items()
        js = {}
        for kv in kvs:
            k = self.clean_key(kv[0])
            v = kv[1]
            js[k] = v
        return js

    def node_tag(self, nd):
        tag = nd.tag
        tag = tag if type(nd.tag) is str else "XXX"
        p = tag.rfind('}')
        if p > 1:
            self.logerr.log("ERROR in  xml")
            self.logerr.log(nd.tag)
            sys.exit(1)
        return tag.strip()

    def node_id(self, nd):
        s = ''
        kvs = nd.items()
        for kv in kvs:
            if kv[0].rfind('id') > -1:
                s = kv[1]
                break
        return s

    def node_id_num(self, id):
        if id == '':
            return ''
        m = re.search(r'\d', id)
        if m is None:
            return -1
        p = m.start()
        return id[p:]

    def node_text(self, nd):
        text = nd.text
        text = '' if text is None else text.strip()
        text = text.strip().replace(os.linesep, ',,')
        return text

    def node_tail(self, nd):
        tail = '' if nd.tail is None else nd.tail
        tail = tail.strip().replace(os.linesep, '')
        return tail

    def node_val(self, nd):
        ls = []
        for x in nd.itertext():
            s = x.strip().replace(os.linesep, '')
            ls.append(s)
        texts = ' '.join(ls)
        s = re.sub(r"\s{2,}", ' ', texts)
        return s

    def node_is_parent(self, nd):
        cs = nd.getchildren()
        le = len(cs)
        return le > 0

    def get_node_data(self, nd):
        items = self.node_items(nd)
        id = self.node_id(nd)
        if id != '':
            id_num = self.node_id_num(id)
            items['id_num'] = id_num
        return {
            'id': id,
            'liv': self.node_liv(nd),
            'tag': self.node_tag(nd),
            'text': self.node_text(nd),
            'tail': self.node_tail(nd),
            'items': items,
            # 'keys': self.node_keys(nd)
            # 'val': self.node_val(nd),
            'val': "",
            'is_parent': self.node_is_parent(nd)
        }

    def get_data_row_text_csv(self, x_data):
        """ ritorna dati della row di <tag>.csv individuata
            dall tag o tag+attr di x_data del in xml_data_dict
            la key è quella ottenuta dal tag xml 
            e l'eventuale/i attributo
        Args:
            x_data (dict):xml data
        Returns:
            [row_data (dict): dati estartti da csv
        """
        xml_tag = x_data['tag']
        row_data = self.txt_tag_cfg.get(xml_tag, None)
        if row_data is None:
            row_data = self.txt_tag_cfg.get('x', {})
            csv_tag = xml_tag
            self.csv_tag_ctrl = f'_x_{csv_tag}'            
        else:
            tag = row_data.get('tag', f"_x_{xml_tag}")
            p = tag.find('+')
            if p > -1:
                x_items = x_data['items']
                lsk = tag.split('+')[1:]
                lsv = [x_items[k] for k in lsk if k in x_items.keys()]
                attrs_val = '+'.join(lsv)
                csv_tag = xml_tag+'+'+attrs_val
                row_data = self.txt_tag_cfg.get(csv_tag, None)
                if row_data is None:
                    row_data = self.txt_tag_cfg.get('x+y', None)
                    self.csv_tag_ctrl = f'_xy_{csv_tag}'
                else:
                    self.csv_tag_ctrl = csv_tag
            else:
                csv_tag = xml_tag
                self.csv_tag_ctrl = csv_tag
        # TODO aggiunta a row_data csv_data  utilizzata come key
        # nella ricerca del json risultante dalla lettura di csc
        # può sosituire self.csv_tag_ctrl
        # verificato csvtaga=self.csv_tag_ctrl
        if csv_tag != self.csv_tag_ctrl:
            print(csv_tag)
            print(self.csv_tag_ctrl)
            print(pp(x_data))
            set_trace()
        row_data['csv_tag']=self.csv_tag_ctrl
        self.x_data_dict[csv_tag] = x_data
        return row_data


    def build_txt_data(self, nd):
        """ crea un json contenente
        x_data (estratto da xml)
        c_data (estratto da tag.csv)
        t_data (empty per la furua elaborazione)
        Args:
            nd : nod xml

        Returns:
            json: json=x_data + c_data + t_data
        """        
        x_data = self.get_node_data(nd)
        # c_data corrisponde a row_data
        c_data = self. get_data_row_text_csv(x_data)
        # ERRORi nella gestione del files csv dei tag html
        if self.csv_tag_ctrl.find('_x') > -1:
            self.logerr.log(f"ERROR in csv tag:{self.csv_tag_ctrl}")
            self.logerr.log(f"file: {self.xml_path}")
            self.logerr.log("xml:", pp(x_data))
            self.logerr.log("csv:", self.csv_tag_ctrl)
            self.logerr.log(os.linesep)
            inp.inp("!")
            set_trace()
        #############################################
        txt_data = {
            'id': x_data.get('id',0),
            'is_parent':x_data.get('is_parent',False),
            'items': x_data.get('items',{}),
            'liv': x_data.get('liv',0),
            'tag': x_data.get('tag',''),
            'text': x_data.get('text',''),
            'tail': x_data.get('tail',''),
            'val': x_data.get('val',''),

            #'c_xml_tag': c_data.get('xml_tag',''),
            # 'c_tag': c_data.get('tag',''),
            'c_csv_tag': c_data.get('csv_tag',''),
            'c_keys':c_data.get('keys',[]),
            'c_attrs':c_data.get('',{}),
            'c_text': c_data.get('text',''),
            'c_params': c_data.get('params',''),
            'c_parent': c_data.get('parent',''),

            't_i':0,
            't_type':'',
            't_up':False,
            't_start':'',          
            't_end':'',
            't_sp':'',
            't_ln':False,
            't_flag':False
            }
        return txt_data
            
    def prn_data_lst(self):
        pd.set_log_liv(1)
        self.log.log('===============').prn()
        for d in self.txt_builder.data_lst:
            self.log.log('').prn()
            pd.prn_data(d,1)
            inp.inp('!')

    def read_conf(self, json_path):
        try:
            self.txt_cfg = read_json(json_path)
            csv_path = self.txt_cfg.get("txt_tag_file", None)
            self.log.log(f"csv_path:{csv_path}")
            if csv_path is None:
                raise Exception("ERROR txt.csv is null.")
            # type : d:txt d:syn i:txt i:syn
            self.txt_tag_cfg = read_text_tag(csv_path, "i:txt")
            #logconf.log(pp(self.html_tag_cfg).replace("'", '"')).prn(0)
        except Exception as e:
            self.logerr.log("ERROR: read_conf())")
            self.logerr.log(e)
            sys.exit(str(e))
    
    def write_txt(self,
                  xml_path='',
                  txt_path='',
                  json_path='',
                  write_append = 'w',
                  debug_liv = '0'):
        try:
            debug_liv=1
            inp.set_liv(debug_liv)
            self.xml_path=xml_path
            self.txt_path=txt_path
            if write_append not in ['w', 'a']:
                raise Exception(
                    f"ERROR in output write/append. {write_append}")
            try:
                parser = etree.XMLParser(ns_clean=True)
                xml_root=etree.parse(self.xml_path,parser)
            except Exception as e:
                self.logerr.log("ERROR teixml2txt.py write_txt() parse_xml")
                self.logerr.log(e)
                sys.exit(1)
            self.read_conf(json_path)
            self.txt_builder=TxtBuilder()
            ########################
            for nd in xml_root.iter():
                txt_data=self.build_txt_data(nd)
                self.txt_builder.add(txt_data)
            ########################
            self.txt_builder.elab()           
            #self.prn_data_lst()
            txt=self.txt_builder.txt
            #print(txt)
            fu.make_dir_of_file(self.txt_path)
            with open(self.txt_path, write_append) as f:
                f.write(txt)
            fu.chmod(self.txt_path)
        except Exception as e:
            self.logerr.log("ERROR teixml2txt.py write_html()")
            self.logerr.log(e)
            ou=StringIO()
            traceback.print_exc(file = ou)
            st=ou.getvalue()
            ou.close()
            self.logerr.log(st)
            sys.exit(1)
        return self.txt_path

def do_mauin(xml, txt, conf, wa = 'w', deb = False):
    Xml2Txt().write_txt(xml, txt, conf, wa, deb)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    if len(sys.argv) == 1:
        print("release: %s  %s" % (__version__, __date__))
        parser.print_help()
        sys.exit(1)
    parser.add_argument('-d',
                        dest = "deb",
                        required = False,
                        metavar = "",
                        default = 0,
                        help = "[-d 0/1/2](setta livello di debug)")
    parser.add_argument('-wa',
                        dest = "wa",
                        required = False,
                        metavar = "",
                        default = "w",
                        help = "[-wa w/a (w)rite a)ppend) default w")
    parser.add_argument('-c',
                        dest = "cfg",
                        required = True,
                        metavar = "",
                        help = "-c <file_conf.json")
    parser.add_argument('-i',
                        dest = "xml",
                        required = True,
                        metavar = "",
                        help = "-i <file_in.xml>")
    parser.add_argument('-o',
                        dest = "txt",
                        required = True,
                        metavar = "",
                        help = "-o <file_out.txt>")
    args=parser.parse_args()
    do_mauin(args.xml, args.txt, args.cfg, args.wa, args.deb)