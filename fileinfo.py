import csv
import atexit
import shutil
import subprocess

from numpy import array
from math import log
from pathlib import Path

from scene import Scene
from utils import fileMD5, changeDirectory

class FileInfo:
    def __init__(self, file, needsFilters = False):
        p = Path(file).resolve()
        assert p.is_file()
        
        self.file  = p
        self.needsFilters = needsFilters
        
        # Determina il nome del file
        self.fileNameWithExt = self.getFile().name
        self.fileName = self.getFile().stem

        # Posso settare il numero di frame ora (prima erano fissi primo e ultimo). Ora il primo è 01
        self.sceneFormat = self.fileName + "-Scene-{0}-01.jpg"  # ".Scene-{0}-IN.jpg"
        
        # Array di tuple (scena, frame)
        self.scenes = None
        
        self.fps = None

        
        # Genera il nome della cartella usando l'MD5 del file
        path = p.parent / f".{fileMD5(self.file)}"
        
        # Crea la cartella (ed eventuali altre cartelle necessarie)
        self.tmpDir = path
        print(f"path is: {path}")
        
        if not path.exists():
            path.mkdir()
            self.__splitScenes()
        
        
        # Da attivare solo una volta operativi
        # atexit.register(self.exit_handler)
    
    def __splitScenes(self):
        with changeDirectory(self.getDir()):
            subprocess.check_output(["scenedetect", "--input", str(self.getFile()), "-s", "OUTPUT.csv", "detect-content", "save-images", "--num-images", "1", "list-scenes"]).splitlines()
        
        self.__splitScenesCSV()

    def getFile(self):
        return self.file
    
    def getDir(self):
        return self.tmpDir
    
    def getCSVfile(self):
        return self.getDir() / f"{self.fileName}-Scenes.csv"
    
    def __splitScenesCSV(self):
        l = list(map(lambda x: x.endFrame-1, self.getScenes()))
        
        # Non so perchè ma la prima scena viene considerata avere +1
        l[0] -= 1
        
        read_frame_info_csv(self.getFrameInfoCSV(), splitByScene=l)
    
    def getFrameInfoCSV(self):
        return self.getDir() / "OUTPUT.csv"
    
    def getFPS(self):
        if not self.fps:
            with open(self.getFrameInfoCSV(), 'r') as f:
                content = f.read().splitlines()
            
            self.fps = float(content[0].split(',')[1])
            print(f"Setting FPS to: {self.fps}")
        
        return self.fps
    
    def getScenes(self):
        if self.scenes is None:
            with open(self.getCSVfile(), newline='') as csvdest:
                next(csvdest)  # Skip header
                destreader = csv.DictReader(csvdest, delimiter=',')
                self.scenes = [Scene(self, row['Start Frame'], row['End Frame']) for row in destreader]
            
        return self.scenes
    
    def getSceneIndexes(self, scene: Scene):
        startIndex, endIndex = None, None
        for i, s in enumerate(self.getScenes()):
            if s.startFrame == scene.startFrame:
                startIndex = i
            
            if s.endFrame == scene.endFrame:
                endIndex = i
                
                return startIndex, endIndex

        return startIndex, endIndex
    
    def getNextScene(self, scene: Scene):
        for s in self.getScenes():
            if s.startFrame >= scene.endFrame:
                return s
    
    def getPrevScene(self, scene: Scene):
        for s in reversed(self.getScenes()):
            if s.endFrame <= scene.startFrame:
                return s
    
    def getScenesCount(self):
        return len(self.getScenes())
    
    def needsEffects(self):
        return self.needsFilters

    def cleanUp(self):
        shutil.rmtree(self.getDir())
        
    def exit_handler(self):
        self.cleanUp()


class Info:
    def __init__(self, frameInfo):
        self.FrameNumber, self.Timecode, self.content_val, self.delta_hue, self.delta_lum, self.delta_sat = frameInfo.split(',')
        self.FrameNumber = int(self.FrameNumber)
        self.content_val = float(self.content_val)
        self.delta_hue = float(self.delta_hue)
        self.delta_lum = float(self.delta_lum)
        self.delta_sat = float(self.delta_sat)


class InfoManager:
    def __init__(self):
        self.infos = []
        self.normalized = False
        self.np = False

    def add(self, info):
        self.infos.append(info)

    def getFrames(self):
        return [i.FrameNumber for i in self.infos]
    
    # TODO: Necessario usare numpy.array? Migliora le performance?
    def initNumpyVal(self):
        self.npContentVal = array(self.getVal())

    def getNumpyVal(self):
        if not self.np:
            self.initNumpyVal()

        return self.npContentVal

    def getVal(self):
        return [i.content_val for i in self.infos]

    def getNormalizedVal(self):
        if self.normalized:
            return self.normalizedVals
        else:
            arr = self.getVal()
            m = max(arr)

            for i in range(len(arr)):
                arr[i] = log(arr[i], m)

            self.normalized = True
            self.normalizedVals = arr

            return arr

    def getHue(self):
        return [i.delta_hue for i in self.infos]

    def getLum(self):
        return [i.delta_lum for i in self.infos]

    def getSat(self):
        return [i.delta_sat for i in self.infos]


def read_frame_info_csv(file, header=True, splitByScene=None):
    # Non è bello il modo in cui accedo ai file
    # tutto un po' mischiato

    with open(file, 'r') as f:
        content = f.read().splitlines()

    if header:
        content = content[2:]

    im = InfoManager()

    if splitByScene:
        print(splitByScene)
        j = 1
        k = splitByScene[j - 1]

    for c in content:
        i = Info(c)
        im.add(i)

        if splitByScene:

            # if i.content_val > 30: # default content-detect threshold

            with open(file.parent / f'scene-{j}.csv', 'a') as f:
                f.write(f'{c}\n')

            k -= 1

            if k < 0:
                j += 1

                if j <= len(splitByScene):
                    k = splitByScene[j - 1]

    return im