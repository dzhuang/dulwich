# test_object_store.py -- tests for object_store.py
# Copyright (C) 2008 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the object store interface."""


import os
import shutil
import tempfile

from dulwich.index import (
    commit_tree,
    )
from dulwich.objects import (
    Blob,
    )
from dulwich.object_store import (
    DiskObjectStore,
    MemoryObjectStore,
    )
from dulwich.tests import (
    TestCase,
    )
from utils import (
    make_object,
    )


testobject = make_object(Blob, data="yummy data")


class ObjectStoreTests(object):

    def test_iter(self):
        self.assertEquals([], list(self.store))

    def test_get_nonexistant(self):
        self.assertRaises(KeyError, lambda: self.store["a" * 40])

    def test_contains_nonexistant(self):
        self.assertFalse(("a" * 40) in self.store)

    def test_add_objects_empty(self):
        self.store.add_objects([])

    def test_add_commit(self):
        # TODO: Argh, no way to construct Git commit objects without 
        # access to a serialized form.
        self.store.add_objects([])

    def test_add_object(self):
        self.store.add_object(testobject)
        self.assertEquals(set([testobject.id]), set(self.store))
        self.assertTrue(testobject.id in self.store)
        r = self.store[testobject.id]
        self.assertEquals(r, testobject)

    def test_add_objects(self):
        data = [(testobject, "mypath")]
        self.store.add_objects(data)
        self.assertEquals(set([testobject.id]), set(self.store))
        self.assertTrue(testobject.id in self.store)
        r = self.store[testobject.id]
        self.assertEquals(r, testobject)

    def test_iter_tree_contents(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        blob_c = make_object(Blob, data='c')
        for blob in [blob_a, blob_b, blob_c]:
            self.store.add_object(blob)

        blobs = [
          ('a', blob_a.id, 0100644),
          ('ad/b', blob_b.id, 0100644),
          ('ad/bd/c', blob_c.id, 0100755),
          ('ad/c', blob_c.id, 0100644),
          ('c', blob_c.id, 0100644),
          ]
        tree_id = commit_tree(self.store, blobs)
        self.assertEquals([(p, m, h) for (p, h, m) in blobs],
                          list(self.store.iter_tree_contents(tree_id)))

    def test_iter_tree_contents_include_trees(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        blob_c = make_object(Blob, data='c')
        for blob in [blob_a, blob_b, blob_c]:
            self.store.add_object(blob)

        blobs = [
          ('a', blob_a.id, 0100644),
          ('ad/b', blob_b.id, 0100644),
          ('ad/bd/c', blob_c.id, 0100755),
          ]
        tree_id = commit_tree(self.store, blobs)
        tree = self.store[tree_id]
        tree_ad = self.store[tree['ad'][1]]
        tree_bd = self.store[tree_ad['bd'][1]]

        expected = [
          ('', 0040000, tree_id),
          ('a', 0100644, blob_a.id),
          ('ad', 0040000, tree_ad.id),
          ('ad/b', 0100644, blob_b.id),
          ('ad/bd', 0040000, tree_bd.id),
          ('ad/bd/c', 0100755, blob_c.id),
          ]
        actual = self.store.iter_tree_contents(tree_id, include_trees=True)
        self.assertEquals(expected, list(actual))


class MemoryObjectStoreTests(ObjectStoreTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.store = MemoryObjectStore()


class PackBasedObjectStoreTests(ObjectStoreTests):

    def test_empty_packs(self):
        self.assertEquals([], self.store.packs)

    def test_pack_loose_objects(self):
        b1 = make_object(Blob, data="yummy data")
        self.store.add_object(b1)
        b2 = make_object(Blob, data="more yummy data")
        self.store.add_object(b2)
        self.assertEquals([], self.store.packs)
        self.assertEquals(2, self.store.pack_loose_objects())
        self.assertNotEquals([], self.store.packs)
        self.assertEquals(0, self.store.pack_loose_objects())


class DiskObjectStoreTests(PackBasedObjectStoreTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.store_dir = tempfile.mkdtemp()
        self.store = DiskObjectStore.init(self.store_dir)

    def tearDown(self):
        TestCase.tearDown(self)
        shutil.rmtree(self.store_dir)

    def test_pack_dir(self):
        o = DiskObjectStore(self.store_dir)
        self.assertEquals(os.path.join(self.store_dir, "pack"), o.pack_dir)

# TODO: MissingObjectFinderTests
