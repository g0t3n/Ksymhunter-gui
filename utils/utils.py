#!/usr/bin/env python
#coding:utf8

from os import listdir
from os.path import join as pathjoin
from os.path import isdir,isfile
import sys
from struct import unpack_from

def assert_elf_file(fd):
    magic = fd.read(4)
    return magic == '\x7fELF'

def assert_vmlinux_file(fd):
    # file is too hard to code in here...
    return assert_elf_file(fd)


def getVmlinuxJson(image_path):
    # directory like this: Ksymhunter/centos/5/vmlinux1
    # Json struct like this
    # { 'distribution' : // centos,ubuntu
    #   {'release_code'  : // 5,6,7
    #       [vmlinux_file]
    #   },
    #   {'release_code2' : // 6
    #       [vmlinux_file]
    #   }
    if "Ksymhunter" not in image_path:
        print "[-] image_path must be Ksymhunter/[ubuntu,centos...]/release_code/file"
        sys.exit(-1)
    print "image_path : %s" % image_path
    vmlinux_json = {}
    distribution_list = listdir(image_path)
    for dis in distribution_list:
        # import IPython;IPython.embed()
        dis_dir = pathjoin(image_path, dis)
        if not isdir(dis_dir):
            continue
        release_dir_list = listdir(dis_dir)
        vmlinux_json[dis] = {}
        for release_item in release_dir_list:
            rel_dir = pathjoin(dis_dir, release_item)
            if not isdir(rel_dir):
                continue
            tmp_vmlinux_files = listdir(rel_dir)
            vmlinux_files = []
            for f in range(len(tmp_vmlinux_files)):
                if isfile(pathjoin(rel_dir, tmp_vmlinux_files[f])):
                    fd = open(pathjoin(rel_dir, tmp_vmlinux_files[f]))
                    if assert_vmlinux_file(fd):
                        vmlinux_files.append(tmp_vmlinux_files[f])
            vmlinux_json[dis][release_item] = vmlinux_files
    return vmlinux_json

if __name__ == '__main__':
    print getVmlinuxJson('/Users/g0t3n/Ksymhunter/Ksymhunter')
