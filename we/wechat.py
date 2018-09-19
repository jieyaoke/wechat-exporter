# -*- coding: utf-8 -*-

import os
import sqlite3
import re
import xmltodict
import calendar
import biplist
from datetime import datetime

from we.utils import logger
from we.utils import id_to_digest


class RecordType:
    SYSTEM = 10000
    SHORT_VIDEO = 62
    CALL = 50
    LINK = 49
    LOCATIOM = 48
    EMOTION = 47
    VIDEO = 43
    CARD = 42
    VOICE = 34
    IMAGE = 3
    TEXT = 1

RecordTypeCN = {
    RecordType.SYSTEM: u'系统消息',
    RecordType.SHORT_VIDEO: u'小视频',
    RecordType.CALL: u'语音电话/视频电话',
    RecordType.LINK: u'链接/红包',
    RecordType.LOCATIOM: u'位置',
    RecordType.EMOTION: u'动画表情',
    RecordType.VIDEO: u'视频',
    RecordType.CARD: u'名片',
    RecordType.VOICE: u'语音',
    RecordType.IMAGE: u'图片',
    RecordType.TEXT: u'文本',
}

FriendTypeExlude = (
    0,
    # 1,
    2, # groups etc
    4, # friends only in group chat
    6, # friends only in group chat
    64, # 语音提醒
)


class WechatParser(object):

    def __init__(self, path, user_id):
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            raise IOError('Path `%s` not exist for user %s' % (self.path, user_id))
        self.user_id = user_id
        self.user_hash = id_to_digest(user_id)

    def get_labels(self):
        plist_path = self.path + '/%s/contactlabel.list' % self.user_hash
        pl = biplist.readPlist(plist_path)
        obj_idxs = pl['$objects'][1]['NS.objects']

        label_map = {}
        for idx in obj_idxs:
            idx = int(idx)
            label_map[pl['$objects'][idx]['m_uiID']] = pl['$objects'][idx+1]

        return label_map

    def get_remark_list(self, remark_origin):
        index = 0
        remark_list = []
        while (True):
            index += 1
            if (index > len(remark_origin)):
                break
            n = ord(remark_origin[index])
            index += 1
            remark_list.append(remark_origin[index:index + n].decode("utf-8"))
            index += n
        return remark_list

    def get_friends(self):
        chat_db = self.path + '/%s/DB/WCDB_Contact.sqlite' % self.user_hash
        logger.debug('DB path %s' % chat_db)
        conn = sqlite3.connect(chat_db)

        friends = []
        # for row in conn.execute('SELECT f.*,fe.ConStrRes2, fe.ConRemark FROM Friend as f JOIN Friend_Ext as fe USING(UsrName) WHERE `Type` NOT IN %s AND `UsrName` NOT LIKE "gh_%%"' % FriendTypeExlude.__str__()):
        for row in conn.execute('SELECT * FROM Friend WHERE `certificationFlag` = 0 AND `type` NOT IN %s AND `userName` NOT LIKE "gh_%%" AND `userName` NOT LIKE "%%@chatroom"' % FriendTypeExlude.__str__()):
            # label_pattern = '<LabelList>(.*)</LabelList>'
            # label_list_str = re.search(label_pattern, row[4], re.MULTILINE).group(1)
            # label_list = label_list_str.split(',')
            # label_list = [int(label_id) for label_id in label_list if label_id]

            # avatar_pattern = '<HeadImgUrl>(.*)</HeadImgUrl>'
            # avatar_url = re.search(avatar_pattern, row[8], re.MULTILINE).group(1)

            remark_list = self.get_remark_list(row[7])
            if len(remark_list) != 8:
                continue
            label_list = [int(i.encode('utf-8')) for i in remark_list[7].split(',') if i]
            friend = dict(
                id=row[0] if len(remark_list) <= 1 or remark_list[1] == u"" else remark_list[1],
                # id=row[2],
                nickname=remark_list[0],
                gender=row[6],
                type=row[2],
                label_ids = label_list,
                remark = remark_list[2] if len(remark_list) > 2 else u"",
                avatar_url = row[8],
            )
            friends.append(friend)
        return friends

    def get_chatrooms(self):
        chat_db = self.path + '/%s/DB/WCDB_Contact.sqlite' % self.user_hash
        logger.debug('DB path %s' % chat_db)
        conn = sqlite3.connect(chat_db)

        friends = []
        for row in conn.execute('SELECT * FROM `Friend` WHERE `userName` LIKE "%chatroom"'):
            remark_list = self.get_remark_list(row[7])
            friend = dict(
                id=row[0],
                nickname=remark_list[0],
                type=row[10],
            )
            friends.append(friend)
        return friends

    def get_chatroom_friends(self, chatroom_id):
        session_db = self.path + '/%s/session/session.db' % self.user_hash
        logger.debug('DB path %s' % session_db)
        group_table = 'SessionAbstract'
        conn = sqlite3.connect(session_db)

        # GET group users nickname xml file
        c = conn.execute('SELECT * FROM %s WHERE UsrName="%s"' % (group_table, chatroom_id))
        row = c.fetchone()
        session_path = "" if row[5] is None else row[5]
        full_session_path = self.path + '/%s%s' % (self.user_hash, session_path)
        logger.debug('Bin path %s' % full_session_path)

        f = open(full_session_path, 'r')
        raw_xml = f.read()
        pattern = '<RoomData>.*</RoomData>'
        chatroom_xml = re.search(pattern, raw_xml, re.MULTILINE).group()
        xml_dict = xmltodict.parse(chatroom_xml)

        chat_db = self.path + '/%s/DB/WCDB_Contact.sqlite' % self.user_hash
        conn2 = sqlite3.connect(chat_db)

        friends = []
        for member in xml_dict['RoomData']['Member']:
            c2 = conn2.execute('SELECT * FROM `Friend` WHERE userName="%s"' % member['@UserName'])
            row2 = c2.fetchone()
            remark_list = [None]
            if row2 is not None:
                remark_list = self.get_remark_list(row2[7])
            friend = dict(
                id=member['@UserName'],
                nickname=remark_list[0],
            )
            friends.append(friend)
        return friends

    def get_friend_records(self):
        pass

    def get_chatroom_records(self, chatroom_id, start=datetime(2000, 1, 1), end=datetime(2050, 1, 1)):
        chatroom_hash = id_to_digest(chatroom_id)
        chatroom_table = 'Chat_' + chatroom_hash

        if start is None:
            start = datetime(2000, 1, 1)
        if end is None:
            end = datetime(2050, 1, 1)
        start = calendar.timegm(start.utctimetuple())
        end = calendar.timegm(end.utctimetuple())

        chat_db = self.path + '/%s/DB/MM.sqlite' % self.user_hash
        logger.debug('DB path %s' % chat_db)
        conn = sqlite3.connect(chat_db)

        records = []
        id_contained_types = (RecordType.TEXT, RecordType.IMAGE, RecordType.VOICE,
                              RecordType.CARD, RecordType.EMOTION, RecordType.LOCATIOM,
                              RecordType.LINK)
        for row in conn.execute("SELECT * FROM %s WHERE CreateTime BETWEEN '%s' and '%s'" % (chatroom_table, start, end)):
            created_at, msg, msg_type, not_self = row[3], row[4] ,row[7], row[8]
            user_id = None

            # split out user_id in msg
            if not_self and msg_type in id_contained_types:
                if msg_type == 48:
                    msg = row[4]
                    continue
                user_id, msg = row[4].split(':\n', 1)

            # TODO: get user_id in non id_contained_types

            if not not_self:
                user_id = self.user_id

            record = dict(
                user_id=user_id,
                msg=msg,
                type=msg_type,
                not_self=not_self,
                created_at=created_at
            )
            records.append(record)
        return records
