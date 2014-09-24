#!/usr/bin/env python
#coding:utf-8

from pyelf import elf

def do_quick_lookupsymbol(vmlinux_abs_dir, symbol_name):
    """ use abs vmlinux dir for safe condition
     return:
     symbol info string or "NotFound"
     symbol info string like this:
     'Symbol info:STT_FUNC:STB_GLOBAL
     0xc0168940:0xa3
     section: .text
     '
    """
    fd = open(vmlinux_abs_dir, 'r')
    e = elf.ELFFile(fd)
    r = e.quick_lookup_symbol(symbol_name)
    fd.close()
    if r is None:
        return "NotFound"
    section_type = r.section
    if section_type.name:
        section_name = section_name
    else:
        section_name = "*NO SECTION@@"
    result_string = "Symbol info:%r:%r\n%s 0x%x:0x%x \nsection: %s\n" %\
            (r.type, r.bind, r.name, r.value, r.size, section_name)

    return result_string

def do_deep_lookupsymbol(vmlinux_abs_dir, symbol_name):
    fd = open(vmlinux_abs_dir, 'r')
    e = elf.ELFFile(fd)
    r_list = e.deep_lookup_symbol(symbol_name)
    fd.close()
    if r_list is None:
        return "NotFound"

    result_string = ""
    for item in r_list:
        section_type = item.section
        if section_type.name:
            section_name = section_name
        else:
            section_name = "*NO SECTION@@"
        result_string += "Symbol info:%r:%r\n%s 0x%x:0x%x \nsection: %s\n\n" %\
                (item.type, item.bind, item.name, item.value, item.size, section_name)

    return result_string


