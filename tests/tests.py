import appbase.bootstrap as bootstrap
import gevent
import sys
sys.path.append('.')
import json
import unittest

from flask import Flask
from sqlalchemy import Table, Column, Integer, String

import appbase.publishers
import appbase.sa

satransaction = appbase.publishers.satransaction


class RESTPublisherTestCase(unittest.TestCase):
    """
    Tests for the RESTPublisher Class.
    These tests use the externally defined functions
    for the resource to to published, i.e. users.
    """
    def setUp(self):
        self.app = Flask(__name__)
        # Creating a RESTPublisher
        rest_publisher = appbase.publishers.RESTPublisher(self.app)
        handlers = (get_all, add_user, get_user, edit_user, delete_user)
        rest_publisher.map_resource('users/', handlers, resource_id=('int', 'id'))
        self.app = self.app.test_client()
        # Dummy test users
        self.test_users = [{'email': 'a@bc.com', 'password': 'p'},
                           {'email': 'a@bc.com', 'password': 'p'}]
        global users  # think of it as a key value datastore ;)

    def test_add_user(self):
        """
        Adding a user and then check if the user is added
        """
        self.app.post('/api/users/', data=json.dumps(self.test_users[0]))
        self.assertEqual(users[0]['email'], self.test_users[0]['email'])

    def test_get_user(self):
        """
        Adding a user and then retreiving it via API and mathing
        """
        resp = self.app.post('/api/users/', data=json.dumps(self.test_users[0]))
        id = json.loads(resp.data)['result']

        resp = self.app.get('/api/users/%s' % id)
        user = json.loads(resp.data)['result']
        self.assertDictEqual(user, self.test_users[0])

    def test_get_users(self):
        """
        Adding two users and then retreiving the collection and comparing
        """
        self.app.post('/api/users/', data=json.dumps(self.test_users[0]))
        self.app.post('/api/users/', data=json.dumps(self.test_users[1]))
        resp = self.app.get('/api/users/')
        users = json.loads(resp.data)['result']
        self.assertTrue(self.test_users[0] in users)
        self.assertTrue(self.test_users[1] in users)

    def test_edit_user(self):
        """
        Adding a new user and changing their password and verifying
        """
        new_user = {'email': 'eviluser@example.com', 'password': 'weakpass'}
        self.app.post('/api/users/0', data=json.dumps(new_user))
        self.assertEqual(users[0]['password'], new_user['password'])

    def test_delete_user(self):
        """
        These tests might fail as ideally we would be using non-changing
        uuids but here we are using array indices which would change on
        deleting a particular elements and tests would fail.
        """
        c = len(users)
        self.app.post('/api/users/', data=json.dumps(self.test_users[0]))
        self.app.post('/api/users/', data=json.dumps(self.test_users[1]))
        self.assertEqual(len(users), (c + 2))
        self.app.delete('/api/users/0')
        self.assertEqual(len(users), (c + 1))
        # id of second user changes here, unlike a practical uuid !
        self.assertEqual(self.test_users[1], users[0])


# TODO: These tests are failing, but example.py runs perfectly. Weird !
class HTTPPublisherTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        http_publisher = appbase.publishers.HTTPPublisher(self.app)
        # TODO: Think, should we move it to respective tests
        http_publisher.add_mapping('/add/', add, ['POST'])
        http_publisher.add_mapping('/iszero/', is_zero, ['POST'])
        self.app = self.app.test_client()

    def test_add(self):
        resp = self.app.post('/add/', data=json.dumps({'a': 2, 'b': 3}))
        result = json.loads(resp.data)['result']
        self.assertEqual(result, 5)

    def test_iszero(self):
        resp = self.app.post('/iszero/', data=json.dumps({'n': 3}))
        result = json.loads(resp.data)['result']
        self.assertFalse(result)


# The User Resource
users = []
PAGE_SIZE = 10


def add_user(email, password):
    user = dict(email=email, password=password)
    users.append(user)
    return users.index(user)


def edit_user(id, email=None, password=None):
    if email is not None:
        users[id]['email'] = email
    if password is not None:
        users[id]['password'] = password
    return True


def get_user(id):
    return users[id]


def get_all(page_no=1):
    return users[PAGE_SIZE * (page_no - 1):PAGE_SIZE * (page_no)]


def delete_user(id):
    users.pop(id)
    return True


def is_zero(n):
    return n == 0


def add(a, b):
    return a + b


class SATransaction(unittest.TestCase):
    def setUp(self):
        self.books = Table("books", appbase.sa.metadata,
                      Column("id", Integer),
                      Column("name", String),
                      extend_existing=True
                      )
        satransaction(appbase.sa.metadata.drop_all)(appbase.sa.engine)
        satransaction(appbase.sa.metadata.create_all)(appbase.sa.engine)

    @satransaction
    def _test_insert(self):
        conn = appbase.sa.connect()
        q = self.books.insert().values(name='A Book')
        conn.execute(q)
        assert((1, 'A Book') in list(conn.execute(self.books.select())))

    @satransaction
    def theapi(self, book_id):
        conn = appbase.sa.connect()
        q = self.books.insert().values(id=book_id, name='Another Book')
        conn.execute(q)
        return (book_id, 'Another Book') in list(conn.execute(self.books.select()))

    def test_api0(self):
        job = gevent.spawn(self.theapi, 0)
        gevent.joinall([job])  # this <^ only simulates appbase api execution
        assert bool(job.value)

    def test_api1(self):
        job = gevent.spawn(self.theapi, 1)
        gevent.joinall([job])  # this <^ only simulates appbase api execution
        assert bool(job.value)

    def test_apis(self):
        jobs = [gevent.spawn(self.theapi, i) for i in range(11, (101))]
        gevent.joinall(jobs)  # this <^ only simulates appbase api execution
        assert all(job.value for job in jobs)

    def test_rollback(self):
        """
        Exceptected to raise an exception
        """
        book_id = 0 # Already inserted
        job = gevent.spawn(self.theapi, book_id)
        job.join()