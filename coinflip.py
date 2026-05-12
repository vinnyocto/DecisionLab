import random

def run_simulation(trials, starting_money, bet_amount):
    money = starting_money
    wins = 0
    losses = 0
    history = [money]

    peak = money
    max_drawdown = 0

    for _ in range(trials):
        flip = random.random()  # 0 to 1

        if flip < 0.5:
            money += bet_amount
            wins += 1
        else:
            money -= bet_amount
            losses += 1

        history.append(money)

        # Track drawdown (nice quant metric)
        if money > peak:
            peak = money
        drawdown = peak - money
        max_drawdown = max(max_drawdown, drawdown)

    profit = money - starting_money
    win_rate = wins / trials if trials > 0 else 0

    return {
        "final_money": money,
        "profit": profit,
        "wins": wins,
        "losses": losses,
        "history": history,
        "win_rate": round(win_rate, 3),
        "max_drawdown": max_drawdown
    }