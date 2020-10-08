#!/usr/bin/python
from parse_webpage import FakeBookParser
from PacketTransfer import PacketTransfer
import re, sys


# Class representing the web crawler
class Crawler:

    def __init__(self):
        self.secretFlag = []
        self.visited = set()
        self.allLinks = []

    # the main crawl function which gets called when the application is started
    def crawl(self, username, password):

        connect = PacketTransfer(username, password, logging_level=10)
        welcome_page = connect.login()
        parse = FakeBookParser()
        parse.feed(welcome_page)
        links_dictionary = parse.links
        self.add_link(links_dictionary)

        # keep crawling until there are a total of 5 flags
        while len(self.secretFlag) < 5:

            if len(self.allLinks) == 0:
                break

            if self.allLinks[0] in self.visited:
                self.allLinks.pop(0)
            else:
                page_parser = FakeBookParser()
                url = self.allLinks[0]
                dictionary = connect.send_request_message(url)
                # handling the 500 server code
                while dictionary is None or 500 in dictionary.keys():
                    connect.login()
                    dictionary = connect.send_request_message(url)

                if self.handle_requests(dictionary):
                    page = dictionary[200]
                    page_parser.feed(page)
                    self.add_link(page_parser.links)
                    self.visited.add(self.allLinks.pop(0))

        for flag in self.secretFlag:
            print(flag[0])

    # function for handling different HTML codes
    def handle_requests(self, dictionary):
        if dictionary.get(200):
            return True
        elif dictionary.get(301):
            self.visited.add(self.allLinks.pop(0))
            if self.check_valid_url(dictionary[301]):
                self.allLinks.append(dictionary[301].split("http://cs5700.ccs.neu.edu")[1])
        elif dictionary.get(403):
            self.visited.add(self.allLinks.pop(0))
        else:
            self.allLinks.append(self.allLinks.pop(0))
        return False

    # function for checking a valid URL so that the crawler only crawls the specified domain links
    def check_valid_url(self, url):
        reg_list = re.compile('^http:\/\/cs5700\.ccs\.neu\.edu\/fakebook').findall(url)
        if len(reg_list) > 0:
            return True
        return False

    # adding a new link to the list
    def add_link(self, dictionary):
        for key in dictionary:
            if key != 'secret_key':
                for link in dictionary[key]:
                    if link not in self.visited:
                        self.allLinks.append(link)

        if len(dictionary['secret_key']) > 0:
            self.secretFlag.append(dictionary['secret_key'])


if __name__ == '__main__':
    obj = Crawler()
    nuid = sys.argv[1]
    password = sys.argv[2]
    obj.crawl(str(nuid), str(password))
