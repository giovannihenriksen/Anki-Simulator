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

import datetime
from typing import List

try:
    from typing import Literal, Final
except ImportError:
    from typing_extensions import Literal, Final

CARD_STATE_NEW: Final = 0
CARD_STATE_LEARNING: Final = 1
CARD_STATE_YOUNG: Final = 2
CARD_STATE_MATURE: Final = 3
CARD_STATE_RELEARN: Final = 4

CARD_STATES_TYPE = Literal[
    0, 1, 2, 3, 4,
]


# TODO: consider refactoring into dataclass if performance allows for it


class SimulatedCard:

    __slots__ = ("id", "ivl", "ease", "state", "step", "reviews", "delay")

    def __init__(
        self,
        *,
        id: int,
        ivl: int = 0,
        ease: int = 250,
        state: CARD_STATES_TYPE = CARD_STATE_NEW,
        step: int = 0,
        delay: int = 0
    ):
        self.id: int = id
        self.ivl: int = ivl
        self.ease: int = ease
        self.state: CARD_STATES_TYPE = state
        self.step: int = step
        self.delay: int = delay

    def copy(self) -> "SimulatedCard":
        return SimulatedCard(
            id=self.id,
            ivl=self.ivl,
            ease=self.ease,
            state=self.state,
            step=self.step,
            delay=self.delay,
        )


DATE_ARRAY_TYPE = List[List[SimulatedCard]]


class CollectionSimulator:
    def __init__(self, mw):
        self._mw = mw

    def generate_for_deck(
        self,
        did: int,
        days_to_simulate: int,
        number_of_new_cards_per_day: int,
        starting_ease: int,
        number_of_learning_steps: int,
        number_of_lapse_steps: int,
        include_overdue_cards: bool,
        include_suspended_new_cards: bool,
        number_of_additional_new_cards_to_generate: int,
    ) -> (DATE_ARRAY_TYPE, int):
        # Before we start the simulation, we will collect all the cards from the database.
        crt = datetime.date.fromtimestamp(
            self._mw.col.crt
        )  # Gets collection creation time. We need this to find out when a card is due.
        today = datetime.date.today()
        todayInteger = (today - crt).days
        dateArray: DATE_ARRAY_TYPE = []
        while len(dateArray) < days_to_simulate:
            dateArray.append([])
        newCards = []
        numberOfMatureCards = 0
        cids = self._mw.col.decks.cids(did, True)
        totalNumberOfCards = len(cids)
        for cid in cids:
            card = self._mw.col.getCard(cid)
            
            # old bugs with the V2 scheduler or buggy add-ons could cause due and odue
            # values to be a float, so let's preemptively cast them to an int:
            fixed_card_due = round(card.due)
            fixed_card_odue = round(card.odue)
            
            if card.type == 0:
                # New card
                if card.queue != -1 or include_suspended_new_cards:
                    review = SimulatedCard(id=card.id, ease=starting_ease)
                    newCards.append(review)
            elif card.type == 1:
                # Learning card
                if card.queue == -1:
                    continue  # Card is suspended, so we will skip this card.
                cardDue = fixed_card_due - todayInteger
                if fixed_card_odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = fixed_card_odue - todayInteger
                if card.queue == 1:
                    # This is a day learn card, so the due date is today.
                    cardDue = 0
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                review = SimulatedCard(
                    id=card.id,
                    ease=starting_ease,
                    state=CARD_STATE_LEARNING,
                    step=max(number_of_learning_steps - (card.left % 1000), -1),
                )
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)
            elif card.type == 2:
                # Young/mature card
                if card.ivl >= 21:
                    numberOfMatureCards += 1
                if card.queue == -1:
                    # Card is suspended, so we will skip this card.
                    continue
                cardDue = fixed_card_due - todayInteger
                if fixed_card_odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = fixed_card_odue - todayInteger
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                review = SimulatedCard(
                    id=card.id, ease=card.factor / 10, ivl=card.ivl, delay=0
                )
                if card.ivl >= 21:
                    review.state = CARD_STATE_MATURE
                else:
                    review.state = CARD_STATE_YOUNG
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)
            elif card.type == 3:
                # Relearn card
                if card.queue == -1:
                    continue  # Relearning card is suspended, so we will skip it.
                cardDue = fixed_card_due - todayInteger
                if fixed_card_odue != 0:
                    # Card is in a filtered deck, so we will use the 'odue' instead.
                    cardDue = fixed_card_odue - todayInteger
                if card.queue == 1:
                    # This is a day relearn card, so the due date is today.
                    cardDue = 0
                if cardDue < 0:
                    if include_overdue_cards:
                        cardDue = 0
                    else:
                        # Card is overdue. We will not include it in the simulation.
                        continue
                if cardDue < days_to_simulate:
                    review = SimulatedCard(
                        id=card.id,
                        ease=card.factor / 10,
                        state=CARD_STATE_RELEARN,
                        ivl=card.ivl,
                        step=max(number_of_lapse_steps - (card.left % 1000), -1),
                    )
                    dateArray[cardDue].append(review)

        if number_of_new_cards_per_day > 0:
            if number_of_additional_new_cards_to_generate > 0:
                additionalCardsToGenerate = min(
                    number_of_additional_new_cards_to_generate,
                    (number_of_new_cards_per_day * days_to_simulate) - len(newCards),
                )
                totalNumberOfCards += number_of_additional_new_cards_to_generate
                for cid in range(additionalCardsToGenerate):
                    newCards.append(SimulatedCard(id=cid, ease=starting_ease,))
            # Adding the collected new cards to our data structure
            deck = self._mw.col.decks.get(did)
            newCardsAlreadySeenToday = min(
                deck["newToday"][1], number_of_new_cards_per_day
            )
            for index, card in enumerate(newCards):
                dayToAddNewCardsTo = int(
                    (index + newCardsAlreadySeenToday) / number_of_new_cards_per_day
                )
                if dayToAddNewCardsTo < days_to_simulate:
                    dateArray[dayToAddNewCardsTo].append(card)

        return (dateArray, totalNumberOfCards, numberOfMatureCards)

    @staticmethod
    def generate_for_new_count(
        days_to_simulate: int,
        number_of_new_cards_per_day: int,
        new_cards_in_deck: int,
        starting_ease: int,
    ) -> DATE_ARRAY_TYPE:
        cards_left = new_cards_in_deck
        dateArray: DATE_ARRAY_TYPE = []

        for day in range(days_to_simulate):
            if not cards_left:
                dateArray.append([])
                continue

            cards_for_the_day = []
            left_today = min(number_of_new_cards_per_day, cards_left)

            for cid in range(left_today):
                cards_for_the_day.append(SimulatedCard(id=cid, ease=starting_ease))

            dateArray.append(cards_for_the_day)

            cards_left -= left_today

        return dateArray
