import numpy as np
import matplotlib.pyplot as plt
from saem import CSEMData
import pygimli as pg
# from pygimli.viewer.mpl import drawModel1D




# %% import transmitter (better by kmlread)
txpos = np.array([[559497.46, 5784467.953],
                  [559026.532, 5784301.022]]).T
self = CSEMData(datafile="data_f*.mat", txPos=txpos, txalt=70)
self.DATAX *= -1  # why?
self.showField(self.line)
self.filter(fmin=100, fmax=20000)
self.filter(f=12000)
self.filter(f=7000)
# self.filter(f=5000)
# self.filter(f=900)
print(self.f)
print(self)
# self.showData(nf=1)
# self.generateDataPDF()
# self.showField("alt", background="BKG")
# %%
self.setPos(320, show=True)  # middle
# self.setPos(333, show=True)  # close to transmitter
# self.setPos(310, show=True)
self.cmp = [1, 1, 1]
self.showSounding(amphi=False)
# %%
# self.depth = np.hstack((0, np.cumsum(10**np.linspace(0.8, 2, 15))))
print(self.depth)
# %%
self.cmp[0] = 0  # no x (Tx)
self.cmp[1] = 1
self.invertSounding(absError=0.002, relError=0.02, lam=10)
# %%
dgfdgd
# %%
line = 10
self.invertLine(line=line)
ax=self.showSection(cMin=3, cMax=200)
ax.figure.savefig(f"line{line}-result.pdf", bbox_inches="tight")
# %%
# ax = self.showSounding(response=resp)
# plotSymbols(self.rx, self.ry, -self.alt, numpoints=0)
# self.showSounding(nrx=20)
self.showField(range(len(self.rx)))
# %%
self.invertSounding(maxIter=1, lam=100000)
from pygimli.utils import modCovar
# %%
var, MCMs = modCovar(self.inv1d.inv)
# %%
pc = plt.matshow(MCMs, cmap="bwr")
pc.set_clim(-1, 1)
