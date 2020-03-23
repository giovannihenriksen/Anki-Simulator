from datetime import date, timedelta
from random import randint

class Simulator:

    def __init__(self, date_array, days_to_simulate, new_cards_per_day, interval_modifier, max_reviews_per_day,
                 learning_steps, lapse_steps, graduating_interval, new_lapse_interval, max_interval,
                 chance_right_unseen, percentages_correct_for_learning_steps, percentages_correct_for_lapse_steps,
                 chance_right_young, chance_right_mature):
        self.dateArray = date_array
        self.daysToSimulate = days_to_simulate
        self.newCardsPerDay = new_cards_per_day
        self.intervalModifier = interval_modifier
        self.maxReviewsPerDay = max_reviews_per_day
        self.learningSteps = learning_steps
        self.lapseSteps = lapse_steps
        self.graduatingInterval = graduating_interval
        self.newLapseInterval = new_lapse_interval
        self.maxInterval = max_interval
        self.chanceRightUnseen = chance_right_unseen
        self.percentagesCorrectForLearningSteps = percentages_correct_for_learning_steps
        self.percentagesCorrectForLapseSteps = percentages_correct_for_lapse_steps
        self.chanceRightYoung = chance_right_young
        self.chanceRightMature = chance_right_mature

    def reviewCorrect(self, state, step):
        randNumber = randint(1, 100)
        if state == 'unseen' and randNumber <= 100 - self.chanceRightUnseen * 100:
            return False  # card incorrect
        elif state == 'learning' and randNumber <= 100 - self.percentagesCorrectForLearningSteps[step] * 100:
            return False  # card incorrect
        elif state == 'relearn' and randNumber <= 100 - self.percentagesCorrectForLapseSteps[step] * 100:
            return False  # card incorrect
        elif state == 'young' and randNumber <= 100 - self.chanceRightYoung * 100:
            return False  # card incorrect
        elif state == 'mature' and randNumber <= 100 - self.chanceRightMature * 100:
            return False  # card incorrect
        return True  # card correct

    def simulate(self, controller=None):
        dayIndex = 0
        while dayIndex < len(self.dateArray):

            if controller:
                controller.tick.emit(dayIndex)
            
            reviewNumber = 0
            idsDoneToday = []
            removeList = []  # some cards may be postponed to the next day. We need to remove them from the
            # current day.
            while reviewNumber < len(self.dateArray[dayIndex]):
                if controller and controller.do_cancel:
                    return None
                
                originalReview = self.dateArray[dayIndex][reviewNumber].copy()
                originalId = originalReview['id']
                originalEase = originalReview['ease']
                originalCurrentInterval = originalReview.get('currentInterval')
                originalState = originalReview['state']
                originalStep = originalReview.get('step')
                newReview = self.dateArray[dayIndex][reviewNumber].copy()

                # Postpone reviews > max reviews per day to the next day:
                if originalState == 'young' or originalState == 'mature' and originalId not in idsDoneToday:
                    if len(idsDoneToday) + 1 > self.maxReviewsPerDay:
                        if (dayIndex + 1) < self.daysToSimulate:
                            self.dateArray[dayIndex + 1].append(newReview)
                        removeList.append(reviewNumber)
                        reviewNumber += 1
                        continue
                    idsDoneToday.append(originalId)

                reviewCorrect = self.reviewCorrect(originalState, originalStep)
                if reviewCorrect:
                    if originalState == 'unseen' or originalState == 'learning':
                        if originalStep < len(self.learningSteps) - 1:
                            # Unseen/learning card was correct and will become/remain a learning card.
                            newReview['state'] = 'learning'
                            newReview['step'] = originalStep + 1
                            daysToAdd = int(self.learningSteps[newReview['step']] / 1440)
                            daysToAdd = min(daysToAdd, self.maxInterval)
                            newReview['reviews'].append(
                                dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                     becomes=newReview['state'], newEase=newReview['ease']))
                            if (dayIndex + daysToAdd) < self.daysToSimulate:
                                self.dateArray[dayIndex + daysToAdd].append(newReview)
                        else:
                            # Learning card was correct and will become a young/mature card.
                            newReview['currentInterval'] = min(self.graduatingInterval, self.maxInterval)
                            if self.graduatingInterval >= 21:
                                newReview['state'] = 'mature'
                            else:
                                newReview['state'] = 'young'
                            daysToAdd = newReview['currentInterval']
                            newReview['reviews'].append(
                                dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                     becomes=newReview['state'], newEase=newReview['ease']))
                            if (dayIndex + daysToAdd) < self.daysToSimulate:
                                self.dateArray[dayIndex + daysToAdd].append(newReview)
                    elif originalState == 'relearn':
                        if originalStep < len(self.lapseSteps) - 1:
                            # Relearn card was correct and will remain a relearn card.
                            newReview['state'] = 'relearn'
                            newReview['step'] = originalStep + 1
                            daysToAdd = int(self.lapseSteps[newReview['step']] / 1440)
                            daysToAdd = min(daysToAdd, self.maxInterval)
                            newReview['reviews'].append(
                                dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                     becomes=newReview['state'], newEase=newReview['ease']))
                            if (dayIndex + daysToAdd) < self.daysToSimulate:
                                self.dateArray[dayIndex + daysToAdd].append(newReview)
                        else:
                            # Relearn card was correct and will become a young/mature card.
                            newReview['currentInterval'] = int(originalCurrentInterval * self.intervalModifier)
                            newReview['currentInterval'] = min(newReview['currentInterval'], self.maxInterval)
                            if newReview['currentInterval'] >= 21:
                                newReview['state'] = 'mature'
                            else:
                                newReview['state'] = 'young'
                            daysToAdd = newReview['currentInterval']
                            newReview['reviews'].append(
                                dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                     becomes=newReview['state'], newEase=newReview['ease']))
                            if (dayIndex + daysToAdd) < self.daysToSimulate:
                                self.dateArray[dayIndex + daysToAdd].append(newReview)
                    elif originalState == 'young':
                        # Young card was correct and might become a mature card.
                        newReview['currentInterval'] = int(
                            ((originalCurrentInterval * newReview['ease']) / 100) * self.intervalModifier)
                        newReview['currentInterval'] = min(newReview['currentInterval'], self.maxInterval)
                        if newReview['currentInterval'] >= 21:
                            newReview['state'] = 'mature'
                        daysToAdd = newReview['currentInterval']
                        newReview['reviews'].append(
                            dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                 becomes=newReview['state'], newEase=newReview['ease']))
                        if (dayIndex + daysToAdd) < self.daysToSimulate:
                            self.dateArray[dayIndex + daysToAdd].append(newReview)
                    elif originalState == 'mature':
                        # Mature card was correct and will remain a mature card.
                        newReview['currentInterval'] = int(
                            ((originalCurrentInterval * newReview['ease']) / 100) * self.intervalModifier)
                        newReview['currentInterval'] = min(newReview['currentInterval'], self.maxInterval)
                        daysToAdd = newReview['currentInterval']
                        newReview['reviews'].append(
                            dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                 becomes=newReview['state'], newEase=newReview['ease']))
                        if (dayIndex + daysToAdd) < self.daysToSimulate:
                            self.dateArray[dayIndex + daysToAdd].append(newReview)
                else:
                    if originalState == 'unseen' or originalState == 'learning':
                        # Unseen/learning card was incorrect and will become/remain a learning card.
                        newReview['state'] = 'learning'
                        newReview['step'] = 0
                        daysToAdd = int(self.learningSteps[0] / 1440)
                        daysToAdd = min(daysToAdd, self.maxInterval)
                        newReview['reviews'].append(
                            dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                 becomes=newReview['state'], newEase=newReview['ease']))
                        if (dayIndex + daysToAdd) < self.daysToSimulate:
                            self.dateArray[dayIndex + daysToAdd].append(newReview)
                    elif originalState == 'relearn':
                        # Relearn card was incorrect and will remain a relearn card.
                        newReview['state'] = 'relearn'
                        newReview['step'] = 0
                        daysToAdd = int(self.lapseSteps[0] / 1440)
                        daysToAdd = min(daysToAdd, self.maxInterval)
                        newReview['reviews'].append(
                            dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                 becomes=newReview['state'], newEase=newReview['ease']))
                        if (dayIndex + daysToAdd) < self.daysToSimulate:
                            self.dateArray[dayIndex + daysToAdd].append(newReview)
                    elif originalState == 'young' or originalState == 'mature':
                        # Young/mature card was incorrect and will become a relearn card.
                        newReview['state'] = 'relearn'
                        newReview['step'] = 0
                        newReview['ease'] = max(originalEase - 20, 130)
                        newInterval = int(originalCurrentInterval * self.newLapseInterval)
                        newReview['currentInterval'] = max(newInterval, 3)
                        daysToAdd = int(self.lapseSteps[0] / 1440)
                        daysToAdd = min(daysToAdd, self.maxInterval)
                        newReview['reviews'].append(
                            dict(day=dayIndex, wasState=originalState, correct=reviewCorrect, daysToAdd=daysToAdd,
                                 becomes=newReview['state'], newEase=newReview['ease']))
                        if (dayIndex + daysToAdd) < self.daysToSimulate:
                            self.dateArray[dayIndex + daysToAdd].append(newReview)
                reviewNumber += 1
            # We will now remove all postponed reviews from their original day:
            for index in sorted(removeList, reverse=True):
                del self.dateArray[dayIndex][index]
            dayIndex += 1
        today = date.today()
        return [dict(x=(today + timedelta(days=index)), y=len(reviews)) for index, reviews in
                enumerate(self.dateArray)]  # Returns the number of reviews for each day
