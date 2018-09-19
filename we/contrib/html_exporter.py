# -*- coding: utf-8 -*-

import os
import shutil
import sys

from jinja2 import Environment, FileSystemLoader

from we.wechat import WechatParser


class HTMLExporter(object):

    def __init__(self, path, user_id, chatroom_id, start_at, end_at):
        self.wechat = WechatParser(path, user_id)
        self.records = self.wechat.get_chatroom_records(chatroom_id, start_at, end_at)
        self.friends = self.wechat.get_chatroom_friends(chatroom_id)

    def export(self, export_path):
        id_nicknames = {friend['id']: friend['nickname'] for friend in self.friends}
        for record in self.records:
            if not record['user_id']:
                continue

            record['nickname'] = id_nicknames.get(record['user_id']) or u'已退群'

        searchpath = [os.path.join(path, 'we/contrib/html_exporter_res') for path in sys.path]
        env = Environment(loader=FileSystemLoader(searchpath))
        template = env.get_template('wechat.html')
        output_from_parsed_template = template.render(records=self.records)

        # make dir
        export_full_path = os.path.join(os.path.realpath(export_path), 'records')
        if not os.path.exists(export_full_path):
            os.makedirs(export_full_path)

        # copy res
        # shutil.copytree('we/contrib/html_exporter_res/css', export_full_path+'/css')
        # shutil.copytree('we/contrib/html_exporter_res/img', export_full_path+'/img')
        if not os.path.exists(os.path.join(export_full_path, 'css')):
            for path in searchpath:
                source = os.path.join(path, 'css')
                if os.path.exists(source):
                    # copy res
                    shutil.copytree(os.path.join(path, 'css'), os.path.join(export_full_path, 'css'))
                    shutil.copytree(os.path.join(path, 'img'), os.path.join(export_full_path, 'img'))
                    break

        # build records html
        with open(export_full_path + "/records.html", "w") as fh:
            fh.write(output_from_parsed_template.encode('utf8'))
