import random
from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import current_user

from models import db, BlackjackResult

blackjack_bp = Blueprint("blackjack", __name__)


def create_deck():
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    deck = [rank + suit for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck


def card_rank(card):
    return card[:-1]


def card_value(card):
    rank = card_rank(card)

    if rank in ["J", "Q", "K"]:
        return 10
    if rank == "A":
        return 11

    return int(rank)


def hand_value(hand):
    total = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card_rank(card) == "A")

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total


# ✅ NEW: natural blackjack check
def is_blackjack(hand):
    return len(hand) == 2 and hand_value(hand) == 21


def basic_strategy_hint(player_hand, dealer_upcard):
    player_total = hand_value(player_hand)
    dealer_value = card_value(dealer_upcard)

    if player_total >= 17:
        return f"You have {player_total}, dealer shows {dealer_value} → Suggested move: Stand"

    if player_total <= 11:
        return f"You have {player_total}, dealer shows {dealer_value} → Suggested move: Hit"

    if 12 <= player_total <= 16:
        if dealer_value >= 7:
            return f"You have {player_total}, dealer shows {dealer_value} → Suggested move: Hit"
        else:
            return f"You have {player_total}, dealer shows {dealer_value} → Suggested move: Stand"

    return f"You have {player_total}, dealer shows {dealer_value} → Suggested move: Hit"


def has_active_round():
    return session.get("round_started", False)


def can_split():
    if not has_active_round():
        return False

    hands = session.get("player_hands", [])

    if len(hands) != 1:
        return False

    hand = hands[0]

    if len(hand) != 2:
        return False

    bankroll = session.get("bankroll", 1000)
    wager = session.get("wager", 25)

    return card_value(hand[0]) == card_value(hand[1]) and bankroll >= wager


def can_double():
    if not has_active_round():
        return False

    hands = session.get("player_hands", [])
    active = session.get("active_hand", 0)

    if session.get("game_over"):
        return False

    if active >= len(hands):
        return False

    hand = hands[active]
    bankroll = session.get("bankroll", 1000)
    wager = session.get("wager", 25)

    return len(hand) == 2 and bankroll >= wager


def render_game(show_dealer=False):
    hands = session.get("player_hands", [])
    active = session.get("active_hand", 0)
    dealer_hand = session.get("dealer_hand", [])

    strategy_hint = ""

    if session.get("round_started", False) and not session.get("game_over", False):
        if hands and dealer_hand:
            strategy_hint = basic_strategy_hint(hands[active], dealer_hand[0])

    return render_template(
        "blackjack.html",
        round_started=session.get("round_started", False),
        dealer_hand=dealer_hand,
        dealer_total=hand_value(dealer_hand) if dealer_hand else 0,
        player_hands=hands,
        active_hand=active,
        hand_totals=[hand_value(hand) for hand in hands],
        show_dealer=show_dealer,
        message=session.get("message", "Choose your wager, then deal."),
        game_over=session.get("game_over", False),
        bankroll=session.get("bankroll", 1000),
        wager=session.get("wager", 25),
        can_split=can_split(),
        can_double=can_double(),
        strategy_hint=strategy_hint,
    )


@blackjack_bp.route("/blackjack")
def blackjack():
    if "bankroll" not in session:
        session["bankroll"] = 1000

    if "wager" not in session:
        session["wager"] = 25

    session["round_started"] = False
    session["game_over"] = False
    session["deck"] = []
    session["player_hands"] = []
    session["dealer_hand"] = []
    session["active_hand"] = 0
    session["message"] = "Choose your wager, then press Deal."

    return render_game(show_dealer=False)


@blackjack_bp.route("/blackjack/bet/<int:amount>")
def set_bet(amount):
    bankroll = session.get("bankroll", 1000)

    if session.get("round_started"):
        session["message"] = "You can only change your wager before dealing."
        return render_game(show_dealer=False)

    if amount <= bankroll:
        session["wager"] = amount
        session["message"] = f"Wager set to ${amount}. Press Deal."
    else:
        session["message"] = "You do not have enough bankroll for that wager."

    return render_game(show_dealer=False)


@blackjack_bp.route("/blackjack/deal")
def deal():
    wager = session.get("wager", 25)
    bankroll = session.get("bankroll", 1000)

    if wager > bankroll:
        session["message"] = "Your wager is higher than your bankroll."
        return render_game(show_dealer=False)

    deck = create_deck()

    session["deck"] = deck
    session["player_hands"] = [[deck.pop(), deck.pop()]]
    session["dealer_hand"] = [deck.pop(), deck.pop()]
    session["active_hand"] = 0
    session["round_started"] = True
    session["game_over"] = False
    session["message"] = "Choose Hit, Stand, Double, or Split."

    # ✅ NEW: automatic natural blackjack result
    player_hand = session["player_hands"][0]
    dealer_hand = session["dealer_hand"]

    if is_blackjack(player_hand):
        if is_blackjack(dealer_hand):
            session["message"] = "Both player and dealer have blackjack. Push."
            result_label = "push"
        else:
            winnings = int(wager * 1.5)
            session["bankroll"] += winnings
            session["message"] = f"Blackjack! You win ${winnings}."
            result_label = "win"

        session["game_over"] = True

        if current_user.is_authenticated:
            saved_result = BlackjackResult(
                user_id=current_user.id,
                result=result_label,
                wager=wager,
                bankroll_after=session["bankroll"],
                player_total=hand_value(player_hand),
                dealer_total=hand_value(dealer_hand)
            )

            db.session.add(saved_result)
            db.session.commit()

        return render_game(show_dealer=True)

    return render_game(show_dealer=False)


@blackjack_bp.route("/blackjack/hit")
def hit():
    if not has_active_round():
        return redirect(url_for("blackjack.blackjack"))

    if session.get("game_over"):
        return redirect(url_for("blackjack.blackjack"))

    deck = session["deck"]
    hands = session["player_hands"]
    active = session["active_hand"]

    hands[active].append(deck.pop())

    session["player_hands"] = hands
    session["deck"] = deck

    if hand_value(hands[active]) > 21:
        if active + 1 < len(hands):
            session["active_hand"] = active + 1
            session["message"] = "Hand busted. Moving to next hand."
            return render_game(show_dealer=False)

        return finish_round()

    session["message"] = "Choose Hit, Stand, or Double."
    return render_game(show_dealer=False)


@blackjack_bp.route("/blackjack/stand")
def stand():
    if not has_active_round():
        return redirect(url_for("blackjack.blackjack"))

    active = session["active_hand"]
    hands = session["player_hands"]

    if active + 1 < len(hands):
        session["active_hand"] = active + 1
        session["message"] = "Next hand."
        return render_game(show_dealer=False)

    return finish_round()


@blackjack_bp.route("/blackjack/double")
def double():
    if not can_double():
        session["message"] = "Double down is not available."
        return render_game(show_dealer=False)

    session["wager"] *= 2

    deck = session["deck"]
    hands = session["player_hands"]
    active = session["active_hand"]

    hands[active].append(deck.pop())

    session["deck"] = deck
    session["player_hands"] = hands
    session["message"] = "You doubled down."

    return stand()


@blackjack_bp.route("/blackjack/split")
def split():
    if not can_split():
        session["message"] = "Split is not available."
        return render_game(show_dealer=False)

    deck = session["deck"]
    original = session["player_hands"][0]

    hand1 = [original[0], deck.pop()]
    hand2 = [original[1], deck.pop()]

    session["player_hands"] = [hand1, hand2]
    session["active_hand"] = 0
    session["deck"] = deck
    session["message"] = "Split successful. Play hand 1."

    return render_game(show_dealer=False)


def finish_round():
    deck = session["deck"]
    dealer_hand = session["dealer_hand"]

    while hand_value(dealer_hand) < 17:
        dealer_hand.append(deck.pop())

    session["dealer_hand"] = dealer_hand
    session["deck"] = deck

    dealer_total = hand_value(dealer_hand)
    wager = session["wager"]
    total_change = 0
    results = []

    final_player_total = 0

    for i, hand in enumerate(session["player_hands"]):
        player_total = hand_value(hand)
        final_player_total = player_total

        if player_total > 21:
            total_change -= wager
            results.append(f"Hand {i + 1}: bust, lost ${wager}")
        elif dealer_total > 21:
            total_change += wager
            results.append(f"Hand {i + 1}: dealer bust, won ${wager}")
        elif player_total > dealer_total:
            total_change += wager
            results.append(f"Hand {i + 1}: won ${wager}")
        elif player_total < dealer_total:
            total_change -= wager
            results.append(f"Hand {i + 1}: lost ${wager}")
        else:
            results.append(f"Hand {i + 1}: push")

    session["bankroll"] += total_change
    session["game_over"] = True
    session["round_started"] = True
    session["message"] = " | ".join(results)

    if total_change > 0:
        result_label = "win"
    elif total_change < 0:
        result_label = "loss"
    else:
        result_label = "push"

    if current_user.is_authenticated:
        saved_result = BlackjackResult(
            user_id=current_user.id,
            result=result_label,
            wager=wager,
            bankroll_after=session["bankroll"],
            player_total=final_player_total,
            dealer_total=dealer_total
        )

        db.session.add(saved_result)
        db.session.commit()

    return render_game(show_dealer=True)


@blackjack_bp.route("/blackjack/reset")
def reset_bankroll():
    session.clear()
    session["bankroll"] = 1000
    session["wager"] = 25

    return redirect(url_for("blackjack.blackjack"))