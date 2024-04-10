# cython: language_level=3

from pkg1.one cimport one

cdef int two():
    return one() + one()
