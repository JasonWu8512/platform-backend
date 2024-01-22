# -*- coding: utf-8 -*-
# @Time    : 2020/11/30 11:00 上午
# @Author  : zoey
# @File    : fileHandle.py
# @Software: PyCharm
import os
import xmind


def store_upload_tmp_file(file: object, module: str):
    # 缓存上传需要解析的临时文件
    item_file = os.path.join(os.getcwd(), f'{module}_tmp.xmind')
    # 创建一个文件，将上传文件的缓存内容写入新文件
    destination = open(item_file, 'wb+')
    for chunk in file.chunks():
        destination.write(chunk)
    destination.close()
    return item_file


def dict_ite(dicts, topic):
    for key in dicts:
        # Create a topic with key
        subtopic = topic.addSubTopic()
        subtopic.setTitle(key)
        if isinstance(dicts[key], dict):  # if the key is a dict, then
            dict_ite(dicts[key], subtopic)
            return True


def casejson2xmin(casejson, filename):
    """
    把指定casejson转成xmind文件
    :param casejson:
    :param filename:
    :return:
    """
    file_str = os.path.join(os.getcwd(), f'{filename}.xmind')
    workbook = xmind.load(file_str)
    sheet = workbook.getPrimarySheet()  # get the first sheet
    sheet.setTitle(filename)  # set its title
    rtopic_sheet = sheet.getRootTopic()  # get the root topic of this sheet
    rtopic_sheet.setTitle(filename)  # set its title

    if dict_ite(casejson, rtopic_sheet):
        xmind.save(workbook, file_str)
        return file_str
    else:
        return False

# if __name__ == '__main__':
#     data = casejson2xmin(casejson={"H1":1,"H2":2,"H3":{"H21":1,"H22":22,"H23":{"H31":1}}}, filename='temp')
