import os
import sys
import random
from copy import deepcopy
import jsonpickle              #To parse JSON type File.
import numpy                   #To calculate Difference between Generated and Reference Image (Fitness Calculation)
from PIL import Image, ImageDraw          #For Opening and Working on the Image
import multiprocessing         #To make use of all Cores available inorder to speed up Processing of Code.



try:
    Opened_Image = Image.open("reference1.png")      
except IOError:
    print "Please Save A Reference Image In The Project Directory"
    exit()


class Position_of_circle:
    
    def __init__(self,x,y):
        self.x = x
        self.y = y

class Color_of_circle:
    
    def __init__(self,r,g,b):
        self.r = r
        self.g = g
        self.b = b

class Individual:
    
    def __init__(self,Boundary):

        self.Boundary = Boundary
        self.diameter = random.randint(1,10)
        self.position = Position_of_circle(random.randint(0,Boundary[0]),random.randint(0,Boundary[1]))
        self.color = Color_of_circle(random.randint(0,255),random.randint(0,255),random.randint(0,255))
        self.parameters = ["diameter","position","color"]

    def mutate(self):        

        Type = random.choice(self.parameters)
        if Type == "diameter":
            self.diameter = max(1,self.diameter)

        elif Type == "position":
            X = max(0,self.position.x)
            Y = max(0,self.position.y)
            self.position = Position_of_circle(min(X,self.Boundary[0]),min(Y,self.Boundary[1]))

        elif Type == "color":
            R = min(max(0,self.color.r),255)
            G = min(max(0,self.color.g),255)
            B = min(max(0,self.color.b),255)
            self.color = Color_of_circle(R,G,B)

    def Make_Recovery(self):
        
        so = {}
        so["Boundary"] = self.Boundary
        so["diameter"] = self.diameter
        so["position"] = (self.position.x,self.position.y)
        so["color"] = (self.color.r,self.color.g,self.color.b)
        return so

    def Use_Recovery(self,so):
       
        self.Boundary = so["Boundary"]
        self.diameter = so["diameter"]
        self.position = Position_of_circle(so["position"][0],so["position"][1])
        self.color = Color_of_circle(so["color"][0],so["color"][1],so["color"][2])

class Organism:
   
    def __init__(self,Boundary,num):
        self.Boundary = Boundary

        self.genes = [Individual(Boundary) for _ in xrange (num)]        


    def mutate(self):
        if len(self.genes) < 200:
            for g in self.genes:
                if 0.1 < random.random():      # The Probability of Mutation is kept 0.1
                    g.mutate()

        else:
            for g in random.sample(self.genes,int(len(self.genes)*0.1)):
                g.mutate()

        if 0.3 < random.random():          #The Probability of Addition of Individual is Kept 0.3
            self.genes.append(Individual(self.Boundary))
        if len(self.genes) > 0 and 0.2 < random.random():        #The Probability of Removal of Individual is Kept 0.2
            self.genes.remove(random.choice(self.genes))

    def drawImage(self):
        
        image = Image.new("RGB",self.Boundary,(255,255,255))
        canvas = ImageDraw.Draw(image)

        for g in self.genes:
            color = (g.color.r,g.color.g,g.color.b)
            canvas.ellipse([g.position.x-g.diameter,g.position.y-g.diameter,g.position.x+g.diameter,g.position.y+g.diameter],outline=color,fill=color)

        return image

    def Make_Recovery(self,generation):
        
        so = [generation]
        return so + [g.Make_Recovery() for g in self.genes]

    def Use_Recovery(self,so):
        
        self.genes = []
        gen = so[0]
        so = so[1:]
        for g in so:
            newGene = Individual(self.Boundary)
            newGene.Use_Recovery(g)
            self.genes.append(newGene)
        return gen

def fitness(im1,im2):
    
    i1 = numpy.array(im1,numpy.int16)
    i2 = numpy.array(im2,numpy.int16)
    dif = numpy.sum(numpy.abs(i1-(i2[...,0:3])))
    return (dif / 255.0 * 100) / i1.size

def run(cores,so=None):
    
    if not os.path.exists("results"):
        os.mkdir("results")

    f = file(os.path.join("results","log.txt"),'a')

    Image_Operated_On = Opened_Image

    generation = 1
    parent = Organism(Image_Operated_On.size,50)       #The Number of Genes present in the population is 50.

    if so != None:
        gen = parent.Use_Recovery(jsonpickle.decode(so))
        generation = int(gen)
    prevScore = 101
    score = fitness(parent.drawImage(),Image_Operated_On)
    p = multiprocessing.Pool(cores)
    while True:
        print "Generation {} - {}".format(generation,score)
        f.write("Generation {} - {}\n".format(generation,score))

        if (generation) % 100 == 0:                  #The Frequency of image generation is 1 image per 100 generations.
            parent.drawImage().save(os.path.join("results","{}.png".format(generation)))
        generation += 1
        prevScore = score
        children = []
        scores = []
        children.append(parent)
        scores.append(score)

        try:
            results = groupMutate(parent,50 - 1,p)            #Population Boundary is kept 50     
        except KeyboardInterrupt:
            print 'Bye!'
            p.close()
            return
        
        newScores,newChildren = zip(*results)
        children.extend(newChildren)
        scores.extend(newScores)
        winners = sorted(zip(children,scores),key=lambda x: x[1])
        parent,score = winners[0]

        if generation % 100 == 0:
            sf = file(os.path.join("results","{}.txt".format(generation)),'w')
            sf.write(jsonpickle.encode(parent.Make_Recovery(generation)))
            sf.close()

def mutateAndTest(o):
    
    try:
        c = deepcopy(o)
        c.mutate()
        i1 = c.drawImage()
        i2 = Opened_Image
        return (fitness(i1,i2),c)
    except KeyboardInterrupt, e:
        pass

def groupMutate(o,number,p):
    
    results = p.map(mutateAndTest,[o]*int(number))
    return results
        

if __name__ == "__main__":
    cores = max(1,multiprocessing.cpu_count()-1)
    so = None

    if len(sys.argv) > 1:
        args = sys.argv[1:]

        for i,a in enumerate(args):
            if a == "-t":
                cores = int(args[i+1])
            elif a == "-s":
                with open(args[i+1],'r') as save:
                    so = save.read()

    run(cores,so)
