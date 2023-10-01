from pkg1.one cimport one

cdef int two():
    return one() + one()
