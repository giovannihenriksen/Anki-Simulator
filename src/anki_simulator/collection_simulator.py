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

from typing import Optional, List

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


# TODO: consider refactoring into dataclasses if performance allows for it


class SimulatedReview:

    __slots__ = (
        "day",
        "delay",
        "wasState",
        "correct",
        "daysToAdd",
        "becomes",
        "newEase",
    )

    def __init__(
        self,
        *,
        day: int,
        delay: int,
        wasState: CARD_STATES_TYPE,
        correct: bool,
        daysToAdd: int,
        becomes: CARD_STATES_TYPE,
        newEase: int
    ):
        self.day: int = day
        self.delay: int = delay
        self.wasState: CARD_STATES_TYPE = wasState
        self.correct: bool = correct
        self.daysToAdd: int = daysToAdd
        self.becomes: CARD_STATES_TYPE = becomes
        self.newEase: int = newEase


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
        reviews: Optional[List[SimulatedReview]] = None,
        delay: int = 0
    ):
        self.id: int = id
        self.ivl: int = ivl
        self.ease: int = ease
        self.state: CARD_STATES_TYPE = state
        self.step: int = step
        self.reviews: List[SimulatedReview] = reviews or []
        self.delay: int = delay

    def copy(self) -> "SimulatedCard":
        return SimulatedCard(
            id=self.id,
            ivl=self.ivl,
            ease=self.ease,
            state=self.state,
            step=self.step,
            reviews=self.reviews,
            delay=self.delay,
        )


DATE_ARRAY_TYPE = List[List[SimulatedCard]]


class CollectionSimulator:
    def __init__(self, mw):
        self._mw = mw

    def generate_for_deck(
        self,
        did,
        days_to_simulate,
        number_of_new_cards_per_day,
        starting_ease,
        number_of_learning_steps,
        number_of_lapse_steps,
        include_overdue_cards,
        include_suspended_new_cards,
    ) -> DATE_ARRAY_TYPE:
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
        cids = self._mw.col.decks.cids(did, True)
        for cid in cids:
            card = self._mw.col.getCard(cid)
            if card.type == 0:
                # New card
                if card.queue != -1 or include_suspended_new_cards:
                    review = SimulatedCard(id=card.id, ease=starting_ease)
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
                review = SimulatedCard(
                    id=card.id,
                    ease=starting_ease,
                    state=CARD_STATE_LEARNING,
                    step=max(number_of_learning_steps - (card.left % 10), -1),
                )
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
                review = SimulatedCard(
                    id=card.id,
                    ease=card.factor / 10,
                    state=CARD_STATE_RELEARN,
                    ivl=card.ivl,
                    step=max(number_of_lapse_steps - (card.left % 10), -1),
                )
                if cardDue < days_to_simulate:
                    dateArray[cardDue].append(review)

        # Adding new cards
        if number_of_new_cards_per_day > 0:
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

        return dateArray

    @staticmethod
    def generate_for_new_count(
        days_to_simulate, number_of_new_cards_per_day, new_cards_in_deck, starting_ease,
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
