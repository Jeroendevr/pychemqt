#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''Pychemqt, Chemical Engineering Process simulator
Copyright (C) 2009-2017, Juan José Gómez Romera <jjgomera@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.'''


###############################################################################
# Module to implement new component
#   -newComponent: Main dialog class with common functionality
#   -UI_Contribution: Definition for group contribution
#   -Definicion_Petro: Definition of crude and oil fraction
###############################################################################

import os
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
from scipy import arange


from lib.config import IMAGE_PATH, Preferences
from lib.crude import Crudo
from lib.compuestos import (Joback, Constantinou_Gani, Wilson_Jasperson,
                            Marrero_Pardillo, Elliott, Ambrose)
from lib import sql
from lib.plot import Plot
from lib.petro import Petroleo, curve_Predicted, _Tb_Predicted
from lib.unidades import Temperature, Pressure, Diffusivity
from UI import prefPetro
from UI.delegate import SpinEditor
from UI.inputTable import InputTableWidget
from UI.viewComponents import View_Component, View_Petro, View_Contribution
from UI.widgets import Entrada_con_unidades, Status


class newComponent(QtWidgets.QDialog):
    """Main dialog class with common functionality"""

    def loadUI(self):
        """Define common widget for chid class"""
        layoutBottom = QtWidgets.QHBoxLayout()
        self.status = Status()
        layoutBottom.addWidget(self.status)
        self.buttonShowDetails = QtWidgets.QPushButton(
            QtWidgets.QApplication.translate("pychemqt", "Show Details"))
        self.buttonShowDetails.clicked.connect(self.showDetails)
        self.buttonShowDetails.setEnabled(False)
        layoutBottom.addWidget(self.buttonShowDetails)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel |
                                                QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setEnabled(False)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.reject)
        layoutBottom.addWidget(self.buttonBox)
        # self.layout().addLayout(layoutBottom, 30, 0, 1, 6)
        self.layout().addLayout(layoutBottom)

    def save(self):
        """Save new componente in user database"""
        elemento = self.unknown.export2Component()
        sql.inserElementsFromArray(sql.databank_Custom_name, [elemento])
        Dialog = View_Component(1001+sql.N_comp_Custom)
        Dialog.show()
        QtWidgets.QDialog.accept(self)

    def changeParams(self, parametro, valor):
        self.calculo(**{parametro: valor})

    def calculo(self, **kwargs):
        self.status.setState(4)
        self.unknown(**kwargs)
        self.status.setState(self.unknown.status, self.unknown.msg)
        self.buttonShowDetails.setEnabled(self.unknown.status)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setEnabled(
            self.unknown.status)

    def showDetails(self):
        """Show details of new component"""
        dialog = self.ViewDetails(self.unknown)
        dialog.exec_()


class Ui_Contribution(newComponent):
    """Dialog to define hypotethical new component with several group
    contribucion methods"""
    ViewDetails = View_Contribution

    def __init__(self, metodo, parent=None):
        """Metodo: name of group contribution method:
            Joback
            Constantinou-Gani
            Wilson-Jasperson
            Marrero-Pardillo
            Elliott
            Ambrose
        """
        super(Ui_Contribution, self).__init__(parent)
        self.setWindowTitle(QtWidgets.QApplication.translate(
            "pychemqt", "Select the component group for method") +" "+ metodo)

        self.grupo = []
        self.indices = []
        self.contribucion = []
        self.metodo = metodo
        layout = QtWidgets.QGridLayout(self)
        self.Grupos = QtWidgets.QTableWidget()
        self.Grupos.verticalHeader().hide()
        self.Grupos.setRowCount(0)
        self.Grupos.setColumnCount(2)
        self.Grupos.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("Nk"))
        self.Grupos.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem(
            QtWidgets.QApplication.translate("pychemqt", "Group")))
        self.Grupos.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.Grupos.setSortingEnabled(True)
        self.Grupos.horizontalHeader().setStretchLastSection(True)
        self.Grupos.setColumnWidth(0, 50)
        self.Grupos.setItemDelegateForColumn(0, SpinEditor(self))
        self.Grupos.cellChanged.connect(self.cellChanged)
        self.Grupos.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        layout.addWidget(self.Grupos, 0, 0, 3, 3)

        self.Formula = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(12)
        self.Formula.setFont(font)
        self.Formula.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.Formula.setFixedHeight(50)
        layout.addWidget(self.Formula, 0, 3)
        self.botonBorrar = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
            os.environ["pychemqt"]+"/images/button/editDelete.png")),
            QtWidgets.QApplication.translate("pychemqt", "Delete"))
        self.botonBorrar.clicked.connect(self.borrar)
        layout.addWidget(self.botonBorrar, 1, 3)
        self.botonClear = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
            os.environ["pychemqt"]+"/images/button/clear.png")),
            QtWidgets.QApplication.translate("pychemqt", "Clear"))
        self.botonClear.clicked.connect(self.clear)
        layout.addWidget(self.botonClear, 2, 3)

        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self.line, 3, 0, 1, 4)

        self.TablaContribuciones = QtWidgets.QListWidget()
        self.TablaContribuciones.currentItemChanged.connect(self.selectedChanged)
        self.TablaContribuciones.itemDoubleClicked.connect(self.add)
        layout.addWidget(self.TablaContribuciones, 4, 0, 7, 3)
        self.botonAdd = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
            os.environ["pychemqt"]+"/images/button/add.png")),
            QtWidgets.QApplication.translate("pychemqt", "Add"))
        self.botonAdd.setDisabled(True)
        self.botonAdd.clicked.connect(self.add)
        layout.addWidget(self.botonAdd, 4, 3)
        layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Expanding), 5, 1, 1, 1)

        # Show widget for specific method
        if metodo in ["Constantinou", "Wilson"]:
            self.Order1 = QtWidgets.QRadioButton(
                QtWidgets.QApplication.translate("pychemqt", "1st order"))
            self.Order1.setChecked(True)
            self.Order1.toggled.connect(self.Order)
            layout.addWidget(self.Order1, 6, 3)
            self.Order2 = QtWidgets.QRadioButton(
                QtWidgets.QApplication.translate("pychemqt", "2nd order"))
            layout.addWidget(self.Order2, 7, 3)

        if metodo == "Wilson":
            layout.addWidget(QtWidgets.QLabel(
                QtWidgets.QApplication.translate("pychemqt", "Rings")), 8, 3)
            self.anillos = QtWidgets.QSpinBox()
            self.anillos.valueChanged.connect(partial(self.changeParams, "ring"))
            layout.addWidget(self.anillos, 9, 3)

        if metodo == "Marrero":
            layout.addWidget(QtWidgets.QLabel(
                QtWidgets.QApplication.translate("pychemqt", "Atoms")), 8, 3)
            self.Atomos = QtWidgets.QSpinBox()
            self.Atomos.valueChanged.connect(partial(self.changeParams, "atomos"))
            layout.addWidget(self.Atomos, 9, 3)

        if metodo == "Ambrose":
            layout.addWidget(QtWidgets.QLabel(
                QtWidgets.QApplication.translate("pychemqt", "Platt number")), 8, 3)
            self.Platt = QtWidgets.QSpinBox()
            self.Platt.setToolTip(QtWidgets.QApplication.translate(
                "pychemqt", "The Platt number is the number of pairs of carbon \
                atoms which are separated \nby three carbon-carbon bonds and \
                is an indicator of the degree of branching in the molecule.\n\
                The Platt number of an n-alkane is equal to the number of \
                carbons minus three"))
            self.Platt.valueChanged.connect(partial(self.changeParams, "platt"))
            layout.addWidget(self.Platt, 9, 3)

        layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Expanding), 10, 1, 1, 1)
        layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Expanding), 11, 0, 1, 4)
        layout.addWidget(QtWidgets.QLabel(
            QtWidgets.QApplication.translate("pychemqt", "Name")), 12, 0)
        self.nombre = QtWidgets.QLineEdit()
        self.nombre.textChanged.connect(partial(self.changeParams, "name"))
        layout.addWidget(self.nombre, 12, 1, 1, 3)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Molecular Weight")), 13, 0)
        self.M = Entrada_con_unidades(float, textounidad="g/mol")
        self.M.valueChanged.connect(partial(self.changeParams, "M"))
        layout.addWidget(self.M, 13, 1)
        layout.addWidget(QtWidgets.QLabel(
            QtWidgets.QApplication.translate("pychemqt", "Boiling point")), 14, 0)
        self.Tb = Entrada_con_unidades(Temperature)
        self.Tb.valueChanged.connect(partial(self.changeParams, "Tb"))
        layout.addWidget(self.Tb, 14, 1)
        layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Specific Gravity")), 15, 0)
        self.SG = Entrada_con_unidades(float)
        self.SG.valueChanged.connect(partial(self.changeParams, "SG"))
        layout.addWidget(self.SG, 15, 1)

        newComponent.loadUI(self)

        func = {"Constantinou": Constantinou_Gani,
                "Wilson": Wilson_Jasperson,
                "Joback": Joback,
                "Ambrose": Ambrose,
                "Elliott": Elliott,
                "Marrero": Marrero_Pardillo}
        self.unknown = func[self.metodo]()

        for i, nombre in enumerate(self.unknown.coeff["txt"]):
            self.TablaContribuciones.addItem(nombre[0])

        if metodo in ["Constantinou", "Wilson"]:
            self.Order()

    def Order(self):
        """Show/Hide group of undesired order"""
        for i in range(self.unknown.FirstOrder):
            self.TablaContribuciones.item(i).setHidden(self.Order2.isChecked())
        for i in range(self.unknown.FirstOrder, self.unknown.SecondOrder):
            self.TablaContribuciones.item(i).setHidden(self.Order1.isChecked())

    def borrar(self, indice=None):
        """Remove some group contribution from list"""
        if not indice:
            indice = self.Grupos.currentRow()
        if indice != -1:
            self.Grupos.removeRow(indice)
            del self.grupo[indice]
            del self.indices[indice]
            del self.contribucion[indice]
            self.calculo(**{"group": self.indices,
                            "contribution": self.contribucion})

    def clear(self):
        """Clear widgets from dialog"""
        self.Grupos.clearContents()
        self.Grupos.setRowCount(0)
        self.grupo = []
        self.indices = []
        self.contribucion = []
        self.Formula.clear()
        self.M.clear()
        self.nombre.clear()
        self.Tb.clear()
        self.SG.clear()
        self.unknown.clear()
        self.status.setState(self.unknown.status, self.unknown.msg)

    def cellChanged(self, i, j):
        if j == 0:
            valor = int(self.Grupos.item(i, j).text())
            if valor <= 0:
                self.borrar(i)
            else:
                self.contribucion[i] = int(valor)
        self.calculo(**{"group": self.indices, "contribution": self.contribucion})

    def selectedChanged(self, i):
        self.botonAdd.setEnabled(i != -1)

    def add(self):
        indice = self.Grupos.rowCount()
        grupo = self.TablaContribuciones.currentItem().text()
        if grupo not in self.grupo:
            self.grupo.append(grupo)
            self.indices.append(self.TablaContribuciones.currentRow())
            self.contribucion.append(1)
            self.Grupos.setRowCount(indice+1)
            self.Grupos.setItem(indice, 0, QtWidgets.QTableWidgetItem("1"))
            self.Grupos.item(indice, 0).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.Grupos.setItem(indice, 1, QtWidgets.QTableWidgetItem(grupo))
            self.Grupos.item(indice, 1).setFlags(
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.Grupos.setRowHeight(indice, 20)
        else:
            indice = self.grupo.index(grupo)
            self.contribucion[indice] += 1
            self.Grupos.item(indice, 0).setText(str(int(
                self.Grupos.item(indice, 0).text())+1))
        self.calculo(**{"group": self.indices, "contribution": self.contribucion})

    def calculo(self, **kwargs):
        """Calculate function"""
        newComponent.calculo(self, **kwargs)
        if self.unknown.status:
            self.Formula.setText(self.unknown.formula)


class Definicion_Petro(newComponent):
    """Dialog for define hypothetical crude and oil fraction"""
    ViewDetails = View_Petro

    def __init__(self, parent=None):
        super(Definicion_Petro, self).__init__(parent)
        self.setWindowTitle(QtWidgets.QApplication.translate(
            "pychemqt", "Petrol component definition"))

        layout = QtWidgets.QVBoxLayout(self)
        self.toolBox = QtWidgets.QTabWidget()
        self.toolBox.setTabPosition(QtWidgets.QTabWidget.South)
        layout.addWidget(self.toolBox)

        # Distillation data definition
        distilationPage = QtWidgets.QWidget()
        self.toolBox.addTab(
            distilationPage,
            QtWidgets.QApplication.translate("pychemqt", "Distillation data"))
        lyt = QtWidgets.QGridLayout(distilationPage)

        # Widget with curve functionality
        curveWidget = QtWidgets.QWidget()
        lytcurve = QtWidgets.QGridLayout(curveWidget)
        lytcurve.addWidget(QtWidgets.QLabel("Curve type"), 1, 1)
        self.tipoCurva = QtWidgets.QComboBox()
        for method in Petroleo.CURVE_TYPE:
            self.tipoCurva.addItem(method)
        self.tipoCurva.currentIndexChanged.connect(self.curveIndexChanged)
        lytcurve.addWidget(self.tipoCurva, 1, 2)
        self.curvaDestilacion = InputTableWidget(2)
        self.curvaDestilacion.tabla.horizontalHeader().show()
        self.curvaDestilacion.tabla.rowFinished.connect(self.checkStatusCurve)
        lytcurve.addWidget(self.curvaDestilacion, 2, 1, 3, 3)
        self.regresionButton = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
            os.environ["pychemqt"]+"/images/button/Regression.gif")),
            QtWidgets.QApplication.translate("pychemqt", "Regression"))
        self.regresionButton.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Calculate missing required values from a curve fit"))
        self.regresionButton.clicked.connect(self.regresionCurve)
        lytcurve.addWidget(self.regresionButton, 2, 3)
        self.finishButton = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
            os.environ["pychemqt"]+"/images/button/arrow-right.png")),
            QtWidgets.QApplication.translate("pychemqt", "Finish"))
        self.finishButton.clicked.connect(self.finishCurva)
        lytcurve.addWidget(self.finishButton, 5, 3)
        lytcurve.addWidget(QtWidgets.QLabel(
            QtWidgets.QApplication.translate("pychemqt", "Pressure")), 5, 1)
        self.presion = Entrada_con_unidades(Pressure, value=101325.)
        self.presion.valueChanged.connect(partial(self.changeParams, "P_curve"))
        lytcurve.addWidget(self.presion, 5, 2)
        lytcurve.addItem(QtWidgets.QSpacerItem(
            20, 20, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding), 6, 4)

        # Widget with crude functionality
        crudeWidget = QtWidgets.QWidget()
        lytcrude = QtWidgets.QGridLayout(crudeWidget)
        self.crudo = QtWidgets.QComboBox()
        self.crudo.addItem("")
        query = "SELECT name, location, API, sulfur FROM CrudeOil"
        sql.databank.execute(query)
        for name, location, API, sulfur in sql.databank:
            self.crudo.addItem("%s (%s)  API: %s %s: %s" % (
                name, location, API, "%S", sulfur))
        self.crudo.currentIndexChanged.connect(partial(
            self.changeParams, "index"))
        lytcrude.addWidget(self.crudo, 1, 1, 1, 2)
        lytcrude.addWidget(QtWidgets.QLabel("Pseudo C+"), 2, 1)
        self.Cplus = Entrada_con_unidades(int, width=50)
        self.Cplus.valueChanged.connect(partial(self.changeParams, "Cplus"))
        lytcrude.addWidget(self.Cplus, 2, 2)

        self.checkCurva = QtWidgets.QRadioButton(
            QtWidgets.QApplication.translate(
                "pychemqt", "Define destillation curve"))
        self.checkCurva.toggled.connect(curveWidget.setEnabled)
        curveWidget.setEnabled(False)
        lyt.addWidget(self.checkCurva, 1, 1, 1, 2)
        lyt.addWidget(curveWidget, 2, 1, 1, 2)
        lyt.addItem(QtWidgets.QSpacerItem(
            20, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed),
            3, 1)
        self.checkCrudo = QtWidgets.QRadioButton(
            QtWidgets.QApplication.translate(
                "pychemqt", "Use petrol fraction from list"))
        self.checkCrudo.toggled.connect(self.changeUnknown)
        self.checkCrudo.toggled.connect(crudeWidget.setEnabled)
        crudeWidget.setEnabled(False)
        lyt.addWidget(self.checkCrudo, 4, 1, 1, 2)
        lyt.addWidget(crudeWidget, 5, 1, 1, 2)
        lyt.addItem(QtWidgets.QSpacerItem(
            20, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed),
            6, 1, 1, 2)
        self.checkBlend = QtWidgets.QCheckBox(QtWidgets.QApplication.translate(
            "pychemqt", "Blend if its necessary"))
        lyt.addWidget(self.checkBlend, 7, 1, 1, 2)
        self.cutButton = QtWidgets.QPushButton(
            QtWidgets.QApplication.translate("pychemqt", "Define cut ranges"))
        self.cutButton.setEnabled(False)
        self.cutButton.clicked.connect(self.showCutRange)
        lyt.addWidget(self.cutButton, 7, 2)
        self.checkBlend.toggled.connect(self.cutButton.setEnabled)
        lyt.addItem(QtWidgets.QSpacerItem(
            5, 5, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding), 8, 1)

        # Definition with bulk properties
        definitionPage = QtWidgets.QWidget()
        self.toolBox.addTab(
            definitionPage,
            QtWidgets.QApplication.translate("pychemqt", "Bulk Definition"))

        lyt = QtWidgets.QGridLayout(definitionPage)
        txt = QtWidgets.QLabel("Tb")
        txt.setToolTip(
            QtWidgets.QApplication.translate("pychemqt", "Boiling point"))
        lyt.addWidget(txt, 1, 1)
        self.Tb = Entrada_con_unidades(Temperature)
        self.Tb.valueChanged.connect(partial(self.changeParams, "Tb"))
        lyt.addWidget(self.Tb, 1, 2)
        txt = QtWidgets.QLabel("M")
        txt.setToolTip(
            QtWidgets.QApplication.translate("pychemqt", "Molecular weight"))
        lyt.addWidget(txt, 2, 1)
        self.M = Entrada_con_unidades(float, textounidad="g/mol")
        self.M.valueChanged.connect(partial(self.changeParams, "M"))
        lyt.addWidget(self.M, 2, 2)
        txt = QtWidgets.QLabel("SG")
        txt.setToolTip(
            QtWidgets.QApplication.translate("pychemqt", "Specific Gravity"))
        lyt.addWidget(txt, 3, 1)
        self.SG = Entrada_con_unidades(float)
        self.SG.valueChanged.connect(partial(self.changeParams, "SG"))
        lyt.addWidget(self.SG, 3, 2)
        txt = QtWidgets.QLabel("API")
        txt.setToolTip(
            QtWidgets.QApplication.translate("pychemqt", "API Gravity"))
        lyt.addWidget(txt, 4, 1)
        self.API = Entrada_con_unidades(float)
        self.API.valueChanged.connect(partial(self.changeParams, "API"))
        lyt.addWidget(self.API, 4, 2)
        txt = QtWidgets.QLabel("Kw")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Watson characterization factor"))
        lyt.addWidget(txt, 5, 1)
        self.Kw = Entrada_con_unidades(float)
        self.Kw.valueChanged.connect(partial(self.changeParams, "Kw"))
        lyt.addWidget(self.Kw, 5, 2)
        lyt.addWidget(QtWidgets.QLabel("C/H"), 6, 1)
        self.CH = Entrada_con_unidades(float)
        self.CH.valueChanged.connect(partial(self.changeParams, "CH"))
        lyt.addWidget(self.CH, 6, 2)
        txt = QtWidgets.QLabel("ν<sub>100F</sub>")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Kinematic viscosity at 100ºF"))
        lyt.addWidget(txt, 7, 1)
        self.v100 = Entrada_con_unidades(Diffusivity)
        self.v100.valueChanged.connect(partial(self.changeParams, "v100"))
        lyt.addWidget(self.v100, 7, 2)
        txt = QtWidgets.QLabel("ν<sub>210F</sub>")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Kinematic viscosity at 210ºF"))
        lyt.addWidget(txt, 8, 1)
        self.v210 = Entrada_con_unidades(Diffusivity)
        self.v210.valueChanged.connect(partial(self.changeParams, "v210"))
        lyt.addWidget(self.v210, 8, 2)
        txt = QtWidgets.QLabel("n")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Refractive index"))
        lyt.addWidget(txt, 9, 1)
        self.n = Entrada_con_unidades(float)
        self.n.valueChanged.connect(partial(self.changeParams, "n"))
        lyt.addWidget(self.n, 9, 2)
        txt = QtWidgets.QLabel("I")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Huang Parameter"))
        lyt.addWidget(txt, 10, 1)
        self.I = Entrada_con_unidades(float)
        self.I.valueChanged.connect(partial(self.changeParams, "I"))
        lyt.addWidget(self.I, 10, 2)
        lyt.addWidget(QtWidgets.QLabel("%S"), 11, 1)
        self.S = Entrada_con_unidades(float, spinbox=True, step=1.0, max=100)
        self.S.valueChanged.connect(partial(self.changeParams, "S"))
        lyt.addWidget(self.S, 11, 2)
        lyt.addWidget(QtWidgets.QLabel("%H"), 12, 1)
        self.H = Entrada_con_unidades(float, spinbox=True, step=1.0, max=100)
        self.H.valueChanged.connect(partial(self.changeParams, "H"))
        lyt.addWidget(self.H, 12, 2)
        lyt.addWidget(QtWidgets.QLabel("%N"), 13, 1)
        self.N = Entrada_con_unidades(float, spinbox=True, step=1.0, max=100)
        self.N.valueChanged.connect(partial(self.changeParams, "N"))
        lyt.addWidget(self.N, 13, 2)

        lyt.addItem(QtWidgets.QSpacerItem(
            10, 10, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed),
            14, 1, 1, 2)
        lyt.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate(
            "pychemqt", "Alternate definition, poor accuracy")), 15, 1, 1, 2)
        txt = QtWidgets.QLabel("Nc")
        txt.setToolTip(QtWidgets.QApplication.translate(
            "pychemqt", "Carbon number"))
        lyt.addWidget(txt, 16, 1)
        self.Nc = Entrada_con_unidades(int, width=50)
        self.Nc.valueChanged.connect(partial(self.changeParams, "Nc"))
        lyt.addWidget(self.Nc, 16, 2)

        # Configuration
        configPage = prefPetro.Widget(Preferences)
        self.toolBox.addTab(
            configPage,
            QtGui.QIcon(IMAGE_PATH + "button/configure.png"),
            QtWidgets.QApplication.translate("pychemqt", "Configuration"))

        # Initialization section
        newComponent.loadUI(self)
        self.curveParameters = None  # Fitting parameter for distillation curve

        self.Petroleo = Petroleo()
        self.Crudo = Crudo()
        self.curveIndexChanged(0)
        self.checkStatusCurve()

    @property
    def unknown(self):
        if self.checkCrudo.isChecked():
            return self.Crudo
        else:
            return self.Petroleo

    def changeUnknown(self):
        self.status.setState(self.unknown.status, self.unknown.msg)
        self.buttonShowDetails.setEnabled(self.unknown.status)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Save).setEnabled(
            self.unknown.status)

    # Curve distillation definition
    def curveIndexChanged(self, index):
        """Show the composition unit appropiated to the new curve selected"""
        if index == 3:
            header = ["wt.%", "Tb, " + Temperature.text()]
        else:
            header = ["Vol.%", "Tb, " + Temperature.text()]
        self.curvaDestilacion.tabla.setHorizontalHeaderLabels(header)

    def finishCurva(self):
        """End the curve distillation definition and add the data to the
        Petroleo instance"""
        kwargs = {}
        curve = Petroleo.CURVE_TYPE[self.tipoCurva.currentIndex()]
        kwargs["curveType"] = curve
        kwargs["X_curve"] = self.curvaDestilacion.column(0)
        kwargs["T_curve"] = self.curvaDestilacion.column(1)
        kwargs["fit_curve"] = self.curveParameters
        self.calculo(**kwargs)

    def checkStatusCurve(self):
        """Check curren data of curve to check completeness of its definition
        and enable/disable accordly the buttons"""
        X = self.curvaDestilacion.column(0)
        self.regresionButton.setEnabled(len(X) > 3)

        defined = True
        for xi in [0.1, 0.5]:
            defined = defined and xi in X
        regresion = self.curveParameters is not None
        self.finishButton.setEnabled(defined or regresion)

    def regresionCurve(self):
        dlg = Plot(accept=True)
        x = self.curvaDestilacion.column(0)
        T = self.curvaDestilacion.column(1, Temperature)
        dlg.addData(x, T, color="black", ls="None", marker="s", mfc="red")
        parameters, r2 = curve_Predicted(x, T)
        xi = arange(0, 1, 0.01)
        Ti = [_Tb_Predicted(parameters, x_i) for x_i in xi]
        dlg.addData(xi, Ti, color="black", lw=0.5)

        # Add equation formula to plot
        txt = r"$\frac{T-T_{o}}{T_{o}}=\left[\frac{A}{B}\ln\left(\frac{1}{1-x}"
        txt += r"\right)\right]^{1/B}$"
        To = Temperature(parameters[0])
        txt2 = "\n\n\n$T_o=%s$" % To.str
        txt2 += "\n$A=%0.4f$" % parameters[1]
        txt2 += "\n$B=%0.4f$" % parameters[2]
        txt2 += "\n$r^2=%0.6f$" % r2
        dlg.plot.ax.text(0, T[-1], txt, size="14", va="top", ha="left")
        dlg.plot.ax.text(0, T[-1], txt2, size="10", va="top", ha="left")
        if dlg.exec_():
            self.curveParameters = parameters
            self.checkStatusCurve()

    def showCutRange(self):
        pass


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = Definicion_Petro()
    # Dialog = Ui_Contribution("Ambrose")
    Dialog.show()
    sys.exit(app.exec_())
