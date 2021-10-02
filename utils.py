import hashlib
import math
import os

from numpy import std
from scipy.stats import t
from contextlib import contextmanager

# Singleton implementation:
# piazza 'Borg.__init__(self)' nell'__init__
class Borg:
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state


@contextmanager
def changeDirectory(dir):
    cur_dir = os.getcwd()
    os.chdir(dir)

    try:
        yield
    finally:
        os.chdir(cur_dir)

@contextmanager
def suppressException(exp):
    try:
        yield 
    except exp:
        pass
    
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

        
# TODO: Mi sta salendo il dubbio che questa sia l'esatta implementazione di un binary search.
#  in qual caso fare tutta sta roba, per quanto simpatica, mi fa sembrare un coglione.
#  Verificare se l'output è lo stesso per un po' di casi, e sbarazzarsi di tutto il superfluo
def maxima(h, s, f, interval=False):
    # type: (function, int, int, bool) -> (int, int)
    
    '''
    to find the maximum of h on [s,f]
    :param f: a strictly unimodal function on [s,f]
    :param s: the start of the interval
    :param f: the end of the interval
    :param interval: If True returns the interval where the maxima could be (s, f), otherwise (s, h(s))

    RETURNS (a,b) such that h(a) = b and
            b is the maximum for h
    '''
    
    results = {}
    
    def evaluate(f, x):
        if x not in results:
            val = f(x)
            results[x] = val
        
        return results[x]
            
    
    start  = evaluate(h, s)
    finish = evaluate(h, f)
    
    
    while s + 1 < f:
        
        m = math.ceil((s + f) / 2)
        
        median = evaluate(h, m)
        
        
        if median > start and median > finish:
            
            '''
            
            ^
            |            x
            |            |
            | x          |          x
            | |          |          |
            | s          m          f
            ------------------------->
            
            '''
            
            m1 = math.ceil((s + m) / 2)
            m1_val = evaluate(h, m1)
            
            if m1_val > median:
                
                '''
                
                ^
                |       x 
                |       |     x
                |       |     |
                | x     |     |         x
                | |     |     |         |
                | s     m1    m         f
                ------------------------->
                
                '''
                
                f = m
                finish = median
                
            else:
                m2 = math.ceil((m + f) / 2)
                m2_val = evaluate(h, m2)
                
                if m2_val > median:
                
                    '''
                    
                    ^
                    |                x      
                    |           x    |     
                    |      x    |    |     
                    | x    |    |    |    x
                    | |    |    |    |    |
                    | s    m1   m    m2   f
                    ------------------------->
                    
                    '''
                    
                    s = m
                    start = median
                    
                    
                else:
                    
                    '''
                    
                    ^
                    |                      
                    |           x         
                    |      x    |    x     
                    | x    |    |    |    x
                    | |    |    |    |    |
                    | s    m1   m    m2   f
                    ------------------------->
                    
                    '''
                    
                    s = m1
                    start = m1_val
                    
                    f = m2
                    finish = m2_val
            
        else:
            
            '''
            
            ^                                       ^                         
            | x                                     |                       x 
            | |          x                          |            x          | 
            | |          |          x               | x          |          | 
            | |          |          |               | |          |          | 
            | s          m          f               | s          m          f 
            ------------------------->    oppure    ------------------------->
            
            '''
            
            if start > finish:
                f = m
                finish = median
            else:
                s = m
                start = median

        if interval:
            break

    if start > finish:
        score = start
        height = s
    else:
        score = finish
        height = f

    if interval:
        return (s,f)
    else:
        return (height, score)


def confidenceInterval(data, alpha=0.05, debug=False):
    mean = sum(data) / len(data)
    stddev = std(data, ddof=1)
    t_bounds = t.interval(1 - alpha, len(data) - 1)

    ci = [mean + critval * stddev / math.sqrt(len(data)) for critval in t_bounds]
    
    if debug:
        print(f"Mean: {mean}")
        print(f"Confidence Interval {(1-alpha)*100}%: {ci[0]}, {ci[1]}")

    return ci


# Thanks to Omnifarious.  https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest()# if ashexstr else hasher.digest()

def file_as_blockiter(afile, blocksize=65536):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)

def fileMD5(file):
    with open(file, 'rb') as f:
        return hash_bytestr_iter(file_as_blockiter(f), hashlib.md5())