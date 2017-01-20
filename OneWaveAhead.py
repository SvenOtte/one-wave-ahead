#!/usr/bin/python
import time
import socket
import sys
import re
from sense_hat import SenseHat

sense = SenseHat()
tdDefault = 0.1     # Default time between sent messages
tcpTimeout = 5.0    # Timeout for inactive TCP socket
tcpConnectTimeout = 60.0        # Wait 60 seconds for a connection then exit
talker = "WI"

sense.set_rotation(0)  # Initial correction of north direction of compass against ship
sense.clear()

# default readings from sensors 
sensor_pressure = 1013.0   # hPa
sensor_temp     = 20.0     # Celsius

def add_checksum(sentence):
 
    """ Remove any newlines """
    if re.search("\n$", sentence):
        sentence = sentence[:-1]
 
    nmeadata,cksum = re.split('\*', sentence)
 
    calc_cksum = 0
    for s in nmeadata:
        calc_cksum ^= ord(s)
 
    """ Return the nmeadata, the checksum from
        sentence, and the calculated checksum
    """
    return nmeadata + "*{:02X}".format(calc_cksum)

def get_MDA(p, t):
#/*Wind speed, meters/second
#**Wind speed, knots
#**Wind direction,
#**degrees Magnetic
#**Wind direction, degrees True
#**$
#**--
#**MDA,x.x,I,x.x,B,x.x,C,x.x,C,x.x,x.x,x.x,C,x.x,T,x.x,M,x.x,N,x.x,M*hh<CR><LF>
#**    |   |  |  |          Dew point, degrees C
#**    |   |  |  |          Absolute humidity, percent
#**    |   |  |  |          Relative humidity, percent
#**    |   |  |  |        Water temperature, degrees C
#**    |   |  |  |          Air temperature, degrees C
#**    |   |  |----Barometric pressure, bars
#**    |----- Barometric pressure, inches of mercur
    nmea_mda = "WIMDA,,,{:01.4f},B,{:02.1f},C,,,,,,,,,,,,,,*00".format(p/1000, t)
    nmea_mda = "$" + add_checksum(nmea_mda)
    return nmea_mda

def get_XDR(t,p,r):
#XDR - Transducer Measurement
#
#        1 2   3 4            n
#        | |   | |            |
# $--XDR,a,x.x,a,c--c, ..... *hh<CR><LF>
#
# Field Number: 
#  1) Transducer Type
#    temperature C
#    angular displacement A
#    linear displacement D
#    frequency F
#    force N
#    pressure P
#    flow rate R
#    tachometer T
#    humidity H
#    volume V
#  2) Measurement Data
#  3) Units of measurement
#    C = degrees Celsius
#    D = degrees ("-" = anticlockwise)
#    M = meters ("-" = compression)
#    H = Hertz
#    N = Newtons ("-" = compression)
#    B = Bars ("-" = vacuum)
#    l = liters/second
#    R = RPM
#    P = Percent
#    M = cubic meters
#  4) Name of transducer
#     NKE style of XDR Airtemp "AirTemp"
#     NKE style of XDR Pitch (=Nose up/down) "PTCH"
#     NKE style of XDR Heel "ROLL"
#  x) More of the same
#  n) Checksum 
    nmea_xdr = "INXDR,C,{:02.1f},C,AirTemp,A,{:03.1f},D,PTCH,A,{:03.1f},D,ROLL,*00".format(t,p,r)
    nmea_xdr = "$" + add_checksum(nmea_mta)
    return nmea_xdr

def get_HDM(d):
#HDM - Heading - Magnetic
#
#        1   2 3 
#        |   | | 
# $--HDM,x.x,M*hh<CR><LF>
#
# Field Number:  
#  1) Heading Degrees, magnetic 
#  2) M = magnetic 
#  3) Checksum
    nmea_hdm = "IIHDM,{:02.1f},M*00".format(d)
    nmea_hdm = "$" + add_checksum(nmea_hdm)
    return nmea_hdm

def get_MMB(p):
#Barometer: 
#$IIMMB,x.x,I,x.x,B*hh
#                I   I   I__I_Atmospheric pressure in bars 
#                I_ I_Atmospheric pressure in inches of mercury 
    nmea_mmb = "WIMMB,,,{:01.4f},B,*00".format(p/1000)
    nmea_mmb = "$" + add_checksum(nmea_mmb)
    return nmea_mmb

def usage():
    print("USAGE:")
    print("NMEA_Temp.py IP_Address Port# [Sleep time [TCP]]")
    print("Sleep time is the delay in seconds between UDP messages sent.")
    print("Sleep time defaults to 0.1 seconds")
    print("If three letter string after sleep time is TCP then TCP/IP packets are sent")
    print("else UDP packets are sent.")
    return

def udp(UDP_IP, UDP_PORT, delay):
    print(['UDP target IP:', UDP_IP])
    print(['UDP target port:', str(UDP_PORT)])
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    print("Type Ctrl-C to exit...")
    while True :
        try:
            temp = sense.get_temperature_from_pressure()
            pressure = sense.get_pressure()
            magnetic_compass = round(sense.get_compass(), 0)
            yaw,pitch,roll=sense.get_orientation().values()

            nmea = get_MDA(pressure, temp)
#            print(nmea)
            nmea = nmea.strip()
            nmea = nmea + u"\r\n"
            sock.sendto(nmea.encode("utf-8"),(UDP_IP, UDP_PORT))

            nmea = get_MMB(pressure)
#            print(nmea)
            nmea = nmea.strip()
            nmea = nmea + u"\r\n"
            sock.sendto(nmea.encode("utf-8"),(UDP_IP, UDP_PORT))

            nmea = get_MTA(temp)
#            print(nmea)
            nmea = nmea.strip()
            nmea = nmea + u"\r\n"
            sock.sendto(nmea.encode("utf-8"),(UDP_IP, UDP_PORT))

            nmea = get_HDM(magnetic_compass)
#            print(nmea)
            nmea = nmea.strip()
            nmea = nmea + u"\r\n"
            sock.sendto(nmea.encode("utf-8"),(UDP_IP, UDP_PORT))

            nmea = get_XDR(temp)
#            print(nmea)
            nmea = nmea.strip()
            nmea = nmea + u"\r\n"
            sock.sendto(nmea.encode("utf-8"),(UDP_IP, UDP_PORT))

            time.sleep(delay)

        except KeyboardInterrupt:
            sock.close()
            return True
        except Exception as msg:
            print(msg)
            sock.close()
            return False

def tcp(TCP_IP, TCP_PORT, delay):
    if TCP_IP == None:
        TCP_IP = socket.gethostname()

    server_address = (TCP_IP, TCP_PORT)

#    print(['TCP target IP:%s:%d', server_address])
#    print(['TCP target port:', str(TCP_PORT)])
    lsock = socket.socket(socket.AF_INET, # Internet
                          socket.SOCK_STREAM) # TCP
    lsock.settimeout(tcpConnectTimeout)
    try:
        lsock.bind(server_address)
        lsock.listen(1)
        print(["Server is waiting up to " + repr(tcpConnectTimeout) + "S for a connection at:", server_address]);
        conn, addr = lsock.accept()
    except socket.error as msg:
        print(msg)
        lsock.close()
        return False

    print(['Connecting to:', addr]);
    print("Type Ctrl-C to exit...")
    while True:
        try:
            temp = sense.get_temperature_from_pressure()
            pressure = sense.get_pressure()
            nmea = get_MDA(pressure, temp)
            print(nmea)
            conn.send(nmea.encode("utf-8"))
            nmea = get_MTA(temp)
            print(nmea)
            conn.send(nmea.encode("utf-8"))
            time.sleep(delay)
        except KeyboardInterrupt:
            conn.close()
            lsock.close()
            return True
        except Exception as msg:
            print(msg)
            conn.close()
            lsock.close()
            return False

if len(sys.argv) < 3:
    print(sys.argv)
    usage()
    sys.exit()

if len(sys.argv) > 3:
    td = float(sys.argv[3])
else:
    td = tdDefault        # default time between messages

if len(sys.argv) > 4:
    mode = sys.argv[4]
else:
    mode = "UDP"

ip = sys.argv[1]
port = sys.argv[2]

print "IP:", ip
print "Port:" , port
print "Delay:" , td
print "Using mode:", mode

rCode = False

if mode.upper() == "UDP":
    rCode = udp(ip, int(port), td)

if mode.upper() == "TCP":
    rCode = tcp(ip, int(port), td)

if rCode == True:
    print("Exiting cleanly.")
else:
    print("Something went wrong, exiting.")

sys.exit()
