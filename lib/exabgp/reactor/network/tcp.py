# encoding: utf-8
"""
setup.py

Created by Thomas Mangin on 2013-07-13.
Copyright (c) 2013-2013 Exa Networks. All rights reserved.
"""

import struct
import socket
import platform

from exabgp.protocol.family import AFI
from exabgp.reactor.network.error import errno

from .error import NotConnected,BindingError,MD5Error,NagleError,TTLError,AsyncError

def create (afi):
	try:
		if afi == AFI.ipv4:
			io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		if afi == AFI.ipv6:
			io = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		try:
			io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except AttributeError:
			pass
		try:
			io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		except AttributeError:
			pass
	except socket.error:
		raise NotConnected('Could not create socket')
	return io

def bind (io,afi,ip):
	try:
		if afi == AFI.ipv4:
			io.bind((ip,0))
		if afi == AFI.ipv6:
			io.bind((ip,0,0,0))
	except socket.error,e:
		raise BindingError('Could not bind to local ip %s - %s' % (ip,str(e)))

def connect (io,ip,afi,md5):
	try:
		if afi == AFI.ipv4:
			io.connect((ip,179))
		if afi == AFI.ipv6:
			io.connect((ip,179,0,0))
	except socket.error, e:
		if e.errno == errno.EINPROGRESS:
			return
		if md5:
			raise NotConnected('Could not connect to peer %s (check your MD5 passwords): %s' % (ip,str(e)))
		raise NotConnected('Could not connect to peer %s: %s' % (ip,str(e)))


def MD5 (io,ip,afi,md5):
	if md5:
		os = platform.system()
		if os == 'FreeBSD':
			if md5 != 'kernel':
				raise MD5Error(
					'FreeBSD requires that you set your MD5 key via ipsec.conf.\n'
					'Something like:\n'
					'flush;\n'
					'add <local ip> <peer ip> tcp 0x1000 -A tcp-md5 "password";'
					)
			try:
				TCP_MD5SIG = 0x10
				io.setsockopt(socket.IPPROTO_TCP, TCP_MD5SIG, 1)
			except socket.error,e:
				raise MD5Error(
					'FreeBSD requires that you rebuild your kernel to enable TCP MD5 Signatures:\n'
					'options         IPSEC\n'
					'options         TCP_SIGNATURE\n'
					'device          crypto\n'
				)
		elif os == 'Linux':
			try:
				TCP_MD5SIG = 14
				TCP_MD5SIG_MAXKEYLEN = 80

				n_port = socket.htons(179)
				if afi == AFI.ipv4:
					SS_PADSIZE = 120
					n_addr = socket.inet_pton(socket.AF_INET, ip)
					tcp_md5sig = 'HH4s%dx2xH4x%ds' % (SS_PADSIZE, TCP_MD5SIG_MAXKEYLEN)
					md5sig = struct.pack(tcp_md5sig, socket.AF_INET, n_port, n_addr, len(md5), md5)
				if afi == AFI.ipv6:
					SS_PADSIZE = 100
					SIN6_FLOWINFO = 0
					SIN6_SCOPE_ID = 0
					n_addr = socket.inet_pton(socket.AF_INET6, ip)
					tcp_md5sig = 'HHI16sI%dx2xH4x%ds' % (SS_PADSIZE, TCP_MD5SIG_MAXKEYLEN)
					md5sig = struct.pack(tcp_md5sig, socket.AF_INET6, n_port, SIN6_FLOWINFO, n_addr, SIN6_SCOPE_ID, len(md5), md5)
				io.setsockopt(socket.IPPROTO_TCP, TCP_MD5SIG, md5sig)
			except socket.error,e:
				raise MD5Error('This linux machine does not support TCP_MD5SIG, you can not use MD5 : %s' % str(e))
		else:
			raise MD5Error('ExaBGP has no MD5 support for %s' % os)

def nagle (io,ip):
	try:
		# diable Nagle's algorithm (no grouping of packets)
		io.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	except AttributeError:
		raise NagleError("Could not disable nagle's algorithm for %s" % ip)

def TTL (io,ip,ttl):
	# None (ttl-security unset) or zero (maximum TTL) is the same thing
	if ttl:
		try:
			io.setsockopt(socket.IPPROTO_IP,socket.IP_TTL, 20)
		except socket.error,e:
			raise TTLError('This OS does not support IP_TTL (ttl-security) for %s: %s' % (ip,str(e)))

def async (io,ip):
	try:
		io.setblocking(0)
	except socket.error, e:
		raise AsyncError('could not set socket non-blocking for %s: %s' % (ip,str(e)))

# try:
# 	try:
# 		# Linux / Windows
# 		self.message_size = io.getsockopt(socket.SOL_SOCKET, socket.SO_MAX_MSG_SIZE)
# 	except AttributeError:
# 		# BSD
# 		self.message_size = io.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
# except socket.error, e:
# 	self.message_size = None