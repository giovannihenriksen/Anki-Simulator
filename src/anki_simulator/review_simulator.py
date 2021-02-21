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

from datetime import date, timedelta
from random import randint
from typing import Optional, List, Dict, Union
from itertools import accumulate

from .collection_simulator import (
    CARD_STATE_NEW,
    CARD_STATE_LEARNING,
    CARD_STATE_YOUNG,
    CARD_STATE_MATURE,
    CARD_STATE_RELEARN,
    DATE_ARRAY_TYPE,
    CARD_STATES_TYPE,
)

try:
    from typing import Literal, Final
except ImportError:
    from typing_extensions import Literal, Final

ANSWER_WRONG: Final = 0
ANSWER_HARD: Final = 1
ANSWER_GOOD: Final = 2
ANSWER_EASY: Final = 3

REVIEW_ANSWER = Literal[
    0, 1, 2, 3,
]


class ReviewSimulator:
    def __init__(
        self,
        date_array: DATE_ARRAY_TYPE,
        days_to_simulate: int,
        new_cards_per_day: int,
        interval_modifier: int,
        max_reviews_per_day: int,
        learning_steps: List[float],
        lapse_steps: List[float],
        graduating_interval: int,
        new_lapse_interval: int,
        max_interval: int,
        percentages_correct_for_learning_steps: List[int],
        percentages_correct_for_lapse_steps: List[int],
        percentage_good_young: int,
        percentage_good_mature: int,
        percentage_hard_review: int,
        percentage_easy_review: int,
        scheduler_version: int,
        total_number_of_cards: int,
        current_number_mature_cards: int,
    ):
        self.dateArray: DATE_ARRAY_TYPE = date_array
        self.daysToSimulate: int = days_to_simulate
        self.newCardsPerDay: int = new_cards_per_day
        self.intervalModifier: int = interval_modifier
        self.maxReviewsPerDay: int = max_reviews_per_day
        self.learningSteps: List[float] = learning_steps
        self.lapseSteps: List[float] = lapse_steps
        self.graduatingInterval: int = graduating_interval
        self.newLapseInterval: int = new_lapse_interval
        self.maxInterval: int = max_interval
        self.schedulerVersion: int = scheduler_version
        self.totalNumberOfCards: int = total_number_of_cards
        self.currentNumberMatureCards: int = current_number_mature_cards
        self._percentage_hard: Dict[CARD_STATES_TYPE, Union[int, List[int]]] = {
            CARD_STATE_NEW: 0,
            CARD_STATE_LEARNING: 0,
            CARD_STATE_RELEARN: 0,
            CARD_STATE_YOUNG: percentage_hard_review,
            CARD_STATE_MATURE: percentage_hard_review,
        }

        self._percentage_good: Dict[CARD_STATES_TYPE, Union[int, List[int]]] = {
            CARD_STATE_NEW: percentages_correct_for_learning_steps,
            CARD_STATE_LEARNING: percentages_correct_for_learning_steps,
            CARD_STATE_RELEARN: percentages_correct_for_lapse_steps,
            CARD_STATE_YOUNG: percentage_good_young,
            CARD_STATE_MATURE: percentage_good_mature,
        }

        self._percentage_easy: Dict[CARD_STATES_TYPE, Union[int, List[int]]] = {
            CARD_STATE_NEW: 0,
            CARD_STATE_LEARNING: 0,
            CARD_STATE_RELEARN: 0,
            CARD_STATE_YOUNG: percentage_easy_review,
            CARD_STATE_MATURE: percentage_easy_review,
        }

    def reviewAnswer(self, state: CARD_STATES_TYPE, step: int) -> REVIEW_ANSWER:

        randNumber = randint(1, 100)
        percentage_hard = self._percentage_hard[state]
        if isinstance(percentage_hard, (list, tuple)):
            percentage_right = percentage_hard[step]
        percentage_good = self._percentage_good[state]
        if isinstance(percentage_good, (list, tuple)):
            percentage_good = percentage_good[step]
        percentage_easy = self._percentage_easy[state]
        if isinstance(percentage_easy, (list, tuple)):
            percentage_easy = percentage_easy[step]
        percentage_incorrect = 100 - percentage_hard - percentage_good - percentage_easy
        if percentage_incorrect < 0:
            return (
                -1
            )  # percentage hard + percentage good + percentage easy was more than 100. Returning -1 on every review
        all_percentages = [
            percentage_incorrect,
            percentage_hard,
            percentage_good,
            percentage_easy,
        ]
        percentageSum = 0
        for index, percentage in enumerate(all_percentages):
            percentageSum += percentage
            if percentageSum >= randNumber:
                return index
        return -1

    def nextRevInterval(
        self,
        current_interval: int,
        delay: int,
        ease_factor: int,
        review_answer: REVIEW_ANSWER,
    ) -> int:
        if self.schedulerVersion == 1:
            baseHardInterval = (current_interval + delay // 4) * 1.2
            # Hard factor is 1.2 by default in all simulations and can't be changed.
            # The user may have different actual settings.
        else:
            baseHardInterval = current_interval * 1.2
        constrainedHardInterval = max(
            baseHardInterval * self.intervalModifier, current_interval + 1
        )
        baseGoodInterval = (current_interval + delay // 2) * (ease_factor / 100)
        constrainedGoodInterval = max(
            baseGoodInterval * self.intervalModifier, constrainedHardInterval + 1
        )
        baseEasyInterval = (current_interval + delay) * ease_factor * 1.5
        # Hard factor is 1.5 by default in all simulations and can't be changed.
        # The user may have different actual settings.
        constrainedEasyInterval = max(
            baseEasyInterval * self.intervalModifier, constrainedGoodInterval + 1
        )
        if review_answer == ANSWER_HARD:
            return int(min(constrainedHardInterval, self.maxInterval))
        elif review_answer == ANSWER_GOOD:
            return int(min(constrainedGoodInterval, self.maxInterval))
        elif review_answer == ANSWER_EASY:
            return int(min(constrainedEasyInterval, self.maxInterval))

    def adjustedIvl(
        self, state: CARD_STATES_TYPE, current_day: int, ideal_interval: int
    ):
        # This function is blank for now, but can be used to apply additional review schedules (load balancer, free weekend, etc)
        return ideal_interval

    def simulate(self, controller=None) -> Optional[List[Dict[str, Union[str, int]]]]:
        dayIndex = 0

        matureDeltas: List[int] = []

        while dayIndex < len(self.dateArray):

            if controller:
                controller.day_processed(dayIndex)

            reviewNumber = 0
            daysToAdd = None
            idsDoneToday: List[int] = []
            # some cards may be postponed to the next day. We need to remove them from
            # the current day:
            removeList = []
            matureDeltas.append(0)

            while reviewNumber < len(self.dateArray[dayIndex]):
                if controller and controller.do_cancel:
                    return None

                card = self.dateArray[dayIndex][reviewNumber]
                original_state = card.state

                # Postpone reviews > max reviews per day to the next day:
                if (
                    card.state == CARD_STATE_YOUNG
                    or card.state == CARD_STATE_MATURE
                    and card.id not in idsDoneToday
                ):
                    if len(idsDoneToday) + 1 > self.maxReviewsPerDay:
                        if (dayIndex + 1) < self.daysToSimulate:
                            card.delay += 1
                            self.dateArray[dayIndex + 1].append(card)
                        removeList.append(reviewNumber)
                        reviewNumber += 1
                        continue
                    idsDoneToday.append(card.id)

                review_answer = self.reviewAnswer(card.state, card.step)
                if card.state == CARD_STATE_NEW:
                    if review_answer == ANSWER_WRONG:
                        # New card was incorrect and will become/remain a learning card.
                        card.state = CARD_STATE_LEARNING
                        card.step = 0
                        daysToAdd = self.adjustedIvl(
                            card.state, dayIndex, int(self.learningSteps[0] / 1440)
                        )
                    elif review_answer == ANSWER_HARD:
                        raise ValueError("No support currently for 'hard' new cards.")
                    elif review_answer == ANSWER_GOOD:
                        if card.step < len(self.learningSteps) - 1:
                            # Unseen card was correct and will become a learning card.
                            card.state = CARD_STATE_LEARNING
                            card.step = card.step + 1
                            daysToAdd = self.adjustedIvl(
                                card.state,
                                dayIndex,
                                int(self.learningSteps[card.step] / 1440),
                            )
                        else:
                            # There are no learning steps. Unseen card was correct and will become a young/mature card.
                            card.ivl = self.adjustedIvl(
                                card.state, dayIndex, self.graduatingInterval
                            )
                            if self.graduatingInterval >= 21:
                                card.state = CARD_STATE_MATURE
                            else:
                                card.state = CARD_STATE_YOUNG
                            daysToAdd = card.ivl
                    elif review_answer == ANSWER_EASY:
                        raise ValueError("No support currently for 'easy' new cards.")
                elif card.state == CARD_STATE_LEARNING:
                    if review_answer == ANSWER_WRONG:
                        # Learning card was incorrect and will become/remain a learning card.
                        card.state = CARD_STATE_LEARNING
                        card.step = 0
                        daysToAdd = self.adjustedIvl(
                            card.state, dayIndex, int(self.learningSteps[0] / 1440)
                        )
                    elif review_answer == ANSWER_HARD:
                        raise ValueError("No support currently for 'hard' learning cards.")
                    elif review_answer == ANSWER_GOOD:
                        if card.step < len(self.learningSteps) - 1:
                            # Learning card was correct and will remain a learning card.
                            card.state = CARD_STATE_LEARNING
                            card.step = card.step + 1
                            daysToAdd = self.adjustedIvl(
                                card.state,
                                dayIndex,
                                int(self.learningSteps[card.step] / 1440),
                            )
                        else:
                            # There are no learning steps left. Learning card was correct and will become a
                            # young/mature card.
                            card.ivl = self.adjustedIvl(
                                card.state, dayIndex, self.graduatingInterval
                            )
                            if self.graduatingInterval >= 21:
                                card.state = CARD_STATE_MATURE
                            else:
                                card.state = CARD_STATE_YOUNG
                            daysToAdd = card.ivl
                    elif review_answer == ANSWER_EASY:
                        raise ValueError("No support currently for 'easy' learning cards.")
                elif card.state == CARD_STATE_RELEARN:
                    if review_answer == ANSWER_WRONG:
                        # Relearn card was incorrect and will remain a relearn card.
                        card.state = CARD_STATE_RELEARN
                        card.step = 0
                        card.ivl = max(
                            int(card.ivl * self.newLapseInterval), 1
                        )  # 1 is the minimum interval
                        daysToAdd = self.adjustedIvl(
                            card.state, dayIndex, int(self.lapseSteps[0] / 1440)
                        )
                    elif review_answer == ANSWER_HARD:
                        raise ValueError("No support currently for 'hard' relearn cards.")
                    elif review_answer == ANSWER_GOOD:
                        if card.step < len(self.lapseSteps) - 1:
                            # Relearn card was correct and will remain a relearn card.
                            card.state = CARD_STATE_RELEARN
                            card.step = card.step + 1
                            daysToAdd = self.adjustedIvl(
                                card.state,
                                dayIndex,
                                int(self.lapseSteps[card.step] / 1440),
                            )
                        else:
                            # Relearn card was correct and will become a young/mature card.
                            card.ivl = self.adjustedIvl(
                                CARD_STATE_YOUNG, dayIndex, card.ivl
                            )
                            if card.ivl >= 21:
                                card.state = CARD_STATE_MATURE
                            else:
                                card.state = CARD_STATE_YOUNG
                            daysToAdd = card.ivl
                    elif review_answer == ANSWER_EASY:
                        raise ValueError("No support currently for 'easy' relearn cards.")
                elif card.state == CARD_STATE_YOUNG or card.state == CARD_STATE_MATURE:
                    if review_answer == ANSWER_WRONG:
                        card.state = CARD_STATE_RELEARN
                        card.step = 0
                        card.delay = 0
                        card.ease = max(card.ease - 20, 130)
                        card.ivl = max(int(card.ivl * self.newLapseInterval), 1)
                        daysToAdd = self.adjustedIvl(
                            card.state, dayIndex, int(self.lapseSteps[0] / 1440)
                        )
                    elif review_answer == ANSWER_HARD:
                        idealInterval = self.nextRevInterval(
                            card.ivl, card.delay, card.ease, ANSWER_HARD
                        )
                        adjustedInterval = self.adjustedIvl(
                            card.state, dayIndex, idealInterval
                        )
                        card.ivl = min(
                            max(adjustedInterval, card.ivl + 1), self.maxInterval
                        )
                        card.delay = 0
                        card.ease = max(card.ease - 15, 130)
                        if card.ivl >= 21:
                            card.state = CARD_STATE_MATURE
                        daysToAdd = card.ivl
                    elif review_answer == ANSWER_GOOD:
                        idealInterval = self.nextRevInterval(
                            card.ivl, card.delay, card.ease, ANSWER_GOOD
                        )
                        adjustedInterval = self.adjustedIvl(
                            card.state, dayIndex, idealInterval
                        )
                        card.ivl = min(
                            max(adjustedInterval, card.ivl + 1), self.maxInterval
                        )
                        card.delay = 0
                        if card.ivl >= 21:
                            card.state = CARD_STATE_MATURE
                        daysToAdd = card.ivl
                    elif review_answer == ANSWER_EASY:
                        idealInterval = self.nextRevInterval(
                            card.ivl, card.delay, card.ease, ANSWER_EASY
                        )
                        adjustedInterval = self.adjustedIvl(
                            card.state, dayIndex, idealInterval
                        )
                        card.ivl = min(
                            max(adjustedInterval, card.ivl + 1), self.maxInterval
                        )
                        card.delay = 0
                        card.ease = card.ease + 15
                        if card.ivl >= 21:
                            card.state = CARD_STATE_MATURE
                        daysToAdd = card.ivl

                if original_state != CARD_STATE_MATURE and card.state == CARD_STATE_MATURE:
                    matureDeltas[dayIndex] += 1
                elif original_state == CARD_STATE_MATURE and card.state != CARD_STATE_MATURE:
                    matureDeltas[dayIndex] -= 1

                if (
                    daysToAdd is not None
                    and (dayIndex + daysToAdd) < self.daysToSimulate
                ):
                    self.dateArray[dayIndex + daysToAdd].append(card)

                reviewNumber += 1

            # We will now remove all postponed reviews from their original day:
            for index in sorted(removeList, reverse=True):
                del self.dateArray[dayIndex][index]

            dayIndex += 1

        today = date.today()

        totalCardsPerDay = [len(day) for day in self.dateArray]
        matureDeltas[0] += self.currentNumberMatureCards
        return [
            {
                "x": (today + timedelta(days=index)).isoformat(),
                "y": reviews,
                "dayNumber": (index + 1),
                "accumulate": accumulate,
                "average": accumulate/(index+1),
                "totalNumberOfCards": self.totalNumberOfCards,
                "matureCount": matureCount
            }
            for index, (reviews, accumulate, matureCount) in enumerate(
                zip(totalCardsPerDay, accumulate(totalCardsPerDay), accumulate(matureDeltas))
            )
        ]  # Returns the number of reviews for each day
