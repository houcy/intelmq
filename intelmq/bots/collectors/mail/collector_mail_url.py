# -*- coding: utf-8 -*-

import re
import sys

import imbox
import requests

from intelmq.lib.bot import Bot
from intelmq.lib.message import Report


class MailURLCollectorBot(Bot):

    def process(self):
        mailbox = imbox.Imbox(self.parameters.mail_host,
                              self.parameters.mail_user,
                              self.parameters.mail_password,
                              self.parameters.mail_ssl)
        emails = mailbox.messages(folder=self.parameters.mail_folder, unread=True)

        if emails:
            for uid, message in emails:

                if (self.parameters.mail_subject_regex and
                        not re.search(self.parameters.mail_subject_regex,
                                      message.subject)):
                    continue

                self.logger.info("Reading email report")

                for body in message.body['plain']:
                    match = re.search(self.parameters.mail_url_regex, body)
                    if match:
                        url = match.group()

                        # Build request
                        self.http_header = getattr(self.parameters,
                                'http_header', {})
                        self.http_verify_cert = getattr(self.parameters,
                                                        'http_verify_cert', True)

                        if hasattr(self.parameters, 'http_username') and hasattr(
                                self.parameters, 'http_password'):
                            self.auth = (self.parameters.http_username,
                                         self.parameters.http_password)
                        else:
                            self.auth = None

                        http_proxy = getattr(self.parameters, 'http_proxy', None)
                        https_proxy = getattr(self.parameters,
                                              'http_ssl_proxy', None)
                        if http_proxy and https_proxy:
                            self.proxy = {'http': http_proxy, 'https': https_proxy}
                        else:
                            self.proxy = None

                        self.http_header['User-agent'] = self.parameters.http_user_agent

                        self.logger.info("Downloading report from %s" % url)
                        resp = requests.get(url=url,
                                            auth=self.auth, proxies=self.proxy,
                                            headers=self.http_header,
                                            verify=self.http_verify_cert)

                        if resp.status_code // 100 != 2:
                            raise ValueError('HTTP response status code was {}.'
                                             ''.format(resp.status_code))

                        self.logger.info("Report downloaded.")

                        report = Report()
                        report.add("raw", resp.content)
                        report.add("feed.name",
                                   self.parameters.feed)
                        report.add("feed.accuracy", self.parameters.accuracy)
                        self.send_message(report)

                mailbox.mark_seen(uid)
                self.logger.info("Email report read")


if __name__ == "__main__":
    bot = MailURLCollectorBot(sys.argv[1])
    bot.start()
