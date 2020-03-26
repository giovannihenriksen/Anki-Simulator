
import datetime

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
    ):
        # Before we start the simulation, we will collect all the cards from the database.
        crt = datetime.date.fromtimestamp(
            self._mw.col.crt
        )  # Gets collection creation time. We need this to find out when a card is due.
        today = datetime.date.today()
        todayInteger = (today - crt).days
        dateArray = []
        while len(dateArray) < days_to_simulate:
            dateArray.append([])
        newCards = []
        cids = self._mw.col.decks.cids(did, True)
        for cid in cids:
            card = self._mw.col.getCard(cid)
            if card.type == 0:
                # New card
                if card.queue != -1 or include_suspended_new_cards:
                    review = dict(
                        id=card.id,
                        ease=starting_ease,
                        state="unseen",
                        step=0,
                        reviews=[],
                        delay=0,
                    )
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
                review = dict(
                    id=card.id,
                    ease=starting_ease,
                    state="learning",
                    step=max(number_of_learning_steps - (card.left % 10), -1),
                    reviews=[],
                    delay=0,
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
                review = dict(
                    id=card.id, ease=card.factor / 10, currentInterval=card.ivl, delay=0
                )
                if card.ivl >= 21:
                    review["state"] = "mature"
                else:
                    review["state"] = "young"
                review["reviews"] = []
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
                review = dict(
                    id=card.id,
                    ease=card.factor / 10,
                    state="relearn",
                    currentInterval=card.ivl,
                    step=max(number_of_lapse_steps - (card.left % 10), -1),
                    reviews=[],
                    delay=0,
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

    def generate_for_new_count(
        self,
        days_to_simulate,
        number_of_new_cards_per_day,
        new_cards_in_deck,
        starting_ease,
    ):
        cards_left = new_cards_in_deck
        dateArray = []
        for day in range(days_to_simulate):
            if not cards_left:
                dateArray.append([])
                continue

            cards_for_the_day = []
            left_today = min(number_of_new_cards_per_day, cards_left)

            for cid in range(left_today):
                cards_for_the_day.append(
                    dict(
                        id=cid,
                        ease=starting_ease,
                        state="unseen",
                        step=0,
                        reviews=[],
                        delay=0,
                    )
                )

            dateArray.append(cards_for_the_day)

            cards_left -= left_today

        return dateArray
