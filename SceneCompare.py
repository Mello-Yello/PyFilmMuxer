import traceback

from enum import Enum, auto
from multiprocessing.dummy import Pool as ThreadPool
from scipy.stats import spearmanr, pearsonr, zscore

# Inizializzo il comparatore
from perceptual_compare import perceptual_compare as IA_pic_sim
from picturefilters import Effects
from scene import Scene, TimeSerie

# Imposta il numero di thread
pool = ThreadPool(5)

def pearson(tsA: TimeSerie, tsB: TimeSerie):
    a, b = map(lambda x: x.serie, [tsA, tsB])
    if len(b) < len(a):
        a, b = b, a

    seq = [pearsonr(a, b[i:i + len(a)]) for i in range(len(b) - len(a) + 1)]
    scores, errors = zip(*seq)
    return scores

def spearman(tsA: TimeSerie, tsB: TimeSerie):
    a, b = map(lambda x: x.serie, [tsA, tsB])
    if len(b) < len(a):
        a, b = b, a

    seq = [spearmanr(a, b[i:i + len(a)]) for i in range(len(b) - len(a) + 1)]
    scores, errors = zip(*seq)
    return scores


# TODO: Classe di logger (ma in realtà debug) tipo la logger di python
#  ogni classe che la implementa dice "io sono qua" e fornisco questi paramentri
#  (quindi posso dire direttamente tramite i parametri, che vengono generati dinamicamente
#  cosa mostrerò per esempio anche delle statistiche sul tempo impiegato
#  (magari anche su un singolo set di operazioni) e quante volte è successo.
#  Anche se intere sezioni devono riportare o meno il log di debug

class SceneMatch:
    def __init__(self, badScene, goodScene, relax, aSource, vSource):
        self.vSource = vSource
        self.aSource = aSource
        self.badScene = badScene
        self.goodScene = goodScene
        self.relax = relax
        
        print(f"        Created new SceneMatch {self}")
        self.matchResults = self.__evaluate()

    # TODO: Sarebbe meglio farlo gestire alla classe Interval [anche il metodo successivo]
    def overlaps(self, other):
        return any([
            self.badScene.startFrame <= other.badScene.startFrame <= self.badScene.endFrame,
            self.goodScene.startFrame <= other.goodScene.startFrame <= self.goodScene.endFrame,
            self.badScene.startFrame <= other.badScene.endFrame <= self.badScene.endFrame,
            self.goodScene.startFrame <= other.goodScene.endFrame <= self.goodScene.endFrame,

            other.badScene.startFrame <= self.badScene.startFrame <= other.badScene.endFrame,
            other.goodScene.startFrame <= self.goodScene.startFrame <= other.goodScene.endFrame,
            other.badScene.startFrame <= self.badScene.endFrame <= other.badScene.endFrame,
            other.goodScene.startFrame <= self.goodScene.endFrame <= other.goodScene.endFrame
        ])

    def contains(self, other):
        return all([
            self.badScene.startFrame <= other.badScene.startFrame <= self.badScene.endFrame,
            self.goodScene.startFrame <= other.goodScene.startFrame <= self.goodScene.endFrame,
            self.badScene.startFrame <= other.badScene.endFrame <= self.badScene.endFrame,
            self.goodScene.startFrame <= other.goodScene.endFrame <= self.goodScene.endFrame
        ])

    def __lt__(self, other):
        if self.badScene.startFrame < other.badScene.startFrame and self.badScene.startFrame < other.badScene.startFrame:
            return True
        elif self.badScene.startFrame == other.badScene.startFrame and self.badScene.startFrame == other.badScene.startFrame:
            return self.badScene.endFrame < other.badScene.endFrame and self.badScene.endFrame < other.badScene.endFrame
        else:
            return False

    def __repr__(self):
        return f"aSource Scene: {self.badScene}; vSource Scene:{self.goodScene}. Result: " # {self.matchResults}

    def __eq__(self, other):
        if type(other) == type(self):
            return all([
                self.badScene == other.badScene,
                self.goodScene == other.goodScene,
                self.relax == other.relax
            ])
        else:
            return self.matchResults == other

    def improvePartial(self, relax=None):
        assert self.matchResults == MatchResult.PARTIAL

        if not relax:
            relax = self.relax
            fst = self
        elif relax != self.relax:
            fst = SceneMatch(self.badScene, self.goodScene, relax=relax, aSource=self.aSource, vSource=self.vSource),
        else:
            fst = self
        
        
        arr = [
            fst,
            SceneMatch(self.badScene, 
                       Scene(self.vSource, self.goodScene.startFrame, self.vSource.getNextScene(self.goodScene).endFrame),
                       relax=relax, aSource=self.aSource, vSource=self.vSource),
            SceneMatch(Scene(self.aSource, self.badScene.startFrame, self.aSource.getNextScene(self.badScene).endFrame), 
                       self.goodScene,
                       relax=relax, aSource=self.aSource, vSource=self.vSource),
            SceneMatch(Scene(self.aSource, self.badScene.startFrame, self.aSource.getNextScene(self.badScene).endFrame),
                       Scene(self.vSource, self.goodScene.startFrame, self.vSource.getNextScene(self.goodScene).endFrame),
                       relax=relax, aSource=self.aSource, vSource=self.vSource)
        ]
        
        
        # TODO: MA CHE CAZZO SUCCEDE DA QUI ALLA FINE???
        arrP = list(map((lambda x: x.matchResults.getPearson() if x == MatchResult.POSITIVE else 0), arr))

        if max(arrP) != 0:
            i = arrP.index(max(arrP))

            # Aggiungiamo una scena a ciascuna (sia good che bad)
            if i == 3:
                if SceneMatch(
                        self.aSource.getNextScene(self.badScene), 
                        self.vSource.getNextScene(self.goodScene),
                        relax=relax, aSource=self.aSource, vSource=self.vSource
                ) == MatchResult.POSITIVE and \
                        SceneMatch(
                            self.badScene, 
                            self.goodScene,
                            relax=relax + 1, aSource=self.aSource, vSource=self.vSource
                ) == MatchResult.POSITIVE:
                    self.matchResults.type = MatchResult.POSITIVE
                    return self
                else:
                    return arr[3]
            else:
                return arr[i]

        else:
            return MatchResult.NEGATIVE

    def __evaluate(self):
        # TODO: Questi valori non dovrebbero piovere giù dal cielo
        perceputal_score = 0.81 * (0.95 ** self.relax)
        pearson_score = 0.8 * (0.95 ** self.relax)
        spearman_score = 0.8 * (0.95 ** self.relax)
        
        badFrame = self.badScene.getFirstFrame()
        goodFrame = self.goodScene.getFirstFrame()

        # TODO: Invece che controllare e basta, prendere il valore (perceptualScore)
        #  per usarlo nell'unsupervised learning [assieme agli altri]
        if not ic.is_match(
                badFrame.content, 
                Effects(badFrame.content, goodFrame.content).do(goodFrame.content), score=perceputal_score): # DEBUG=True
            return SceneMatchMetrics(MatchResult.NEGATIVE)
        
        
        # TODO: Ora come ora, col nuovo metodo non sono in grado di applicare effetti (crop - resize) 
        #  prima di calcolare la TimeSerie. Domanda: Questo migliora veramente il match?

        # arrA1 = compareFrameWith(self.aSource, self.badScene,  which="first")
        # arrA2 = compareFrameWith(self.vSource, self.goodScene, which="first", effects=effect)
        
        arr1 = self.badScene.getTimeSerie()
        arr2 = self.goodScene.getTimeSerie()
        
        
        # TODO: Anche qui, calcolare
        p = max(pearson(arr1, arr2))
        s = max(spearman(arr1, arr2))
        

        # if p >= 0.9:
        #    return MatchResult.POSITIVE
        # elif p >= 0.8:
        #    if s >= 0.8:
        #        return MatchResult.POSITIVE
        if p >= pearson_score or s >= spearman_score:
            return SceneMatchMetrics(MatchResult.POSITIVE).setPearson(p).setSpearman(s)
        
        return SceneMatchMetrics(MatchResult.PARTIAL).setPearson(p).setSpearman(s)

        # Questo serve per il DTW
        # arrB1 = apply(arrA1, extractJumps)
        # arrB2 = apply(arrA2, extractJumps)


class MatchResult(Enum):
    NEGATIVE = auto()
    POSITIVE = auto()
    PARTIAL = auto()


class SceneMatchMetrics:
    def __init__(self, type):
        self.type = type
    
    def __repr__(self):
        return str(self.type)

    def setPearson(self, p):
        self.pearson = p
        return self

    def getPearson(self):
        return self.pearson

    def setSpearman(self, s):
        self.spearman = s
        return self

    def getSpearman(self):
        return self.spearman

    def __eq__(self, other):
        return self.type == other


class MatchManager:
    def __init__(self, vSource, aSource):
        self.vSource = vSource
        self.aSource = aSource
    
    def match(self, *args):
        return SceneMatch(*args + (self.aSource, self.vSource))


ic = IA_pic_sim(81)
