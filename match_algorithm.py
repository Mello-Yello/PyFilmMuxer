from enum import Enum, auto
from math import ceil
from numpy import infty
from pprint import pprint
from collections import namedtuple
from clint.textui import colored

from DTW_LB import kimFL
from SceneCompare import MatchResult, MatchManager
from perceptual_compare import DTW_compare
from Visualizer import VisualizeSceneComparisons


# TODO: Questa classe si deve occupare di fornire gli iteratori!
class Interval:
    def __init__(self, badStart, badEnd, goodStart, goodEnd):
        self.badStart = badStart
        self.badEnd = badEnd
        self.goodStart = goodStart
        self.goodEnd = goodEnd
        #assert self.isValid(), f"Invalid interval: {self}"

    def isValid(self):
        return not(self.badStart > self.badEnd or self.goodStart > self.goodEnd)

    def __repr__(self):
        return f"[{self.badStart}, {self.badEnd}] - [{self.goodStart}, {self.goodEnd}]"

    def __contains__(self, other):
        b, g = other
        return self.badStart <= b <= self.badEnd and self.goodStart <= g <= self.goodEnd


def kangaroo(l, start, end):
    Kang = namedtuple("Kangaroo", ["index", "item"])
    perm = list(range(start, end + 1))
    
    new = []
    for i in range(ceil(len(perm) / 2)):
        new.append(Kang(perm[i], l[perm[i]]))
        j = -1 * (i + 1)
        
        if perm[i] != perm[j]:
            new.append(Kang(perm[j], l[perm[j]]))
    
    assert len(new) == end - start + 1, f"start = {start}; end = {end}.   =>   {len(new)} != {end - start + 1}"
    return list(reversed(new))


class ExpandDirection(Enum):
    LEFT = auto()
    RIGHT = auto()

class MatchVideos:
    def __init__(self, aSource, vSource):
        self.dtw = DTW_compare()
        self.aSource = aSource
        self.vSource = vSource
        self.matchManager = MatchManager(vSource=vSource, aSource=aSource)
        self.k = 25
        self.algVisualizer = VisualizeSceneComparisons(aSource, vSource)
     
    def findMatches(self, startInterval, relax=0):
        if not startInterval.isValid():
            return [], []

        stack = [startInterval]
        matches = []
        unmatchedIntervals = []

        while stack:
            interval = stack.pop()
            print(f"Current interval is: {interval}")

            found = False
            
            for sourceSceneNumber, sourceScene in kangaroo(self.aSource.getScenes(), interval.badStart, interval.badEnd):
                # Questo non mi piace tanto... Credo di poterlo fare come 'else' del for
                if found:
                    break
                
                sourceSceneSequence = sourceScene.getTimeSerie()

                # TODO: Al momento ho deciso di valutare solo la migliore. Un array ** POTREBBE ** essere una buona soluzione
                #  anche se andare a ravanare probabilmente può portare più falsi positivi che altro 
                min_score = infty
                best_match = None
                best_matchNumber = None
                done = 0

                for i, (destSceneNumber, destScene) in enumerate(kangaroo(self.vSource.getScenes(), interval.goodStart, interval.goodEnd)):
                    destSceneSequence = destScene.getTimeSerie()
                    
                    done += 1
                    print()
                    print("sourceSceneSequence is:")
                    print(sourceSceneSequence)
                    print()
                    print("destSceneSequence is:")
                    print(destSceneSequence)

                    print(f"    Trying to compare {sourceScene} with {destScene}")
                    if kimFL(sourceSceneSequence, destSceneSequence) < min_score:
                        seqScore = self.dtw.score(sourceSceneSequence, destSceneSequence)
                        print(f"DTW {sourceScene} - {destScene}: {seqScore}")

                        if seqScore < min_score:
                            min_score = seqScore
                            best_match = destScene
                            best_matchNumber = destSceneNumber

                        # La distanza tra sequenze è superiore rispetto ad una già trovata.
                        # Questo non è il candidato ideale. E se è uguale? 
                        # Bella merda ... Soprattutto se done < k, perchè per l'idea che ho 
                        # dell algoritmo non controllo ancora la somiglianza immagini.
                        # La soluzione potrebbe essere avere un manager dei confronti, che si
                        # ricorda le comparazioni tra sequenze o immagini + filtri e si ricorda 
                        # i risultati. In pratica una cache. Se c'è l'uguaglianza (improbabile ma  
                        #  possibile), controlliamo le immagini. Sarebbe da vedere se questa cache
                        # può sfruttare dei dati calcolati anche qualora performi delle modifiche.
                        # ES: Ho un arr. di sequenze: [s0, s1, s2, s3, s4]. Unisco s3 ed s4 avendo
                        # ora [s0, s1, s2, s3]. Facendo il confronto di immagini tra s3 ed una sequenza
                        # sX, vorrei continuare a usare il risultato già calcolato, se disponibile.

                        elif seqScore == min_score:
                            pass

                        self.algVisualizer.addBadMatch(sourceSceneNumber, destSceneNumber)
                    else:
                        print(colored.red(f"DTW {sourceScene} - {destScene}"))
                        self.algVisualizer.addSkippedMatch(sourceSceneNumber, destSceneNumber)

                    if any([
                        interval.goodEnd - interval.goodStart == i and done < self.k,
                        # Non raggiungeremo mai k, ma possiamo comunque avere un match  
                        done == self.k,  # Abbiamo aspettato k confronti, vediamo se abbiamo un match
                        done > self.k and min_score == seqScore  # Non dobbiamo più aspettare, vediamo se current è un match
                    ]) and best_match:  # Questo ci assicura che un match sia stato trovato
                        print(f"{sourceScene} BAD - {best_match} GOOD.                                           COMPARISONS = {done}")

                        match = self.matchManager.match(sourceScene, best_match, relax)
                        
                        # TODO: Fare in modo che il rilassamento sia automatico, e perciò solo POSITIVE e NEGATIVE
                        if match == MatchResult.PARTIAL:
                            match = match.improvePartial(relax=relax)

                        if match == MatchResult.POSITIVE:
                            self.algVisualizer.removeTemporaryMatches()
                            self.algVisualizer.addMatch(match)

                            newMatchesR, (r1, r2) = self.expandMatches(
                                match.goodScene, sourceSceneNumber,
                                match.badScene, destSceneNumber,
                                interval, direction=ExpandDirection.RIGHT, relax=relax + 1)
                            
                            newMatchesL, (l1, l2) = self.expandMatches(
                                match.goodScene, sourceSceneNumber,
                                match.badScene, destSceneNumber,
                                interval, direction=ExpandDirection.LEFT,  relax=relax + 1)

                            # matches.append((sourceSceneNumber, best_match))
                            matches.append(match)
                            
                            print("MATCHES:")
                            pprint(matches)
                            print()
                            print(newMatchesR, (r1, r2))
                            print(newMatchesL, (l1, l2))
                            print()
                            
                            assert r1 > 0 and r2 > 0 # CREDO?
                            assert l1 < 0 and l2 < 0 # CREDO?
                            
                            matches += newMatchesR
                            matches += newMatchesL

                            stack.append(
                                Interval(sourceSceneNumber + r1, interval.badEnd, best_matchNumber + r2, interval.goodEnd))

                            # Non sottraggo in quanto i valori sono già sottratti
                            stack.append(
                                Interval(interval.badStart, sourceSceneNumber + l1, interval.goodStart, best_matchNumber + l2))

                            found = True
                            break

                        else:
                            print(f"{sourceScene} - {best_match} is not a match... =(")

                self.algVisualizer.removeTemporaryMatches()

            if not found:
                unmatchedIntervals.append(interval)

        return matches, unmatchedIntervals
    
    # TODO: Se fa casini si può anche disabilitare
    def expandMatches(self, sourceStartScene, sourceNumber, destStartScene, destNumber, interval, direction: ExpandDirection, relax=1):
        if direction == ExpandDirection.LEFT:
            moveV = lambda s: self.vSource.getPrevScene(s)
            moveA = lambda s: self.aSource.getPrevScene(s)
        else:
            moveV = lambda s: self.vSource.getNextScene(s)
            moveA = lambda s: self.aSource.getNextScene(s)
        
        
        moveBy = -1 if direction == ExpandDirection.LEFT else 1
        m = []

        a, b = moveBy, moveBy
        while (sourceNumber + a, destNumber + b) in interval:
            match = self.matchManager.match(moveA(destStartScene), moveV(sourceStartScene), relax)
            # prevA, prevB = a, b
            
            if match == MatchResult.POSITIVE:
                pass
            
            # AL MOMENTO PARTIAL SIGNIFICA CHE IL PRIMO FRAME COINCIDE PERCIò estendo verso DX
            elif match == MatchResult.PARTIAL and direction == ExpandDirection.RIGHT:
                match = match.improvePartial(relax=relax)
                
                if match == MatchResult.NEGATIVE:
                    break
                
                #a = match.badScenes[-1] - sourceNumber
                #b = match.goodScenes[-1] - destNumber
                
                # TODO: Non so se il numero così va bene, oppure va sottratto od aggiungo un + o - 1
                # Il fatto è che moveBy comunque prima era 1 o -1, non dovrebbe diminuire anche se è la stessa scena
                a = self.aSource.scenes.index(self.aSource.getNextScene(match.badScene)) - sourceNumber  # -1 ???
                b = self.vSource.scenes.index(self.vSource.getNextScene(match.goodScene)) - destNumber   # -1 ???
            else:
                break
            
            m.append(match)
            self.algVisualizer.addMatch(match)

            a += moveBy
            b += moveBy
            destStartScene = moveA(destStartScene)
            sourceStartScene = moveV(sourceStartScene)

        return m, (a, b)