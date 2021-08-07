# Anki Simulator Add-on for Anki
#
# Copyright (C) 2020  GiovanniHenriksen https://github.com/giovannihenriksen
# Copyright (C) 2020  Aristotelis P. https://glutanimate.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see https://www.gnu.org/licenses/.

import gc
import time
import math

from typing import TYPE_CHECKING, Dict, List, Optional, Type, Union

from PyQt5.QtCore import QEventLoop, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QDialog, QProgressDialog

# import the main window object (mw) from aqt
import aqt
from aqt.main import AnkiQt
from aqt.utils import restoreGeom, saveGeom, showInfo, tooltip, openLink

from .._version import __version__
from ..collection_simulator import CollectionSimulator
from ..review_simulator import ReviewSimulator
from .forms.anki21 import (
    about_dialog,
    anki_simulator_dialog,
    manual_dialog,
    support_dialog,
)
from .graph import GraphWebView


def listToUser(l):
    def num_to_user(n: Union[int, float]):
        if n == round(n):
            return str(int(n))
        else:
            return str(n)

    return " ".join(map(num_to_user, l))


def isFloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def stepsAreValid(steps: List[str]):
    for step in steps:
        if not isFloat(step):
            return False
    if len(steps) == 0:
        return False
    else:
        return True


def downsampleList(list: list, threshold: int):
    if len(list) <= threshold or not threshold:
        return list
    else:
        step = (len(list) - 1) / (threshold - 1)
        return [list[round(index * step)] for index in range(threshold)]


class SimulatorDialog(QDialog):
    def __init__(
        self,
        mw: "AnkiQt",
        review_simulator: Type[ReviewSimulator],
        collection_simulator: Type[CollectionSimulator],
        deck_id: Optional[int] = None,
    ):
        QDialog.__init__(self, parent=mw)
        self.mw = mw
        self._review_simulator = review_simulator
        self._collection_simulator = collection_simulator
        self.dialog = anki_simulator_dialog.Ui_simulator_dialog()
        self.dialog.setupUi(self)
        self._setupHooks()
        self.setupGraph()
        self.deckChooser = aqt.deckchooser.DeckChooser(self.mw, self.dialog.deckChooser)
        if deck_id is not None:
            if hasattr(self.deckChooser, 'selected_deck_id'): # Anki >= 2.1.45
                self.deckChooser.selected_deck_id = deck_id
            else:
                deck_name = self.mw.col.decks.nameOrNone(deck_id)
                if deck_name:
                    self.deckChooser.setDeckName(deck_name)
        self.dialog.simulateButton.clicked.connect(self.simulate)
        self.dialog.loadDeckConfigurationsButton.clicked.connect(
            self.loadDeckConfigurations
        )
        self.dialog.clearLastSimulationButton.clicked.connect(
            self.clear_last_simulation
        )
        self.dialog.aboutButton.clicked.connect(self.showAboutDialog)
        self.dialog.manualButton.clicked.connect(self.showManual)
        self.dialog.supportButton.clicked.connect(self.showSupportDialog)
        self.dialog.useActualCardsCheckbox.toggled.connect(
            self.toggledUseActualCardsCheckbox
        )
        self.dialog.simulateAdditionalNewCardsCheckbox.toggled.connect(
            self.toggledGenerateAdditionalCardsCheckbox
        )
        self.schedVersion = self.mw.col.schedVer()
        self.config = self.mw.addonManager.getConfig(__name__)
        self.dialog.daysToSimulateSpinbox.setProperty(
            "value", self.config["default_days_to_simulate"]
        )
        self.loadDeckConfigurations()
        self.numberOfSimulations = 0

        self.setWindowTitle(
            f"Anki Simulator v{__version__} by GiovanniHenriksen & Glutanimate"
        )
        restoreGeom(self, "simulatorDialog")

        self._thread = None
        self._progress = None

    def _setupHooks(self):
        try:  # 2.1.20+
            from aqt.gui_hooks import profile_will_close

            profile_will_close.append(self.close)
        except (ImportError, ModuleNotFoundError):
            from anki.hooks import addHook

            addHook("unloadProfile", self.close)

    def _tearDownHooks(self):
        try:  # 2.1.20+
            from aqt.gui_hooks import profile_will_close

            profile_will_close.remove(self.close)
        except (ImportError, ModuleNotFoundError):
            from anki.hooks import remHook

            remHook("unloadProfile", self.close)

    def showAboutDialog(self):
        aboutDialog = AboutDialog(self)
        aboutDialog.exec_()

    def showManual(self):
        manual = ManualDialog(self)
        manual.exec_()

    def showSupportDialog(self):
        supportDialog = SupportDialog(parent=self)
        supportDialog.exec_()

    def _onClose(self):
        saveGeom(self, "simulatorDialog")
        self._tearDownHooks()

    def reject(self):
        self._onClose()
        super().reject()

    def accept(self):
        self._onClose()
        super().accept()

    def setupGraph(self):
        simulationGraph = GraphWebView(self.mw, parent=self)
        simulationGraph.setMinimumSize(QSize(0, 227))
        simulationGraph.setObjectName("simulationGraph")
        self.dialog.simulationGraph = simulationGraph
        self.dialog.graphLayout.addWidget(self.dialog.simulationGraph)
        self.dialog.verticalLayout.setStretchFactor(self.dialog.graphLayout, 10)

    def loadDeckConfigurations(self):
        deckID = self.deckChooser.selectedId()
        conf = self.mw.col.decks.confForDid(deckID)
        numberOfNewCardsPerDay = conf["new"]["perDay"]
        startingEase = conf["new"]["initialFactor"] / 10.0
        intervalModifier = conf["rev"]["ivlFct"] * 100
        maxRevPerDay = conf["rev"]["perDay"]
        learningSteps = conf["new"]["delays"]
        numberOfLearningSteps = len(learningSteps)
        lapseSteps = conf["lapse"]["delays"]
        numberOfLapseSteps = len(lapseSteps)
        graduatingInterval = conf["new"]["ints"][0]
        newLapseInterval = conf["lapse"]["mult"] * 100
        maxInterval = conf["rev"]["maxIvl"]

        self.dialog.newCardsPerDaySpinbox.setProperty("value", numberOfNewCardsPerDay)
        self.dialog.startingEaseSpinBox.setProperty("value", startingEase)
        self.dialog.intervalModifierSpinbox.setProperty("value", intervalModifier)
        self.dialog.maximumReviewsPerDaySpinbox.setProperty("value", maxRevPerDay)
        self.dialog.learningStepsTextfield.setText(listToUser(learningSteps))
        self.dialog.lapseStepsTextfield.setText(listToUser(lapseSteps))
        self.dialog.graduatingIntervalSpinbox.setProperty("value", graduatingInterval)
        self.dialog.newLapseIntervalSpinbox.setProperty("value", newLapseInterval)
        self.dialog.maximumIntervalSpinbox.setProperty("value", maxInterval)

        # Collecting deck stats
        deckChildren = [
            childDeck[1] for childDeck in self.mw.col.decks.children(deckID)
        ]
        deckChildren.append(deckID)
        childrenDIDs = "(" + ", ".join(str(did) for did in deckChildren) + ")"
        idCutOff = (
            self.mw.col.sched.dayCutoff - self.config["retention_cutoff_days"] * 86400
        ) * 1000

        schedulerEaseCorrection = 1 if self.schedVersion == 1 else 0
        stats = self.mw.col.db.all(
            f"""\
            WITH logs 
                 AS (SELECT type, 
                            ( CASE 
                                WHEN type = 0 
                                     AND ease = 2 THEN {2 + schedulerEaseCorrection} 
                                WHEN type = 0 
                                     AND ease = 3 THEN {3 + schedulerEaseCorrection} 
                                WHEN type = 2 
                                     AND ease = 2 THEN {2 + schedulerEaseCorrection} 
                                WHEN type = 2 
                                     AND ease = 3 THEN {3 + schedulerEaseCorrection} 
                                ELSE ease 
                              END ) AS adjustedEase, 
                            ( CASE 
                                WHEN type = 0 THEN 0 
                                WHEN type = 2 THEN 1 
                                WHEN type = 1 
                                     AND lastivl < 21 THEN 2 
                                WHEN type = 1 THEN 3 
                                WHEN type = 3 THEN 4 
                                ELSE 5 
                              END ) AS adjustedType, 
                            lastivl 
                     FROM   revlog 
                     WHERE  cid IN (SELECT cards.id 
                                    FROM   cards 
                                           INNER JOIN notes 
                                                   ON cards.nid = notes.id 
                                    WHERE  did IN {childrenDIDs} 
                                           AND NOT notes.tags LIKE 
                                    '%exclude-retention-rate%' 
                                   ) 
                            AND id > {idCutOff}) 
            SELECT adjustedtype, 
                   ( CASE 
                       WHEN lastivl < 0 THEN lastivl / -60 
                     END )               AS adjustedLastIvl, 
                   Sum(adjustedease = 1) AS incorrectCount, 
                   Sum(adjustedease = 2) AS hardCount, 
                   Sum(adjustedease = 3) AS correctCount, 
                   Sum(adjustedease = 4) AS easyCount, 
                   Count(*)              AS totalCount 
            FROM   logs 
            GROUP  BY adjustedtype, 
                      adjustedlastivl 
            ORDER  BY adjustedtype, 
                      adjustedlastivl """
        )  # type 0 = learn; type 1 = relearn; type 2 = young; type 3 = mature; type 4 = cram; type 5 = reschedule

        # Setting default values for percentages:
        learningStepsPercentages = {
            learningStep: ((70, None, 0, 0) if index == 0 else (92, None, 0, 0))
            for index, learningStep in enumerate(learningSteps)
        }
        lapseStepsPercentages = {
            lapseStep: (92, None, 0, 0) for lapseStep in lapseSteps
        }
        percentageCorrectYoungCards = (90, None, 0, 0)
        percentageCorrectMatureCards = (90, None, 0, 0)

        for (
            type,
            lastIvl,
            incorrectCount,
            hardCount,
            correctCount,
            easyCount,
            totalCount,
        ) in stats:
            if totalCount > 0:
                included = hardCount / 2 + correctCount + easyCount
                percentage = included / totalCount
                marginOfError = 196 * math.sqrt(
                    ((percentage * (1 - percentage)) / totalCount)
                )  # for 95% confidence interval
                marginOfErrorCutOff = 5  # only include actual percentages if the 95% margin of error from the mean
                # is less than 5%
                if type == 0:
                    if 0 < marginOfError <= marginOfErrorCutOff and totalCount > 10:
                        learningStepsPercentages[lastIvl] = (
                            percentage * 100,
                            marginOfError,
                            included,
                            totalCount,
                        )
                    else:
                        if lastIvl in learningStepsPercentages:
                            learningStepsPercentages[lastIvl] = (
                                learningStepsPercentages[lastIvl][0],
                                learningStepsPercentages[lastIvl][1],
                                included,
                                totalCount,
                            )
                elif type == 1:
                    if 0 < marginOfError <= marginOfErrorCutOff and totalCount > 10:
                        lapseStepsPercentages[lastIvl] = (
                            percentage * 100,
                            marginOfError,
                            included,
                            totalCount,
                        )
                    else:
                        if lastIvl in lapseStepsPercentages:
                            lapseStepsPercentages[lastIvl] = (
                                lapseStepsPercentages[lastIvl][0],
                                lapseStepsPercentages[lastIvl][1],
                                included,
                                totalCount,
                            )
                elif type == 2:
                    if 0 < marginOfError <= marginOfErrorCutOff and totalCount > 10:
                        percentageCorrectYoungCards = (
                            percentage * 100,
                            marginOfError,
                            included,
                            totalCount,
                        )
                    else:
                        percentageCorrectYoungCards = (
                            percentageCorrectYoungCards[0],
                            percentageCorrectYoungCards[1],
                            included,
                            totalCount,
                        )
                elif type == 3:
                    if 0 < marginOfError <= marginOfErrorCutOff and totalCount > 10:
                        percentageCorrectMatureCards = (
                            percentage * 100,
                            marginOfError,
                            included,
                            totalCount,
                        )
                    else:
                        percentageCorrectMatureCards = (
                            percentageCorrectMatureCards[0],
                            percentageCorrectMatureCards[1],
                            included,
                            totalCount,
                        )
                else:
                    break
        self.dialog.percentCorrectLearningTextfield.setText(
            listToUser(
                [
                    int(learningStepsPercentages[learningStep][0])
                    for learningStep in learningSteps
                ]
            )
        )
        learningStepsToolTip = "95% Confidence intervals:"
        for learningStep in learningSteps:
            marginOfError = learningStepsPercentages[learningStep][1]
            included = learningStepsPercentages[learningStep][2]
            total = learningStepsPercentages[learningStep][3]
            if marginOfError:
                mean = learningStepsPercentages[learningStep][0]
                lowerBound = max(round(mean - marginOfError, 1), 0)
                upperBound = min(round(mean + marginOfError, 1), 100)
                learningStepsToolTip += "\n- Learning step {}: {}% - {}% ({}/{})".format(
                    learningStep, lowerBound, upperBound, round(included), total
                )
            else:
                learningStepsToolTip += "\n- Learning step {}: Not enough data to accurately estimate retention rate ({}/{})".format(
                    learningStep, round(included), total
                )
        self.dialog.percentCorrectLearningTextfield.setToolTip(learningStepsToolTip)
        self.dialog.percentCorrectLapseTextfield.setText(
            listToUser(
                [int(lapseStepsPercentages[lapseStep][0]) for lapseStep in lapseSteps]
            )
        )

        lapseStepsToolTip = "95% Confidence intervals:"
        for lapseStep in lapseSteps:
            marginOfError = lapseStepsPercentages[lapseStep][1]
            included = lapseStepsPercentages[lapseStep][2]
            total = lapseStepsPercentages[lapseStep][3]
            if marginOfError:
                mean = lapseStepsPercentages[lapseStep][0]
                lowerBound = max(round(mean - marginOfError, 1), 0)
                upperBound = min(round(mean + marginOfError, 1), 100)
                lapseStepsToolTip += "\n- Lapse step {}: {}% - {}% ({}/{})".format(
                    lapseStep, lowerBound, upperBound, round(included), total
                )
            else:
                lapseStepsToolTip += (
                    "\n- Lapse step {}: Not enough data to accurately estimate retention rate ({"
                    "}/{})".format(lapseStep, round(included), total)
                )
        self.dialog.percentCorrectLapseTextfield.setToolTip(lapseStepsToolTip)

        youngCardsMean = percentageCorrectYoungCards[0]
        youngCardsMarginOfError = percentageCorrectYoungCards[1]
        youngCardsIncluded = percentageCorrectYoungCards[2]
        youngCardsTotal = percentageCorrectYoungCards[3]
        self.dialog.percentCorrectYoungSpinbox.setProperty("value", int(youngCardsMean))
        if youngCardsMarginOfError:
            youngCardsLowerBound = max(
                round(youngCardsMean - youngCardsMarginOfError, 1), 0
            )
            youngCardsUpperBound = min(
                round(youngCardsMean + youngCardsMarginOfError, 1), 100
            )
            self.dialog.percentCorrectYoungSpinbox.setToolTip(
                "95% Confidence interval: {}% - {}% ({}/{})".format(
                    youngCardsLowerBound,
                    youngCardsUpperBound,
                    round(youngCardsIncluded),
                    youngCardsTotal,
                )
            )
        else:
            self.dialog.percentCorrectYoungSpinbox.setToolTip(
                "Not enough data to accurately estimate retention rate ({}/{})".format(
                    round(youngCardsIncluded), youngCardsTotal,
                )
            )

        matureCardsMean = percentageCorrectMatureCards[0]
        matureCardsMarginOfError = percentageCorrectMatureCards[1]
        matureCardsIncluded = percentageCorrectMatureCards[2]
        matureCardsTotal = percentageCorrectMatureCards[3]
        self.dialog.percentCorrectMatureSpinbox.setProperty(
            "value", int(matureCardsMean)
        )
        if matureCardsMarginOfError:
            matureCardsLowerBound = max(
                round(matureCardsMean - matureCardsMarginOfError, 1), 0
            )
            matureCardsUpperBound = min(
                round(matureCardsMean + matureCardsMarginOfError, 1), 100
            )
            self.dialog.percentCorrectMatureSpinbox.setToolTip(
                "95% Confidence interval: {}% - {}% ({}/{})".format(
                    matureCardsLowerBound,
                    matureCardsUpperBound,
                    round(matureCardsIncluded),
                    matureCardsTotal,
                )
            )
        else:
            self.dialog.percentCorrectMatureSpinbox.setToolTip(
                "Not enough data to accurately estimate retention rate ({}/{})".format(
                    round(matureCardsIncluded), matureCardsTotal,
                )
            )

    def simulate(self):
        daysToSimulate = int(self.dialog.daysToSimulateSpinbox.value())
        startingEase = int(self.dialog.startingEaseSpinBox.value())
        newCardsPerDay = int(self.dialog.newCardsPerDaySpinbox.value())
        intervalModifier = float(self.dialog.intervalModifierSpinbox.value()) / 100
        maxReviewsPerDay = int(self.dialog.maximumReviewsPerDaySpinbox.value())
        if not stepsAreValid(self.dialog.learningStepsTextfield.text().split()):
            showInfo("Please correctly enter 'Learning steps' (e.g. '30 1440')")
            self.dialog.learningStepsTextfield.setFocus()
            return
        learningSteps = [
            float(i) for i in self.dialog.learningStepsTextfield.text().split()
        ]
        if not stepsAreValid(self.dialog.lapseStepsTextfield.text().split()):
            showInfo("Please correctly enter 'Lapse steps' (e.g. '30 1440')")
            self.dialog.lapseStepsTextfield.setFocus()
            return
        lapseSteps = [float(i) for i in self.dialog.lapseStepsTextfield.text().split()]
        graduatingInterval = int(self.dialog.graduatingIntervalSpinbox.value())
        newLapseInterval = float(self.dialog.newLapseIntervalSpinbox.value()) / 100
        maxInterval = int(self.dialog.maximumIntervalSpinbox.value())
        if not stepsAreValid(
            self.dialog.percentCorrectLearningTextfield.text().split()
        ):
            showInfo("Please correctly enter '% correct learning steps' (e.g. '90 90')")
            self.dialog.percentCorrectLearningTextfield.setFocus()
            return
        percentagesCorrectForLearningSteps = [
            int(i) for i in self.dialog.percentCorrectLearningTextfield.text().split()
        ]
        if len(percentagesCorrectForLearningSteps) != len(learningSteps):
            showInfo(
                "Number of '% correct learning steps' does not match the number of 'Learning steps'"
            )
            self.dialog.percentCorrectLearningTextfield.setFocus()
            return
        if not stepsAreValid(self.dialog.percentCorrectLapseTextfield.text().split()):
            showInfo("Please correctly enter '% correct lapse steps' (e.g. '90 90')")
            self.dialog.percentCorrectLapseTextfield.setFocus()
            return
        percentagesCorrectForLapseSteps = [
            int(i) for i in self.dialog.percentCorrectLapseTextfield.text().split()
        ]
        if len(percentagesCorrectForLapseSteps) != len(lapseSteps):
            showInfo(
                "Number of '% correct lapse steps' does not match the number of 'Lapse steps'"
            )
            self.dialog.percentCorrectLapseTextfield.setFocus()
            return
        percentageGoodYoung = self.dialog.percentCorrectYoungSpinbox.value()
        percentageGoodMature = self.dialog.percentCorrectMatureSpinbox.value()

        shouldUseActualCards = self.dialog.useActualCardsCheckbox.isChecked()
        shouldGenerateAdditionalCards = (
            self.dialog.simulateAdditionalNewCardsCheckbox.isChecked()
        )
        newCardsToGenerate = (
            self.dialog.mockedNewCardsSpinbox.value()
            if self.dialog.simulateAdditionalNewCardsCheckbox.isChecked()
            else 0
        )

        collection_simulator = self._collection_simulator(self.mw)

        if shouldUseActualCards:
            # Use actual card data for simulation
            includeOverdueCards = self.dialog.includeOverdueCardsCheckbox.isChecked()
            includeSuspendedNewCards = (
                self.dialog.includeSuspendedNewCardsCheckbox.isChecked()
            )
            # returns an array of days, each day is another array that contains all
            # the cards for that day:
            dateArray, totalNumberOfCards, numberOfMatureCards = collection_simulator.generate_for_deck(
                self.deckChooser.selectedId(),
                daysToSimulate,
                int(self.dialog.newCardsPerDaySpinbox.value()),
                startingEase,
                len(learningSteps),
                len(lapseSteps),
                includeOverdueCards,
                includeSuspendedNewCards,
                newCardsToGenerate,
            )
        elif shouldGenerateAdditionalCards:
            # Simulate a deck with x new cards
            dateArray = collection_simulator.generate_for_new_count(
                daysToSimulate, newCardsPerDay, newCardsToGenerate, startingEase
            )
            totalNumberOfCards = newCardsToGenerate
            numberOfMatureCards = 0
        else:
            raise NotImplementedError

        sim = self._review_simulator(
            dateArray,
            daysToSimulate,
            newCardsPerDay,
            intervalModifier,
            maxReviewsPerDay,
            learningSteps,
            lapseSteps,
            graduatingInterval,
            newLapseInterval,
            maxInterval,
            percentagesCorrectForLearningSteps,
            percentagesCorrectForLapseSteps,
            percentageGoodYoung,
            percentageGoodMature,
            0,  # Percentage hard is set to 0
            0,  # Percentage easy is set to 0
            self.schedVersion,
            totalNumberOfCards,
            numberOfMatureCards
        )

        thread = SimulatorThread(sim, parent=self)
        progress = SimulatorProgressDialog(maximum=len(dateArray), parent=self)

        thread.done.connect(self._on_simulation_done)
        thread.canceled.connect(self._on_simulation_canceled)

        thread.tick.connect(progress.update)
        progress.canceled.connect(thread.cancel)

        self._thread = thread
        self._progress = progress

        self._thread.start()
        self._progress.exec_()

    def _on_simulation_done(self, data: List[Dict[str, Union[str, int]]]):
        self.__gc_qobjects()

        self.numberOfSimulations += 1
        deck = self.mw.col.decks.get(self.deckChooser.selectedId())

        # total_cards = sum(day["y"] for day in data)
        if self.dialog.useActualCardsCheckbox.isChecked():
            simulationTitle = "{} ({})".format(
                self.dialog.simulationTitleTextfield.text(), deck["name"]
            )
        else:
            simulationTitle = "{} repetitions".format(
                self.dialog.simulationTitleTextfield.text()
            )

        self.dialog.simulationGraph.addDataSet(
            simulationTitle,
            downsampleList(data, self.config["max_number_of_data_points"]),
        )
        self.dialog.simulationTitleTextfield.setText(
            "Simulation {}".format(self.numberOfSimulations + 1)
        )

        self.dialog.clearLastSimulationButton.setEnabled(True)

    def _on_simulation_canceled(self):
        self.__gc_qobjects()

        if self._progress:
            # seems to be necessary to prevent progress dialog from being stuck:
            QApplication.instance().processEvents(QEventLoop.ExcludeUserInputEvents)
            self._progress.cancel()
        tooltip("Canceled", parent=self)

    def __gc_qobjects(self):
        # manually garbage collect to prevent memory leak:
        if self._progress:
            self._progress.deleteLater()
            self._progress = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        gc.collect()

    def clear_last_simulation(self):
        self.dialog.simulationGraph.clearLastDataset()
        self.numberOfSimulations -= 1
        if self.numberOfSimulations == 0:
            self.dialog.clearLastSimulationButton.setEnabled(False)
        if not self.dialog.simulationTitleTextfield.isModified():
            self.dialog.simulationTitleTextfield.setText(
                "Simulation {}".format(self.numberOfSimulations + 1)
            )

    def toggledUseActualCardsCheckbox(self):
        if not self.dialog.useActualCardsCheckbox.isChecked():
            self.dialog.simulateAdditionalNewCardsCheckbox.setChecked(True)

    def toggledGenerateAdditionalCardsCheckbox(self):
        if not self.dialog.simulateAdditionalNewCardsCheckbox.isChecked():
            self.dialog.useActualCardsCheckbox.setChecked(True)


class SimulatorThread(QThread):
    done = pyqtSignal(object)
    canceled = pyqtSignal()
    tick = pyqtSignal(int)

    def __init__(self, simulator: "ReviewSimulator", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._simulator = simulator
        self.do_cancel = False
        self._last_tick = time.time()

    def run(self):
        # import timeit
        # start = timeit.default_timer()
        data = self._simulator.simulate(self)
        # print(timeit.default_timer() - start)
        if data is None:
            self.canceled.emit()
            return
        self.done.emit(data)

    def cancel(self):
        self.do_cancel = True

    def day_processed(self, day: int):
        now = time.time()
        if (now - self._last_tick) >= 0.1:
            self.tick.emit(day)  # type: ignore
            self._last_tick = now


class SimulatorProgressDialog(QProgressDialog):
    def __init__(self, minimum=0, maximum=100, *args, **kwargs):
        super().__init__(minimum=minimum, maximum=maximum, *args, **kwargs)
        self.setLabelText("Simulating reviews...")
        self.setCancelButtonText("Cancel simulation")

    @pyqtSlot(int)
    def update(self, value):
        self.setValue(value)

    @pyqtSlot()
    def finish(self):
        self.setValue(self.maximum())


class AboutDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.dialog = about_dialog.Ui_about_dialog()
        self.dialog.setupUi(self)
        self._setVersionText()
        self.dialog.closeButton.clicked.connect(self.close)

    def _setVersionText(self):
        html = self.dialog.textBrowser.toHtml()
        html = html.replace("%VERSION%", __version__)
        self.dialog.textBrowser.setHtml(html)

    def close(self):
        self.reject()


class ManualDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.dialog = manual_dialog.Ui_manual_dialog()
        self.dialog.setupUi(self)
        self.dialog.closeButton.clicked.connect(self.close)

    def close(self):
        self.reject()


class SupportDialog(QDialog):

    _giovanni_link = "https://www.ko-fi.com/giovannihenriksen"
    _glutanimate_link = "https://www.patreon.com/glutanimate"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialog = support_dialog.Ui_support_dialog()
        self.dialog.setupUi(self)
        self.dialog.giovanniButton.clicked.connect(self.onGiovanni)
        self.dialog.glutanimateButton.clicked.connect(self.onGlutanimate)

    def onGiovanni(self):
        openLink(self._giovanni_link)

    def onGlutanimate(self):
        openLink(self._glutanimate_link)
