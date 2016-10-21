#!/usr/bin/python
# coding=utf-8
# 
# author: Allen Feng
# date: 2016-10-21 
# 
# 注意，渠道列表中的任何渠道名称长度不能大于ORIGIN_CHANNEL_NAME的长度
# 
# 原理：
# 1. 读取渠道列表，解压渠道母包，删除掉META-INF/*
# 2. 用真正渠道名替换AndroidManifest.xml中的占位字符串
# 3. 删除AndroidManifest.xml， 覆盖替换渠道名后的AndroidManifest.xml （直接操作AXML文件格式）
# 4. 按照渠道名称重新压缩apk
# 5. apk签名
# 6. zipalign
# 7. 完成一个渠道，拷贝至output目录
# 8. 重复2~7

import os
import shutil
import struct
import datetime

CHANNEL_PREFIX_NAME = "app-"

ORIGIN_CHANNEL_NAME = "ORIGIN_CHANNEL_VALUE"

ORIGIN_APK_NAME = "./origin-apk/app.apk"
EXTRACT_DIR_NAME = "app-origin"

OUT_PUT_DIR_NAME = "./output"
CHANNELS_FILE_NAME = "./channels.txt"
BUILT_DIR_NAME = "./build"

KEYSTORE_FILE = "./keystore/my-release-key.keystore"
STORE_PASSWORD = "123456"
KEY_ALIAS = "my_alias_name"
KEY_PASSWORD = "123456"

def clean_last_built():
    extract_dir_exists = os.path.exists(EXTRACT_DIR_NAME)
    output_dir_exists = os.path.exists(OUT_PUT_DIR_NAME)
    build_dir_exists = os.path.exists(BUILT_DIR_NAME)

    if extract_dir_exists:
        print "remove " + EXTRACT_DIR_NAME
        shutil.rmtree(EXTRACT_DIR_NAME)

    if output_dir_exists:
        print "remove " + OUT_PUT_DIR_NAME
        shutil.rmtree(OUT_PUT_DIR_NAME)

    if build_dir_exists:
        print "remove " + BUILT_DIR_NAME
        shutil.rmtree(BUILT_DIR_NAME)

def create_dir():
    os.makedirs(OUT_PUT_DIR_NAME)
    os.makedirs(BUILT_DIR_NAME)


def extract_apk():
    print "extracting apk..."
    apk_decode_cmd = "unzip -q " + ORIGIN_APK_NAME + " -d " + BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME

    extract_result = os.system(apk_decode_cmd)

    if extract_result == 0:
        print "extracting apk success"
    else:
        print "extracting apk failed"
        sys.exit(-1)

    os.remove(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/META-INF/CERT.RSA")
    os.remove(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/META-INF/CERT.SF")
    os.remove(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/META-INF/MANIFEST.MF")

    shutil.copyfile(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/AndroidManifest.xml", BUILT_DIR_NAME + "/AndroidManifest-origin.xml")

def get_bytes_from_file(filename):
    return bytearray(open(filename, "rb").read())

def create_new_apk(channel):

    origin_data = get_bytes_from_file(BUILT_DIR_NAME + "/AndroidManifest-origin.xml")

    os.remove(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/AndroidManifest.xml")

    replace_axml_string(origin_data, ORIGIN_CHANNEL_NAME, channel)

    with open(BUILT_DIR_NAME + "/AndroidManifest.xml", 'wb') as f:
    	f.write(origin_data)

    shutil.copyfile(BUILT_DIR_NAME + "/AndroidManifest.xml", BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME + "/AndroidManifest.xml")	

    root_work_dir = os.getcwd()

    os.chdir(BUILT_DIR_NAME + "/" + EXTRACT_DIR_NAME)

    output_apk_name = CHANNEL_PREFIX_NAME + channel + ".apk"

    apk_zip_cmd = "zip -q -r ../" + output_apk_name + " *"


    print apk_zip_cmd

    zip_result = os.system(apk_zip_cmd)

    if zip_result == 0:
        print "zip apk success"
    else:
        print "zip apk failed"
        sys.exit(-1)

    os.chdir(root_work_dir)

    sign_cmd = "jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1" \
    + " -keystore " + KEYSTORE_FILE \
    + " -storepass " + STORE_PASSWORD \
    + " -keypass " + KEY_PASSWORD \
    + " " + BUILT_DIR_NAME + "/" + output_apk_name + " " + KEY_ALIAS


    print sign_cmd

    sign_result = os.system(sign_cmd)

    if sign_result == 0:
        print "sign apk success"
    else:
        print "sign apk failed"
        sys.exit(-1)


    verify_cmd = "jarsigner -verify -verbose -certs " + BUILT_DIR_NAME + "/" + output_apk_name

    print verify_cmd

    verify_result = os.system(verify_cmd)

    if verify_result == 0:
        print "verify apk success"
    else:
        print "verify apk failed"
        sys.exit(-1)


    # zipalign -c -v <alignment> existing.apk

    zipalign_cmd = "zipalign -f -v 4 " + BUILT_DIR_NAME + "/" + output_apk_name + " " + OUT_PUT_DIR_NAME + "/" + output_apk_name

    print zipalign_cmd

    zipalign_result = os.system(zipalign_cmd)

    if zipalign_result == 0:
        print "zipalign apk success"
    else:
        print "zipalign apk failed"
        sys.exit(-1)

    verify_zipalign_cmd = "zipalign -c -v 4 " + OUT_PUT_DIR_NAME + "/" + output_apk_name

    print verify_zipalign_cmd

    verify_zipalign_result = os.system(verify_zipalign_cmd)

    if verify_zipalign_result == 0:
        print "verify zipalign apk success"
    else:
        print "verify zipalign apk failed"
        sys.exit(-1)

    shutil.move(BUILT_DIR_NAME + "/" + output_apk_name, OUT_PUT_DIR_NAME + "/" + output_apk_name)

def replace_axml_string(axml_data, old_string, new_string):
    '''
    axml_data: the raw bytearray readed from AndroidManifest.xml
    '''
    new_string_pack = axml_utf16_pack(new_string)
    old_string_pack = axml_utf16_pack(old_string)
    new_string_pack_len = len(new_string_pack)
    old_string_pack_len = len(old_string_pack)
    if old_string_pack_len < new_string_pack_len:
        raise ValueError('new_string cannot be larger than old_string! ')
    pos = 0
    while True:
        pos = find_pack_in_axml(axml_data, old_string_pack, pos)
        if pos < 0:
            break
        axml_data[pos : pos + new_string_pack_len] = new_string_pack[ : new_string_pack_len]
        delta = old_string_pack_len - new_string_pack_len
        if delta:
            axml_data[pos + new_string_pack_len: pos + old_string_pack_len] = bytearray(delta)

def axml_utf16_pack(string):
    pack = bytearray(string.encode('utf-16'))
    str_len_pack = struct.pack('<I', len(string))
    pack[ : 2] = struct.unpack('BB', str_len_pack[ : 2])
    return pack

def find_pack_in_axml(axml_data, pack, start):
    pos = axml_data.find(pack, start, -1)
    return pos


def create_multi_channels():
	with open(CHANNELS_FILE_NAME) as channels_file:
		for channel in channels_file:
			channel = channel.strip('\n')
			print "\n\n>>> creating channel: " + channel
			create_new_apk(channel)
			print "\n\n>>> finish channel: " + channel

start_time = datetime.datetime.now()
clean_last_built()
create_dir()
extract_apk()
create_multi_channels()
end_time = datetime.datetime.now()
total_time = (end_time - start_time).seconds
print ">>> Total time: " + str(total_time) + " seconds\n"




