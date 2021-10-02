import atexit
import cv2
import pickle

from collections import namedtuple, defaultdict
from enum import Enum, auto
from scipy.stats import zscore

from perceptual_compare import HUE_diff
from picturefilters import Resize
from utils import Singleton

FrameComparisonWithinScene = namedtuple("FrameComparisonWithinScene", ["frame", "score", "comparedWith"])

def HUE_score_metric(*args):
    _, _, _, score = HUE_diff(*args)
    return score

# TODO: Spostare in scena
def getFrames(file, scene=None, effects=None, debug=False, startFrame = None, endFrame = None):
    SceneFrame = namedtuple("sceneFrame", ["start", "end"])
    if startFrame is None or endFrame is None:
        sceneFrame = SceneFrame(scene.startFrame, scene.endFrame) # Non mi piace tantissimo prendere gli attributi così
    else:
        sceneFrame = SceneFrame(startFrame, endFrame)
    
    cap = cv2.VideoCapture(str(file.getFile()))
    cap.set(cv2.CAP_PROP_POS_FRAMES, sceneFrame.start)
    
    for i in range(sceneFrame.end - sceneFrame.start + 1):
        success, image = cap.read()
        
        if effects:
            image = effects.do(image)
        
        if debug:
            cv2.imshow(f"Frame: {sceneFrame.start + i}", image)
            cv2.waitKey(0)
            cv2.destroyWindow(f"Frame: {sceneFrame.start + i}")
        
        yield FrameInfo(file, sceneFrame.start + i, image) # TODO: Check that frameNumber is correct


class FrameInfo:
    def __init__(self, sourceFile, frameNumber, content):
        self.sourceFile = sourceFile
        self.frameNumber = frameNumber
        self.content = content


# TODO: FORSE questo può anche essere eliminato
#       OPPURE usato per facilitare la creazione delle Scene iniziali???
class SceneFactory:
    def __init__(self):
        pass
    
    def sceneInterval(self, start, finish):
        return Scene(start,finish)
    
    

class Scene:
    def __init__(self, file, startFrame, endFrame):
        self.file = file
        self.startFrame = int(startFrame)
        self.endFrame = int(endFrame)
        self.timeSerie = None
        self.firstFrame = None
    
    def __eq__(self, other):
        return all([
            self.file == other.file,
            self.startFrame == other.startFrame,
            self.endFrame == other.endFrame,
        ])
    
    # TODO: It would be better to iter all the frames and then just use next() to get only the first 
    def getFirstFrame(self):
        if self.firstFrame is None:
            self.firstFrame = next(getFrames(self.file, startFrame=self.startFrame, endFrame=self.startFrame + 1))
        return self.firstFrame
    
    def getTimeSerie(self):
        if self.timeSerie is None:
            self.timeSerie = TimeSerie(file=self.file, startFrame=self.startFrame, endFrame=self.endFrame)
        
        return self.timeSerie
    
    def __repr__(self):
        return f"{self.startFrame} - {self.endFrame}"

class TimeSerie:
    def __init__(self, file, startFrame, endFrame):
        self.startFrame = startFrame
        self.endFrame = endFrame
        
        self.time, self.serie = zip(*zip(
            self.__timeIterator(file.getFPS()),
            TimeSeriesFactory().withFile(file).get(startFrame, endFrame, compareWith=CompareFrameWith.FIRST)
        ))
    
    def __timeIterator(self, fps):
        i = 0
        while True:
            yield i / fps
            i += 1
    
    def get(self):
        return self.serie


class CompareFrameWith(Enum):
    FIRST = auto()
    FIXED = auto()
    PREV  = auto()

# TODO:
#       1 + SI DEVE RICORDARE I CONFRONTI GIA' FATTI
#       2 + Deve ricevere una metrica per immagini come default 
#       3 - Deve poter accettare solo metriche per immagini
#       4 + Eseguire zscore sulla sequenza prima di restituirla
#       5 - Cambiare nome classe
#       6 + Delegare il recupero dei 'match' mancanti alle due sottoclassi, in maniera corretta
#       7 + Check: Verificare che i punteggi calcolati da get() e MetricGetter (PySceneDetect) e compareFrameWith siano più o meno gli stessi 
#       8 - Nell'init caricare i match del csv [MA solo SE metrica == HUE_diff]
#       9 - Effettuare salvataggio e successiva ricarica delle comparazioni
#            - Se eseguito tra 2 frame dello stesso video, va salvato nella cartella relativa al file 
#            - Se eseguito tra 2 frame di video diversi, va salvato in una cartella comune ad entrambi
#      10 - Si può usare per contare il numero di confronti pratici rispetto a quelli teorici 
#      11 - Devo poter passare effects 
#        - 

DEFAULT_DOWNSCALE_FACTORS = {
    3200: 12,   # ~4k
    2100:  8,   # ~2k
    1700:  6,   # ~1080p
    1200:  5,
    900:   4,   # ~720p
    600:   3,
    400:   2    # ~480p
}
"""Dict[int, int]: The default downscale factor for a video of size W x H,
which enforces the constraint that W >= 200 to ensure an adequate amount
of pixels for scene detection while providing a speedup in processing. """



def compute_downscale_factor(frame_width):
    # type: (int) -> int
    """ Compute Downscale Factor: Returns the optimal default downscale factor based on
    a video's resolution (specifically, the width parameter).
    Returns:
        int: The defalt downscale factor to use with a video of frame_height x frame_width.
    """
    for width in sorted(DEFAULT_DOWNSCALE_FACTORS, reverse=True):
        if frame_width >= width:
            return DEFAULT_DOWNSCALE_FACTORS[width]
    return 1


class TimeSeriesFactory(metaclass=Singleton):
    def __init__(self):
        self.timeSeries = {}
    
    def withFile(self, file):
        if file not in self.timeSeries.keys():
            self.timeSeries[file] = TimeSeriesGetter(file)

        return self.timeSeries[file]


class TimeSeriesGetter():
    def __init__(self, file, metric = HUE_score_metric):
        self.file = file
        self.metric = metric
        self.d = defaultdict(dict)
        
        self.__initResize()
        self.__load()
        atexit.register(self.__save)
    
    def __initResize(self):
        # E' bello che ravani per prendere l'altezza? No.
        scene = self.file.getScenes()[0].getFirstFrame()
        height = len(scene.content)
        width = len(scene.content[0])
        downscaleFactor = compute_downscale_factor(width)
        self.effect = Resize(width=width // downscaleFactor, height=height // downscaleFactor)

    def __load(self):
        if self.getCacheFile().exists():
            with self.getCacheFile().open('rb') as f:
                self.file, self.metric, self.d = pickle.load(f)
    
    def __save(self):
        with self.getCacheFile().open('wb') as f:
            pickle.dump((self.file, self.metric, self.d), f)
    
    def getCacheFile(self):
        return self.file.file.with_name(self.file.file.name + '.cache')
        
    def get(self, start, finish, compareWith, fixedFrame=None, norm=True):            
        self.getMissingComparisons(start, finish, compareWith, fixedFrame)
        output = [self.d[x][y] for x, y in self.iterComparisons(start, finish, compareWith, fixedFrame)]
        
        if norm:
            return zscore(output)
        else:
            return output
    
    def iterComparisons(self, start, finish, method, frameCompared = None):
        # skip the comparison of a frame with itself, since it's meaningless
        if any([method == CompareFrameWith.FIRST,
                method == CompareFrameWith.FIXED and start == frameCompared]
        ):
            moveBy = 1
        else:
            moveBy = 0
        
        for i in range(start + moveBy, finish + moveBy):
            if method == CompareFrameWith.PREV:
                yield i, i+1 # TODO: Se i+1 va OLTRE il file, come bisogna comportarsi???
            elif method == CompareFrameWith.FIRST:
                yield start, i
            elif method == CompareFrameWith.FIXED:
                yield frameCompared, i
    
    def getMissingComparisons(self, start, finish, compareWith, fixedFrame):
        if compareWith == CompareFrameWith.FIXED:
            assert fixedFrame is not None, "If 'compareWith == FIXED' then 'fixedFrame' should hold a value"
            self.__getMissingComparisonsFixedFrame(start, finish, fixed = fixedFrame)
        elif compareWith == CompareFrameWith.FIRST:
            self.__getMissingComparisonsFixedFrame(start, finish, fixed = start)
        elif compareWith == CompareFrameWith.PREV:
            self.__getMissingComparisonsPrevFrame(start, finish)
        else:
            raise BaseException(f"Unknown value for compareWith = {compareWith}")
    
    def __getMissingComparisonsFixedFrame(self, start, finish, fixed):
        toCompare = set(range(start, finish + 1)).difference(set(self.d[fixed].keys()))
        
        if len(toCompare):
            print(f"BAD NEWS. There are still {len(toCompare)} matches to be calculated")
            frameToCompare = next(getFrames(self.file, startFrame=fixed, endFrame=fixed, effects=self.effect))
            for frame in getFrames(self.file, startFrame=min(toCompare), endFrame=max(toCompare), effects=self.effect):
                if frame.frameNumber in toCompare:
                    self.d[fixed][frame.frameNumber] = self.metric(frameToCompare, frame)
        else:
            print("Good news. Everything has already been calculated")
    
    def __getMissingComparisonsPrevFrame(self, start, finish):
        toCompare = []
        for x, y in self.iterComparisons(start, finish, CompareFrameWith.PREV):
            try:
                self.d[x][y]
            except KeyError:
                toCompare.append(x)

        if len(toCompare):
            print(f"BAD NEWS. There are still {len(toCompare)} matches to be calculated")
            frameToCompare = None
            for frame in getFrames(self.file, startFrame=min(toCompare), endFrame=max(toCompare)+1, effects=self.effect):
                if frameToCompare is None:
                    frameToCompare = frame
                else:
                    if frame.frameNumber in toCompare or frameToCompare.frameNumber in toCompare:
                        self.d[frameToCompare.frameNumber][frame.frameNumber] = self.metric(frameToCompare, frame)
                    
                    frameToCompare = frame
        else:
            print("Good news. Everything has already been calculated")