import socket
import json
import os
import datetime
import struct
import decimal
import subprocess

HOST = "172.16.107.27"  #function may not work in Linux systems, change to string with IP adress example: "192.168.0.1"
PORT = 665  #change this to your port

def input_trigger(): #triggers user input

        print("Paste full 'Codec 8' packet to parse it or:")
        print("Type SERVER to start the server or:")
        print("Type EXIT to stop the program")
        device_imei = "default_IMEI"
        user_input = input("waiting for input: ")
        if user_input.upper() == "EXIT":
                print(f"exiting program............")
                exit()

        elif user_input.upper() == "SERVER":
                start_server_trigger()
        else:
                try:
                        if codec_8e_checker(user_input.replace(" ","")) == False:
                                print("Wrong input or invalid Codec8 packet")
                                print()
                                input_trigger()
                        else:
                                codec_8E_packet = user_input.replace(" ", "")
                                io_dict_raw = {}
                                io_dict_raw["device_IMEI"] = device_imei
                                io_dict_raw["server_time"] = time_stamper_for_json()
                                io_dict_raw["data_length"] = "Record length: " + str(int(len(codec_8E_packet))) + " characters" + " // " + str(int(len(codec_8E_packet) // 2)) + " bytes"
                                io_dict_raw["_raw_data__"] = codec_8E_packet
                                json_printer_rawDATA(io_dict_raw, device_imei)
                except Exception as e:
                        print(f"error occured: {e} enter proper Codec8 packet or EXIT!!!")
                        input_trigger()

####################################################
###############__CRC16/ARC Checker__################
####################################################

def crc16_arc(data):
        data_part_length_crc = int(data[8:16], 16)
        data_part_for_crc = bytes.fromhex(data[16:16+2*data_part_length_crc])
        crc16_arc_from_record = data[16+len(data_part_for_crc.hex()):24+len(data_part_for_crc.hex())]

        crc = 0

        for byte in data_part_for_crc:
                crc ^= byte
                for _ in range(8):
                        if crc & 1:
                                crc = (crc >> 1) ^ 0xA001
                        else:
                                crc >>= 1

        if crc16_arc_from_record.upper() == crc.to_bytes(4, byteorder='big').hex().upper():
                print ("CRC check passed!")
                print (f"Record length: {len(data)} characters // {int(len(data)/2)} bytes")
                return True
        else:
                print("CRC check Failed!")
                return False

####################################################

def codec_8e_checker(codec8_packet):
        if str(codec8_packet[16:16+2]).upper() != "8E" and str(codec8_packet[16:16+2]).upper() != "08":
                print()
                print(f"Invalid packet!!!!!!!!!!!!!!!!!!!")
                return False
        else:
                return crc16_arc(codec8_packet)

def imei_checker(hex_imei): #IMEI checker function
        imei_length = int(hex_imei[:4], 16)
#       print(f"IMEI length = {imei_length}")
        if imei_length != len(hex_imei[4:]) / 2:
#               print(f"Not an IMEI - length is not correct!")
                return False
        else:
                pass

        ascii_imei = ascii_imei_converter(hex_imei)
        print(f"IMEI received = {ascii_imei}")
        if not ascii_imei.isnumeric() or len(ascii_imei) != 15:
                print(f"Not an IMEI - is not numeric or wrong length!")
                return False
        else:
                return True

def ascii_imei_converter(hex_imei):
        return bytes.fromhex(hex_imei[4:]).decode()

def start_server_trigger():
        print("Starting server!")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                while True:
                        s.listen()
                        print(f"// {time_stamper()} // listening port: {PORT} // IP: {HOST}")
                        conn, addr = s.accept()
                        conn.settimeout(20) #connection timeout, change this value to close the socket if no DATA is received for X amount of seconds
                        with conn:
                                print(f"// {time_stamper()} // Connected by {addr}")
                                device_imei = "default_IMEI"
                                while True:
                                        try:
                                                data = conn.recv(1280)
                                                print(f"// {time_stamper()} // data received = {data.hex()}")
                                                if not data:
                                                        break
                                                elif imei_checker(data.hex()) != False:
                                                        device_imei = ascii_imei_converter(data.hex())
                                                        imei_reply = (1).to_bytes(1, byteorder="big")
                                                        conn.sendall(imei_reply)
                                                        print(f"-- {time_stamper()} sending reply = {imei_reply}")
                                                elif codec_8e_checker(data.hex().replace(" ","")) != False:
                                                        record_number = int((data.hex().replace(" ", ""))[18:18+2], 16)
                                                        print(f"received records {record_number}")
                                                        print(f"from device IMEI = {device_imei}")
                                                        print()
                                                        record_response = (record_number).to_bytes(4, byteorder="big")
                                                        conn.sendall(record_response)
                                                        print(f"// {time_stamper()} // response sent = {record_response.hex()}")
                                                else:
                                                        print(f"// {time_stamper()} // no expected DATA received - dropping connection")
                                                        break
                                        except:
                                                print(f"// {time_stamper()} // Socket timed out. Closing connection with {addr}")
                                                break


####################################################
###############_End_of_MAIN_Parser_Code#############
####################################################

####################################################
###############_Coordinates_Function_###############
####################################################

def coordinate_formater(hex_coordinate): # Fixed :), hopefuly this works for you too - https://stackoverflow.com/questions/36506910/convert-integer-to-lat-long-geo-position
        coordinate = int(hex_coordinate, 16)
        if coordinate & (1 << 31):
            new_int = coordinate - 2**32
            dec_coordinate = new_int/1e7
        else:
            dec_coordinate = coordinate / 10000000
        return dec_coordinate



####################################################
###############____JSON_Functions____###############
####################################################

def json_printer(io_dict, device_imei): #function to write JSON file with data
        json_data = json.dumps(io_dict, indent=4)
        data_path = "./data/" + str(device_imei)
        json_file = str(device_imei) + "_data.json"
        json_file_s = str(device_imei) + "__data.json"
        if not os.path.exists(data_path):
                os.makedirs(data_path)
        else:
                pass

        if not os.path.exists(os.path.join(data_path, json_file)):
                with open(os.path.join(data_path, json_file), "w") as file:
                        file.write(json_data)
        else:
                with open(os.path.join(data_path, json_file), "a") as file:
                        file.write(json_data)
        with open(os.path.join(data_path, json_file_s), "w") as file:
                file.write(json_data)

        subprocess.run(["sudo", "cp", "/var/www/parser/data/" + str(device_imei) + "/" + str(device_imei) + "__data.json", "/var/www/backend/" + str(device_imei) + "_data.json"], check=True)
        return

def json_printer_rawDATA(io_dict_raw, device_imei): #function to write JSON file with data
#       print (io_dict_raw)
        json_data = json.dumps(io_dict_raw, indent=4)
        data_path = "./data/" + str(device_imei)
        json_file = str(device_imei) + "_RAWdata.json"

        if not os.path.exists(data_path):
                os.makedirs(data_path)
        else:
                pass

        if not os.path.exists(os.path.join(data_path, json_file)):
                with open(os.path.join(data_path, json_file), "w") as file:
                        file.write(json_data)
        else:
                with open(os.path.join(data_path, json_file), "a") as file:
                        file.write(json_data)
        return
####################################################
###############____TIME_FUNCTIONS____###############
####################################################

def time_stamper():
        current_server_time = datetime.datetime.now()
        server_time_stamp = current_server_time.strftime('%H:%M:%S %d-%m-%Y')
        return server_time_stamp

def time_stamper_for_json():
        current_server_time = datetime.datetime.now()
        timestamp_utc = datetime.datetime.utcnow()
        server_time_stamp = f"{current_server_time.strftime('%H:%M:%S %d-%m-%Y')} (local) / {timestamp_utc.strftime('%H:%M:%S %d-%m-%Y')} (utc)"
        return server_time_stamp

def device_time_stamper(timestamp):
        timestamp_ms = int(timestamp, 16) / 1000
        timestamp_utc = datetime.datetime.utcfromtimestamp(timestamp_ms)
        utc_offset = datetime.datetime.fromtimestamp(timestamp_ms) - datetime.datetime.utcfromtimestamp(timestamp_ms)
        timestamp_local = timestamp_utc + utc_offset
        formatted_timestamp_local = timestamp_local.strftime("%H:%M:%S %d-%m-%Y")
        formatted_timestamp_utc = timestamp_utc.strftime("%H:%M:%S %d-%m-%Y")
        formatted_timestamp = f"{formatted_timestamp_local} (local) / {formatted_timestamp_utc} (utc)"

        return formatted_timestamp

def record_delay_counter(timestamp):
        timestamp_ms = int(timestamp, 16) / 1000
        current_server_time = datetime.datetime.now().timestamp()
        return f"{int(current_server_time - timestamp_ms)} seconds"

####################################################
###############_PARSE_FUNCTIONS_CODE_###############
####################################################

def parse_data_integer(data):
        return int(data, 16)

def int_multiply_01(data):
        return float(decimal.Decimal(int(data, 16)) * decimal.Decimal('0.1'))

def int_multiply_001(data):
        return float(decimal.Decimal(int(data, 16)) * decimal.Decimal('0.01'))

def int_multiply_0001(data):
        return float(decimal.Decimal(int(data, 16)) * decimal.Decimal('0.001'))

def signed_no_multiply(data): #need more testing of this function
        try:
                binary = bytes.fromhex(data.zfill(8))
                value = struct.unpack(">i", binary)[0]
                return value
        except Exception as e:
                print(f"unexpected value received in function '{data}' error: '{e}' will leave unparsed value!")
                return f"0x{data}"

####################################################

def fileAccessTest(): #check if script can create files and folders
        try:
                testDict = {}
                testDict["_Writing_Test_"] = "Writing_Test"
                testDict["Script_Started"] = time_stamper_for_json()

                json_printer(testDict, "file_Write_Test")

                print (f"---### File access test passed! ###---")
                input_trigger()

        except Exception as e:
                print ()
                print (f"---### File access error occured ###---")
                print (f"'{e}'")
                print (f"---### Try running terminal with Administrator rights! ###---")
                print (f"---### Nothing will be saved if you decide to continue! ###---")
                print ()
                input_trigger()


def main():
        fileAccessTest()

if __name__ == "__main__":
        main()