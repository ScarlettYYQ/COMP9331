#python3
import time
from socket import socket, AF_INET, SOCK_DGRAM
import random
import sys
import os
import threading
import pickle

class PackageSTP:
	def __init__(self, sequence, acknowledge, checksum,syn, ack, fin, data):
		self.sequence = sequence
		self.acknowledge = acknowledge
		self.syn = syn
		self.ack = ack
		self.fin = fin
		self.data = data
		self.checksum=checksum

class sender:	
	def __init__(self,receiver_host_ip, receiver_port):
			self.receiver_host_ip = receiver_host_ip
			self.receiver_port = int(receiver_port)
			self.transmitted=0			
			
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
		self.beginTime = time.time()
		self.sendpacket(0, 0, True, False, False, '')		
		STPpacket = self.receivepacket()
		if STPpacket.acknowledge == 1 and STPpacket.syn == True and STPpacket.ack == True and STPpacket.fin == False and STPpacket.data == '':
			self.sendpacket(STPpacket.acknowledge, STPpacket.sequence+1 , False, True, False,'')
			return (STPpacket.acknowledge,STPpacket.sequence+1,self.beginTime,self.transmitted)
					
	def sendpacket(self,sequence, acknowledge, syn, ack, fin, data):
		self.flagNUM(syn,ack,fin)
		STPpacket = pickle.dumps(PackageSTP(sequence, acknowledge,0, syn, ack, fin, data))		
		self.transmitted+=1
		socket.sendto(STPpacket, (self.receiver_host_ip, self.receiver_port))
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd',(time.time()-self.beginTime),self.Flag,sequence,len(data),acknowledge))
			
	def receivepacket(self):
		STPpacket, addr = socket.recvfrom(2048)
		STPpacket = pickle.loads(STPpacket)
		self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
		return STPpacket
			
class SendData:	
	def __init__(self,SeqStart,AckStart, receiver_host_ip, receiver_port, filename, MWS, MSS, gamma,beginTime,pDrop,pDuplicate, pCorrupt,pOrder,maxOrder,pDelay,maxDelay,seed):
		self.receiver_host_ip = receiver_host_ip
		self.receiver_port = int(receiver_port)
		self.filename = filename      		
		self.MWS = int(MWS)			# max window size
		self.MSS = int(MSS) 		# max segment size
		self.gamma = int(gamma)
		self.SeqStart=SeqStart
		self.AckNOW=AckStart
		self.beginTime=beginTime
		self.Lock=threading.RLock()
		self.pDrop=float(pDrop)
		self.pDuplicate=float(pDuplicate)
		self.pCorrupt=float(pCorrupt)
		self.pOrder=float(pOrder)
		self.maxOrder=int(maxOrder)
		self.pDelay=float(pDelay)
		self.maxDelay=int(maxDelay)
		self.seed=seed
		random.seed(self.seed)
		self.EstimatedRTT=500/1000
		self.DevRTT=250/1000
		self.TimeoutInterval=self.EstimatedRTT+self.gamma*self.DevRTT
		self.transmitted=0
		self.PLDtotal=0
		self.droptotal=0
		self.corrupttotal=0
		self.reordertotal=0
		self.Duplicatedtotal=0
		self.Delayedtotal=0
		self.timeouttotal=0
		self.fasttotal=0
		self.DupACKtotal=0
				
	def checksum(self,source_bin):
		m = 0
		max_count = (len(source_bin)//2) * 2 
		counter = 0
		while counter < max_count:
			val = source_bin[counter + 1] * 256 + source_bin[counter]
			m = m + val
			m = m & 0xffffffff 
			counter = counter + 2 
		if max_count < len(source_bin):
			m = m + source_bin[len(source_bin) - 1]
		m = (m >> 16) + (m & 0xffff)
		m = m + (m >> 16)
		checksum = ~m
		checksum = checksum & 0xffff
		return checksum
			
	def flagNUM(self,S,A,F):
				self.Flag=''
				if A==True:
					self.Flag+='A'
				if F==True:
					self.Flag+='F'
				if S!=True and A!=True and F!= True:
					self.Flag='D'
		
	def Send(self,sequence,acknowledge,syn,ack,fin,data,s):
		self.flagNUM(syn,ack,fin)
		checksum=self.checksum(data)
		STPpacket = pickle.dumps(PackageSTP(sequence, acknowledge,checksum, syn, ack, fin, data))
		socket.sendto(STPpacket, (self.receiver_host_ip, self.receiver_port))
		s='snd'+s
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format(s,(time.time()-self.beginTime),self.Flag,sequence,len(data),acknowledge))
						
	def Receive(self):
		print('start 2')
		self.DArcv={}
		for i in self.packetNode:
			self.DArcv[i]=0
		Recived=[]
		self.maxACK=0
		while True:		
			STPpacket, addr = socket.recvfrom(2048)
			STPpacket = pickle.loads(STPpacket)
			self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
			if int(STPpacket.acknowledge)==len(self.data)+1:				
				self.notACK=[]
				self.timestop=1
				print('stop 2')
				break
			if STPpacket.acknowledge>self.maxACK:
				self.maxACK=STPpacket.acknowledge
			if STPpacket.acknowledge not in Recived:
				Recived.append(STPpacket.acknowledge)
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
			else:
				self.DArcv[STPpacket.acknowledge]+=1
				self.DupACKtotal+=1	
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv/DA',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))		
			self.Lock.acquire()
			if STPpacket.acknowledge-self.MSS in self.notACK:
				self.Time=time.time()
				if STPpacket.acknowledge-self.MSS in self.RTTstart:
					SampleRTT=time.time()-self.RTTstart[STPpacket.acknowledge-self.MSS]
					self.RTTstart={}
					self.EstimatedRTT= 0.875*self.EstimatedRTT+0.125*SampleRTT
					self.DevRTT=0.75*self.DevRTT+0.25*abs(SampleRTT-self.EstimatedRTT)
					self.TimeoutInterval=self.EstimatedRTT+self.gamma*self.DevRTT
				leng=len(self.notACK)
				x=sorted(set(self.notACK)).index(STPpacket.acknowledge-self.MSS)
				self.notACK=sorted(set(self.notACK))[x+1:]
				self.rest+=(leng-len(self.notACK))*self.MSS
				self.Lock.release()
			else:
				if self.DArcv[STPpacket.acknowledge]>=3:
					if self.notinOrder==1:
						self.numOrder+=1
					self.DArcv[STPpacket.acknowledge]=0
					self.rest+=len(self.packetNode[STPpacket.acknowledge])
					self.PLD(STPpacket.acknowledge)
					self.fasttotal+=1
				self.Lock.release()
	
	def PLD(self,tempseq):
		if self.Dely==1 :			
			if len(self.packetNode[self.watingDelay[0]])<=self.rest and time.time()-self.timedelay>=self.t:
				self.Send(self.watingDelay[0],self.AckNOW,False,False,False,self.watingDelay[1],'/Del')
				self.transmitted+=1
				self.PLDtotal+=1
				self.Delayedtotal+=1
				self.notACK.append(self.watingDelay[0])
				if self.watingDelay[0]==tempseq:
					self.rest-=len(self.packetNode[self.watingDelay[0]])
				self.Dely=0
				if self.notinOrder==1:
					self.numOrder+=1
		if self.notinOrder==1 : 			
			if len(self.packetNode[self.watingorder[0]])<=self.rest and self.numOrder>=self.maxOrder:						
				self.Send(self.watingorder[0],self.AckNOW,False,False,False,self.watingorder[1],'/rord')
				self.transmitted+=1
				self.PLDtotal+=1
				self.reordertotal+=1
				self.notinOrder=0
				self.notACK.append(self.watingorder[0])
				self.numOrder=0
				if self.watingorder[0]==tempseq:
					self.rest-=len(self.packetNode[self.watingorder[0]])
		if tempseq>=len(self.data):			
			return
		if random.random() < self.pDrop:		
			if len(self.packetNode[tempseq])<=self.rest:
				self.transmitted+=1
				self.PLDtotal+=1
				self.droptotal+=1
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('drop',(time.time()-self.beginTime),'D',tempseq,len(self.packetNode[tempseq]),self.AckNOW))
				self.notACK.append(tempseq)
				self.rest-=len(self.packetNode[tempseq])				 
				if self.notinOrder==1:
					self.numOrder+=1										
		else:
			if random.random() < self.pDuplicate:
				if len(self.packetNode[tempseq])<=self.rest and tempseq-self.MSS in self.packetNode:
#					log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd',(time.time()-self.beginTime),'D',tempseq,len(self.packetNode[tempseq]),self.AckNOW))		
#					log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd/dup',(time.time()-self.beginTime),'D',tempseq,len(self.packetNode[tempseq]),self.AckNOW))	
					self.transmitted+=2	
					self.PLDtotal+=2	
					self.Duplicatedtotal+=1	
					self.Send(tempseq-self.MSS,self.AckNOW,False,False,False,self.packetNode[tempseq-self.MSS],'')			
					self.Send(tempseq-self.MSS,self.AckNOW,False,False,False,self.packetNode[tempseq-self.MSS],'/dup')
					self.notACK.append(tempseq)
					self.rest=self.rest-len(self.packetNode[tempseq])
					if self.notinOrder==1:
						self.numOrder+=1				
			else:
				if random.random() < self.pCorrupt:
					if len(self.packetNode[tempseq])<=self.rest:
						self.flagNUM(False,False,False)
						checksum=self.checksum(self.packetNode[tempseq])
						STPpacket = pickle.dumps(PackageSTP(tempseq,self.AckNOW,checksum-1,False,False,False,self.packetNode[tempseq]))
						if self.notinOrder==1:
							self.numOrder+=1
						self.transmitted+=1
						self.PLDtotal+=1
						self.corrupttotal+=1
						socket.sendto(STPpacket, (self.receiver_host_ip, self.receiver_port))
						log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd/corr',(time.time()-self.beginTime),'D',tempseq,len(self.packetNode[tempseq]),self.AckNOW))
						self.notACK.append(tempseq)					 
				else:
					if random.random() < self.pOrder and self.notinOrder==0 and self.Dely==0:
						if len(self.packetNode[tempseq])<=self.rest:
							self.notinOrder=1
							if (len(self.key)-self.key.index(tempseq)-1)<self.maxOrder:
								self.maxOrder=len(self.key)-self.key.index(tempseq)-1
							self.watingorder=(tempseq,self.packetNode[tempseq])								 						
					else:
						if random.random() < self.pDelay and self.notinOrder==0 and self.Dely==0:
							if len(self.packetNode[tempseq])<=self.rest:
								self.t=random.randint(0,self.maxDelay)/1000
								self.timedelay=time.time()
								self.watingDelay=(tempseq,self.packetNode[tempseq])
								self.Dely=1										 													
						else:
							if len(self.packetNode[tempseq])<=self.rest:
								self.transmitted+=1
								self.PLDtotal+=1
								self.Send(tempseq,self.AckNOW,False,False,False,self.packetNode[tempseq],'')
								if self.notinOrder==1:
									self.numOrder+=1
								self.notACK.append(tempseq)

	def PLDsend(self):
		if self.Dely==1 :
			if len(self.packetNode[self.watingDelay[0]])<=self.rest and time.time()-self.timedelay>=self.t:
				self.Send(self.watingDelay[0],self.AckNOW,False,False,False,self.watingDelay[1],'/Del')
				self.transmitted+=1
				self.PLDtotal+=1
				self.Delayedtotal+=1
				self.notACK.append(self.watingDelay[0])
				self.rest-=len(self.packetNode[self.watingDelay[0]])
				self.Dely=0
				if self.notinOrder==1:
					self.numOrder+=1
		if self.notinOrder==1 : 
			if len(self.packetNode[self.watingorder[0]])<=self.rest and self.numOrder>=self.maxOrder:						
				self.Send(self.watingorder[0],self.AckNOW,False,False,False,self.watingorder[1],'/rord')
				self.transmitted+=1
				self.PLDtotal+=1
				self.reordertotal+=1
				self.notinOrder=0
				self.notACK.append(self.watingorder[0])
				self.rest-=len(self.packetNode[self.watingorder[0]])
				self.numOrder=0
		if self.seq>=len(self.data):
			return
		if random.random() < self.pDrop:
			if len(self.packetNode[self.seq])<=self.rest:
				self.transmitted+=1
				self.PLDtotal+=1
				self.droptotal+=1
				log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('drop',(time.time()-self.beginTime),'D',self.seq,len(self.packetNode[self.seq]),self.AckNOW))
				self.notACK.append(self.seq)
				self.rest-=len(self.packetNode[self.seq])
				self.seq+=self.MSS
				if self.notinOrder==1:
					self.numOrder+=1										
		else:
			if random.random() < self.pDuplicate:
				if len(self.packetNode[self.seq])<=self.rest and self.seq-self.MSS in self.packetNode:	
					self.transmitted+=2	
					self.PLDtotal+=2	
					self.Duplicatedtotal+=1	
#					log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd',(time.time()-self.beginTime),'D',self.seq,len(self.packetNode[self.seq]),self.AckNOW))		
#					log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd/dup',(time.time()-self.beginTime),'D',self.seq,len(self.packetNode[self.seq]),self.AckNOW))
					self.Send(self.seq,self.AckNOW,False,False,False,self.packetNode[self.seq],'')			
					self.Send(self.seq,self.AckNOW,False,False,False,self.packetNode[self.seq],'/dup')
					self.notACK.append(self.seq)
					self.rest=self.rest-1*len(self.packetNode[self.seq])
					self.seq=self.seq+2*self.MSS
					if self.notinOrder==1:
						self.numOrder+=1				
			else:
				if random.random() < self.pCorrupt:
					if len(self.packetNode[self.seq])<=self.rest:
						self.flagNUM(False,False,False)
						checksum=self.checksum(self.packetNode[self.seq])
						STPpacket = pickle.dumps(PackageSTP(self.seq,self.AckNOW,checksum-1,False,False,False,self.packetNode[self.seq]))						
						if self.notinOrder==1:
							self.numOrder+=1
						self.transmitted+=1
						self.PLDtotal+=1
						self.corrupttotal+=1
						socket.sendto(STPpacket, (self.receiver_host_ip, self.receiver_port))
						log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('snd/corr',(time.time()-self.beginTime),'D',self.seq,len(self.packetNode[self.seq]),self.AckNOW))
						self.notACK.append(self.seq)
						self.rest-=len(self.packetNode[self.seq])
						self.seq+=self.MSS
				else:
					if random.random() < self.pOrder and self.notinOrder==0 and self.Dely==0:
						if len(self.packetNode[self.seq])<=self.rest:
							self.notinOrder=1
							if (len(self.key)-self.key.index(self.seq)-1)<self.maxOrder:
								self.maxOrder=len(self.key)-self.key.index(self.seq)-1
							self.watingorder=(self.seq,self.packetNode[self.seq])
							self.seq+=self.MSS						
					else:
						if random.random() < self.pDelay and self.notinOrder==0 and self.Dely==0:
							if len(self.packetNode[self.seq])<=self.rest:
								self.t=random.randint(0,self.maxDelay)/1000
								self.timedelay=time.time()
								self.watingDelay=(self.seq,self.packetNode[self.seq])
								self.Dely=1	
								self.seq+=self.MSS													
						else:
							if len(self.packetNode[self.seq])<=self.rest:
								self.transmitted+=1
								self.PLDtotal+=1
								self.Send(self.seq,self.AckNOW,False,False,False,self.packetNode[self.seq],'')
								if self.notinOrder==1:
									self.numOrder+=1
								self.notACK.append(self.seq)
								self.rest-=len(self.packetNode[self.seq])
								self.seq+=self.MSS
			return
				
	def payloadsend(self):
		print('start 1')
		self.seq=self.SeqStart
		self.rest=self.MWS
		self.notinOrder=self.numOrder=self.TimeStart=self.Dely=0
		self.RTTstart={}
		self.timedelay=time.time()
		while True:
			time.sleep(0.01)
			if self.seq in self.packetNode :
				self.Lock.acquire()
				if self.RTTstart=={}:
					self.RTTstart[self.seq]=time.time()		
				self.PLDsend()												
				if self.TimeStart==0:
					self.Time=time.time()
					self.TimeStart=1				
				self.Lock.release()
			else:
				print(self.Dely,'and',self.notinOrder,self.numOrder,'and rest',self.rest,'and',self.notACK)
				if self.Dely!=0 or self.notinOrder!=0:
					self.Lock.acquire()					
					self.PLDsend()					
					self.Lock.release()																
				else:
					print('stop 1')
					break
		
	def timeout(self):
		print('start 3')
		while self.timestop==0:
			time.sleep(0.001)			
			if  time.time()-self.Time >= self.TimeoutInterval:
				self.Lock.acquire()
				self.timeouttotal+=1
				self.rest+=len(self.packetNode[self.maxACK])
				self.PLD(self.maxACK)	
				self.Time=time.time()
				self.Lock.release()
		print('stop 3')
	
	def Transport(self):
		self.packetNode = {}
		self.key=[]
		with open(self.filename, 'rb') as filename:
			self.data = filename.read()		
		for i in range(0,int(len(self.data)/self.MSS+1)):
			self.key.append(i*self.MSS+self.SeqStart)
			if (i+1)*self.MSS<=len(self.data):
				self.packetNode[i*self.MSS+self.SeqStart] = self.data[i*self.MSS:(i+1)*self.MSS]
			else:
				self.packetNode[i*self.MSS+self.SeqStart] = self.data[i*self.MSS:]
		self.alreadysend=[]
		self.alreadyreceive=[]
		
		self.notACK=[]
		self.timestop=0
		self.Time=time.time()
		l=[threading.Thread(target=self.payloadsend),threading.Thread(target=self.Receive),threading.Thread(target=self.timeout)]
		for i in l:
			i.start()
		for j in l:
			j.join()
		if self.FIN(len(self.data)+1):
			print('stop 123')
		RT=[len(self.data),self.transmitted,self.PLDtotal,self.droptotal,self.corrupttotal,self.reordertotal,self.Duplicatedtotal,self.Delayedtotal,self.timeouttotal,self.fasttotal,self.DupACKtotal]
				
		return(RT)
			
	def FIN(self,finNUM):
		self.finNUM=finNUM
		self.transmitted+=1
		self.Send(self.finNUM, 1, False, False, True, '','')
		STPpacket, addr = socket.recvfrom(2048)
		STPpacket = pickle.loads(STPpacket)
		self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
		log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
		if STPpacket.acknowledge == self.finNUM+1 and STPpacket.syn == False and STPpacket.ack == True and STPpacket.fin == False:
			STPpacket, addr = socket.recvfrom(2048)
			STPpacket = pickle.loads(STPpacket)
			self.flagNUM(STPpacket.syn,STPpacket.ack,STPpacket.fin)
			log.write('{:10s}{:10.2f}         {:5s}{:12d}{:12d}{:12d}\n'.format('rcv',(time.time()-self.beginTime),self.Flag,STPpacket.sequence,len(STPpacket.data),STPpacket.acknowledge))
			if STPpacket.acknowledge == self.finNUM+1 and STPpacket.syn == False and STPpacket.ack == False and STPpacket.fin == True:
				self.transmitted+=1
				self.Send(STPpacket.acknowledge, 2, False, True, False, '','')
		return True

def writelog():
	global log 
	log= open('Sender_log.txt', "w")
	Sender = sender(receiver_host_ip, receiver_port)
	DataSeqStart,DataACKStart,beginTime,handshakesendnum=Sender.handshake()
	Data = SendData(DataSeqStart,DataACKStart, receiver_host_ip, receiver_port, filename, MWS, MSS, gamma,beginTime, pdrop,pDuplicate, pCorrupt,pOrder,maxOrder,pDelay,maxDelay,seed)
	L=Data.Transport()
	L[1]+=handshakesendnum
	log.write('===============================================================================\n')
	log.write('{:50s}{:5d}\n'.format('Size of the file (in Bytes)', L[0]))
	log.write('{:50s}{:5d}\n'.format('Segments transmitted (including drop & RXT)', L[1]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments handled by PLD', L[2]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments Dropped', L[3]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments Corrupted',L[4]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments Re-ordered', L[5]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments Duplicated', L[6]))
	log.write('{:50s}{:5d}\n'.format('Number of Segments Delayed', L[7]))
	log.write('{:50s}{:5d}\n'.format('Number of Retransmissions due to timeout', L[8]))
	log.write('{:50s}{:5d}\n'.format('Number of Fast Retransmissions', L[9]))
	log.write('{:50s}{:5d}\n'.format('Number of Duplicate Acknowledgements received', L[10]))
	log.write('===============================================================================\n')
	
	log.close()

if len(sys.argv)!=15:
	print('python3 sender.py receiver_host_ip receiver_port filename MWS MSS gamma pdrop pDuplicate pCorrupt pOrder maxOrder pDelay maxDelay seed')
	sys.exit()
receiver_host_ip = sys.argv[1]
receiver_port = sys.argv[2]
filename = sys.argv[3]
MWS = sys.argv[4]
MSS = sys.argv[5]
gamma = sys.argv[6]
pdrop = sys.argv[7]
pDuplicate =sys.argv[8]
pCorrupt=sys.argv[9]
pOrder=sys.argv[10]
maxOrder= sys.argv[11]
pDelay=sys.argv[12]
maxDelay=sys.argv[13]
seed = sys.argv[14]
socket = socket(AF_INET, SOCK_DGRAM)
writelog()
