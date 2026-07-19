# !/usr/bin/env python
# -*- coding: utf-8 -*-

import web  # web.py framework
import gv  # Get access to SIP's settings
import time
from urls import urls  # Get access to SIP's URLs
from sip import template_render  #  Needed for working with web.py templates
from webpages import ProtectedPage  # Needed for security
from helpers import read_log
from pathlib import Path
import json  # for working with data file
from urllib.parse import quote

# Add new URLs to access classes in this plugin.
# fmt: off
urls.extend([
    u"/backup", u"plugins.backup_settings.backup",
    u"/download", u"plugins.backup_settings.download"
    ])
# fmt: on

# Add this plugin to the PLUGINS menu ["Menu Name", "URL"], (Optional)
gv.plugin_menu.append([_(u"Backup/Restore Settings"), u"/backup"])


def _read_uploaded_data(uploaded_file):
    if uploaded_file in ({}, None):
        raise ValueError("No backup file uploaded")

    if hasattr(uploaded_file, 'raw'):
        try:
            return uploaded_file.raw
        except Exception as e:
            raise ValueError("Unable to read backup file") from e

    if hasattr(uploaded_file, 'value'):
        return uploaded_file.value

    if hasattr(uploaded_file, 'file'):
        try:
            uploaded_file.file.seek(0)
        except (AttributeError, IOError):
            pass
        return uploaded_file.file.read()

    return uploaded_file


class download(ProtectedPage):
    """
    Download all data files as a single JSON archive file.
    """

    def GET(self):
        try:
            restorePoint = time.strftime('%Y-%m-%dT%H:%M:%SZ', gv.nowt)
            data = {
                '__restorePoint' : restorePoint,
            }

            dataFiles = Path('./data')
            for filename in list(dataFiles.glob('**/*.json')):
                filename = str(filename)[5:] # convert path to the filename string by stripping off "data/"
                with open(
                    u"./data/" + filename, u"r"
                ) as f:
                    print("Backing up " + filename)
                    if (filename != "log.json"):
                        try:
                            data[filename[:-5]] = json.load(f) # strip off the ".json" for the key name
                        except ValueError as e:
                            print(f"Failed to backup {filename} {e}")
                    else:
                        data["log"] = read_log()

            web.header('Content-Type','text/json')
            web.header('Content-disposition', 'attachment; filename=SIP-backup-%s-%s.json'%(gv.sd['name'].replace(" ", "_"),restorePoint))
            return json.dumps(data)  # return data as json txt file
        except IOError:  # If file does not exist return empty value
            raise web.seeother('/backup?success=false')

class backup(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """

    def POST(self):
        try:
            upload = web.input(myfile={})
            uploaded_file = upload.get('myfile')
            uploaded_data = _read_uploaded_data(uploaded_file)
            if isinstance(uploaded_data, bytes):
                uploaded_data = uploaded_data.decode("utf-8-sig")
            elif not isinstance(uploaded_data, str):
                raise ValueError("Unable to read backup file data")

            if not uploaded_data or not uploaded_data.strip():
                raise ValueError("Backup file is empty")

            data = json.loads(uploaded_data)
            if not isinstance(data, dict):
                raise ValueError("Backup file does not contain a JSON object")

            # break the master data into individual components corresponding to files
            restorePoint = data.get("__restorePoint", "")

            for d in data:
                if d == "__restorePoint":
                    continue
                elif d == "log":
                    print("Restoring log.json")
                    log = data["log"]
                    lines = []
                    for r in log:
                        lines.append(json.dumps(r) + "\n")
                        with open("./data/log.json", "w", encoding="utf-8") as f:
                            f.writelines(lines)
                else:
                    print("Restoring " + d + ".json")
                    with open(u"./data/" + d + ".json", u"w") as f:
                        json.dump(data[d], f, indent=4, sort_keys=True)

            raise web.seeother('/backup?success=true&restorePoint=' + quote(str(restorePoint), safe=''))
        except (IOError, ValueError, AttributeError, KeyError, TypeError) as e:
            print("Failed to restore settings: " + str(e))
            raise web.seeother('/backup?success=false')


    def GET(self):
        user_data = web.input(success="unknown", restorePoint="")
        status = {"success" : user_data.success, "restorePoint" : user_data.restorePoint }  # report the status
        return template_render.backup_settings(status)  # open backup/restore page
