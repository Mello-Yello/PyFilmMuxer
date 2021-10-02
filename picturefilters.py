import cv2
import math
from clint.textui import puts, colored

from perceptual_compare import perceptual_compare as IA_pic_sim
from utils import confidenceInterval, maxima


class Blur:
    def __init__(self, radius=None, sigma=None):
        self.r = radius
        self.s = sigma

    def do(self, img):
        if self.r is None or self.s is None:
            return img
        else:
            return  cv2.GaussianBlur(img, (self.r, 0), self.s)

class FindBlur:
    def __init__(self, image1, image2):
        self.image1 = image1
        self.image2 = image2

    def getBest(self):
        def get_pic_size(pic):
            h0, w0, _ = pic.shape
            return (w0, h0)


        img1x, img1y = get_pic_size(self.image1)
        img2x, img2y = get_pic_size(self.image2)

        best_radius = 0
        best_sigma = 0
        best_score = compare.score(self.image1, self.image2)
        best_blur = Blur()

        for radius in range(9 + 1):
            # since sigma = 0 doesn't do anything
            for sigma in range(1, 9 + 1):

                if radius > 0 and radius % 2 == 0:
                    continue

                blur = Blur(radius, sigma)
                blurred = blur.do(self.image2)
                #blur = cv2.GaussianBlur(self.image2, (radius, 0), sigma)


                # cv2.imwrite(f"cv2_gaussian/{radius}{sigma}.jpg", blur)

                # process = subprocess.Popen(["convert", image2, "-gaussian-blur", f"{radius}x{sigma}", "out_tmp.jpg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # process.communicate()

                score = compare.score(self.image1, blurred)

                if score > best_score:
                    puts(colored.green(f"{score} > {best_score} with -gaussian-blur {radius}x{sigma}"))
                    best_score = score
                    best_blur = blur
                else:
                    puts(colored.red(f"{score} <= {best_score} with -gaussian-blur {radius}x{sigma}"))

        return best_blur

class Crop:
    def __init__(self, x1, x2, y1, y2):
        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

    def do(self, img):
        return img[self.y1:self.y2, self.x1:self.x2]

    def __str__(self):
        return f"Cropping to: [{self.x1}]:[{self.x2}],[{self.y1}]:[{self.y2}]"


class Resize:
    def __init__(self, img=None, width=None, height=None):
        if img is None:
            if width is not None and height is not None:
                self.w = width
                self.h = height
            else:
                raise BaseException()
        else:
            imgY, imgX, _ = img.shape

            if width is not None and height is not None:
                self.w = width
                self.h = height
            elif width is not None and height is None:
                self.w = width
                self.h = math.floor((imgY * width) / imgX)
            elif width is None and height is not None:
                self.h = height
                self.w = math.floor((imgX * height) / imgY)
            else:
                raise BaseException()


    def do(self, img):
        return cv2.resize(img, (self.w, self.h))

    def __str__(self):
        return f"Resize to: {self.w}w x {self.h}h"


class FindCrop:
    def __init__(self):
        self.goodCrops = []
        self.k = 5 # after finding a good crop k times, use statiscal methods to reduce cropping size
        self.minY = self.maxY = None


    def __resizeScore(self, i1, i2, y):
        def get_pic_size(pic):
            h0, w0, _ = pic.shape
            return (w0, h0)

        img1x, img1y = get_pic_size(i1)

        # ridimensiona l'immagine
        # resized = cv2.resize(self.image2, (math.floor((img2x * y) / img2y), y))
        resize = Resize(img=i2, height=y)
        resized = resize.do(i2)

        # ottieni le nuove dimensioni (cosi' non tiriamo ad indovinare, anche se forse le possiamo determinare a priori, il che sarebbe oro)
        tmp_x, tmp_y = get_pic_size(resized)

        future_y = 0 if tmp_y < img1y else int(abs(tmp_y - img1y) / 2)
        future_x = 0 if tmp_x < img1x else int(abs(tmp_x - img1x) / 2)

        # effettua il crop
        crop = Crop(future_x, img1x + future_x, future_y, img1y + future_y)
        cropped = crop.do(resized)

        if get_pic_size(i1) == get_pic_size(cropped):
            match = compare.score(i1, cropped)
        else:
            print(f"{get_pic_size(i1)} !== {get_pic_size(cropped)}")
            match = -1

        return (match, crop, resize)

    @staticmethod
    def get_pic_size(pic):
        h0, w0, _ = pic.shape
        return (w0, h0)
    
    # Quello che voglio è che la più grande venga trasformata come la più piccola
    def getBest(self, img1, img2, algorithm, debug=False):
        img2x, img2y = self.get_pic_size(img2)
        img1x, img1y = self.get_pic_size(img1)
        
        assert img1y <= img2y
        
        if img2y < img1y:
            img1x, img1y, img2x, img2y = img2x, img2y, img1x, img1y

        best_match = None
        best_resize = None
        best_crop = None
        best_y = None
        
        
        # TODO: Sebbene questo funzioni, fa comunque sempre una comparazione. Se potessimo sbarazzarcene sarebbe oro
        # Cerca il primo resize "buono"
        for y in range(img1y, img2y):
            if self.__resizeScore(img1, img2, y) != -1:
                fst = y
                break                
        else:
            raise BaseException(f"Couldn't find a single good resize. Is {img1y} > {img2y}?")
        
        def f(x):
            return self.__resizeScore(img1, img2, x)[0]
        
        assert fst is not None
        
        # Questi due assegnamenti stravolgono un po' il significato del nome della variabile
        # ma fattà così si risolve in fretta. E riduce velocemente l'assegnamento
        if self.minY and self.maxY:
            fst = max(fst, self.minY)
            img2y = min(img2y, self.maxY)
        
        if algorithm == "n":
            r1, r2 = fst, img2y
        elif algorithm == "n/2":
            r1, r2 = maxima(f, fst, img2y, True)
        elif algorithm == "n/4":
            r1, r2 = maxima(f, fst, img2y, True)
            r1, r2 = maxima(f, r1, r2, True)
        elif algorithm == "logN":
            r1, _ = maxima(f, fst, img2y)
            r2 = r1
        else:
            raise BaseException("No algorithm provided")

        for y in range(r1, r2 + 1):
            score, crop, resize = self.__resizeScore(img1, img2, y)
            if not best_resize or score > best_match:
                if debug:
                    puts(colored.green(f"{y}: {score} > {best_match}"))
                    
                best_match = score
                best_resize = resize
                best_crop = crop
                best_y = y
                
                if debug:
                    print(resize)
                    print(crop)
            else:
                if debug:
                    puts(colored.red(f"{y}: {score} <= {best_match}"))
        
        if debug:
            print(best_match)
            print(best_resize)
            print(best_crop)
        
        if compare.above_threshold(best_match):
            self.goodCrops.append(best_y)
            
            if len(self.goodCrops) >= self.k: # TODO: Il >= mi taglia le gambe o si migliora sempre?
                self.minY, self.maxY = confidenceInterval(self.goodCrops, 0.001)
                self.minY = int(self.minY)
                self.maxY = int(self.maxY) + 1
        
        return (best_resize, best_crop)



class Effects:
    def __init__(self, base, target):
        self.resize, self.crop = cropfinder.getBest(base, target, "logN")
        
        # TODO: Togliere 3 commenti una volta sistemato todo (ripristinando il codice)
        #i2 = self.resize.do(image2)
        #i2 = self.crop.do(i2)

        #self.blur = FindBlur(image1, i2).getBest()

    def do(self, img):
        for e in [self.resize, self.crop]: #, self.blur]:
            img = e.do(img)

        return img



compare = IA_pic_sim(81)
cropfinder = FindCrop() # Necessario: Integra un alg. avanzato per velocizzare la ricerca dei nuovi crop