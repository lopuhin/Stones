
#- rev: v4 -
#- hash: GCMXIY -

import shutil
import itertools
import contextlib
from .base import BaseStore

try:
    import plyvel
except ModuleNotFoundError:
    print('LevelDB store requires PyPi.python.org/pypi/plyvel')
    exit(1)


class LevelStore(BaseStore):
    """
    LevelDB container compatible with Python dicts.
    Keys and values MUST be byte strings.
    """

    __slots__ = ('db', '_name')

    def __init__(self, name, encoder='cbor', encode_decode=tuple(), value_type=bytes,
            iterable=tuple(), **kwargs):
        super().__init__(encoder=encoder, encode_decode=encode_decode, value_type=value_type)
        self._name = name + '.lvl'
        self.db = plyvel.DB(self._name, create_if_missing=True)
        if iterable or kwargs:
            self._populate(iterable, **kwargs)

    def close(self):
        self.db.close()


    def _populate(self, iterable=tuple(), **kwargs):
        with contextlib.suppress(AttributeError):
            iterable = iterable.items()
        with self.db.write_batch() as batch:
            for key, value in itertools.chain(iterable, kwargs.items()):
                batch.put(key, self._encode(value))


    def get(self, key, default=None):
        encoded_value = self.db.get(key, False)
        return self._decode(encoded_value) if encoded_value else default

    def put(self, key, value, overwrite=False):
        if not overwrite and self.db.get(key):
            return
        self.db.put(key, self._encode(value))

    def delete(self, key):
        return self.db.delete(key)


    def __getitem__(self, key):
        encoded_value = self.db.get(key)
        return self._decode(encoded_value)

    def __setitem__(self, key, value):
        return self.db.put(key, self._encode(value))

    __delitem__ = delete


    def __contains__(self, key):
        return bool(self.db.get(key))

    def __len__(self):
        return len(set(self.db))

    def __iter__(self):
        return self.db.iterator(include_key=True, include_value=False)

    def __repr__(self):
        items = dict(self.items())
        return self.__class__.__name__ + repr(items)


    def keys(self):
        keys_list = []
        for key in self.db.iterator(include_key=True, include_value=False):
            keys_list.append(key)
        return keys_list

    def values(self):
        vals_list = []
        for value in self.db.iterator(include_key=False, include_value=True):
            vals_list.append(self._decode(value))
        return vals_list

    def items(self):
        items_list = []
        for key, value in self.db.iterator(include_key=True, include_value=True):
            items_list.append((key, self._decode(value)))
        return items_list


    def update(self, iterable=tuple(), **kwargs):
        self._populate(iterable, **kwargs)

    def clear(self):
        self.close()
        plyvel.destroy_db(self._name)
        self.db = plyvel.DB(self._name, create_if_missing=True)

    def destroy(self, yes_im_sure=False):
        if yes_im_sure:
            self.close()
            shutil.rmtree(self._name)
