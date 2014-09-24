#!/usr/bin/env python
#coding:utf-8

import urllib,urllib2
from lxml import etree
from os.path import isdir as isdir
from os.path import isdir as isfile
from os import system as system
download_dir			= "./tmp/"
root_dir			= "./Ksymhunter/"
ubuntu_kernel_image_dir		= root_dir + '/ubuntu_vmlinux/'
ubuntu_kernel_image_file	= root_dir + 'ubuntu_kernel_image_url.txt'
ubuntu_kernel_image_fd 		= ""
exist_files			= []


def download_file(target_url, filename):
	system("axel  -q -n 5 %s -o %s/%s" % (target_url, download_dir, filename))

def get_ubuntu_urls():
	url = "http://ddebs.ubuntu.com/pool/main/l/linux/"
	req = urllib2.Request(url)
	print "[+] retrying %s " % url,
	try:
		resp = urllib2.urlopen(req)
		print " Success.."
	except:
		print " False.. exiting.."
		exit(1)
	html = resp.read()
	page = etree.HTML(html.lower().decode('utf-8'))
	hrefs = page.xpath(u'/html/body/table/tr/td/a')
	hrefs = hrefs[1:] 	# the first is top
	for i in hrefs:
		item = i.values()[0]
		if item in exist_files:
			print item + " already exists,skip.."
			continue
		if item.find('powerpc') != -1:
			continue
		if item.find('arm') != -1:
			continue
		if item.find('ppc') != -1:
			continue
		if item.find("linux-image-") != -1:
			print "[+] Download target : %s" % url + item
			download_file(url+item, item)
			extract_and_process(item, ubuntu_kernel_image_dir)
			ubuntu_kernel_image_fd.write(url + item + '\n')


def extract_and_process(filename, kernel_image_dir):
	print "extract %s..." % filename
	system('ar p %s/%s data.tar.gz|tar xzf - -C %s' % (download_dir, filename, download_dir))
	#system('tar -xzf %s/data.tar.gz' % download_dir)
	system('mv %s/usr/lib/debug/boot/* %s/vmlinux-%s' % (download_dir, kernel_image_dir, 
				filename[:filename.rfind(".")])) 
			# linux-image-2.6.32-24-386-dbgsym_2.6.32-24.42_i386.ddeb
	system('rm -rf %s/usr' % download_dir)

if __name__ == '__main__':
	if not isdir(download_dir):
		print "[-] " + download_dir + " not exists,exit..."
		exit()
	if not isdir(ubuntu_kernel_image_dir):
		print "[-] " + ubuntu_kernel_image_dir + " not exists,exit..."
		exit()
	if isfile(ubuntu_kernel_image_file):
		print "[+] ubuntu_kernel_image_file exists,let's load it"
		tmp_fd = open(ubuntu_kernel_image_file, 'r')
		exist_files = tmp_fd.readlines()
		for i in range(len(exist_files)):
			exist_files[i].strip()
		tmp_fd.close()
		
	ubuntu_kernel_image_fd = open(ubuntu_kernel_image_file, "a+")
	
	get_ubuntu_urls()
