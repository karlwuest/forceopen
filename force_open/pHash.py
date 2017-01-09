from ctypes import *

libpHash = cdll.LoadLibrary("libpHash.so.0")


def dct_imagehash(filename):
    """
    dct based image hash
    """
    res = c_ulonglong()
    libpHash.ph_dct_imagehash(filename, byref(res))
    return res.value


def hamming_distance(hash_1, hash_2):
    """
    hamming distance between two 64bit hashes
    """
    return libpHash.ph_hamming_distance(c_ulonglong(hash_1), c_ulonglong(hash_2))


def dct_similar(file_1, file_2, threshhold=26):
    """
    decide whether file_1 and file_2 are similar based on the dct_imagehash
    """
    hash_1 = dct_imagehash(file_1)
    hash_2 = dct_imagehash(file_2)
    return hamming_distance(hash_1, hash_2) <= threshhold


def mh_imagehash(filename, alpha=2.0, lvl=1.0):
    """
    Marr-Hildreth image hash
    """
    libpHash.ph_mh_imagehash.restype = POINTER(c_char * 72)
    N = c_int()
    res = libpHash.ph_mh_imagehash(filename, byref(N), c_float(alpha), c_float(lvl))
    return bytes(res.contents[:N.value])


def hamming_distance_2(hash_1, hash_2):
    """
    normalised hamming distance between two byte strings of the same length
    """
    libpHash.ph_hammingdistance2.argtypes = [c_char_p, c_int, c_char_p, c_int]
    libpHash.ph_hammingdistance2.restype = c_double
    return libpHash.ph_hammingdistance2(hash_1, len(hash_1), hash_2, len(hash_2))


def image_digest(filename, sigma=1.0, gamma=1.0, angles=180):
    pass


def crosscorr(hash_1, hash_2):
    pass

