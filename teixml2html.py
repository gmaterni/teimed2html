#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pdb import set_trace
import os
import re
import sys
from lxml import etree
import pprint
import sys
import copy
import argparse
from readhtmlconf import read_html_conf
from readjson import read_json
from htmlbuilder import HtmlBuilder
from ualog import Log
from uainput import Inp

__date__ = "15-12-2020"
__version__ = "0.0.2"
__author__ = "Marta Materni"


def pp(data):
    if data is None:
        return ""
    s = pprint.pformat(data, indent=2, width=30)
    return s+os.linesep


logconf = Log()
logdeb = Log()

loginfo = Log()
logerr = Log()
inp = Inp()


class Xml2Html(object):

    def __init__(self, xml_path, html_path, csv_path, json_path, deb):
        logdeb.open("log/teixml2html.deb.log", 0)
        logconf.open("log/teixml2html.cnf.log", 0)
        loginfo.open("log/teixml2html.log", 0)
        logerr.open("log/teixml2html.err.log", 1)
        inp.enable(deb)
        #
        self.xml_path = xml_path
        self.html_path = html_path
        # lettura confiurazioni
        self.man_conf = read_json(json_path)
        logconf.log(">> man_coonf",pp(self.man_conf)).prn(0)
        self.html_conf = read_html_conf(csv_path)
        logconf.log(">> html_conf",pp(self.html_conf)).prn(0)
        #precede id per diplomatia e interpretativa
        rd = self.html_conf.get("before_id",{})
        self.before_id = rd.get('tag',"")
        #
        self.hb = HtmlBuilder()
        self.store_xml_data = {}
        ## self.inp_x = False
        self.ok_deb=False

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
            logerr.log("Error in T xml")
            logerr.log(nd.tag)
            sys.exyt()
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
            return ""
        m = re.search('\d', id)
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

    """
    def node_val(self, nd):
        ls = []
        for x in nd.itertext():
            s = x.strip().replace(os.linesep, '')
            ls.append(s)
        texts = ' '.join(ls)
        s = re.sub(r"\s{2,}", ' ', texts)
        return s
    """

    def node_is_parent(self, nd):
        cs = nd.getchildren()
        l = len(cs)
        return l > 0

    def get_node_data(self, nd):
        id = self.node_id(nd)
        id_num = self.node_id_num(id)
        items = self.node_items(nd)
        items['id_num'] = id_num
        return {
            'id': id,
            'liv': self.node_liv(nd),
            'tag': self.node_tag(nd).lower(),
            'tail': self.node_tail(nd),
            'text': self.node_text(nd),
            'items': items,
            # 'keys': self.node_keys(nd),
            # 'val':self.node_val(nd),
            'is_parent': self.node_is_parent(nd)
        }

    # controla se 'text' è nei parametri di  text
    # individuati dat %parametro%
    def text_is_text_params(self, text):
        ms = re.findall("[%]\w+[%]", text)
        ks = [x.replace('%', '') for x in ms]
        return 'text' in ks

    # formatta text utilizzado attrs
    # pqrw={'k0':'val0','k1':'val1', ..}
    def text_format(self, text, pars):
        try:
            ms = re.findall("[%]\w+[%]", text)
            ks = [x.replace('%', '') for x in ms]
            for k in ks:
                v = pars.get(k, f'%{k}%')
                text = text.replace(f'%{k}%', v)
            return text
        except Exception as e:
            logerr.set_out(1)
            logerr.log(e)
            logerr.log("text_format()")
            logerr.log("text:", text)
            logerr.log("pars:", pars)
            sys.exit()

    # formatta html_attr_str se il parametro 
    # non esiste lo rimuove
    # aggiusta gli argommenti di class
    def attrs_format(self, text, pars):
        ms = re.findall("[%]\w+[%]", text)
        ks = [x.replace('%', '') for x in ms]
        for k in ks:
            v = pars.get(k,'')
            text = text.replace(f'%{k}%', v)
        text=text.replace(' "','"')
        text=text.replace(' _int','')
        p0=text.find('class')
        if p0> -1:
            p1=text.find('"',p0+5)
            p2=text.find('"',p1+1)
            s0=text[:p2]
            s1=text[p2:]
            text=s0.replace('#','')+s1
        return text


    # parent x_data.items +
    # x.data.items +
    # csv_data.attrs +
    # text:text
    def items_extend(self, x_data, csv_data,):
        attrs = {}
        # parent x_data items
        c_parent = csv_data.get('parent', None)
        if c_parent is not None:
            x_data_parent = self.store_xml_data.get(c_parent, None)
            if x_data_parent is not None:
                items = x_data_parent.get('items', {})
                attrs = copy.deepcopy(items)
        # x_data items
        items = x_data.get('items', {})
        for k, v in items.items():
            attrs[k] = v
        # csv_data attrs
        c_attrs = csv_data.get('attrs', {})
        for k, v in c_attrs.items():
            attrs[k] = v
        # text:text
        text = x_data.get('text', '')
        if text != '':
            attrs['text'] = text
        return attrs

    # seleziona gli elemnti di x_items individuati da c_kets
    # aggiunge gli elementi c_attrs {}
    def attrs_builder(self, x_items, c_keys=[], c_attrs={}):
        attrs = {}
        try:
            for k in c_keys:
                attrs[k] = x_items[k]
            for k in c_attrs.keys():
                attrs[k] = c_attrs[k]
        except Exception as e:
            logerr.log(e)
            logerr.log("attrs_builder()")
            logerr.log("x_items:", x_items)
            logerr.log("c_keys:", c_keys)
            logerr.log("c_attrs:", c_attrs)
            sys.exit()
        return attrs

    # ritorna una str che inizia, se esisotno,
    # con class=".."  id=".." ...
    def attrs2html(self, attrs):
        ks = []
        if 'class' in attrs.keys():
            ks.append('class')
        if 'id' in attrs.keys():
            ks.append('id')
        for k in attrs.keys():
            if k not in ['id', 'class']:
                ks.append(k)
        ls=[]
        for k in ks:
            v = attrs[k]
            if k=='id':
                v= f'{self.before_id}{v}'
            s=f'{k}="{v}"'
            ls.append(s)
        return " ".join(ls)

    # ritorna dati della row di <tag>.csvindividuata
    # dall tag o tag+attr di x_data del file xml
    # memorizza  i dati in store_csv_data
    # la key è quella ottenuta dal tag xml e l'eventuale attributo
    def get_conf_data(self, x_data):
        """
        if x_data.get('id',"").find("Il902w3") > -1:
            self.ok_deb=True
        if self.ok_deb:
            set_trace()
        """
        xml_tag = x_data['tag']
        row_data = self.html_conf.get(xml_tag, None)
        if row_data is None:
            row_data = self.html_conf.get('x', {})
        tag = row_data.get('tag', f"_x_{xml_tag}")
        p = tag.find('+')
        if p > -1:
            x_items = x_data['items']
            # tag|tag + att1_name + attr2_name+..
            # x_items[attr<n>_name]  => [attr1_val,attr2_val]
            # #tag + attr1_val + att2_vap + ..
            lsk = tag.split('+')[1:]
            lsv = [x_items[k] for k in lsk if k in x_items.keys()]
            attrs_val = '+'.join(lsv)
            tag_csv = xml_tag+'+'+attrs_val
            row_data = self.html_conf.get(tag_csv, None)
            ############
            # logdeb.log(tag_csv).prn()
            #############
            if row_data is None:
                row_data = self.html_conf.get('x+y', None)
        else:
            tag_csv = xml_tag
        self.store_xml_data[tag_csv] = x_data
        return row_data

    def build_html_tag(self, x_data):
        x_items = x_data['items']
        x_text = x_data['text']
        c_data = self. get_conf_data(x_data)
        ##############
        id=x_data.get('id',"")
        if id.find("Il902w3") > -1:
            # inp.inp("!")
            pass
        ################
        ################################
        if inp.prn:
            loginfo.log("============").prn()
            loginfo.log(">> x_data").prn()
            loginfo.log(pp(x_data)).prn()
            loginfo.log(">> csv_data").prn()
            loginfo.log(pp(c_data)).prn()
        ################################
        c_tag = c_data.get('tag')
        # h_keys sone le key degli elementi di items da prendere
        c_keys = c_data.get('keys', [])
        c_attrs = c_data.get('attrs', {})
        c_text = c_data.get('text', "")
        c_params = c_data.get('params', {})
        html_attrs = self.attrs_builder(x_items, c_keys, c_attrs)
        html_attrs_str = self.attrs2html(html_attrs)
        ext_items = self.items_extend(x_data, c_data)
        #
        # formatta attr utilizzando x_items
        if html_attrs_str.find('%') > -1:
            html_attrs_str = self.attrs_format(html_attrs_str, x_items)
        #
        # formatta c_text itilizzando ext_items (items estsesi + text)
        if c_text.find('%') > -1:
            x_text_is_par = self.text_is_text_params(c_text)
            c_text = self.text_format(c_text, ext_items)
            # text è stato utilizzato come parametro
            if x_text_is_par:
                x_text = ''
            # formatta c_text utilizzando c_params
            if c_text.find('%') > -1:
                c_text = self.text_format(c_text, c_params)
        #
        html_text = x_text+c_text
        #
        if c_tag.find('_x') > -1:
            c_tag = f'{c_tag}_{x_data["tag"]}'
            logerr.log(c_tag).prn()
            inp.inp("!")
        ####################
        html_data = {
            'tag': c_tag,
            'attrs': html_attrs_str,
            'text': html_text
        }
        ################################
        if inp.prn:
            loginfo.log(">> htl_data").prn()
            loginfo.log(pp(html_data)).prn()
            loginfo.log(">> ext_items").prn()
            loginfo.log(pp(ext_items)).prn()
        ################################
        return html_data

    def html_append(self, nd):
        x_data = self.get_node_data(nd)
        x_tag = x_data['tag']
        x_liv = x_data['liv']
        is_parent = x_data['is_parent']
        x_tail = x_data['tail']
        h_data = self.build_html_tag(x_data)
        h_tag = h_data['tag']
        h_text = h_data['text']
        h_attrs = h_data['attrs']
        if is_parent:
            self.hb.opn(x_liv, h_tag, h_attrs, h_text, x_tail)
        else:
            self.hb.ovc(x_liv, h_tag, h_attrs, h_text, x_tail)
        ################################
        if inp.prn:
            loginfo.log(">> html node").prn()
            loginfo.log(self.hb.tag_last()).prn()
        inp.inp(x_tag)
        if inp.equals('?'):
            print(self.hb.html_format())
            inp.inp()
        ################################

    def set_html_pramas(self, html):
        pars = self.man_conf.get("html_params", {})
        for k, v in pars.items():
            html = html.replace(k, v)
        return html

    def write_html(self):
        self.hb.init()
        xml_root = etree.parse(self.xml_path)
        for nd in xml_root.iter():
            self.html_append(nd)
        self.hb.del_tags('XXX')
        self.hb.end()
        #
        # html su una riga versione per produzione
        html = self.hb.html_onerow()
        html = self.set_html_pramas(html)
        with open(self.html_path, "w+") as f:
            f.write(html)
        os.chmod(self.html_path, 0o666)
        #
        # html formattao versione per il debug
        # file_name.html => file_name_X.html
        html = self.hb.html_format()
        html = self.set_html_pramas(html)
        path = self.html_path.replace(".html", "_X.html")
        with open(path, "w+") as f:
            f.write(html)
        os.chmod(self.html_path, 0o666)

        """
        soup = BeautifulSoup(html,"html.parser")
        html=soup.prettify(formatter="html5")
        h_path=self.html_path.replace('.html','F.html')
        with open(h_path, "w+") as f:
            f.write(html)
        os.chmod(self.html_path, 0o666)
        """


def do_mauin(xml, html, tags, conf, deb=False):
    Xml2Html(xml, html, tags, conf, deb).write_html()
    print("ok")


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
    parser.add_argument('-t',
                        dest="tag",
                        required=True,
                        default="",
                        metavar="",
                        help="-t <file_hml_tags.csv>")
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
    do_mauin(args.xml, args.html, args.tag, args.cnf, args.deb)
