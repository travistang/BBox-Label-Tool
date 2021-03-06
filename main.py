#------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
#-------------------------------------------------------------------------------
from __future__ import division
from Tkinter import *
import tkMessageBox
from PIL import Image, ImageTk
import os
import glob
import random
import numpy as np
from re import sub as sed

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
HIGHLIGHT = 'purple'
# image sizes for the examples
SIZE = 256, 256

class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None
        self.minBoxFilterSize = StringVar()

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0
        self.STATE['rclick'] = 0 # right click state

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2, sticky = W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Button-3>",self.rMouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("e",self.delBBox)
        self.parent.bind("f",self.filterBBox)

        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 4, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 1, column = 2,  sticky = W+N)
        self.listbox = Listbox(self.frame, selectmode=MULTIPLE,width = 22, height = 12)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 4, column = 2, sticky = W+E+N)
        self.btnFilter = Button(self.frame,text = 'FilterBox', command = self.filterBBox)
        self.btnFilter.grid(row = 5, column = 2, sticky = W+E+N)
        self.lbl2 = Label(self.frame,text = 'min box size:')
        self.lbl2.grid(row = 6, column = 2, sticky = W+N)
        self.filterEntry = Entry(self.frame,width = 5,vcmd=self.validateFilterEntry,textvariable=self.minBoxFilterSize)
        self.filterEntry.grid(row = 7, column = 2, sticky = W + N)
        self.btnExportPatches = Button(self.frame,text = 'ExportBBoxes', command = self.exportPatches)
        self.btnExportPatches.grid(row = 8,column = 2,sticky = W+N)
        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 5, column = 1, columnspan = 2, sticky = W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border = 10)
        self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        self.tmpLabel2.pack(side = TOP, pady = 5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(8, weight = 1)

        # for debugging
##        self.setImage()
##        self.loadDir()

    def loadDir(self, dbg = False):
    	if not dbg:
            s = self.entry.get()
            self.imageDir = s
            # load my default directory:)
            if len(s) == 0:
            	self.imageDir = '/home/travis/Research/Car/images_2_jpg'
            if self.imageDir[-1] == '/': self.imageDir = self.imageDir[0:-1]
            self.parent.focus()
            self.category = 1
	
        # get image list
        print os.path.join(self.imageDir, '*.jpg')
#        self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageList = filter(lambda n:".jpg" in n,os.listdir(self.imageDir))
        self.imageList = map(lambda n: os.path.join(self.imageDir,n),self.imageList)
        if len(self.imageList) == 0:
            print 'No .jpg images found in the specified dir!'
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        
        self.outDir = self.imageDir + '_labels'
        print self.outDir
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        # load example bboxes
        self.egDir = os.path.join(r'./Examples', '%03d' %(self.category))
        if not os.path.exists(self.egDir):
            return
        filelist = glob.glob(os.path.join(self.egDir, '*.JPEG'))
        self.tmp = []
        self.egList = []
        #random.shuffle(filelist)
        for (i, f) in enumerate(filelist):
            if i == 3:
                break
            im = Image.open(f)
            r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
            new_size = int(r * im.size[0]), int(r * im.size[1])
            self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
            self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
            self.egLabels[i].config(image = self.egList[-1], width = SIZE[0], height = SIZE[1])

        self.loadImage()
        print '%d images loaded from %s' %(self.total, s)

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
            	lines = f.readlines()
            	# list of strings with 4 numbers
            	recs = filter(lambda a: len(a.split()) == 4,lines)
            	# list of tuples of int with 4 entries
            	tups = map(lambda l: tuple(map(int,l.split())),recs)
            	bbox_cnt = len(tups)
            	self.bboxList = self.bboxList + tups
            	col_ind = 0
            	for a,b,c,d in tups:
            		tmpId = self.mainPanel.create_rectangle(a,b,c,d,width = 2,outline = COLORS[col_ind % len(COLORS)])
            		self.bboxIdList.append(tmpId)
                    	self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(a,b,c,d))
                    	self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[col_ind % len(COLORS)])
                    	col_ind = col_ind + 1

    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxList))
            for bbox in self.bboxList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print 'Image No. %d saved' %(self.cur)


    # select box under cursor by right-clicking
    def rMouseClick(self,event):
        if self.STATE['rclick'] == 0: # click or start dragging
    	    self.listbox.selection_clear(0,END)
            self.STATE['x'] = event.x
            self.STATE['y'] = event.y

            box = self.getBoundingBox(event.x,event.y)
            if box:
                    a,b,c,d = box
                    lbl = '(%d, %d) -> (%d, %d)' % (a,b,c,d)
                    for i,l in enumerate(self.listbox.get(0,END)):
                            if l == lbl:
                                    self.listbox.selection_set(i)
	else: # done dargging
            self.STATE['x'] = self.STATE['y'] = 0
    	self.STATE['rclick'] = 1 - self.STATE['rclick'] # toggle rclick flag
    				
    # helper function to help getting bounding box given coordinates
    def getBoundingBox(self,x,y):
    	if self.bboxList is None: return None
    	bbox = filter(lambda (x1,y1,x2,y2): x in range(x1,x2 + 1) and y in range(y1,y2 + 1),self.bboxList)
    	return bbox[0] if len(bbox) > 0 else None
    
    # select all bbox less than or equal to the given size
    def filterBBox(self,event = None):
    	# TODO: add a field to adjust filter size
    	size = int(self.minBoxFilterSize.get())
    	boxes = filter(lambda (x1,y1,x2,y2): (y2 - y1) * (x2 - x1) <= size,self.bboxList)
    	lbls = map(lambda (a,b,c,d): '(%d, %d) -> (%d, %d)' % (a,b,c,d),boxes)
    	sels = [self.listbox.selection_set(i) for i,l in enumerate(self.listbox.get(0,END)) if l in lbls]
    	
    def mouseClick(self, event):
        self.STATE['rclick'] = 0 # elimiate right click
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(x1, y1, x2, y2))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxList) % len(COLORS)])
        elif 1 == self.STATE['rclick']:
            self.listbox.selection_clear(0,END) # remove all selection and try again
            # create a rectangle
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = HIGHLIGHT)
            # get selection
            boxes = self.getSelection(self.STATE['x'],self.STATE['y'],event.x,event.y)
    	    lbls = map(lambda (a,b,c,d): '(%d, %d) -> (%d, %d)' % (a,b,c,d),boxes)
            
    	    sels = [self.listbox.selection_set(i) for i,l in enumerate(self.listbox.get(0,END)) if l in lbls]
    def getSelection(self,sx,sy,x,y):
            startx,endx = min(sx,x),max(sx,x)
            starty,endy = min(sy,y),max(sy,y)
            res = []
            for (i,j,k,l) in self.bboxList:
                if i in range(startx,endx) and j in range(starty,endy):
                    res.append((i,j,k,l))
            return res
    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self,event = None):
        while len(self.listbox.curselection()) > 0:
            idx = int(self.listbox.curselection()[0])
            self.mainPanel.delete(self.bboxIdList[idx])
            self.bboxIdList.pop(idx)
            self.bboxList.pop(idx)
            self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()
    def validateFilterEntry(self):
    	try:
    		int(self.minBoxFilterSize)
    		return True
    	except:
    		return False
    @staticmethod
    def boxArea(tup):
        a,b,c,d = tup
        return (d - b) * (c - a)
    # export bbox(patches) to given directory (hard-coded here)
    def exportPatches(self):
        path = '/home/travis/patches'
        if not os.path.isdir(path): os.mkdir(path)
        print 'writing to %s' % path
        def extract_patch_coord(fn):
            res = None
            with open(os.path.join(self.outDir,fn),'r') as f:
                res = f.readlines()
            return map(lambda l: map(int,l.split()),filter(lambda l: len(l.split()) == 4,res))
        # collect patches as dictionary
        patches = dict()
        for fn in filter(lambda n: ".txt" == n[-4:],os.listdir(self.outDir)):
            patches[fn] = extract_patch_coord(fn)

        for fn,pats in patches.items():
            # TODO: test this 
            baseName = fn.replace('.txt','')
            inputImName = baseName + '.jpg'
            im = Image.open(os.path.join(self.imageDir,inputImName))
            res = [im.crop(tuple(r)).save("%s-%s.jpg" % (baseName,i)) for (i,r) in enumerate(pats) if self.boxArea(r) > 90]
            print "%d boxes from %s saved" % (len(res),fn)
if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.mainloop()
