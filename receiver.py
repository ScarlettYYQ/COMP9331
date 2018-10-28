import time
from socket import socket, AF_INET, SOCK_DGRAM
#import random
import sys
import os
import pickle

class PackageSTP:
	def __init__(self, sequence, acknowledge, syn, ack, fin, data):
		self.sequence = sequence
		self.acknowledge = acknowledge
		self.syn = syn
		self.ack = ack
		self.fin = fin
		self.data = data
class checksumpacket:
	def __init__(self, STP):
		self.sequence = STP.sequence
		self.acknowledge = STP.acknowledge
		self.syn = STP.syn
		self.ack = STP.ack
		self.fin = STP.fin
		self.data = STP.data
				
class receiver:
	
	def __init__(self, receiver_port, filename):
			self.receiver_port = int(receiver_port)
			self.filename = filename
			self.beginTime = None
			self.Totalsegments=0
	
	def flagNUM(self,S,A,F):
		self.Flag=''
		if S==True:
			self.Flag+='S'
		if A==True:
			self.Flag+='A'
		if F==True:
			self.Flag+='F'
		if S!=True and A!=True and F!= True:
			self.Flag='D'
	
	def handshake(self):
		STPpacket = self.receivepacket()
		if STPpacket.syn == True:
			self.sendpacket(0, STPpacket.sequence+1, True, True, False, '')

			STPpacket = self.receivepacket()
			if STPpacket.acknowledge == 1 and STPpacket.syn == False and STPpacket.ack == True and STPpacket.fin == False and STPpacket.data == '':
				self.dataStartSeq = 2
				return self.beginTime,STPpacket.acknowledge,self.Totalsegments

		
	def sendpacket(self,sequence, acknowledge, syn, ack, fin, data):
		self.flagNUM(syn,ack,fin)
		STPpacket = pickle.dumps(PackageSTP(sequence, acknowledge, syn, ack, fin, data))
		socket.sendto(STPpacket, self.sender_addr)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd',(time.time()-self.beginTime),self.Flag,sequence,len(data),acknowledge))
	
	def receivepacket(self):
		
		STPpacket, addr = socket.recvfrom(2048)	
		if self.beginTime == None:
			self.beginTime = time.time()
		self.Totalsegments+=1	
		self.sender_addr = addr
		STPpacket = pickle.loads(STPpacket)
		self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
		
		return STPpacket
		
class ReceiveData:	
	def __init__(self,receiver_port, filename,beginTime,startwaiting):
		self.receiver_port = int(receiver_port)
		self.filename = filename
		self.beginTime = beginTime
		self.waiting=startwaiting##from handshake
		self.Totalsegments=0
		self.datatotal=0
		self.errortotal=0
		self.Dupdata=0
		self.DupACK=0
		
	def flagNUM(self,S,A,F):
				self.Flag=''
				if S==True:
					self.Flag+='S'
				if A==True:
					self.Flag+='A'
				if F==True:
					self.Flag+='F'
				if S!=True and A!=True and F!= True:
					self.Flag='D'
	
	
	
	def checksum(self,source_bin):
			sum = 0
			max_count = (len(source_bin)//2) * 2 
			counter = 0
			while counter < max_count:
				val = source_bin[counter + 1] * 256 + source_bin[counter]
				sum = sum + val
				sum = sum & 0xffffffff 
				counter = counter + 2 
			if max_count < len(source_bin):
				sum = sum + source_bin[len(source_bin) - 1]
			sum = (sum >> 16) + (sum & 0xffff)
			sum = sum + (sum >> 16)
			checksum = ~sum
			checksum = checksum & 0xffff
			return checksum
	
	def Send(self,sequence,acknowledge,syn,ack,fin,data,s):
		self.flagNUM(syn,ack,fin)
		a='snd'+s
		STPpacket = pickle.dumps(PackageSTP(sequence, acknowledge, syn, ack, fin, data))
		socket.sendto(STPpacket, self.sender_addr)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format(a,(time.time()-self.beginTime),self.Flag,sequence,len(data),acknowledge))
								
	def Transport(self):
		
		self.nextSeq=0
		self.ACKed=[]
		self.drop=[]
		self.buffer={}
		self.data={}
		self.key=[]
		self.alreadysend=[]
#		if self.waiting==1:
		while True:
			STPpacket, addr = socket.recvfrom(2048)
			self.Totalsegments+=1
#			checksum=sum(STPpacket)&0xffff
#			print('checksum:',checksum)
			self.sender_addr = addr
			STPpacket = pickle.loads(STPpacket)
#			tempPacket= pickle.dumps(checksumpacket(STPpacket))
			checksum=self.checksum(STPpacket.data)
			
			print('checksum:',checksum,STPpacket.checksum)
			print('waiting: ',self.waiting,'Rec:',STPpacket.sequence)
			self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)			
			# ending
			if STPpacket.fin==True:
				with open(self.filename, 'wb') as file:	
					print(sorted(set(self.key)))
					self.lengthdata=0				
					for m in sorted(set(self.key)):
						self.lengthdata+=len(self.data[m])
						file.write(self.data[m])
				if self.FIN(STPpacket):
					L=[self.lengthdata,self.Totalsegments,self.datatotal,self.errortotal,self.Dupdata,self.DupACK]
					return L
			self.datatotal+=1
			if STPpacket.sequence in self.buffer or STPpacket.sequence in self.data:
				self.Dupdata+=1
				if self.waiting not in self.alreadysend:
					self.alreadysend.append(self.waiting)
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','')
				else:
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','/DA')
					self.DupACK+=1
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv/DA',(time.time()-self.beginTime),'D',STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
			if STPpacket.checksum!=checksum:
				self.errortotal+=1
				print('no data')
#				if self.waiting not in self.alreadysend:
#					self.alreadysend.append(self.waiting)
#					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','')
#				else:
#					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','/DA')
#					self.DupACK+=1
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv/corr',(time.time()-self.beginTime),'D',STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
				
			elif STPpacket.sequence==self.waiting:

				print('yes')
#				if STPpacket.sequence not in self.ACKed:
#				self.ACKed.append(STPpacket.sequence)
				self.key.append(STPpacket.sequence)
				self.data[STPpacket.sequence]=STPpacket.data
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),'D',STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))

				b=STPpacket.sequence+len(STPpacket.data)
				while b in self.buffer:
					print('remove buffer:',b)
					self.key.append(b)
					self.data[b]=self.buffer[b]
					length=len(self.buffer[b])
					del self.buffer[b]
					b+=length
				self.waiting=b
				if self.waiting not in self.alreadysend:
					self.alreadysend.append(self.waiting)
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','')
				else:
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','/DA')
					self.DupACK+=1
					
			elif STPpacket.sequence>self.waiting:
					
				print('buffer')
				self.buffer[STPpacket.sequence]=STPpacket.data
				if self.waiting not in self.alreadysend:
					self.alreadysend.append(self.waiting)
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','')
				else:
					self.Send(STPpacket.acknowledge, self.waiting, False, True, False, '','/DA')
					self.DupACK+=1
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),'D',STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
				
				
	def FIN(self,STPpacket):
		self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
		self.Send(STPpacket.acknowledge, STPpacket.sequence+1, False, True, False, '','')
		self.Send(STPpacket.acknowledge, STPpacket.sequence+1, False, False, True, '','')		
		STPpacket, addr = socket.recvfrom(2048)
		self.Totalsegments+=1
		self.sender_addr = addr
		STPpacket = pickle.loads(STPpacket)
		self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
		return True




def writelog():
	socket.bind(('', int(receiver_port)))
	global log
	log = open('Receiver_log.txt', "w")
	Receiver = receiver(receiver_port, filename)
	beginTime,startwaiting,addnum=Receiver.handshake()
	print("handshake done!")
	Data=ReceiveData(receiver_port, filename ,beginTime,startwaiting)

	L= Data.Transport()
	L[1]+=addnum

	log.write('===============================================================================\n')
	log.write('{:50s}{:5d}\n'.format('Amount of Data Received (bytes)', L[0]))
	log.write('{:50s}{:5d}\n'.format('Total segments received', L[1]))
	log.write('{:50s}{:5d}\n'.format('Data segments received', L[2]))
	log.write('{:50s}{:5d}\n'.format('Data Segments with bit errors', L[3]))
	log.write('{:50s}{:5d}\n'.format('Duplicate data segments received',L[4]))
	log.write('{:50s}{:5d}\n'.format('Duplicate Acks sent', L[5]))
	log.write('===============================================================================\n')
			
	log.close()
	
if len(sys.argv)!=3:
	print('python3 receiver.py receiver_port filename')	
receiver_port = sys.argv[1]
filename = sys.argv[2]	
	
socket = socket(AF_INET, SOCK_DGRAM)
writelog()

