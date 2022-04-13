import os.path
from glob import glob
import numpy as np
import matplotlib.pyplot as plt
import pygimli as pg
from saem import Mare2dEMData
from saem import CSEMData


class CSEMSurvey():
    """Class for (multi-patch/transmitter) CSEM data."""

    def __init__(self, arg=None, **kwargs):
        """Initialize class with either data filename or patch instances.


        Parameters
        ----------
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        None.


        """
        self.patches = []
        self.origin = [0, 0, 0]
        self.angle = 0.
        self.basename = "new"
        self.cmp = [1, 1, 1]
        if arg is not None:
            if isinstance(arg, str):
                if arg.endswith(".emdata"):  # obviously a Mare2d File
                    self.importMareData(arg, **kwargs)
                elif arg.endswith(".npz"):
                    self.loadNPZ(arg, **kwargs)

    def __repr__(self):
        st = "CSEMSurvey class with {:d} patches".format(len(self.patches))
        for i, p in enumerate(self.patches):
            st = "\n".join([st, p.__repr__()])

        return st

    def loadNPZ(self, filename, **kwargs):
        """Load numpy-compressed (NPZ) file."""
        ALL = np.load(filename, allow_pickle=True)
        self.f = ALL["freqs"]
        for i in range(len(ALL["DATA"])):
            patch = CSEMData()
            patch.extractData(ALL, i)
            self.addPatch(patch)

    def importMareData(self, mare, flipxy=False, **kwargs):
        """Import Mare2dEM file format."""

        if isinstance(mare, str):
            self.basename = mare.replace(".emdata", "")
            mare = Mare2dEMData(mare, flipxy=flipxy)

        tI = kwargs.setdefault('tI', np.arange(len(mare.txPositions())))
        for i in tI:
            part = mare.getPart(tx=i+1, typ="B", clean=True)
            txl = mare.txpos[i, 3]
            txpos = [[mare.txpos[i, 0], mare.txpos[i, 0]],
                     mare.txpos[i, 1] + np.array([-1/2, 1/2])*txl]
            fak = 1e9
            mats = [part.getDataMatrix(field="Bx") * txl * fak,
                    part.getDataMatrix(field="By") * txl * fak,
                    -part.getDataMatrix(field="Bz") * txl * fak]
            errs = [part.getDataMatrix(field="Bx", column="StdErr"),
                    part.getDataMatrix(field="By", column="StdErr"),
                    part.getDataMatrix(field="Bz", column="StdErr")]
            udt = np.unique(mare.DATA["Type"])
            # make convention: either Real/Imag 1-6,1-6
            if max(udt) < 20:  # real imag
                for i in range(3):
                    errs[i] = errs[i].real*np.abs(mats[i].real) + \
                        errs[i].imag*np.abs(mats[i].imag) * 1j
            else:
                if 31 in udt or 33 in udt or 35 in udt:  # no log
                    for i in range(3):
                        errs[i] = np.abs(errs[i]) * (
                            np.abs(mats[i].real) + np.abs(mats[i].imag) * 1j)
                else:
                    for i in range(3):
                        errs[i] = np.log10(np.abs(errs[i])) * (
                            np.abs(mats[i].real) + np.abs(mats[i].imag) * 1j)

            rx, ry, rz = part.rxpos.T
            cs = CSEMData(f=np.array(mare.f), rx=rx, ry=ry, rz=rz,
                          txPos=txpos)
            cs.cmp = [1, 1, 1]
            cs.basename = "patch{:d}".format(i+1)
            for i, mat in enumerate(mats):
                if mat.shape[0] == 0:
                    cs.cmp[i] = 0
                    mats[i] = np.zeros((len(part.f), part.rxpos.shape[0]))
                    errs[i] = np.zeros_like(mats[i])

            cs.DATA = np.stack(mats)
            cs.ERR = np.stack(errs)
            cs.chooseData()
            self.addPatch(cs)

        if "txs" in kwargs:
            txs = kwargs["txs"]
            for i, p in enumerate(self.patches):
                p.tx, p.ty = txs[tI[i]].T[:2]

    def addPatch(self, patch, name=None):
        """Add a new patch to the file.

        Parameters
        ----------
        patch : CSEMData | str
            CSEMData instance or string to load into that
        """
        if isinstance(patch, str):
            patch = CSEMData(patch)
            if name is not None:
                patch.basename = name

        if len(self.patches) == 0:
            self.angle = patch.angle
            self.origin = patch.origin
        else:
            assert self.angle == patch.angle, "angle not matching"
            assert np.allclose(self.origin, patch.origin), "origin not equal"
            if hasattr(self, 'f'):
                assert len(self.f) == len(patch.f), "frequency number unequal"
                f1 = np.round(self.f, 1)
                f2 = np.round(patch.f, 1)
                assert np.allclose(f1, f2), \
                    "frequencies not equal" + f1.__str__()+" vs. "+f2.__str__()

        self.patches.append(patch)

    def showPositions(self):
        """Show all positions."""
        fig, ax = plt.subplots()
        ma = ["x", "+"]
        for i, p in enumerate(self.patches):
            p.showPos(ax=ax, color="C{:d}".format(i), marker=ma[i % 2])

        return fig, ax

    def showData(self, **kwargs):
        """."""
        for i, p in enumerate(self.patches):
            p.showData(**kwargs)

    def getData(self, line=None, **kwargs):
        """Gather data from individual patches."""
        DATA = []
        lines = np.array([])
        for i, p in enumerate(self.patches):
            data = p.getData(line=line, **kwargs)
            data["tx_ids"] = [i]  # for now fixed, later global list
            DATA.append(data)
            lines = np.concatenate((lines, p.line+(i+1)*100))

        return DATA, lines

    def filter(self, *args, **kwargs):
        """Filter."""
        for p in self.patches:
            p.filter(*args, **kwargs)

    def estimateError(self, *args, **kwargs):
        """estimate error model."""
        for p in self.patches:
            p.estimateError(*args, **kwargs)

    def saveData(self, fname=None, line=None, **kwargs):
        """Save data in numpy format for 2D/3D inversion."""
        cmp = kwargs.setdefault("cmp", self.patches[0].cmp)
        allcmp = ['X', 'Y', 'Z']
        if fname is None:
            fname = self.basename
            if line is not None:
                fname += "-line" + str(line)

            for i in range(3):
                if cmp[i]:
                    fname += "B" + allcmp[i].lower()
        else:
            if fname.startswith("+"):
                fname = self.basename + "-" + fname

        txs = [np.column_stack((p.tx, p.ty, p.ty*0)) for p in self.patches]
        DATA, lines = self.getData(line=line, **kwargs)
        np.savez(fname+".npz",
                 tx=txs,
                 freqs=self.patches[0].f,
                 DATA=DATA,
                 line=lines,
                 cmp=cmp,
                 origin=self.origin,  # global coordinates with altitude
                 rotation=self.angle)

    def loadResponse(self, dirname=None, response=None):
        """Load model response file."""
        if response is None:
            respfiles = sorted(glob(dirname+"response_iter*.npy"))
            if len(respfiles) == 0:
                respfiles = sorted(glob(dirname+"reponse_iter*.npy"))  # TYPO
            if len(respfiles) == 0:
                pg.error("Could not find response file")

            responseVec = np.load(respfiles[-1])
            respR, respI = np.split(responseVec, 2)
            response = respR + respI*1j

        ind = np.hstack((0, np.cumsum([p.nData() for p in self.patches])))
        for i, p in enumerate(self.patches):
            p.loadResponse(response=response[ind[i]:ind[i+1]])

    def loadResults(self, dirname=None, datafile=None, invmesh="Prisms",
                    jacobian=None):
        """Load inversion results from directory."""
        datafile = datafile or self.basename
        if dirname is None:
            dirname = datafile + "_" + invmesh + "/"
        if dirname[-1] != "/":
            dirname += "/"

        if os.path.exists(dirname + "inv_model.npy"):
            self.model = np.load(dirname + "inv_model.npy")
        else:
            self.model = np.load(sorted(glob(dirname+"sig_iter_*.npy"))[0])

        self.chi2s = np.loadtxt(dirname + "chi2.dat", usecols=3)
        self.loadResponse(dirname)
        self.J = None
        if os.path.exists(dirname+"invmesh.vtk"):
            self.mesh = pg.load(dirname+"invmesh.vtk")
        else:
            self.mesh = pg.load(dirname + datafile + "_final_invmodel.vtk")

        jacobian = jacobian or datafile+"_jacobian.bmat"
        jname = dirname + jacobian
        if os.path.exists(jname):
            self.J = pg.load(jname)
            print("Loaded jacobian: "+jname, self.J.rows(), self.J.cols())
        elif os.path.exists(dirname+"jacobian.bmat"):
            self.J = pg.load(dirname+"jacobian.bmat")
            print("Loaded jacobian: ", self.J.rows(), self.J.cols())

    def showResult(self, **kwargs):
        """Show inversion result."""
        kwargs.setdefault("logScale", True)
        kwargs.setdefault("cMap", "Spectral")
        kwargs.setdefault("xlabel", "x (m)")
        kwargs.setdefault("ylabel", "z (m)")
        kwargs.setdefault("label", r"$\rho$ ($\Omega$m)")
        return pg.show(self.mesh, 1./self.model, **kwargs)

    def exportRxTxVTK(self, marker=1):
        """Export Receiver and Transmitter positions as VTK file."""
        rxmesh = pg.Mesh(3)
        for i in range(self.nRx):
            rxmesh.createNode([self.rx[i], self.ry[i], self.rz[i]], marker)

        rxmesh.exportVTK(self.basename+"-rxpos.vtk")
        txmesh = pg.Mesh(3)
        for xx, yy in zip(self.tx, self.ty):
            txmesh.createNode(xx, yy, self.txAlt)

        for i in range(txmesh.nodeCount()-1):
            txmesh.createEdge(txmesh.node(i), txmesh.node(i+1), marker)

        txmesh.exportVTK(self.basename+"-txpos.vtk")


if __name__ == "__main__":
    # %% way 1 - load ready patches
    self = CSEMSurvey()
    self.addPatch("Tx1.npz")
    self.addPatch("Tx2.npz")
    # %% way 2 - patch instances
    # patch1 = CSEMData("flight*.mat")
    # self.addPatch(patch1)
    # %% way 3 - directly from Mare file or npz
    # self = CSEMSurvey("blabla.mare")
    # self = CSEMSurvey("blabla.npz")
    # %%
    print(self)
    self.showPositions()
    p = self.patches[0]
    # p.filter() etc.
    self.saveData()
