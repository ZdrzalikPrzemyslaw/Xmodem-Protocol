import serial
import console_IO
import time
import crc16
import sys


checksumType = ""


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
DLE = b'\x10'
NAK = b'\x15'
CAN = b'\x18'
CRC = b'C'


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


def read_data(ser, previous_block_number = 0):
    return_val = __read_data(ser, previous_block_number)
    ser.read(ser.in_waiting)
    return return_val


def __read_data(ser, previous_block_number = 0):
    if checksumType == "CRC":
        block = ser.read(133)
    else:
        block = ser.read(132)
    print(block)
    if len(block) == 0:
        print("ERR0")
        return "EMPTY"
    if block[0].to_bytes(1, 'big') == EOT:
        print("ERR1")
        return EOT
    if block[0].to_bytes(1, 'big') == CAN:
        print("ERR2")
        return CAN
    if block[0].to_bytes(1, 'big') == SOH:
        if not check_ctrl_sum(block):
            print("ERR3")
            return NAK
        if not check_number(block, previous_block_number):
            print("ERR4")
            return NAK
        if checksumType == "CRC":
            block = block[3:-2]
        else:
            block = block[3:-1]
        return block
    print("ERR5")
    return NAK


def strip_ctrl_sum(block):
    global checksumType
    if checksumType == "algebraic":
        ctrl_sum = block[-1]
        block_clean = block[3:-1]
        return block_clean, ctrl_sum
    elif checksumType == "CRC":
        ctrl_sum = block[-1] + block[-2] * 256
        block_clean = block[3:-2]
        return block_clean, ctrl_sum
        pass
    return 0, 0


def check_ctrl_sum(block):
    block, ctrl_sum = strip_ctrl_sum(block)
    if suma_kontrolna(block) == ctrl_sum:
        return True
    return False


def check_number(block, previous_number):
    if not block[1] == previous_number + 1:
        return False
    if not (block[1] + block[2]) == 255:
        return False
    return True


def init_serial(port, baudrate = 19200, timeout = 3):
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
    port = console_IO.choose_COM()
    global checksumType
    ser = init_serial(port = port, timeout = 3)
    checksumType = console_IO.choose_checksum()
    print(checksumType)
    did_work = False
    cala_wiadomosc = b''
    previous_block_number = 1
    for i in range(0, 20):
        if checksumType == "CRC":
            print("WRITING CRC, ", CRC)
            ser.write(CRC)
        else:
            print("WRITING NAK, ", NAK)
            ser.write(NAK)
        block = read_data(ser)
        if block != "EMPTY" and block != NAK and block != EOT and block != CAN:
            print("Transfer of block ", previous_block_number, " succesful")
            cala_wiadomosc += block
            ser.write(ACK)
            did_work = True
            break
        elif block == EOT or block == CAN:
            print("error, exiting")
            exit(123)
        else:
            time.sleep(1)
    ser.timeout = 1
    empty_counter = 0
    while did_work:
        block = read_data(ser, previous_block_number)
        if block == NAK:
            print("Invalid packet, sending NAK")
            ser.write(NAK)
        elif block == EOT:
            print("Recieved EOT, transmision over")
            ser.write(ACK)
            break
        elif block == CAN:
            print("Recieved CAN, transmision over")
            ser.write(ACK)
            break
        elif block == "EMPTY":
            empty_counter += 1
            print("Invalid packet, empty, sending NAK")
            ser.write(NAK)
            if empty_counter > 9:
                print("Didn't Recieve anything, sending CAN and exiting")
                ser.write(CAN)
                break
        else:
            print("Transfer of block ", previous_block_number + 1, " succesful")
            previous_block_number += 1
            if previous_block_number == 255:
                previous_block_number = 0
            cala_wiadomosc += block
            ser.write(ACK)
        if block != "EMPTY":
            empty_counter = 0
    if len(cala_wiadomosc) > 0:
        while cala_wiadomosc[-1] == 0x1A:
            cala_wiadomosc = cala_wiadomosc[:-1]
    print(cala_wiadomosc.decode())
    print("wybierz plik do zapisu")
    try:
        plik = open(console_IO.choose_file(), "wb+")
        plik.write(cala_wiadomosc)
        plik.close()
    except IOError:
        print("wrong file name, using default savefile.txt")
        try:
            plik = open("savefile.txt", "wb+")
            plik.write(cala_wiadomosc)
            plik.close()
        except IOError:
            print("Can't write to file")
    ser.close()
    exit(1)


if __name__ == "__main__":
    __main()
