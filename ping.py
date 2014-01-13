"""
   A pure python ping implementation using raw socket.

   Original Version from Matthew Dixon Cowles:
   -> ftp://ftp.visi.com/users/mdc/ping.py
   
   Edited by vnX. Added rdomain support, working on OpenBSD 5.1.
"""

import os, sys, socket, struct, select, time

ICMP_ECHO_REQUEST = 8
socket.SO_RTABLE = 4129
TIMEOUT = 2
def checksum(source_string):
	"""
	I'm not too confident that this is right but testing seems
	to suggest that it gives the same answers as in_cksum in ping.c
	"""
	sum = 0
	countTo = (len(source_string)/2)*2
	count = 0
	while count<countTo:
		thisVal = ord(source_string[count + 1])*256 + ord(source_string[count])
		sum = sum + thisVal
		sum = sum & 0xffffffff
		count = count + 2
 
	if countTo<len(source_string):
		sum = sum + ord(source_string[len(source_string) - 1])
		sum = sum & 0xffffffff
 
	sum = (sum >> 16)  +  (sum & 0xffff)
	sum = sum + (sum >> 16)
	answer = ~sum
	answer = answer & 0xffff
	answer = answer >> 8 | (answer << 8 & 0xff00)
 
	return answer
 
 
def receive_one_ping(my_socket, ID, timeout):
	"""
	receive the ping from the socket.
	"""
	timeLeft = timeout
	while True:
		startedSelect = time.time()
		whatReady = select.select([my_socket], [], [], timeLeft)
		howLongInSelect = (time.time() - startedSelect)
		if whatReady[0] == []:
			return timeout
		timeReceived = time.time()
		recPacket, addr = my_socket.recvfrom(1024)
		icmpHeader = recPacket[20:28]
		type, code, checksum, packetID, sequence = struct.unpack(
			"bbHHh", icmpHeader
		)
		if packetID == ID:
			bytesInDouble = struct.calcsize("d")
			timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
			return timeReceived - timeSent
		timeLeft = timeLeft - howLongInSelect
		if timeLeft <= 0:
			return timeout

def send_one_ping(my_socket, dest_addr, ID):
	"""
	Send one ping to the given >dest_addr<.
	"""
	dest_addr  =  socket.gethostbyname(dest_addr)
	my_checksum = 0
	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
	bytesInDouble = struct.calcsize("d")
	data = (192 - bytesInDouble) * "Q"
	data = struct.pack("d", time.time()) + data
	my_checksum = checksum(header + data)
	header = struct.pack(
		"bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1
	)
	packet = header + data
	my_socket.sendto(packet, (dest_addr, 1))
	
def do_one(dest_addr, timeout, rtableid):
	"""
	Returns either the delay (in seconds) or none on timeout.
	"""
	icmp = socket.getprotobyname("icmp")
	try:
		my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
		my_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RTABLE,rtableid)
		my_socket.settimeout(TIMEOUT)
	except socket.error, (errno, msg):
		if errno == 1:
			msg = msg + (
				" - Note that ICMP messages can only be sent from processes"
				" running as root."
			)
			raise socket.error(msg)
		raise
	my_ID = os.getpid() & 0xFFFF
	send_one_ping(my_socket, dest_addr, my_ID)
	delay = receive_one_ping(my_socket, my_ID, timeout)
	my_socket.close()
	return delay
	
def checkit(addr,rtable):
	try:
		result=do_one(addr, TIMEOUT, rtable)
		if (result==TIMEOUT):
			return 1
		else:
			return 0
	except socket.error, (errno):
		if (errno==50): return 4
		if (errno==-5): return 2
		if (errno==65): return 3
		else:
			return 1
