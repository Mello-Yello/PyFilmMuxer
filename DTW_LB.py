from numpy import infty
from scipy.spatial.distance import euclidean

def kimFL(Q, C, dist=euclidean):
    q, c = Q.get(), C.get()
    if len(q) <= 1 or len(c) <= 1:
        # TODO: Da una parte questo non è corretto. Dall'altra tornare 0 significa dire che questo è ideale
        #  bisogna comunque indagare su una soluzione migliore
        return infty
    else:
        return dist(q[0], c[0]) + dist(q[-1], c[-1])