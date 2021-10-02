import cv2
import numpy as np
import time

from abc import ABC, abstractmethod
from fastdtw import dtw, fastdtw
from math import log
from sim import similarity
from scipy.spatial.distance import euclidean

class compare(ABC):
    def __init__(self, threshold, visualize):
        self.visualize = visualize
        self.threshold = threshold / 100
        
        self.tot_compare_time = 0
        self.comparisons = 0
    
    @abstractmethod
    def score(self, a, b):
        pass

    #@abstractmethod
    #@staticmethod
    #def visualizeComparison():
    #    pass

    def above_threshold(self, score):
        return score >= self.threshold

    def is_match(self, a, b, score=None, DEBUG=False):
        if not score:
            return self.above_threshold(self.score(a, b, DEBUG))
        else:
            return self.score(a, b, DEBUG) >= score


def avg(x):
    return sum(x)/len(x)


class DTW_compare(compare):
    def __init__(self, threshold=100, visualize=False):
        super().__init__(threshold, visualize)
    
    @staticmethod
    def findMultiplierDTW(good, bad, warp):
        s = list(map((lambda w: good[w[0]] / bad[w[1]]), warp))
        return avg([s[len(s) // 2], s[len(s) // 2 + 1]])
    
    @staticmethod
    def mydist(u, v):
        return abs(u[1] - v[1])
    
    # TODO: Sinceramente mi sentirei di abbandonare scoreDistance 
    #  [e probsabilmente anche findMultiplier, questo lo lasciamo alla mia classe di confronto]
    def score(self, x, y, findMultiplier = False, scoreDistance = False, approx=True, distOnly=True):
        #max_length = max(len(x), len(y.get()))
        #mydist2 = (lambda a,b: abs(a[1] - b[1]) + log(abs(a[0] - b[0])+1, max_length))
        
        if approx:
            distance, path = fastdtw(x.get(), y.get(), dist=euclidean)
        else:
            distance, path = dtw(x.get(), y.get(), dist=euclidean)
        
        #if self.visualize:
        #    self.visualizeComparison(x.get(), y.get(), path)
        
        if findMultiplier:
            c = self.findMultiplierDTW(x.get(), y.get(), path)
            #(bI, bV), (gI, gV) = zip(*x.get()), zip(*y.get())
            
            # Al limite se good è y, sostituisci e festa finita
            gI, gV = zip(*y.get())
            gV2 = map((lambda a: a * c), gV)
            
            #bs, gs = zip(bI, bV), zip(gI, gV)
            distance, path = fastdtw(x.get(), zip(gI, gV2), dist=euclidean)
        
        #if scoreDistance:            
        #    true_distance = 0
        #    max_length = max(len(x.get()), len(y.get()))
        #    for p in path:
        #        a = x.get()[p[0]]
        #        b = y.get()[p[1]]
        #        true_distance += self.mydist(a, b)
        #    
        #    return true_distance
        #else:
        #    return distance

        #if self.visualize:
        #    return distance, self.visualizeComparison(x.get(), y.get(), path)
        #else:
        
        if distOnly:
            return distance
        else:
            return distance, path
            
        
        


class perceptual_compare(compare):
    
    def __init__(self, threshold = 70, visualize=False):
        super().__init__(threshold, visualize)
        self.compare = similarity.similarity()
        
        self.tot_compare_time = 0
        self.comparisons = 0
    
    
    # TODO: Qui sono unite la logica, oltre alla misurazione del tempo. Non buono
    def score(self, img1, img2, DEBUG=False):
        t0 = time.time()
        
        def resize(imgA, imgB):

            height0, width0, _ = imgA.shape
            height1, width1, _ = imgB.shape

            if height0 > height1:
                if width0 > width1:
                    imgA = cv2.resize(imgA, (width1, height1))
                else:
                    imgA = cv2.resize(imgA, (width0, height1))
                    imgB = cv2.resize(imgB, (width0, height1))
            else:
                if width0 > width1:
                    imgB = cv2.resize(imgB, (width0, height0))
                else:
                    imgA = cv2.resize(imgA, (width1, height0))
                    imgB = cv2.resize(imgB, (width1, height0))

            return (imgA[:, :, ::-1], imgB[:, :, ::-1])

        img1, img2 = resize(img1[:, :, ::-1], img2[:, :, ::-1])
            
        val = 1 - self.compare.scoreCV2(img1, img2)
        
        
        if DEBUG:
            vis = np.concatenate((img1, img2), axis=1)
            cv2.imshow(f"Similarity score: {val}", vis)
            cv2.waitKey(0)
            cv2.destroyWindow(f"Similarity score: {val}")

        #HUE_diff(img1, img2)
        t1 = time.time()

        self.tot_compare_time += t1 - t0
        self.comparisons += 1
        
        if DEBUG:
            print(f"Avg. time for a comparison ({self.comparisons} done) is {self.tot_compare_time/self.comparisons}s")
        
        return val
    
    
    def best_match(self, img1, imgs):
        best_index = -1
        best_score = -1
        
        for i, img2 in enumerate(imgs):
            score = self.score(img1, img2)
            
            if score > best_score:
                best_index = i
                best_score = score
        
        if best_index >= 0:
            return (imgs[best_index], self.above_threshold(best_score))
        else:
            return None


def HUE_diff(last_frame, cur_frame):
    delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0
    
    num_pixels = cur_frame.content.shape[0] * cur_frame.content.shape[1]
    curr_hsv = cv2.split(cv2.cvtColor(cur_frame.content, cv2.COLOR_BGR2HSV))
    
    last_hsv = cv2.split(cv2.cvtColor(last_frame.content, cv2.COLOR_BGR2HSV))

    delta_hsv = [0, 0, 0, 0]
    for i in range(3):
        num_pixels = curr_hsv[i].shape[0] * curr_hsv[i].shape[1]
        curr_hsv[i] = curr_hsv[i].astype(np.int32)
        last_hsv[i] = last_hsv[i].astype(np.int32)
        delta_hsv[i] = np.sum(np.abs(curr_hsv[i] - last_hsv[i])) / float(num_pixels)
    
    delta_hsv[3] = sum(delta_hsv[0:3]) / 3.0
    delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv
    
    return delta_h, delta_s, delta_v, delta_hsv_avg