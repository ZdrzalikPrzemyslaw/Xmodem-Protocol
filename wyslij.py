import serial
import console_IO
import crc16
import sys
import time


checksumType = ""


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
DLE = b'\x10'
NAK = b'\x15'
CAN = b'\x18'
CRC = b'C'


def pack_file(file_name):
    lista_pakietow = []
    try:
        plik = open(file_name, "rb")
    except IOError:
        print("wrong file name, using default file.txt")
        plik = open("file.txt", "rb")
    while 1:
        pakiet = plik.read(128)
        if len(pakiet) < 128:
            while len(pakiet) < 128:
                pakiet = bytearray(pakiet)
                pakiet.append(0x1A)
            pakiet = bytes(pakiet)
            lista_pakietow.append(pakiet)
            break
        lista_pakietow.append(pakiet)
    return lista_pakietow


def suma_kontrolna(block):
    global checksumType
    if checksumType == "algebraic":
        suma = 0
        for i in block:
            suma += i
        suma = suma % 256
        return suma
    elif checksumType == "CRC":
        crc = crc16.crc16xmodem(block)
        return crc
        pass
    return 0


def send_packet(ser, packet_nr, packet):
    ctrl_sum = suma_kontrolna(packet)
    global checksumType
    packet_to_send = bytearray(SOH)
    packet_to_send += bytearray(packet_nr.to_bytes(1, 'big'))
    packet_to_send += bytearray((255 - packet_nr).to_bytes(1, 'big'))
    packet_to_send += packet
    if checksumType == "algebraic":
        ctrl_sum = bytearray(ctrl_sum.to_bytes(1, 'big'))
    else:
        ctrl_sum = bytearray(ctrl_sum.to_bytes(2, 'big'))
    packet_to_send += ctrl_sum
    packet_to_send = bytes(packet_to_send)
    ser.write(packet_to_send)


def init_serial(port, baudrate = 19200, timeout = 10):
    ser = serial.Serial()
    ser.baudrate = baudrate
    ser.port = port
    ser.timeout = timeout
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    ser.open()
    return ser


def __main():
    global checksumType
    packed_file = pack_file(console_IO.choose_file())
    ser = init_serial(port = console_IO.choose_COM())
    incoming_msg = b''
    counter = 0
    while incoming_msg != NAK and incoming_msg !=CRC and counter < 6:
        incoming_msg = ser.read(1)
        if incoming_msg == NAK:
            checksumType = "algebraic"
        if incoming_msg == CRC:
            checksumType = "CRC"
        counter += 1
    index = 0
    packet_nr = 1
    if incoming_msg != NAK and incoming_msg != CRC:
        exit(3)
    while index != len(packed_file):
        send_packet(ser, packet_nr, packed_file[index])
        print("NADANO PAKIET nr. ", packet_nr)
        incoming_msg = ser.read()
        print("odpowiedz: ", incoming_msg)
        if incoming_msg == ACK:
            print("received input ACK")
            index += 1
            packet_nr += 1
            if packet_nr == 256:
                packet_nr = 1
            pass
        elif incoming_msg == NAK:
            print("received input NAK")
            pass
        elif incoming_msg == CAN:
            print("CAN")
            print("received CAN, exiting")
            exit(4)
            break
        ser.read(ser.in_waiting)
    ser.timeout = 2
    print("finished transfer")
    while True:
        print("sending EOT")
        ser.write(EOT)
        rid = ser.read()
        if rid == ACK:
            print("received ACK")
            break
        if rid == CAN:
            print("received CAN")
            break
        ser.read(ser.in_waiting)
    ser.close()


if __name__ == '__main__':
    __main()