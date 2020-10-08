import socket
import re
import logging
import os

BUFFFER_SIZE = 4096
CSRF_STRING = 'csrftoken'
SESSIONID_STRING = 'sessionid'


class PacketTransfer(object):

    def __init__(self, username, password, logging_level):
        """
        This is the constructor for the class PacketTransfer. It creates a logger and initialises the variables of the
        class.
        """
        self.logger = logging.getLogger(__name__)
        log_format = logging.Formatter('%(asctime)s - %(message)s')
        file_handler = logging.FileHandler(filename=(os.path.join(os.getcwd(), 'log')), mode='a')
        file_handler.setFormatter(log_format)

        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging_level)
        self.username = username
        self.password = password
        self.host = 'cs5700.ccs.neu.edu'
        self.port = 80
        self.csrf = ''
        self.session_id = ''

    def _open_socket(self):
        """
        Creates a socket object and connects to the given port and host.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.logger.debug('Connected to %s on %s.' % (self.host, self.port))

    def login(self):
        """
        Creates a new socket and sends a series of packets to log into the /fakebook/ server.
        Sends an initial GET request which returns the login page.
        Sends a POST request to log into the server.
        The server sends a 301 whose location is extracted and a request is sent to the new location.
        The text (including head and body) is returned.
        This function updates the session ID every time a call to the server has been made.
        The csrf key is stored and sent with every request during the login sequence.
        :returns A string of the header and body once the user logs in.
        """
        self.logger.info("--New Session--")
        self._open_socket()

        initial_header = 'GET /accounts/login/?next=/fakebook/ HTTP/1.1\r\nHost: %s\r\n\r\n' % self.host
        self._send_request(initial_header)

        data = self._receive_message()

        # Update the CSRF
        self.csrf = self.get_cookie(data, CSRF_STRING)
        # Update the sessionID
        self.session_id = self.get_cookie(data, SESSIONID_STRING)

        request_body = 'csrfmiddlewaretoken=%s&username=%s&password=%s&next=' % (
            self.csrf, self.username, self.password)
        request = 'POST /accounts/login/ HTTP/1.1\r\n' \
                  'Host: %s\r\n' \
                  'Content-Length: %d\r\n' \
                  'Content-Type: application/x-www-form-urlencoded\r\n' \
                  'Cookie: csrftoken=%s; sessionid=%s\r\n\r\n%s' % (
                      self.host, len(request_body), self.csrf, self.session_id, request_body)

        self._send_request(request)
        data = self._receive_message()

        # Update the session ID
        self.session_id = self.get_cookie(data, SESSIONID_STRING)

        request = "GET /fakebook/ HTTP/1.1\r\nHost: %s\r\n" \
                  "Cookie: csrftoken=%s; sessionid=%s\r\n\r\n" % (self.host, self.csrf, self.session_id)

        self._send_request(request)
        data = self._receive_message()

        # Update the session ID
        self.session_id = self.get_cookie(data, SESSIONID_STRING)

        self._close_socket()
        return data

    def _close_socket(self):
        """
        Closes the socket that was created.
        """
        self.sock.close()
        self.logger.debug('Connection closed.')

    def _send_request(self, request_message):
        """
        Sends the request_message from the socket created before.
        :param request_message: is the message to be sent from the socket opened before.
        """
        self.logger.debug("--REQUEST SENT--\n%s" % request_message)
        try:
            self.sock.sendall(b'%s' % request_message)
        except (socket.timeout, socket.error, socket.herror), e:
            self.logger.error('Error in sending message: ', exec_info=True)
            print('Terminated: Exception occurred in sending. Try again later.\n')

    def _receive_message(self):
        """
        Receives the message from the server and returns to the calling function.
        :return: the message sent by the server to the program.
        """
        try:
            data = self.sock.recv(BUFFFER_SIZE).decode('utf8')

            # If server does not send data, wait for more data from the server
            while data is None:
                data = self.sock.recv(BUFFFER_SIZE).decode('utf8')
            self.logger.debug("--RESPONSE RECEIVED--\n%s" % data)
            return data

        # If the server fails to send data on time or does so later, the connection is terminated
        except (socket.timeout, socket.error, socket.herror), e:
            self.logger.error('Error in receiving message: ', exec_info=True)
            print('Terminated: Exception occurred in receiving. Try again later.\n')

    def get_cookie(self, data, cookie):
        """
        Returns the value of the cookie present on the web-page.
        :param data: each response from the server (header and body)
        :param cookie: can be the CSRF identifier or the Session ID identifier.
        :return: the value associated with the cookie.
        """
        try:
            csrf_list = re.compile('(?:%s=)[\d\w]*' % cookie).findall(data)
            self.logger.debug('%s' % csrf_list)
            csrf_number = csrf_list[0].split("=")
            self.logger.debug('%s: %s' % (cookie, csrf_number[1]))
            # Returns the first occurrence of the value associated with the cookie given in the argument.
            return csrf_number[1]
        except Exception as e:
            # print('Connection terminated. Incorrect Data. Try again.')
            self.logger.error('Terminated: Did not receive data from the server.')

    def send_request_message(self, resource):
        """
        Function that sends GET request to the server by creating a socket and connecting to the server. Along with this
        GET request, cookies (CSRF and Session ID) are sent. Once the response is received, the socket is closed.
        :param resource: the path of the resource that is attached to the GET request.
        :return: The response sent by the server.
        """
        self._open_socket()
        request = "GET %s HTTP/1.1\r\nHost: %s\r\n" \
                  "Cookie: csrftoken=%s; sessionid=%s\r\n\r\n" % (resource, self.host, self.csrf, self.session_id)
        self._send_request(request)
        self.logger.debug("--REQUEST SENT--\n%s" % request)
        data = self._receive_message()
        self.logger.debug("--RESPONSE RECEIVED--\n%s" % data)

        self._close_socket()
        return self._pack_response(data)
        # Since session ID is not updated in this request, it's not updated
        # self._update_session_id(data)

    def _pack_response(self, data):
        """
        Packs the response and the status code in a dictionary and returns it where the 'key' is the status code and
        the 'value' is the response.
        :param data: the response from the server once a request is sent.
        :return: a dictionary that has packed data.
        """
        status_code = self._get_status_code(data)
        # Checks if the data sent by the server is empty
        if len(status_code) > 0:
            return self._get_value(status_code[0], data)
        # If the response is empty, return a dictionary with status code 500
        self.logger.debug('No status code found. Sending {500, \'retry\'}')
        return {500: 'retry'}

    def _get_status_code(self, data):
        """
        Returns the status code of the header from the response from the server.
        :param data: the entire response from the server
        :return: status code of the header
        """
        status_list = re.compile('(?<=HTTP\/1.1 )[0-9]{3}').findall(data)
        self.logger.debug("--STATUS CODE--\n%s" % status_list[0])
        return status_list

    def _get_value(self, status_code, data):
        """
        Bundles the response into a dictionary with the key as status code and the value as the information associated
        with it.
        :param status_code: status code of the response message.
        :param data: entire response message.
        :return: a dictionary with status code and the associated information.
        """
        # Returns a dictionary
        if status_code == '200':
            self.logger.debug('Response: {200, %s', data)
            return {200: data}
        elif status_code == '301':
            self.logger.debug('Response: {301, %s', self._get_redirected_link(data))
            return {301: self._get_redirected_link(data)}
        elif status_code == '403' or status_code == '404':
            self.logger.debug('Response: {403, \'Empty value\'}')
            return {403: 'Empty value'}
        elif status_code == '500':
            self.logger.debug('Response: {500, \'Server Error\'}')
            return {500: 'Server Error'}

    def _get_redirected_link(self, data):
        """
        Returns the new location of the path from the server when the status code is 301.
        :param data: Response sent from the server (With status code 301).
        :return: new location of the resource on the server.
        """
        links_list = re.compile('(?<=HTTP\/1.1 )[0-9]{3}').findall(data)
        self.logger.debug("--REDIRECTED LINK--\n%s" % links_list)
        return links_list[0]
