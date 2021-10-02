# Non so se fare fare una classe che si occupi di tutto, oppure semplicemente implementi un'interfaccia
# che poi deve essere implementata dalle varie classi


# Parliamo ora di cosa ci interessa mostrare nel DTW:
# - Abbiamo 2 sequenze. Vogliamo mostrare
#   * Sequenza 1
#   * Sequenza 2
#   * Sequenza 1 + 2
#   * Sequenza 1 + 2 + DTW
# - 

from typing import List
import matplotlib.pyplot as plt

from SceneCompare import MatchResult
from utils import suppressException

def subplot(i, k):
    if k:
        return i, k
    else:
        return i

# Usato solo in useful_scripts (DTWinDepth)
# TODO: Considerare di ricevere solo grafici con squeeze = False [e poi ovviamente andare a cercare tutte le visualizzazioni]
#  e modificarle di conseguenza [aggiungere squeeze=False nelle chiamate a subplots(...)  ]
def visualize_DTW_Comparison(bad_plot, good_plot, path, axs, pathOnly=False, k=None):
    j = 0
    bA, bB = zip(*bad_plot)
    gA, gB = zip(*good_plot)
    
    if not pathOnly:
        axs[subplot(j, k)].plot(bA, bB, 'ro')
        axs[subplot(j, k)].plot(gA, gB, 'bo')
        j+=1

    axs[subplot(j, k)].plot(bA, bB, 'ro')
    axs[subplot(j, k)].plot(gA, gB, 'go')

    for p in path:
        a = bad_plot[p[0]]
        b = good_plot[p[1]]

        axs[subplot(j, k)].plot((a[0], b[0]), (a[1], b[1]), 'k')


# TODO: 
#   1 - Check che i match disegnati siano quelli corretti
#   2 - Far andare la classe con Scene (e rimuovere tutta la storia del doNothing)

class VisualizeSceneComparisons:
    def __init__(self, source, dest, doNothing = False):
        self.source = source
        self.dest = dest
        self.testedLines = []
        self.doNothing = doNothing
        
        # TODO: Questo non mi piace per niente 
        plt.ion()
        plt.plot(list(range(len(source.getScenes()))), [1] * len(source.getScenes()), 'y')
        plt.plot(list(range(len(dest.getScenes()))), [0] * len(dest.getScenes()), 'b')
        plt.pause(0.005)
        plt.draw()
    
    
    def addMatch(self, match):
        def __isSingle(indexes):
            assert len(indexes) == 2
            return indexes[0] == indexes[1]
        
        if self.doNothing:
            return 
        
        if match.matchResults == MatchResult.POSITIVE:
            self.removeTemporaryMatches()

            badSceneIndex  = self.source.getSceneIndexes(match.badScene)
            goodSceneIndex = self.dest.getSceneIndexes(match.goodScene)
            
            # Il match è per una scena di source con 1 scena di dest
            if __isSingle(badSceneIndex) and __isSingle(goodSceneIndex):
                print(f"{badSceneIndex[0]} - {goodSceneIndex[0]} IS A MATCH! =)")
                plt.plot((badSceneIndex[0], goodSceneIndex[0]), (1, 0), 'g')
            else:
                # Il match per scene 1 <-> n, oppure n <-> m
                l = list(sorted([[badSceneIndex[0], 1], [badSceneIndex[1], 1]]) + sorted(
                    [[goodSceneIndex[0], 0], [goodSceneIndex[1], 0]], reverse=True))
                t = plt.Polygon(l, 'y')
                plt.gca().add_patch(t)

                x = list(sorted([badSceneIndex[0], badSceneIndex[1]]))
                x = list(range(x[0], x[1] + 1))

                y = list(sorted([goodSceneIndex[0], goodSceneIndex[1]]))
                y = list(range(y[0], y[1] + 1))

                print(f"{x} - {y} IS A MATCH! =)")

            plt.pause(0.005)
            plt.draw()
    
    def addBadMatch(self, sourceScene, destScene):
        if self.doNothing:
            return 
        
        ln, = plt.plot((sourceScene, destScene), (1, 0), 'r')
        plt.pause(0.005)
        self.testedLines.append(ln)
    
    def addSkippedMatch(self, sourceScene, destScene):
        if self.doNothing:
            return 
        
        ln, = plt.plot((sourceScene, destScene), (1, 0), 'k')
        plt.pause(0.005)
        self.testedLines.append(ln)
    
    # Viene chiamata quando: Ho provato tutti i possibili match per una certa scena, oppure ho terminato trovando un match
    # Nel primo caso però, sono obbligato a chiamare manualmente da match_algorithm removeSkippedMatched
    # Perchè dico questo? Sarebbe stato bello gestirlo in automatico da questa classe, magari alla fine di addCorrectMatch 
    def removeTemporaryMatches(self):
        if self.doNothing:
            return 
        
        with suppressException(ValueError):
            for i, ln in enumerate(self.testedLines):
                ln.remove()
        
        self.testedLines = []
        