from HTMLParser import HTMLParser
import re


class FakeBookParser(HTMLParser):
    # This class reads all the pages and extracts the relevant links and the secret keys from the web page.
    # This class is inherited from the HTMLParse class.
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = {}
        self.is_last_tag_secret_flag = False
        self.links["profiles_url_list"] = set()
        self.links["friend_list_pages"] = set()
        self.links["secret_key"] = []

    def handle_starttag(self, tag, attrs):
        # If a html tag is found with anchor tag extract url from it.
        if tag == "a":
            attr = dict(attrs)
            if "/friends/" in attr.get('href'):
                self.links["friend_list_pages"].add(attr.get('href'))

            if "/fakebook/" in attr.get('href'):
                pattern = re.compile(r'^\/fakebook\/\d*\/$')
                link = pattern.findall(attr.get('href'))
                if len(link) > 0:
                    self.links["profiles_url_list"].add(link[0])

        #  If a html tag is found with h2 tag and class as secret key extract the secret key from it done in
        #  handle_data.
        if tag == "h2":
            attr = dict(attrs)
            if attr.get("class") == "secret_flag":
                self.is_last_tag_secret_flag = True

    def handle_data(self, data):
        if self.is_last_tag_secret_flag:
            self.links["secret_key"].append(data)
            self.is_last_tag_secret_flag = False
