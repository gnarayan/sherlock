#!/usr/local/bin/python
# encoding: utf-8
"""
*Update sherlock's github wiki pages with some useful info regarding the crossmatch database catalogue tables*

:Author:
    David Young

:Date Created:
    November 18, 2016
"""
import sys
import os
os.environ['TERM'] = 'vt100'
import readline
import glob
import collections
import codecs
from datetime import datetime, date, time
import pickle
from docopt import docopt
from fundamentals.mysql import readquery


class update_wiki_pages():

    """
    Update sherlock's github wiki pages with some useful info regarding the crossmatch database catalogue tables

    **Key Arguments:**
        - ``log`` -- logger
        - ``settings`` -- the settings dictionary

    **Usage:**

        To trigger an update of sherlock's wiki pages to give an overview of the crossmatch table database tables run the following:

        .. code-block:: python 

            from sherlock.commonutils import update_wiki_pages
            wiki = update_wiki_pages(
                log=log,
                settings=settings
            )
            wiki.update() 
    """
    # INITIALISATION

    def __init__(
            self,
            log,
            settings=False,

    ):
        self.log = log
        log.debug("instansiating a new 'update_wiki_pages' object")
        self.settings = settings

        # INITIAL ACTIONS
        # SETUP ALL DATABASE CONNECTIONS
        # SETUP ALL DATABASE CONNECTIONS
        from sherlock import database
        db = database(
            log=self.log,
            settings=self.settings
        )
        dbConns, dbVersions = db.connect()
        self.transientsDbConn = dbConns["transients"]
        self.cataloguesDbConn = dbConns["catalogues"]
        self.pmDbConn = dbConns["marshall"]

        self.basicColumns = [
            "view_name",
            "master table",
            "description",
            "version_number",
            "object_types",
            "object_type",
            "number_of_rows",
            "url",
            "object_type_accuracy",
            "last_updated",
        ]

        return None

    def update(self):
        """
        Update wiki pages

        See class docstring for usage
        """
        self.log.info('starting the ``update`` method')

        if "sherlock wiki root" not in self.settings:
            print "Sherlock wiki settings not found in settings file"
            return

        staticTableInfo = self._get_table_infos()
        viewInfo = self._get_view_infos()
        streamedTableInfo = self._get_stream_view_infos()
        mdContent = self._create_md_tables(
            tableData=staticTableInfo,
            viewData=viewInfo,
            streamData=streamedTableInfo
        )
        self._write_wiki_pages(
            mdContent=mdContent
        )
        self._update_github()

        # RECODE INTO ASCII
        mdContent = mdContent.encode("utf-8", "ignore")

        self.log.info('completed the ``update`` method')
        return update_wiki_pages

    def _get_table_infos(
            self,
            trimmed=False):
        """query the crossmatch catalogues database table metadata
        """
        self.log.info('starting the ``_get_table_infos`` method')

        sqlQuery = u"""
            SELECT * FROM crossmatch_catalogues.tcs_helper_catalogue_tables_info where legacy_table = 0 and table_name not like "legacy%%" and table_name not like "%%stream"  order by number_of_rows desc;
        """ % locals()
        tableInfo = readquery(
            log=self.log,
            sqlQuery=sqlQuery,
            dbConn=self.cataloguesDbConn,
            quiet=False
        )

        if trimmed:
            cleanTable = []
            for r in tableInfo:
                orow = collections.OrderedDict(sorted({}.items()))
                for c in self.basicColumns:
                    if c in r:
                        orow[c] = r[c]
                cleanTable.append(orow)
            tableInfo = cleanTable

        self.log.info('completed the ``_get_table_infos`` method')
        return tableInfo

    def _get_view_infos(
            self,
            trimmed=False):
        """query the crossmatch catalogues database view metadata
        """
        self.log.info('starting the ``_get_view_infos`` method')

        sqlQuery = u"""
            SELECT v.*, t.description as "master table" FROM crossmatch_catalogues.tcs_helper_catalogue_views_info as v,  crossmatch_catalogues.tcs_helper_catalogue_tables_info AS t where v.legacy_view = 0 and v.view_name not like "legacy%%" and t.id=v.table_id order by number_of_rows desc
        """ % locals()
        viewInfo = readquery(
            log=self.log,
            sqlQuery=sqlQuery,
            dbConn=self.cataloguesDbConn,
            quiet=False
        )

        if trimmed:
            cleanTable = []
            for r in viewInfo:
                orow = collections.OrderedDict(sorted({}.items()))
                for c in self.basicColumns:
                    if c in r:
                        orow[c] = r[c]
                cleanTable.append(orow)
            viewInfo = cleanTable

        self.log.info('completed the ``_get_view_infos`` method')
        return viewInfo

    def _get_stream_view_infos(
            self,
            trimmed=False):
        """query the crossmatch catalogues database streamed data tables' metadata
        """
        self.log.info('starting the ``_get_stream_view_infos`` method')

        sqlQuery = u"""
            SELECT * FROM crossmatch_catalogues.tcs_helper_catalogue_tables_info where legacy_table = 0 and table_name not like "legacy%%"  and table_name like "%%stream" order by number_of_rows desc;
        """ % locals()
        streamInfo = readquery(
            log=self.log,
            sqlQuery=sqlQuery,
            dbConn=self.cataloguesDbConn,
            quiet=False
        )

        if trimmed:
            cleanTable = []
            for r in streamInfo:
                orow = collections.OrderedDict(sorted({}.items()))
                for c in self.basicColumns:
                    if c in r:
                        orow[c] = r[c]
                cleanTable.append(orow)
            streamInfo = cleanTable

        self.log.info('completed the ``_get_stream_view_infos`` method')
        return streamInfo

    def _create_md_tables(
        self,
        tableData,
        viewData,
        streamData
    ):
        """generate markdown format tables from the database query results

        **Key Arguments:**
            - ``tableData`` -- the crossmatch catalogues database table metadata.
            - ``viewData`` -- the crossmatch catalogues database view metadata.
            - ``streamData`` -- the crossmatch catalogues database streamed data tables' metadata.

        **Return:**
            - ``mdContent`` -- the content of the markdown file
        """
        self.log.info('starting the ``_create_md_tables`` method')

        header = u"""
| <sub>Table Name</sub> | <sub>Description</sub> | <sub>Reference</sub> | <sub>Number Rows</sub> | <sub>Vizier</sub> | <sub>NED</sub> | <sub>Objects</sub> | <sub>Weight (1-10)</sub> |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"""

        rows = u""
        for ti in tableData:
            table_name = ti["table_name"]
            description = ti["description"]
            url = ti["url"]
            number_of_rows = ti["number_of_rows"]
            reference_url = ti["reference_url"]
            reference_text = ti["reference_text"]
            notes = ti["notes"]
            vizier_link = ti["vizier_link"]
            in_ned = ti["in_ned"]
            object_types = ti["object_types"]
            version_number = ti["version_number"]
            last_updated = ti["last_updated"]
            legacy_table = ti["legacy_table"]
            old_table_name = ti["old_table_name"]
            weight = ti["object_type_accuracy"]

            number_of_rows = str(number_of_rows)
            thisLen = len(number_of_rows)
            newNumber = ""
            count = 0
            while count < thisLen:
                count += 1
                newNumber = number_of_rows[-count] + newNumber
                if count % 3 == 0:
                    newNumber = "," + newNumber
            if newNumber[0] == ",":
                newNumber = newNumber[1:]

            if vizier_link and len(vizier_link) and vizier_link != 0 and vizier_link != "0":
                vizier_link = u"[✓](%(vizier_link)s)" % locals()
            else:
                vizier_link = u""

            if in_ned:
                in_ned = u"✓"
            else:
                in_ned = u""

            rows += u"""
| <sub>%(table_name)s</sub> | <sub>[%(description)s](%(url)s)</sub> | <sub>[%(reference_text)s](%(reference_url)s)</sub> | <sub>%(newNumber)s</sub> | <sub>%(vizier_link)s</sub> | <sub>%(in_ned)s</sub> | <sub>%(object_types)s</sub> | <sub>%(weight)s</sub> |""" % locals()

        mdContent = header + rows

        header = u"""
| <sub>View Name</sub> | <sub>Number Rows</sub> | <sub>Object Type</sub> |
| :--- | :--- | :--- |"""

        rows = u""
        for ti in viewData:
            view_name = ti["view_name"]
            number_of_rows = ti["number_of_rows"]
            object_type = ti["object_type"]

            number_of_rows = str(number_of_rows)
            thisLen = len(number_of_rows)
            newNumber = ""
            count = 0
            while count < thisLen:
                count += 1
                newNumber = number_of_rows[-count] + newNumber
                if count % 3 == 0:
                    newNumber = "," + newNumber
            if newNumber[0] == ",":
                newNumber = newNumber[1:]

            rows += u"""
| <sub>%(view_name)s</sub> | <sub>%(newNumber)s</sub> | <sub>%(object_type)s</sub> |""" % locals()

        self.mdView = header + rows

        header = u"""
| <sub>Table Name</sub> | <sub>Description</sub> | <sub>Reference</sub> | <sub>Number Rows</sub> | <sub>Objects</sub> |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"""

        rows = u""
        for ti in streamData:
            table_name = ti["table_name"]
            description = ti["description"]
            url = ti["url"]
            number_of_rows = ti["number_of_rows"]
            reference_url = ti["reference_url"]
            reference_text = ti["reference_text"]
            notes = ti["notes"]
            vizier_link = ti["vizier_link"]
            in_ned = ti["in_ned"]
            object_types = ti["object_types"]
            version_number = ti["version_number"]
            last_updated = ti["last_updated"]
            legacy_table = ti["legacy_table"]
            old_table_name = ti["old_table_name"]

            number_of_rows = str(number_of_rows)
            thisLen = len(number_of_rows)
            newNumber = ""
            count = 0
            while count < thisLen:
                count += 1
                newNumber = number_of_rows[-count] + newNumber
                if count % 3 == 0:
                    newNumber = "," + newNumber
            if newNumber[0] == ",":
                newNumber = newNumber[1:]

            if len(vizier_link) and vizier_link != 0 and vizier_link != "0":
                vizier_link = u"[✓](%(vizier_link)s)" % locals()
            else:
                vizier_link = u""

            if in_ned:
                in_ned = u"✓"
            else:
                in_ned = u""

            rows += u"""
| <sub>%(table_name)s</sub> | <sub>[%(description)s](%(url)s)</sub> | <sub>[%(reference_text)s](%(reference_url)s)</sub> | <sub>%(newNumber)s</sub> | <sub>%(object_types)s</sub> |""" % locals()

        mdContent = header + rows

        self.log.info('completed the ``_create_md_tables`` method')
        return mdContent

    def _write_wiki_pages(
            self,
            mdContent):
        """write the markdown formated content of the database tables' metadata to local wiki pages

        **Key Arguments:**
            - ``mdContent`` -- the content of the markdown file
        """
        self.log.info('starting the ``_write_wiki_pages`` method')

        pathToWriteFile = self.settings[
            "sherlock wiki root"] + "/Crossmatch-Catalogue Tables.md"
        writeFile = codecs.open(pathToWriteFile, encoding='utf-8', mode='w')
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M")
        lastUpdated = """Last Updated %(now)s
""" % locals()

        writeFile.write(lastUpdated + mdContent)
        writeFile.close()

        pathToWriteFile = self.settings[
            "sherlock wiki root"] + "/Crossmatch-Catalogue Views.md"
        writeFile = codecs.open(pathToWriteFile, encoding='utf-8', mode='w')
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M")
        lastUpdated = """Last Updated %(now)s
""" % locals()

        writeFile.write(lastUpdated + self.mdView)
        writeFile.close()

        pathToWriteFile = self.settings[
            "sherlock wiki root"] + "/Crossmatch-Catalogue Streams.md"
        writeFile = codecs.open(pathToWriteFile, encoding='utf-8', mode='w')
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M")
        lastUpdated = """Last Updated %(now)s
""" % locals()

        writeFile.write(lastUpdated + mdContent)
        writeFile.close()

        self.log.info('completed the ``_write_wiki_pages`` method')
        return None

    def _update_github(
            self):
        """commit the changes and push them to github
        """
        self.log.info('starting the ``_update_github`` method')

        from subprocess import Popen, PIPE, STDOUT
        gdir = self.settings["sherlock wiki root"]
        cmd = """cd %(gdir)s && git add --all && git commit -m "x" && git pull origin master && git push origin master""" % locals()
        p = Popen(cmd, stdout=PIPE, stdin=PIPE, shell=True)
        output = p.communicate()[0]
        print output
        self.log.debug('output: %(output)s' % locals())

        self.log.info('completed the ``_update_github`` method')
        return None

    # use the tab-trigger below for new method
    # xt-class-method
