from datetime import date

from PyQt5.QtCore import QEventLoop, QSize, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAction, QApplication, QDialog, QProgressDialog

# import the main window object (mw) from aqt
import aqt
from aqt.utils import showInfo, tooltip

from .simulator import Simulator
from .gui import graph
from .gui.forms.anki21 import anki_simulator_dialog


def listToUser(l):
    return " ".join([str(x) for x in l])


def stepsAreValid(steps):
    for step in steps:
        if not step.isdecimal():
            return False
    if len(steps) == 0:
        return False
    else:
        return True


class SimulatorDialog(QDialog):

    def __init__(self, mw, deck_id=None):
        QDialog.__init__(self, parent=mw)
        self.mw = mw
        self.dialog = anki_simulator_dialog.Ui_simulator_dialog()
        self.dialog.setupUi(self)
        self.setupGraph()
        self.deckChooser = aqt.deckchooser.DeckChooser(self.mw, self.dialog.deckChooser)
        if deck_id is not None:
            deck_name = self.mw.col.decks.nameOrNone(deck_id)
            if deck_name:
                self.deckChooser.setDeckName(deck_name)
        self.dialog.simulateButton.clicked.connect(self.simulate)
        self.dialog.loadDeckConfigurationsButton.clicked.connect(self.loadDeckConfigurations)
        self.dialog.clearLastSimulationButton.clicked.connect(self.clear_last_simulation)
        self.loadDeckConfigurations()
        self.warnedAboutOverdueCards = False
        self.numberOfSimulations = 0
        
        self._thread = None
        self._progress = None
        
        self.setWindowModality(Qt.WindowModal)

    def setupGraph(self):
        simulationGraph = graph.Graph(parent=self)
        simulationGraph.setMinimumSize(QSize(0, 227))
        simulationGraph.setObjectName("simulationGraph")
        self.dialog.simulationGraph = simulationGraph
        self.dialog.verticalLayout.addWidget(self.dialog.simulationGraph)

    def loadDeckConfigurations(self):
        deckID = self.deckChooser.selectedId()
        conf = self.mw.col.decks.confForDid(deckID)
        numberOfNewCardsPerDay = conf['new']['perDay']
        startingEase = conf['new']['initialFactor'] / 10.0
        intervalModifier = conf['rev']['ivlFct'] * 100
        maxRevPerDay = conf['rev']['perDay']
        numberOfLearningSteps = len(conf['new']['delays'])
        learningSteps = listToUser(conf['new']['delays'])
        numberOfLapseSteps = len(conf['lapse']['delays'])
        lapseSteps = listToUser(conf['lapse']['delays'])
        graduatingInterval = conf['new']['ints'][0]
        newLapseInterval = conf['lapse']['mult'] * 100
        maxInterval = conf['rev']['maxIvl']

        self.dialog.newCardsPerDaySpinbox.setProperty('value', numberOfNewCardsPerDay)
        self.dialog.startingEaseSpinBox.setProperty('value', startingEase)
        self.dialog.intervalModifierSpinbox.setProperty('value', intervalModifier)
        self.dialog.maximumReviewsPerDaySpinbox.setProperty('value', maxRevPerDay)
        self.dialog.learningStepsTextfield.setText(learningSteps)
        self.dialog.lapseStepsTextfield.setText(lapseSteps)
        self.dialog.graduatingIntervalSpinbox.setProperty('value', graduatingInterval)
        self.dialog.newLapseIntervalSpinbox.setProperty('value', newLapseInterval)
        self.dialog.maximumIntervalSpinbox.setProperty('value', maxInterval)
        self.dialog.percentCorrectLearningTextfield.setText(listToUser([92] * numberOfLearningSteps))
        self.dialog.percentCorrectLapseTextfield.setText(listToUser([92] * numberOfLapseSteps))

    def loadCards(self, did, days_to_simulate, number_of_new_cards_per_day, starting_ease, number_of_learning_steps,
                  number_of_lapse_steps, include_overdue_cards):
        # Before we start the simulation, we will collect all the cards from the database.
        crt = date.fromtimestamp(
            self.mw.col.crt)  # Gets collection creation time. We need this to find out when a card is due.
        today = date.today()
        todayInteger = (today - crt).days
        dateArray = []
        while len(dateArray) < days_to_simulate:
            dateArray.append([])
        newCards = []
        cids = self.mw.col.decks.cids(did, True)
        for cid in cids:
            card = self.mw.col.getCard(cid)
            if card.type == 0:
                # New card
                review = dict(id=card.id, ease=starting_ease, state='unseen', step=0, reviews=[])
                newCards.append(review)
            elif card.type == 1:
                # Learning card
                if card.queue == -1:
                    continue  # Card is suspended, so we will skip this card.
                cardDue = card.due - todayInteger
                if card.odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = card.odue - todayInteger
                if card.queue == 1:
                    # This is a day learn card, so the due date is today.
                    cardDue = 0
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                review = dict(id=card.id, ease=starting_ease, state='learning',
                              step=max(number_of_learning_steps - (card.left % 10), -1), reviews=[])
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)
            elif card.type == 2:
                # Young/mature card
                if card.queue == -1:
                    # Card is suspended, so we will skip this card.
                    continue
                cardDue = card.due - todayInteger
                if card.odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = card.odue - todayInteger
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                review = dict(id=card.id, ease=card.factor / 10, currentInterval=card.ivl)
                if card.ivl >= 21:
                    review['state'] = 'mature'
                if card.ivl < 21:
                    review['state'] = 'young'
                review['reviews'] = []
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)
            elif card.type == 3:
                # Relearn card
                if card.queue == -1:
                    continue  # Relearning card is suspended, so we will skip it.
                cardDue = card.due - todayInteger
                if card.odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = card.odue - todayInteger
                if card.queue == 1:
                    # This is a day relearn card, so the due date is today.
                    cardDue = 0
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                review = dict(id=card.id, ease=card.factor / 10, state='relearn', currentInterval=card.ivl,
                              step=max(number_of_lapse_steps - (
                                      card.left % 10), -1), reviews=[])
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)

        # Adding new cards
        if number_of_new_cards_per_day > 0:
            deck = self.mw.col.decks.get(did)
            newCardsAlreadySeenToday = min(deck['newToday'][1], number_of_new_cards_per_day)
            for index, card in enumerate(newCards):
                dayToAddNewCardsTo = int((index + newCardsAlreadySeenToday) / number_of_new_cards_per_day)
                if dayToAddNewCardsTo < days_to_simulate:
                    dateArray[dayToAddNewCardsTo].append(card)
        return dateArray

    def simulate(self):
        daysToSimulate = int(self.dialog.daysToSimulateSpinbox.value())
        startingEase = int(self.dialog.startingEaseSpinBox.value())
        newCardsPerDay = int(self.dialog.newCardsPerDaySpinbox.value())
        intervalModifier = float(self.dialog.intervalModifierSpinbox.value()) / 100
        maxReviewsPerDay = int(self.dialog.maximumReviewsPerDaySpinbox.value())
        if not stepsAreValid(self.dialog.learningStepsTextfield.text().split()):
            showInfo('Please correctly enter \'Learning steps\' (e.g. \'30 1440\')')
            self.dialog.learningStepsTextfield.setFocus()
            return
        learningSteps = [int(i) for i in self.dialog.learningStepsTextfield.text().split()]
        if not stepsAreValid(self.dialog.lapseStepsTextfield.text().split()):
            showInfo('Please correctly enter \'Lapse steps\' (e.g. \'30 1440\')')
            self.dialog.lapseStepsTextfield.setFocus()
            return
        lapseSteps = [int(i) for i in self.dialog.lapseStepsTextfield.text().split()]
        graduatingInterval = int(self.dialog.graduatingIntervalSpinbox.value())
        newLapseInterval = float(self.dialog.newLapseIntervalSpinbox.value()) / 100
        maxInterval = int(self.dialog.maximumIntervalSpinbox.value())
        chanceRightUnseen = float(self.dialog.percentCorrectUnseenSpinbox.value()) / 100
        if not stepsAreValid(self.dialog.percentCorrectLearningTextfield.text().split()):
            showInfo('Please correctly enter \'% correct learning steps\' (e.g. \'90 90\')')
            self.dialog.percentCorrectLearningTextfield.setFocus()
            return
        percentagesCorrectForLearningSteps = [float(i) / 100 for i in
                                              self.dialog.percentCorrectLearningTextfield.text().split()]
        if len(percentagesCorrectForLearningSteps) != len(learningSteps):
            showInfo("Number of \'% correct learning steps\' does not match the number of \'Learning steps\'")
            self.dialog.percentCorrectLearningTextfield.setFocus()
            return
        if not stepsAreValid(self.dialog.percentCorrectLapseTextfield.text().split()):
            showInfo('Please correctly enter \'% correct lapse steps\' (e.g. \'90 90\')')
            self.dialog.percentCorrectLapseTextfield.setFocus()
            return
        percentagesCorrectForLapseSteps = [float(i) / 100 for i in
                                           self.dialog.percentCorrectLapseTextfield.text().split()]
        if len(percentagesCorrectForLapseSteps) != len(lapseSteps):
            showInfo("Number of \'% correct lapse steps\' does not match the number of \'Lapse steps\'")
            self.dialog.percentCorrectLapseTextfield.setFocus()
            return
        chanceRightYoung = float(self.dialog.percentCorrectYoungSpinbox.value()) / 100
        chanceRightMature = float(self.dialog.percentCorrectMatureSpinbox.value()) / 100
        includeOverdueCards = self.dialog.includeOverdueCardsCheckbox.isChecked()
        dateArray = self.loadCards(self.deckChooser.selectedId(), daysToSimulate,
                                   int(self.dialog.newCardsPerDaySpinbox.value()),
                                   startingEase, len(learningSteps), len(lapseSteps), includeOverdueCards)  # returns an array of days,
        # each day is another array that contains all the cards for that day


        sim = Simulator(dateArray, daysToSimulate, newCardsPerDay, intervalModifier, maxReviewsPerDay,
                        learningSteps, lapseSteps, graduatingInterval, newLapseInterval, maxInterval,
                        chanceRightUnseen, percentagesCorrectForLearningSteps,
                        percentagesCorrectForLapseSteps, chanceRightYoung, chanceRightMature)
        
        thread = SimulatorThread(sim, parent=self)
        progress = SimulatorProgressDialog(maximum=len(dateArray), parent=self)
        
        thread.done.connect(progress.finish)
        thread.done.connect(self._on_simulation_done)
        thread.canceled.connect(self._on_simulation_canceled)
        
        thread.tick.connect(progress.update)
        progress.canceled.connect(thread.cancel)
       
        self._thread = thread
        self._progress = progress
       
        self._thread.start()
        self._progress.show()
        
    def _on_simulation_done(self, data):
        self.numberOfSimulations += 1
        deck = self.mw.col.decks.get(self.deckChooser.selectedId())
        simulationTitle = "{} ({})".format(self.dialog.simulationTitleTextfield.text(), deck['name'])
        self.dialog.simulationGraph.addDataSet(simulationTitle, data)
        self.dialog.simulationTitleTextfield.setText("Simulation {}".format(self.numberOfSimulations+1))
        self.dialog.clearLastSimulationButton.setEnabled(True)

    def _on_simulation_canceled(self):
        if self._progress:
            # seems to be necessary to prevent progress dialog from being stuck:
            QApplication.instance().processEvents(QEventLoop.ExcludeUserInputEvents)
            self._progress.cancel()
        tooltip("Canceled", parent=self)

    def clear_last_simulation(self):
        self.dialog.simulationGraph.clearLastDataset()
        self.numberOfSimulations -= 1
        if self.numberOfSimulations == 0:
            self.dialog.clearLastSimulationButton.setEnabled(False)
        if not self.dialog.simulationTitleTextfield.isModified():
            self.dialog.simulationTitleTextfield.setText("Simulation {}".format(self.numberOfSimulations + 1))

class SimulatorThread(QThread):
    
    done = pyqtSignal(object)
    canceled = pyqtSignal()
    tick = pyqtSignal(int)
    
    def __init__(self, simulator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._simulator = simulator
        self.do_cancel = False
    
    def run(self):
        data = self._simulator.simulate(self)
        if data is None:
            self.canceled.emit()
            return
        self.done.emit(data)

    def cancel(self):
        self.do_cancel = True

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


def open_simulator_dialog(deck_id=None):
    dialog = SimulatorDialog(aqt.mw, deck_id=deck_id)
    dialog.show()

def on_deck_browser_will_show_options_menu(menu, deck_id):
    action = menu.addAction("Simulate")
    action.triggered.connect(lambda _, did=deck_id: open_simulator_dialog(did))

# Main menu

action = QAction('Anki Simulator', aqt.mw)
action.triggered.connect(open_simulator_dialog)
aqt.mw.form.menuTools.addAction(action)

# Deck options context menu

try:  # Anki 2.1.20+
    from aqt.gui_hooks import deck_browser_will_show_options_menu
    deck_browser_will_show_options_menu.append(on_deck_browser_will_show_options_menu)
except (ImportError, ModuleNotFoundError):
    from anki.hooks import addHook
    addHook("showDeckOptions", on_deck_browser_will_show_options_menu)
